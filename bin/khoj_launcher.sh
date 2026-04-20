#!/bin/bash
# Khoj Server Launcher for HIGH-GRAVITY
# Starts Khoj with proper environment and configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
KHOJ_DIR="$REPO_ROOT/khoj"
DATA_DIR="$REPO_ROOT/data/khoj"
LOG_FILE="$REPO_ROOT/logs/khoj.log"
PID_FILE="$REPO_ROOT/data/khoj.pid"

# Load environment if exists
if [ -f "$REPO_ROOT/config/khoj.env" ]; then
    source "$REPO_ROOT/config/khoj.env"
fi

# Default configuration
KHOJ_HOST="${HG_KHOJ_HOST:-127.0.0.1}"
KHOJ_PORT="${HG_KHOJ_PORT:-42110}"
KHOJ_ADMIN_EMAIL="${HG_KHOJ_ADMIN_EMAIL:-admin@highgravity.local}"
KHOJ_ADMIN_PASSWORD="${HG_KHOJ_ADMIN_PASSWORD:-highgravity2026}"

echo "[*] HIGH-GRAVITY Khoj Integration Launcher"
echo "[*] Khoj Directory: $KHOJ_DIR"
echo "[*] Data Directory: $DATA_DIR"

# Check if Khoj directory exists
if [ ! -d "$KHOJ_DIR" ]; then
    echo "[!] Khoj directory not found at $KHOJ_DIR"
    echo "[!] Please clone Khoj: git clone https://github.com/khoj-ai/khoj.git"
    exit 1
fi

# Create data directory
mkdir -p "$DATA_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[!] Khoj already running (PID: $OLD_PID)"
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

# Export environment variables
export KHOJ_ADMIN_EMAIL="$KHOJ_ADMIN_EMAIL"
export KHOJ_ADMIN_PASSWORD="$KHOJ_ADMIN_PASSWORD"

# Use embedded PostgreSQL (pgserver)
export USE_EMBEDDED_DB="true"
export PGSERVER_DATA_DIR="$DATA_DIR/pgserver"
export POSTGRES_DB="khoj"

cd "$KHOJ_DIR"

# Check for uv (faster) or fall back to pip
if command -v uv &> /dev/null; then
    echo "[*] Using uv for dependency management"
    RUN_CMD="uv run"
else
    echo "[*] Using pip/venv for dependency management"
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install -q -e .
    RUN_CMD="python3 -m"
fi

echo "[*] Starting Khoj server on $KHOJ_HOST:$KHOJ_PORT"

# Start Khoj in background
$RUN_CMD khoj --host "$KHOJ_HOST" --port "$KHOJ_PORT" --anonymous-mode > "$LOG_FILE" 2>&1 &
KHOJ_PID=$!

echo "$KHOJ_PID" > "$PID_FILE"
echo "[✓] Khoj started (PID: $KHOJ_PID)"

# Wait for Khoj to be ready
echo "[*] Waiting for Khoj to be ready..."
for i in {1..30}; do
    if curl -s "http://$KHOJ_HOST:$KHOJ_PORT/api/health" > /dev/null 2>&1; then
        echo "[✓] Khoj is ready!"
        echo "[*] Access Khoj at: http://$KHOJ_HOST:$KHOJ_PORT"
        echo "[*] Logs: $LOG_FILE"
        exit 0
    fi
    sleep 1
done

echo "[!] Khoj failed to start within 30 seconds"
echo "[*] Check logs: $LOG_FILE"
exit 1
