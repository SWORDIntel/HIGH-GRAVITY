#!/bin/bash
# HIGH-GRAVITY Universal Bootstrap
# Starts all services: Proxy, Khoj, Dashboard

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║            HIGH-GRAVITY BOOTSTRAP v1.0                     ║"
echo "║         Universal Startup for All Services                 ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if already running
check_running() {
    local service=$1
    local port=$2
    if lsof -i:$port >/dev/null 2>&1; then
        echo -e "${YELLOW}[!] $service already running on port $port${NC}"
        return 0
    fi
    return 1
}

# Kill existing processes
cleanup() {
    echo -e "${BLUE}[*] Cleaning up existing processes...${NC}"
    pkill -f "hg.py" 2>/dev/null || true
    pkill -f "src/proxy.py" 2>/dev/null || true
    pkill -f "tools/integration/highgravity_proxy.py" 2>/dev/null || true
    pkill -f "khoj.*--port.*42110" 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}[✓] Cleanup complete${NC}"
}

# Start Proxy
start_proxy() {
    echo -e "${BLUE}[*] Starting HIGH-GRAVITY Proxy...${NC}"
    
    if check_running "Proxy" 9999; then
        return 0
    fi
    
    mkdir -p logs
    PYTHONPATH=. nohup python3 src/proxy.py > logs/proxy.log 2>&1 &
    PROXY_PID=$!
    
    # Wait for proxy to be ready
    for i in {1..10}; do
        if lsof -i:9999 >/dev/null 2>&1; then
            echo -e "${GREEN}[✓] Proxy started (PID: $PROXY_PID, Port: 9999)${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}[✗] Proxy failed to start${NC}"
    return 1
}

# Start Khoj
start_khoj() {
    echo -e "${BLUE}[*] Starting Khoj Semantic Search...${NC}"
    
    if check_running "Khoj" 42110; then
        return 0
    fi
    
    if [ ! -d "khoj" ]; then
        echo -e "${YELLOW}[!] Khoj not found. Skipping...${NC}"
        echo -e "${YELLOW}    To enable: git clone https://github.com/khoj-ai/khoj.git${NC}"
        return 0
    fi
    
    bash bin/khoj_launcher.sh >/dev/null 2>&1 &
    
    # Wait for Khoj to be ready
    echo -e "${BLUE}[*] Waiting for Khoj to initialize...${NC}"
    for i in {1..30}; do
        if curl -s http://127.0.0.1:42110/api/health >/dev/null 2>&1; then
            echo -e "${GREEN}[✓] Khoj started (Port: 42110)${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${YELLOW}[!] Khoj startup timeout (may still be initializing)${NC}"
    return 0
}

# Start Dashboard
start_dashboard() {
    echo -e "${BLUE}[*] Starting hg.py Dashboard...${NC}"
    
    if pgrep -f "hg.py" >/dev/null 2>&1; then
        echo -e "${YELLOW}[!] Dashboard already running${NC}"
        return 0
    fi
    
    # Start in background, will take over terminal
    python3 hg.py &
    DASHBOARD_PID=$!
    sleep 2
    
    if ps -p $DASHBOARD_PID >/dev/null 2>&1; then
        echo -e "${GREEN}[✓] Dashboard started (PID: $DASHBOARD_PID)${NC}"
        return 0
    else
        echo -e "${RED}[✗] Dashboard failed to start${NC}"
        return 1
    fi
}

# Verify services
verify_services() {
    echo ""
    echo -e "${CYAN}[*] Service Status:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Proxy
    if lsof -i:9999 >/dev/null 2>&1; then
        echo -e "  Proxy:     ${GREEN}✓ RUNNING${NC} (http://127.0.0.1:9999)"
    else
        echo -e "  Proxy:     ${RED}✗ OFFLINE${NC}"
    fi
    
    # Khoj
    if curl -s http://127.0.0.1:42110/api/health >/dev/null 2>&1; then
        echo -e "  Khoj:      ${GREEN}✓ RUNNING${NC} (http://127.0.0.1:42110)"
    else
        echo -e "  Khoj:      ${YELLOW}○ OFFLINE${NC} (optional)"
    fi
    
    # Dashboard
    if pgrep -f "hg.py" >/dev/null 2>&1; then
        echo -e "  Dashboard: ${GREEN}✓ RUNNING${NC}"
    else
        echo -e "  Dashboard: ${RED}✗ OFFLINE${NC}"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Show usage info
show_info() {
    echo ""
    echo -e "${CYAN}[*] Quick Reference:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "  ${BLUE}Dashboard Controls:${NC}"
    echo "    P - Toggle Pegasus panel"
    echo "    E - Toggle Pegasus + Khoj panels"
    echo "    A - Toggle Aliases"
    echo "    Q - Quit dashboard"
    echo ""
    echo -e "  ${BLUE}Logs:${NC}"
    echo "    Proxy:  tail -f logs/proxy.log"
    echo "    Khoj:   tail -f logs/khoj.log"
    echo "    MITM:   tail -f logs/cascade_midway.log"
    echo ""
    echo -e "  ${BLUE}Endpoints:${NC}"
    echo "    Proxy Status:  curl http://127.0.0.1:9999/hg/telemetry"
    echo "    Khoj Status:   curl http://127.0.0.1:9999/hg/khoj/status"
    echo "    Khoj Reindex:  curl -X POST http://127.0.0.1:9999/hg/khoj/reindex"
    echo ""
    echo -e "  ${BLUE}Stop All:${NC}"
    echo "    bash hg_stop.sh"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Main execution
main() {
    # Parse arguments
    CLEAN=false
    NO_DASHBOARD=false
    NO_KHOJ=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                CLEAN=true
                shift
                ;;
            --no-dashboard)
                NO_DASHBOARD=true
                shift
                ;;
            --no-khoj)
                NO_KHOJ=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --clean         Kill existing processes before starting"
                echo "  --no-dashboard  Start proxy/khoj only (no dashboard)"
                echo "  --no-khoj       Skip Khoj startup"
                echo "  --help, -h      Show this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Cleanup if requested
    if [ "$CLEAN" = true ]; then
        cleanup
    fi
    
    # Start services
    start_proxy || exit 1
    
    if [ "$NO_KHOJ" = false ]; then
        start_khoj
    fi
    
    # Verify
    verify_services
    show_info
    
    # Start dashboard (foreground)
    if [ "$NO_DASHBOARD" = false ]; then
        echo -e "${CYAN}[*] Launching dashboard in 3 seconds...${NC}"
        echo -e "${YELLOW}    Press Ctrl+C now to cancel${NC}"
        sleep 3
        echo ""
        exec python3 hg.py
    else
        echo -e "${GREEN}[✓] All services started in background${NC}"
        echo -e "${CYAN}[*] Run 'python3 hg.py' to start dashboard${NC}"
    fi
}

# Run
main "$@"
