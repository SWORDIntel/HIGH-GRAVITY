#!/bin/bash
# Stop Khoj Server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$REPO_ROOT/data/khoj.pid"

echo "[*] Stopping Khoj server..."

if [ ! -f "$PID_FILE" ]; then
    echo "[!] PID file not found. Khoj may not be running."
    pkill -f "khoj.*--port.*42110" && echo "[✓] Killed orphaned Khoj process" || echo "[!] No Khoj process found"
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "[✓] Sent TERM signal to Khoj (PID: $PID)"
    
    # Wait for graceful shutdown
    for i in {1..10}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            echo "[✓] Khoj stopped"
            rm -f "$PID_FILE"
            exit 0
        fi
        sleep 1
    done
    
    # Force kill if still running
    kill -9 "$PID" 2>/dev/null
    echo "[✓] Khoj force-stopped"
else
    echo "[!] Khoj process (PID: $PID) not found"
fi

rm -f "$PID_FILE"
