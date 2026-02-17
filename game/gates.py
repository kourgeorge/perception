"""
Gate positions per block, teleport, 3s/5s timer, exit key, ghost clearing.
"""
from dataclasses import dataclass
from typing import Callable, List, Literal, Optional, Tuple

from game.grid import COLS, ROWS
from game.entities import Player
from game.ghosts import clear_ghosts_near_gate

GateSide = Literal["left", "right"]

MIN_WAIT_SEC = 3.0
PENALTY_PER_EARLY_TAP_SEC = 2.0
MAX_WAIT_SEC = 12.0  # cap so player is never stuck forever
GATE_CLEAR_RADIUS = 1  # cells


@dataclass
class BlockGateConfig:
    left_gate_row: int
    right_gate_row: int


def gate_cell(side: GateSide, gate_row: int) -> Tuple[int, int]:
    if side == "left":
        return (0, gate_row)
    return (COLS - 1, gate_row)


@dataclass
class GateState:
    active: bool = False
    side: Optional[GateSide] = None
    gate_row: Optional[int] = None
    enter_time: float = 0.0
    early_tap_count: int = 0  # each premature Space adds 2s penalty
    exited_by_key: bool = False
    return_col: int = 0
    return_row: int = 0

    def reset(self) -> None:
        self.active = False
        self.side = None
        self.gate_row = None
        self.enter_time = 0.0
        self.early_tap_count = 0
        self.exited_by_key = False
        self.return_col = 0
        self.return_row = 0

    def required_wait_sec(self) -> float:
        """Seconds that must pass before Space can unfreeze (3 + 2 per early tap)."""
        return MIN_WAIT_SEC + PENALTY_PER_EARLY_TAP_SEC * self.early_tap_count


def enter_gate(
    player: Player,
    state: GateState,
    config: BlockGateConfig,
    side: GateSide,
    now: float,
) -> None:
    """Teleport player to gate and lock. Save return position."""
    state.active = True
    state.side = side
    state.gate_row = config.left_gate_row if side == "left" else config.right_gate_row
    state.enter_time = now
    state.early_tap_count = 0
    state.exited_by_key = False
    state.return_col = player.col
    state.return_row = player.row
    col, row = gate_cell(side, state.gate_row)
    player.set_cell(col, row)
    player.direction = None
    player.frozen = True


def update_gate(
    state: GateState,
    player: Player,
    ghosts: List,
    now: float,
    exit_key_pressed: bool,
    on_exit: Callable[[float, int, bool], None],
) -> bool:
    """
    Update gate state. Unfreeze with Space after 3s (or 3 + 2*early_taps).
    Premature Space adds 2s penalty each time.
    Returns True if we just exited.
    """
    if not state.active:
        return False
    elapsed = now - state.enter_time
    required = min(state.required_wait_sec(), MAX_WAIT_SEC)
    if exit_key_pressed:
        if elapsed >= required:
            state.exited_by_key = True
            state.active = False
            player.frozen = False
            player.set_cell(state.return_col, state.return_row)
            on_exit(now, state.early_tap_count, True)
            return True
        else:
            state.early_tap_count += 1
    if elapsed >= MAX_WAIT_SEC:
        state.active = False
        player.frozen = False
        player.set_cell(state.return_col, state.return_row)
        on_exit(now, state.early_tap_count, False)
        return True
    return False


def clear_ghosts_at_gate(state: GateState, ghosts: List) -> None:
    """Clear ghosts near the gate after exit. Call after update_gate returned True."""
    if state.side is None or state.gate_row is None:
        return
    col, row = gate_cell(state.side, state.gate_row)
    clear_ghosts_near_gate(ghosts, col, row, GATE_CLEAR_RADIUS)
