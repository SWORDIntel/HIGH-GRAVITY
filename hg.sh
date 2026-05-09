#!/bin/bash
# HIGH-GRAVITY Unified Entrypoint CLI
# Expert-Tier Management Suite for Windsurf Proxies

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.hg_proxy_venv"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
PYTHON="$VENV_DIR/bin/python"

# Colors
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[0;34m'; C='\033[0;36m'; NC='\033[0m'
BOLD='\033[1m'

bootstrap_venv() {
    if [ ! -d "$VENV_DIR" ] || [ ! -f "$PYTHON" ]; then
        echo -e "${B}[*] Bootstrapping virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
        "$PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null
        "$PYTHON" -m pip install aiohttp fastapi uvicorn requests rich textual sentence-transformers numpy >/dev/null
        echo -e "${G}[✓] Environment ready${NC}"
    fi
}

print_sudo_notice() {
    local cmd="$1"
    case "$cmd" in
        menu|start|restart|stop|verify|status|doctor|patch|repatch|undo|unpatch|kp14|re)
            echo -e "${Y}Notice: '$cmd' requires sudo for system-level shields (iptables, /etc/hosts).${NC}"
            ;;
    esac
}

usage() {
    cat <<USAGE
${BOLD}${C}HIGH-GRAVITY Unified CLI${NC}

Usage: ./hg.sh <command>

Core Commands:
  ${G}(none)${NC}      Launch the interactive Management Menu (default)
  ${G}dashboard${NC}   Launch the real-time Rich TUI Dashboard
  ${G}start${NC}       Quick start: Patch and launch all services
  ${G}stop${NC}        Emergency shutdown of all shields and proxies
  ${G}doctor${NC}      Run CSEC-tier deep system diagnostics

Shield Management:
  ${G}patch${NC}       Apply multi-point binary, JS, and DNS patches
  ${G}unpatch${NC}     Restore original system files (undo all patches)
  ${G}repatch${NC}     Clean restoration followed by fresh patching
  ${G}shim${NC}        Deploy LSP process-level bash shield

Monitoring:
  ${G}status${NC}      Quick CLI health check
  ${G}trace${NC}       Watch real-time prompt/completion routing
  ${G}logs${NC}        View central intelligence logs

Advanced:
  ${G}khoj${NC}        Manage RAG intelligence (reindex/status)
  ${G}reauth${NC}      Reset local Windsurf identity/auth state
  ${G}kp14${NC}        Run advanced binary analysis pipeline

USAGE
}

# Ensure we are in the right directory
cd "$SCRIPT_DIR"
bootstrap_venv

cmd="${1:-menu}"

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
    status|check)
        print_sudo_notice "status"
        exec bash "$SCRIPTS_DIR/internal/hg_status.sh" --direct
        ;;
    doctor)
        print_sudo_notice "$cmd"
        exec bash "$SCRIPTS_DIR/hg_doctor.sh"
        ;;
    shim)
        print_sudo_notice "$cmd"
        exec bash "$SCRIPTS_DIR/internal/deploy_lsp_shim.sh"
        ;;
    verify|patch|repatch|undo|unpatch|reset)
        print_sudo_notice "$cmd"
        target_cmd="$cmd"
        [[ "$cmd" == "unpatch" ]] && target_cmd="undo"
        [[ "$cmd" == "reset" ]] && target_cmd="repatch"
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" "$target_cmd"
        ;;
    khoj)
        shift || true
        exec bash "$SCRIPTS_DIR/hg_khoj.sh" "${1:-status}"
        ;;
    trace|watch)
        shift || true
        exec bash "$SCRIPTS_DIR/hg_trace.sh" "$@"
        ;;
    logs)
        tail -f logs/proxy.log logs/cascade_midway.log
        ;;
    reauth)
        echo -e "${Y}[!] This will reset your local Windsurf identity database.${NC}"
        read -p "Are you sure? (y/N) " confirm
        if [[ $confirm == [yY] ]]; then
            rm -rf "/home/john/.codeium/windsurf-next/database"
            rm -f "/home/john/.codeium/windsurf-next/user_settings.pb"
            echo -e "${G}[✓] Auth state reset. Restart Windsurf to log in.${NC}"
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
