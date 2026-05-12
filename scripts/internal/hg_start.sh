#!/bin/bash
# HIGH-GRAVITY Bootstrap v3.0 — Authoritative Entry Point
#
# ALL patch/undo/verify operations go through this script.
# Underlying patcher: src/patch_all.py  (do not run directly)
# Clean repatch:      bash scripts/internal/repatch.sh    (or menu item 2)
# Pure bash, no whiptail/dialog dependency

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SCRIPT_DIR"

SUDO_PASS="1786"
HG_PROXY_MODE="${HG_PROXY_MODE:-full}"
HG_MICROPROXY_FRONT="${HG_MICROPROXY_FRONT:-1}"
HG_PROXY_HTTPS_PORT="${HG_PROXY_HTTPS_PORT:-443}"
HG_PROXY_INTERNAL_HTTPS_PORT="${HG_PROXY_INTERNAL_HTTPS_PORT:-9443}"
HG_KHOJ_BINARY_INJECT="${HG_KHOJ_BINARY_INJECT:-1}"
HG_KHOJ_BINARY_INLINE_TIMEOUT_SECONDS="${HG_KHOJ_BINARY_INLINE_TIMEOUT_SECONDS:-0}"
HG_BINARY_REASONING_INJECT_MAX_BYTES="${HG_BINARY_REASONING_INJECT_MAX_BYTES:-32768}"
HG_EXACT_RESPONSE_CACHE="${HG_EXACT_RESPONSE_CACHE:-1}"
HG_EXACT_RESPONSE_CACHE_TTL_SECONDS="${HG_EXACT_RESPONSE_CACHE_TTL_SECONDS:-600}"
HG_EXACT_RESPONSE_CACHE_MAX_ENTRIES="${HG_EXACT_RESPONSE_CACHE_MAX_ENTRIES:-64}"
HG_EXACT_RESPONSE_CACHE_MAX_BODY_BYTES="${HG_EXACT_RESPONSE_CACHE_MAX_BODY_BYTES:-1048576}"
HG_CANONICAL_RESPONSE_CACHE="${HG_CANONICAL_RESPONSE_CACHE:-1}"
HG_CANONICAL_RESPONSE_CACHE_MIN_TEXT_CHARS="${HG_CANONICAL_RESPONSE_CACHE_MIN_TEXT_CHARS:-80}"
HG_LOCAL_ACK_TELEMETRY="${HG_LOCAL_ACK_TELEMETRY:-1}"
HG_LOCAL_ACK_TELEMETRY_MAX_BODY_BYTES="${HG_LOCAL_ACK_TELEMETRY_MAX_BODY_BYTES:-1048576}"
HG_UPSTREAM_INFERENCE_MODE="${HG_UPSTREAM_INFERENCE_MODE:-cache-first}"
HG_BINARY_FAIL_OPEN="${HG_BINARY_FAIL_OPEN:-1}"
HG_BINARY_FAIL_OPEN_BYTES="${HG_BINARY_FAIL_OPEN_BYTES:-65536}"
HG_BINARY_FAIL_OPEN_CONCURRENT="${HG_BINARY_FAIL_OPEN_CONCURRENT:-2}"
HG_QUOTA_PROBE="${HG_QUOTA_PROBE:-0}"
HG_BILLING_GUARD="${HG_BILLING_GUARD:-0}"
HG_BILLING_GUARD_WINDOW_SECONDS="${HG_BILLING_GUARD_WINDOW_SECONDS:-60}"
HG_BILLING_GUARD_MAX_INFERENCE="${HG_BILLING_GUARD_MAX_INFERENCE:-3}"
HG_BILLING_GUARD_MODE="${HG_BILLING_GUARD_MODE:-queue}"
HG_BILLING_GUARD_MAX_WAIT_SECONDS="${HG_BILLING_GUARD_MAX_WAIT_SECONDS:-90}"
HG_PEGASUS_SWARM_TRIGGER="${HG_PEGASUS_SWARM_TRIGGER:-1}"
HG_PEGASUS_SWARM_HOT_PATH="${HG_PEGASUS_SWARM_HOT_PATH:-0}"
HG_PEGASUS_SWARM_TRIGGER_LEVELS="${HG_PEGASUS_SWARM_TRIGGER_LEVELS:-high,xhigh}"
HG_PEGASUS_SWARM_COOLDOWN_SECONDS="${HG_PEGASUS_SWARM_COOLDOWN_SECONDS:-90}"
HG_PEGASUS_MAX_ACTIVE_AGENTS="${HG_PEGASUS_MAX_ACTIVE_AGENTS:-3}"
HG_PEGASUS_AGENT_MAX_SECONDS="${HG_PEGASUS_AGENT_MAX_SECONDS:-900}"
HG_MICROPROXY_FRONT_LISTEN="${HG_MICROPROXY_FRONT_LISTEN:-0.0.0.0:443}"
HG_MICROPROXY_FRONT_UPSTREAM="${HG_MICROPROXY_FRONT_UPSTREAM:-127.0.0.1:${HG_PROXY_INTERNAL_HTTPS_PORT}}"
HG_MICROPROXY_FRONT_IDLE_TIMEOUT="${HG_MICROPROXY_FRONT_IDLE_TIMEOUT:-180}"
HG_MICROPROXY_FRONT_MAX_STREAM_SECONDS="${HG_MICROPROXY_FRONT_MAX_STREAM_SECONDS:-600}"
HG_MICROPROXY_FRONT_MAX_ACTIVE_STREAMS="${HG_MICROPROXY_FRONT_MAX_ACTIVE_STREAMS:-96}"
HG_EGRESS_SHIELD="${HG_EGRESS_SHIELD:-1}"
HG_UPSTREAM_TOTAL_TIMEOUT_SECONDS="${HG_UPSTREAM_TOTAL_TIMEOUT_SECONDS:-900}"
HG_UPSTREAM_CONNECT_TIMEOUT_SECONDS="${HG_UPSTREAM_CONNECT_TIMEOUT_SECONDS:-15}"
HG_UPSTREAM_READ_TIMEOUT_SECONDS="${HG_UPSTREAM_READ_TIMEOUT_SECONDS:-900}"
HG_MICROPROXY_FRONT_PID="$SCRIPT_DIR/logs/microproxy_front.pid"
HG_MICROPROXY_FRONT_LOG="$SCRIPT_DIR/logs/microproxy_front.log"
HG_MICROPROXY_FRONT_EVENTS="$SCRIPT_DIR/logs/microproxy_events.jsonl"
PROXY_PYTHON_BIN="$SCRIPT_DIR/.hg_proxy_venv/bin/python"
if [ ! -x "$PROXY_PYTHON_BIN" ]; then
    PROXY_PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
fi
if [ ! -x "$PROXY_PYTHON_BIN" ]; then
    PROXY_PYTHON_BIN="$(command -v python3)"
fi
TARGET_USER="${SUDO_USER:-$(whoami)}"
TARGET_HOME="$(eval echo "~${TARGET_USER}")"
HG_CA_CERT="$SCRIPT_DIR/certs/proxy.ca.crt"
HG_SYSTEM_CA="/usr/local/share/ca-certificates/hg-proxy.crt"
HG_WINDSURF_WRAPPER="/usr/local/bin/hg-windsurf-next"
PY_MAJOR_MINOR="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"

# ─── ANSI codes ──────────────────────────────────────────────────────
ESC=$'\033'
G="${ESC}[32m"; R="${ESC}[31m"; Y="${ESC}[33m"; B="${ESC}[34m"
C="${ESC}[36m"; M="${ESC}[35m"; W="${ESC}[97m"; D="${ESC}[2m"
BG="${ESC}[44m"; BOLD="${ESC}[1m"; INV="${ESC}[7m"; NC="${ESC}[0m"
HIDE="${ESC}[?25l"; SHOW="${ESC}[?25h"; CLR="${ESC}[2J${ESC}[H"

check_port() {
    ss -ltn "( sport = :$1 )" 2>/dev/null | tail -n +2 | grep -q ":$1 "
}
is_khoj_healthy() {
    curl -fsS --max-time 3 http://127.0.0.1:42110/api/health >/dev/null 2>&1
}
iptables_active() {
    echo "$SUDO_PASS" | sudo -S iptables -t nat -C OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998 >/dev/null 2>&1
}
pidfile_read() {
    local pidfile="$1"
    [ -f "$pidfile" ] || return 1
    tr -d '[:space:]' < "$pidfile"
}
pidfile_alive() {
    local pidfile="$1"
    local pid
    pid="$(pidfile_read "$pidfile" 2>/dev/null)" || return 1
    [ -n "$pid" ] && ps -p "$pid" -o pid= >/dev/null 2>&1
}
wait_for_port() {
    local port="$1"
    local attempts="${2:-15}"
    local delay="${3:-1}"
    local i
    for ((i = 1; i <= attempts; i++)); do
        if check_port "$port"; then
            return 0
        fi
        sleep "$delay"
    done
    return 1
}

