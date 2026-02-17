"""
Draw grid, zones, pellets, ghosts, player, gates, and instruction/end screens.
"""
import math
import pygame
from typing import Dict, List, Optional, Tuple

from game.grid import (
    CENTER_COL,
    CENTER_ROW,
    BOTTOM_STRIPE_ROWS,
    TOP_STRIPE_ROWS,
    DISK_RADIUS_COLS,
    DISK_RADIUS_ROWS,
    PLAYABLE_COL_MIN,
    PLAYABLE_COL_MAX,
    PLAYABLE_ROW_MIN,
    PLAYABLE_ROW_MAX,
    MAZE_WALLS,
    cell_to_pixel,
    is_wall,
    COLS,
    ROWS,
)
from game.grid import GridConfig
from game.entities import Player, Ghost, PelletMap
from game.arena import HIGH_VALUE
from game.gates import GateState, BlockGateConfig


# Colors (RGB)
BG = (20, 20, 30)
WALL = (40, 50, 120)  # Pac-Man style blue walls
WALL_EDGE = (80, 100, 200)
ZONE_TOP = (80, 40, 60)
ZONE_BOTTOM = (60, 40, 80)
ZONE_CENTER = (40, 70, 60)
PELLET_HIGH = (255, 220, 100)
PELLET_LOW = (120, 120, 140)
PACMAN_YELLOW = (255, 255, 0)
PACMAN_MOUTH = (0, 0, 0)
GHOST_COLOR = (255, 100, 100)
GATE_COLOR = (150, 150, 200)
GATE_ACTIVE = (200, 180, 255)
TEXT_COLOR = (240, 240, 240)
EARLY_TAP_MSG = (255, 180, 80)


def draw_arena(surface: pygame.Surface, config: GridConfig, gate_config: Optional[BlockGateConfig] = None) -> None:
    cs = config.cell_size
    # Draw floor and hot zones only for playable non-wall cells
    for row in range(PLAYABLE_ROW_MIN, PLAYABLE_ROW_MAX + 1):
        for col in range(PLAYABLE_COL_MIN, PLAYABLE_COL_MAX + 1):
            if (col, row) in MAZE_WALLS:
                continue
            x, y = col * cs, row * cs
            if row in TOP_STRIPE_ROWS:
                pygame.draw.rect(surface, ZONE_TOP, (x, y, cs, cs))
            elif row in BOTTOM_STRIPE_ROWS:
                pygame.draw.rect(surface, ZONE_BOTTOM, (x, y, cs, cs))
            elif (
                abs(col - CENTER_COL) <= DISK_RADIUS_COLS
                and abs(row - CENTER_ROW) <= DISK_RADIUS_ROWS
            ):
                pygame.draw.rect(surface, ZONE_CENTER, (x, y, cs, cs))
            else:
                pygame.draw.rect(surface, BG, (x, y, cs, cs))
            pygame.draw.rect(surface, (50, 50, 60), (x, y, cs, cs), 1)
    # Boundary walls and maze walls (Pac-Man style)
    for row in range(config.rows):
        for col in range(config.cols):
            if not is_wall(col, row):
                continue
            # Skip gate cells so gates can be drawn on top
            if gate_config:
                if col == 0 and row == gate_config.left_gate_row:
                    continue
                if col == config.cols - 1 and row == gate_config.right_gate_row:
                    continue
            x, y = col * cs, row * cs
            pygame.draw.rect(surface, WALL, (x + 1, y + 1, cs - 2, cs - 2))
            pygame.draw.rect(surface, WALL_EDGE, (x, y, cs, cs), 2)


def draw_pellets(surface: pygame.Surface, pellets: PelletMap, config: GridConfig) -> None:
    cs = config.cell_size
    for (col, row), ptype in pellets.items():
        x, y = cell_to_pixel(col, row, cs)
        if ptype == HIGH_VALUE:
            r = cs // 4
            pygame.draw.circle(surface, PELLET_HIGH, (x, y), r)
        else:
            r = cs // 8
            pygame.draw.circle(surface, PELLET_LOW, (x, y), r)


