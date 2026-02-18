#!/usr/bin/env bash
# Start the Phaser server on port 8080 (Ubuntu / Linux)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASER_DIR="$SCRIPT_DIR/phaser"
PID_FILE="$SCRIPT_DIR/.phaser-server.pid"
LOG_FILE="$SCRIPT_DIR/phaser-server.log"
PORT=8080

# Already running?
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "Phaser server is already running (PID $PID). Stop it first with ./stop-server.sh"
    exit 1
  fi
  rm -f "$PID_FILE"
fi

# Port in use by something else?
if command -v lsof &>/dev/null && lsof -Pi ":$PORT" -sTCP:LISTEN -t &>/dev/null; then
  echo "Port $PORT is already in use. Stop the process using it or use ./stop-server.sh"
  exit 1
fi

cd "$PHASER_DIR"
nohup python3 -m http.server "$PORT" > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Phaser server started on http://localhost:$PORT (PID $(cat "$PID_FILE"))"
echo "Log: $LOG_FILE"
