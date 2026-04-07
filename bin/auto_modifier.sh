#!/bin/bash
# HIGH-GRAVITY Auto-Modifier
# Monitors Windsurf installations and ensures patches are active.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PATCHER="$REPO_ROOT/src/patch_windsurf_client.py"
SUDO_PASS="1786"

echo "[*] HIGH-GRAVITY Auto-Modifier starting..."

# 1. Run the patcher
python3 "$PATCHER"

# 2. Check if we should install a systemd service for persistence
if [[ "$1" == "--install" ]]; then
    SERVICE_FILE="/etc/systemd/system/highgravity-autopatch.service"
    TIMER_FILE="/etc/systemd/system/highgravity-autopatch.timer"

    echo "[*] Installing systemd persistence..."

    cat <<EOF | echo "$SUDO_PASS" | sudo -S tee "$SERVICE_FILE" > /dev/null
[Unit]
Description=HIGH-GRAVITY Windsurf Auto-Patcher
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 $PATCHER
User=root

[Install]
WantedBy=multi-user.target
EOF

    cat <<EOF | echo "$SUDO_PASS" | sudo -S tee "$TIMER_FILE" > /dev/null
[Unit]
Description=Run HIGH-GRAVITY Auto-Patcher every hour

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Unit=highgravity-autopatch.service

[Install]
WantedBy=timers.target
EOF

    echo "$SUDO_PASS" | sudo -S systemctl daemon-reload
    echo "$SUDO_PASS" | sudo -S systemctl enable --now highgravity-autopatch.timer
    
    echo "[✓] systemd persistence installed. Patches will be re-applied every hour."
fi
