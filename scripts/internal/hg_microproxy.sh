#!/usr/bin/env bash
# C microproxy stage management for the HIGH-GRAVITY Antigravity stack.
#
# The live Antigravity launch path uses hg-edge as the C front when enabled.
# This helper provides build/smoke/status controls and keeps ad hoc runs on
# non-live ports unless HG_MICROPROXY_FORCE_LIVE_PORTS=1 is set explicitly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
PID_FILE="${HG_MICROPROXY_PID_FILE:-$LOG_DIR/microproxy.pid}"
LOG_FILE="${HG_MICROPROXY_LOG_FILE:-$LOG_DIR/microproxy.log}"
LISTEN_ENDPOINT="${HG_MICROPROXY_LISTEN:-127.0.0.1:18443}"
UPSTREAM_ENDPOINT="${HG_MICROPROXY_UPSTREAM:-127.0.0.1:443}"
LIVE_PROXY_PORT="${HG_PROXY_PORT:-9998}"

usage() {
    cat <<'USAGE'
Usage: ./hg.sh microproxy <command>

Commands:
  status       Report configured C microproxy path and build/runtime readiness
  build        Build the configured C microproxy without starting it
  run          Start the C microproxy on non-live defaults
  smoke        Build and probe hg-edge with local fixture traffic only
  smoke-direct Build and probe the direct fast-path against local fixtures
  stop         Stop the C microproxy started by this helper
  help         Show this help

Configuration:
  HG_MICROPROXY_DIR=/path/to/prototype  Override prototype directory.
  HG_MICROPROXY_BIN=/path/to/binary      Override prototype executable.
  HG_MICROPROXY_LISTEN=HOST:PORT         Default: 127.0.0.1:18443.
  HG_MICROPROXY_UPSTREAM=HOST:PORT       Default: 127.0.0.1:443.
  HG_MICROPROXY_PID_FILE=/path/to/pid    Default: logs/microproxy.pid.
  HG_MICROPROXY_LOG_FILE=/path/to/log    Default: logs/microproxy.log.
  HG_MICROPROXY_HOT_PATH_OBSERVE=1       Emit advisory C hot-path markers.
  HG_MICROPROXY_DIRECT_UPSTREAM=HOST:PORT Opt-in direct fast-path upstream.
  HG_MICROPROXY_DIRECT_HOT_PATH=1        Enable direct fast-path for candidates.
  HG_MICROPROXY_FORCE_LIVE_PORTS=1       Allow privileged/live listen ports.
  HG_MICROPROXY_SMOKE_LISTEN=HOST:PORT   Override smoke listen endpoint.
  HG_MICROPROXY_SMOKE_UPSTREAM=HOST:PORT Override smoke upstream endpoint.

Default search paths:
  src/microproxy/
  microproxy/
  prototypes/microproxy/
  tools/microproxy/

The standard Antigravity stack is a C-front -> Python TLS-observer chain.
Ad hoc run/smoke commands here do not switch live traffic unless explicitly configured.
USAGE
}

candidate_dirs() {
    if [ -n "${HG_MICROPROXY_DIR:-}" ]; then
        printf '%s\n' "$HG_MICROPROXY_DIR"
        return 0
    fi

    printf '%s\n' \
        "$ROOT_DIR/src/microproxy" \
        "$ROOT_DIR/microproxy" \
        "$ROOT_DIR/prototypes/microproxy" \
        "$ROOT_DIR/tools/microproxy"
}

find_microproxy_dir() {
    local candidate
    while IFS= read -r candidate; do
        [ -d "$candidate" ] && {
            printf '%s\n' "$candidate"
            return 0
        }
    done <<EOF
$(candidate_dirs)
EOF

    return 1
}

detect_build_system() {
    local dir="$1"

    if [ -f "$dir/Cargo.toml" ]; then
        printf '%s\n' cargo
    elif [ -f "$dir/Makefile" ] || [ -f "$dir/makefile" ]; then
        printf '%s\n' make
    elif [ -f "$dir/go.mod" ]; then
        printf '%s\n' go
    elif [ -f "$dir/package.json" ]; then
        printf '%s\n' npm
    else
        return 1
    fi
}

