#!/usr/bin/env bash
# Focused quota/inference watcher for proxy logs.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

LOG_FILE="${HG_WATCH_QUOTA_LOG:-logs/proxy.log}"
DURATION_SECONDS="${HG_WATCH_QUOTA_DURATION_SECONDS:-120}"
FOLLOW=1

usage() {
    cat <<'USAGE'
Usage: ./hg.sh watch-quota [options]

Watch focused quota/inference lifecycle signals from proxy logs.

Options:
  -d, --duration <sec>   Stop after N seconds (default: 120)
  -n, --no-follow        Print current tail only (no follow)
  -h, --help             Show help

Environment:
  HG_WATCH_QUOTA_LOG               Log path (default logs/proxy.log)
  HG_WATCH_QUOTA_DURATION_SECONDS  Default duration
  HG_QUOTA_PROBE=1                 Enable deep quota frame probes in src/proxy.py
USAGE
}

while [[ $# -gt 0 ]]; do
    case "${1:-}" in
        -d|--duration)
            if [[ $# -lt 2 ]]; then
                echo "missing duration value"
                usage
                exit 1
            fi
            shift
            DURATION_SECONDS="$1"
            ;;
        -n|--no-follow)
            FOLLOW=0
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

if ! [[ "$DURATION_SECONDS" =~ ^[0-9]+$ ]] || [[ "$DURATION_SECONDS" -le 0 ]]; then
    echo "duration must be a positive integer"
    exit 1
fi

FILTER='QUOTA_PROBE_(HEADERS|BODY|STREAM_BYTES|STREAM_END)|UPSTREAM_QUOTA_SIGNAL|CONNECTION: POST /exa\.api_server_pb\.ApiServerService/GetChatMessage|CONNECTION: POST /exa\.api_server_pb\.ApiServerService/CheckUserMessageRateLimit|PULSE_STREAM:|STREAM_UPSTREAM_TIMEOUT|RELAY_ERROR|Upstream unreachable|STATUS=(4[0-9]{2}|5[0-9]{2})'

if [[ "$FOLLOW" -eq 0 ]]; then
    tail -n 200 "$LOG_FILE" | rg -n "$FILTER" || true
    exit 0
fi

echo "Watching quota/inference signals from $LOG_FILE for ${DURATION_SECONDS}s ..."
timeout "${DURATION_SECONDS}s" bash -lc "tail -n 0 -f '$LOG_FILE' | rg --line-buffered -n \"$FILTER\"" || true
