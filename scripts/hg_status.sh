#!/bin/bash
# HIGH-GRAVITY Status Checker
# Quick health check for all services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

if [ "${1:-}" != "--direct" ]; then
    exec bash "$SCRIPT_DIR/../hg.sh" status
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

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

port_listening() {
    ss -ltn "( sport = :$1 )" 2>/dev/null | tail -n +2 | grep -q ":$1 "
}

listener_pid() {
    ss -ltnp "( sport = :$1 )" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1
}

binary_patched() {
    local bin="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64.real"
    [ -f "$bin" ] && strings "$bin" 2>/dev/null | grep -q "https://proxy.windsurf.com"
}

js_patched() {
    local ext="/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js"
    [ -f "$ext" ] && strings "$ext" 2>/dev/null | grep -q "globalThis.HG_OPT"
}

echo -e "${CYAN}HIGH-GRAVITY System Status${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Proxy
if port_listening 9999; then
    PROXY_PID=$(pidfile_read "logs/proxy.pid" 2>/dev/null || true)
    [ -z "$PROXY_PID" ] && PROXY_PID=$(listener_pid 9999)
    [ -z "$PROXY_PID" ] && PROXY_PID="unknown"
    echo -e "Proxy:     ${GREEN}✓ HTTP RUNNING${NC} (PID: $PROXY_PID, Port: 9999)"
    if curl -s http://127.0.0.1:9999/hg/telemetry >/dev/null 2>&1; then
        echo -e "           ${GREEN}✓ Responding to requests${NC}"
        TELEMETRY=$(curl -s http://127.0.0.1:9999/hg/telemetry 2>/dev/null)
        if [ -n "$TELEMETRY" ]; then
            LAT=$(echo "$TELEMETRY" | python3 -c "import sys,json; t=json.load(sys.stdin); l=t.get('latency_ms',{}); print(f\"p50={l.get('p50')} p95={l.get('p95')} p99={l.get('p99')}\")" 2>/dev/null)
            echo -e "           Latency: $LAT"
        fi
    else
        echo -e "           ${YELLOW}! Not responding${NC}"
    fi
else
    echo -e "Proxy:     ${RED}✗ HTTP OFFLINE${NC}"
fi

if [ -f "certs/proxy.crt" ] && [ -f "certs/proxy.key" ]; then
    if port_listening 443; then
        HTTPS_PID=$(pidfile_read "logs/proxy_https.pid" 2>/dev/null || true)
        [ -z "$HTTPS_PID" ] && HTTPS_PID=$(listener_pid 443)
        [ -z "$HTTPS_PID" ] && HTTPS_PID="unknown"
        echo -e "Proxy TLS: ${GREEN}✓ HTTPS RUNNING${NC} (PID: $HTTPS_PID, Port: 443)"
    elif pidfile_alive "logs/proxy_https.pid"; then
        echo -e "Proxy TLS: ${YELLOW}! PID alive but port 443 not bound${NC}"
    else
        echo -e "Proxy TLS: ${RED}✗ HTTPS OFFLINE${NC}"
    fi
else
    echo -e "Proxy TLS: ${YELLOW}○ SKIPPED${NC} (certs missing)"
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
    if js_patched; then
        echo -e "           ${GREEN}✓ MITM patch loaded${NC}"
    else
        echo -e "           ${CYAN}i MITM patch not loaded yet${NC}"
    fi
    LS_PID=$(pgrep -f "language_server_linux_x64" | head -1)
    if [ -n "$LS_PID" ]; then
        API_URL=$(ps aux | grep language_server_linux_x64 | grep -v grep | head -1 | grep -oP '\-\-api_server_url \S+' | awk '{print $2}')
        INFER_URL=$(ps aux | grep language_server_linux_x64 | grep -v grep | head -1 | grep -oP '\-\-inference_api_server_url \S+' | awk '{print $2}')
        LS_AGE=$(ps -o etimes= -p "$LS_PID" 2>/dev/null | tr -d ' ')
        echo -e "           api_server_url: ${API_URL:-unknown}"
        echo -e "           inference_api_server_url: ${INFER_URL:-unknown}"
        if binary_patched; then
            echo -e "           ${GREEN}✓ Binary patch applied${NC}"
        else
            echo -e "           ${YELLOW}! Binary patch not detected${NC}"
        fi
        if echo "${INFER_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
            echo -e "           ${GREEN}✓ Proxy path active${NC}"
        else
            echo -e "           ${YELLOW}! Proxy path inactive${NC}"
        fi
        if echo "${API_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com' && \
           echo "${INFER_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
            echo -e "           ${GREEN}✓ Full proxy mode${NC}"
        elif ! echo "${API_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com' && \
             echo "${INFER_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
            echo -e "           ${CYAN}i Direct split: intentional${NC}"
            echo -e "           ${CYAN}  login/control-plane direct, inference proxied${NC}"
        elif ! echo "${API_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
            echo -e "           ${YELLOW}! DIRECT-only mode detected${NC}"
            if [ "${LS_AGE:-0}" -gt 90 ] 2>/dev/null; then
                echo -e "           ${RED}! Stale direct mode: reload/restart Windsurf${NC}"
            fi
        fi
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
