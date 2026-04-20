#!/bin/bash
# HIGH-GRAVITY Bootstrap v2.0
# Interactive menu for all operations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SUDO_PASS="1786"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

banner() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          HIGH-GRAVITY BOOTSTRAP v2.0                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ─── helpers ──────────────────────────────────────────────────────────
check_port() { lsof -i:$1 >/dev/null 2>&1; }

status_line() {
    local name="$1" check="$2"
    if eval "$check"; then
        echo -e "  ${name}: ${GREEN}✓ RUNNING${NC}"
    else
        echo -e "  ${name}: ${RED}✗ OFFLINE${NC}"
    fi
}

# ─── core functions ───────────────────────────────────────────────────
do_cleanup() {
    echo -e "${BLUE}[*] Cleaning up...${NC}"
    pkill -f "hg.py\|hg_simple.py" 2>/dev/null || true
    pkill -f "src/proxy.py" 2>/dev/null || true
    pkill -f "khoj.*--port.*42110" 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}[✓] All processes killed${NC}"
}

do_patch() {
    echo ""
    echo -e "${BOLD}Applying all patches...${NC}"
    echo ""

    # Extension patches
    echo -e "${BLUE}[1/2] Extension patches${NC}"
    python3 src/patch_windsurf_client.py --force
    echo ""

    # Binary patches
    echo -e "${BLUE}[2/2] Binary patches${NC}"
    python3 src/patch_language_server_binary.py
    echo ""

    echo -e "${GREEN}[✓] All patches applied${NC}"
    echo -e "${YELLOW}[!] Restart Windsurf for changes to take effect${NC}"
}

do_undo() {
    echo ""
    echo -e "${BOLD}Undoing all patches...${NC}"
    echo ""

    # Extension undo
    echo -e "${BLUE}[1/2] Restoring extension.js${NC}"
    python3 src/patch_windsurf_client.py --undo
    echo ""

    # Binary undo
    echo -e "${BLUE}[2/2] Restoring language server binary${NC}"
    python3 src/patch_language_server_binary.py --restore
    echo ""

    echo -e "${GREEN}[✓] All patches undone${NC}"
    echo -e "${YELLOW}[!] Restart Windsurf for changes to take effect${NC}"
}

do_start() {
    echo ""
    echo -e "${BOLD}Starting all services...${NC}"
    echo ""

    # Cleanup first
    do_cleanup

    # Setup certs
    echo -e "${BLUE}[*] Checking HTTPS certificates...${NC}"
    if [ -f "certs/proxy.crt" ] && [ -f "certs/proxy.key" ]; then
        echo -e "${GREEN}[✓] Certificates found${NC}"
    else
        echo -e "${YELLOW}[*] Generating certificates...${NC}"
        python3 add_https_to_proxy.py >/dev/null 2>&1
    fi

    mkdir -p logs

    # HTTP proxy
    echo -e "${BLUE}[*] Starting HTTP proxy (port 9999)...${NC}"
    PYTHONPATH=. nohup python3 src/proxy.py > logs/proxy.log 2>&1 &

    # HTTPS proxy
    if [ -f "certs/proxy.crt" ] && [ -f "certs/proxy.key" ]; then
        echo -e "${BLUE}[*] Starting HTTPS proxy (port 443)...${NC}"
        echo "$SUDO_PASS" | sudo -S -E PYTHONPATH=. python3 src/proxy.py --https > logs/proxy_https.log 2>&1 &
    fi

    # Wait for HTTP
    for i in {1..10}; do
        check_port 9999 && break
        sleep 1
    done

    # Khoj
    echo -e "${BLUE}[*] Starting Khoj...${NC}"
    if [ -d "khoj" ]; then
        bash bin/khoj_launcher.sh >/dev/null 2>&1 &
        for i in {1..20}; do
            curl -s http://127.0.0.1:42110/api/health >/dev/null 2>&1 && break
            sleep 1
        done
    else
        echo -e "${YELLOW}    Khoj directory not found, skipping${NC}"
    fi

    echo ""
    do_verify
}

