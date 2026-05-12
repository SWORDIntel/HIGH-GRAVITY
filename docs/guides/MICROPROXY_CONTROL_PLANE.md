# Microproxy Control Plane

HIGH-GRAVITY still uses the Python proxy as the default live proxy. The
microproxy commands are disabled-by-default management hooks for prototype
build, readiness checks, and explicit prototype runtime checks only.

## Commands

```bash
./hg.sh microproxy status
./hg.sh microproxy build
./hg.sh microproxy run
./hg.sh microproxy smoke
./hg.sh microproxy stop
```

`status` reports whether a prototype directory exists, which build system was
detected, the configured prototype runtime endpoints, pid/log paths, and
whether the pid file points at a running process. It does not start or stop
anything.

`build` runs the detected local build command for the prototype. It does not
launch the prototype and does not change routing for live traffic.

`smoke` runs a shadow-mode local fixture check for `hg-edge`. It builds the
prototype, starts a Python plaintext HTTP fixture upstream on localhost, starts
`hg-edge` on a separate localhost high port, sends one local HTTP request
through the relay, stops both smoke processes, and prints the passive event
summary with `tools/read_microproxy_events.py`.

The smoke command does not use the live Python proxy, port 443, or port 9998 by
default. It does not call the live `run`/`stop` paths and does not change live
routing. Smoke logs are written under `logs/microproxy-smoke.*` unless
`HG_MICROPROXY_SMOKE_DIR` is set.

`run` starts a prototype binary in the background with non-live defaults:

```bash
HG_MICROPROXY_LISTEN=127.0.0.1:18443
HG_MICROPROXY_UPSTREAM=127.0.0.1:443
```

The helper writes runtime state under `logs/` by default:

- `logs/microproxy.pid`
- `logs/microproxy.log`

`stop` only stops the process recorded in the microproxy pid file. It does not
call `./hg.sh stop`, does not stop the Python proxy, and does not touch live
iptables, certificates, dashboard state, or routing.

## Prototype Location

Set `HG_MICROPROXY_DIR` to point at a prototype checkout:

```bash
HG_MICROPROXY_DIR=/path/to/microproxy ./hg.sh microproxy status
```

If `HG_MICROPROXY_DIR` is unset, the helper checks these repository-relative
paths:

- `src/microproxy/`
- `microproxy/`
- `prototypes/microproxy/`
- `tools/microproxy/`

## Supported Build Markers

The helper detects a build command from one of these files:

- `Cargo.toml`: `cargo build --manifest-path ...`
- `Makefile` or `makefile`: `make -C ... build` when a `build` target exists,
  otherwise `make -C ...`
- `go.mod`: `go build ./...`
- `package.json`: `npm run build`

For Rust release builds, set `HG_MICROPROXY_RELEASE=1`.

## Runtime Configuration

Set these variables to control the prototype runtime without changing live
HIGH-GRAVITY behavior:

- `HG_MICROPROXY_BIN=/path/to/binary`: explicit executable to run.
- `HG_MICROPROXY_LISTEN=HOST:PORT`: listen endpoint, default
  `127.0.0.1:18443`.
- `HG_MICROPROXY_UPSTREAM=HOST:PORT`: upstream endpoint, default
  `127.0.0.1:443`.
- `HG_MICROPROXY_PID_FILE=/path/to/pid`: pid file path, default
  `logs/microproxy.pid`.
- `HG_MICROPROXY_LOG_FILE=/path/to/log`: log path, default
  `logs/microproxy.log`.
- `HG_MICROPROXY_SMOKE_DIR=/path/to/dir`: smoke run output directory, default
  `logs/microproxy-smoke.*`.
- `HG_MICROPROXY_SMOKE_LISTEN=HOST:PORT`: smoke relay listen endpoint, default
  auto-selected `127.0.0.1` high port.
- `HG_MICROPROXY_SMOKE_UPSTREAM=HOST:PORT`: smoke fixture upstream endpoint,
  default auto-selected `127.0.0.1` high port.
- `HG_MICROPROXY_SMOKE_EVENT_LOG=/path/to/events.jsonl`: smoke event log path,
  default `$HG_MICROPROXY_SMOKE_DIR/events.jsonl`.
- `HG_MICROPROXY_SMOKE_LOG=/path/to/log`: smoke relay process log, default
  `$HG_MICROPROXY_SMOKE_DIR/hg-edge.log`.

The helper refuses privileged listen ports and the live Python proxy listen
port by default. Set `HG_MICROPROXY_FORCE_LIVE_PORTS=1` only for deliberate
local experiments where using those ports is understood and intended.

The smoke command applies the same live-port guard to both its listen and
upstream endpoints, and also refuses non-local smoke hosts. It will not use
ports 443 or 9998 unless those endpoints are explicitly configured and
`HG_MICROPROXY_FORCE_LIVE_PORTS=1` is set.

## Passive Event Summaries

The Python-side consumer for append-only microproxy event files is
`tools/read_microproxy_events.py`. It is read-only and does not start, stop, or
route traffic:

```bash
python3 tools/read_microproxy_events.py --json logs/microproxy-events.jsonl
python3 tools/read_microproxy_events.py --skip-invalid --missing-ok --json logs/microproxy-events.jsonl
```

Use `--skip-invalid` for tailing files that may contain partially written or
legacy rows. Use `--missing-ok` when a polling control plane should treat an
event file that has not been created yet as an empty stream.

The JSON output is the intended future dashboard/control-plane contract:

- `reader`: source path, source existence, valid row count, skipped invalid row
  count.
- `events`: per-event counts for schema rows.
- `requests`: distinct request counts across `request_seen`, route selection,
  stream start/finish, and upstream error buckets.
- `routes`: route counts, route classification counts, and latest route
  metadata keyed by request id.
- `streams`: `stream_started`/`stream_finished` lifecycle counts, open streams,
  status-code counts, and per-stream details.
- `upstream_errors`: `upstream_error` totals by upstream, error type, and
  request id.

Dashboards can poll this JSON periodically or a control-plane service can wrap
the helper API in `src/microproxy/events.py`. Any promotion from passive event
summaries into live health gates, alerting, dashboard widgets, or runtime
decisions should be a separate opt-in change.

## Traffic Safety

These commands intentionally do not modify `./hg.sh start`, `./hg.sh stop`,
`scripts/internal/hg_start.sh`, `scripts/internal/hg_stop.sh`, or the Python
proxy. Promoting a microproxy prototype into live routing should be handled as
a separate change with explicit opt-in configuration.
