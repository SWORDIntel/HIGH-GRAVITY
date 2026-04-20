#!/bin/bash
# HIGH-GRAVITY Bootstrap v3.0 — ANSI TUI
# Pure bash, no whiptail/dialog dependency

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SUDO_PASS="1786"

# ─── ANSI codes ──────────────────────────────────────────────────────
ESC=$'\033'
G="${ESC}[32m"; R="${ESC}[31m"; Y="${ESC}[33m"; B="${ESC}[34m"
C="${ESC}[36m"; M="${ESC}[35m"; W="${ESC}[97m"; D="${ESC}[2m"
BG="${ESC}[44m"; BOLD="${ESC}[1m"; INV="${ESC}[7m"; NC="${ESC}[0m"
HIDE="${ESC}[?25l"; SHOW="${ESC}[?25h"; CLR="${ESC}[2J${ESC}[H"

check_port() { lsof -i:$1 >/dev/null 2>&1; }

# ─── draw menu ───────────────────────────────────────────────────────
ITEMS=(
    "Patch Windsurf         extension + binary"
    "Undo patches           restore originals"
    "Start everything       proxy + khoj + verify"
    "Open Dashboard         Rich TUI monitor"
    "Verify status          services + patches"
    "Tidy project root      archive stale files"
    "Start sniffer          capture Cascade traffic"
    "Stop sniffer           restore hosts"
    "Clean /etc/hosts       remove HG redirects"
    "Full setup             patch > start > verify"
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
    check_port 9999 && p_s="${G}ON${NC}" || p_s="${R}OFF${NC}"
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

    printf "\n  ${D}Arrow keys to move, Enter to select, q to quit${NC}\n"
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
    echo ""
    echo -e "  ${D}Press any key to return...${NC}"
    read -rsn1
}

# ─── core operations ─────────────────────────────────────────────────
do_patch() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Applying all patches...${NC}\n"

    echo -e "${B}  [1/2] Extension patches${NC}"
    python3 src/patch_windsurf_client.py --force 2>&1 | sed 's/^/  /'
    echo ""

    echo -e "${B}  [2/2] Binary patches${NC}"
    python3 src/patch_language_server_binary.py 2>&1 | sed 's/^/  /'
    echo ""

    echo -e "${G}  Done. Restart Windsurf to apply.${NC}"
    pause
}

do_undo() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Undoing all patches...${NC}\n"

    echo -e "${B}  [1/2] Restoring extension.js${NC}"
    python3 src/patch_windsurf_client.py --undo 2>&1 | sed 's/^/  /'
    echo ""

    echo -e "${B}  [2/2] Restoring language server binary${NC}"
    python3 src/patch_language_server_binary.py --restore 2>&1 | sed 's/^/  /'
    echo ""

    echo -e "${G}  Done. Restart Windsurf to apply.${NC}"
    pause
}

do_start() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Starting all services...${NC}\n"

    echo -e "${B}  [*] Killing old processes${NC}"
    pkill -f "hg_dashboard.py\|hg_simple.py\|hg.py" 2>/dev/null || true
    pkill -f "src/proxy.py" 2>/dev/null || true
    pkill -f "khoj.*--port.*42110" 2>/dev/null || true
    sleep 1
    echo -e "${G}  [+] Cleaned${NC}"

    mkdir -p logs

    echo -e "${B}  [*] Starting HTTP proxy (9999)${NC}"
    PYTHONPATH=. nohup python3 src/proxy.py > logs/proxy.log 2>&1 &

    if [ -f "certs/proxy.crt" ] && [ -f "certs/proxy.key" ]; then
        echo -e "${B}  [*] Starting HTTPS proxy (443)${NC}"
        echo "$SUDO_PASS" | sudo -S -E PYTHONPATH=. python3 src/proxy.py --https > logs/proxy_https.log 2>&1 &
    fi

    echo -e "${B}  [*] Waiting for proxy...${NC}"
    for i in {1..10}; do check_port 9999 && break; sleep 1; done
    check_port 9999 && echo -e "${G}  [+] Proxy online${NC}" || echo -e "${R}  [-] Proxy failed${NC}"

    if [ -d "khoj" ]; then
        echo -e "${B}  [*] Starting Khoj${NC}"
        bash bin/khoj_launcher.sh >/dev/null 2>&1 &
        for i in {1..15}; do
            curl -s http://127.0.0.1:42110/api/health >/dev/null 2>&1 && break
            sleep 1
        done
        curl -s http://127.0.0.1:42110/api/health >/dev/null 2>&1 \
            && echo -e "${G}  [+] Khoj online${NC}" \
            || echo -e "${Y}  [~] Khoj still starting${NC}"
    else
        echo -e "${D}  [~] Khoj not installed, skipping${NC}"
    fi

    echo ""
    do_verify_inline
    pause
}

