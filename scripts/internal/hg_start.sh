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
PROXY_PYTHON_BIN="$SCRIPT_DIR/.hg_proxy_venv/bin/python"
if [ ! -x "$PROXY_PYTHON_BIN" ]; then
    PROXY_PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
fi
if [ ! -x "$PROXY_PYTHON_BIN" ]; then
    PROXY_PYTHON_BIN="$(command -v python3)"
fi
TARGET_USER="${SUDO_USER:-$(whoami)}"
TARGET_HOME="$(eval echo "~${TARGET_USER}")"
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
    "Undo                restore originals + clean hosts"
    "Start all           patch + proxy + Windsurf"
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

    printf "\n  ${D}↑↓ / 1-6 to select  •  0 = repatch+start  •  q quit${NC}\n"
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
    echo -e "${B}  [*] Checking clean backup exists...${NC}"
    local bak_out
    bak_out=$(python3 src/patch_all.py --check-backups --binary-only 2>&1)
    echo "$bak_out" | sed 's/^/  /'
    if ! echo "$bak_out" | grep -q 'Clean backup verified'; then
        echo -e "${R}  [!] No clean binary backup — cannot repatch safely.${NC}"
        echo -e "${Y}      Reinstall Windsurf or place clean .original manually.${NC}"
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

    # Restore binary
    echo -e "${B}  [*] Restoring binary...${NC}"
    python3 src/patch_all.py --restore --binary-only 2>&1 | sed 's/^/  /'

    # Patch all
    echo -e "${B}  [*] Patching all layers...${NC}"
    python3 src/patch_all.py --force 2>&1 | sed 's/^/  /'

    # Verify
    echo ""
    python3 src/patch_all.py --verify 2>&1 | grep -E '✓|✗|OK|FAIL' | sed 's/^/  /'

    echo -e "\n${G}  Done. Restart Windsurf:${NC}"
    echo -e "  ${D}/usr/share/windsurf-next/windsurf-next &${NC}"
    pause
}

do_undo() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Undoing all patches...${NC}\n"

    echo -e "${B}  [1/2] Restoring files from backups...${NC}"
    python3 src/patch_all.py --restore 2>&1 | sed 's/^/  /'
    echo ""

    echo -e "${B}  [2/3] Removing /etc/hosts entries...${NC}"
    do_hosts_clean_silent
    echo -e "  ${G}[+] /etc/hosts cleaned${NC}"
    echo ""

    echo -e "${G}  All patches undone. Restart Windsurf to apply.${NC}"
    pause
}

_start_proxy_http() {
    mkdir -p logs
    local root_cmd
    local khoj_token="${HG_KHOJ_TOKEN:-}"
    root_cmd="cd \"$SCRIPT_DIR\" && export PYTHONNOUSERSITE=1 PYTHONPATH=\"$SCRIPT_DIR\" HG_KHOJ_ENABLED=true HG_KHOJ_TOKEN=\"$khoj_token\" && nohup \"$PROXY_PYTHON_BIN\" \"$SCRIPT_DIR/src/proxy.py\" >> \"$SCRIPT_DIR/logs/proxy.log\" 2>&1 & echo \$! > \"$SCRIPT_DIR/logs/proxy.pid\" && chown $USER:$USER \"$SCRIPT_DIR/logs/proxy.pid\" \"$SCRIPT_DIR/logs/proxy.log\""
    echo "$SUDO_PASS" | sudo -S bash -c "$root_cmd"
}

_start_proxy_https() {
    mkdir -p logs
    local root_cmd
    local khoj_token="${HG_KHOJ_TOKEN:-}"
    root_cmd="cd \"$SCRIPT_DIR\" && export PYTHONNOUSERSITE=1 PYTHONPATH=\"$SCRIPT_DIR\" HG_KHOJ_ENABLED=true HG_KHOJ_TOKEN=\"$khoj_token\" && nohup \"$PROXY_PYTHON_BIN\" \"$SCRIPT_DIR/src/proxy.py\" --https >> \"$SCRIPT_DIR/logs/proxy_https.log\" 2>&1 & echo \$! > \"$SCRIPT_DIR/logs/proxy_https.pid\" && chown $USER:$USER \"$SCRIPT_DIR/logs/proxy_https.pid\" \"$SCRIPT_DIR/logs/proxy_https.log\""
    echo "$SUDO_PASS" | sudo -S bash -c "$root_cmd"
}

_start_khoj_async() {
    mkdir -p logs
    local launcher="$SCRIPT_DIR/scripts/internal/khoj_docker.sh"
    local pidfile="$SCRIPT_DIR/logs/khoj_docker.pid"
    local logfile="$SCRIPT_DIR/logs/khoj_docker.log"

    if pidfile_alive "$pidfile"; then
        return 0
    fi

    if [ -f "$launcher" ]; then
        rotate_log_if_large "$logfile" 10485760 5
        nohup bash "$launcher" >> "$logfile" 2>&1 &
        echo "$SUDO_PASS" | sudo -S bash -c "echo $! > \"$pidfile\" && chown $USER:$USER \"$pidfile\""
    fi
}

