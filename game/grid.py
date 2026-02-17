"""
Grid: 20×14 cells, cell–pixel conversion, walls (Pac-Man-style maze), and hot-zone definitions.
"""
from dataclasses import dataclass
from typing import FrozenSet, Set, Tuple

# Grid dimensions (cols, rows)
COLS = 20
ROWS = 14

# Playable area: boundary walls at row 0, row 13, col 0, col 19. Gates at (0, left_gate_row) and (19, right_gate_row).
PLAYABLE_COL_MIN = 1
PLAYABLE_COL_MAX = 18
PLAYABLE_ROW_MIN = 1
PLAYABLE_ROW_MAX = 12

# Default cell size in pixels
DEFAULT_CELL_SIZE = 40

# Pac-Man-style maze: internal walls within playable area (cols 1-18, rows 1-12).
# Each string is one row (row 1 to 12); each char is one col (1 to 18). '#' = wall.
_MAZE_ROWS = [
    "  ###    ###      ",   # row 1
    "  #  #   #  #  #  ",
    "  #      #     #  ",
    "    ######  ###   ",
    "  #    #    #  #  ",
    "  #  #    #    #  ",   # row 6
    "  #    #  #  #    ",
    "    ###  ######   ",
    "  #  #      #  #  ",
    "  #     #     #   ",
    "  #  #   #  #  #  ",
    "  ###      ###    ",   # row 12
]


def _build_maze_walls() -> FrozenSet[Tuple[int, int]]:
    out: Set[Tuple[int, int]] = set()
    for r, line in enumerate(_MAZE_ROWS):
        row = r + PLAYABLE_ROW_MIN
        for c, ch in enumerate(line):
            if ch == "#":
                col = c + PLAYABLE_COL_MIN
                out.add((col, row))
    return frozenset(out)


MAZE_WALLS: FrozenSet[Tuple[int, int]] = _build_maze_walls()


@dataclass
class GridConfig:
    cols: int = COLS
    rows: int = ROWS
    cell_size: int = DEFAULT_CELL_SIZE

    @property
    def width_px(self) -> int:
        return self.cols * self.cell_size

    @property
    def height_px(self) -> int:
        return self.rows * self.cell_size


def cell_to_pixel(col: int, row: int, cell_size: int = DEFAULT_CELL_SIZE) -> Tuple[int, int]:
    """Convert grid (col, row) to pixel (x, y) of cell center."""
    x = col * cell_size + cell_size // 2
    y = row * cell_size + cell_size // 2
    return (x, y)


def pixel_to_cell(x: int, y: int, cell_size: int = DEFAULT_CELL_SIZE) -> Tuple[int, int]:
    """Convert pixel (x, y) to grid (col, row)."""
    col = x // cell_size
    row = y // cell_size
    return (col, row)


def is_wall(col: int, row: int, cols: int = COLS, rows: int = ROWS) -> bool:
    """True if (col, row) is a boundary wall, a gate column (0 or 19), or an internal maze wall."""
    if col < 0 or col >= cols or row < 0 or row >= rows:
        return True
    # Boundary: top and bottom rows
    if row < PLAYABLE_ROW_MIN or row > PLAYABLE_ROW_MAX:
        return True
    # Left and right columns are walls (gates drawn separately; player only reaches them by teleport)
    if col < PLAYABLE_COL_MIN or col > PLAYABLE_COL_MAX:
        return True
    return (col, row) in MAZE_WALLS


def in_bounds(col: int, row: int, cols: int = COLS, rows: int = ROWS) -> bool:
    """True if (col, row) is inside the full grid (including gate cells)."""
    return 0 <= col < cols and 0 <= row < rows


def is_playable_cell(col: int, row: int) -> bool:
    """True if (col, row) is in the playable area and not a wall (for pellets, spawns)."""
    if not (PLAYABLE_COL_MIN <= col <= PLAYABLE_COL_MAX and PLAYABLE_ROW_MIN <= row <= PLAYABLE_ROW_MAX):
        return False
    return (col, row) not in MAZE_WALLS


# --- Hot zones (grid coordinates, within playable area) ---
# Top stripe: first two playable rows
TOP_STRIPE_ROWS = (1, 2)

# Bottom stripe: last two playable rows
BOTTOM_STRIPE_ROWS = (11, 12)

# Central disk: center (10, 7); 5×5 region (cols 8–12, rows 5–9)
CENTER_COL = 10
CENTER_ROW = 7
DISK_RADIUS_COLS = 2
DISK_RADIUS_ROWS = 2


def in_top_stripe(row: int) -> bool:
    return row in TOP_STRIPE_ROWS


def in_bottom_stripe(row: int) -> bool:
    return row in BOTTOM_STRIPE_ROWS


def in_central_disk(col: int, row: int) -> bool:
    return (
        abs(col - CENTER_COL) <= DISK_RADIUS_COLS
        and abs(row - CENTER_ROW) <= DISK_RADIUS_ROWS
    )


def is_hot_zone(col: int, row: int) -> bool:
    """True if (col, row) is in any hot zone."""
    return in_top_stripe(row) or in_bottom_stripe(row) or in_central_disk(col, row)


def get_hot_zone_cells(cols: int = COLS, rows: int = ROWS) -> list:
    """Return list of (col, row) for every playable cell in hot zones."""
    out = []
    for c in range(cols):
        for r in range(rows):
            if is_hot_zone(c, r) and is_playable_cell(c, r):
                out.append((c, r))
    return out


def get_cold_zone_cells(cols: int = COLS, rows: int = ROWS) -> list:
    """Return list of (col, row) for every playable cell not in hot zones."""
    out = []
    for c in range(cols):
        for r in range(rows):
            if not is_hot_zone(c, r) and is_playable_cell(c, r):
                out.append((c, r))
    return out


def get_playable_cells() -> list:
    """Return list of all (col, row) that are playable (no wall)."""
    out = []
    for c in range(PLAYABLE_COL_MIN, PLAYABLE_COL_MAX + 1):
        for r in range(PLAYABLE_ROW_MIN, PLAYABLE_ROW_MAX + 1):
            if (c, r) not in MAZE_WALLS:
                out.append((c, r))
    return out
