"""
Entry point: load config, run instructions, blocks, end screen, save logs.
"""
import argparse
import json
import os
import pygame

from game.grid import GridConfig
from game.gates import BlockGateConfig
from game.game_loop import run_block, run_instructions
from game.render import draw_end_screen, draw_game_over_screen
from game.logger import ExperimentLogger


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiment_config.json", help="Path to experiment config JSON")
    parser.add_argument("--log-dir", default="logs", help="Directory for session log files")
    args = parser.parse_args()

    config_path = args.config
    if not os.path.exists(config_path):
        print(f"Config not found: {config_path}")
        return
    cfg = load_config(config_path)

    blocks_cfg = cfg.get("blocks", [
        {"left_gate_row": 1, "right_gate_row": 12},
        {"left_gate_row": 6, "right_gate_row": 7},
    ])
    teleport_interval = float(cfg.get("teleport_interval_sec", 75))
    teleports_per_block = int(cfg.get("teleports_per_block", 2))
    cell_size = int(cfg.get("cell_size", 40))
    practice = cfg.get("practice_block", False)

    grid_config = GridConfig(cell_size=cell_size)
    pygame.init()
    screen = pygame.display.set_mode((grid_config.width_px, grid_config.height_px))
    pygame.display.set_caption("Time Game - Foraging Task")
    font = pygame.font.Font(None, 28)
    font_big = pygame.font.Font(None, 42)

    logger = ExperimentLogger(log_dir=args.log_dir)
    logger.start_session()

    # Instructions
    run_instructions(screen, font_big)

    # Optional practice block (same as block 0 config)
    if practice:
        bc = BlockGateConfig(
            left_gate_row=blocks_cfg[0]["left_gate_row"],
            right_gate_row=blocks_cfg[0]["right_gate_row"],
        )
        _, user_quit = run_block(
            screen, font, grid_config, bc, block_id=-1, logger=logger,
            teleport_interval_sec=teleport_interval,
            teleports_per_block=teleports_per_block,
        )
        if user_quit:
            logger.end_session()
            pygame.quit()
            return
        draw_end_screen(screen, font_big, 0, 0, 1)
        while True:
            ev = pygame.event.wait()
            if ev.type == pygame.QUIT:
                break
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
                break

    total_score = 0
    for i, b in enumerate(blocks_cfg):
        block_config = BlockGateConfig(
            left_gate_row=b["left_gate_row"],
            right_gate_row=b["right_gate_row"],
        )
        score, user_quit = run_block(
            screen, font, grid_config, block_config, block_id=i, logger=logger,
            teleport_interval_sec=teleport_interval,
            teleports_per_block=teleports_per_block,
        )
        total_score += score
        if user_quit:
            break
        if i < len(blocks_cfg) - 1:
            draw_end_screen(screen, font_big, total_score, i + 1, len(blocks_cfg))
            while True:
                ev = pygame.event.wait()
                if ev.type == pygame.QUIT:
                    break
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
                    break

    log_path = logger.end_session()
    print(f"Session log saved to {log_path}")

    draw_game_over_screen(screen, font_big, total_score)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
        pygame.time.wait(100)


if __name__ == "__main__":
    main()
