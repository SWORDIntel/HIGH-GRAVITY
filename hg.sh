#!/bin/bash
# HIGH-GRAVITY Unified CLI v4.0
# The authoritative entry point for the HIGH-GRAVITY Antigravity observability stack.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.hg_proxy_venv"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
PYTHON="$VENV_DIR/bin/python"

# Environment Defaults
export HG_MICROPROXY_FRONT="${HG_MICROPROXY_FRONT:-1}"
export HG_UPSTREAM_INFERENCE_MODE="${HG_UPSTREAM_INFERENCE_MODE:-cache-first}"
export HG_LOCAL_ACK_TELEMETRY="${HG_LOCAL_ACK_TELEMETRY:-0}"
export HG_CLIENT_TARGET="${HG_CLIENT_TARGET:-antigravity}"
export HG_TRAFFIC_MUTATION_ENABLED="${HG_TRAFFIC_MUTATION_ENABLED:-0}"
export HG_DECRYPTED_TRAFFIC_LOG="${HG_DECRYPTED_TRAFFIC_LOG:-1}"
export HG_DECRYPTED_TRAFFIC_FULL_BODY="${HG_DECRYPTED_TRAFFIC_FULL_BODY:-1}"
export HG_KHOJ_BINARY_INJECT="${HG_KHOJ_BINARY_INJECT:-0}"
export HG_TOKEN_SAVER="${HG_TOKEN_SAVER:-0}"
export HG_EDGE_EVENT_LOG="${HG_EDGE_EVENT_LOG:-$SCRIPT_DIR/logs/microproxy_events.jsonl}"

