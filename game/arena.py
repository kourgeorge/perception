"""
Arena: hot zone geometry and pellet placement (dense in zones, sparse elsewhere).
"""
import random
from typing import List, Tuple

from game.grid import (
    COLS,
    ROWS,
    get_cold_zone_cells,
    get_hot_zone_cells,
    is_hot_zone,
)


# Pellet types
HIGH_VALUE = "high"
LOW_VALUE = "low"

# Points
POINTS_HIGH = 10
POINTS_LOW = 1

# Density: hot zones get pellet in every cell (dense); cold zone gets a subset (sparse)
# For cold zone, use a fraction of cells, e.g. 1/3
COLD_ZONE_PELLET_FRACTION = 0.35


def build_pellet_cells(seed: int | None = None) -> List[Tuple[Tuple[int, int], str]]:
    """
    Returns a list of ((col, row), pellet_type).
    Hot zones: dense (every cell gets high-value).
    Cold zone: sparse (random subset gets low-value).
    """
    rng = random.Random(seed)
    result: List[Tuple[Tuple[int, int], str]] = []

    for (col, row) in get_hot_zone_cells(COLS, ROWS):
        result.append(((col, row), HIGH_VALUE))

    cold = get_cold_zone_cells(COLS, ROWS)
    n_cold = max(1, int(len(cold) * COLD_ZONE_PELLET_FRACTION))
    chosen = rng.sample(cold, n_cold)
    for (col, row) in chosen:
        result.append(((col, row), LOW_VALUE))

    return result
