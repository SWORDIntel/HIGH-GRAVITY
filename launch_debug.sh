#!/usr/bin/env bash
# HighGravity Debug Launcher
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${REPO_ROOT}/logs"
DEBUG_LOG="${LOG_DIR}/debug.log"

mkdir -p "${LOG_DIR}"
echo "[*] Starting HighGravity Debug Session at $(date)" | tee "${DEBUG_LOG}"

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

# 3. Detect latest profile
PROFILE_SCRIPT=$(ls -t "${REPO_ROOT}"/windsurf_profiles/*/launch_windsurf.sh 2>/dev/null | head -n 1)

if [ -z "${PROFILE_SCRIPT}" ]; then
    echo "[!] No Windsurf profile found. Running wire-in..." | tee -a "${DEBUG_LOG}"
    python3 "${REPO_ROOT}/tools/integration/detect_and_wire_windsurf.py" >> "${DEBUG_LOG}" 2>&1
    PROFILE_SCRIPT=$(ls -t "${REPO_ROOT}"/windsurf_profiles/*/launch_windsurf.sh 2>/dev/null | head -n 1)
fi

if [ -z "${PROFILE_SCRIPT}" ]; then
    echo "[X] Error: Failed to find or create a profile." | tee -a "${DEBUG_LOG}"
    exit 1
fi

echo "[*] Using profile script: ${PROFILE_SCRIPT}" | tee -a "${DEBUG_LOG}"

# 4. Launch Windsurf with set -x
echo "[*] Launching Windsurf Next in debug mode..." | tee -a "${DEBUG_LOG}"
export WINDSURF_BIN=windsurf-next
bash -x "${PROFILE_SCRIPT}" >> "${DEBUG_LOG}" 2>&1 &

echo "[✓] Debug session active. Watch logs with: tail -f ${DEBUG_LOG}"
echo "[*] Waiting for traffic... (Ctrl+C to stop)"

# Keep alive to see logs
tail -f "${DEBUG_LOG}"
