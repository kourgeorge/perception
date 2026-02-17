"""
Main game loop: input, update, draw, gate state machine, teleport trigger.
"""
import math
import random
import time
from typing import Callable, List, Optional

import pygame

from game.grid import GridConfig, cell_to_pixel, is_wall, in_bounds, get_playable_cells
from game.arena import build_pellet_cells
from game.entities import Player, Ghost, PelletMap, make_pellet_map, pellet_points
from game.ghosts import move_ghosts, check_ghost_player_collision
from game.gates import (
    BlockGateConfig,
    GateState,
    enter_gate,
    update_gate,
    clear_ghosts_at_gate,
    gate_cell,
    MIN_WAIT_SEC,
)
from game.render import (
    draw_arena,
    draw_pellets,
    draw_gates,
    draw_player,
    draw_ghosts,
    draw_quarantine_message,
    draw_quarantine_halo,
    draw_blast,
    draw_death_screen,
    draw_all_pellets_collected_screen,
)
from game.logger import ExperimentLogger

# Movement: arrow keys; one cell per keypress, or continue moving while key is held
MOVE_KEYS = {
    pygame.K_UP: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_RIGHT: (1, 0),
}
PLAYER_MOVE_DELAY_SEC = 0.12  # min time between moves when holding an arrow
EXIT_KEY = pygame.K_SPACE

# Quarantine: ~0.5 min (30s) with distribution between teleports
TELEPORT_MIN_INTERVAL_SEC = 30.0
TELEPORTS_PER_BLOCK = 2

# One cell per arrow keypress (no continuous movement)
# Ghosts move slower so the user can avoid them
GHOST_MOVE_DELAY_SEC = 0.55
# Invincibility after losing a life (seconds)
RESPAWN_INVINCIBILITY_SEC = 2.0


