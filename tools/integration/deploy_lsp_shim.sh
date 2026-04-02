#!/bin/bash
# deploy_lsp_shim.sh - Fully wires in the HIGH-GRAVITY LSP shield.

SUDO_PASS="1786"
LSP_DIR="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin"
LSP_BIN="language_server_linux_x64"
SHIM_SRC="/home/john/HIGH-GRAVITY/tools/integration/lsp_shim.py"

echo "[*] Deploying HIGH-GRAVITY LSP Shield..."

# 1. Ensure we are in the right directory
if [ ! -d "$LSP_DIR" ]; then
    echo "[!] Error: LSP directory $LSP_DIR not found."
    exit 1
fi

# 2. Backup and Rename real binary if not already done
if [ ! -f "$LSP_DIR/$LSP_BIN.real" ]; then
    echo "    - Moving real binary to .real"
    echo "$SUDO_PASS" | sudo -S mv "$LSP_DIR/$LSP_BIN" "$LSP_DIR/$LSP_BIN.real"
else
    echo "    - Real binary already renamed."
fi

# 3. Copy Shim and make it executable
echo "    - Installing Python shim..."
echo "$SUDO_PASS" | sudo -S cp "$SHIM_SRC" "$LSP_DIR/$LSP_BIN"
echo "$SUDO_PASS" | sudo -S chmod +x "$LSP_DIR/$LSP_BIN"

# 4. Run JS patcher for the extension
echo "[*] Running extension JS patcher..."
python3 /home/john/HIGH-GRAVITY/tools/integration/patch_windsurf_client.py

echo ""
echo "[✓] LSP Shield deployed and wired to localhost:9999."
echo "[!] RESTART WINDSURF NOW to activate the shield."
