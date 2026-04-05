#!/bin/bash
# Script to run KP14 decompilation on Windsurf Language Server

set -e

KP14_ROOT="/media/john/NVME_STORAGE5/KP14_PROJECT"
KP14_SRC="$KP14_ROOT/src"
KP14_VENV="$KP14_ROOT/venv"
GHIDRA_PATH="/media/john/NVME_STORAGE5/KP14_PROJECT/deps/ghidra/Ghidra/RuntimeScripts/Linux"
LS_BINARY="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64"

# Set environment
export GHIDRA_INSTALL_DIR="$GHIDRA_PATH"
export PYTHONPATH="$KP14_SRC:/media/john/NVME_STORAGE5/DSMILSystem/tools/blackroom_ai"
export PATH="/usr/local/bin:$PATH"

# Run analysis
echo "[*] Starting KP14 analysis of Windsurf Language Server..."
"$KP14_VENV/bin/python" -m kp14.cli.kp14 analyze "$LS_BINARY"