def draw_gates(
    surface: pygame.Surface,
    gate_config: BlockGateConfig,
    gate_state: GateState,
    config: GridConfig,
) -> None:
    cs = config.cell_size
    for side, gate_row in [("left", gate_config.left_gate_row), ("right", gate_config.right_gate_row)]:
        col = 0 if side == "left" else config.cols - 1
        x, y = col * cs, gate_row * cs
        active = gate_state.active and gate_state.side == side and gate_state.gate_row == gate_row
        color = GATE_ACTIVE if active else GATE_COLOR
        pygame.draw.rect(surface, color, (x, y, cs, cs))
        pygame.draw.rect(surface, (80, 80, 100), (x, y, cs, cs), 2)


def draw_player(
    surface: pygame.Surface,
    player: Player,
    config: GridConfig,
    mouth_angle: float = 0.4,
) -> None:
    """Draw Pac-Man as a yellow circle with a wedge-shaped mouth facing the direction of movement."""
    x, y = cell_to_pixel(player.col, player.row, config.cell_size)
    r = config.cell_size // 2 - 2
    # Default mouth facing right (0°) if no direction
    if player.direction:
        dc, dr = player.direction
        # pygame: 0 = right, 90 = down. We want: right=0, down=90, left=180, up=270
        if dc == 1:
            base_angle = 0
        elif dc == -1:
            base_angle = 180
        elif dr == -1:
            base_angle = 270  # up
        else:
            base_angle = 90   # down
    else:
        base_angle = 0
    # Mouth: wedge from (base_angle - spread) to (base_angle + spread)
    # Screen y is down, so point at angle θ: (x + r*cos θ, y + r*sin θ)
    spread_deg = mouth_angle * 45
    spread_rad = math.radians(spread_deg)
    pygame.draw.circle(surface, PACMAN_YELLOW, (x, y), r)
    a1 = math.radians(base_angle) - spread_rad
    a2 = math.radians(base_angle) + spread_rad
    p1 = (x + r * math.cos(a1), y + r * math.sin(a1))
    p2 = (x + r * math.cos(a2), y + r * math.sin(a2))
    pygame.draw.polygon(surface, PACMAN_MOUTH, [(x, y), p1, p2])
    # Outline for visibility
    pygame.draw.circle(surface, (200, 200, 0), (x, y), r, 1)


# Classic Pac-Man ghost colors (red, pink, cyan, orange)
GHOST_COLORS = [
    (255, 0, 0),      # Blinky red
    (255, 182, 255),  # Pinky pink
    (0, 255, 255),    # Inky cyan
]
GHOST_EYE_WHITE = (255, 255, 255)
GHOST_PUPIL = (0, 0, 128)


def draw_ghosts(surface: pygame.Surface, ghosts: List[Ghost], config: GridConfig) -> None:
    """Draw classic Pac-Man-style ghosts: rounded body with wavy bottom, eyes with pupils."""
    cs = config.cell_size
    for g in ghosts:
        if g.removed:
            continue
        x, y = cell_to_pixel(g.col, g.row, cs)
        color = GHOST_COLORS[g.id % len(GHOST_COLORS)]
        w = cs * 0.85
        h = cs * 0.95
        left = x - w / 2
        top = y - h / 2
        # Body: rounded rectangle
        body_rect = pygame.Rect(left, top, w, h)
        pygame.draw.rect(surface, color, body_rect, border_radius=int(cs * 0.22))
        # Wavy bottom: 4 overlapping circles in body color to create classic ghost "feet"
        foot_r = cs * 0.14
        for i in range(4):
            fx = left + (i + 0.5) * (w / 4)
            fy = top + h
            pygame.draw.circle(surface, color, (int(fx), int(fy)), int(foot_r))
        # Eyes: two white ovals
        eye_w = cs * 0.2
        eye_h = cs * 0.26
        eye_y = top + h * 0.38
        left_eye_rect = pygame.Rect(x - cs * 0.26 - eye_w / 2, eye_y - eye_h / 2, eye_w, eye_h)
        right_eye_rect = pygame.Rect(x + cs * 0.06 - eye_w / 2, eye_y - eye_h / 2, eye_w, eye_h)
        pygame.draw.ellipse(surface, GHOST_EYE_WHITE, left_eye_rect)
        pygame.draw.ellipse(surface, GHOST_EYE_WHITE, right_eye_rect)
        # Pupils: offset in ghost direction
        pupil_off = cs * 0.09
        dc, dr = g.direction if g.direction != (0, 0) else (1, 0)
        px_off = dc * pupil_off
        py_off = dr * pupil_off
        pupil_r = max(2, int(cs * 0.07))
        pygame.draw.circle(surface, GHOST_PUPIL, (int(x - cs * 0.26 + px_off), int(eye_y + py_off)), pupil_r)
        pygame.draw.circle(surface, GHOST_PUPIL, (int(x + cs * 0.06 + px_off), int(eye_y + py_off)), pupil_r)
        # Thin outline
        pygame.draw.rect(surface, (180, 180, 200), body_rect, 1, border_radius=int(cs * 0.22))