# Colors
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[0;34m'; C='\033[0;36m'; NC='\033[0m'
BOLD='\033[1m'

bootstrap_venv() {
    if [ ! -d "$VENV_DIR" ] || [ ! -x "$PYTHON" ]; then
        echo -e "${B}[*] Bootstrapping virtual environment...${NC}"
        python3 -m venv --system-site-packages "$VENV_DIR"
    fi
    if "$PYTHON" -c 'import aiohttp, fastapi, h2, hypercorn, requests, rich, uvicorn, yaml' >/dev/null 2>&1; then
        echo -e "${G}[✓] Environment ready${NC}"
        return 0
    fi
    echo -e "${Y}[!] Core imports missing; attempting requirements install${NC}"
    if ! "$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" >/dev/null; then
        echo -e "${Y}[!] dependency install blocked; run './hg.sh audit' for exact findings${NC}"
        return 1
    fi
    echo -e "${G}[✓] Environment ready${NC}"
}

print_sudo_notice() {
    echo -e "${Y}Notice: This operation requires sudo for system-level shields (iptables, /etc/hosts).${NC}"
}

usage() {
    cat <<USAGE
${BOLD}${C}HIGH-GRAVITY Unified CLI${NC}

Usage: ./hg.sh <command> [args]

Core Commands:
  ${G}start${NC}           Full stack launch: Antigravity observe-only proxy stack
  ${G}stop${NC}            Full stack shutdown (emergency kill)
  ${G}restart${NC}         Full stack restart
  ${G}dash${NC}            Launch the real-time Rich TUI Dashboard (alias: dashboard)
  ${G}antigravity${NC}     Bootstrap/status/run/resume/monitor the ag-cli control plane

Proxy Management:
  ${G}proxy start${NC}     Start only proxy services (C-front + Python)
  ${G}proxy stop${NC}      Stop only proxy services
  ${G}proxy restart${NC}   Restart only proxy services
  ${G}proxy status${NC}    Check proxy health and port status
  ${G}microproxy${NC}       Build/smoke/status the C microproxy stage

Shield Management:
  ${G}patch${NC}           Apply binary, JS, and DNS identity patches
  ${G}unpatch${NC}         Restore original system state (alias: undo)
  ${G}repatch${NC}         Clean restoration followed by fresh patching
  ${G}reauth${NC}          Reset local Windsurf identity database

Advanced:
  ${G}doctor${NC}          Deep system diagnostics
  ${G}audit${NC}           Run E2E dependency, build, stream, and test audit
  ${G}logs${NC}            Tail proxy, C microproxy, and decrypted flow logs
  ${G}usage${NC}           Show real-time quota pressure and cache savings ratio
  ${G}egress${NC}          Monitor/Trap direct-IP bypass attempts

USAGE
}

# Ensure we are in the right directory
cd "$SCRIPT_DIR"
cmd="${1:-menu}"
case "$cmd" in
    audit|e2e-audit|microproxy|cproxy|edge|antigravity|ag|agy|usage|logs|egress|-h|--help|help)
        ;;
    *)
        bootstrap_venv
        ;;
esac

# --- CLI Router ---
case "$cmd" in
    # --- Full Stack ---
    start)
        print_sudo_notice
        if [ "${HG_CLIENT_TARGET:-antigravity}" != "antigravity" ]; then
            HG_NON_INTERACTIVE=1 bash "$SCRIPTS_DIR/internal/hg_start.sh" patch
        fi
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" start
        ;;
    stop)
        print_sudo_notice
        exec bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct
        ;;
    restart)
        print_sudo_notice
        bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct
        exec bash "$SCRIPT_DIR/hg.sh" start
        ;;

    # --- Proxy Stack ---
    proxy|start-proxy|start-proxy-c|proxy-start|proxy-start-c)
        subcmd="${2:-status}"
        # Compatibility: if first arg was start-proxy-c, second arg is the mode
        if [[ "$cmd" == "start-proxy-c" || "$cmd" == "proxy-start-c" ]]; then
            mode="$2"
            subcmd="start"
        elif [[ "$subcmd" == "start" || "$subcmd" == "restart" ]]; then
            mode="$3"
        fi
        
        case "$subcmd" in
            start)
                print_sudo_notice
                export HG_MICROPROXY_FRONT=1
                export HG_UPSTREAM_INFERENCE_MODE="${mode:-cache-first}"
                exec bash "$SCRIPTS_DIR/internal/hg_start.sh" start_proxy
                ;;
            stop)
                print_sudo_notice
                exec bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct --proxy-only
                ;;
            restart)
                print_sudo_notice
                bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct --proxy-only
                export HG_MICROPROXY_FRONT=1
                export HG_UPSTREAM_INFERENCE_MODE="${mode:-cache-first}"
                exec bash "$SCRIPTS_DIR/internal/hg_start.sh" start_proxy
                ;;
            status|check)
                exec bash "$SCRIPTS_DIR/internal/hg_status.sh" --direct
                ;;
            *)
                # Handle direct mode switch if subcmd is a mode
                case "$subcmd" in
                    cache-first|cache-only|confirm|block|local-only|passthrough)
                        print_sudo_notice
                        bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct --proxy-only
                        export HG_MICROPROXY_FRONT=1
                        export HG_UPSTREAM_INFERENCE_MODE="$subcmd"
                        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" start_proxy
                        ;;
                    *)
                        echo -e "${R}Unknown proxy subcommand: $subcmd${NC}"
                        exit 1
                        ;;
                esac
                ;;
        esac
        ;;

    proxy-stop|stop-proxy)
        print_sudo_notice
        exec bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct --proxy-only
        ;;

    # --- Shield Management ---
    patch)
        print_sudo_notice
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" patch
        ;;
    unpatch|undo)
        print_sudo_notice
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" undo
        ;;
    repatch|reset)
        print_sudo_notice
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" repatch
        ;;
    reauth)
        echo -e "${Y}[!] This will reset your local Windsurf identity database.${NC}"
        read -p "Are you sure? (y/N) " confirm
        if [[ $confirm == [yY] ]]; then
            rm -rf "/home/john/.codeium/windsurf-next/database"
            rm -f "/home/john/.codeium/windsurf-next/user_settings.pb"
            echo -e "${G}[✓] Auth state reset. Restart Windsurf to log in.${NC}"
        fi
        ;;

    # --- Antigravity Control Plane ---
    antigravity|ag|agy)
        exec bash "$SCRIPTS_DIR/internal/hg_antigravity.sh" "${@:2}"
        ;;

    # --- C Microproxy Control Plane ---
    microproxy|cproxy|edge)
        exec bash "$SCRIPTS_DIR/internal/hg_microproxy.sh" "${@:2}"
        ;;

    # --- Monitoring & Tools ---
    dash|dashboard)
        exec "$PYTHON" "$SCRIPT_DIR/src/hg_dashboard.py"
        ;;
    doctor)
        exec bash "$SCRIPTS_DIR/hg_doctor.sh"
        ;;
    audit|e2e-audit)
        exec python3 "$SCRIPT_DIR/tools/audit/hg_e2e_audit.py" "${@:2}"
        ;;
    logs)
        touch logs/proxy.log logs/traffic_flows.jsonl "${HG_EDGE_EVENT_LOG}"
        tail -f logs/proxy.log logs/traffic_flows.jsonl "${HG_EDGE_EVENT_LOG}" logs/cascade_midway.log
        ;;
    usage)
        exec bash "$SCRIPTS_DIR/internal/hg_usage.sh" "${@:2}"
        ;;
    egress)
        exec bash "$SCRIPTS_DIR/internal/hg_egress.sh" "${2:-status}"
        ;;
    
    # --- Interactive Menu ---
    menu)
        exec bash "$SCRIPTS_DIR/internal/hgmenu.sh"
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
