#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

cmd="${1:-status}"

case "$cmd" in
  start)
    echo "[*] Starting Khoj..."
    bash scripts/internal/khoj_docker.sh
    ;;
  stop)
    echo "[*] Stopping Khoj..."
    docker stop khoj khoj-pg >/dev/null 2>&1 || true
    echo "[+] Khoj stop signal sent."
    ;;
  status)
    curl -s http://127.0.0.1:9998/hg/khoj/status | jq .
    ;;
  reindex)
    curl -s -X POST http://127.0.0.1:9998/hg/khoj/reindex | jq .
    ;;
  accel|probe)
    mkdir -p logs
    runtime_tmp="$(mktemp)"
    if docker ps --format '{{.Names}}' | grep -qx khoj; then
      if docker exec -i khoj python3 - < scripts/internal/khoj_accel_runtime_probe.py > "$runtime_tmp" 2>/dev/null; then
        :
      else
        echo '{"error":"docker_exec_failed"}' > "$runtime_tmp"
      fi
    else
      echo '{"error":"khoj_container_not_running"}' > "$runtime_tmp"
    fi
    status_tmp="$(mktemp)"
    python3 scripts/internal/khoj_accel_status.py \
      --phase live_probe \
      --runtime-file "$runtime_tmp" \
      --previous-file logs/khoj_accel.json > "$status_tmp"
    rm -f "$runtime_tmp"
    mv "$status_tmp" logs/khoj_accel.json
    jq . logs/khoj_accel.json
    ;;
  ncs2|myriad)
    shift || true
    bash scripts/internal/khoj_ncs2_recover.sh "${1:-status}"
    ;;
  logs)
    tail -n 120 logs/khoj_docker.log 2>/dev/null || echo "No khoj log file yet."
    ;;
  *)
    echo "Usage: ./hg_khoj.sh {start|stop|status|reindex|accel|ncs2|logs}"
    exit 1
    ;;
esac
