#!/bin/bash
# HIGH-GRAVITY Unified Entrypoint CLI
# Expert-Tier Management Suite for Windsurf Proxies

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.hg_proxy_venv"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
PYTHON="$VENV_DIR/bin/python"
HG_DEFAULT_PROXY_URL="http://127.0.0.1:${HG_PROXY_PORT:-9998}"
HG_DEFAULT_USAGE_PATH="/api/oauth/usage"

# Colors
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[0;34m'; C='\033[0;36m'; NC='\033[0m'
BOLD='\033[1m'

bootstrap_venv() {
    if [ ! -d "$VENV_DIR" ] || [ ! -f "$PYTHON" ]; then
        echo -e "${B}[*] Bootstrapping virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
        "$PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null
        "$PYTHON" -m pip install aiohttp fastapi uvicorn hypercorn h2 requests rich textual sentence-transformers numpy >/dev/null
        echo -e "${G}[✓] Environment ready${NC}"
    fi
}

print_sudo_notice() {
    local cmd="$1"
    case "$cmd" in
        menu|start|restart|stop|verify|status|doctor|patch|repatch|undo|unpatch|unpoatch|kp14|re|egress)
            echo -e "${Y}Notice: '$cmd' requires sudo for system-level shields (iptables, /etc/hosts).${NC}"
            ;;
    esac
}

run_usage_probe() {
    # Keep usage probing bound to the local compatibility endpoint unless explicitly
    # overridden by a caller/environment variable.
    if [ -z "${HG_PROXY_URL:-}" ]; then
        export HG_PROXY_URL="$HG_DEFAULT_PROXY_URL"
    fi
    if [ -z "${HG_USAGE_PATH:-}" ]; then
        export HG_USAGE_PATH="$HG_DEFAULT_USAGE_PATH"
    fi

    exec bash "$SCRIPTS_DIR/internal/hg_usage.sh" "$@"
}

normalize_upstream_mode() {
    local mode="${1:-${HG_UPSTREAM_INFERENCE_MODE:-cache-first}}"
    case "$mode" in
        cache-first|cache-only|confirm|block|local-only)
            printf '%s' "$mode"
            ;;
        *)
            echo -e "${R}Invalid upstream inference mode: $mode${NC}" >&2
            echo "Valid modes: cache-first, cache-only, confirm, block, local-only" >&2
            return 2
            ;;
    esac
}