endpoint_port() {
    local endpoint="$1"
    local port="${endpoint##*:}"

    if [ "$port" = "$endpoint" ] || ! [[ "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
        return 1
    fi

    printf '%s\n' "$port"
}

endpoint_host() {
    local endpoint="$1"
    local host="${endpoint%:*}"

    [ "$host" != "$endpoint" ] || return 1
    [ -n "$host" ] || return 1

    printf '%s\n' "$host"
}

ensure_safe_endpoint() {
    local label="$1"
    local endpoint="$2"
    local port

    if ! port="$(endpoint_port "$endpoint")"; then
        echo "Invalid microproxy $label endpoint: $endpoint" >&2
        return 2
    fi

    if [ "${HG_MICROPROXY_FORCE_LIVE_PORTS:-0}" = "1" ]; then
        return 0
    fi

    if [ "$port" -lt 1024 ]; then
        echo "Refusing privileged microproxy $label port $port." >&2
        echo "Set HG_MICROPROXY_FORCE_LIVE_PORTS=1 to override explicitly." >&2
        return 5
    fi

    if [ "$port" = "443" ] || [ "$port" = "$LIVE_PROXY_PORT" ]; then
        echo "Refusing live HIGH-GRAVITY $label port $port." >&2
        echo "Set HG_MICROPROXY_FORCE_LIVE_PORTS=1 to override explicitly." >&2
        return 5
    fi
}

ensure_safe_listen_endpoint() {
    ensure_safe_endpoint "listen" "$LISTEN_ENDPOINT"
}

ensure_local_endpoint() {
    local label="$1"
    local endpoint="$2"
    local host

    if ! host="$(endpoint_host "$endpoint")"; then
        echo "Invalid microproxy $label endpoint: $endpoint" >&2
        return 2
    fi

    case "$host" in
        127.0.0.1|localhost)
            ;;
        *)
            echo "Refusing non-local microproxy $label host $host." >&2
            echo "Smoke traffic must stay on localhost." >&2
            return 5
            ;;
    esac

    ensure_safe_endpoint "$label" "$endpoint"
}

pid_is_running() {
    local pid="$1"
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

hot_path_observe_enabled() {
    [ "${HG_MICROPROXY_HOT_PATH_OBSERVE:-0}" = "1" ] || \
        [ "${HG_MICROPROXY_HOT_PATH_OBSERVE:-0}" = "true" ]
}

direct_fast_path_enabled() {
    [ -n "${HG_MICROPROXY_DIRECT_UPSTREAM:-}" ]
}

direct_fast_path_hot_enabled() {
    case "${HG_MICROPROXY_DIRECT_HOT_PATH:-0}" in
        1|true|TRUE|yes|YES|on|ON)
            return 0
            ;;
    esac
    return 1
}

print_direct_fast_path_state() {
    if direct_fast_path_enabled; then
        if direct_fast_path_hot_enabled; then
            echo "Direct fast-path: enabled (upstream=$HG_MICROPROXY_DIRECT_UPSTREAM, hot-path=enabled)"
        else
            echo "Direct fast-path: enabled (upstream=$HG_MICROPROXY_DIRECT_UPSTREAM, hot-path=disabled)"
        fi
    else
        echo "Direct fast-path: disabled"
    fi
}

running_pid() {
    local pid

    [ -f "$PID_FILE" ] || return 1
    pid="$(tr -d '[:space:]' < "$PID_FILE")"
    if pid_is_running "$pid"; then
        printf '%s\n' "$pid"
        return 0
    fi

    return 1
}