def run_block(
    screen: pygame.Surface,
    font: pygame.font.Font,
    config: GridConfig,
    block_config: BlockGateConfig,
    block_id: int,
    logger: ExperimentLogger,
    teleport_interval_sec: float = TELEPORT_MIN_INTERVAL_SEC,
    teleports_per_block: int = TELEPORTS_PER_BLOCK,
) -> tuple[int, bool]:
    """Run one block. Returns (score for this block, user_quit)."""
    clock = pygame.time.Clock()
    cell_size = config.cell_size

    # Pellets
    pellet_list = build_pellet_cells(seed=block_id)
    pellets: PelletMap = make_pellet_map(pellet_list)

    # Player start: random playable cell
    playable = get_playable_cells()
    if not playable:
        playable = [(config.cols // 2, config.rows // 2)]
    start_col, start_row = random.choice(playable)
    player = Player(col=start_col, row=start_row, lives=3)

    # Ghosts: spawn on playable cells, not on player
    other_cells = [c for c in playable if c != (start_col, start_row)]
    ghost_starts = random.sample(other_cells, min(3, len(other_cells))) if len(other_cells) >= 3 else []
    while len(ghost_starts) < 3 and other_cells:
        c = random.choice(other_cells)
        if c not in ghost_starts:
            ghost_starts.append(c)
    ghosts = [
        Ghost(id=i, col=ghost_starts[i][0], row=ghost_starts[i][1], direction=random.choice([(0, -1), (0, 1), (-1, 0), (1, 0)]))
        for i in range(min(3, len(ghost_starts)))
    ]

    gate_state = GateState()
    last_ghost_time = time.perf_counter()
    last_move_time = time.perf_counter()
    next_teleport_time = time.perf_counter() + teleport_interval_sec * (0.7 + 0.6 * random.random())
    teleport_count_this_block = 0
    exit_key_just_pressed = False
    user_quit = False

    logger.log_block_start(block_id, block_config.left_gate_row, block_config.right_gate_row)

    def on_gate_exit(t_exit: float, early_tap_count: int, exited_by_key: bool) -> None:
        duration = t_exit - gate_state.enter_time
        logger.log_gate_exit(duration, early_tap_count, exited_by_key)
        clear_ghosts_at_gate(gate_state, ghosts)

    running = True
    while running:
        now = time.perf_counter()
        exit_key_just_pressed = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                user_quit = True
                break
            if event.type == pygame.KEYDOWN:
                logger.log_key(pygame.key.name(event.key))
                if event.key == EXIT_KEY:
                    exit_key_just_pressed = True
                # Arrow keys: immediate one cell move on keypress
                if not gate_state.active and event.key in MOVE_KEYS and not player.frozen:
                    dc, dr = MOVE_KEYS[event.key]
                    nc, nr = player.col + dc, player.row + dr
                    if not is_wall(nc, nr) and in_bounds(nc, nr):
                        player.col, player.row = nc, nr
                        player.direction = (dc, dr)
                        last_move_time = now
                        cell = (player.col, player.row)
                        if cell in pellets:
                            ptype = pellets.pop(cell)
                            pts = pellet_points(ptype)
                            player.score += pts
                            logger.log_pellet(player.col, player.row, ptype, pts, player.score)

        if not running:
            break

        # Gate logic
        if gate_state.active:
            if update_gate(gate_state, player, ghosts, now, exit_key_just_pressed, on_gate_exit):
                pass  # already cleared ghosts in on_gate_exit
        else:
            # Continuous movement: if an arrow is held, move one cell after delay
            if not gate_state.active and not player.frozen and (now - last_move_time) >= PLAYER_MOVE_DELAY_SEC:
                keys = pygame.key.get_pressed()
                for key, (dc, dr) in MOVE_KEYS.items():
                    if keys[key]:
                        nc, nr = player.col + dc, player.row + dr
                        if not is_wall(nc, nr) and in_bounds(nc, nr):
                            player.col, player.row = nc, nr
                            player.direction = (dc, dr)
                            last_move_time = now
                            cell = (player.col, player.row)
                            if cell in pellets:
                                ptype = pellets.pop(cell)
                                pts = pellet_points(ptype)
                                player.score += pts
                                logger.log_pellet(player.col, player.row, ptype, pts, player.score)
                        break
            # Teleport trigger
            if (
                teleport_count_this_block < teleports_per_block
                and now >= next_teleport_time
                and not player.frozen
            ):
                side: str = random.choice(["left", "right"])
                enter_gate(player, gate_state, block_config, side, now)
                logger.log_teleport(side, gate_state.gate_row or 0, gate_state.return_col, gate_state.return_row)
                teleport_count_this_block += 1
                # Next quarantine in ~0.5 min with distribution (e.g. 21–39 s)
                next_teleport_time = now + teleport_interval_sec * (0.7 + 0.6 * random.random())

            # Ghost movement
            if now - last_ghost_time >= GHOST_MOVE_DELAY_SEC:
                last_ghost_time = now
                move_ghosts(ghosts)

            # Ghost collision: Pac-Man dies (lose a life)
            if now < player.invincible_until:
                hit = []
            else:
                hit = check_ghost_player_collision(ghosts, player)
            if hit:
                for gid in hit:
                    logger.log_ghost_contact(gid)
                player.lives -= 1
                # Blast animation at avatar position, then death overlay
                cx, cy = cell_to_pixel(player.col, player.row, config.cell_size)
                blast_frames = 14
                blast_duration_ms = 480
                frame_ms = blast_duration_ms // blast_frames
                for frame in range(blast_frames):
                    progress = frame / (blast_frames - 1) if blast_frames > 1 else 1.0
                    screen.fill((0, 0, 0))
                    draw_arena(screen, config, block_config)
                    draw_pellets(screen, pellets, config)
                    draw_ghosts(screen, ghosts, config)
                    draw_player(screen, player, config)
                    draw_blast(screen, cx, cy, progress, config.cell_size)
                    pygame.display.flip()
                    pygame.time.wait(frame_ms)
                screen.fill((0, 0, 0))
                draw_arena(screen, config, block_config)
                draw_pellets(screen, pellets, config)
                draw_ghosts(screen, ghosts, config)
                draw_player(screen, player, config)
                draw_death_screen(screen, font, player.lives)
                if player.lives <= 0:
                    pygame.time.wait(2500)
                    running = False
                    break
                pygame.time.wait(1500)
                # Respawn at start and brief invincibility
                player.col, player.row = start_col, start_row
                player.invincible_until = now + RESPAWN_INVINCIBILITY_SEC
                player.direction = None

        # All pellets consumed: game over, show score
        if len(pellets) == 0:
            draw_all_pellets_collected_screen(screen, font, player.score)
            waiting = True
            while waiting:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        waiting = False
                        user_quit = True
                    if ev.type == pygame.KEYDOWN and ev.key == EXIT_KEY:
                        waiting = False
                pygame.time.wait(50)
            running = False
            break

        # Draw
        screen.fill((0, 0, 0))
        draw_arena(screen, config, block_config)
        draw_pellets(screen, pellets, config)
        draw_gates(screen, block_config, gate_state, config)
        draw_ghosts(screen, ghosts, config)
        if gate_state.active:
            draw_quarantine_halo(screen, player, config)
        mouth_angle = 0.35 + 0.35 * (1 + math.sin(now * 10)) / 2
        draw_player(screen, player, config, mouth_angle=mouth_angle)
        if gate_state.active:
            draw_quarantine_message(screen, font, gate_state.early_tap_count)
        # Score and lives
        score_text = font.render(f"Score: {player.score}", True, (240, 240, 240))
        screen.blit(score_text, (10, 10))
        lives_text = font.render(f"Lives: {player.lives}", True, (240, 240, 240))
        screen.blit(lives_text, (10, 34))
        if now < player.invincible_until:
            flash = (255, 255, 255) if int(now * 8) % 2 == 0 else (255, 255, 0)
            pygame.draw.rect(screen, flash, (screen.get_width() - 120, 8, 112, 24), 2)
            inv_text = font.render("Invincible", True, flash)
            screen.blit(inv_text, (screen.get_width() - 115, 10))
        pygame.display.flip()
        clock.tick(60)

    logger.log_block_end(block_id)
    return (player.score, user_quit)


def run_instructions(screen: pygame.Surface, font: pygame.font.Font) -> None:
    from game.render import draw_instructions
    draw_instructions(screen, font)
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                waiting = False
            if event.type == pygame.KEYDOWN and event.key == EXIT_KEY:
                waiting = False
        pygame.time.wait(50)
