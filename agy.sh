#!/usr/bin/env bash
# HIGH-GRAVITY triple-account Antigravity launcher.

set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HG="$ROOT_DIR/hg.sh"
CONFIG_FILE="${AGY_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/high-gravity/antigravity/accounts.json}"
MONITOR_LOG="${AGY_MONITOR_LOG:-$ROOT_DIR/logs/antigravity_monitor.log}"
DRY_RUN="${AGY_LAUNCH_DRY_RUN:-0}"

export HG_CLIENT_TARGET="${HG_CLIENT_TARGET:-antigravity}"
export HG_MICROPROXY_FRONT="${HG_MICROPROXY_FRONT:-1}"
export HG_TRAFFIC_MUTATION_ENABLED="${HG_TRAFFIC_MUTATION_ENABLED:-0}"
export HG_LOCAL_ACK_TELEMETRY="${HG_LOCAL_ACK_TELEMETRY:-0}"
export HG_KHOJ_BINARY_INJECT="${HG_KHOJ_BINARY_INJECT:-0}"
export HG_DECRYPTED_TRAFFIC_LOG="${HG_DECRYPTED_TRAFFIC_LOG:-1}"
export HG_EDGE_EVENT_LOG="${HG_EDGE_EVENT_LOG:-$ROOT_DIR/logs/microproxy_events.jsonl}"

log() { printf '[agy-launch] %s\n' "$*"; }
run() {
    if [[ "$DRY_RUN" == "1" ]]; then
        printf '[agy-launch] DRY_RUN:'
        printf ' %q' "$@"
        printf '\n'
        return 0
    fi
    "$@"
}
exec_or_print() {
    if [[ "$DRY_RUN" == "1" ]]; then
        run "$@"
        return 0
    fi
    exec "$@"
}

usage() {
    cat <<'USAGE'
Usage: ./agy.sh [command] [args]

Commands:
  launch              Start C-front/Python proxy stack and open a live monitor.
  run [agy args...]   Launch stack/monitor, then run the triple-account wrapper.
  resume [args...]    Launch stack/monitor, then resume the saved command.
  monitor             Run the live monitor in the current terminal.
  monitor-window      Open the live monitor in another terminal/tmux pane.
  status              Show Antigravity and microproxy status.
  bootstrap           Stage triple-account config and wrapper venv.
  audit [args...]     Run the HIGH-GRAVITY E2E audit.
  stop                Stop the managed proxy stack.
  plan                Print launch actions without executing them.
  help                Show this help.

Environment:
  AGY_LAUNCH_DRY_RUN=1       Print commands without running them.
  AGY_MONITOR_INTERVAL=2     Live monitor refresh interval in seconds.
  AGY_NO_MONITOR_WINDOW=1    Do not open the companion monitor window.
USAGE
}

require_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log "triple-account config missing: $CONFIG_FILE"
        log "run: ./agy.sh bootstrap"
        [[ "$DRY_RUN" == "1" ]] && return 0
        return 3
    fi
}

monitor_loop() {
    local interval="${AGY_MONITOR_INTERVAL:-2}"
    mkdir -p "$ROOT_DIR/logs"
    while true; do
        printf '\033[2J\033[H'
        printf 'HIGH-GRAVITY // ANTIGRAVITY LIVE MONITOR // %s\n\n' "$(date -Is)"
        "$HG" antigravity monitor || true
        printf '\nRefresh: %ss  |  Ctrl-C to stop\n' "$interval"
        sleep "$interval"
    done
}

open_monitor_window() {
    if [[ "${AGY_NO_MONITOR_WINDOW:-0}" == "1" ]]; then
        log "companion monitor window disabled"
        return 0
    fi
    if [[ "$DRY_RUN" == "1" ]]; then
        log "DRY_RUN: open companion monitor window"
        return 0
    fi

    mkdir -p "$ROOT_DIR/logs"
    local command="cd $(printf '%q' "$ROOT_DIR") && exec ./agy.sh monitor"
    if [[ -n "${TMUX:-}" ]] && command -v tmux >/dev/null 2>&1; then
        tmux split-window -h "$command"
        log "monitor opened in tmux pane"
    elif command -v konsole >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
        konsole --new-tab -p tabtitle='HIGH-GRAVITY Monitor' -e bash -lc "$command" >/dev/null 2>&1 &
        log "monitor opened in Konsole"
    elif command -v x-terminal-emulator >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
        x-terminal-emulator -T 'HIGH-GRAVITY Monitor' -e bash -lc "$command" >/dev/null 2>&1 &
        log "monitor opened in terminal window"
    elif command -v gnome-terminal >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
        gnome-terminal --title='HIGH-GRAVITY Monitor' -- bash -lc "$command" >/dev/null 2>&1 &
        log "monitor opened in GNOME Terminal"
    elif command -v xterm >/dev/null 2>&1 && [[ -n "${DISPLAY:-}" ]]; then
        xterm -T 'HIGH-GRAVITY Monitor' -e bash -lc "$command" >/dev/null 2>&1 &
        log "monitor opened in xterm"
    else
        nohup bash -lc "$command" >"$MONITOR_LOG" 2>&1 &
        printf '%s\n' "$!" > "$ROOT_DIR/logs/antigravity_monitor.pid"
        log "no GUI terminal detected; monitor backgrounded at $MONITOR_LOG"
    fi
}

launch_stack() {
    require_config
    run "$HG" microproxy build
    run "$HG" proxy start
    open_monitor_window
    run "$HG" antigravity status
}

cd "$ROOT_DIR"
cmd="${1:-launch}"
shift || true
case "$cmd" in
    launch|start)
        launch_stack
        ;;
    run)
        launch_stack
        exec_or_print "$HG" antigravity run "$@"
        ;;
    resume)
        launch_stack
        exec_or_print "$HG" antigravity resume "$@"
        ;;
    monitor)
        monitor_loop
        ;;
    monitor-window)
        open_monitor_window
        ;;
    status)
        "$HG" microproxy status || true
        exec "$HG" antigravity status "$@"
        ;;
    bootstrap|setup)
        exec "$HG" antigravity bootstrap "$@"
        ;;
    audit)
        exec "$HG" audit "$@"
        ;;
    stop)
        exec "$HG" proxy stop
        ;;
    plan)
        DRY_RUN=1
        launch_stack
        ;;
    help|-h|--help)
        usage
        ;;
    *)
        log "unknown command: $cmd"
        usage >&2
        exit 2
        ;;
esac
