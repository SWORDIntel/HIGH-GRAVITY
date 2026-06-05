#!/usr/bin/env bash
# HIGH-GRAVITY Antigravity CLI control-plane bridge.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AG_DIR="$ROOT_DIR/tools/antigravity_three_account"
STATE_DIR="${AGY_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/high-gravity/antigravity}"
CONFIG_FILE="${AGY_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/high-gravity/antigravity/accounts.json}"
STATE_DIR="${AGY_STATE_DIR:-$HOME/.local/state/high-gravity/antigravity}"
CONFIG_FILE="${AGY_CONFIG:-$HOME/.config/high-gravity/antigravity/accounts.json}"
VENV_DIR="${AGY_VENV:-$AG_DIR/.venv}"
PY_BIN="$VENV_DIR/bin/python"
if [ ! -x "$PY_BIN" ]; then
    PY_BIN="$(command -v python3)"
fi

log() { printf '[hg-antigravity] %s\n' "$*"; }

export HG_CLIENT_TARGET="${HG_CLIENT_TARGET:-antigravity}"
export HG_TRAFFIC_MUTATION_ENABLED="${HG_TRAFFIC_MUTATION_ENABLED:-0}"
export HG_KHOJ_BINARY_INJECT="${HG_KHOJ_BINARY_INJECT:-0}"
export HG_DECRYPTED_TRAFFIC_LOG="${HG_DECRYPTED_TRAFFIC_LOG:-1}"
export HG_DECRYPTED_TRAFFIC_FULL_BODY="${HG_DECRYPTED_TRAFFIC_FULL_BODY:-1}"
export HG_MICROPROXY_FRONT="${HG_MICROPROXY_FRONT:-1}"
export HG_EDGE_EVENT_LOG="${HG_EDGE_EVENT_LOG:-$ROOT_DIR/logs/microproxy_events.jsonl}"
export HG_DECRYPTED_TRAFFIC_LOG_FILE="${HG_DECRYPTED_TRAFFIC_LOG_FILE:-$ROOT_DIR/logs/traffic_flows.jsonl}"
export HG_DECRYPTED_TRAFFIC_LOG_MAX_BYTES="${HG_DECRYPTED_TRAFFIC_LOG_MAX_BYTES:-104857600}"
export HG_DECRYPTED_TRAFFIC_LOG_BACKUP_COUNT="${HG_DECRYPTED_TRAFFIC_LOG_BACKUP_COUNT:-5}"
export HG_DECRYPTED_TRAFFIC_QUEUE_SIZE="${HG_DECRYPTED_TRAFFIC_QUEUE_SIZE:-256}"
export HG_ANTIGRAVITY_STATE_FILE="$STATE_DIR/state.json"

usage() {
    cat <<USAGE
Usage: ./hg.sh antigravity <command> [args]

Commands:
  bootstrap          Create wrapper venv and staged three-account config.
  status             Show agy-rotate status plus proxy/microproxy monitoring pointers.
  run [agy args...]  Run through agy-rotate with Antigravity-safe logging env.
  resume             Resume the last saved agy-rotate command.
  monitor            Human summary of Antigravity + proxy + C microproxy streams.
  streams [cmd]      Summarize/tail/export decrypted traffic and microproxy JSONL.
  logs               Tail proxy, traffic-flow, C microproxy, and session logs.
  env                Print export lines for manual shell integration.
USAGE
}

cmd="${1:-status}"
shift || true

