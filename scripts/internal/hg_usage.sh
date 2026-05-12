#!/usr/bin/env bash
# High-gravity usage probe.
# One-shot or watch-mode snapshot of proxy-side usage and cache efficiency.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SCRIPT_DIR"

PROXY_URL="${HG_PROXY_URL:-http://127.0.0.1:${HG_PROXY_PORT:-9998}}"
PROXY_USAGE_PATH="${HG_USAGE_PATH:-/api/oauth/usage}"
INTERVAL_SECONDS="${HG_USAGE_INTERVAL_SECONDS:-10}"
WATCH_MODE=0
OUTPUT_JSON=0

usage() {
    cat <<'USAGE'
Usage: ./hg.sh usage [options]

Show proxy-side usage and efficiency counters for routing/caching.

Options:
  -w, --watch                 Continuously sample until interrupted
  -i, --interval <seconds>    Refresh interval in watch mode (default: 10)
  -j, --json                  Emit JSON snapshot (one shot only)
  -h, --help                  Show this help

Environment overrides:
  HG_PROXY_URL                 Base proxy URL (default http://127.0.0.1:9998)
  HG_PROXY_PORT                Proxy port used when HG_PROXY_URL is unset
  HG_USAGE_PATH                Usage endpoint path (default /api/oauth/usage)
  HG_USAGE_INTERVAL_SECONDS    Default watch interval when -w is used
USAGE
}

while [[ $# -gt 0 ]]; do
    case "${1:-}" in
        -w|--watch)
            WATCH_MODE=1
            ;;
        -i|--interval)
            if [[ $# -lt 2 ]]; then
                echo "missing interval value"
                usage
                exit 1
            fi
            shift
            INTERVAL_SECONDS="$1"
            ;;
        -j|--json)
            OUTPUT_JSON=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "unknown option: $1"
            usage
            exit 1
            ;;
    esac
    shift
 done

if ! [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || [[ "$INTERVAL_SECONDS" -le 0 ]]; then
    echo "interval must be a positive integer"
    usage
    exit 1
fi

python3 - "$PROXY_URL" "$PROXY_USAGE_PATH" "$INTERVAL_SECONDS" "$WATCH_MODE" "$OUTPUT_JSON" <<'PY'
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.request import Request, urlopen

PROXY_URL, USAGE_PATH, INTERVAL_TEXT, WATCH_MODE_TEXT, OUTPUT_JSON_TEXT = sys.argv[1:6]
INTERVAL = max(1, int(INTERVAL_TEXT))
WATCH_MODE = WATCH_MODE_TEXT == "1"
OUTPUT_JSON = OUTPUT_JSON_TEXT == "1"

PERCENT_KEYS = (
    "usagePercent",
    "usedPercent",
    "percentUsed",
    "contextUsagePercent",
    "contextUsedPercent",
    "tokenUsagePercent",
    "used_tokens_pct",
)

USED_KEYS = (
    "used_credits",
    "used_prompt_credits",
    "used_flow_credits",
    "used_flex_credits",
    "used_tokens",
    "usedTokens",
    "used_tokens_total",
    "tokensUsed",
    "inputTokensUsed",
    "contextTokensUsed",
    "input_tokens_used",
)

CAP_KEYS = (
    "monthly_limit",
    "user_prompt_credit_cap",
    "user_flow_credit_cap",
    "add_on_credits_available",
    "add_on_credits_total",
    "token_cap",
    "token_limit",
    "credit_limit",
    "flex_credit_quota",
    "used_prompt_limit",
)

UNLIMITED_MARKERS = (
    999999,
    99999,
    9999,
    "unlimited",
    "infinite",
)


def to_int(value, default=0):
    try:
        if isinstance(value, bool):
            return int(value)
        return int(float(str(value).strip()))
    except Exception:
        return default


def to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def safe_fetch_json(url, *, headers=None, timeout=2):
    request = Request(url)
    if headers:
        for key, val in headers.items():
            request.add_header(key, val)
    with urlopen(request, timeout=timeout) as handle:
        raw = handle.read().decode("utf-8", "replace")
        return json.loads(raw)


def to_str(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def pct(value, total):
    try:
        total = float(total)
        if total <= 0:
            return 0.0
        return float(value) / total * 100.0
    except Exception:
        return 0.0


def choose_usage_percent(payload):
    if not isinstance(payload, dict):
        return None

    for key in PERCENT_KEYS:
        if key in payload:
            value = to_float(payload[key], default=None)
            if value is not None:
                return max(0.0, min(100.0, value))

    limit_candidates = [
        to_float(payload.get(key), default=0.0)
        for key in CAP_KEYS
        if to_int(payload.get(key), default=None) is not None
    ]

    used_candidates = [
        to_float(payload.get(key), default=0.0)
        for key in USED_KEYS
        if to_int(payload.get(key), default=None) is not None
    ]

    if not limit_candidates and isinstance(payload.get("extra_usage"), dict):
        extra = payload["extra_usage"]
        maybe_enabled = to_int(extra.get("is_enabled"), default=1.0)
        maybe_monthly = extra.get("monthly_limit")
        if not (maybe_enabled == 0 or maybe_enabled is False):
            if maybe_monthly is None:
                limit_candidates.append(999999.0)

    if used_candidates and limit_candidates:
        used = max(used_candidates)
        limit = max(limit_candidates)
        if limit > 0:
            return min(100.0, pct(used, limit))

    return None


def parse_usage_payload(payload):
    if not isinstance(payload, dict):
        return {
            "reachable": False,
            "error": "no usage payload",
        }

    usage_percent = choose_usage_percent(payload)
    used_values = [to_int(payload.get(key)) for key in USED_KEYS]
    cap_values = [to_int(payload.get(key)) for key in CAP_KEYS]
    extra = payload.get("extra_usage") if isinstance(payload.get("extra_usage"), dict) else {}

    remaining_values = [
        to_int(payload.get(key))
        for key in (
            "remaining_credits",
            "remainingCredits",
            "requestsRemaining",
            "remaining_tokens",
            "remainingRequests",
        )
        if key in payload
    ]

    used = max(used_values) if used_values else 0
    limit = max(cap_values) if cap_values else 0
    remaining = max(remaining_values) if remaining_values else None
    remaining_derived = max(0, (limit - used)) if used and limit > 0 else (
        remaining if isinstance(remaining, int) else None
    )
    is_unlimited = (
        bool(payload.get("isLimited") is False)
        or bool(payload.get("isRateLimited") is False)
        or bool(extra.get("is_enabled") is True and bool(extra.get("monthly_limit") is None))
        or any((v in UNLIMITED_MARKERS for v in [payload.get("monthly_limit"), payload.get("add_on_credits_available")]))
    )

    if usage_percent is None and limit > 0 and used >= 0 and not is_unlimited:
        usage_percent = pct(used, limit)

    usage_mode = "unknown"
    if is_unlimited or (limit in (0, 999999) and usage_percent == 0.0):
        usage_mode = "proxy-spoofed"
    elif usage_percent is not None:
        usage_mode = "provider-reported"

    return {
        "reachable": True,
        "payload": payload,
        "usage_percent": usage_percent,
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "remaining_derived": remaining_derived,
        "remaining_mode": "direct" if remaining is not None else "derived",
        "extra_usage": extra,
        "usage_mode": usage_mode,
    }


def format_int(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return "0"


def format_pct(value):
    if value is None:
        return "n/a"
    return f"{value:.2f}%"


def active_swarm_workers():
    try:
        output = subprocess.check_output(["ps", "-eo", "args"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return 0
    request_ids = set()
    fallback_count = 0
    for line in output.splitlines():
        if "gemini --prompt [HG_SWARM_TRIGGER]" not in line:
            continue
        match = re.search(r"\brequest_id=([A-Za-z0-9_-]+)", line)
        if match:
            request_ids.add(match.group(1))
        elif line.startswith("node ") or line.startswith("/usr/bin/node "):
            fallback_count += 1
    return len(request_ids) if request_ids else fallback_count


def language_server_direct_egress():
    try:
        proc = subprocess.run(
            ["ss", "-tanpH", "state", "established", "( dport = :443 )"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
    except Exception:
        return {"count": 0, "peers": []}

    peers = []
    for line in proc.stdout.splitlines():
        if "language_server" not in line:
            continue
        parts = line.split()
        for peer in parts:
            if not (peer.endswith(":443") or peer.endswith(":https")):
                continue
            if peer.startswith("127.0.0.1:") or peer.startswith("[::1]:"):
                continue
            peers.append(peer.replace(":https", ":443"))
    return {"count": len(peers), "peers": sorted(set(peers))}


def sample():
    try:
        usage_payload = safe_fetch_json(
            f"{PROXY_URL}{USAGE_PATH}",
            headers={"Host": "proxy.windsurf.com"},
        )
        usage_parsed = parse_usage_payload(usage_payload)
    except Exception as exc:  # noqa: BLE001
        usage_parsed = {
            "reachable": False,
            "error": str(exc),
        }

    telemetry_error = None
    try:
        telemetry = safe_fetch_json(f"{PROXY_URL}/hg/telemetry")
    except Exception as exc:  # noqa: BLE001
        telemetry_error = str(exc)
        telemetry = {}

    microproxy = {}
    try:
        microproxy = safe_fetch_json(f"{PROXY_URL}/hg/microproxy/status")
    except Exception:
        microproxy = {}

    requests_total = int(telemetry.get("total_requests", telemetry.get("requests", 0) or 0))
    cache_hits = int(telemetry.get("cache_hits", 0) or 0)
    tokens_saved = int(telemetry.get("tokens_saved", 0) or 0)
    direct_usage = {}
    if isinstance(microproxy, dict):
        direct_usage = microproxy.get("direct_fast_path", {}).get("usage", {})

    shared = telemetry.get("shared_metrics", {}) if isinstance(telemetry.get("shared_metrics"), dict) else {}
    thinking = telemetry.get("mitm_thinking_by_level", {}) if isinstance(telemetry.get("mitm_thinking_by_level"), dict) else {}
    swarm = telemetry.get("pegasus_swarm", {}) if isinstance(telemetry.get("pegasus_swarm"), dict) else {}

    direct_total = int(direct_usage.get("total", 0) or 0)
    direct_direct = int(direct_usage.get("direct_upstream", 0) or 0)
    direct_fallback = int(direct_usage.get("python_fallback", 0) or 0)
    direct_passthrough = int(direct_usage.get("passthrough", 0) or 0)
    streams = microproxy.get("streams", {}) if isinstance(microproxy.get("streams"), dict) else {}
    backpressure = microproxy.get("backpressure", {}) if isinstance(microproxy.get("backpressure"), dict) else {}
    stream_finished = int(streams.get("streams_finished", 0) or 0)
    stream_quota_exhausted = int(streams.get("quota_exhausted_signals", 0) or 0)
    stream_connect_error = int(streams.get("connect_error_signals", 0) or 0)
    cache_pct = pct(cache_hits, requests_total)
    direct_egress = language_server_direct_egress()

    return {
        "snapshot_ts": time.time(),
        "proxy_url": PROXY_URL,
        "telemetry_error": telemetry_error,
        "usage_route": usage_parsed,
        "usage_path": USAGE_PATH,
        "proxy_stats": {
            "requests_total": requests_total,
            "cache_hits": cache_hits,
            "tokens_saved": tokens_saved,
            "cache_hit_pct": cache_pct,
            "control_plane_cache_hits": int(shared.get("control_plane_cache_hits", 0) or 0),
            "control_plane_cache_stores": int(shared.get("control_plane_cache_stores", 0) or 0),
            "billing_guard_allows": int(shared.get("billing_guard_allows", 0) or 0),
            "billing_guard_blocks": int(shared.get("billing_guard_blocks", 0) or 0),
            "bypass_control_plane": bool(telemetry.get("bypass_control_plane", False)),
            "active_keys": int(telemetry.get("active_keys", 0) or 0),
            "total_keys": int(telemetry.get("total_keys", 0) or 0),
            "rotation_mode": telemetry.get("rotation_mode", "unknown"),
        },
        "khoj_cache": {
            "search_count": int((telemetry.get("khoj") or {}).get("search_count", 0) or 0),
            "search_cache_hits": int((telemetry.get("khoj") or {}).get("search_cache_hits", 0) or 0),
            "binary_injection_count": int((telemetry.get("khoj") or {}).get("injection_count", 0) or 0),
            "binary_tokens_saved": int((telemetry.get("khoj") or {}).get("binary_tokens_avoided", 0) or 0),
            "binary_tokens_injected": int((telemetry.get("khoj") or {}).get("binary_tokens_injected", 0) or 0),
            "thinking_injections": int(shared.get("mitm_reasoning_injections", 0) or 0),
            "swarm_triggers": int(shared.get("pegasus_swarm_triggers", 0) or 0),
            "thinking_low": int(thinking.get("low", 0) or 0),
            "thinking_medium": int(thinking.get("medium", 0) or 0),
            "thinking_high": int(thinking.get("high", 0) or 0),
            "thinking_xhigh": int(thinking.get("xhigh", 0) or 0),
        },
        "swarm_quality": {
            "attempts": int(swarm.get("attempts", shared.get("pegasus_swarm_attempts", 0)) or 0),
            "success": int(swarm.get("success", shared.get("pegasus_swarm_success", 0)) or 0),
            "failed": int(swarm.get("failed", shared.get("pegasus_swarm_fail", 0)) or 0),
            "denied": int(swarm.get("denied", shared.get("pegasus_swarm_denied", 0)) or 0),
            "avg_latency_ms": float(swarm.get("avg_latency_ms", 0.0) or 0.0),
            "active_workers": active_swarm_workers(),
            "max_active_workers": int(os.environ.get("HG_PEGASUS_MAX_ACTIVE_AGENTS", "3") or 3),
            "last": swarm.get("last", {}) if isinstance(swarm.get("last"), dict) else {},
        },
        "microproxy_direct_usage": {
            "total": direct_total,
            "direct_upstream": direct_direct,
            "python_fallback": direct_fallback,
            "passthrough": direct_passthrough,
            "hot_path_enabled": bool((microproxy.get("direct_fast_path") or {}).get("active", False)),
            "state": (microproxy.get("direct_fast_path") or {}).get("state", "disabled"),
            "target": (microproxy.get("direct_fast_path") or {}).get("target")
            or (microproxy.get("direct_fast_path") or {}).get("upstream"),
        },
        "microproxy_stream_signals": {
            "finished": stream_finished,
            "quota_exhausted": stream_quota_exhausted,
            "connect_error": stream_connect_error,
            "backpressure": int(backpressure.get("total", 0) or 0),
            "max_active_seen": int(backpressure.get("max_active_seen", 0) or 0),
            "max_active_streams": int(backpressure.get("max_active_streams", 0) or 0),
        },
        "language_server_direct_egress": direct_egress,
    }


def print_human(snapshot):
    usage = snapshot.get("usage_route", {})
    telemetry_ok = snapshot.get("telemetry_error") is None

    print(f"Proxy usage snapshot | {snapshot['proxy_url']} | ts={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(snapshot['snapshot_ts']))}")
    print(f"Usage endpoint: {snapshot['usage_path']}")

    if usage.get("reachable"):
        extra_usage = usage.get("extra_usage", {})
        rem = usage.get("remaining")
        if rem is None:
            rem = usage.get("remaining_derived")
        remaining_mode = usage.get("remaining_mode", "n/a")
        print("Provider usage:")
        print(
            f"  usage={format_pct(usage.get('usage_percent'))} "
            f"mode={usage.get('usage_mode')} used={format_int(usage.get('used'))} "
            f"limit={format_int(usage.get('limit'))} remaining={format_int(rem)} ({remaining_mode})"
        )
        if extra_usage:
            print(
                "  extra_usage: "
                f"is_enabled={to_str(extra_usage.get('is_enabled'))} "
                f"monthly_limit={to_str(extra_usage.get('monthly_limit'))} "
                f"used_credits={to_str(usage.get('payload', {}).get('used_credits'))}"
            )
    else:
        err = usage.get("error") if isinstance(usage.get("error"), str) else "unreachable"
        print(f"Provider usage: unreachable ({err})")

    print("Proxy telemetry:")
    if telemetry_ok:
        p = snapshot["proxy_stats"]
        print(
            f"  requests={format_int(p['requests_total'])} "
            f"cache_hits={format_int(p['cache_hits'])} ({format_pct(p['cache_hit_pct'])}) "
            f"tokens_saved={format_int(p['tokens_saved'])} active_keys={p['active_keys']}/{p['total_keys']}"
        )
        print(
            f"  bypass_control_plane={p['bypass_control_plane']} "
            f"cp_cache_hits={format_int(p['control_plane_cache_hits'])} "
            f"cp_cache_stores={format_int(p['control_plane_cache_stores'])} "
            f"rotation={p['rotation_mode']}"
        )
        print(
            f"  billing_guard: allows={format_int(p['billing_guard_allows'])} "
            f"blocks={format_int(p['billing_guard_blocks'])}"
        )

        k = snapshot["khoj_cache"]
        rag_ratio = pct(k["search_cache_hits"], k["search_count"]) if k["search_count"] > 0 else 0.0
        print(
            f"  RAG search: total={format_int(k['search_count'])} "
            f"cache_hits={format_int(k['search_cache_hits'])} ({format_pct(rag_ratio)})"
        )
        print(
            f"  Reasoning: low={k['thinking_low']} med={k['thinking_medium']} "
            f"high={k['thinking_high']} xhigh={k['thinking_xhigh']} "
            f"injections={k['thinking_injections']} swarm={k['swarm_triggers']}"
        )
        q = snapshot["swarm_quality"]
        last = q.get("last", {}) if isinstance(q.get("last"), dict) else {}
        print(
            f"  Swarm quality: attempts={format_int(q['attempts'])} "
            f"success={format_int(q['success'])} failed={format_int(q['failed'])} "
            f"denied={format_int(q['denied'])} avg_latency={q['avg_latency_ms']:.2f}ms "
            f"active={format_int(q.get('active_workers', 0))}/{format_int(q.get('max_active_workers', 0))} "
            f"last={last.get('status', 'none')}"
        )
        print(
            f"  Binary RAG: injects={format_int(k['binary_injection_count'])} "
            f"tokens_saved={format_int(k['binary_tokens_saved'])} "
            f"tokens_injected={format_int(k['binary_tokens_injected'])}"
        )

        m = snapshot["microproxy_direct_usage"]
        s = snapshot["microproxy_stream_signals"]
        print(
            f"Direct path: state={m['state']} hot_path={m['hot_path_enabled']} "
            f"target={m['target'] or 'n/a'}"
        )
        print(
            f"  stream_signals finished={format_int(s['finished'])} "
            f"quota_exhausted={format_int(s['quota_exhausted'])} "
            f"connect_error={format_int(s['connect_error'])} "
            f"backpressure={format_int(s.get('backpressure', 0))} "
            f"active_cap={format_int(s.get('max_active_seen', 0))}/{format_int(s.get('max_active_streams', 0))}"
        )
        if m["total"]:
            direct_pct = pct(m["direct_upstream"], m["total"])
            fb_pct = pct(m["python_fallback"], m["total"])
            pass_pct = pct(m["passthrough"], m["total"])
            print(
                f"  direct_fast_path total={format_int(m['total'])} "
                f"upstream={format_int(m['direct_upstream'])} [{format_pct(direct_pct)}] "
                f"fallback={format_int(m['python_fallback'])} [{format_pct(fb_pct)}] "
                f"passthrough={format_int(m['passthrough'])} [{format_pct(pass_pct)}]"
            )
        else:
            print("  direct_fast_path: no traffic yet")
        e = snapshot.get("language_server_direct_egress", {})
        print(
            f"  language_server_direct_egress={format_int(e.get('count', 0))} "
            f"peers={','.join(e.get('peers', [])) or 'none'}"
        )
    else:
        print(f"Telemetry: unreachable ({snapshot.get('telemetry_error')})")


def main():
    if OUTPUT_JSON:
        snapshot = sample()
        print(json.dumps(snapshot, sort_keys=True))
        return

    if WATCH_MODE:
        while True:
            print_human(sample())
            print()
            time.sleep(INTERVAL)
    else:
        print_human(sample())


if __name__ == "__main__":
    main()
PY