rotate_log_if_large() {
    local logfile="$1"
    local max_bytes="${2:-10485760}"
    local keep_count="${3:-5}"
    local size
    [ -f "$logfile" ] || return 0
    size=$(wc -c < "$logfile" 2>/dev/null || echo 0)
    [ "$size" -lt "$max_bytes" ] && return 0

    local i
    for ((i = keep_count; i >= 1; i--)); do
        if [ -f "${logfile}.${i}" ]; then
            if [ "$i" -eq "$keep_count" ]; then
                rm -f "${logfile}.${i}"
            else
                mv "${logfile}.${i}" "${logfile}.$((i + 1))"
            fi
        fi
    done
    mv "$logfile" "${logfile}.1"
}

# ─── draw menu ───────────────────────────────────────────────────────
ITEMS=(
    "Patch               apply all patches"
    "Repatch (clean)     stop > restore > repatch"
    "Undo                restore files; keep hosts"
    "Start all           patch + proxy + Windsurf"
    "C proxy mode        restart proxy only with selected inference mode"
    "Dashboard           rich TUI monitor"
    "Verify              services + patch status"
    "Quit"
)
SEL=0

draw_menu() {
    printf "${CLR}"
    printf "${C}${BOLD}"
    printf "  ╔══════════════════════════════════════════════════════╗\n"
    printf "  ║           HIGH-GRAVITY  BOOTSTRAP  v3.0             ║\n"
    printf "  ╚══════════════════════════════════════════════════════╝\n"
    printf "${NC}\n"

    # Quick status bar
    local p_s k_s w_s
    check_port 9998 && p_s="${G}ON${NC}" || p_s="${R}OFF${NC}"
    curl -s http://127.0.0.1:42110/api/health >/dev/null 2>&1 && k_s="${G}ON${NC}" || k_s="${D}OFF${NC}"
    pgrep -f "windsurf" >/dev/null 2>&1 && w_s="${G}ON${NC}" || w_s="${D}OFF${NC}"
    printf "  ${D}Proxy:${NC} $p_s  ${D}Khoj:${NC} $k_s  ${D}Windsurf:${NC} $w_s\n\n"

    local i=0
    for item in "${ITEMS[@]}"; do
        local label="${item%%  *}"
        local desc="${item#*  }"
        if [ $i -eq $SEL ]; then
            printf "  ${INV}${C} > %-24s ${D}%s ${NC}\n" "$label" "$desc"
        else
            printf "    ${W}%-24s ${D}%s${NC}\n" "$label" "$desc"
        fi
        i=$((i+1))
    done

    printf "\n  ${D}↑↓ / 1-7 to select  •  0 = repatch+start  •  q quit${NC}\n"
}

read_key() {
    local key
    IFS= read -rsn1 key
    if [[ "$key" == "$ESC" ]]; then
        read -rsn2 -t 0.1 key
        case "$key" in
            '[A') echo "UP" ;;
            '[B') echo "DOWN" ;;
            *)    echo "ESC" ;;
        esac
    elif [[ "$key" == "" ]]; then
        echo "ENTER"
    elif [[ "$key" == "q" || "$key" == "Q" ]]; then
        echo "QUIT"
    elif [[ "$key" =~ [1-8] ]]; then
        echo "NUM$key"
    else
        echo "OTHER"
    fi
}

# ─── pause helper ────────────────────────────────────────────────────
pause() {
    if [ "${HG_NON_INTERACTIVE:-0}" = "1" ]; then
        return
    fi
    echo ""
    echo -e "  ${D}Press any key to return...${NC}"
    read -rsn1
}

# ─── core operations ─────────────────────────────────────────────────
do_patch() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Applying all patches...${NC}\n"

    # Check backups first — warn but don't block (patch may still be safe)
    echo -e "${B}  [*] Verifying clean backups...${NC}"
    python3 src/patch_all.py --check-backups 2>&1 | grep -E '✓|✗|tainted|missing|MISSING|clean' | sed 's/^/  /'
    echo ""

    python3 src/patch_all.py --force 2>&1 | sed 's/^/  /'

    echo -e "${G}  Done. Restart Windsurf to apply.${NC}"
    pause
}

do_repatch() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Re-patch from clean backup...${NC}\n"
    echo -e "${Y}  This will: stop Windsurf, restore binary, re-patch all layers.${NC}\n"

    # Check backups — abort if not clean
    echo -e "${B}  [*] Checking clean backups exist...${NC}"
    local bak_out
    bak_out=$(python3 src/patch_all.py --check-backups 2>&1)
    echo "$bak_out" | sed 's/^/  /'
    if ! echo "$bak_out" | grep -q 'All backups are clean'; then
        echo -e "${R}  [!] Not all backups are clean — cannot repatch safely.${NC}"
        echo -e "${Y}      Reinstall Windsurf or place clean .original files manually.${NC}"
        pause; return
    fi

    # Kill Windsurf
    echo -e "${B}  [*] Stopping Windsurf...${NC}"
    echo "$SUDO_PASS" | sudo -S pkill -f windsurf-next 2>/dev/null || true
    sleep 2
    if pgrep -f windsurf-next >/dev/null 2>&1; then
        echo -e "${R}  [!] Windsurf still running — kill it manually first.${NC}"
        pause; return
    fi
    echo -e "${G}  [+] Windsurf stopped${NC}"

    # Restore all layers
    echo -e "${B}  [*] Restoring all patched files...${NC}"
    python3 src/patch_all.py --restore 2>&1 | sed 's/^/  /'

    # Patch all
    echo -e "${B}  [*] Patching all layers...${NC}"
    python3 src/patch_all.py --force 2>&1 | sed 's/^/  /'

    # Verify
    echo ""
    python3 src/patch_all.py --verify 2>&1 | grep -E '✓|✗|OK|FAIL|Binary|JS|Workbench|hosts|iptables' | sed 's/^/  /'

    echo -e "\n${G}  Done. Restart Windsurf:${NC}"
    echo -e "  ${D}/usr/share/windsurf-next/windsurf-next &${NC}"
    pause
}

do_undo() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Undoing all patches...${NC}\n"

    echo -e "${B}  [0/3] Removing LSP shield if active...${NC}"
    "$SCRIPT_DIR/scripts/internal/deploy_lsp_shim.sh" --undo >/tmp/hg_lsp_undo.log 2>&1 || true
    sed 's/^/  /' /tmp/hg_lsp_undo.log | tail -n 20

    echo -e "${B}  [1/3] Restoring files from backups...${NC}"
    python3 src/patch_all.py --restore 2>&1 | sed 's/^/  /'
    echo ""

    echo -e "${B}  [2/3] Preserving redirected /etc/hosts domains${NC}"
    echo -e "  ${G}[+] Hosts left intact for local HTTPS routing${NC}"
    echo -e "${B}  [3/3] LSP shield cleanup complete${NC}"
    echo ""

    echo -e "${G}  File patches undone. Redirected domains remain active.${NC}"
    pause
}

