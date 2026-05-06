#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

if [ "${1:-}" = "--watch" ] || [ "${1:-}" = "watch" ]; then
  shift || true
  exec bash "$SCRIPT_DIR/hg_trace.sh" "$@"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}HIGH-GRAVITY Doctor${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if lsof -i:9998 >/dev/null 2>&1; then
  echo -e "Proxy 9998: ${GREEN}UP${NC}"
else
  echo -e "Proxy 9998: ${RED}DOWN${NC}"
fi

if lsof -i:443 >/dev/null 2>&1; then
  echo -e "Proxy 443:  ${GREEN}UP${NC}"
else
  echo -e "Proxy 443:  ${RED}DOWN${NC}"
fi

if curl -fsS --max-time 3 http://127.0.0.1:42110/api/health >/dev/null 2>&1; then
  echo -e "Khoj:       ${GREEN}HEALTHY${NC}"
else
  echo -e "Khoj:       ${YELLOW}WARMING/OFFLINE${NC}"
fi

LS_CMD="$(ps aux | grep language_server_linux_x64 | grep -v grep | head -1 || true)"
if [ -n "$LS_CMD" ]; then
  API_URL="$(echo "$LS_CMD" | grep -oP '\-\-api_server_url \S+' | awk '{print $2}')"
  INF_URL="$(echo "$LS_CMD" | grep -oP '\-\-inference_api_server_url \S+' | awk '{print $2}')"
  LS_PID="$(pgrep -f language_server_linux_x64 | head -1)"
  LS_AGE="$(ps -o etimes= -p "$LS_PID" 2>/dev/null | tr -d ' ' || echo 0)"
  echo "LS api_server_url:       ${API_URL:-unknown}"
  echo "LS inference_api_url:    ${INF_URL:-unknown}"
  if echo "${API_URL:-}" | grep -q 'proxy.windsurf.com'; then
    echo -e "LS routing mode: ${GREEN}PROXIED${NC}"
  else
    echo -e "LS routing mode: ${YELLOW}DIRECT${NC} (age=${LS_AGE}s)"
  fi
else
  echo -e "LS routing mode: ${YELLOW}LS not running${NC}"
fi

echo ""
echo "Telemetry snapshot:"
curl -s http://127.0.0.1:9998/hg/telemetry 2>/dev/null | jq -c '{active_keys,exhausted_keys,total_keys,total_requests,mitm_rate_limit_hits,latency_ms,slow_requests_recent,concurrent_requests,max_concurrent}' || echo "unavailable"

echo ""
echo "Recent upstream errors:"
rg -n "UPSTREAM_ERROR|AUTH_FLOW|BUNDLE_FOLLOWER|PULSE" logs/proxy.log -S | tail -n 20 || true
