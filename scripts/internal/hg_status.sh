#!/bin/bash
# HIGH-GRAVITY Status Checker
# Quick health check for all services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SCRIPT_DIR"
PROXY_PORT="${HG_PROXY_PORT:-9998}"
PROXY_URL="http://127.0.0.1:${PROXY_PORT}"
HG_MICROPROXY_FRONT="${HG_MICROPROXY_FRONT:-1}"
HG_PROXY_HTTPS_PORT="${HG_PROXY_HTTPS_PORT:-443}"
HG_PROXY_INTERNAL_HTTPS_PORT="${HG_PROXY_INTERNAL_HTTPS_PORT:-9443}"
HG_MICROPROXY_FRONT_LISTEN="${HG_MICROPROXY_FRONT_LISTEN:-0.0.0.0:443}"
HG_MICROPROXY_FRONT_UPSTREAM="${HG_MICROPROXY_FRONT_UPSTREAM:-127.0.0.1:${HG_PROXY_INTERNAL_HTTPS_PORT}}"
HG_MICROPROXY_DIRECT_UPSTREAM="${HG_MICROPROXY_DIRECT_UPSTREAM:-}"
HG_MICROPROXY_DIRECT_HOT_PATH="${HG_MICROPROXY_DIRECT_HOT_PATH:-0}"
HG_MICROPROXY_HOT_PATH_OBSERVE="${HG_MICROPROXY_HOT_PATH_OBSERVE:-0}"

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

process_args() {
    local pid="$1"
    [ -n "$pid" ] || return 1
    ps -p "$pid" -o args= 2>/dev/null | sed 's/^[[:space:]]*//'
}

cmdline_flag_value() {
    local args="$1"
    local flag="$2"
    local rest
    rest="${args#*${flag} }"
    if [ "$rest" != "$args" ]; then
        printf '%s\n' "${rest%% *}"
    fi
}

cmdline_flag_present() {
    local args="$1"
    local flag="$2"
    case "$args" in
        *"$flag"*)
            return 0
            ;;
    esac
    return 1
}

port_listening() {
    ss -ltn "( sport = :$1 )" 2>/dev/null | tail -n +2 | grep -q ":$1 "
}

listener_pid() {
    ss -ltnp "( sport = :$1 )" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1
}

language_server_direct_egress() {
    ss -tanpH state established '( dport = :443 )' 2>/dev/null \
        | awk '
            /language_server/ {
                peer = ""
                for (i = 1; i <= NF; i++) {
                    if ($i ~ /:443$/ || $i ~ /:https$/) {
                        if ($i !~ /^127[.]0[.]0[.]1:/ && $i !~ /^\[::1\]:/) {
                            peer = $i
                        }
                    }
                }
                if (peer != "") print peer " " $0
            }
        '
}

microproxy_front_enabled() {
    if [ "$HG_MICROPROXY_FRONT" = "1" ] || [ "$HG_MICROPROXY_FRONT" = "true" ]; then
        return 0
    fi
    local pid args
    pid="$(pidfile_read "logs/microproxy_front.pid" 2>/dev/null || true)"
    [ -n "$pid" ] || return 1
    args="$(process_args "$pid" 2>/dev/null || true)"
    [ -n "$args" ] && cmdline_flag_present "$args" "--relay"
}

microproxy_front_cmdline() {
    local pid
    pid="$(pidfile_read "logs/microproxy_front.pid" 2>/dev/null || true)"
    [ -n "$pid" ] || return 1
    process_args "$pid" 2>/dev/null || true
}

