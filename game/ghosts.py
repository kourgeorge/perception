"""
Ghost movement AI and collision with player. Mild aversive roaming.
"""
import random
from typing import List, Tuple

from game.grid import COLS, ROWS, in_bounds, is_wall
from game.entities import Ghost, Player


DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # up, down, left, right


def move_ghosts(ghosts: List[Ghost], walls_only: bool = True) -> None:
    """
    Update ghost positions: random direction changes with some persistence.
    ghosts are modified in place. Only consider walls (no player chasing for mild aversive).
    """
    for g in ghosts:
        if g.removed:
            continue
        # With probability 0.3 turn to a new random direction; else keep current
        if g.direction == (0, 0) or random.random() < 0.3:
            g.direction = random.choice(DIRS)
        nc, nr = g.col + g.direction[0], g.row + g.direction[1]
        if is_wall(nc, nr):
            g.direction = random.choice(DIRS)
            nc, nr = g.col + g.direction[0], g.row + g.direction[1]
        if in_bounds(nc, nr):
            g.col, g.row = nc, nr


def check_ghost_player_collision(ghosts: List[Ghost], player: Player) -> List[int]:
    """Return list of ghost ids that overlap the player (same cell)."""
    hit = []
    for g in ghosts:
        if g.removed:
            continue
        if g.col == player.col and g.row == player.row:
            hit.append(g.id)
    return hit


def clear_ghosts_near_gate(ghosts: List[Ghost], gate_col: int, gate_row: int, radius: int = 1) -> None:
    """Mark ghosts within manhattan radius of (gate_col, gate_row) as removed."""
    for g in ghosts:
        if g.removed:
            continue
        if abs(g.col - gate_col) + abs(g.row - gate_row) <= radius:
            g.removed = True