find_microproxy_bin() {
    local dir="$1"
    local candidate

    if [ -n "${HG_MICROPROXY_BIN:-}" ]; then
        [ -x "$HG_MICROPROXY_BIN" ] && {
            printf '%s\n' "$HG_MICROPROXY_BIN"
            return 0
        }
        return 1
    fi

    for candidate in \
        "$dir/build/hg-edge" \
        "$dir/hg-edge" \
        "$dir/target/release/hg-microproxy" \
        "$dir/target/debug/hg-microproxy" \
        "$dir/target/release/microproxy" \
        "$dir/target/debug/microproxy"
    do
        if [ -x "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

print_status() {
    local dir build_system pid

    echo "HIGH-GRAVITY C microproxy status"
    echo "Live traffic: standard Antigravity path is C-front -> Python TLS observer when HG_MICROPROXY_FRONT=1."
    echo "Runtime listen: $LISTEN_ENDPOINT"
    echo "Runtime upstream: $UPSTREAM_ENDPOINT"
    print_direct_fast_path_state
    echo "Runtime pid file: $PID_FILE"
    echo "Runtime log file: $LOG_FILE"

    if ! dir="$(find_microproxy_dir)"; then
        echo "C microproxy path: not configured"
        echo "Set HG_MICROPROXY_DIR or add one of the default prototype directories."
        return 3
    fi

    echo "C microproxy path: $dir"

    if build_system="$(detect_build_system "$dir")"; then
        echo "Build system: $build_system"
    else
        echo "Build system: not detected"
        return 4
    fi

    if pid="$(running_pid)"; then
        echo "C microproxy process: running (PID: $pid)"
    elif [ -f "$PID_FILE" ]; then
        echo "C microproxy process: not running (stale pid file)"
    else
        echo "C microproxy process: not running"
    fi
}

build_microproxy() {
    local dir build_system

    if ! dir="$(find_microproxy_dir)"; then
        echo "C microproxy path is not configured." >&2
        echo "Set HG_MICROPROXY_DIR or add microproxy/, prototypes/microproxy/, or tools/microproxy/." >&2
        return 3
    fi

    if ! build_system="$(detect_build_system "$dir")"; then
        echo "No supported build system found in $dir." >&2
        echo "Supported markers: Cargo.toml, Makefile, go.mod, package.json." >&2
        return 4
    fi

    echo "Building C microproxy in $dir ($build_system)."
    echo "This builds only; it does not start or switch live traffic."

    case "$build_system" in
        cargo)
            if [ "${HG_MICROPROXY_RELEASE:-0}" = "1" ]; then
                cargo build --manifest-path "$dir/Cargo.toml" --release
            else
                cargo build --manifest-path "$dir/Cargo.toml"
            fi
            ;;
        make)
            if grep -Eq '^build:' "$dir/Makefile" "$dir/makefile" 2>/dev/null; then
                make -C "$dir" build
            else
                make -C "$dir"
            fi
            ;;
        go)
            (cd "$dir" && go build ./...)
            ;;
        npm)
            (cd "$dir" && npm run build)
            ;;
    esac
}