FRONT_CMDLINE="$(microproxy_front_cmdline 2>/dev/null || true)"
if [ -n "$FRONT_CMDLINE" ]; then
    if [ "$HG_MICROPROXY_FRONT" = "0" ] || [ "$HG_MICROPROXY_FRONT" = "false" ] || [ -z "$HG_MICROPROXY_FRONT" ]; then
        if cmdline_flag_present "$FRONT_CMDLINE" "--relay"; then
            HG_MICROPROXY_FRONT="1"
        fi
    fi
    if [ -z "$HG_MICROPROXY_FRONT_LISTEN" ] || [ "$HG_MICROPROXY_FRONT_LISTEN" = "0.0.0.0:443" ]; then
        value="$(cmdline_flag_value "$FRONT_CMDLINE" "--listen" || true)"
        [ -n "$value" ] && HG_MICROPROXY_FRONT_LISTEN="$value"
    fi
    if [ -z "$HG_MICROPROXY_FRONT_UPSTREAM" ] || [ "$HG_MICROPROXY_FRONT_UPSTREAM" = "127.0.0.1:${HG_PROXY_INTERNAL_HTTPS_PORT}" ]; then
        value="$(cmdline_flag_value "$FRONT_CMDLINE" "--upstream" || true)"
        [ -n "$value" ] && HG_MICROPROXY_FRONT_UPSTREAM="$value"
    fi
    if [ -z "$HG_MICROPROXY_DIRECT_UPSTREAM" ]; then
        value="$(cmdline_flag_value "$FRONT_CMDLINE" "--direct-upstream" || true)"
        [ -n "$value" ] && HG_MICROPROXY_DIRECT_UPSTREAM="$value"
    fi
    if [ "$HG_MICROPROXY_DIRECT_HOT_PATH" = "0" ] && cmdline_flag_present "$FRONT_CMDLINE" "--direct-hot-path"; then
        HG_MICROPROXY_DIRECT_HOT_PATH="1"
    fi
    if [ "$HG_MICROPROXY_HOT_PATH_OBSERVE" = "0" ] && cmdline_flag_present "$FRONT_CMDLINE" "--hot-path-observe"; then
        HG_MICROPROXY_HOT_PATH_OBSERVE="1"
    fi
fi

endpoint_port() {
    local endpoint="$1"
    local port="${endpoint##*:}"

    if [ "$port" = "$endpoint" ] || ! [[ "$port" =~ ^[0-9]+$ ]]; then
        return 1
    fi

    printf '%s\n' "$port"
}

binary_patched() {
    local bin_real="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64.real"
    local bin_std="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64"
    local target=""

    # prefer real binary if shim exists, else use active binary
    [ -f "$bin_real" ] && target="$bin_real"
    [ -z "$target" ] && [ -f "$bin_std" ] && target="$bin_std"

    [ -z "$target" ] && return 1
    [ -f "$target" ] || return 1

    # Legacy/legacy+textual marker check
    if strings "$target" 2>/dev/null | grep -q "https://proxy.windsurf.com\|proxy.windsurf.com"; then
        echo "full"
        return 0
    fi

    # Modern marker: machine-code NOP/JMP rewrite used by current patcher
    local patch_state
    patch_state="$(python3 - "$target" <<'PY'
import sys

path = sys.argv[1]
with open(path, "rb") as fh:
    data = fh.read()

count_new = data.count(b"\x49\x39\xd3\xeb\x2e")
count_old = data.count(b"\x49\x39\xd3\x74\x2e")

if count_new == 0:
    # Also support older marker style
    count_new = data.count(b"\x49\x39\xd3\x90\x90")

if count_new == 0 and count_old > 0:
    print("none")
    sys.exit(1)

if count_new >= 3:
    print("full")
    sys.exit(0)
elif count_new > 0:
    print("partial")
    sys.exit(0)

print("none")
sys.exit(1)
PY
)"
    case "$patch_state" in
      full|partial)
        echo "$patch_state"
        return 0
        ;;
    esac
    return 1
}

js_patched() {
    local ext="/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js"
    [ -f "$ext" ] || return 1
    if strings "$ext" 2>/dev/null | grep -Eq "https://api\\.codeium\\.com|https://server\\.codeium\\.com|https://inference\\.codeium\\.com|https://server\\.self-serve\\.windsurf\\.com"; then
        return 1
    fi
    strings "$ext" 2>/dev/null | grep -Eq "https://proxy\\.windsurf\\.com|https://inferapi\\.windsurf\\.com"
}

lsp_shim_active() {
    local shim="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64"
    if [ -f "$shim" ] && grep -q "language_server_linux_x64.real" "$shim" 2>/dev/null; then
        echo "active"
        return 0
    fi
    return 1
}

