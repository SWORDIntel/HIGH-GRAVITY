#!/usr/bin/env bash
# install_keylog_wrapper.sh — Installs/removes LD_PRELOAD wrapper for TLS key logging
#
# Replaces language_server_linux_x64 with a shell wrapper that injects
# LD_PRELOAD=keylog_preload.so, then execs the real binary.
# The original binary is backed up as language_server_linux_x64.real
#
# Usage:
#   sudo bash tools/install_keylog_wrapper.sh          # install
#   sudo bash tools/install_keylog_wrapper.sh --undo   # remove
#   sudo bash tools/install_keylog_wrapper.sh --verify # check status

set -euo pipefail

BIN_DIR="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin"
BIN="$BIN_DIR/language_server_linux_x64"
REAL="$BIN_DIR/language_server_linux_x64.real"
SO_SRC="$(cd "$(dirname "$0")" && pwd)/keylog_preload.so"
SO_DST="$BIN_DIR/keylog_preload.so"

verify() {
    echo ""
    echo "  Binary:   $BIN"
    if file "$BIN" | grep -q "shell script"; then
        echo "  Status:   WRAPPED (keylog active)"
        echo "  Real bin: $REAL"
        echo "  SO:       $SO_DST"
        if [ -f /tmp/hg_tls.keys ]; then
            local lines; lines=$(wc -l < /tmp/hg_tls.keys)
            echo "  Keys:     /tmp/hg_tls.keys ($lines lines)"
        else
            echo "  Keys:     none yet (restart Windsurf to generate)"
        fi
        return 0
    else
        echo "  Status:   ORIGINAL (not wrapped)"
        return 1
    fi
}

install_wrapper() {
    if file "$BIN" | grep -q "shell script"; then
        echo "  [!] Already wrapped — run with --undo first"
        exit 1
    fi

    if [ ! -f "$SO_SRC" ]; then
        echo "  [!] keylog_preload.so not found at $SO_SRC"
        echo "      Run: gcc -shared -fPIC -O0 -o tools/keylog_preload.so tools/keylog_preload.c -ldl"
        exit 1
    fi

    # Kill any running language server so the binary isn't busy
    local ls_pids
    ls_pids=$(pgrep -f "language_server_linux_x64" 2>/dev/null || true)
    if [ -n "$ls_pids" ]; then
        echo "  [*] Stopping language server (PIDs: $ls_pids)..."
        kill $ls_pids 2>/dev/null || true
        sleep 1
        # Force-kill if still running
        pgrep -f "language_server_linux_x64" | xargs kill -9 2>/dev/null || true
        sleep 0.5
    fi

    echo "  [*] Backing up original binary..."
    cp "$BIN" "$REAL"
    chmod 755 "$REAL"

    echo "  [*] Installing preload library..."
    cp "$SO_SRC" "$SO_DST"
    chmod 755 "$SO_DST"

    echo "  [*] Writing wrapper script..."
    cat > "$BIN" << WRAPPER
#!/bin/bash
export LD_PRELOAD="$SO_DST"
export HG_KEYLOG_FILE="/tmp/hg_tls.keys"
exec "$REAL" "\$@"
WRAPPER
    chmod 755 "$BIN"

    echo "  [+] Wrapper installed"
    echo "  [+] TLS keys -> /tmp/hg_tls.keys"
    echo ""
    echo "  Restart Windsurf language server to activate."
    echo "  (Close and reopen a file, or reload the window)"
}

remove_wrapper() {
    if ! file "$BIN" | grep -q "shell script"; then
        echo "  [!] Not wrapped — nothing to undo"
        exit 1
    fi

    if [ ! -f "$REAL" ]; then
        echo "  [!] Backup not found at $REAL — cannot restore"
        exit 1
    fi

    echo "  [*] Restoring original binary..."
    cp "$REAL" "$BIN"
    chmod 755 "$BIN"
    rm -f "$REAL" "$SO_DST"

    echo "  [+] Wrapper removed, original binary restored"
    echo "  [+] Restart Windsurf to deactivate"
}

case "${1:-}" in
    --undo|--remove)    remove_wrapper ;;
    --verify|--status)  verify ;;
    *)                  install_wrapper ;;
esac