allocate_local_port() {
    python3 - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

wait_for_tcp_endpoint() {
    local endpoint="$1"
    local host port

    host="$(endpoint_host "$endpoint")"
    port="$(endpoint_port "$endpoint")"

    python3 - "$host" "$port" "${HG_MICROPROXY_SMOKE_READY_TIMEOUT:-5}" <<'PY'
import socket
import sys
import time

host = sys.argv[1]
port = int(sys.argv[2])
deadline = time.monotonic() + float(sys.argv[3])

while time.monotonic() < deadline:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            raise SystemExit(0)
    except OSError:
        time.sleep(0.05)

raise SystemExit(1)
PY
}

wait_for_file_pattern() {
    local path="$1"
    local pattern="$2"
    local timeout="${3:-5}"

    python3 - "$path" "$pattern" "$timeout" <<'PY'
from pathlib import Path
import sys
import time

path = Path(sys.argv[1])
pattern = sys.argv[2]
deadline = time.monotonic() + float(sys.argv[3])

while time.monotonic() < deadline:
    if path.exists() and pattern in path.read_text(errors="replace"):
        raise SystemExit(0)
    time.sleep(0.05)

raise SystemExit(1)
PY
}

send_smoke_fixture_request() {
    local endpoint="$1"
    local host port

    host="$(endpoint_host "$endpoint")"
    port="$(endpoint_port "$endpoint")"

    python3 - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
request = (
    b"GET /microproxy-smoke.txt HTTP/1.1\r\n"
    b"Host: smoke.local\r\n"
    b"Connection: close\r\n"
    b"\r\n"
)

with socket.create_connection((host, port), timeout=5) as sock:
    sock.sendall(request)
    response = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk

if b"HTTP/1.0 200 OK" not in response and b"HTTP/1.1 200 OK" not in response:
    sys.stderr.write(response.decode("utf-8", errors="replace"))
    raise SystemExit(1)
if b"high-gravity microproxy smoke ok\n" not in response:
    sys.stderr.write(response.decode("utf-8", errors="replace"))
    raise SystemExit(1)

print(response.split(b"\r\n", 1)[0].decode("ascii", errors="replace"))
PY
}

smoke_microproxy() {
    local dir bin smoke_dir fixture_dir event_log run_log upstream_log
    local smoke_listen smoke_upstream edge_pid="" upstream_pid="" probe_status=0

    if ! dir="$(find_microproxy_dir)"; then
        echo "C microproxy path is not configured." >&2
        echo "Set HG_MICROPROXY_DIR or add microproxy/, prototypes/microproxy/, or tools/microproxy/." >&2
        return 3
    fi

    mkdir -p "$LOG_DIR"
    smoke_dir="${HG_MICROPROXY_SMOKE_DIR:-$(mktemp -d "$LOG_DIR/microproxy-smoke.XXXXXX")}"
    fixture_dir="$smoke_dir/upstream"
    event_log="${HG_MICROPROXY_SMOKE_EVENT_LOG:-$smoke_dir/events.jsonl}"
    run_log="${HG_MICROPROXY_SMOKE_LOG:-$smoke_dir/hg-edge.log}"
    upstream_log="$smoke_dir/upstream.log"
    mkdir -p "$fixture_dir" "$(dirname "$event_log")" "$(dirname "$run_log")"
    printf 'high-gravity microproxy smoke ok\n' > "$fixture_dir/microproxy-smoke.txt"

    smoke_listen="${HG_MICROPROXY_SMOKE_LISTEN:-127.0.0.1:$(allocate_local_port)}"
    smoke_upstream="${HG_MICROPROXY_SMOKE_UPSTREAM:-127.0.0.1:$(allocate_local_port)}"
    if [ "$smoke_listen" = "$smoke_upstream" ] && [ -z "${HG_MICROPROXY_SMOKE_UPSTREAM:-}" ]; then
        smoke_upstream="127.0.0.1:$(allocate_local_port)"
    fi

    ensure_local_endpoint "smoke listen" "$smoke_listen"
    ensure_local_endpoint "smoke upstream" "$smoke_upstream"

    echo "Running microproxy smoke check."
    echo "C microproxy path: $dir"
    echo "Smoke listen: $smoke_listen"
    echo "Smoke upstream: $smoke_upstream"
    print_direct_fast_path_state
    echo "Smoke event log: $event_log"
    echo "This uses localhost fixture traffic only; live routing is unchanged."

    build_microproxy

    if ! bin="$(find_microproxy_bin "$dir")"; then
        echo "No runnable C microproxy binary found in $dir after build." >&2
        return 4
    fi

    python3 -m http.server "$(endpoint_port "$smoke_upstream")" \
        --bind "$(endpoint_host "$smoke_upstream")" \
        --directory "$fixture_dir" > "$upstream_log" 2>&1 &
    upstream_pid="$!"

    cleanup_smoke() {
        if [ -n "$edge_pid" ] && pid_is_running "$edge_pid"; then
            kill "$edge_pid" 2>/dev/null || true
            wait "$edge_pid" 2>/dev/null || true
        fi
        if [ -n "$upstream_pid" ] && pid_is_running "$upstream_pid"; then
            kill "$upstream_pid" 2>/dev/null || true
            wait "$upstream_pid" 2>/dev/null || true
        fi
    }
    trap cleanup_smoke RETURN

    if ! wait_for_tcp_endpoint "$smoke_upstream"; then
        echo "Smoke upstream did not become ready; see $upstream_log." >&2
        return 6
    fi

    (
        cd "$dir"
        args=(
            --relay
            --listen "$smoke_listen"
            --upstream "$smoke_upstream"
            --idle-timeout "${HG_MICROPROXY_SMOKE_IDLE_TIMEOUT:-2}"
            --event-log "$event_log"
        )
        if hot_path_observe_enabled; then
            args+=(--hot-path-observe)
        fi
        printf 'command='
        printf '%q ' "$bin" "${args[@]}"
        printf '\n'
        exec "$bin" "${args[@]}"
    ) >> "$run_log" 2>&1 &
    edge_pid="$!"

    if ! wait_for_file_pattern \
        "$run_log" \
        "relay listening" \
        "${HG_MICROPROXY_SMOKE_READY_TIMEOUT:-5}"; then
        echo "hg-edge smoke relay did not become ready; see $run_log." >&2
        return 6
    fi

    echo "Sending plaintext HTTP fixture through hg-edge..."
    send_smoke_fixture_request "$smoke_listen" || probe_status="$?"

    cleanup_smoke
    trap - RETURN

    if [ "$probe_status" -ne 0 ]; then
        echo "Smoke fixture request failed; see $run_log and $upstream_log." >&2
        return "$probe_status"
    fi

    echo
    echo "Microproxy smoke event summary:"
    python3 "$ROOT_DIR/tools/read_microproxy_events.py" --skip-invalid --missing-ok "$event_log"
    echo
    echo "Smoke complete. Logs: $smoke_dir"
    echo "Ad hoc helper run did not change the managed live C-front chain."
}

start_local_fixture_server() {
    local endpoint="$1"
    local fixture_file="$2"
    local log_file="$3"
    local host port

    host="$(endpoint_host "$endpoint")"
    port="$(endpoint_port "$endpoint")"

    python3 - "$host" "$port" "$fixture_file" "$log_file" <<'PY' &
import sys
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path

host = sys.argv[1]
port = int(sys.argv[2])
fixture = Path(sys.argv[3]).read_bytes()
log_path = Path(sys.argv[4])


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _respond(self):
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"{self.command} {self.path}\n")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(fixture)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(fixture)

    def do_GET(self):
        self._respond()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 0:
            self.rfile.read(length)
        self._respond()

    def do_HEAD(self):
        self._respond()

    def log_message(self, format, *args):
        return


class Server(ThreadingHTTPServer):
    allow_reuse_address = True


server = Server((host, port), Handler)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
PY
    STARTED_PID="$!"
}