echo -e "${CYAN}HIGH-GRAVITY System Status${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Proxy
if port_listening "${PROXY_PORT}"; then
    PROXY_PID=$(pidfile_read "logs/proxy.pid" 2>/dev/null || true)
    [ -z "$PROXY_PID" ] && PROXY_PID=$(listener_pid "${PROXY_PORT}")
    [ -z "$PROXY_PID" ] && PROXY_PID="unknown"
    echo -e "Proxy:     ${GREEN}✓ HTTP RUNNING${NC} (PID: $PROXY_PID, Port: ${PROXY_PORT})"
    TELEMETRY="$(curl -s --max-time 2 "${PROXY_URL}/hg/telemetry" 2>/dev/null || true)"
    if [ -n "$TELEMETRY" ]; then
        echo -e "           ${GREEN}✓ Responding to requests${NC}"
        LAT=$(echo "$TELEMETRY" | python3 -c "import sys,json; t=json.load(sys.stdin); l=t.get('latency_ms',{}); print(f\"p50={l.get('p50')} p95={l.get('p95')} p99={l.get('p99')}\")" 2>/dev/null)
        echo -e "           Latency: ${LAT:-n/a}"
        RUNTIME_SUMMARY="$(python3 - "$TELEMETRY" <<'PY' 2>/dev/null
import json
import sys

try:
    payload = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)

shared = payload.get("shared_metrics") if isinstance(payload.get("shared_metrics"), dict) else {}

def num(key):
    try:
        return int(shared.get(key, payload.get(key, 0)) or 0)
    except Exception:
        return 0

mode = payload.get("upstream_inference_mode") or shared.get("upstream_inference_mode") or "unknown"
exact_hits = num("exact_response_cache_hits")
exact_stores = num("exact_response_cache_stores")
canonical_hits = num("canonical_response_cache_hits")
canonical_stores = num("canonical_response_cache_stores")
forwards = num("upstream_inference_forwards")
misses = num("upstream_inference_cache_misses")
blocks = num("upstream_inference_blocks") + num("upstream_inference_cache_only_blocks")
acks = num("local_ack_telemetry")
ack_bytes = num("local_ack_bytes_avoided")
print(f"           Runtime mode: {mode}")
print(f"           Response cache: {exact_hits + canonical_hits} hit / {exact_stores + canonical_stores} store")
print(f"           Upstream gate: {forwards} forward / {misses} miss / {blocks} block")
print(f"           Local ACK: {acks} req / {ack_bytes // 1024} KiB avoided")
PY
)"
        if [ -n "$RUNTIME_SUMMARY" ]; then
            echo "$RUNTIME_SUMMARY"
        fi
    else
        echo -e "           ${YELLOW}! Telemetry not responding${NC}"
    fi
else
    if pidfile_alive "logs/proxy.pid"; then
        echo -e "Proxy:     ${YELLOW}! HTTP RESTARTING${NC} (pid still alive, socket not yet bound)"
    else
        echo -e "Proxy:     ${RED}✗ HTTP OFFLINE${NC}"
    fi
fi