usage() {
    cat <<USAGE
${BOLD}${C}HIGH-GRAVITY Unified CLI${NC}

Usage: ./hg.sh <command>

  Core Commands:
  ${G}(none)${NC}      Launch the interactive Management Menu (default)
  ${G}dashboard${NC}   Launch the real-time Rich TUI Dashboard (alias: dash)
  ${G}hmi-dashboard${NC} Launch the procedural HMI dashboard (alias: hmi dashboard)
  ${G}start${NC}       Quick start: Patch and launch all services
  ${G}start-proxy${NC}  Restart only proxy services (keep Windsurf running)
  ${G}start-proxy-c [mode]${NC} Start C-front proxy; mode: cache-first/cache-only/confirm/block/local-only
  ${G}stop${NC}        Emergency shutdown of all shields and proxies
  ${G}stop-proxy${NC}  Shutdown only proxy services (keep Windsurf running)
  ${G}restart-proxy${NC}Restart only proxy services (no Windsurf restart)
  ${G}restart-proxy-c [mode]${NC}Restart C-front proxy with selected upstream inference mode
  ${G}doctor${NC}      Run CSEC-tier deep system diagnostics

Shield Management:
  ${G}patch${NC}       Apply multi-point binary, JS, and DNS patches
  ${G}unpatch${NC}     Restore original system files (undo all patches)
  ${G}repatch${NC}     Clean restoration followed by fresh patching
  ${G}shim${NC}        Deploy LSP process-level bash shield

  Monitoring:
  ${G}status${NC}      Quick CLI health check
  ${G}throughput${NC}  Sample live proxy + microproxy counters for throughput baseline
  ${G}usage${NC}       Show proxy-side usage pressure and cache savings ratio (via /api/oauth/usage)
  ${G}watch-quota${NC} Focused watch for quota/inference stream lifecycle
  ${G}egress${NC}      Detect/trap Windsurf direct-IP egress that bypasses local proxy
  ${G}trace${NC}       Watch real-time prompt/completion routing
  ${G}logs${NC}        View central intelligence logs

Advanced:
  ${G}microproxy${NC}  Manage disabled microproxy prototype build/status/run/stop
  ${G}hmi${NC}         Manage procedural C++ HMI build/check/run/tui/status
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
    hmi-dashboard|hmi_dash|hmidashboard)
        exec bash "$SCRIPTS_DIR/internal/hg_hmi.sh" tui
        ;;
    dashboard|dash)
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
    start-proxy|proxy-start)
        print_sudo_notice "$cmd"
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" start_proxy
        ;;
    start-proxy-c|proxy-start-c|c-proxy-start)
        print_sudo_notice "$cmd"
        proxy_mode="$(normalize_upstream_mode "${2:-}")"
        HG_MICROPROXY_FRONT=1 \
        HG_MICROPROXY_HOT_PATH_OBSERVE="${HG_MICROPROXY_HOT_PATH_OBSERVE:-0}" \
        HG_KHOJ_BINARY_INJECT="${HG_KHOJ_BINARY_INJECT:-1}" \
        HG_EXACT_RESPONSE_CACHE="${HG_EXACT_RESPONSE_CACHE:-1}" \
        HG_CANONICAL_RESPONSE_CACHE="${HG_CANONICAL_RESPONSE_CACHE:-1}" \
        HG_LOCAL_ACK_TELEMETRY="${HG_LOCAL_ACK_TELEMETRY:-1}" \
        HG_UPSTREAM_INFERENCE_MODE="$proxy_mode" \
        HG_BINARY_FAIL_OPEN="${HG_BINARY_FAIL_OPEN:-1}" \
        HG_BINARY_FAIL_OPEN_BYTES="${HG_BINARY_FAIL_OPEN_BYTES:-65536}" \
        HG_PEGASUS_SWARM_TRIGGER="${HG_PEGASUS_SWARM_TRIGGER:-1}" \
        HG_PEGASUS_SWARM_TRIGGER_LEVELS="${HG_PEGASUS_SWARM_TRIGGER_LEVELS:-high,xhigh}" \
        HG_PEGASUS_SWARM_COOLDOWN_SECONDS="${HG_PEGASUS_SWARM_COOLDOWN_SECONDS:-90}" \
        HG_MICROPROXY_FRONT_IDLE_TIMEOUT="${HG_MICROPROXY_FRONT_IDLE_TIMEOUT:-180}" \
        HG_MICROPROXY_FRONT_MAX_STREAM_SECONDS="${HG_MICROPROXY_FRONT_MAX_STREAM_SECONDS:-600}" \
        HG_MICROPROXY_FRONT_MAX_ACTIVE_STREAMS="${HG_MICROPROXY_FRONT_MAX_ACTIVE_STREAMS:-96}" \
        HG_QUOTA_PROBE="${HG_QUOTA_PROBE:-0}" \
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" start_proxy
        ;;
    stop)
        print_sudo_notice "$cmd"
        exec bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct
        ;;
    stop-proxy|proxy-stop)
        print_sudo_notice "$cmd"
        exec bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct --proxy-only
        ;;
    restart-proxy|proxy-restart)
        print_sudo_notice "$cmd"
        bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct --proxy-only
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" start_proxy
        ;;
    restart-proxy-c|proxy-restart-c|c-proxy-restart)
        print_sudo_notice "$cmd"
        proxy_mode="$(normalize_upstream_mode "${2:-}")"
        bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct --proxy-only
        HG_MICROPROXY_FRONT=1 \
        HG_MICROPROXY_HOT_PATH_OBSERVE="${HG_MICROPROXY_HOT_PATH_OBSERVE:-0}" \
        HG_KHOJ_BINARY_INJECT="${HG_KHOJ_BINARY_INJECT:-1}" \
        HG_EXACT_RESPONSE_CACHE="${HG_EXACT_RESPONSE_CACHE:-1}" \
        HG_CANONICAL_RESPONSE_CACHE="${HG_CANONICAL_RESPONSE_CACHE:-1}" \
        HG_LOCAL_ACK_TELEMETRY="${HG_LOCAL_ACK_TELEMETRY:-1}" \
        HG_UPSTREAM_INFERENCE_MODE="$proxy_mode" \
        HG_BINARY_FAIL_OPEN="${HG_BINARY_FAIL_OPEN:-1}" \
        HG_BINARY_FAIL_OPEN_BYTES="${HG_BINARY_FAIL_OPEN_BYTES:-65536}" \
        HG_PEGASUS_SWARM_TRIGGER="${HG_PEGASUS_SWARM_TRIGGER:-1}" \
        HG_PEGASUS_SWARM_TRIGGER_LEVELS="${HG_PEGASUS_SWARM_TRIGGER_LEVELS:-high,xhigh}" \
        HG_PEGASUS_SWARM_COOLDOWN_SECONDS="${HG_PEGASUS_SWARM_COOLDOWN_SECONDS:-90}" \
        HG_MICROPROXY_FRONT_IDLE_TIMEOUT="${HG_MICROPROXY_FRONT_IDLE_TIMEOUT:-180}" \
        HG_MICROPROXY_FRONT_MAX_STREAM_SECONDS="${HG_MICROPROXY_FRONT_MAX_STREAM_SECONDS:-600}" \
        HG_MICROPROXY_FRONT_MAX_ACTIVE_STREAMS="${HG_MICROPROXY_FRONT_MAX_ACTIVE_STREAMS:-96}" \
        HG_QUOTA_PROBE="${HG_QUOTA_PROBE:-0}" \
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" start_proxy
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
    throughput)
        shift || true
        exec bash "$SCRIPTS_DIR/internal/hg_throughput.sh" "$@"
        ;;
    usage)
        shift || true
        run_usage_probe "$@"
        ;;
    egress)
        print_sudo_notice "$cmd"
        shift || true
        exec bash "$SCRIPTS_DIR/internal/hg_egress.sh" "${@:-status}"
        ;;
    watch-quota|watch_quota|quota-watch)
        shift || true
        exec bash "$SCRIPTS_DIR/internal/hg_watch_quota.sh" "$@"
        ;;
    doctor)
        print_sudo_notice "$cmd"
        exec bash "$SCRIPTS_DIR/hg_doctor.sh"
        ;;
    shim)
        print_sudo_notice "$cmd"
        exec bash "$SCRIPTS_DIR/internal/deploy_lsp_shim.sh"
        ;;
    verify|patch|repatch|undo|unpatch|unpoatch|reset)
        print_sudo_notice "$cmd"
        target_cmd="$cmd"
        [[ "$cmd" == "unpatch" ]] && target_cmd="undo"
        [[ "$cmd" == "unpoatch" ]] && target_cmd="undo"
        [[ "$cmd" == "reset" ]] && target_cmd="repatch"
        exec bash "$SCRIPTS_DIR/internal/hg_start.sh" "$target_cmd"
        ;;
    khoj)
        shift || true
        exec bash "$SCRIPTS_DIR/hg_khoj.sh" "${@:-status}"
        ;;
    microproxy)
        shift || true
        exec bash "$SCRIPTS_DIR/internal/hg_microproxy.sh" "${@:-status}"
        ;;
    hmi)
        shift || true
        exec bash "$SCRIPTS_DIR/internal/hg_hmi.sh" "${@:-status}"
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
