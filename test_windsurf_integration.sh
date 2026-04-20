#!/bin/bash
# Test Windsurf + Proxy + MITM Integration
# Verifies all components are functional

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Windsurf Integration Test Suite                       ║"
echo "║     Proxy + MITM + UI Verification                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Test 1: Proxy Running
echo -e "${BLUE}[1/7] Testing Proxy...${NC}"
if lsof -i:9999 >/dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Proxy running on port 9999${NC}"
else
    echo -e "${RED}  ✗ Proxy not running${NC}"
    exit 1
fi

# Test 2: Proxy Responding
echo -e "${BLUE}[2/7] Testing Proxy API...${NC}"
RESPONSE=$(curl -s http://127.0.0.1:9999/hg/telemetry)
if echo "$RESPONSE" | grep -q "status"; then
    echo -e "${GREEN}  ✓ Proxy API responding${NC}"
else
    echo -e "${RED}  ✗ Proxy API not responding${NC}"
    exit 1
fi

# Test 3: DNS Resolution
echo -e "${BLUE}[3/7] Testing DNS (shield.windsurf.com)...${NC}"
if grep -q "shield.windsurf.com" /etc/hosts; then
    echo -e "${GREEN}  ✓ shield.windsurf.com → 127.0.0.1${NC}"
else
    echo -e "${YELLOW}  ! shield.windsurf.com not in /etc/hosts${NC}"
    echo -e "${YELLOW}    Add: 127.0.0.1 shield.windsurf.com${NC}"
fi

# Test 4: MITM Patch
echo -e "${BLUE}[4/7] Testing MITM Patch...${NC}"
if strings /usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js 2>/dev/null | grep -q "globalThis.HG_OPT"; then
    echo -e "${GREEN}  ✓ MITM patch applied (HG_OPT found)${NC}"
else
    echo -e "${RED}  ✗ MITM patch not found${NC}"
    echo -e "${YELLOW}    Run: python3 src/patch_windsurf_client.py${NC}"
fi

# Test 5: Windsurf Running
echo -e "${BLUE}[5/7] Testing Windsurf Process...${NC}"
if pgrep -f "windsurf" >/dev/null 2>&1; then
    WS_PID=$(pgrep -f "windsurf-next" | head -1)
    echo -e "${GREEN}  ✓ Windsurf running (PID: $WS_PID)${NC}"
else
    echo -e "${YELLOW}  ! Windsurf not running${NC}"
fi

# Test 6: Dashboard
echo -e "${BLUE}[6/7] Testing Dashboard...${NC}"
if pgrep -f "hg.py" >/dev/null 2>&1; then
    DASH_PID=$(pgrep -f "hg.py")
    echo -e "${GREEN}  ✓ Dashboard running (PID: $DASH_PID)${NC}"
else
    echo -e "${YELLOW}  ! Dashboard not running${NC}"
    echo -e "${YELLOW}    Run: python3 hg.py${NC}"
fi

# Test 7: Khoj Integration
echo -e "${BLUE}[7/7] Testing Khoj Integration...${NC}"
KHOJ_STATUS=$(curl -s http://127.0.0.1:9999/hg/khoj/status 2>/dev/null)
if echo "$KHOJ_STATUS" | grep -q "healthy"; then
    HEALTHY=$(echo "$KHOJ_STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('healthy', False))" 2>/dev/null)
    if [ "$HEALTHY" = "True" ]; then
        echo -e "${GREEN}  ✓ Khoj healthy and integrated${NC}"
    else
        echo -e "${YELLOW}  ! Khoj offline${NC}"
    fi
else
    echo -e "${YELLOW}  ! Khoj status unavailable${NC}"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Test Results Summary${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check logs
echo -e "${BLUE}Log Status:${NC}"
PROXY_LINES=$(wc -l < logs/proxy.log 2>/dev/null || echo 0)
MITM_LINES=$(wc -l < logs/cascade_midway.log 2>/dev/null || echo 0)
KHOJ_LINES=$(wc -l < logs/khoj.log 2>/dev/null || echo 0)

echo "  Proxy Log:  $PROXY_LINES lines"
echo "  MITM Log:   $MITM_LINES lines"
echo "  Khoj Log:   $KHOJ_LINES lines"

if [ $MITM_LINES -eq 0 ]; then
    echo ""
    echo -e "${YELLOW}[!] MITM log is empty${NC}"
    echo -e "${YELLOW}    This is normal if you haven't used Cascade yet${NC}"
    echo -e "${YELLOW}    To test: Open Windsurf → Ctrl+L → Ask a question${NC}"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Manual Tests${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}1. Test Proxy Routing:${NC}"
echo "   curl http://shield.windsurf.com:9999/hg/telemetry"
echo ""
echo -e "${BLUE}2. Test Cascade (in Windsurf):${NC}"
echo "   - Press Ctrl+L"
echo "   - Ask: 'Hello, how are you?'"
echo "   - Watch: tail -f logs/cascade_midway.log"
echo ""
echo -e "${BLUE}3. Test Dashboard:${NC}"
echo "   - Press 'E' to toggle Khoj panel"
echo "   - Press 'P' to toggle Pegasus panel"
echo "   - Press 'Q' to quit"
echo ""
echo -e "${GREEN}[✓] Integration test complete!${NC}"