send_smoke_direct_fixture_request() {
    local endpoint="$1"
    local host port

    host="$(endpoint_host "$endpoint")"
    port="$(endpoint_port "$endpoint")"

    python3 - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
request = (
    b"POST /exa.api_server_pb.ApiServerService/GetChatMessage HTTP/1.1\r\n"
    b"Host: antigravity.local\r\n"
    b"Content-Type: application/connect+proto\r\n"
    b"Content-Length: 5\r\n"
    b"Connection: close\r\n"
    b"\r\n"
    b"\x00\x00\x00\x00\x00"
)

with socket.create_connection((host, port), timeout=5) as sock:
    sock.sendall(request)
    response = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk

if b"HTTP/1.0 200 OK" not in response and b"HTTP/1.1 200 OK" not in response:
    sys.stderr.write(response.decode("utf-8", errors="replace"))
    raise SystemExit(1)
if b"high-gravity microproxy direct smoke ok\n" not in response:
    sys.stderr.write(response.decode("utf-8", errors="replace"))
    raise SystemExit(1)

print(response.split(b"\r\n", 1)[0].decode("ascii", errors="replace"))
PY
}

smoke_microproxy_direct() {
    local dir bin smoke_dir fixture_dir event_log run_log direct_log
    local smoke_listen smoke_upstream smoke_direct_upstream edge_pid="" direct_pid="" probe_status=0

    if ! dir="$(find_microproxy_dir)"; then
        echo "C microproxy path is not configured." >&2
        echo "Set HG_MICROPROXY_DIR or add microproxy/, prototypes/microproxy/, or tools/microproxy/." >&2
        return 3
    fi

    mkdir -p "$LOG_DIR"
    smoke_dir="${HG_MICROPROXY_SMOKE_DIR:-$(mktemp -d "$LOG_DIR/microproxy-direct-smoke.XXXXXX")}"
    fixture_dir="$smoke_dir/direct-fixture"
    event_log="${HG_MICROPROXY_SMOKE_EVENT_LOG:-$smoke_dir/events.jsonl}"
    run_log="${HG_MICROPROXY_SMOKE_LOG:-$smoke_dir/hg-edge.log}"
    direct_log="$smoke_dir/direct-fixture.log"
    mkdir -p "$fixture_dir" "$(dirname "$event_log")" "$(dirname "$run_log")"
    printf 'high-gravity microproxy direct smoke ok\n' > "$fixture_dir/microproxy-direct-smoke.txt"

    smoke_listen="${HG_MICROPROXY_SMOKE_LISTEN:-127.0.0.1:$(allocate_local_port)}"
    smoke_upstream="${HG_MICROPROXY_SMOKE_UPSTREAM:-127.0.0.1:$(allocate_local_port)}"
    smoke_direct_upstream="127.0.0.1:$(allocate_local_port)"
    if [ "$smoke_listen" = "$smoke_upstream" ] && [ -z "${HG_MICROPROXY_SMOKE_UPSTREAM:-}" ]; then
        smoke_upstream="127.0.0.1:$(allocate_local_port)"
    fi
    if [ "$smoke_direct_upstream" = "$smoke_listen" ] || [ "$smoke_direct_upstream" = "$smoke_upstream" ]; then
        smoke_direct_upstream="127.0.0.1:$(allocate_local_port)"
    fi

    ensure_local_endpoint "smoke listen" "$smoke_listen"
    ensure_safe_endpoint "smoke upstream" "$smoke_upstream"
    ensure_local_endpoint "smoke direct upstream" "$smoke_direct_upstream"

    echo "Running direct-path microproxy smoke check."
    echo "C microproxy path: $dir"
    echo "Smoke listen: $smoke_listen"
    echo "Smoke upstream: $smoke_upstream"
    echo "Smoke direct upstream: $smoke_direct_upstream"
    echo "Direct fast-path: enabled (upstream=$smoke_direct_upstream, hot-path=enabled)"
    echo "Smoke event log: $event_log"
    echo "This uses localhost fixture traffic only; live routing is unchanged."

    build_microproxy

    if ! bin="$(find_microproxy_bin "$dir")"; then
        echo "No runnable C microproxy binary found in $dir after build." >&2
        return 4
    fi

    start_local_fixture_server "$smoke_direct_upstream" "$fixture_dir/microproxy-direct-smoke.txt" "$direct_log"
    direct_pid="$STARTED_PID"

    cleanup_smoke() {
        if [ -n "$edge_pid" ] && pid_is_running "$edge_pid"; then
            kill "$edge_pid" 2>/dev/null || true
            wait "$edge_pid" 2>/dev/null || true
        fi
        if [ -n "$direct_pid" ] && pid_is_running "$direct_pid"; then
            kill "$direct_pid" 2>/dev/null || true
            wait "$direct_pid" 2>/dev/null || true
        fi
    }
    trap cleanup_smoke RETURN

    if ! wait_for_tcp_endpoint "$smoke_direct_upstream"; then
        echo "Smoke direct upstream did not become ready; see $direct_log." >&2
        return 6
    fi

    (
        cd "$dir"
        args=(
            --relay
            --listen "$smoke_listen"
            --upstream "$smoke_upstream"
            --direct-upstream "$smoke_direct_upstream"
            --direct-hot-path
            --idle-timeout "${HG_MICROPROXY_SMOKE_IDLE_TIMEOUT:-2}"
            --event-log "$event_log"
        )
        if hot_path_observe_enabled; then
            args+=(--hot-path-observe)
        fi
        printf 'command='
        printf '%q ' "$bin" "${args[@]}"
        printf '\n'
        exec "$bin" "${args[@]}"
    ) >> "$run_log" 2>&1 &
    edge_pid="$!"

    if ! wait_for_file_pattern \
        "$run_log" \
        "relay listening" \
        "${HG_MICROPROXY_SMOKE_READY_TIMEOUT:-5}"; then
        echo "hg-edge direct smoke relay did not become ready; see $run_log." >&2
        return 6
    fi

    echo "Sending direct-path HTTP fixture through hg-edge..."
    send_smoke_direct_fixture_request "$smoke_listen" || probe_status="$?"

    cleanup_smoke
    trap - RETURN

    if [ "$probe_status" -ne 0 ]; then
        echo "Direct smoke fixture request failed; see $run_log and $direct_log." >&2
        return "$probe_status"
    fi

    echo
    echo "Microproxy direct smoke event summary:"
    python3 "$ROOT_DIR/tools/read_microproxy_events.py" --skip-invalid --missing-ok "$event_log"
    echo
    echo "Smoke complete. Logs: $smoke_dir"
    echo "Ad hoc helper run did not change the managed live C-front chain."
}

