#!/usr/bin/env bash
# HighGravity Debug Launcher - Enhanced for Windsurf/Codex/Gemini
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${REPO_ROOT}/logs"
DEBUG_LOG="${LOG_DIR}/debug.log"
LAUNCHER="${REPO_ROOT}/bin/gemini_session_launcher.py"

# Parse arguments
MODE="${1:-windsurf}"  # windsurf, studio, chat
KEY_INDEX="${2:-1}"

mkdir -p "${LOG_DIR}"
echo "[*] Starting HighGravity Debug Session at $(date)" | tee "${DEBUG_LOG}"
echo "[*] Mode: ${MODE} | Key Index: ${KEY_INDEX}" | tee -a "${DEBUG_LOG}"

# 1. Kill existing proxy
echo "[*] Cleaning up existing proxy..." | tee -a "${DEBUG_LOG}"
pkill -f "highgravity_proxy.py" || true
sleep 1

# 2. Start Proxy with DEBUG logging
echo "[*] Starting Proxy with DEBUG logging..." | tee -a "${DEBUG_LOG}"
export HG_LOG_LEVEL=DEBUG
python3 "${REPO_ROOT}/tools/integration/highgravity_proxy.py" >> "${DEBUG_LOG}" 2>&1 &
PROXY_PID=$!
echo "[+] Proxy started (PID: ${PROXY_PID})" | tee -a "${DEBUG_LOG}"

# Wait for proxy to be ready
sleep 2
if ! curl -s http://localhost:9998/hg/telemetry > /dev/null 2>&1; then
    echo "[!] Warning: Proxy may not be ready yet" | tee -a "${DEBUG_LOG}"
fi

# 3. Launch based on mode
case "${MODE}" in
    windsurf|w)
        echo "[*] Launching Windsurf with Codex bypass..." | tee -a "${DEBUG_LOG}"
        python3 "${LAUNCHER}" \
            --mode windsurf \
            --provider proxy \
            --proxy-url http://localhost:9998 \
            --key-index "${KEY_INDEX}" \
            --dangerously-bypass-approvals-and-sandbox \
            >> "${DEBUG_LOG}" 2>&1 &
        ;;
    studio|s)
        echo "[*] Launching Gemini AI Studio..." | tee -a "${DEBUG_LOG}"
        python3 "${LAUNCHER}" \
            --mode studio \
            --key-index "${KEY_INDEX}" \
            -y \
            >> "${DEBUG_LOG}" 2>&1 &
        ;;
    chat|c)
        echo "[*] Launching Gemini Chat..." | tee -a "${DEBUG_LOG}"
        python3 "${LAUNCHER}" \
            --mode chat \
            --key-index "${KEY_INDEX}" \
            -y \
            >> "${DEBUG_LOG}" 2>&1 &
        ;;
    *)
        echo "[X] Unknown mode: ${MODE}" | tee -a "${DEBUG_LOG}"
        echo "Usage: $0 [windsurf|studio|chat] [key_index]" | tee -a "${DEBUG_LOG}"
        exit 1
        ;;
esac

echo "[✓] Debug session active. Watch logs with: tail -f ${DEBUG_LOG}"
echo "[*] Proxy telemetry: curl http://localhost:9998/hg/telemetry | jq"
echo "[*] Waiting for traffic... (Ctrl+C to stop)"

# Keep alive to see logs
tail -f "${DEBUG_LOG}"
