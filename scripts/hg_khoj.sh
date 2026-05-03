#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

cmd="${1:-status}"

case "$cmd" in
  start)
    echo "[*] Starting Khoj..."
    bash scripts/khoj_docker.sh
    ;;
  stop)
    echo "[*] Stopping Khoj..."
    docker stop khoj khoj-pg >/dev/null 2>&1 || true
    echo "[+] Khoj stop signal sent."
    ;;
  status)
    curl -s http://127.0.0.1:9999/hg/khoj/status | jq .
    ;;
  reindex)
    curl -s -X POST http://127.0.0.1:9999/hg/khoj/reindex | jq .
    ;;
  logs)
    tail -n 120 logs/khoj_docker.log 2>/dev/null || echo "No khoj log file yet."
    ;;
  *)
    echo "Usage: ./hg_khoj.sh {start|stop|status|reindex|logs}"
    exit 1
    ;;
esac

