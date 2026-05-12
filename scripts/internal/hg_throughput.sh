#!/usr/bin/env bash
# Throughput baseline sampler for live microproxy and proxy metrics.
#
# Collects a short time-series of route, error, and latency counters so you can
# compare baseline vs baseline+direct-path behavior during real traffic runs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

PROXY_URL="${HG_PROXY_URL:-http://127.0.0.1:${HG_PROXY_PORT:-9998}}"
INTERVAL_SECONDS="${HG_THROUGHPUT_INTERVAL_SECONDS:-5}"
DURATION_SECONDS="${HG_THROUGHPUT_DURATION_SECONDS:-60}"
OUTPUT_PATH="${HG_THROUGHPUT_OUTPUT_PATH:-}"

usage() {
    cat <<'USAGE'
Usage: ./hg.sh throughput [options]

Collect live throughput/error samples from /hg/telemetry and /hg/microproxy/status.

Options:
  -i, --interval <seconds>  Sampling interval (default: 5)
  -d, --duration <seconds>  Total window duration (default: 60)
  -j, --json <path>         Write samples as JSONL to path
  -h, --help                Show this help

Environment overrides:
  HG_PROXY_URL                 Base proxy URL (default http://127.0.0.1:9998)
  HG_THROUGHPUT_INTERVAL_SECONDS Sampling interval
  HG_THROUGHPUT_DURATION_SECONDS Total duration
  HG_THROUGHPUT_OUTPUT_PATH    Optional default JSONL output path
USAGE
}

while [ $# -gt 0 ]; do
    case "${1:-}" in
        -i|--interval)
            if [ $# -lt 2 ]; then
                echo "missing interval value"
                usage
                exit 1
            fi
            shift
            INTERVAL_SECONDS="${1:-}"
            ;;
        -d|--duration)
            if [ $# -lt 2 ]; then
                echo "missing duration value"
                usage
                exit 1
            fi
            shift
            DURATION_SECONDS="${1:-}"
            ;;
        -j|--json)
            if [ $# -lt 2 ]; then
                echo "missing json output path"
                usage
                exit 1
            fi
            shift
            OUTPUT_PATH="${1:-}"
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
    shift
done

if ! [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || ! [[ "$DURATION_SECONDS" =~ ^[0-9]+$ ]]; then
    echo "interval and duration must be integer seconds"
    usage
    exit 1
fi

python3 - "$PROXY_URL" "$INTERVAL_SECONDS" "$DURATION_SECONDS" "$OUTPUT_PATH" <<'PY'
import json
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def fetch_json(endpoint):
    with urlopen(endpoint, timeout=2) as handle:
        return json.loads(handle.read().decode("utf-8"))


def extract_status_metrics(proxy_url):
    telemetry = fetch_json(f"{proxy_url}/hg/telemetry")
    status = fetch_json(f"{proxy_url}/hg/microproxy/status")

    latency = telemetry.get("latency_ms", {})
    routes = status.get("routes", {})
    route_counts = routes.get("routes", {}) if isinstance(routes, dict) else {}
    usage = status.get("direct_fast_path", {}).get("usage", {})
    upstream_errors = status.get("upstream_errors", {})
    classifier = status.get("classifier", {})
    return {
        "ts": telemetry.get("ts", time.time()),
        "latency": {
            "p50": latency.get("p50"),
            "p95": latency.get("p95"),
            "p99": latency.get("p99"),
        },
        "stream_totals": {
            "route_total": to_int(routes.get("total", 0)),
            "direct": to_int(usage.get("direct_upstream", 0)),
            "fallback": to_int(usage.get("python_fallback", 0)),
            "passthrough": to_int(usage.get("passthrough", 0)),
        },
        "errors_total": to_int(upstream_errors.get("total", 0)),
        "route_by_class": classifier.get("route_selected_by_class", {}),
        "direct_state": status.get("direct_fast_path", {}).get("state", "disabled"),
        "direct_last_failure": status.get("direct_fast_path", {}).get("last_failure", {}),
    }


def pct(value, total):
    if total <= 0:
        return 0.0
    return (float(value) / float(total)) * 100.0


def main():
    proxy_url, interval_text, duration_text = sys.argv[1:4]
    output_path = (sys.argv[4] if len(sys.argv) > 4 else "").strip()
    interval = max(1, int(interval_text))
    duration = max(interval, int(duration_text))
    samples = []

    print(
        f"Throughput baseline session | proxy={proxy_url} | "
        f"interval={interval}s duration={duration}s"
    )

    t_end = time.time() + float(duration)
    sample = 0
    previous = None

    while time.time() < t_end:
        try:
            snapshot = extract_status_metrics(proxy_url)
        except (URLError, OSError, ValueError) as exc:
            print(f"sample[{sample:02d}] fetch failed: {exc}")
            time.sleep(interval)
            sample += 1
            continue

        if previous is None:
            print(
                "sample:00 baseline | "
                f"routes={snapshot['stream_totals']['route_total']} "
                f"direct={snapshot['stream_totals']['direct']} "
                f"fallback={snapshot['stream_totals']['fallback']} "
                f"pass={snapshot['stream_totals']['passthrough']} "
                f"errors={snapshot['errors_total']} "
                f"p50={snapshot['latency']['p50']} p95={snapshot['latency']['p95']} p99={snapshot['latency']['p99']} "
                f"direct_state={snapshot['direct_state']}"
            )
            record = dict(snapshot)
            record["sample"] = 0
            record["route_delta"] = snapshot["stream_totals"]
            record["error_delta"] = 0
            record["rate_rps"] = 0.0
            record["error_rate_pct"] = 0.0
            samples.append(record)
            previous = snapshot
            time.sleep(interval)
            sample += 1
            continue

        route_delta = {
            key: max(0, snapshot["stream_totals"][key] - previous["stream_totals"][key])
            for key in ("route_total", "direct", "fallback", "passthrough")
        }
        error_delta = max(0, snapshot["errors_total"] - previous["errors_total"])
        class_delta = {}
        current_route_by_class = snapshot["route_by_class"]
        previous_route_by_class = previous["route_by_class"]
        for key in set(current_route_by_class) | set(previous_route_by_class):
            class_delta[key] = max(
                0,
                to_int(current_route_by_class.get(key, 0))
                - to_int(previous_route_by_class.get(key, 0))
            )
        if not class_delta:
            class_delta = {}

        total_delta = route_delta["route_total"]
        direct_share = pct(route_delta["direct"], total_delta)
        fallback_share = pct(route_delta["fallback"], total_delta)
        error_rate = pct(error_delta, max(total_delta, 0))

        print(
            f"sample[{sample:02d}] +route={total_delta} "
            f"(dir {route_delta['direct']} [{direct_share:.1f}%] "
            f"| fb {route_delta['fallback']} [{fallback_share:.1f}%] "
            f"| pass {route_delta['passthrough']}), "
            f"rps={total_delta / max(interval, 1):.2f}, "
            f"err={error_delta} ({error_rate:.2f}%), "
            f"lat p50={snapshot['latency']['p50']} p95={snapshot['latency']['p95']} p99={snapshot['latency']['p99']} "
            f"route_classes={class_delta if class_delta else {}} "
            f"state={snapshot['direct_state']}"
        )

        if snapshot["direct_last_failure"].get("message"):
            print(
                "          last_direct_failure="
                f"{snapshot['direct_last_failure'].get('fallback_state')} "
                f"count={snapshot['direct_last_failure'].get('direct_failure_count')} "
                f"cooldown_ms={snapshot['direct_last_failure'].get('direct_cooldown_remaining_ms')} "
                f"{snapshot['direct_last_failure'].get('message')}"
            )

        record = dict(snapshot)
        record.update(
            {
                "sample": sample,
                "route_delta": route_delta,
                "error_delta": error_delta,
                "rate_rps": total_delta / max(interval, 1),
                "error_rate_pct": error_rate,
            }
        )
        samples.append(record)
        previous = snapshot
        time.sleep(interval)
        sample += 1

    if output_path:
        with open(output_path, "w", encoding="utf-8") as handle:
            for sample_data in samples:
                handle.write(json.dumps(sample_data, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
PY
