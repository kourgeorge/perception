"""
Entities: Player, Ghost, Pellet (position, state, collision).
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from game.grid import COLS, ROWS, in_bounds, is_wall
from game.arena import HIGH_VALUE, LOW_VALUE, POINTS_HIGH, POINTS_LOW


@dataclass
class Player:
    col: int
    row: int
    direction: Optional[Tuple[int, int]] = None  # (dc, dr) or None
    frozen: bool = False  # True when at gate
    score: int = 0
    lives: int = 3
    invincible_until: float = 0  # time (perf_counter) until which ghost contact is ignored (after respawn)

    def cell(self) -> Tuple[int, int]:
        return (self.col, self.row)

    def set_cell(self, col: int, row: int) -> None:
        self.col = col
        self.row = row

    def can_move_to(self, col: int, row: int) -> bool:
        if is_wall(col, row):
            return False
        return in_bounds(col, row)


@dataclass
class Ghost:
    id: int
    col: int
    row: int
    direction: Tuple[int, int] = (0, 0)  # (dc, dr)
    removed: bool = False  # True when cleared at gate

    def cell(self) -> Tuple[int, int]:
        return (self.col, self.row)


# Pellets: map (col, row) -> type
PelletMap = Dict[Tuple[int, int], str]


def pellet_points(pellet_type: str) -> int:
    return POINTS_HIGH if pellet_type == HIGH_VALUE else POINTS_LOW


def make_pellet_map(pellet_cells: List[Tuple[Tuple[int, int], str]]) -> PelletMap:
    return {cell: ptype for cell, ptype in pellet_cells}