if [ -f "certs/proxy.crt" ] && [ -f "certs/proxy.key" ]; then
    TLS_PORT="$HG_PROXY_HTTPS_PORT"
    microproxy_front_enabled && TLS_PORT="$HG_PROXY_INTERNAL_HTTPS_PORT"
    if port_listening "$TLS_PORT"; then
        HTTPS_PID=$(pidfile_read "logs/proxy_https.pid" 2>/dev/null || true)
        [ -z "$HTTPS_PID" ] && HTTPS_PID=$(listener_pid "$TLS_PORT")
        [ -z "$HTTPS_PID" ] && HTTPS_PID="unknown"
        if microproxy_front_enabled; then
            echo -e "Proxy TLS: ${GREEN}✓ HTTPS RUNNING${NC} (PID: $HTTPS_PID, Port: ${TLS_PORT}, internal)"
        else
            echo -e "Proxy TLS: ${GREEN}✓ HTTPS RUNNING${NC} (PID: $HTTPS_PID, Port: ${TLS_PORT})"
        fi
    elif pidfile_alive "logs/proxy_https.pid"; then
        echo -e "Proxy TLS: ${YELLOW}! TLS RESTARTING${NC} (pid alive, socket not yet bound)"
    else
        echo -e "Proxy TLS: ${RED}✗ HTTPS OFFLINE${NC}"
    fi
    FRONT_PORT="$(endpoint_port "$HG_MICROPROXY_FRONT_LISTEN" 2>/dev/null || printf '443')"
    if microproxy_front_enabled; then
        if port_listening "$FRONT_PORT"; then
            FRONT_PID=$(pidfile_read "logs/microproxy_front.pid" 2>/dev/null || true)
            [ -z "$FRONT_PID" ] && FRONT_PID=$(listener_pid "$FRONT_PORT")
            [ -z "$FRONT_PID" ] && FRONT_PID="unknown"
            echo -e "C Front:   ${GREEN}✓ TLS RELAY RUNNING${NC} (PID: $FRONT_PID, ${HG_MICROPROXY_FRONT_LISTEN}→${HG_MICROPROXY_FRONT_UPSTREAM})"
        elif pidfile_alive "logs/microproxy_front.pid"; then
            echo -e "C Front:   ${YELLOW}! RELAY PROCESS UP, LISTENER DOWN${NC} (pid $(pidfile_read "logs/microproxy_front.pid"), expected ${HG_MICROPROXY_FRONT_LISTEN}→${HG_MICROPROXY_FRONT_UPSTREAM})"
        elif [ -f "logs/microproxy_front.pid" ]; then
            echo -e "C Front:   ${RED}✗ TLS RELAY OFFLINE${NC} (stale pid file, expected ${HG_MICROPROXY_FRONT_LISTEN}→${HG_MICROPROXY_FRONT_UPSTREAM})"
        else
            echo -e "C Front:   ${RED}✗ TLS RELAY OFFLINE${NC} (expected ${HG_MICROPROXY_FRONT_LISTEN}→${HG_MICROPROXY_FRONT_UPSTREAM})"
        fi
    elif pidfile_alive "logs/microproxy_front.pid"; then
        echo -e "C Front:   ${YELLOW}! RUNNING BUT DISABLED BY ENV${NC} (pid $(pidfile_read "logs/microproxy_front.pid"))"
    elif port_listening "$FRONT_PORT"; then
        FRONT_PID=$(listener_pid "$FRONT_PORT")
        [ -z "$FRONT_PID" ] && FRONT_PID="unknown"
        FRONT_HINT="(likely Python HTTPS listener; relay disabled in environment)"
        echo -e "C Front:   ${YELLOW}! LISTENER ACTIVE BUT DISABLED BY ENV${NC} (PID: $FRONT_PID, Port: $FRONT_PORT) $FRONT_HINT"
    elif [ -f "logs/microproxy_front.pid" ]; then
        echo -e "C Front:   ${YELLOW}! DISABLED WITH STALE PID FILE${NC} ($(pidfile_read "logs/microproxy_front.pid" 2>/dev/null || true))"
    fi
else
    echo -e "Proxy TLS: ${YELLOW}○ SKIPPED${NC} (certs missing)"
fi

if port_listening "${PROXY_PORT}"; then
    MICROPROXY_STATUS="$(curl -s --max-time 2 "${PROXY_URL}/hg/microproxy/status" 2>/dev/null || true)"
    if [ -n "$MICROPROXY_STATUS" ]; then
        MICROPROXY_LINES="$(python3 - "$MICROPROXY_STATUS" <<'PY' 2>/dev/null
import json
import sys

try:
    status = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)

def as_dict(value):
    return value if isinstance(value, dict) else {}

def fmt_counts(value):
    counts = as_dict(value)
    if not counts:
        return "none"
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))