_start_proxy_http() {
    mkdir -p logs
    local root_cmd
    local khoj_token="${HG_KHOJ_TOKEN:-}"
    root_cmd="cd \"$SCRIPT_DIR\" || exit 1; export PYTHONNOUSERSITE=1 PYTHONPATH=\"$SCRIPT_DIR\" HG_KHOJ_ENABLED=true HG_KHOJ_TOKEN=\"$khoj_token\" HG_KHOJ_BINARY_INJECT=\"$HG_KHOJ_BINARY_INJECT\" HG_KHOJ_BINARY_INLINE_TIMEOUT_SECONDS=\"$HG_KHOJ_BINARY_INLINE_TIMEOUT_SECONDS\" HG_BINARY_REASONING_INJECT_MAX_BYTES=\"$HG_BINARY_REASONING_INJECT_MAX_BYTES\" HG_EXACT_RESPONSE_CACHE=\"$HG_EXACT_RESPONSE_CACHE\" HG_EXACT_RESPONSE_CACHE_TTL_SECONDS=\"$HG_EXACT_RESPONSE_CACHE_TTL_SECONDS\" HG_EXACT_RESPONSE_CACHE_MAX_ENTRIES=\"$HG_EXACT_RESPONSE_CACHE_MAX_ENTRIES\" HG_EXACT_RESPONSE_CACHE_MAX_BODY_BYTES=\"$HG_EXACT_RESPONSE_CACHE_MAX_BODY_BYTES\" HG_CANONICAL_RESPONSE_CACHE=\"$HG_CANONICAL_RESPONSE_CACHE\" HG_CANONICAL_RESPONSE_CACHE_MIN_TEXT_CHARS=\"$HG_CANONICAL_RESPONSE_CACHE_MIN_TEXT_CHARS\" HG_LOCAL_ACK_TELEMETRY=\"$HG_LOCAL_ACK_TELEMETRY\" HG_LOCAL_ACK_TELEMETRY_MAX_BODY_BYTES=\"$HG_LOCAL_ACK_TELEMETRY_MAX_BODY_BYTES\" HG_UPSTREAM_INFERENCE_MODE=\"$HG_UPSTREAM_INFERENCE_MODE\" HG_BINARY_FAIL_OPEN=\"$HG_BINARY_FAIL_OPEN\" HG_BINARY_FAIL_OPEN_BYTES=\"$HG_BINARY_FAIL_OPEN_BYTES\" HG_BINARY_FAIL_OPEN_CONCURRENT=\"$HG_BINARY_FAIL_OPEN_CONCURRENT\" HG_UPSTREAM_TOTAL_TIMEOUT_SECONDS=\"$HG_UPSTREAM_TOTAL_TIMEOUT_SECONDS\" HG_UPSTREAM_CONNECT_TIMEOUT_SECONDS=\"$HG_UPSTREAM_CONNECT_TIMEOUT_SECONDS\" HG_UPSTREAM_READ_TIMEOUT_SECONDS=\"$HG_UPSTREAM_READ_TIMEOUT_SECONDS\" HG_QUOTA_PROBE=\"$HG_QUOTA_PROBE\" HG_BILLING_GUARD=\"$HG_BILLING_GUARD\" HG_BILLING_GUARD_WINDOW_SECONDS=\"$HG_BILLING_GUARD_WINDOW_SECONDS\" HG_BILLING_GUARD_MAX_INFERENCE=\"$HG_BILLING_GUARD_MAX_INFERENCE\" HG_BILLING_GUARD_MODE=\"$HG_BILLING_GUARD_MODE\" HG_BILLING_GUARD_MAX_WAIT_SECONDS=\"$HG_BILLING_GUARD_MAX_WAIT_SECONDS\" HG_PEGASUS_SWARM_TRIGGER=\"$HG_PEGASUS_SWARM_TRIGGER\" HG_PEGASUS_SWARM_HOT_PATH=\"$HG_PEGASUS_SWARM_HOT_PATH\" HG_PEGASUS_SWARM_TRIGGER_LEVELS=\"$HG_PEGASUS_SWARM_TRIGGER_LEVELS\" HG_PEGASUS_SWARM_COOLDOWN_SECONDS=\"$HG_PEGASUS_SWARM_COOLDOWN_SECONDS\" HG_PEGASUS_MAX_ACTIVE_AGENTS=\"$HG_PEGASUS_MAX_ACTIVE_AGENTS\" HG_PEGASUS_AGENT_MAX_SECONDS=\"$HG_PEGASUS_AGENT_MAX_SECONDS\"; nohup \"$PROXY_PYTHON_BIN\" \"$SCRIPT_DIR/src/proxy.py\" >> \"$SCRIPT_DIR/logs/proxy.log\" 2>&1 & echo \$! > \"$SCRIPT_DIR/logs/proxy.pid\"; chown $USER:$USER \"$SCRIPT_DIR/logs/proxy.pid\" \"$SCRIPT_DIR/logs/proxy.log\""
    echo "$SUDO_PASS" | sudo -S bash -c "$root_cmd"
}

_start_proxy_https() {
    mkdir -p logs
    local root_cmd
    local khoj_token="${HG_KHOJ_TOKEN:-}"
    root_cmd="cd \"$SCRIPT_DIR\" || exit 1; export PYTHONNOUSERSITE=1 PYTHONPATH=\"$SCRIPT_DIR\" HG_KHOJ_ENABLED=true HG_KHOJ_TOKEN=\"$khoj_token\" HG_KHOJ_BINARY_INJECT=\"$HG_KHOJ_BINARY_INJECT\" HG_KHOJ_BINARY_INLINE_TIMEOUT_SECONDS=\"$HG_KHOJ_BINARY_INLINE_TIMEOUT_SECONDS\" HG_BINARY_REASONING_INJECT_MAX_BYTES=\"$HG_BINARY_REASONING_INJECT_MAX_BYTES\" HG_EXACT_RESPONSE_CACHE=\"$HG_EXACT_RESPONSE_CACHE\" HG_EXACT_RESPONSE_CACHE_TTL_SECONDS=\"$HG_EXACT_RESPONSE_CACHE_TTL_SECONDS\" HG_EXACT_RESPONSE_CACHE_MAX_ENTRIES=\"$HG_EXACT_RESPONSE_CACHE_MAX_ENTRIES\" HG_EXACT_RESPONSE_CACHE_MAX_BODY_BYTES=\"$HG_EXACT_RESPONSE_CACHE_MAX_BODY_BYTES\" HG_CANONICAL_RESPONSE_CACHE=\"$HG_CANONICAL_RESPONSE_CACHE\" HG_CANONICAL_RESPONSE_CACHE_MIN_TEXT_CHARS=\"$HG_CANONICAL_RESPONSE_CACHE_MIN_TEXT_CHARS\" HG_LOCAL_ACK_TELEMETRY=\"$HG_LOCAL_ACK_TELEMETRY\" HG_LOCAL_ACK_TELEMETRY_MAX_BODY_BYTES=\"$HG_LOCAL_ACK_TELEMETRY_MAX_BODY_BYTES\" HG_UPSTREAM_INFERENCE_MODE=\"$HG_UPSTREAM_INFERENCE_MODE\" HG_BINARY_FAIL_OPEN=\"$HG_BINARY_FAIL_OPEN\" HG_BINARY_FAIL_OPEN_BYTES=\"$HG_BINARY_FAIL_OPEN_BYTES\" HG_BINARY_FAIL_OPEN_CONCURRENT=\"$HG_BINARY_FAIL_OPEN_CONCURRENT\" HG_UPSTREAM_TOTAL_TIMEOUT_SECONDS=\"$HG_UPSTREAM_TOTAL_TIMEOUT_SECONDS\" HG_UPSTREAM_CONNECT_TIMEOUT_SECONDS=\"$HG_UPSTREAM_CONNECT_TIMEOUT_SECONDS\" HG_UPSTREAM_READ_TIMEOUT_SECONDS=\"$HG_UPSTREAM_READ_TIMEOUT_SECONDS\" HG_QUOTA_PROBE=\"$HG_QUOTA_PROBE\" HG_BILLING_GUARD=\"$HG_BILLING_GUARD\" HG_BILLING_GUARD_WINDOW_SECONDS=\"$HG_BILLING_GUARD_WINDOW_SECONDS\" HG_BILLING_GUARD_MAX_INFERENCE=\"$HG_BILLING_GUARD_MAX_INFERENCE\" HG_BILLING_GUARD_MODE=\"$HG_BILLING_GUARD_MODE\" HG_BILLING_GUARD_MAX_WAIT_SECONDS=\"$HG_BILLING_GUARD_MAX_WAIT_SECONDS\" HG_PEGASUS_SWARM_TRIGGER=\"$HG_PEGASUS_SWARM_TRIGGER\" HG_PEGASUS_SWARM_HOT_PATH=\"$HG_PEGASUS_SWARM_HOT_PATH\" HG_PEGASUS_SWARM_TRIGGER_LEVELS=\"$HG_PEGASUS_SWARM_TRIGGER_LEVELS\" HG_PEGASUS_SWARM_COOLDOWN_SECONDS=\"$HG_PEGASUS_SWARM_COOLDOWN_SECONDS\" HG_PEGASUS_MAX_ACTIVE_AGENTS=\"$HG_PEGASUS_MAX_ACTIVE_AGENTS\" HG_PEGASUS_AGENT_MAX_SECONDS=\"$HG_PEGASUS_AGENT_MAX_SECONDS\" HG_PROXY_HTTPS_PORT=\"$HG_PROXY_HTTPS_PORT\"; nohup \"$PROXY_PYTHON_BIN\" \"$SCRIPT_DIR/src/proxy.py\" --https >> \"$SCRIPT_DIR/logs/proxy_https.log\" 2>&1 & echo \$! > \"$SCRIPT_DIR/logs/proxy_https.pid\"; chown $USER:$USER \"$SCRIPT_DIR/logs/proxy_https.pid\" \"$SCRIPT_DIR/logs/proxy_https.log\""
    echo "$SUDO_PASS" | sudo -S bash -c "$root_cmd"
}

_microproxy_front_enabled() {
    [ "$HG_MICROPROXY_FRONT" = "1" ] || [ "$HG_MICROPROXY_FRONT" = "true" ]
}

_microproxy_direct_enabled() {
    [ -n "${HG_MICROPROXY_DIRECT_UPSTREAM:-}" ]
}

_microproxy_direct_hot_enabled() {
    case "${HG_MICROPROXY_DIRECT_HOT_PATH:-0}" in
        1|true|TRUE|yes|YES|on|ON) return 0 ;;
    esac
    return 1
}

_microproxy_direct_banner() {
    if _microproxy_direct_enabled; then
        if _microproxy_direct_hot_enabled; then
            echo -e "${B}  [*] Direct fast-path configured: ${HG_MICROPROXY_DIRECT_UPSTREAM} (hot-path enabled)${NC}"
        else
            echo -e "${B}  [*] Direct fast-path configured: ${HG_MICROPROXY_DIRECT_UPSTREAM} (hot-path disabled)${NC}"
        fi
    else
        echo -e "${D}  [~] Direct fast-path disabled${NC}"
    fi
}