_stop_windsurf() {
    echo -e "${B}  [*] Stopping Windsurf...${NC}"
    echo "$SUDO_PASS" | sudo -S pkill -f "language_server_linux_x64.real" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "windsurf-next --new-window" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "/usr/share/windsurf-next/windsurf-next" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "codeium.windsurf" 2>/dev/null || true
    sleep 2
    if pgrep -f "language_server_linux_x64.real\|windsurf-next --new-window\|codeium.windsurf" >/dev/null 2>&1; then
        echo -e "${Y}  [~] Windsurf still present after stop attempt${NC}"
    else
        echo -e "${G}  [+] Windsurf stopped${NC}"
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
    nohup /usr/share/windsurf-next/windsurf-next > "$SCRIPT_DIR/logs/windsurf_launch.log" 2>&1 &
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
    while true; do
        sleep 15
        is_khoj_healthy && continue
        echo "$(date): khoj health down, restarting docker launcher" >> "$SCRIPT_DIR/logs/khoj_watchdog.log"
        _start_khoj_async
    done
}

_watchdog_proxy() {
    # Background watchdog: restart HTTP/HTTPS proxies if they die
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
            if ! check_port 443; then
                if pidfile_alive "$SCRIPT_DIR/logs/proxy_https.pid"; then
                    echo "$(date): https proxy port down but process still alive; waiting" >> "$SCRIPT_DIR/logs/proxy_watchdog.log"
                else
                    echo "$(date): https proxy down, restarting" >> "$SCRIPT_DIR/logs/proxy_watchdog.log"
                    _start_proxy_https
                fi
            fi
        fi
    done
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
    echo "$SUDO_PASS" | sudo -S pkill -f "src/proxy.py" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "_watchdog_proxy" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "_watchdog_khoj" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "gemini_session_launcher.py" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "highgravity_proxy.py" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "lsp_shim" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "proxyt" 2>/dev/null || true
    echo "$SUDO_PASS" | sudo -S pkill -f "khoj.*--port.*42110" 2>/dev/null || true
    bash scripts/internal/khoj_stop.sh >/dev/null 2>&1 || true
    docker stop khoj khoj-pg >/dev/null 2>&1 || true
    echo "$SUDO_PASS" | sudo -S rm -f logs/*.pid 2>/dev/null || true
    sleep 1
    echo -e "${G}  [+] Cleaned${NC}"

    mkdir -p logs
    echo "$SUDO_PASS" | sudo -S chown -R $USER:$USER logs/

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
        # Launch watchdog in background
        ( _watchdog_proxy ) &
        echo $! > logs/proxy_watchdog.pid
        # Launch Khoj watchdog in background
        ( _watchdog_khoj ) &
        echo $! > logs/khoj_watchdog.pid
    else
        echo -e "${R}  [-] HTTP proxy failed — check logs/proxy.log${NC}"
        tail -5 logs/proxy.log | sed 's/^/      /'
    fi

    # ── HTTPS proxy (if certs present) ───────────────────────────────
    if [ -f "certs/proxy.crt" ] && [ -f "certs/proxy.key" ]; then
        # Install CA cert into system trust store (idempotent)
        if [ ! -f "/usr/local/share/ca-certificates/hg-proxy.crt" ]; then
            echo -e "${B}  [*] Installing CA cert into system trust store${NC}"
            echo "$SUDO_PASS" | sudo -S cp certs/proxy.crt /usr/local/share/ca-certificates/hg-proxy.crt
            echo "$SUDO_PASS" | sudo -S update-ca-certificates 2>/dev/null | tail -1 | sed 's/^/  /'
        fi
        echo -e "${B}  [*] Starting HTTPS proxy (443)${NC}"
        _start_proxy_https
        wait_for_port 443 15 1 \
            && echo -e "${G}  [+] HTTPS proxy online${NC}" \
            || echo -e "${Y}  [~] HTTPS starting (logs/proxy_https.log)${NC}"
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
            curl -s -X POST http://127.0.0.1:9998/hg/khoj/reindex >/dev/null 2>&1 \
                && echo -e "${D}  [~] Khoj reindex triggered${NC}"
        else
            echo -e "${Y}  [~] Khoj warming up, waiting for readiness...${NC}"
            local wait_i
            for wait_i in {1..45}; do
                if is_khoj_healthy; then
                    echo -e "${G}  [+] Khoj healthy${NC}"
                    curl -s -X POST http://127.0.0.1:9998/hg/khoj/reindex >/dev/null 2>&1 \
                        && echo -e "${D}  [~] Khoj reindex triggered${NC}"
                    break
                fi
                sleep 1
            done
            if ! is_khoj_healthy; then
                echo -e "${Y}  [~] Khoj still warming in background (logs/khoj_docker.log)${NC}"
            fi
        fi
    else
        echo -e "${D}  [~] scripts/internal/khoj_docker.sh not found, skipping${NC}"
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
    check_port 443  && echo -e "  Proxy HTTPS (443)   ${G}UP${NC}" \
        || echo -e "  Proxy HTTPS (443)   ${Y}DOWN${NC}"
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
    python3 src/patch_all.py --verify --binary-only --js-only --hosts-only 2>&1 \
        | grep -E 'Binary|JS|hosts|iptables|OK|FAIL' \
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
    if [ -f "hg_dashboard.py" ]; then
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
    pip install -q aiohttp fastapi uvicorn requests 2>&1 | tail -3
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
                    4) do_dashboard ;;
                    5) do_verify ;;
                    6) break ;;
                    *) ;;
                esac
                ;;
            NUM1) SEL=0; do_patch ;;
            NUM2) SEL=1; do_repatch ;;
            NUM3) SEL=2; do_undo ;;
            NUM4) SEL=3; do_start ;;
            NUM5) SEL=5; do_verify ;;
            NUM6) SEL=4; do_dashboard ;;
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
        verify|status)
            do_verify
            ;;
        dashboard)
            do_dashboard
            ;;
        *)
            echo "Usage: $0 [menu|patch|repatch|undo|start|verify|status|dashboard]"
            return 1
            ;;
    esac
}

run_command "${1:-menu}"