def one_line(value, limit=96):
    text = str(value or "").replace("\n", " ").replace("\r", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."

reader = as_dict(status.get("reader"))
classifier = as_dict(status.get("classifier"))
fast_path = as_dict(status.get("fast_path_candidates"))
upstream_errors = as_dict(status.get("upstream_errors"))
direct_fast_path = as_dict(status.get("direct_fast_path"))
direct_usage = as_dict(direct_fast_path.get("usage"))
direct_canary = as_dict(direct_fast_path.get("canary"))
direct_last_failure = as_dict(direct_fast_path.get("last_failure"))
streams = as_dict(status.get("streams"))
backpressure = as_dict(status.get("backpressure"))
recent_errors = upstream_errors.get("recent") if isinstance(upstream_errors.get("recent"), list) else []

rows = reader.get("rows", 0)
invalid = reader.get("invalid_rows", 0)
print(f"C Edge:    Observer rows={rows} invalid={invalid}")
print(
    "           Classifier: "
    f"seen={fmt_counts(classifier.get('request_seen_by_class'))} | "
    f"routes={fmt_counts(classifier.get('route_selected_by_class'))}"
)
print(
    "           Fast path candidates: "
    f"total={fast_path.get('total', 0)} | "
    f"classes={fmt_counts(fast_path.get('by_class'))} | "
    f"candidates={fmt_counts(fast_path.get('by_candidate'))}"
)

error_total = upstream_errors.get("total", 0)
print(
    "           Upstream errors: "
    f"total={error_total} | "
    f"types={fmt_counts(upstream_errors.get('error_types'))} | "
    f"upstreams={fmt_counts(upstream_errors.get('upstreams'))}"
)
print(
    "           Stream signals: "
    f"finished={streams.get('streams_finished', 0)} | "
    f"open={streams.get('streams_open', 0)} | "
    f"quota_exhausted={streams.get('quota_exhausted_signals', 0)} | "
    f"connect_error={streams.get('connect_error_signals', 0)}"
)
print(
    "           Backpressure: "
    f"events={backpressure.get('total', 0)} | "
    f"max_active_seen={backpressure.get('max_active_seen', 0)} | "
    f"limit={backpressure.get('max_active_streams', 0)} | "
    f"wait_ms={backpressure.get('wait_ms_total', 0)}"
)
print(
    "           Direct fast path: "
    f"target={one_line(direct_fast_path.get('target') or direct_fast_path.get('upstream'), 48)} | "
    f"configured={direct_fast_path.get('configured')} active={direct_fast_path.get('active')} cooled_down={direct_fast_path.get('cooled_down')} | "
    f"state={one_line(direct_fast_path.get('state'), 24)} health={one_line(direct_fast_path.get('health_state') or direct_fast_path.get('health'), 24)}"
)
print(
    "           Direct usage: "
    f"total={direct_usage.get('total', 0)} | "
    f"direct={direct_usage.get('direct_upstream', 0)} | "
    f"fallbacks={direct_usage.get('python_fallback', 0)} | "
    f"passthrough={direct_usage.get('passthrough', 0)}"
)
if direct_canary:
    print(
        "           Canary: "
        f"{fmt_counts(direct_canary)}"
    )
if direct_last_failure:
    print(
        "           Direct last failure: "
        f"{one_line(direct_last_failure.get('ts'), 28)} "
        f"{one_line(direct_last_failure.get('fallback_state'), 24)} "
        f"{one_line(direct_last_failure.get('message'), 42)}"
    )
for item in recent_errors[-3:]:
    if not isinstance(item, dict):
        continue
    print(
        "           Recent upstream error: "
        f"{one_line(item.get('ts'), 32)} "
        f"{one_line(item.get('error_type'), 32)} "
        f"{one_line(item.get('upstream'), 48)} "
        f"{one_line(item.get('message'))}"
    )
PY
)"
        if [ -n "$MICROPROXY_LINES" ]; then
            echo "$MICROPROXY_LINES"
        fi
    fi
fi

# Khoj
if port_listening 42110; then
    KHOJ_PID=$(listener_pid 42110)
    [ -z "$KHOJ_PID" ] && KHOJ_PID="unknown"
    echo -e "Khoj:      ${GREEN}✓ RUNNING${NC} (PID: $KHOJ_PID, Port: 42110)"

    # Test health
        if curl -fsS --max-time 3 http://127.0.0.1:42110/api/health >/dev/null 2>&1; then
            echo -e "           ${GREEN}✓ Healthy${NC}"

        # Get stats via proxy
        KHOJ_STATS=$(curl -s "${PROXY_URL}/hg/khoj/status" 2>/dev/null)
        if [ $? -eq 0 ]; then
            KHOJ_SUMMARY=$(python3 - "$TELEMETRY" "$KHOJ_STATS" <<'PY' 2>/dev/null
import json
import sys

def load(raw):
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}

