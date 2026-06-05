#!/usr/bin/env bash
# Name: bootstrap-venv.sh | Version: v1.0.0
# Purpose: Create a local Python virtualenv for the Antigravity account rotator UI.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${AGY_VENV:-$SCRIPT_DIR/.venv}"
PYTHON_BIN="${PYTHON:-python3}"

log() { printf '[agy-bootstrap] %s\n' "$*"; }

log "Creating virtualenv at $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"
log "Installing Python UI dependencies"
if ! "$VENV_DIR/bin/python" -m pip install --upgrade pip; then
  log "WARNING: pip upgrade failed; continuing because agy-rotate.py has a plain fallback UI"
fi
if ! "$VENV_DIR/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"; then
  log "WARNING: Rich install failed; continuing with the built-in plain fallback UI"
  if [[ "${REQUIRE_RICH:-0}" == "1" ]]; then
    exit 1
  fi
fi
log "Ready. Use: $VENV_DIR/bin/python $SCRIPT_DIR/agy-rotate.py --status"