_start_microproxy_front() {
    local bin="$SCRIPT_DIR/src/microproxy/build/hg-edge"
    local root_cmd
    local hot_path_arg=""
    local direct_args=""

    if [ ! -f "$SCRIPT_DIR/src/microproxy/Makefile" ]; then
        echo -e "${Y}  [~] Microproxy source missing; C front disabled${NC}"
        return 1
    fi

    echo -e "${B}  [*] Building C microproxy front${NC}"
    if ! make -C "$SCRIPT_DIR/src/microproxy" >/tmp/hg_microproxy_build.log 2>&1; then
        echo -e "${R}  [-] C microproxy build failed${NC}"
        tail -20 /tmp/hg_microproxy_build.log | sed 's/^/      /'
        return 1
    fi

    if [ ! -x "$bin" ]; then
        echo -e "${R}  [-] C microproxy binary missing after build: $bin${NC}"
        return 1
    fi

    rotate_log_if_large "$HG_MICROPROXY_FRONT_LOG" 10485760 5
    case "${HG_MICROPROXY_HOT_PATH_OBSERVE:-1}" in
        1|true|TRUE|yes|YES|on|ON) hot_path_arg=" --hot-path-observe" ;;
    esac
    if [ -n "${HG_MICROPROXY_DIRECT_UPSTREAM:-}" ]; then
        direct_args=" --direct-upstream \"${HG_MICROPROXY_DIRECT_UPSTREAM}\""
        case "${HG_MICROPROXY_DIRECT_HOT_PATH:-0}" in
            1|true|TRUE|yes|YES|on|ON) direct_args="$direct_args --direct-hot-path" ;;
        esac
    fi
    root_cmd="cd \"$SCRIPT_DIR\" || exit 1; nohup \"$bin\" --relay --listen \"$HG_MICROPROXY_FRONT_LISTEN\" --upstream \"$HG_MICROPROXY_FRONT_UPSTREAM\"$direct_args --idle-timeout \"${HG_MICROPROXY_FRONT_IDLE_TIMEOUT}\" --max-stream-seconds \"${HG_MICROPROXY_FRONT_MAX_STREAM_SECONDS}\" --max-active-streams \"${HG_MICROPROXY_FRONT_MAX_ACTIVE_STREAMS}\" --event-log \"$HG_MICROPROXY_FRONT_EVENTS\"$hot_path_arg >> \"$HG_MICROPROXY_FRONT_LOG\" 2>&1 & echo \$! > \"$HG_MICROPROXY_FRONT_PID\"; chown $USER:$USER \"$HG_MICROPROXY_FRONT_PID\" \"$HG_MICROPROXY_FRONT_LOG\" \"$HG_MICROPROXY_FRONT_EVENTS\" 2>/dev/null || true"
    echo "$SUDO_PASS" | sudo -S bash -c "$root_cmd"
}

_start_khoj_async() {
    mkdir -p logs
    local launcher="$SCRIPT_DIR/scripts/internal/khoj_docker.sh"
    local pidfile="$SCRIPT_DIR/logs/khoj_docker.pid"
    local logfile="$SCRIPT_DIR/logs/khoj_docker.log"

    if pidfile_alive "$pidfile"; then
        if is_khoj_healthy || docker ps --format '{{.Names}}' | grep -qx "khoj"; then
            return 0
        fi
        local old_pid
        old_pid="$(pidfile_read "$pidfile" 2>/dev/null || true)"
        [ -n "$old_pid" ] && kill "$old_pid" 2>/dev/null || true
        rm -f "$pidfile"
    fi

    if [ -f "$launcher" ]; then
        rotate_log_if_large "$logfile" 10485760 5
        nohup bash "$launcher" >> "$logfile" 2>&1 &
        echo "$SUDO_PASS" | sudo -S bash -c "echo $! > \"$pidfile\" && chown $USER:$USER \"$pidfile\""
    fi
}

_ensure_lsp_shim() {
    local mode="${HG_PROXY_MODE}"
    if [ "${HG_ENFORCE_SHIM:-1}" != "1" ]; then
        return 0
    fi

    if [ "$mode" != "full" ] && [ "$mode" != "inference-only" ]; then
        echo -e "${Y}  [~] Unsupported HG_PROXY_MODE '$mode', falling back to full${NC}"
        mode="full"
    fi

    echo -e "${B}  [*] Enforcing LSP shield (mode=${mode})${NC}"
    HG_PROXY_MODE="$mode" bash "$SCRIPT_DIR/scripts/internal/deploy_lsp_shim.sh" --mode "$mode"
}

_stop_windsurf() {
    echo -e "${B}  [*] Stopping Windsurf...${NC}"
    echo "$SUDO_PASS" | sudo -S pkill -f "language_server_linux_x64.real" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "windsurf-next --new-window" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "/usr/share/windsurf-next/windsurf-next" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "codeium.windsurf" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "/extensions/windsurf/devin/bin/devin acp" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "/extensions/windsurf/devin/bin/devin summarizer" 2>/dev/null || true
    sleep 2
    if pgrep -f "language_server_linux_x64.real\|windsurf-next --new-window\|codeium.windsurf\|/extensions/windsurf/devin/bin/devin acp" >/dev/null 2>&1; then
        echo -e "${Y}  [~] Windsurf still present after stop attempt${NC}"
    else
        echo -e "${G}  [+] Windsurf stopped${NC}"
    fi
}

_install_proxy_ca() {
    if [ ! -f "$HG_CA_CERT" ]; then
        echo -e "${Y}  [~] CA cert missing: $HG_CA_CERT${NC}"
        return 1
    fi

    echo -e "${B}  [*] Installing HIGH-GRAVITY CA into trust stores${NC}"
    if [ -f "$HG_SYSTEM_CA" ] && cmp -s "$HG_CA_CERT" "$HG_SYSTEM_CA"; then
        echo -e "${D}  [~] CA already installed${NC}"
    else
        echo "$SUDO_PASS" | sudo -S cp "$HG_CA_CERT" "$HG_SYSTEM_CA"
        echo "$SUDO_PASS" | sudo -S chmod 0644 "$HG_SYSTEM_CA"
        if command -v timeout >/dev/null 2>&1; then
            echo "$SUDO_PASS" | sudo -S timeout 20 update-ca-certificates 2>/dev/null | tail -1 | sed 's/^/  /'
        else
            echo "$SUDO_PASS" | sudo -S update-ca-certificates 2>/dev/null | tail -1 | sed 's/^/  /'
        fi
    fi

    if [ -x "scripts/internal/update_nss.sh" ]; then
        echo "$SUDO_PASS" | sudo -S -u "$TARGET_USER" env HOME="$TARGET_HOME" bash scripts/internal/update_nss.sh >/dev/null 2>&1 || true
    fi
}

_install_windsurf_wrapper() {
    local wrapper_src="$SCRIPT_DIR/scripts/internal/hg_windsurf_next.sh"
    if [ -f "$wrapper_src" ]; then
        echo "$SUDO_PASS" | sudo -S install -m 0755 "$wrapper_src" "$HG_WINDSURF_WRAPPER"
        echo "$SUDO_PASS" | sudo -S sed -i \
            -e "s|^Exec=/usr/share/windsurf-next/windsurf-next --open-url %U|Exec=$HG_WINDSURF_WRAPPER --open-url %U|" \
            -e "s|^Exec=/usr/share/windsurf-next/windsurf-next --new-window %F|Exec=$HG_WINDSURF_WRAPPER --new-window %F|" \
            -e "s|^Exec=/usr/share/windsurf-next/windsurf-next %F|Exec=$HG_WINDSURF_WRAPPER %F|" \
            /usr/share/applications/windsurf-next.desktop \
            /usr/share/applications/windsurf-next-url-handler.desktop 2>/dev/null || true
        command -v update-desktop-database >/dev/null 2>&1 \
            && echo "$SUDO_PASS" | sudo -S update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
    fi
}

_launch_windsurf() {
    local launcher="$SCRIPT_DIR/bin/gemini_session_launcher.py"
    if [ ! -f "$launcher" ]; then
        echo -e "${Y}  [~] Windsurf launcher not found (${launcher})${NC}"
        return 0
    fi
    if [ ! -f "$SCRIPT_DIR/config/gemini_keys.json" ]; then
        echo -e "${Y}  [~] config/gemini_keys.json missing; skipping Windsurf launch${NC}"
        return 0
    fi

    echo -e "${B}  [*] Launching Windsurf editor${NC}"
    # Use sudo -u to launch as the regular user (Electron refuses to run as root)
    # NODE_EXTRA_CA_CERTS is required for the Node extension host HTTP/2 client.
    nohup sudo -u "$TARGET_USER" env HOME="$TARGET_HOME" "$HG_WINDSURF_WRAPPER" > "$SCRIPT_DIR/logs/windsurf_launch.log" 2>&1 &
    echo $! > "$SCRIPT_DIR/logs/windsurf_launch.pid"

    local i
    for ((i = 1; i <= 20; i++)); do
        if pgrep -f "/usr/share/windsurf-next/windsurf-next" >/dev/null 2>&1 || \
           pgrep -f "windsurf-next --new-window" >/dev/null 2>&1; then
            echo -e "${G}  [+] Windsurf launch requested${NC}"
            return 0
        fi
        sleep 1
    done

    echo -e "${Y}  [~] Windsurf launch requested but not yet visible${NC}"
    return 0
}

