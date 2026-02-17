"""
Experiment data logging: session, block, gate, pellet, ghost, keypress events.
"""
import json
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List


def _ts() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _time_sec() -> float:
    return time.perf_counter()


class ExperimentLogger:
    def __init__(self, log_dir: str = "logs", session_id: str | None = None):
        self.log_dir = log_dir
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.session_start_sec: float | None = None
        self.events: List[Dict[str, Any]] = []
        self.keypresses: List[Dict[str, Any]] = []
        os.makedirs(log_dir, exist_ok=True)

    def start_session(self) -> None:
        self.session_start_sec = _time_sec()
        self.events.append({
            "event": "session_start",
            "session_id": self.session_id,
            "timestamp_iso": _ts(),
            "timestamp_sec": self.session_start_sec,
               })

    def log_block_start(self, block_id: int, left_gate_row: int, right_gate_row: int) -> None:
        t = _time_sec()
        self.events.append({
            "event": "block_start",
            "block_id": block_id,
            "left_gate_row": left_gate_row,
            "right_gate_row": right_gate_row,
            "timestamp_sec": t,
            "timestamp_iso": _ts(),
        })

    def log_block_end(self, block_id: int) -> None:
        t = _time_sec()
        self.events.append({
            "event": "block_end",
            "block_id": block_id,
            "timestamp_sec": t,
            "timestamp_iso": _ts(),
        })

    def log_teleport(self, gate_side: str, gate_row: int, player_col: int, player_row: int) -> None:
        t = _time_sec()
        self.events.append({
            "event": "teleport",
            "t_teleport_sec": t,
            "gate_side": gate_side,
            "gate_row": gate_row,
            "player_cell_before": (player_col, player_row),
            "timestamp_iso": _ts(),
        })

    def log_gate_exit(self, duration_at_gate_sec: float, early_tap_count: int, exited_by_key: bool) -> None:
        t = _time_sec()
        self.events.append({
            "event": "gate_exit",
            "t_exit_sec": t,
            "duration_at_gate_sec": duration_at_gate_sec,
            "early_tap_count": early_tap_count,
            "exited_by_key": exited_by_key,
            "timestamp_iso": _ts(),
        })

    def log_pellet(self, col: int, row: int, pellet_type: str, points: int, total_score: int) -> None:
        t = _time_sec()
        self.events.append({
            "event": "pellet",
            "t_sec": t,
            "cell": (col, row),
            "pellet_type": pellet_type,
            "points": points,
            "total_score": total_score,
            "timestamp_iso": _ts(),
        })

    def log_ghost_contact(self, ghost_id: int) -> None:
        t = _time_sec()
        self.events.append({
            "event": "ghost_contact",
            "t_sec": t,
            "ghost_id": ghost_id,
            "timestamp_iso": _ts(),
        })

    def log_key(self, key_name: str) -> None:
        t = _time_sec()
        self.keypresses.append({
            "key": key_name,
            "timestamp_sec": t,
            "timestamp_iso": _ts(),
        })

    def end_session(self) -> str:
        t = _time_sec()
        self.events.append({
            "event": "session_end",
            "timestamp_sec": t,
            "timestamp_iso": _ts(),
        })
        path = os.path.join(
            self.log_dir,
            f"session_{self.session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
        )
        data = {
            "session_id": self.session_id,
            "events": self.events,
            "keypresses": self.keypresses,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path