case "$cmd" in
    bootstrap|setup)
        exec "$AG_DIR/setup.sh" "$@"
        ;;
    status)
        log "config=$CONFIG_FILE"
        log "state=$STATE_DIR/state.json"
        log "traffic_log=$HG_DECRYPTED_TRAFFIC_LOG_FILE"
        "$PY_BIN" "$AG_DIR/agy-rotate.py" --config "$CONFIG_FILE" --state-dir "$STATE_DIR" --status "$@"
        if command -v curl >/dev/null 2>&1; then
            curl -fsS --max-time 2 http://127.0.0.1:${HG_PROXY_PORT:-9998}/hg/antigravity/status 2>/dev/null || true
            printf '\n'
        fi
        ;;
    run)
        exec "$PY_BIN" "$AG_DIR/agy-rotate.py" --config "$CONFIG_FILE" --state-dir "$STATE_DIR" "$@"
        ;;
    resume)
        exec "$PY_BIN" "$AG_DIR/agy-rotate.py" --config "$CONFIG_FILE" --state-dir "$STATE_DIR" --resume "$@"
        ;;
    monitor)
        log "stream paths"
        "$PY_BIN" "$AG_DIR/ag-streams.py" \
            --traffic-log "$HG_DECRYPTED_TRAFFIC_LOG_FILE" \
            --microproxy-log "$HG_EDGE_EVENT_LOG" \
            --state-file "$STATE_DIR/state.json" paths
        log "stream summary"
        "$PY_BIN" "$AG_DIR/ag-streams.py" \
            --traffic-log "$HG_DECRYPTED_TRAFFIC_LOG_FILE" \
            --microproxy-log "$HG_EDGE_EVENT_LOG" \
            --state-file "$STATE_DIR/state.json" summary
        if command -v curl >/dev/null 2>&1; then
            log "proxy telemetry"
            curl -fsS --max-time 2 "http://127.0.0.1:${HG_PROXY_PORT:-9998}/hg/telemetry" 2>/dev/null || true
            printf '\n'
        fi
        ;;
    streams|stream)
        exec "$PY_BIN" "$AG_DIR/ag-streams.py" \
            --traffic-log "$HG_DECRYPTED_TRAFFIC_LOG_FILE" \
            --microproxy-log "$HG_EDGE_EVENT_LOG" \
            --state-file "$STATE_DIR/state.json" "$@"
        ;;
    logs)
        touch "$ROOT_DIR/logs/proxy.log" "$HG_DECRYPTED_TRAFFIC_LOG_FILE" "$HG_EDGE_EVENT_LOG"
        log "tailing logs; Ctrl-C to stop"
        tail -f "$ROOT_DIR/logs/proxy.log" "$HG_DECRYPTED_TRAFFIC_LOG_FILE" "$HG_EDGE_EVENT_LOG" "$STATE_DIR"/sessions/*.log 2>/dev/null || true
        ;;
    env)
        cat <<ENV
export HG_CLIENT_TARGET=antigravity
export HG_TRAFFIC_MUTATION_ENABLED=0
export HG_KHOJ_BINARY_INJECT=0
export HG_DECRYPTED_TRAFFIC_LOG=1
export HG_DECRYPTED_TRAFFIC_FULL_BODY=1
export HG_DECRYPTED_TRAFFIC_LOG_FILE="$HG_DECRYPTED_TRAFFIC_LOG_FILE"
export HG_DECRYPTED_TRAFFIC_LOG_MAX_BYTES="$HG_DECRYPTED_TRAFFIC_LOG_MAX_BYTES"
export HG_DECRYPTED_TRAFFIC_LOG_BACKUP_COUNT="$HG_DECRYPTED_TRAFFIC_LOG_BACKUP_COUNT"
export HG_DECRYPTED_TRAFFIC_QUEUE_SIZE="$HG_DECRYPTED_TRAFFIC_QUEUE_SIZE"
export HG_ANTIGRAVITY_STATE_FILE="$STATE_DIR/state.json"
export HG_MICROPROXY_FRONT="$HG_MICROPROXY_FRONT"
export HG_EDGE_EVENT_LOG="$HG_EDGE_EVENT_LOG"
export AGY_CONFIG="$CONFIG_FILE"
export AGY_STATE_DIR="$STATE_DIR"
ENV
        ;;
    help|-h|--help)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
