#!/usr/bin/env bash
# Name: setup.sh | Version: v1.1.0
# Purpose: Install Antigravity CLI and stage HIGH-GRAVITY's three-account wrapper.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/high-gravity/antigravity"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/high-gravity/antigravity"
PROFILE_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/high-gravity/antigravity/profiles"
CONFIG_FILE="$CONFIG_DIR/accounts.json"
INSTALL_URL="https://antigravity.google/cli/install.sh"

log() { printf '[antigravity-setup] %s\n' "$*"; }

log "Creating config/state/profile directories"
mkdir -p "$CONFIG_DIR" "$STATE_DIR/sessions" "$PROFILE_ROOT/account_1" "$PROFILE_ROOT/account_2" "$PROFILE_ROOT/account_3"
chmod 700 "$CONFIG_DIR" "$STATE_DIR" "$PROFILE_ROOT" "$PROFILE_ROOT"/account_*

if [[ ! -f "$CONFIG_FILE" ]]; then
  log "Staging sanitized permissive account config at $CONFIG_FILE"
  cp "$SCRIPT_DIR/accounts.example.json" "$CONFIG_FILE"
  CONFIG_FILE="$CONFIG_FILE" PROFILE_ROOT="$PROFILE_ROOT" python3 - <<'PYCFG'
import json
import os
from pathlib import Path
config_path = Path(os.environ["CONFIG_FILE"])
profile_root = Path(os.environ["PROFILE_ROOT"])
data = json.loads(config_path.read_text(encoding="utf-8"))
for index, account in enumerate(data.get("accounts", []), start=1):
    account["profile_dir"] = str(profile_root / f"account_{index}")
config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PYCFG
  chmod 600 "$CONFIG_FILE"
else
  log "Keeping existing account config at $CONFIG_FILE"
fi

if [[ "${SKIP_VENV:-0}" == "1" ]]; then
  log "SKIP_VENV=1 set; skipping wrapper virtualenv bootstrap"
else
  log "Bootstrapping Rich UI virtualenv"
  "$SCRIPT_DIR/bootstrap-venv.sh"
fi

if command -v agy >/dev/null 2>&1; then
  log "Antigravity CLI already present: $(command -v agy)"
elif command -v antigravity >/dev/null 2>&1; then
  log "Antigravity CLI already present: $(command -v antigravity)"
elif [[ "${DRY_RUN:-0}" == "1" ]]; then
  log "DRY_RUN=1 set; would install with: curl -fsSL $INSTALL_URL | bash"
else
  log "Installing official Antigravity CLI from $INSTALL_URL"
  curl -fsSL "$INSTALL_URL" | bash
fi

log "Validation commands:"
printf '  %q/bin/python %q --status\n' "${AGY_VENV:-$SCRIPT_DIR/.venv}" "$SCRIPT_DIR/agy-rotate.py"
printf '  %q/bin/python %q --model standard --dry-run -- "hello"\n' "${AGY_VENV:-$SCRIPT_DIR/.venv}" "$SCRIPT_DIR/agy-rotate.py"
log "Next step: edit $CONFIG_FILE only if you need custom labels/models, then authenticate each account with --login."
