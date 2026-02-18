#!/usr/bin/env bash
# Stop the Phaser server on port 8080 (Ubuntu / Linux)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.phaser-server.pid"
PORT=8080

stop_by_pid_file() {
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
      kill "$PID" 2>/dev/null || true
      echo "Stopped Phaser server (PID $PID)"
    fi
    rm -f "$PID_FILE"
    return 0
  fi
  return 1
}

stop_by_port() {
  if command -v lsof &>/dev/null; then
    PIDS=$(lsof -ti ":$PORT" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
      echo "$PIDS" | xargs -r kill 2>/dev/null || true
      echo "Stopped process(es) on port $PORT"
      return 0
    fi
  fi
  if command -v fuser &>/dev/null; then
    if fuser -k "$PORT/tcp" 2>/dev/null; then
      echo "Stopped process(es) on port $PORT"
      return 0
    fi
  fi
  return 1
}

if stop_by_pid_file; then
  exit 0
fi

if stop_by_port; then
  exit 0
fi

echo "No Phaser server found running on port $PORT"
