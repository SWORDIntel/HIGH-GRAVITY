#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"
PROXY_PORT="${HG_PROXY_PORT:-9998}"
PROXY_URL="http://127.0.0.1:${PROXY_PORT}"

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

# 1. Network & Proxy Check
if ss -ltn "( sport = :${PROXY_PORT} )" 2>/dev/null | tail -n +2 | grep -q ":${PROXY_PORT} "; then
  if curl -fsS --max-time 2 "${PROXY_URL}/hg/telemetry" >/dev/null 2>&1; then
    echo -e "Proxy ${PROXY_PORT}: ${GREEN}UP${NC}"
  else
    echo -e "Proxy ${PROXY_PORT}: ${YELLOW}DEGRADED${NC} (socket up, telemetry down)"
  fi
else
  echo -e "Proxy ${PROXY_PORT}: ${RED}DOWN${NC}"
fi

if lsof -i:443 >/dev/null 2>&1; then
  echo -e "Proxy 443:  ${GREEN}UP${NC}"
else
  echo -e "Proxy 443:  ${RED}DOWN${NC}"
fi

# 2. DNS Redirection Check (CSEC Shield)
echo -ne "DNS Shield: "
DOMAINS=("proxy.windsurf.com" "unleash.codeium.com" "api.codeium.com" "server.self-serve.windsurf.com")
MISSING=0
for d in "${DOMAINS[@]}"; do
  if ! grep -q "$d" /etc/hosts; then MISSING=$((MISSING+1)); fi
done
if [ $MISSING -eq 0 ]; then
  echo -e "${GREEN}WATERTIGHT${NC}"
else
  echo -e "${RED}LEAKING${NC} ($MISSING domains missing from /etc/hosts)"
fi

# 3. Intelligence Check
if curl -fsS --max-time 3 http://127.0.0.1:42110/api/health >/dev/null 2>&1; then
  echo -e "Khoj RAG:   ${GREEN}HEALTHY${NC}"
else
  echo -e "Khoj RAG:   ${YELLOW}OFFLINE${NC}"
fi

# 4. Binary Integrity Check
BIN_PATH="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64"
BIN_REAL_PATH="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64.real"
BIN_PATH_ACTIVE="$BIN_PATH"
[ -f "$BIN_REAL_PATH" ] && BIN_PATH_ACTIVE="$BIN_REAL_PATH"

if [ -f "$BIN_PATH_ACTIVE" ]; then
  if strings "$BIN_PATH_ACTIVE" | grep -q "proxy.windsurf.com"; then
    echo -e "Binary:     ${GREEN}PATCHED${NC} (v1.110.1 URLs)"
    patch_state="full"
  else
    patch_state="$(python3 - "$BIN_PATH_ACTIVE" <<'PY'
import sys

with open(sys.argv[1], 'rb') as fh:
    data = fh.read()

count_new = data.count(b'\x49\x39\xd3\xeb\x2e')
if count_new == 0:
    count_new = data.count(b'\x49\x39\xd3\x90\x90')

if count_new >= 3:
    print('full')
elif count_new > 0:
    print('partial')
else:
    print('none')
PY
)"
  fi

  if [ "${patch_state:-none}" = "full" ]; then
    echo -e "Binary:     ${GREEN}PATCHED${NC} (v1.110.1 machine-code marker)"
  elif [ "${patch_state:-none}" = "partial" ]; then
    echo -e "Binary:     ${YELLOW}PARTIAL${NC} (machine-code marker)"
  else
    echo -e "Binary:     ${RED}ORIGINAL${NC} (Bypass active!)"
  fi
else
  echo -e "Binary:     ${RED}NOT FOUND${NC}"
fi

# 5. Runtime Routing Check
LS_CMD="$(ps aux | grep language_server_linux_x64 | grep -v grep | head -1 || true)"
if [ -n "$LS_CMD" ]; then
  API_URL="$(echo "$LS_CMD" | grep -oP '\-\-api_server_url \S+' | awk '{print $2}' || echo "")"
  INF_URL="$(echo "$LS_CMD" | grep -oP '\-\-inference_api_server_url \S+' | awk '{print $2}' || echo "")"
  LS_PID="$(pgrep -f language_server_linux_x64 | head -1)"
  LS_AGE="$(ps -o etimes= -p "$LS_PID" 2>/dev/null | tr -d ' ' || echo 0)"
  echo "LS api_server_url:       ${API_URL:-unknown}"
  echo "LS inference_api_url:    ${INF_URL:-unknown}"
  if echo "${API_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com' && \
     echo "${INF_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
    echo -e "LS routing mode: ${GREEN}PROXIED${NC}"
  elif echo "${API_URL:-}" | grep -q 'server.self-serve.windsurf.com' && \
       echo "${INF_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
    echo -e "LS routing mode: ${CYAN}SPLIT (intentional)${NC} (api direct, inference proxied)"
  else
    echo -e "LS routing mode: ${YELLOW}DIRECT${NC} (age=${LS_AGE}s)"
  fi
else
  echo -e "LS routing mode: ${YELLOW}LS not running${NC}"
fi

echo ""
echo "Telemetry snapshot:"
curl -s "${PROXY_URL}/hg/telemetry" 2>/dev/null | jq -c '{active_keys,exhausted_keys,total_keys,total_requests,mitm_rate_limit_hits,latency_ms,slow_requests_recent,concurrent_requests,max_concurrent}' || echo "unavailable"

echo ""
echo "Recent upstream errors:"
if [ -f "logs/proxy.log" ]; then
  grep -Ei "RELAY_ERROR|Upstream unreachable|UPSTREAM_ERROR|AUTH_FLOW|BUNDLE_FOLLOWER|PULSE" logs/proxy.log | tail -n 20 || true
else
  echo "proxy.log not found"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