_watchdog_khoj() {
    echo "$(date): khoj watchdog started pid=$$" >> "$SCRIPT_DIR/logs/khoj_watchdog.log"
    while true; do
        sleep 15
        is_khoj_healthy && continue
        if docker ps --format '{{.Names}}' | grep -qx "khoj"; then
            continue
        fi
        echo "$(date): khoj health down, restarting docker launcher" >> "$SCRIPT_DIR/logs/khoj_watchdog.log"
        _start_khoj_async
    done
}

_watchdog_proxy() {
    # Background watchdog: restart HTTP/HTTPS proxies if they die
    echo "$(date): proxy watchdog started pid=$$ mode=${HG_UPSTREAM_INFERENCE_MODE:-unknown}" >> "$SCRIPT_DIR/logs/proxy_watchdog.log"
    while true; do
        sleep 10
        if ! check_port 9998; then
            if pidfile_alive "$SCRIPT_DIR/logs/proxy.pid"; then
                echo "$(date): http proxy port down but process still alive; waiting" >> "$SCRIPT_DIR/logs/proxy_watchdog.log"
            else
                echo "$(date): http proxy down, restarting" >> "$SCRIPT_DIR/logs/proxy_watchdog.log"
                _start_proxy_http
            fi
        fi
        if [ -f "$SCRIPT_DIR/certs/proxy.crt" ] && [ -f "$SCRIPT_DIR/certs/proxy.key" ]; then
            local tls_port="$HG_PROXY_HTTPS_PORT"
            _microproxy_front_enabled && tls_port="$HG_PROXY_INTERNAL_HTTPS_PORT"
            if ! check_port "$tls_port"; then
                if pidfile_alive "$SCRIPT_DIR/logs/proxy_https.pid"; then
                    echo "$(date): https proxy port down but process still alive; waiting" >> "$SCRIPT_DIR/logs/proxy_watchdog.log"
                else
                    echo "$(date): https proxy down, restarting" >> "$SCRIPT_DIR/logs/proxy_watchdog.log"
                    _start_proxy_https
                fi
            fi
            if _microproxy_front_enabled && ! check_port 443; then
                if pidfile_alive "$HG_MICROPROXY_FRONT_PID"; then
                    echo "$(date): microproxy front port down but process still alive; waiting" >> "$SCRIPT_DIR/logs/proxy_watchdog.log"
                else
                    echo "$(date): microproxy front down, restarting" >> "$SCRIPT_DIR/logs/proxy_watchdog.log"
                    _start_microproxy_front
                fi
            fi
        fi
    done
}

_launch_watchdog_processes() {
    local scope="${1:-full}"
    local pid
    local daemon_prefix=()
    if command -v setsid >/dev/null 2>&1; then
        daemon_prefix=(setsid)
    else
        daemon_prefix=(nohup)
    fi
    pid="$(pidfile_read "$SCRIPT_DIR/logs/proxy_watchdog.pid" 2>/dev/null || true)"
    if [ -n "$pid" ] && ps -p "$pid" -o pid= >/dev/null 2>&1; then
        echo "$(date): proxy watchdog already running pid=$pid" >> "$SCRIPT_DIR/logs/proxy_watchdog.log"
    else
        rm -f "$SCRIPT_DIR/logs/proxy_watchdog.pid"
        (
            export HG_START_SOURCE_ONLY=1
            export HG_MICROPROXY_FRONT HG_PROXY_HTTPS_PORT HG_PROXY_INTERNAL_HTTPS_PORT
            export HG_MICROPROXY_FRONT_LISTEN HG_MICROPROXY_FRONT_UPSTREAM
            export HG_MICROPROXY_FRONT_IDLE_TIMEOUT HG_MICROPROXY_FRONT_MAX_STREAM_SECONDS HG_MICROPROXY_FRONT_MAX_ACTIVE_STREAMS
            export HG_MICROPROXY_DIRECT_UPSTREAM HG_MICROPROXY_DIRECT_HOT_PATH
            export HG_KHOJ_BINARY_INJECT HG_KHOJ_BINARY_INLINE_TIMEOUT_SECONDS HG_BINARY_REASONING_INJECT_MAX_BYTES
            export HG_EXACT_RESPONSE_CACHE HG_EXACT_RESPONSE_CACHE_TTL_SECONDS HG_EXACT_RESPONSE_CACHE_MAX_ENTRIES HG_EXACT_RESPONSE_CACHE_MAX_BODY_BYTES
            export HG_CANONICAL_RESPONSE_CACHE HG_CANONICAL_RESPONSE_CACHE_MIN_TEXT_CHARS
            export HG_LOCAL_ACK_TELEMETRY HG_LOCAL_ACK_TELEMETRY_MAX_BODY_BYTES
            export HG_UPSTREAM_INFERENCE_MODE HG_BINARY_FAIL_OPEN HG_BINARY_FAIL_OPEN_BYTES HG_BINARY_FAIL_OPEN_CONCURRENT
            export HG_UPSTREAM_TOTAL_TIMEOUT_SECONDS HG_UPSTREAM_CONNECT_TIMEOUT_SECONDS HG_UPSTREAM_READ_TIMEOUT_SECONDS
            export HG_QUOTA_PROBE HG_BILLING_GUARD HG_BILLING_GUARD_WINDOW_SECONDS HG_BILLING_GUARD_MAX_INFERENCE HG_BILLING_GUARD_MODE HG_BILLING_GUARD_MAX_WAIT_SECONDS
            export HG_PEGASUS_SWARM_TRIGGER HG_PEGASUS_SWARM_HOT_PATH HG_PEGASUS_SWARM_TRIGGER_LEVELS HG_PEGASUS_SWARM_COOLDOWN_SECONDS
            export HG_PEGASUS_MAX_ACTIVE_AGENTS HG_PEGASUS_AGENT_MAX_SECONDS
            "${daemon_prefix[@]}" bash -c 'cd "$1" || exit 1; source scripts/internal/hg_start.sh; _watchdog_proxy' hg-proxy-watchdog "$SCRIPT_DIR" >> "$SCRIPT_DIR/logs/proxy_watchdog.log" 2>&1 &
            echo $! > "$SCRIPT_DIR/logs/proxy_watchdog.pid"
        )
        sleep 0.2
        pid="$(pidfile_read "$SCRIPT_DIR/logs/proxy_watchdog.pid" 2>/dev/null || true)"
        if [ -z "$pid" ] || ! ps -p "$pid" -o pid= >/dev/null 2>&1; then
            echo "$(date): proxy watchdog failed to stay running pid=${pid:-none}" >> "$SCRIPT_DIR/logs/proxy_watchdog.log"
            rm -f "$SCRIPT_DIR/logs/proxy_watchdog.pid"
        fi
    fi

    if [ "$scope" = "proxy-only" ] && [ "${HG_KHOJ_WATCHDOG:-0}" != "1" ]; then
        return 0
    fi

    pid="$(pidfile_read "$SCRIPT_DIR/logs/khoj_watchdog.pid" 2>/dev/null || true)"
    if [ -n "$pid" ] && ps -p "$pid" -o pid= >/dev/null 2>&1; then
        echo "$(date): khoj watchdog already running pid=$pid" >> "$SCRIPT_DIR/logs/khoj_watchdog.log"
        return 0
    fi
    rm -f "$SCRIPT_DIR/logs/khoj_watchdog.pid"
    "${daemon_prefix[@]}" env HG_START_SOURCE_ONLY=1 bash -c 'cd "$1" || exit 1; source scripts/internal/hg_start.sh; _watchdog_khoj' hg-khoj-watchdog "$SCRIPT_DIR" >> "$SCRIPT_DIR/logs/khoj_watchdog.log" 2>&1 &
    echo $! > "$SCRIPT_DIR/logs/khoj_watchdog.pid"
    sleep 0.2
    pid="$(pidfile_read "$SCRIPT_DIR/logs/khoj_watchdog.pid" 2>/dev/null || true)"
    if [ -z "$pid" ] || ! ps -p "$pid" -o pid= >/dev/null 2>&1; then
        echo "$(date): khoj watchdog failed to stay running pid=${pid:-none}" >> "$SCRIPT_DIR/logs/khoj_watchdog.log"
        rm -f "$SCRIPT_DIR/logs/khoj_watchdog.pid"
    fi
}

