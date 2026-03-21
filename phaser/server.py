#!/usr/bin/env python3
"""
Serve the Phaser client and persist gameplay events on the server.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


SQLITE_COLUMNS = [
    "event_id",
    "session_id",
    "event_seq",
    "event_type",
    "event_ts",
    "received_at",
    "player_name",
    "level_index",
    "score_total",
    "lives_left",
    "context_id",
    "entity_type",
    "entity_id",
    "x",
    "y",
    "client_ip",
    "user_agent",
    "payload_json",
]

CSV_COLUMNS = SQLITE_COLUMNS


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_bool_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return 1 if value else 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return 1
        if lowered in {"0", "false", "no", "n"}:
            return 0
    return None


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


KNOWN_EVENT_KEYS = {
    "event_id",
    "session_id",
    "event_seq",
    "event_type",
    "event",
    "event_ts",
    "timestamp_iso",
    "received_at",
    "player_name",
    "level_index",
    "score_total",
    "total_score",
    "lives_left",
    "context_id",
    "entity_type",
    "entity_id",
    "x",
    "y",
    "col",
    "row",
    "payload",
}


class EventStore:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.sqlite_path = log_dir / "phaser_events.sqlite"
        self.csv_path = log_dir / "phaser_events.csv"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS game_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                session_id TEXT,
                event_seq INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_ts TEXT NOT NULL,
                received_at TEXT NOT NULL,
                player_name TEXT,
                level_index INTEGER,
                lives_left INTEGER,
                score_total INTEGER,
                context_id TEXT,
                entity_type TEXT,
                entity_id TEXT,
                x INTEGER,
                y INTEGER,
                client_ip TEXT,
                user_agent TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_game_events_session_id ON game_events(session_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_game_events_event_type ON game_events(event_type)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_game_events_context_id ON game_events(context_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_game_events_event_ts ON game_events(event_ts)"
        )
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_game_events_session_seq ON game_events(session_id, event_seq)"
        )
        self._conn.commit()

    def write_events(
        self,
        events: list[dict[str, Any]],
        *,
        client_ip: str | None,
        user_agent: str | None,
    ) -> int:
        rows = [
            self._normalize_event(
                event,
                client_ip=client_ip,
                user_agent=user_agent,
            )
            for event in events
            if isinstance(event, dict)
        ]
        if not rows:
            return 0

        inserted_rows: list[dict[str, Any]] = []
        with self._lock:
            cursor = self._conn.cursor()
            for row in rows:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO game_events (
                        event_id,
                        session_id,
                        event_seq,
                        event_type,
                        event_ts,
                        received_at,
                        player_name,
                        level_index,
                        lives_left,
                        score_total,
                        context_id,
                        entity_type,
                        entity_id,
                        x,
                        y,
                        client_ip,
                        user_agent,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(row[column] for column in SQLITE_COLUMNS),
                )
                if cursor.rowcount == 1:
                    inserted_rows.append(row)
            self._conn.commit()
            self._append_csv(inserted_rows)
        return len(inserted_rows)

    def _append_csv(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        expected_header = ",".join(CSV_COLUMNS)
        write_mode = "a"
        write_header = not self.csv_path.exists() or self.csv_path.stat().st_size == 0
        if not write_header:
            with self.csv_path.open("r", encoding="utf-8") as handle:
                existing_header = handle.readline().strip()
            if existing_header != expected_header:
                write_mode = "w"
                write_header = True

        with self.csv_path.open(write_mode, newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            if write_header:
                writer.writeheader()
            for row in rows:
                writer.writerow({column: row.get(column) for column in CSV_COLUMNS})

    def _normalize_event(
        self,
        event: dict[str, Any],
        *,
        client_ip: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        event_id = str(event.get("event_id") or uuid.uuid4())
        event_seq = as_int(event.get("event_seq"))
        if event_seq is None:
            event_seq = 0
        received_at = utc_now_iso()
        payload = event.get("payload")
        if not isinstance(payload, dict):
            payload = {
                key: value
                for key, value in event.items()
                if key not in KNOWN_EVENT_KEYS
            }
        payload_json = json_dumps(payload)
        return {
            "event_id": event_id,
            "session_id": event.get("session_id"),
            "event_seq": event_seq,
            "event_type": str(event.get("event_type") or event.get("event") or "unknown"),
            "event_ts": first_non_empty(event.get("event_ts"), event.get("timestamp_iso"), received_at),
            "received_at": received_at,
            "player_name": event.get("player_name"),
            "level_index": as_int(event.get("level_index")),
            "score_total": as_int(first_non_empty(event.get("score_total"), event.get("total_score"))),
            "lives_left": as_int(event.get("lives_left")),
            "context_id": event.get("context_id"),
            "entity_type": event.get("entity_type"),
            "entity_id": event.get("entity_id"),
            "x": as_int(first_non_empty(event.get("x"), event.get("col"))),
            "y": as_int(first_non_empty(event.get("y"), event.get("row"))),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "payload_json": payload_json,
        }

    def count_events(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS count FROM game_events").fetchone()
        return int(row["count"])


class PhaserRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str, store: EventStore, **kwargs: Any):
        self.store = store
        super().__init__(*args, directory=directory, **kwargs)

    def end_headers(self) -> None:
        if self.path == "/" or self.path.endswith(".html") or self.path.endswith(".js"):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        if self.path.startswith("/api/"):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        if self.path.startswith("/api/"):
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_GET(self) -> None:
        if self.path == "/api/logs/health":
            self._write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "event_count": self.store.count_events(),
                    "sqlite_path": str(self.store.sqlite_path),
                    "csv_path": str(self.store.csv_path),
                },
            )
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/logs/events":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid Content-Length"})
            return

        if content_length <= 0:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Request body is required"})
            return

        try:
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Body must be valid JSON"})
            return

        if isinstance(payload, dict) and isinstance(payload.get("events"), list):
            events = payload["events"]
        elif isinstance(payload, dict):
            events = [payload]
        elif isinstance(payload, list):
            events = payload
        else:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Unsupported JSON payload"})
            return

        stored = self.store.write_events(
            events,
            client_ip=self.client_address[0] if self.client_address else None,
            user_agent=self.headers.get("User-Agent"),
        )
        self._write_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "received": len(events),
                "stored": stored,
            },
        )

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    parser = argparse.ArgumentParser(description="Serve Phaser and persist server-side logs.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8081, type=int)
    parser.add_argument("--log-dir", default=str(project_dir / "logs"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    phaser_dir = Path(__file__).resolve().parent
    store = EventStore(Path(args.log_dir).resolve())

    def handler_factory(*handler_args: Any, **handler_kwargs: Any) -> PhaserRequestHandler:
        return PhaserRequestHandler(
            *handler_args,
            directory=str(phaser_dir),
            store=store,
            **handler_kwargs,
        )

    server = ThreadingHTTPServer((args.host, args.port), handler_factory)
    print(f"Serving Phaser on http://{args.host}:{args.port}")
    print(f"SQLite log: {store.sqlite_path}")
    print(f"CSV log: {store.csv_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
