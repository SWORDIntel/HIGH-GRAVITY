#!/bin/bash
# Restore binary from backup and repatch cleanly.
# Run this any time the binary needs to be re-patched from a fresh state.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

SUDO_PASS="1786"
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; B='\033[0;34m'; NC='\033[0m'

echo -e "${B}[1/5] Checking clean backups exist...${NC}"
if ! python3 src/patch_all.py --check-backups --binary-only; then
    echo ""
    echo -e "${R}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${R}║  NO CLEAN BINARY BACKUP — cannot restore.                   ║${NC}"
    echo -e "${R}║  Options:                                                    ║${NC}"
    echo -e "${R}║    1. Reinstall Windsurf to get a fresh binary.              ║${NC}"
    echo -e "${R}║    2. Copy the original from another machine / package.      ║${NC}"
    echo -e "${R}║  Then place it at:                                           ║${NC}"
    echo -e "${R}║    ...windsurf/bin/language_server_linux_x64.original        ║${NC}"
    echo -e "${R}╚══════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi

echo -e "${B}[2/5] Stopping Windsurf...${NC}"
echo "$SUDO_PASS" | sudo -S pkill -f windsurf-next 2>/dev/null || true
sleep 2
if pgrep -f windsurf-next >/dev/null 2>&1; then
    echo -e "${R}[!] Windsurf still running — kill it manually and re-run.${NC}"
    exit 1
fi
echo -e "${G}[+] Windsurf stopped${NC}"

echo -e "${B}[3/5] Restoring binary from backup...${NC}"
python3 src/patch_all.py --restore --binary-only

echo -e "${B}[4/5] Patching all layers...${NC}"
python3 src/patch_all.py --force

echo -e "${B}[5/5] Verifying...${NC}"
python3 src/patch_all.py --verify

echo ""
echo -e "${G}Done. Start Windsurf:${NC}"
echo -e "  /usr/share/windsurf-next/windsurf-next &"