def draw_quarantine_halo(surface: pygame.Surface, player: Player, config: GridConfig) -> None:
    """Draw a halo around Pac-Man when quarantined at the gate."""
    x, y = cell_to_pixel(player.col, player.row, config.cell_size)
    cs = config.cell_size
    # Outer glow (semi-transparent)
    halo_surf = pygame.Surface((cs * 2, cs * 2))
    halo_surf.set_colorkey((0, 0, 0))
    pygame.draw.circle(halo_surf, (255, 220, 100), (cs, cs), cs)
    halo_surf.set_alpha(70)
    surface.blit(halo_surf, (x - cs, y - cs))
    # Bright ring
    pygame.draw.circle(surface, (255, 255, 200), (x, y), int(cs * 0.7), 3)
    pygame.draw.circle(surface, (255, 240, 150), (x, y), int(cs * 0.6), 1)


def draw_quarantine_message(
    surface: pygame.Surface, font: pygame.font.Font, early_tap_count: int
) -> None:
    """When quarantined: show 'Press SPACE after 3s'; if early taps, show penalty."""
    line1 = font.render("Press SPACE after 3 seconds to unfreeze", True, TEXT_COLOR)
    r1 = line1.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2 + 40))
    surface.blit(line1, r1)
    if early_tap_count > 0:
        line2 = font.render(
            f"Premature press: +2s penalty ({early_tap_count} so far)",
            True,
            EARLY_TAP_MSG,
        )
        r2 = line2.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2 + 70))
        surface.blit(line2, r2)


def draw_instructions(surface: pygame.Surface, font: pygame.font.Font) -> None:
    surface.fill(BG)
    lines = [
        "Pac-Man style foraging task",
        "",
        "Use Arrow keys to move (one cell per keypress).",
        "Collect pellets. Avoid ghosts - if a ghost touches you, you lose a life.",
        "You have 3 lives. No lives left = game over for this block.",
        "Once in a while you will be quarantined (halo around you) at a gate.",
        "Wait at least 3 seconds, then press SPACE to unfreeze.",
        "A premature Space adds 2 seconds penalty each time.",
        "",
        "Press SPACE to start.",
    ]
    y = 80
    for line in lines:
        text = font.render(line, True, TEXT_COLOR)
        surface.blit(text, (80, y))
        y += 36
    pygame.display.flip()


