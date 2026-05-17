#!/usr/bin/env bash
# Procedural C++/Vulkan HMI control-plane helper.
#
# This script only builds, validates, or explicitly launches the local HMI
# prototype. It does not start/stop proxies and does not alter routing.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HMI_DIR="${HG_HMI_DIR:-$ROOT_DIR/src/hmi}"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="${HG_HMI_LOG_FILE:-$LOG_DIR/hmi.log}"

usage() {
    cat <<'USAGE'
Usage: ./hg.sh hmi <command>

Commands:
  status       Report HMI path, build artifacts, and runtime readiness
  build        Build the C++ validator and shaders with the existing Makefile
  check        Run headless HMI ABI validation; compile shaders when glslc exists
  run          Launch an explicit HMI runtime binary when display/Vulkan are ready
  dash         Alias for run (keeps legacy naming aligned with HMI dashboard users)
  dashboard    Launch the HMI TUI dashboard (same as tui)
  tui          Launch the text UI control panel without touching proxy routing
  help         Show this help

Configuration:
  HG_HMI_DIR=/path/to/hmi             Default: src/hmi.
  HG_HMI_BIN=/path/to/runtime         Override executable used by run.
  HG_HMI_LOG_FILE=/path/to/log        Default: logs/hmi.log.
  HG_HMI_ALLOW_HEADLESS_RUN=1         Allow run without DISPLAY/WAYLAND_DISPLAY.
  HG_HMI_ALLOW_NO_VULKANINFO=1        Allow run without vulkaninfo probing.
  HG_HMI_TELEMETRY_HOST=127.0.0.1     Proxy telemetry host consumed by hmi-runner.
  HG_HMI_TELEMETRY_PORT=9998          Proxy telemetry port consumed by hmi-runner.

These commands do not start, stop, or reroute HIGH-GRAVITY proxy traffic.
USAGE
}

require_hmi_dir() {
    if [ -d "$HMI_DIR" ] && [ -f "$HMI_DIR/Makefile" ]; then
        return 0
    fi

    echo "HMI source path is not configured: $HMI_DIR" >&2
    echo "Set HG_HMI_DIR to the C++ procedural HMI directory." >&2
    return 3
}

has_display() {
    [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]
}

has_vulkan_probe() {
    command -v vulkaninfo >/dev/null 2>&1 && vulkaninfo --summary >/dev/null 2>&1
}

print_vulkan_probe() {
    local output

    if ! command -v vulkaninfo >/dev/null 2>&1; then
        echo "Vulkan probe: unavailable (vulkaninfo not found)"
        echo "Vulkan diagnostic: install vulkan-tools or set HG_HMI_ALLOW_NO_VULKANINFO=1 to bypass this guard."
        return 1
    fi

    if output="$(vulkaninfo --summary 2>&1)"; then
        echo "Vulkan probe: runtime available"
        printf '%s\n' "$output" | sed -n '1,3p' | sed 's/^/Vulkan summary: /'
        return 0
    fi

    echo "Vulkan probe: unavailable (vulkaninfo --summary failed)"
    printf '%s\n' "$output" | sed -n '1,5p' | sed 's/^/Vulkan diagnostic: /'
    return 1
}