run_microproxy() {
    local dir bin pid

    if ! dir="$(find_microproxy_dir)"; then
        echo "C microproxy path is not configured." >&2
        echo "Set HG_MICROPROXY_DIR or add microproxy/, prototypes/microproxy/, or tools/microproxy/." >&2
        return 3
    fi

    ensure_safe_listen_endpoint

    if pid="$(running_pid)"; then
        echo "C microproxy is already running (PID: $pid)."
        echo "Managed live C-front chain remains unchanged."
        return 0
    fi

    if ! bin="$(find_microproxy_bin "$dir")"; then
        echo "No runnable C microproxy binary found in $dir." >&2
        echo "Run './hg.sh microproxy build' first or set HG_MICROPROXY_BIN." >&2
        return 4
    fi

    mkdir -p "$LOG_DIR" "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"

    {
        echo
        echo "[$(date -Is)] starting microproxy prototype"
        echo "binary=$bin"
        echo "listen=$LISTEN_ENDPOINT"
        echo "upstream=$UPSTREAM_ENDPOINT"
        if direct_fast_path_enabled; then
            echo "direct_fast_path=enabled"
            echo "direct_upstream=${HG_MICROPROXY_DIRECT_UPSTREAM}"
            echo "direct_hot_path=${HG_MICROPROXY_DIRECT_HOT_PATH:-0}"
        else
            echo "direct_fast_path=disabled"
        fi
        echo "note=Python proxy remains default live proxy"
    } >> "$LOG_FILE"

    local args=(
        --relay
        --listen "$LISTEN_ENDPOINT"
        --upstream "$UPSTREAM_ENDPOINT"
    )
    if [ -n "${HG_MICROPROXY_DIRECT_UPSTREAM:-}" ]; then
        args+=(--direct-upstream "$HG_MICROPROXY_DIRECT_UPSTREAM")
        case "${HG_MICROPROXY_DIRECT_HOT_PATH:-0}" in
            1|true|TRUE|yes|YES|on|ON) args+=(--direct-hot-path) ;;
        esac
    fi
    if hot_path_observe_enabled; then
        args+=(--hot-path-observe)
    fi

    (
        cd "$dir"
        exec "$bin" "${args[@]}"
    ) >> "$LOG_FILE" 2>&1 &

    pid="$!"
    printf '%s\n' "$pid" > "$PID_FILE"

    sleep "${HG_MICROPROXY_START_GRACE:-0.2}"
    if ! pid_is_running "$pid"; then
        local status=0
        wait "$pid" || status="$?"
        rm -f "$PID_FILE"
        if [ "$status" -eq 0 ]; then
            echo "C microproxy completed during startup; no long-running process is active."
            echo "Log: $LOG_FILE"
            echo "Ad hoc helper run did not change the managed live C-front chain."
            return 0
        fi
        echo "C microproxy exited during startup; see $LOG_FILE." >&2
        return "$status"
    fi

    echo "Started C microproxy (PID: $pid)."
    echo "Listen: $LISTEN_ENDPOINT"
    echo "Upstream: $UPSTREAM_ENDPOINT"
    print_direct_fast_path_state
    echo "Log: $LOG_FILE"
    echo "Ad hoc helper run did not change the managed live C-front chain."
}

stop_microproxy() {
    local pid

    if ! pid="$(running_pid)"; then
        if [ -f "$PID_FILE" ]; then
            rm -f "$PID_FILE"
            echo "Removed stale microproxy pid file."
        else
            echo "C microproxy is not running."
        fi
        echo "Managed live C-front chain remains unchanged."
        return 0
    fi

    kill "$pid"
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        if ! pid_is_running "$pid"; then
            rm -f "$PID_FILE"
            echo "Stopped C microproxy (PID: $pid)."
            echo "Managed live C-front chain remains unchanged."
            return 0
        fi
        sleep 0.2
    done

    echo "C microproxy did not stop after SIGTERM (PID: $pid)." >&2
    echo "Pid file retained: $PID_FILE" >&2
    return 7
}

cmd="${1:-status}"

case "$cmd" in
    status|check)
        print_status
        ;;
    build)
        build_microproxy
        ;;
    run|start)
        run_microproxy
        ;;
    smoke)
        smoke_microproxy
        ;;
    smoke-direct)
        smoke_microproxy_direct
        ;;
    stop)
        stop_microproxy
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo "Unknown microproxy command: $cmd" >&2
        usage >&2
        exit 2
        ;;
esac
