#!/bin/bash
# HIGH-GRAVITY Unified Entrypoint CLI
# Consolidates all management scripts and bootstraps the environment.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.hg_proxy_venv"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
PYTHON="$VENV_DIR/bin/python"

# Colors
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[0;34m'; C='\033[0;36m'; NC='\033[0m'

bootstrap_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${B}[*] Creating virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
    fi

    if [ ! -f "$PYTHON" ]; then
        echo -e "${R}[!] Virtual environment broken. Recreating...${NC}"
        rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR"
    fi

    # Check if critical packages are installed
    if ! "$PYTHON" -c "import aiohttp, fastapi, rich, requests" 2>/dev/null; then
        echo -e "${B}[*] Installing/Updating dependencies in venv...${NC}"
        "$PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null
        "$PYTHON" -m pip install aiohttp fastapi uvicorn requests rich textual sentence-transformers >/dev/null
        echo -e "${G}[✓] Dependencies installed${NC}"
    fi
}

print_sudo_notice() {
    local cmd="$1"
    case "$cmd" in
        menu|start|restart|stop|verify|status|doctor|patch|repatch|undo|unpatch|kp14|re)
            echo "Notice: '$cmd' may require sudo (iptables, /etc/hosts, port 443, service control)."
            echo "You may be prompted for your password."
            ;;
    esac
}

usage() {
    cat <<USAGE
${C}HIGH-GRAVITY Unified CLI${NC}

Usage: ./hg.sh <command>

Commands:
  ${G}(none)${NC}      Launch the real-time Rich TUI Dashboard (default)
  ${G}start${NC}       Quick start: Patch then start all services
  ${G}stop${NC}        Quick stop: Emergency shutdown
  ${G}status${NC}      Show service status (CLI)
  ${G}verify${NC}      Verify patch + service status
  ${G}shim${NC}        Deploy LSP Shield (binary wrapper)
  ${G}patch${NC}       Apply all binary/JS/host patches
  ${G}unpatch${NC}     Restore original files (alias for undo)
  ${G}repatch${NC}     Clean repatch flow
  ${G}dashboard${NC}   Launch the Rich TUI dashboard
  ${G}menu${NC}        Classic arrow-key management menu
  ${G}khoj${NC}        Khoj controls (start/stop/status/reindex/logs)
  ${G}doctor${NC}      Deep diagnostics (health, routing, latency)
  ${G}trace${NC}       Watch prompt/completion logs
  ${G}reauth${NC}      Reset local Windsurf auth/login state
  ${G}aliases${NC}     Print command to source aliases

USAGE
}

# Ensure we are in the right directory
cd "$SCRIPT_DIR"

# Bootstrap on every run (fast if already done)
bootstrap_venv

cmd="${1:-dashboard}"

case "$cmd" in
    dashboard)
        exec "$PYTHON" "$SCRIPT_DIR/src/hg_dashboard.py"
        ;;
    menu)
        exec bash "$SCRIPTS_DIR/internal/hgmenu.sh"
        ;;
    start)
        print_sudo_notice "$cmd"
        HG_NON_INTERACTIVE=1 bash "$SCRIPTS_DIR/internal/hg_start.sh" patch
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" start
        ;;
    stop)
        print_sudo_notice "$cmd"
        exec bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct
        ;;
    restart)
        print_sudo_notice "$cmd"
        bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct
        exec bash "$SCRIPT_DIR/hg.sh" start
        ;;
    status)
        print_sudo_notice "$cmd"
        exec bash "$SCRIPTS_DIR/internal/hg_status.sh" --direct
        ;;
    shim)
        print_sudo_notice "$cmd"
        exec bash "$SCRIPTS_DIR/internal/deploy_lsp_shim.sh"
        ;;
    verify|patch|repatch|undo|unpatch)
        print_sudo_notice "$cmd"
        # Map unpatch to undo for the underlying script
        target_cmd="$cmd"
        [[ "$cmd" == "unpatch" ]] && target_cmd="undo"
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" "$target_cmd"
        ;;
    khoj)
        shift || true
        exec bash "$SCRIPTS_DIR/hg_khoj.sh" "${1:-status}"
        ;;
    doctor)
        shift || true
        exec bash "$SCRIPTS_DIR/hg_doctor.sh" "$@"
        ;;
    trace|watch)
        shift || true
        exec bash "$SCRIPTS_DIR/hg_trace.sh" "$@"
        ;;
    reauth)
        echo -e "${Y}[!] This will reset your Windsurf login and local cache.${NC}"
        read -p "Are you sure? (y/N) " confirm
        if [[ $confirm == [yY] ]]; then
            echo -e "${B}[*] Clearing authentication database...${NC}"
            rm -rf "/home/john/.codeium/windsurf-next/database"
            rm -f "/home/john/.codeium/windsurf-next/user_settings.pb"
            echo -e "${G}[✓] Auth state reset. Please restart Windsurf to log in.${NC}"
        else
            echo "Cancelled."
        fi
        ;;
    kp14|re)
        print_sudo_notice "$cmd"
        shift || true
        exec bash "$SCRIPT_DIR/tools/decompilers/run_kp14_decompile.sh" "$@"
        ;;
    aliases)
        echo "Run this command to load aliases:"
        echo "  source $SCRIPTS_DIR/hg_aliases.sh"
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo -e "${R}Unknown command: $cmd${NC}"
        usage
        exit 1
        ;;
esac
