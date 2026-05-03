#!/bin/bash
# Quick test of Veo 3 video generation infrastructure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
KEYS_FILE="${REPO_ROOT}/config/gemini_keys.json"

if [ ! -f "${KEYS_FILE}" ]; then
    KEYS_FILE="${REPO_ROOT}/gemini_keys.json"
fi

echo "======================================================================="
echo "VEO 3.1 INFRASTRUCTURE TEST"
echo "======================================================================="
echo ""

# Check dependencies
echo "[*] Checking dependencies..."
python3 -c "import requests" 2>/dev/null || {
    echo "[!] Installing requests..."
    pip3 install requests --quiet
}

# Check keys file
if [ ! -f "${KEYS_FILE}" ]; then
    echo "[!] gemini_keys.json not found!"
    exit 1
fi

KEYS_COUNT=$(cat "${KEYS_FILE}" | python3 -c "import json, sys; print(len(json.load(sys.stdin)['keys']))")
echo "[+] Found $KEYS_COUNT API keys"

# Test single video generation
echo ""
echo "[*] Testing single video generation..."
echo "    Prompt: 'A futuristic holographic display showing data streams'"
echo ""

python3 "${REPO_ROOT}/scripts/veo3_video_generator.py" \
    --prompt "A futuristic holographic display showing data streams" \
    --duration 8 \
    --aspect-ratio 16:9 \
    --keys-file "${KEYS_FILE}"

echo ""
echo "======================================================================="
echo "TEST COMPLETE"
echo "======================================================================="
echo ""
echo "Check ${REPO_ROOT}/veo3_outputs/ for generated videos"
echo ""