telemetry = load(sys.argv[1] if len(sys.argv) > 1 else "")
status = load(sys.argv[2] if len(sys.argv) > 2 else "")
khoj = telemetry.get("khoj") if isinstance(telemetry.get("khoj"), dict) else status
shared = telemetry.get("shared_metrics") if isinstance(telemetry.get("shared_metrics"), dict) else status.get("shared_metrics", {})
thinking = telemetry.get("mitm_thinking_by_level", {}) if isinstance(telemetry.get("mitm_thinking_by_level"), dict) else {}
swarm = telemetry.get("pegasus_swarm") if isinstance(telemetry.get("pegasus_swarm"), dict) else {}

def num(data, key):
    try:
        return int(data.get(key, 0) or 0)
    except Exception:
        return 0

print("|".join(str(v) for v in (
    num(khoj, "search_count"),
    num(khoj, "injection_count"),
    max(num(khoj, "search_cache_hits"), num(shared, "khoj_search_cache_hits")),
    max(num(khoj, "binary_injection_count"), num(shared, "khoj_binary_injections")),
    max(num(khoj, "binary_inject_dedupe_skips"), num(shared, "khoj_binary_dedupe_skips")),
    max(num(khoj, "binary_tokens_injected"), num(shared, "khoj_tokens_injected")),
    max(num(khoj, "binary_tokens_avoided"), num(shared, "khoj_tokens_avoided")),
    num(shared, "binary_fail_open"),
    num(thinking, "low"),
    num(thinking, "medium"),
    num(thinking, "high"),
    num(thinking, "xhigh"),
    num(shared, "mitm_reasoning_injections"),
    num(shared, "pegasus_swarm_triggers"),
    int(swarm.get("attempts", num(shared, "pegasus_swarm_attempts")) or 0),
    int(swarm.get("success", num(shared, "pegasus_swarm_success")) or 0),
    int(swarm.get("failed", num(shared, "pegasus_swarm_fail")) or 0),
    int(swarm.get("denied", num(shared, "pegasus_swarm_denied")) or 0),
    str(swarm.get("avg_latency_ms", 0.0) or 0.0),
    int(swarm.get("active_workers", 0) or 0),
    int(swarm.get("max_active_workers", 3) or 3),
)))
PY
)
            IFS='|' read -r SEARCHES INJECTIONS CACHE_HITS BIN_INJECTIONS BIN_DEDUPES TOK_INJECTED TOK_AVOIDED BINARY_FAIL_OPEN THINK_LOW THINK_MEDIUM THINK_HIGH THINK_XHIGH REASONING_INJECTIONS SWARM_TRIGGERS SWARM_ATTEMPTS SWARM_SUCCESS SWARM_FAILED SWARM_DENIED SWARM_AVG_LATENCY SWARM_ACTIVE SWARM_MAX <<< "${KHOJ_SUMMARY:-0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|3}"
            echo -e "           Searches: $SEARCHES | Injections: $INJECTIONS | Cache hits: $CACHE_HITS"
            echo -e "           Binary RAG: injects=$BIN_INJECTIONS dedupes=$BIN_DEDUPES tokens=+$TOK_INJECTED/-$TOK_AVOIDED"
            if [ "${BINARY_FAIL_OPEN:-0}" -gt 0 ] 2>/dev/null; then
                echo -e "           Large binary fail-open: $BINARY_FAIL_OPEN"
            fi
            echo -e "           Thinking: low=$THINK_LOW med=$THINK_MEDIUM high=$THINK_HIGH xhigh=$THINK_XHIGH | Reasoning injects=$REASONING_INJECTIONS | Swarm triggers=$SWARM_TRIGGERS"
            echo -e "           Swarm quality: attempts=$SWARM_ATTEMPTS success=$SWARM_SUCCESS failed=$SWARM_FAILED denied=$SWARM_DENIED avg_latency=${SWARM_AVG_LATENCY}ms active=${SWARM_ACTIVE}/${SWARM_MAX}"
            ACCEL_SCRIPT="$(mktemp)"
            cat > "$ACCEL_SCRIPT" <<'PY'
