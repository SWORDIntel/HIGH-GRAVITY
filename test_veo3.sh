#!/bin/bash
# Quick test of Veo 3 video generation infrastructure

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
if [ ! -f "gemini_keys.json" ]; then
    echo "[!] gemini_keys.json not found!"
    exit 1
fi

KEYS_COUNT=$(cat gemini_keys.json | python3 -c "import json, sys; print(len(json.load(sys.stdin)['keys']))")
echo "[+] Found $KEYS_COUNT API keys"

# Test single video generation
echo ""
echo "[*] Testing single video generation..."
echo "    Prompt: 'A futuristic holographic display showing data streams'"
echo ""

./veo3_video_generator.py \
    --prompt "A futuristic holographic display showing data streams" \
    --duration 8 \
    --aspect-ratio 16:9

echo ""
echo "======================================================================="
echo "TEST COMPLETE"
echo "======================================================================="
echo ""
echo "Check veo3_outputs/ for generated videos"
echo ""
