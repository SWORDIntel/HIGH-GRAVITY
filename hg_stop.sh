#!/bin/bash
# HIGH-GRAVITY Universal Shutdown
# Stops all services gracefully

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          HIGH-GRAVITY Shutdown Sequence                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Stop Dashboard
echo -e "${BLUE}[*] Stopping Dashboard...${NC}"
pkill -f "hg.py" && echo -e "${GREEN}[✓] Dashboard stopped${NC}" || echo -e "${YELLOW}[!] Dashboard not running${NC}"

# Stop Proxy
echo -e "${BLUE}[*] Stopping Proxy...${NC}"
pkill -f "src/proxy.py" && echo -e "${GREEN}[✓] Proxy stopped${NC}" || echo -e "${YELLOW}[!] Proxy not running${NC}"
pkill -f "tools/integration/highgravity_proxy.py" 2>/dev/null

# Stop Khoj
echo -e "${BLUE}[*] Stopping Khoj...${NC}"
if [ -f "data/khoj.pid" ]; then
    bash bin/khoj_stop.sh
else
    pkill -f "khoj.*--port.*42110" && echo -e "${GREEN}[✓] Khoj stopped${NC}" || echo -e "${YELLOW}[!] Khoj not running${NC}"
fi

# Verify
sleep 1
echo ""
echo -e "${CYAN}[*] Final Status:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if lsof -i:9999 >/dev/null 2>&1; then
    echo -e "  Proxy:     ${RED}✗ STILL RUNNING${NC}"
else
    echo -e "  Proxy:     ${GREEN}✓ STOPPED${NC}"
fi

if lsof -i:42110 >/dev/null 2>&1; then
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