import json
import sys

try:
    data = json.loads(sys.argv[1]).get("acceleration", {})
except Exception:
    print("CPU")
    sys.exit(0)

active = data.get("runtime_active", {})
host = data.get("host", {})
container = data.get("container", {})
proof = data.get("proof", {})
bits = []

if active.get("cuda"):
    bits.append("CUDA runtime")
elif container.get("cuda_exposed", data.get("cuda")):
    bits.append("CUDA exposed")
elif host.get("cuda"):
    bits.append("CUDA host")

ov_devices = active.get("openvino_devices_visible") or []
if active.get("openvino_compile_ok", active.get("openvino")):
    bits.append("OV compile:" + ",".join(ov_devices[:3]))
elif active.get("openvino_runtime_visible") or ov_devices:
    bits.append("OV visible:" + ",".join(ov_devices[:3]))
elif container.get("openvino_exposed", data.get("openvino")):
    bits.append("OV exposed")
elif host.get("openvino"):
    host_devices = host.get("openvino_devices") or []
    bits.append("OV host" + (":" + ",".join(host_devices[:3]) if host_devices else ""))

myriad_count = host.get("myriad_count", data.get("myriad_count", 0))
myriad_compile = (proof.get("myriad") or {}).get("compile") or {}
myriad_errors = list(active.get("myriad_compile_errors") or [])
if myriad_compile.get("error"):
    myriad_errors.append(str(myriad_compile.get("error")))
myriad_devices = active.get("myriad_devices") or [
    device for device in active.get("openvino_devices_visible", [])
    if str(device).upper() == "MYRIAD" or str(device).upper().startswith("MYRIAD.")
]
myriad_visible = bool(active.get("myriad_visible") or myriad_devices)
myriad_compile_failed = bool(active.get("myriad_compile_failed")) or bool(
    myriad_devices and myriad_compile and myriad_compile.get("ok") is False
)
myriad_boot_failed = bool(active.get("myriad_boot_failed")) or any(
    marker in error.lower()
    for error in myriad_errors
    for marker in ("not opened", "failed to find booted device", "allocate graph", "boot")
)
if active.get("myriad_compile_ok") or active.get("myriad"):
    bits.append(f"MYRIAD compile x{myriad_count}")
elif myriad_boot_failed:
    bits.append(f"MYRIAD boot failed x{myriad_count}")
elif myriad_compile_failed:
    bits.append(f"MYRIAD compile failed x{myriad_count}")
elif myriad_visible:
    bits.append(f"MYRIAD visible x{myriad_count}")
elif container.get("myriad_exposed", data.get("myriad")):
    bits.append(f"MYRIAD exposed x{myriad_count}")
elif host.get("myriad"):
    bits.append(f"MYRIAD host x{myriad_count}")

if not bits:
    bits.append("CPU")

print(" | ".join(bits))
PY
            ACCEL=$(python3 "$ACCEL_SCRIPT" "$KHOJ_STATS" 2>/dev/null)
            rm -f "$ACCEL_SCRIPT"
            echo -e "           Accel: ${ACCEL:-CPU}"
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

PROXY_WATCHDOG_PID="$(pidfile_read "logs/proxy_watchdog.pid" 2>/dev/null || true)"
KHOJ_WATCHDOG_PID="$(pidfile_read "logs/khoj_watchdog.pid" 2>/dev/null || true)"
if [ -n "$PROXY_WATCHDOG_PID" ] && ps -p "$PROXY_WATCHDOG_PID" -o pid= >/dev/null 2>&1; then
    echo -e "Watchdogs: ${GREEN}proxy=$PROXY_WATCHDOG_PID${NC}"
else
    echo -e "Watchdogs: ${YELLOW}proxy=off${NC}"
fi
if [ -n "$KHOJ_WATCHDOG_PID" ] && ps -p "$KHOJ_WATCHDOG_PID" -o pid= >/dev/null 2>&1; then
    echo -e "           ${GREEN}khoj=$KHOJ_WATCHDOG_PID${NC}"