def draw_end_screen(surface: pygame.Surface, font: pygame.font.Font, total_score: int, block_index: int, total_blocks: int) -> None:
    surface.fill(BG)
    title = font.render("Block complete", True, TEXT_COLOR)
    surface.blit(title, (surface.get_width() // 2 - title.get_width() // 2, 120))
    sc = font.render(f"Total score: {total_score}", True, PELLET_HIGH)
    surface.blit(sc, (surface.get_width() // 2 - sc.get_width() // 2, 200))
    if block_index < total_blocks - 1:
        inst = font.render("Press SPACE for next block", True, TEXT_COLOR)
    else:
        inst = font.render("Press SPACE to finish", True, TEXT_COLOR)
    surface.blit(inst, (surface.get_width() // 2 - inst.get_width() // 2, 280))
    pygame.display.flip()


def draw_blast(surface: pygame.Surface, center_x: int, center_y: int, progress: float, cell_size: int) -> None:
    """Draw one frame of an explosion/blast at (center_x, center_y). progress 0..1."""
    if progress >= 1.0:
        return
    # Expanding rings that fade: 4 rings at different radii and alphas
    max_r = cell_size * 1.8 * (0.3 + progress * 0.7)
    for i, (r_frac, alpha) in enumerate([
        (0.25, 220), (0.5, 180), (0.75, 120), (1.0, 60),
    ]):
        r = max_r * r_frac
        a = int(alpha * (1.0 - progress))
        if a <= 0 or r < 2:
            continue
        color = (255, 200, 80) if i < 2 else (255, 120, 40)
        s = pygame.Surface((int(r * 2.5), int(r * 2.5)))
        s.set_colorkey((0, 0, 0))
        pygame.draw.circle(s, color, (int(r * 1.25), int(r * 1.25)), int(r))
        s.set_alpha(a)
        surface.blit(s, (center_x - r * 1.25, center_y - r * 1.25))
    # Bright center (fades quickly)
    core_r = int(cell_size * 0.35 * (1.0 - progress))
    if core_r > 0:
        pygame.draw.circle(surface, (255, 255, 200), (center_x, center_y), core_r)
        pygame.draw.circle(surface, (255, 220, 100), (center_x, center_y), max(1, core_r - 2))


def draw_death_screen(surface: pygame.Surface, font: pygame.font.Font, lives_remaining: int) -> None:
    """Visual cue when Pac-Man dies: red flash and 'You died!' with lives left."""
    # Dark red overlay
    overlay = pygame.Surface(surface.get_size())
    overlay.fill((80, 0, 0))
    overlay.set_alpha(180)
    surface.blit(overlay, (0, 0))
    # Message
    title_font = pygame.font.Font(None, 56)
    msg = title_font.render("You died!", True, (255, 80, 80))
    r = msg.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2 - 40))
    surface.blit(msg, r)
    if lives_remaining > 0:
        sub = font.render(f"Lives left: {lives_remaining}", True, TEXT_COLOR)
    else:
        sub = font.render("No lives left!", True, (255, 100, 100))
    r2 = sub.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2 + 10))
    surface.blit(sub, r2)
    pygame.display.flip()


def draw_all_pellets_collected_screen(surface: pygame.Surface, font: pygame.font.Font, score: int) -> None:
    """Shown when all pellets are consumed; game over for this block with score."""
    surface.fill(BG)
    title = font.render("All pellets collected!", True, PELLET_HIGH)
    surface.blit(title, (surface.get_width() // 2 - title.get_width() // 2, 100))
    sub = font.render("Game over", True, TEXT_COLOR)
    surface.blit(sub, (surface.get_width() // 2 - sub.get_width() // 2, 150))
    sc = font.render(f"Score: {score}", True, PELLET_HIGH)
    surface.blit(sc, (surface.get_width() // 2 - sc.get_width() // 2, 220))
    inst = font.render("Press SPACE to continue", True, TEXT_COLOR)
    surface.blit(inst, (surface.get_width() // 2 - inst.get_width() // 2, 300))
    pygame.display.flip()


def draw_game_over_screen(surface: pygame.Surface, font: pygame.font.Font, score: int) -> None:
    surface.fill(BG)
    title = font.render("Session complete", True, TEXT_COLOR)
    surface.blit(title, (surface.get_width() // 2 - title.get_width() // 2, 120))
    sc = font.render(f"Total score: {score}", True, PELLET_HIGH)
    surface.blit(sc, (surface.get_width() // 2 - sc.get_width() // 2, 200))
    inst = font.render("Close window to exit", True, TEXT_COLOR)
    surface.blit(inst, (surface.get_width() // 2 - inst.get_width() // 2, 280))
    pygame.display.flip()
