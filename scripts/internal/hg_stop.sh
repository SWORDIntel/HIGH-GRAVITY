#!/bin/bash
# HIGH-GRAVITY Universal Shutdown
# Stops all services gracefully

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SCRIPT_DIR"

if [ "${1:-}" != "--direct" ]; then
    exec bash "$SCRIPT_DIR/../hg.sh" stop
fi

SUDO_PASS="1786"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

stop_pidfile() {
    local pidfile="$1"
    local label="$2"
    local pid

    if [ ! -f "$pidfile" ]; then
        return 0
    fi

    pid="$(tr -d '[:space:]' < "$pidfile" 2>/dev/null)"
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null || true
        sleep 1
        if ps -p "$pid" -o pid= >/dev/null 2>&1; then
            echo "$SUDO_PASS" | sudo -S kill "$pid" 2>/dev/null || true
            sleep 1
        fi
        if ps -p "$pid" -o pid= >/dev/null 2>&1; then
            echo "$SUDO_PASS" | sudo -S kill -9 "$pid" 2>/dev/null || true
            kill -9 "$pid" 2>/dev/null || true
        fi
        echo -e "${GREEN}[✓] $label stopped (PID: $pid)${NC}"
    fi

    echo "$SUDO_PASS" | sudo -S rm -f "$pidfile"
}

stop_windsurf() {
    local patterns=(
        "language_server_linux_x64.real"
        "/usr/share/windsurf-next/windsurf-next"
        "windsurf-next --new-window"
        "codeium.windsurf"
        "devin acp --agent-type summarizer"
    )
    local still_running=0

    for pattern in "${patterns[@]}"; do
        pkill -f "$pattern" 2>/dev/null || true
        echo "$SUDO_PASS" | sudo -S pkill -f "$pattern" 2>/dev/null || true
    done

    sleep 1

    for pattern in "${patterns[@]}"; do
        if pgrep -f "$pattern" >/dev/null 2>&1; then
            still_running=1
            break
        fi
    done

    if [ "$still_running" -eq 1 ]; then
        echo -e "${YELLOW}[!] Windsurf still running${NC}"
    else
        echo -e "${GREEN}[✓] Windsurf stopped${NC}"
    fi
}

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          HIGH-GRAVITY Shutdown Sequence                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Stop Dashboard
echo -e "${BLUE}[*] Stopping Dashboard...${NC}"
pkill -f "hg.py" && echo -e "${GREEN}[✓] Dashboard stopped${NC}" || echo -e "${YELLOW}[!] Dashboard not running${NC}"

# Stop Launchers and Watchdogs
echo -e "${BLUE}[*] Stopping Launchers and Watchdogs...${NC}"
stop_pidfile "logs/proxy_watchdog.pid" "Proxy watchdog"
stop_pidfile "logs/khoj_watchdog.pid" "Khoj watchdog"
stop_pidfile "logs/windsurf_launch.pid" "Windsurf launcher"
pkill -f "gemini_session_launcher.py" 2>/dev/null || true
pkill -f "_watchdog_proxy" 2>/dev/null || true
pkill -f "_watchdog_khoj" 2>/dev/null || true
pkill -f "hg_trace.sh" 2>/dev/null || true
pkill -f "hg_doctor.sh" 2>/dev/null || true

# Stop Windsurf
echo -e "${BLUE}[*] Stopping Windsurf...${NC}"
stop_windsurf

# Stop Proxy
echo -e "${BLUE}[*] Stopping Proxy...${NC}"
stop_pidfile "logs/proxy.pid" "HTTP proxy"
stop_pidfile "logs/proxy_https.pid" "HTTPS proxy"
echo "$SUDO_PASS" | sudo -S pkill -f "src/proxy.py" 2>/dev/null || true
echo "$SUDO_PASS" | sudo -S pkill -f "src/proxy.py --https" 2>/dev/null || true
pkill -f "src/proxy.py" 2>/dev/null || true
pkill -f "highgravity_proxy.py" 2>/dev/null || true
pkill -f "lsp_shim" 2>/dev/null || true

# Cleanup iptables
echo "$SUDO_PASS" | sudo -S iptables -t nat -D OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998 2>/dev/null || true
echo -e "${GREEN}[✓] Proxy stop sequence sent and iptables cleaned${NC}"

echo -e "${BLUE}[*] Stopping Khoj...${NC}"
if [ -f "logs/khoj_docker.pid" ] || [ -f "data/khoj.pid" ]; then
    stop_pidfile "logs/khoj_docker.pid" "Khoj docker launcher"
    docker stop khoj khoj-pg >/dev/null 2>&1 || true
    bash scripts/internal/khoj_stop.sh 2>/dev/null || true
    echo -e "${GREEN}[✓] Khoj stop sequence sent${NC}"
else
    pkill -f "khoj.*--port.*42110" && echo -e "${GREEN}[✓] Khoj stopped${NC}" || echo -e "${YELLOW}[!] Khoj not running${NC}"
fi

# Verify
sleep 1
echo ""
echo -e "${CYAN}[*] Final Status:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if lsof -i:9998 >/dev/null 2>&1; then
    echo -e "  Proxy:     ${RED}✗ STILL RUNNING${NC}"
else
    echo -e "  Proxy:     ${GREEN}✓ STOPPED${NC}"
fi

if ss -ltn "( sport = :42110 )" 2>/dev/null | tail -n +2 | grep -q ":42110 "; then
    echo -e "  Khoj:      ${RED}✗ STILL RUNNING${NC}"
else
    echo -e "  Khoj:      ${GREEN}✓ STOPPED${NC}"
fi

if pgrep -f "hg.py" >/dev/null 2>&1; then
    echo -e "  Dashboard: ${RED}✗ STILL RUNNING${NC}"
else
    echo -e "  Dashboard: ${GREEN}✓ STOPPED${NC}"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}[✓] Shutdown complete${NC}"