do_verify() {
    echo -e "${BOLD}Service Status:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    status_line "Proxy HTTP  (9999)" "check_port 9999"
    status_line "Proxy HTTPS (443) " "check_port 443"
    status_line "Khoj        (42110)" "curl -s http://127.0.0.1:42110/api/health >/dev/null 2>&1"
    status_line "Dashboard         " "pgrep -f 'hg_simple.py\|hg.py' >/dev/null 2>&1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo ""
    echo -e "${BOLD}Patch Status:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Extension
    EXT="/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js"
    if [ -f "$EXT" ] && grep -q "getApiServerUrlFromContext=A=>{return" "$EXT" 2>/dev/null; then
        echo -e "  Extension:  ${GREEN}✓ PATCHED${NC} (root cause fix applied)"
    elif [ -f "$EXT" ] && grep -q "shield.windsurf.com" "$EXT" 2>/dev/null; then
        echo -e "  Extension:  ${YELLOW}~ PARTIAL${NC} (missing root cause fix)"
    else
        echo -e "  Extension:  ${RED}✗ UNPATCHED${NC}"
    fi

    # Binary
    BIN="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64"
    if [ -f "$BIN" ] && strings "$BIN" 2>/dev/null | grep -q "http://127.0.0.1:9999"; then
        echo -e "  Binary:     ${GREEN}✓ PATCHED${NC}"
    else
        echo -e "  Binary:     ${RED}✗ UNPATCHED${NC}"
    fi

    # Windsurf
    if pgrep -f "windsurf" >/dev/null 2>&1; then
        API_URL=$(ps aux | grep language_server_linux | grep -v grep | head -1 | grep -oP "\-\-api_server_url \S+" | awk '{print $2}')
        if [ -z "$API_URL" ]; then
            echo -e "  Windsurf:   ${YELLOW}~ RUNNING (no language server)${NC}"
        elif echo "$API_URL" | grep -q "shield.windsurf.com\|127.0.0.1"; then
            echo -e "  Windsurf:   ${GREEN}✓ RUNNING (→ proxy: $API_URL)${NC}"
        else
            echo -e "  Windsurf:   ${RED}! RUNNING (→ EXTERNAL: $API_URL)${NC}"
            echo -e "             ${YELLOW}  Restart Windsurf to pick up patches${NC}"
        fi
    else
        echo -e "  Windsurf:   ${RED}○ NOT RUNNING${NC}"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

do_dashboard() {
    echo -e "${BLUE}[*] Launching dashboard...${NC}"
    exec python3 hg_simple.py
}

do_tidy() {
    echo -e "${BOLD}Cleaning project root...${NC}"
    echo ""

    mkdir -p archive/old_scripts

    STALE_FILES=(
        "setup_network_redirect.sh"
        "start_https_proxy.sh"
        "launch_debug.sh"
        "STATUS.md"
        "HTTPS_PROXY_COMPLETE.md"
        "WINDSURF_MITM_FIX.md"
        "WINDSURF_FIX_SUMMARY.md"
        "PATCHER_V2_GUIDE.md"
        "complete_setup.sh"
    )

    MOVED=0
    for f in "${STALE_FILES[@]}"; do
        if [ -f "$f" ]; then
            mv "$f" archive/old_scripts/
            echo -e "  ${GREEN}→${NC} $f → archive/old_scripts/"
            ((MOVED++))
        fi
    done

    if [ "$MOVED" -eq 0 ]; then
        echo -e "  ${GREEN}✓ Root already clean${NC}"
    else
        echo -e "\n  ${GREEN}✓ Moved $MOVED file(s) to archive/${NC}"
    fi
}

# ─── interactive menu ─────────────────────────────────────────────────
menu() {
    banner
    echo -e "${BOLD}  [1]${NC}  Patch Windsurf       (extension + binary)"
    echo -e "${BOLD}  [2]${NC}  Undo patches         (restore originals)"
    echo -e "${BOLD}  [3]${NC}  Start everything      (clean + proxy + khoj + verify)"
    echo -e "${BOLD}  [4]${NC}  Dashboard             (launch hg_simple.py)"
    echo -e "${BOLD}  [5]${NC}  Verify status         (services + patches)"
    echo -e "${BOLD}  [6]${NC}  Tidy project root     (archive stale files)"
    echo -e "${BOLD}  [7]${NC}  Full setup            (patch → start → verify)"
    echo -e "${BOLD}  [q]${NC}  Quit"
    echo ""
    echo -n "Choice: "
}

# ─── CLI or interactive ──────────────────────────────────────────────
main() {
    case "${1:-}" in
        --patch)    banner; do_patch ;;
        --undo)     banner; do_undo ;;
        --start)    banner; do_start ;;
        --dashboard) banner; do_dashboard ;;
        --verify)   banner; do_verify ;;
        --tidy)     banner; do_tidy ;;
        --full)     banner; do_patch; echo ""; do_start ;;
        --help|-h)
            banner
            echo "Usage: $0 [OPTION]"
            echo ""
            echo "Options (non-interactive):"
            echo "  --patch       Apply all patches"
            echo "  --undo        Undo all patches"
            echo "  --start       Clean + start all services"
            echo "  --dashboard   Launch dashboard"
            echo "  --verify      Show status of services + patches"
            echo "  --tidy        Archive stale files from root"
            echo "  --full        Patch + start + verify"
            echo "  --help        Show this help"
            echo ""
            echo "Run without arguments for interactive menu."
            ;;
        "")
            # Interactive mode
            while true; do
                menu
                read -r choice
                echo ""
                case "$choice" in
                    1) do_patch ;;
                    2) do_undo ;;
                    3) do_start ;;
                    4) do_dashboard ;;
                    5) do_verify ;;
                    6) do_tidy ;;
                    7) do_patch; echo ""; do_start ;;
                    q|Q) echo "Bye."; exit 0 ;;
                    *) echo -e "${RED}Invalid choice${NC}" ;;
                esac
                echo ""
                echo -e "${CYAN}Press ENTER to return to menu...${NC}"
                read -r
            done
            ;;
        *)
            echo "Unknown option: $1 (use --help)"
            exit 1
            ;;
    esac
}

main "$@"
