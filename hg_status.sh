#!/bin/bash
# HIGH-GRAVITY Status Checker
# Quick health check for all services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}HIGH-GRAVITY System Status${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Proxy
if lsof -i:9999 >/dev/null 2>&1; then
    PROXY_PID=$(lsof -ti:9999)
    echo -e "Proxy:     ${GREEN}✓ RUNNING${NC} (PID: $PROXY_PID, Port: 9999)"
    
    # Test endpoint
    if curl -s http://127.0.0.1:9999/hg/telemetry >/dev/null 2>&1; then
        echo -e "           ${GREEN}✓ Responding to requests${NC}"
    else
        echo -e "           ${YELLOW}! Not responding${NC}"
    fi
else
    echo -e "Proxy:     ${RED}✗ OFFLINE${NC}"
fi

# Khoj
if lsof -i:42110 >/dev/null 2>&1; then
    KHOJ_PID=$(lsof -ti:42110)
    echo -e "Khoj:      ${GREEN}✓ RUNNING${NC} (PID: $KHOJ_PID, Port: 42110)"
    
    # Test health
    if curl -s http://127.0.0.1:42110/api/health >/dev/null 2>&1; then
        echo -e "           ${GREEN}✓ Healthy${NC}"
        
        # Get stats via proxy
        KHOJ_STATS=$(curl -s http://127.0.0.1:9999/hg/khoj/status 2>/dev/null)
        if [ $? -eq 0 ]; then
            SEARCHES=$(echo "$KHOJ_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('search_count', 0))" 2>/dev/null)
            INJECTIONS=$(echo "$KHOJ_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('injection_count', 0))" 2>/dev/null)
            echo -e "           Searches: $SEARCHES | Injections: $INJECTIONS"
        fi
    else
        echo -e "           ${YELLOW}! Starting up...${NC}"
    fi
else
    echo -e "Khoj:      ${YELLOW}○ OFFLINE${NC} (optional)"
fi

# Dashboard
if pgrep -f "hg.py" >/dev/null 2>&1; then
    DASH_PID=$(pgrep -f "hg.py")
    echo -e "Dashboard: ${GREEN}✓ RUNNING${NC} (PID: $DASH_PID)"
else
    echo -e "Dashboard: ${RED}✗ OFFLINE${NC}"
fi

# Windsurf
if pgrep -f "windsurf" >/dev/null 2>&1; then
    WS_PID=$(pgrep -f "windsurf-next" | head -1)
    echo -e "Windsurf:  ${GREEN}✓ RUNNING${NC} (PID: $WS_PID)"
    
    # Check if patched
    if strings /usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js 2>/dev/null | grep -q "globalThis.HG_OPT"; then
        echo -e "           ${GREEN}✓ MITM patch applied${NC}"
    else
        echo -e "           ${YELLOW}! MITM patch not detected${NC}"
    fi
else
    echo -e "Windsurf:  ${YELLOW}○ NOT RUNNING${NC}"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Log files
echo ""
echo -e "${CYAN}Recent Activity:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "logs/proxy.log" ]; then
    PROXY_LINES=$(wc -l < logs/proxy.log)
    LAST_PROXY=$(tail -1 logs/proxy.log 2>/dev/null | cut -d' ' -f1-2)
    echo -e "Proxy Log:  $PROXY_LINES lines (Last: $LAST_PROXY)"
fi

if [ -f "logs/cascade_midway.log" ]; then
    MITM_LINES=$(wc -l < logs/cascade_midway.log)
    if [ $MITM_LINES -gt 0 ]; then
        echo -e "MITM Log:   ${GREEN}$MITM_LINES events captured${NC}"
    else
        echo -e "MITM Log:   ${YELLOW}Empty (no Cascade requests yet)${NC}"
    fi
fi

if [ -f "logs/khoj.log" ]; then
    KHOJ_LINES=$(wc -l < logs/khoj.log)
    echo -e "Khoj Log:   $KHOJ_LINES lines"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
