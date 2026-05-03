#!/bin/bash
# HIGH-GRAVITY TUI Entrypoint

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

exec bash "$SCRIPT_DIR/hg_start.sh" menu