print_proxy_probe() {
    local host="${HG_HMI_TELEMETRY_HOST:-${HG_PROXY_HOST:-127.0.0.1}}"
    local port="${HG_HMI_TELEMETRY_PORT:-${PROXY_PORT:-9998}}"
    local url="http://${host}:${port}/hg/telemetry"
    local body

    echo "Telemetry source: $url"
    if command -v curl >/dev/null 2>&1 && body="$(curl -fsS --max-time 1 "$url" 2>/dev/null)"; then
        echo "Proxy telemetry: reachable"
        if command -v python3 >/dev/null 2>&1; then
            HG_HMI_TELEMETRY_BODY="$body" python3 - <<'PY'
import json
import os

try:
    payload = json.loads(os.environ.get("HG_HMI_TELEMETRY_BODY", "{}"))
except Exception:
    raise SystemExit(0)

shared = payload.get("shared_metrics") or {}
mode = payload.get("upstream_inference_mode") or shared.get("upstream_inference_mode") or "unknown"
exact_hits = int(shared.get("exact_response_cache_hits") or payload.get("exact_response_cache_hits") or 0)
exact_stores = int(shared.get("exact_response_cache_stores") or payload.get("exact_response_cache_stores") or 0)
canonical_hits = int(shared.get("canonical_response_cache_hits") or payload.get("canonical_response_cache_hits") or 0)
canonical_stores = int(shared.get("canonical_response_cache_stores") or payload.get("canonical_response_cache_stores") or 0)
forwards = int(shared.get("upstream_inference_forwards") or payload.get("upstream_inference_forwards") or 0)
misses = int(shared.get("upstream_inference_cache_misses") or payload.get("upstream_inference_cache_misses") or 0)
blocks = int(shared.get("upstream_inference_blocks") or payload.get("upstream_inference_blocks") or 0)
blocks += int(shared.get("upstream_inference_cache_only_blocks") or payload.get("upstream_inference_cache_only_blocks") or 0)
acks = int(shared.get("local_ack_telemetry") or payload.get("local_ack_telemetry") or 0)
ack_bytes = int(shared.get("local_ack_bytes_avoided") or payload.get("local_ack_bytes_avoided") or 0)
print(f"Proxy inference mode: {mode}")
print(f"Proxy response cache: {exact_hits + canonical_hits} hit / {exact_stores + canonical_stores} store")
print(f"Proxy upstream gate: {forwards} forward / {misses} miss / {blocks} block")
print(f"Proxy local ACK: {acks} req / {ack_bytes // 1024} KiB avoided")
ebpf = payload.get("ebpf") if isinstance(payload.get("ebpf"), dict) else {}
observer = ebpf.get("status") if isinstance(ebpf.get("status"), dict) else {}

def num(data, key):
    try:
        return int(data.get(key, 0) or 0)
    except Exception:
        return 0

if ebpf:
    active = bool(ebpf.get("active") or observer.get("active") or observer.get("running"))
    stale = bool(ebpf.get("stale") or observer.get("stale"))
    if ebpf.get("read_error"):
        state = "read-error"
    elif stale:
        state = "stale"
    elif active:
        state = "active"
    elif ebpf.get("present"):
        state = "event-data" if num(ebpf, "events_total") else "no-events"
    else:
        state = "inactive"
    mode = ebpf.get("mode") or observer.get("mode") or observer.get("active_mode") or "-"
    tool = ebpf.get("tool") or observer.get("tool") or observer.get("active_tool") or observer.get("backend") or "-"
    events = ebpf.get("by_event") if isinstance(ebpf.get("by_event"), dict) else {}
    event_text = ",".join(f"{key}:{value}" for key, value in events.items()) or "none"
    routes = ebpf.get("by_route_class") if isinstance(ebpf.get("by_route_class"), dict) else {}
    route_text = ",".join(f"{key}:{value}" for key, value in routes.items()) or "none"
    retry = ebpf.get("retry_storm") if isinstance(ebpf.get("retry_storm"), dict) else {}
    retry_text = "active" if retry.get("active") else "quiet"
    sessions = ebpf.get("sessions") if isinstance(ebpf.get("sessions"), dict) else {}
    if sessions:
        session_text = f"{num(sessions, 'session_count')}/{num(sessions, 'required_sessions')} visible"
    else:
        session_text = "not-reported"
    print(
        "Proxy eBPF observer: "
        f"{state} mode={mode} tool={tool} "
        f"events={num(ebpf, 'events_total')} ({event_text}) "
        f"direct={num(ebpf, 'direct_egress')} "
        f"retry={retry_text}:{num(retry, 'max_rate')} "
        f"sessions={session_text} routes={route_text}"
    )
PY
        fi
    elif command -v curl >/dev/null 2>&1; then
        echo "Proxy telemetry: unavailable"
    else
        echo "Proxy telemetry: not probed (curl missing)"
    fi
}