do_verify_inline() {
    echo -e "${BOLD}${C}  Status:${NC}"
    echo -e "  ────────────────────────────────────────"

    # Services
    check_port 9999 && echo -e "  Proxy HTTP  (9999)  ${G}RUNNING${NC}" || echo -e "  Proxy HTTP  (9999)  ${R}OFFLINE${NC}"
    check_port 443  && echo -e "  Proxy HTTPS (443)   ${G}RUNNING${NC}" || echo -e "  Proxy HTTPS (443)   ${D}OFFLINE${NC}"
    curl -s http://127.0.0.1:42110/api/health >/dev/null 2>&1 \
        && echo -e "  Khoj        (42110) ${G}RUNNING${NC}" \
        || echo -e "  Khoj        (42110) ${D}OFFLINE${NC}"

    echo ""

    # Extension
    EXT="/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js"
    if [ -f "$EXT" ] && grep -q 'getApiServerUrlFromContext=A=>{return' "$EXT" 2>/dev/null; then
        echo -e "  Extension   ${G}PATCHED${NC} (root cause fix)"
    elif [ -f "$EXT" ] && grep -q "shield.windsurf.com" "$EXT" 2>/dev/null; then
        echo -e "  Extension   ${Y}PARTIAL${NC}"
    else
        echo -e "  Extension   ${R}UNPATCHED${NC}"
    fi

    # Binary
    BIN="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64"
    if [ -f "$BIN" ] && strings "$BIN" 2>/dev/null | grep -q "http://127.0.0.1:9999"; then
        echo -e "  Binary      ${G}PATCHED${NC}"
    else
        echo -e "  Binary      ${R}UNPATCHED${NC}"
    fi

    # Windsurf
    if pgrep -f "windsurf" >/dev/null 2>&1; then
        API_URL=$(ps aux | grep language_server_linux | grep -v grep | head -1 | grep -oP "\-\-api_server_url \S+" | awk '{print $2}')
        if [ -z "$API_URL" ]; then
            echo -e "  Windsurf    ${Y}running (no lang server)${NC}"
        elif echo "$API_URL" | grep -q "shield.windsurf.com\|127.0.0.1"; then
            echo -e "  Windsurf    ${G}PROXY${NC} $API_URL"
        else
            echo -e "  Windsurf    ${R}EXTERNAL${NC} $API_URL"
            echo -e "              ${Y}^ Restart Windsurf to pick up patches${NC}"
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
    exec python3 hg_dashboard.py
}

do_tidy() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Cleaning project root...${NC}\n"

    mkdir -p archive/old_scripts
    local moved=0

    for f in setup_network_redirect.sh start_https_proxy.sh launch_debug.sh \
             STATUS.md HTTPS_PROXY_COMPLETE.md WINDSURF_MITM_FIX.md \
             WINDSURF_FIX_SUMMARY.md PATCHER_V2_GUIDE.md complete_setup.sh; do
        if [ -f "$f" ]; then
            mv "$f" archive/old_scripts/
            echo -e "  ${G}>${NC} $f"
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
    pause
}

do_sniff_start() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Starting Cascade sniffer...${NC}\n"

    # Kill old sniffer
    pkill -f "sniff_cascade.py" 2>/dev/null || true
    sleep 1

    # Start sniffer in background
    echo "$SUDO_PASS" | sudo -S -E PYTHONPATH=. python3 tools/sniff_cascade.py > logs/sniffer.log 2>&1 &
    sleep 2

    if pgrep -f "sniff_cascade.py" >/dev/null 2>&1; then
        echo -e "  ${G}[+] Sniffer running on port 443${NC}"
        echo -e "  ${D}Logs: logs/cascade_sniff.log + .jsonl${NC}"
    else
        echo -e "  ${R}[-] Sniffer failed to start${NC}"
        echo -e "  ${D}Check logs/sniffer.log${NC}"
    fi
    pause
}

do_sniff_stop() {
    printf "${CLR}"
    echo -e "${BOLD}${C}  Stopping Cascade sniffer...${NC}\n"

    pkill -f "sniff_cascade.py" 2>/dev/null || true
    sleep 1

    # Clean hosts
    do_hosts_clean

    echo -e "  ${G}[+] Sniffer stopped, hosts restored${NC}"
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
                    1) do_undo ;;
                    2) do_start ;;
                    3) do_dashboard ;;
                    4) do_verify ;;
                    5) do_tidy ;;
                    6) do_sniff_start ;;
                    7) do_sniff_stop ;;
                    8) do_hosts_clean ;;
                    9) do_patch; do_start ;;
                    10) break ;;
                esac
                ;;
            NUM1) SEL=0; do_patch ;;
            NUM2) SEL=1; do_undo ;;
            NUM3) SEL=2; do_start ;;
            NUM4) SEL=3; do_dashboard ;;
            NUM5) SEL=4; do_verify ;;
            NUM6) SEL=5; do_tidy ;;
            NUM7) SEL=6; do_sniff_start ;;
            NUM8) SEL=7; do_sniff_stop ;;
            NUM9) SEL=8; do_hosts_clean ;;
            NUM0) SEL=9; do_patch; do_start ;;
            QUIT|ESC) break ;;
        esac
    done
}

main
