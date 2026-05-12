#!/bin/bash
# deploy_lsp_shim.sh - HIGH-GRAVITY LSP shield deploy/undo helper.
set -euo pipefail

SUDO_PASS="${SUDO_PASS:-1786}"
OWNER="${SUDO_USER:-$(whoami)}"
LSP_DIR="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin"
LSP_BIN="language_server_linux_x64"
REAL_BIN="${LSP_DIR}/${LSP_BIN}.real"
WRAP_BIN="${LSP_DIR}/${LSP_BIN}"
SHIM_SRC="/home/john/HIGH-GRAVITY/scripts/internal/lsp_shim.sh"

usage() {
    cat <<'USAGE'
Usage: deploy_lsp_shim.sh [--undo] [--mode full|inference-only]

Options:
  --undo          Restore original language server binary and remove shim.
  --mode          Force API routing mode for shim (default: full).
                   full: rewrite both api and inference URLs.
                   inference-only: rewrite inference URL only.
USAGE
}

MODE="${HG_PROXY_MODE:-full}"

while [ $# -gt 0 ]; do
    case "$1" in
        --undo)
            UNDO=1
            shift
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "[!] Unknown arg: $1"
            usage
            exit 1
            ;;
    esac
done

sudo_cmd() {
    echo "$SUDO_PASS" | sudo -S "$@"
}

if [ ! -d "$LSP_DIR" ]; then
    echo "[!] Error: LSP directory $LSP_DIR not found."
    exit 1
fi

if [ "${UNDO:-0}" = "1" ]; then
    echo "[*] Removing HIGH-GRAVITY LSP Shield..."

    if [ -f "$REAL_BIN" ] && [ -f "$WRAP_BIN" ]; then
        echo "    - Restoring binary from .real"
        sudo_cmd cp "$REAL_BIN" "$WRAP_BIN"
        sudo_cmd rm -f "$REAL_BIN"
        echo "    - Restored language_server_linux_x64"
    elif [ -f "$REAL_BIN" ]; then
        echo "    - .real already restored; removing any shim residue"
        sudo_cmd rm -f "$WRAP_BIN"
    else
        echo "    - No shim state found"
    fi
    sudo_cmd chown "$OWNER":"$OWNER" "$WRAP_BIN" 2>/dev/null || true
    echo "[✓] LSP Shield removed."
    exit 0
fi

case "$MODE" in
    full|inference-only) ;;
    *)
        echo "[!] Unsupported mode: $MODE"
        usage
        exit 1
        ;;
esac

echo "[*] Deploying HIGH-GRAVITY LSP Shield (mode=${MODE})..."

if [ -f "$WRAP_BIN" ] && [ ! -f "$REAL_BIN" ]; then
    # If the file exists and .real is missing, assume it is already active shim.
    if grep -q "HG_PROXY_URL\|HG_PROXY_MODE\|Real_BIN" "$WRAP_BIN" 2>/dev/null; then
        echo "    - Shim already active."
        echo "[✓] LSP Shield already deployed."
        exit 0
    fi
fi

if [ ! -f "$SHIM_SRC" ]; then
    echo "[!] Shim source missing: $SHIM_SRC"
    exit 1
fi

# 1) Move real binary aside only once
if [ ! -f "$REAL_BIN" ]; then
    if [ ! -f "$WRAP_BIN" ]; then
        echo "[!] Language server binary not found at $WRAP_BIN"
        exit 1
    fi
    echo "    - Backing up real binary to .real"
    sudo_cmd mv "$WRAP_BIN" "$REAL_BIN"
else
    echo "    - Existing .real backup found."
fi

# 2) Install shim
echo "    - Installing shell shim"
sudo_cmd cp "$SHIM_SRC" "$WRAP_BIN"
sudo_cmd chmod +x "$WRAP_BIN"
sudo_cmd chown root:root "$WRAP_BIN"

# 3) Run JS patcher for the extension so proxy endpoints resolve.
echo "[*] Running extension JS patcher..."
python3 /home/john/HIGH-GRAVITY/src/patch_all.py

echo ""
echo "[✓] LSP Shield deployed and wired to localhost:9998."
echo "[!] RESTART WINDSURF NOW to activate the shield."
