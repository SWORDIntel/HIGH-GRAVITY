#!/bin/bash
# Restart Windsurf to activate MITM patches

echo "[*] Killing all Windsurf processes..."
pkill -9 windsurf

sleep 2

echo "[*] Verifying Windsurf is stopped..."
if pgrep -x windsurf > /dev/null; then
    echo "[!] Windsurf still running, force killing..."
    killall -9 windsurf-next windsurf 2>/dev/null
    sleep 1
fi

echo "[✓] Windsurf stopped"
echo ""
echo "[*] Restart Windsurf manually or run:"
echo "    windsurf-next &"
echo ""
echo "[*] After restart, the MITM hooks will be active"
echo "[*] Check logs/cascade_midway.log for protocol events"