else
    echo -e "           ${YELLOW}khoj=off${NC}"
fi

# Windsurf
WS_MATCH_LINE="$(pgrep -f "windsurf-next|Windsurf|/usr/share/windsurf-next" 2>/dev/null | head -1 || true)"
if [ -n "$WS_MATCH_LINE" ]; then
    WS_PID="${WS_MATCH_LINE%% *}"
    echo -e "Windsurf:  ${GREEN}✓ RUNNING${NC} (PID: $WS_PID)"

    if lsp_shim_active >/dev/null 2>&1; then
        echo -e "           LSP Shield: ${GREEN}ACTIVE${NC}"
    else
        echo -e "           LSP Shield: ${YELLOW}inactive${NC}"
    fi

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
        PATCH_STATE=$(binary_patched | tr -d '\n')
        if [ "$PATCH_STATE" = "full" ]; then
            echo -e "           ${GREEN}✓ Binary patch applied${NC}"
        elif [ "$PATCH_STATE" = "partial" ]; then
            echo -e "           ${YELLOW}! Binary patch partial (${PATCH_STATE})${NC}"
        else
            echo -e "           ${YELLOW}! Binary patch not detected${NC}"
        fi
        if echo "${INFER_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
            echo -e "           ${GREEN}✓ Proxy path active${NC}"
        else
            echo -e "           ${YELLOW}! Proxy path inactive${NC}"
        fi
        if echo "${API_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com\|server.self-serve.windsurf.com'; then
            if echo "${INFER_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
                if echo "${API_URL}" | grep -q 'server.self-serve.windsurf.com' && ! echo "${API_URL}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
                    echo -e "           ${CYAN}i Direct split: intentional${NC}"
                    echo -e "           ${CYAN}  login/control-plane direct, inference proxied${NC}"
                else
                    echo -e "           ${GREEN}✓ Full proxy mode${NC}"
                fi
            else
                echo -e "           ${YELLOW}! DIRECT-only mode detected${NC}"
            fi
        elif ! echo "${API_URL:-}" | grep -q 'proxy.windsurf.com\|inferapi.windsurf.com'; then
            echo -e "           ${YELLOW}! DIRECT-only mode detected${NC}"
            if [ "${LS_AGE:-0}" -gt 90 ] 2>/dev/null; then
                echo -e "           ${RED}! Stale direct mode: reload/restart Windsurf${NC}"
            fi
        fi
        DIRECT_EGRESS="$(language_server_direct_egress || true)"
        if [ -n "$DIRECT_EGRESS" ]; then
            DIRECT_COUNT="$(printf '%s\n' "$DIRECT_EGRESS" | sed '/^$/d' | wc -l | tr -d ' ')"
            DIRECT_PEERS="$(printf '%s\n' "$DIRECT_EGRESS" | awk '{print $1}' | sort -u | paste -sd ',' -)"
            echo -e "           ${RED}! Direct egress sockets: ${DIRECT_COUNT}${NC} (${DIRECT_PEERS})"
            if echo "$SUDO_PASS" | sudo -S iptables -t nat -S HG-WINDSURF-EGRESS >/dev/null 2>&1; then
                echo -e "           ${CYAN}  egress shield active for new sockets${NC}"
            else
                echo -e "           ${YELLOW}  run: ./hg.sh egress on${NC}"
            fi
        else
            echo -e "           ${GREEN}✓ No language-server direct egress sockets${NC}"
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
    MITM_COUNT=$(grep -c "PROTOCOL EVENT" logs/cascade_midway.log || true)
    if [ $MITM_COUNT -gt 0 ]; then
        echo -e "MITM Log:   ${GREEN}$MITM_COUNT events captured${NC}"
    else
        echo -e "MITM Log:   ${YELLOW}Empty (no Cascade requests yet)${NC}"
    fi
fi

if [ -f "logs/khoj.log" ]; then
    KHOJ_LINES=$(wc -l < logs/khoj.log)
    echo -e "Khoj Log:   $KHOJ_LINES lines"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
