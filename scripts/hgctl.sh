#!/bin/bash
# Backward compatibility shim

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "[DEPRECATED] hgctl.sh is deprecated. Use ./hg.sh <command> instead." >&2
exec bash "$SCRIPT_DIR/../hg.sh" "$@"