do_start_proxy() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Starting proxy stack only...${NC}\n"

    # ── Kill old proxy-only instances ───────────────────────────────
    echo -e "${B}  [*] Stopping old proxy components${NC}"
    local pidfile pid
    for pidfile in logs/proxy.pid logs/proxy_https.pid logs/microproxy_front.pid logs/proxy_watchdog.pid; do
        pid="$(pidfile_read "$pidfile" 2>/dev/null || true)"
        if [ -n "$pid" ]; then
            echo "$SUDO_PASS" | sudo -S kill "$pid" 2>/dev/null || true
            kill "$pid" 2>/dev/null || true
        fi
    done
    echo "$SUDO_PASS" | sudo -S pkill -f "src/proxy.py|src\\.proxy|highgravity_proxy.py" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "src/microproxy/build/hg-edge|hg-edge --relay" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "proxyt" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S rm -f logs/proxy.pid logs/proxy_https.pid logs/microproxy_front.pid logs/proxy_watchdog.pid 2>/dev/null || true
    sleep 1

    mkdir -p logs
    echo "$SUDO_PASS" | sudo -S chown -R "$TARGET_USER":"$TARGET_USER" logs/

    # ── iptables: redirect port 50001 → 9998 ───────────────────────
    echo "$SUDO_PASS" | sudo -S iptables -t nat -D OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S iptables -t nat -A OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998
    echo -e "${G}  [+] iptables 50001→9998 active${NC}"

    # ── HTTP proxy (always) ───────────────────────────────────────
    echo -e "${B}  [*] Starting HTTP proxy (9998)${NC}"
    _start_proxy_http
    if wait_for_port 9998 15 1; then
        echo -e "${G}  [+] HTTP proxy online (pid $(cat logs/proxy.pid 2>/dev/null))${NC}"
    else
        echo -e "${R}  [-] HTTP proxy failed — check logs/proxy.log${NC}"
        tail -5 logs/proxy.log | sed 's/^/      /'
    fi

    # ── HTTPS proxy (if certs present) ───────────────────────────
    _microproxy_direct_banner
    if [ -f "certs/proxy.crt" ] && [ -f "certs/proxy.key" ]; then
        _install_proxy_ca
        _install_windsurf_wrapper
        if _microproxy_front_enabled; then
            HG_PROXY_HTTPS_PORT="$HG_PROXY_INTERNAL_HTTPS_PORT"
            HG_MICROPROXY_FRONT_UPSTREAM="${HG_MICROPROXY_FRONT_UPSTREAM:-127.0.0.1:${HG_PROXY_INTERNAL_HTTPS_PORT}}"
            echo -e "${B}  [*] Starting Python HTTPS proxy (${HG_PROXY_HTTPS_PORT}, internal)${NC}"
        else
            HG_PROXY_HTTPS_PORT="${HG_PROXY_HTTPS_PORT:-443}"
            echo -e "${B}  [*] Starting HTTPS proxy (${HG_PROXY_HTTPS_PORT})${NC}"
        fi
        _start_proxy_https
        if ! wait_for_port "$HG_PROXY_HTTPS_PORT" 15 1; then
            echo -e "${Y}  [~] HTTPS starting (logs/proxy_https.log)${NC}"
        fi
        if _microproxy_front_enabled; then
            echo -e "${B}  [*] Starting C microproxy front (443 → ${HG_MICROPROXY_FRONT_UPSTREAM})${NC}"
            if _start_microproxy_front && wait_for_port 443 10 1; then
                echo -e "${G}  [+] C microproxy front online (443)${NC}"
            else
                echo -e "${R}  [-] C microproxy front failed; check ${HG_MICROPROXY_FRONT_LOG}${NC}"
            fi
        fi
    else
        echo -e "${D}  [~] No certs — HTTPS proxy skipped${NC}"
        echo -e "${D}     (run: bash scripts/internal/hg_start.sh from menu to generate)${NC}"
    fi

    if [ "$HG_EGRESS_SHIELD" = "1" ] || [ "$HG_EGRESS_SHIELD" = "true" ]; then
        bash "$SCRIPT_DIR/scripts/internal/hg_egress.sh" on >/tmp/hg_egress_start.log 2>&1 || true
        tail -n 1 /tmp/hg_egress_start.log | sed 's/^/  /'
    fi

    _launch_watchdog_processes proxy-only
    echo -e "${G}  [+] Proxy stack restart complete${NC}"
}