find_hmi_bin() {
    local candidate

    if [ -n "${HG_HMI_BIN:-}" ]; then
        [ -x "$HG_HMI_BIN" ] && {
            printf '%s\n' "$HG_HMI_BIN"
            return 0
        }
        return 1
    fi

    for candidate in \
        "$HMI_DIR/build/highgravity-hmi" \
        "$HMI_DIR/build/hg-hmi" \
        "$HMI_DIR/build/hmi-runner" \
        "$HMI_DIR/build/hmi" \
        "$HMI_DIR/highgravity-hmi" \
        "$HMI_DIR/hg-hmi" \
        "$HMI_DIR/hmi"
    do
        if [ -x "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

print_status() {
    local bin

    echo "HIGH-GRAVITY procedural HMI status"
    echo "Proxy routing: unchanged; HMI control-plane commands are isolated."
    echo "HMI path: $HMI_DIR"
    echo "Log file: $LOG_FILE"

    if ! require_hmi_dir; then
        return 3
    fi

    if command -v make >/dev/null 2>&1; then
        echo "make: available"
    else
        echo "make: missing"
    fi

    if command -v "${CXX:-c++}" >/dev/null 2>&1; then
        echo "C++ compiler: ${CXX:-c++}"
    else
        echo "C++ compiler: missing (${CXX:-c++})"
    fi

    if command -v "${GLSLC:-glslc}" >/dev/null 2>&1; then
        echo "glslc: available"
    else
        echo "glslc: missing; shader compilation will be skipped by check"
    fi

    if [ -x "$HMI_DIR/build/hmi-validate" ]; then
        echo "Validator: built"
    else
        echo "Validator: not built"
    fi

    if [ -s "$HMI_DIR/build/shaders/dashboard.vert.spv" ] && [ -s "$HMI_DIR/build/shaders/dashboard.frag.spv" ]; then
        echo "Shaders: built"
    else
        echo "Shaders: not built"
    fi

    if has_display; then
        echo "Display: available"
    else
        echo "Display: not available"
    fi

    print_vulkan_probe || true
    print_proxy_probe

    if bin="$(find_hmi_bin)"; then
        echo "Runtime binary: $bin"
    else
        echo "Runtime binary: not configured"
    fi
}

build_hmi() {
    require_hmi_dir
    echo "Building procedural HMI in $HMI_DIR."
    echo "Proxy routing remains unchanged."
    make -C "$HMI_DIR" all
}

check_hmi() {
    require_hmi_dir

    echo "Checking procedural HMI in $HMI_DIR."
    echo "This is headless validation only; no display, swapchain, or proxy routing is touched."

    if command -v "${GLSLC:-glslc}" >/dev/null 2>&1; then
        make -C "$HMI_DIR" check
        return $?
    fi

    echo "glslc is not available; skipping shader compilation."
    echo "Running C++ ABI/layout validation only."
    make -C "$HMI_DIR" build/hmi-validate
    "$HMI_DIR/build/hmi-validate"
}

run_hmi() {
    local bin

    require_hmi_dir

    if ! has_display && [ "${HG_HMI_ALLOW_HEADLESS_RUN:-0}" != "1" ]; then
        echo "No DISPLAY or WAYLAND_DISPLAY is available; HMI runtime was not started."
        echo "Set HG_HMI_ALLOW_HEADLESS_RUN=1 to override for offscreen/runtime-specific launchers."
        echo "Proxy routing remains unchanged."
        return 0
    fi

    if ! has_vulkan_probe && [ "${HG_HMI_ALLOW_NO_VULKANINFO:-0}" != "1" ]; then
        echo "Vulkan runtime probe failed; HMI runtime was not started."
        print_vulkan_probe || true
        echo "Set HG_HMI_ALLOW_NO_VULKANINFO=1 to skip this guard for runtime-specific launchers."
        echo "Proxy routing remains unchanged."
        return 0
    fi

    if ! bin="$(find_hmi_bin)"; then
        echo "No runnable HMI binary found." >&2
        echo "Build or set HG_HMI_BIN to the procedural HMI executable." >&2
        return 4
    fi

    mkdir -p "$(dirname "$LOG_FILE")"
    {
        echo
        echo "[$(date -Is)] launching procedural HMI"
        echo "binary=$bin"
        echo "telemetry_host=${HG_HMI_TELEMETRY_HOST:-${HG_PROXY_HOST:-127.0.0.1}}"
        echo "telemetry_port=${HG_HMI_TELEMETRY_PORT:-${PROXY_PORT:-9998}}"
        echo "note=proxy routing unchanged"
    } >> "$LOG_FILE"

    echo "Launching procedural HMI: $bin"
    echo "Log: $LOG_FILE"
    echo "Proxy routing remains unchanged."
    exec "$bin" "$@" >> "$LOG_FILE" 2>&1
}

run_hmi_tui() {
    local dashboard_script="$ROOT_DIR/src/hg_dashboard.py"

    if [ ! -f "$dashboard_script" ]; then
        echo "HMI TUI script not found: $dashboard_script" >&2
        return 3
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        echo "python3 is required for HMI TUI mode." >&2
        return 4
    fi

    if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
        echo "Usage: ./hg.sh hmi tui"
        return 0
    fi

    if [ ! -t 0 ] && [ ! -t 1 ]; then
        echo "HMI TUI mode requires an interactive terminal."
        return 5
    fi

    echo "Launching HMI TUI dashboard."
    echo "Proxy routing remains unchanged."
    exec python3 "$dashboard_script" "$@"
}

cmd="${1:-status}"
case "$cmd" in
    status)
        print_status
        ;;
    build)
        build_hmi
        ;;
    check)
        check_hmi
        ;;
    run|dash)
        shift || true
        run_hmi "$@"
        ;;
    dashboard|tui)
        shift || true
        run_hmi_tui "$@"
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo "Unknown hmi command: $cmd" >&2
        usage >&2
        exit 2
        ;;
esac