do_start() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Starting all services...${NC}\n"

    # ── Patch preflight (informational, no writes) ───────────────────
    echo -e "${B}  [*] Checking patch target compatibility${NC}"
    local preflight_log
    preflight_log="$(mktemp /tmp/hg_preflight.XXXXXX.log)"
    if python3 src/patch_all.py --preflight >"$preflight_log" 2>&1; then
        echo -e "${G}  [+] Patch preflight OK${NC}"
    else
        echo -e "${Y}  [~] Patch preflight failed (safe to run unpatched).${NC}"
        echo -e "${Y}      See: $preflight_log${NC}"
    fi

    # ── Kill old instances ────────────────────────────────────────────
    echo -e "${B}  [*] Killing old processes${NC}"
    local pidfile pid
    for pidfile in logs/proxy.pid logs/proxy_https.pid logs/microproxy_front.pid logs/proxy_watchdog.pid logs/khoj_watchdog.pid logs/khoj_docker.pid; do
        pid="$(pidfile_read "$pidfile" 2>/dev/null || true)"
        if [ -n "$pid" ]; then
            echo "$SUDO_PASS" | sudo -S kill "$pid" 2>/dev/null || true
        fi
    done
    echo "$SUDO_PASS" | sudo -S pkill -f "src/proxy.py|src\\.proxy" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "gemini_session_launcher.py" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "highgravity_proxy.py|src\\.proxy" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "src/microproxy/build/hg-edge|hg-edge --relay" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "lsp_shim" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "proxyt" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "khoj.*--port.*42110" 2>/dev/null || true
    bash scripts/internal/khoj_stop.sh >/dev/null 2>&1 || true
    docker stop khoj khoj-pg >/dev/null 2>&1 || true
    echo "$SUDO_PASS" | sudo -S rm -f logs/*.pid 2>/dev/null || true
    sleep 1
    echo -e "${G}  [+] Cleaned${NC}"

    mkdir -p logs
    echo "$SUDO_PASS" | sudo -S chown -R "$TARGET_USER":"$TARGET_USER" logs/

    # ── iptables: redirect port 50001 → 9998 (language server fallback) ──
    # Clean up existing rule to prevent duplicates before adding
    echo "$SUDO_PASS" | sudo -S iptables -t nat -D OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S iptables -t nat -A OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998
    echo -e "${G}  [+] iptables 50001→9998 active${NC}"

    # ── HTTP proxy (always) ───────────────────────────────────────────
    echo -e "${B}  [*] Starting HTTP proxy (9998)${NC}"
    _start_proxy_http
    if wait_for_port 9998 15 1; then
        echo -e "${G}  [+] HTTP proxy online (pid $(cat logs/proxy.pid 2>/dev/null))${NC}"
        _launch_watchdog_processes
    else
        echo -e "${R}  [-] HTTP proxy failed — check logs/proxy.log${NC}"
        tail -5 logs/proxy.log | sed 's/^/      /'
    fi

    # ── HTTPS proxy (if certs present) ───────────────────────────────
    _microproxy_direct_banner
    if [ -f "certs/proxy.crt" ] && [ -f "certs/proxy.key" ]; then
        _install_proxy_ca
        _install_windsurf_wrapper
        if _microproxy_front_enabled; then
            HG_PROXY_HTTPS_PORT="$HG_PROXY_INTERNAL_HTTPS_PORT"
            HG_MICROPROXY_FRONT_UPSTREAM="${HG_MICROPROXY_FRONT_UPSTREAM:-127.0.0.1:${HG_PROXY_INTERNAL_HTTPS_PORT}}"
            echo -e "${B}  [*] Starting Python HTTPS proxy (${HG_PROXY_HTTPS_PORT}, internal)${NC}"
        else
            HG_PROXY_HTTPS_PORT="${HG_PROXY_HTTPS_PORT:-443}"
            echo -e "${B}  [*] Starting HTTPS proxy (${HG_PROXY_HTTPS_PORT})${NC}"
        fi
        _start_proxy_https
        wait_for_port "$HG_PROXY_HTTPS_PORT" 15 1 \
            && echo -e "${G}  [+] HTTPS proxy online (${HG_PROXY_HTTPS_PORT})${NC}" \
            || echo -e "${Y}  [~] HTTPS starting (logs/proxy_https.log)${NC}"
        if _microproxy_front_enabled; then
            echo -e "${B}  [*] Starting C microproxy front (443 → ${HG_MICROPROXY_FRONT_UPSTREAM})${NC}"
            if _start_microproxy_front && wait_for_port 443 10 1; then
                echo -e "${G}  [+] C microproxy front online (443)${NC}"
            else
                echo -e "${R}  [-] C microproxy front failed; check ${HG_MICROPROXY_FRONT_LOG}${NC}"
        fi
    fi

    if [ "$HG_EGRESS_SHIELD" = "1" ] || [ "$HG_EGRESS_SHIELD" = "true" ]; then
        bash "$SCRIPT_DIR/scripts/internal/hg_egress.sh" on >/tmp/hg_egress_start.log 2>&1 || true
        tail -n 1 /tmp/hg_egress_start.log | sed 's/^/  /'
    fi
    else
        echo -e "${D}  [~] No certs — HTTPS proxy skipped${NC}"
        echo -e "${D}     (run: bash scripts/internal/hg_start.sh from menu to generate)${NC}"
    fi

    # ── Khoj ─────────────────────────────────────────────────────────
    if [ -f "scripts/internal/khoj_docker.sh" ]; then
        echo -e "${B}  [*] Starting Khoj (Docker, background)${NC}"
        _start_khoj_async
        if is_khoj_healthy; then
            echo -e "${G}  [+] Khoj already healthy${NC}"
            ( curl -s -X POST http://127.0.0.1:9998/hg/khoj/reindex >/dev/null 2>&1 && echo -e "\n${D}  [~] Khoj reindex triggered${NC}" ) &
        else
            echo -e "${Y}  [~] Khoj warming up in background (logs/khoj_docker.log)...${NC}"
            (
                local wait_i
                for wait_i in {1..45}; do
                    if is_khoj_healthy; then
                        curl -s -X POST http://127.0.0.1:9998/hg/khoj/reindex >/dev/null 2>&1
                        break
                    fi
                    sleep 1
                done
            ) &
        fi
    else
        echo -e "${D}  [~] scripts/internal/khoj_docker.sh not found, skipping${NC}"
    fi

    if ! _ensure_lsp_shim; then
        echo -e "${Y}  [~] Failed to enforce LSP shield; continuing startup with current routing state${NC}"
    fi

    _stop_windsurf

    # ── Windsurf app ────────────────────────────────────────────────
    _launch_windsurf

    echo ""
    do_verify_inline
    pause
}

do_verify_inline() {
    echo -e "${BOLD}${C}  Status:${NC}"
    echo -e "  ────────────────────────────────────────"

    # ── Services ─────────────────────────────────────────────────────
    check_port 9998 && echo -e "  Proxy HTTP  (9998)  ${G}UP${NC}" \
        || echo -e "  Proxy HTTP  (9998)  ${R}DOWN${NC}"
    if _microproxy_front_enabled; then
        check_port "$HG_PROXY_INTERNAL_HTTPS_PORT" && echo -e "  Proxy HTTPS  (${HG_PROXY_INTERNAL_HTTPS_PORT}) ${G}UP${NC}" \
            || echo -e "  Proxy HTTPS  (${HG_PROXY_INTERNAL_HTTPS_PORT}) ${Y}DOWN${NC}"
        check_port 443 && echo -e "  C front TLS  (443)  ${G}UP${NC}" \
            || echo -e "  C front TLS  (443)  ${Y}DOWN${NC}"
    else
        check_port 443  && echo -e "  Proxy HTTPS (443)   ${G}UP${NC}" \
            || echo -e "  Proxy HTTPS (443)   ${Y}DOWN${NC}"
    fi
    is_khoj_healthy \
        && echo -e "  Khoj        (42110) ${G}UP${NC}" \
        || echo -e "  Khoj        (42110) ${D}--${NC}"

    # ── iptables ─────────────────────────────────────────────────────
    if iptables_active; then
        echo -e "  iptables    50001→9998  ${G}ACTIVE${NC}"
    else
        echo -e "  iptables    50001→9998  ${R}MISSING${NC}"
    fi

    echo ""

    # ── Patch status ─────────────────────────────────────────────────
    python3 src/patch_all.py --verify 2>&1 \
        | grep -E 'Binary|JS|Workbench|hosts|iptables|OK|FAIL' \
        | grep -v '^  \[' \
        | sed 's/^/  /'

    # ── Windsurf process ─────────────────────────────────────────────
    echo ""
    if pgrep -f "windsurf" >/dev/null 2>&1; then
        API_URL=$(ps aux | grep language_server_linux | grep -v grep | head -1 \
            | grep -oP '\-\-api_server_url \S+' | awk '{print $2}')
        INFER_URL=$(ps aux | grep language_server_linux | grep -v grep | head -1 \
            | grep -oP '\-\-inference_api_server_url \S+' | awk '{print $2}')
        if [ -z "$API_URL" ]; then
            echo -e "  Windsurf    ${Y}running — lang server not yet spawned${NC}"
        elif echo "$API_URL" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com' && \
             echo "${INFER_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
            echo -e "  Windsurf    ${G}PROXIED${NC}  $API_URL"
            echo -e "  ${G}  proxy path active${NC}"
        elif ! echo "$API_URL" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com' && \
             echo "${INFER_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
            echo -e "  Windsurf    ${C}DIRECT split${NC}  $API_URL"
            echo -e "  ${C}  login/control-plane direct, inference proxied${NC}"
        else
            echo -e "  Windsurf    ${R}DIRECT-only${NC}   $API_URL"
            echo -e "  ${Y}  ^ reload window to pick up JS patches${NC}"
            LS_PID=$(pgrep -f "language_server_linux_x64" | head -1)
            if [ -n "$LS_PID" ]; then
                LS_AGE=$(ps -o etimes= -p "$LS_PID" 2>/dev/null | tr -d ' ')
                if [ -n "$LS_AGE" ] && [ "$LS_AGE" -gt 90 ]; then
                    echo -e "  ${Y}  ! direct-only mode older than ${LS_AGE}s${NC}"
                fi
            fi
        fi
    else
        echo -e "  Windsurf    ${D}not running${NC}"
    fi
    echo -e "  ────────────────────────────────────────"
}

do_verify() {
    printf "${CLR}"
    do_verify_inline
    pause
}

do_dashboard() {
    printf "${SHOW}"
    if [ -f "src/hg_dashboard.py" ]; then
        exec "$PROXY_PYTHON_BIN" src/hg_dashboard.py
    elif [ -f "hg_dashboard.py" ]; then
        exec python3 hg_dashboard.py
    elif [ -f "archive/old_scripts/internal/hg_dashboard.py" ]; then
        exec python3 archive/old_scripts/internal/hg_dashboard.py
    else
        printf "${CLR}"
        echo -e "${R}  Dashboard not found.${NC}"
        echo -e "  ${D}Run 'Verify status' (item 5) for inline status instead.${NC}"
        pause
    fi
}

do_install_deps() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Installing dependencies...${NC}\n"
    
    echo -e "${B}  [1/3] System packages${NC}"
    echo 1786 | sudo -S apt-get update -qq
    echo 1786 | sudo -S apt-get install -y libxml2-dev libxslt-dev docker.io 2>&1 | tail -3
    echo -e "${G}  [+] System packages installed${NC}\n"
    
    echo -e "${B}  [2/3] Python packages${NC}"
    pip install -q aiohttp fastapi uvicorn hypercorn h2 requests 2>&1 | tail -3
    echo -e "${G}  [+] Python packages installed${NC}\n"
    
    echo -e "${B}  [3/3] Docker images${NC}"
    docker pull -q ghcr.io/khoj-ai/khoj:latest 2>&1 | tail -3
    docker pull -q pgvector/pgvector:pg15 2>&1 | tail -3
    echo -e "${G}  [+] Docker images pulled${NC}\n"
    
    echo -e "${G}  All dependencies installed!${NC}"
    pause
}

do_tidy() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Cleaning project root...${NC}\n"

    mkdir -p archive/old_scripts archive/old_patchers
    local moved=0

    # Stale root scripts
    for f in setup_network_redirect.sh start_https_proxy.sh launch_debug.sh \
             add_https_to_proxy.py hg_dashboard.py hg_simple.py hg.py hg_aliases.sh \
             hg_status.sh hg_stop.sh GEMINI.md README.md \
             WINDSURF_MITM_FIX.md WINDSURF_FIX_SUMMARY.md PATCHER_V2_GUIDE.md; do
        if [ -f "$f" ]; then
            mv "$f" archive/old_scripts/internal/
            echo -e "  ${G}>${NC} $f → archive/old_scripts/internal/"
            moved=$((moved+1))
        fi
    done

    # Superseded individual patchers — archive if somehow still present
    # (authoritative patcher is src/patch_all.py only)
    for f in src/patch_windsurf_client.py src/patch_windsurf_urls.py \
             src/patch_language_server_binary.py src/patch_windsurf_aggressive.py; do
        if [ -f "$f" ]; then
            mv "$f" archive/old_patchers/
            echo -e "  ${G}>${NC} $f → archive/old_patchers/"
            moved=$((moved+1))
        fi
    done

    [ "$moved" -eq 0 ] \
        && echo -e "  ${G}Root already clean.${NC}" \
        || echo -e "\n  ${G}Moved $moved file(s) to archive/${NC}"
    pause
}

do_hosts_clean() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Cleaning /etc/hosts...${NC}\n"

    local hosts="/etc/hosts"
    local removed=0

    if [ ! -w "$hosts" ]; then
        echo -e "  ${R}Need sudo to modify /etc/hosts${NC}"
        pause
        return
    fi

    # Remove HG-SNIFF and HG-PATCH markers
    local temp=$(mktemp)
    while IFS= read -r line; do
        if [[ "$line" != *HG-SNIFF* && "$line" != *HG-PATCH* ]]; then
            echo "$line" >> "$temp"
        else
            removed=$((removed+1))
        fi
    done < "$hosts"

    if [ "$removed" -gt 0 ]; then
        echo "$SUDO_PASS" | sudo -S cp "$temp" "$hosts"
        echo -e "  ${G}Removed $removed host entries${NC}"
    else
        echo -e "  ${G}No HG entries found${NC}"
    fi

    rm "$temp"

    # Remove iptables NAT rules
    echo -e "${B}  [*] Removing iptables NAT rules...${NC}"
    echo "$SUDO_PASS" | sudo -S iptables -t nat -D OUTPUT -j HG-SNIFF 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S iptables -t nat -F HG-SNIFF 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S iptables -t nat -X HG-SNIFF 2>/dev/null || true
    echo -e "  ${G}[+] iptables NAT cleaned${NC}"

    pause
}

do_sniff_start() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Starting passive sniffer (tcpdump)...${NC}\n"

    # Kill old sniffers
    pkill -f "sniff_passive.py\|sniff_cascade.py" 2>/dev/null || true
    sleep 1

    # Start passive sniffer in background
    echo "$SUDO_PASS" | sudo -S python3 tools/sniff_passive.py > logs/sniff_passive.log 2>&1 &
    sleep 2

    if pgrep -f "sniff_passive.py" >/dev/null 2>&1; then
        echo -e "  ${G}[+] Passive sniffer running${NC}"
        echo -e "  ${D}Capture:  logs/cascade_passive.pcap${NC}"
        echo -e "  ${D}Log:      logs/cascade_passive.log${NC}"
        echo -e "\n  ${Y}Does NOT modify traffic. Windsurf continues normally.${NC}"
        echo -e "  ${Y}Analyze later with: sudo tcpdump -r logs/cascade_passive.pcap -nn -A${NC}"
    else
        echo -e "  ${R}[-] Sniffer failed to start${NC}"
        echo -e "  ${D}Check logs/sniff_passive.log${NC}"
    fi
    pause
}

do_sniff_stop() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Stopping sniffer...${NC}\n"

    # Kill all sniffers
    pkill -f "sniff_passive.py\|sniff_cascade.py" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill tcpdump 2>/dev/null || true
    sleep 1

    # Clean hosts + iptables (in case MITM sniffer was used before)
    do_hosts_clean_silent

    echo -e "  ${G}[+] Sniffer stopped${NC}"

    if [ -f "logs/cascade_passive.pcap" ]; then
        local size=$(du -h logs/cascade_passive.pcap | cut -f1)
        echo -e "  ${G}[+] Capture saved: logs/cascade_passive.pcap ($size)${NC}"
        echo -e "\n  ${Y}Analyze:${NC}"
        echo -e "    ${D}sudo tcpdump -r logs/cascade_passive.pcap -nn -A${NC}"
        echo -e "    ${D}wireshark logs/cascade_passive.pcap${NC}"
    fi
    pause
}

do_hosts_clean_silent() {
    local hosts="/etc/hosts"
    local temp=$(mktemp)
    while IFS= read -r line; do
        if [[ "$line" != *HG-SNIFF* && "$line" != *HG-PATCH* ]]; then
            echo "$line" >> "$temp"
        fi
    done < "$hosts"
    echo "$SUDO_PASS" | sudo -S cp "$temp" "$hosts"
    rm "$temp"

    # Remove iptables NAT rules
    echo "$SUDO_PASS" | sudo -S iptables -t nat -D OUTPUT -j HG-SNIFF 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S iptables -t nat -F HG-SNIFF 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S iptables -t nat -X HG-SNIFF 2>/dev/null || true
}

do_keylog_patch() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Installing TLS keylog wrapper...${NC}\n"
    # 1. Compile the preload .so
    echo -e "  ${D}Compiling keylog_preload.so...${NC}"
    if ! gcc -shared -fPIC -O0 -o tools/keylog_preload.so \
             tools/keylog_preload.c -ldl 2>&1 | sed 's/^/    /'; then
        echo -e "  ${R}Compile failed.${NC}"; pause; return
    fi
    # 2. Install wrapper (kills LS, backs up binary, writes shell wrapper)
    echo -e "  ${D}Installing wrapper...${NC}"
    echo "$SUDO_PASS" | sudo -S bash tools/install_keylog_wrapper.sh
    echo -e "\n  ${Y}>>> Reload the Windsurf window now (Ctrl+Shift+P -> Reload Window)${NC}"
    echo -e "  ${D}Then run 'Capture TLS keys' from this menu.${NC}"
    pause
}

do_keylog_capture() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Capturing TLS session keys...${NC}\n"
    echo "$SUDO_PASS" | sudo -S python3 tools/run_keylog.py
    pause
}

do_keylog_undo() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Removing TLS keylog wrapper...${NC}\n"
    echo "$SUDO_PASS" | sudo -S bash tools/install_keylog_wrapper.sh --undo
    echo -e "\n  ${Y}Reload Windsurf window to restore normal operation.${NC}"
    pause
}

do_keylog_verify() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  TLS keylog status...${NC}\n"
    bash tools/install_keylog_wrapper.sh --verify
    if [ -f "/tmp/hg_tls.keys" ]; then
        local lines
        lines=$(wc -l < /tmp/hg_tls.keys)
        echo -e "\n  ${G}Key file: /tmp/hg_tls.keys ($lines lines)${NC}"
        grep -v '^#' /tmp/hg_tls.keys | tail -3
    else
        echo -e "\n  ${Y}No key file yet (/tmp/hg_tls.keys)${NC}"
    fi
    pause
}

do_proxy_mode_restart() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Restart C proxy with upstream inference mode${NC}\n"
    echo -e "  ${G}1${NC}) cache-first  ${D}cache hits replay locally; misses go upstream${NC}"
    echo -e "  ${G}2${NC}) cache-only   ${D}cache hits only; misses blocked locally${NC}"
    echo -e "  ${G}3${NC}) confirm      ${D}block misses with gate telemetry${NC}"
    echo -e "  ${G}4${NC}) block        ${D}block upstream inference misses${NC}"
    echo -e "  ${G}5${NC}) local-only   ${D}local-only alias for block behavior${NC}"
    echo -e "  ${G}q${NC}) back\n"

    local choice mode
    read -r -p "  Mode [1]: " choice
    case "${choice:-1}" in
        1) mode="cache-first" ;;
        2) mode="cache-only" ;;
        3) mode="confirm" ;;
        4) mode="block" ;;
        5) mode="local-only" ;;
        q|Q) return 0 ;;
        *)
            echo -e "${R}  Invalid mode selection${NC}"
            pause
            return 1
            ;;
    esac

    HG_MICROPROXY_FRONT=1 HG_UPSTREAM_INFERENCE_MODE="$mode" do_start_proxy
    echo -e "\n  ${G}Mode active:${NC} $mode"
    pause
}

# ─── main TUI loop ──────────────────────────────────────────────────
main() {
    printf "${HIDE}"
    trap "printf '${SHOW}${CLR}'; exit 0" EXIT INT TERM

    while true; do
        draw_menu
        case "$(read_key)" in
            UP)    SEL=$(( (SEL - 1 + ${#ITEMS[@]}) % ${#ITEMS[@]} )) ;;
            DOWN)  SEL=$(( (SEL + 1) % ${#ITEMS[@]} )) ;;
            ENTER)
                case $SEL in
                    0) do_patch ;;
                    1) do_repatch ;;
                    2) do_undo ;;
                    3) do_start ;;
                    4) do_proxy_mode_restart ;;
                    5) do_dashboard ;;
                    6) do_verify ;;
                    7) break ;;
                    *) ;;
                esac
                ;;
            NUM1) SEL=0; do_patch ;;
            NUM2) SEL=1; do_repatch ;;
            NUM3) SEL=2; do_undo ;;
            NUM4) SEL=3; do_start ;;
            NUM5) SEL=4; do_proxy_mode_restart ;;
            NUM6) SEL=5; do_dashboard ;;
            NUM7) SEL=6; do_verify ;;
            NUM0) SEL=1; do_repatch; do_start ;;
            QUIT|ESC) break ;;
        esac
    done
}

run_command() {
    local cmd="$1"
    if [ "$cmd" != "menu" ] && [ -n "$cmd" ]; then
        HG_NON_INTERACTIVE=1
    fi
    case "$cmd" in
        menu|"")
            main
            ;;
        patch)
            do_patch
            ;;
        repatch)
            do_repatch
            ;;
        undo)
            do_undo
            ;;
        start)
            do_start
            ;;
        start_proxy)
            do_start_proxy
            ;;
        verify|status)
            do_verify
            ;;
        dashboard)
            do_dashboard
            ;;
        *)
            echo "Usage: $0 [menu|patch|repatch|undo|start|start_proxy|verify|status|dashboard]"
            return 1
            ;;
    esac
}

if [ "${HG_START_SOURCE_ONLY:-0}" != "1" ]; then
    run_command "${1:-menu}"
fi
