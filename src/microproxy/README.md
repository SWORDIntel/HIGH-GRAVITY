# hg-edge microproxy prototype

`hg-edge` is the first edge prototype for the planned HIGH-GRAVITY microproxy
split:

```text
Windsurf -> hg-edge -> Python proxy
```

The default path is still deliberately non-invasive. Without `--relay`, it does
not listen on a socket, forward traffic, inspect TLS, or replace the existing
Python proxy. It can validate edge configuration and print the intended flow so
the C binary remains safe to build and run during development.

An explicit `--relay` mode is available for localhost-only prototype testing. It
listens on a caller-provided non-live address and forwards raw TCP bytes to a
caller-provided upstream. There is no TLS parsing yet.

## Ownership boundary

The C microproxy owns the transport edge: accepting connections, connecting to
the configured upstream, forwarding bytes unchanged, classifying bounded
plaintext request metadata, and reporting stream/failover telemetry. It may
identify advisory hot-path candidates, but it does not apply intelligence or
payload mutation.

The Python proxy remains the intelligence and mutation layer. Provider/model
policy, prompt and response understanding, Khoj injection, request/response
rewrites, and semantic failover decisions stay in Python.

## Build

```sh
make -C src/microproxy
```

The binary is written to `src/microproxy/build/hg-edge`.

## Validate

```sh
src/microproxy/build/hg-edge --check-config \
  --listen 127.0.0.1:18080 \
  --upstream 127.0.0.1:8000
```

Expected behavior:

- exits `0` when both endpoints are valid `host:port` pairs
- prints the passive flow summary
- exits non-zero for invalid ports or malformed endpoint strings
- opens no sockets unless `--relay` is also provided

## Relay prototype

Relay mode must be requested explicitly and must include both endpoints:

```sh
src/microproxy/build/hg-edge --relay \
  --listen 127.0.0.1:18443 \
  --upstream 127.0.0.1:443 \
  --direct-upstream 203.0.113.10:443 \
  --direct-hot-path \
  --idle-timeout 30 \
  --max-stream-seconds 300 \
  --event-log logs/microproxy_events.jsonl
```

Guardrails:

- `--relay` fails unless `--listen` and `--upstream` are both explicit
- no live listener is implied by defaults, and `hg-edge` never defaults to port
  `443`
- the relay forwards raw TCP bytes only
- plaintext HTTP request bytes in the first client read are bounded-sniffed for
  method, path, Host, and route classification; the bytes are forwarded
  unchanged
- TLS and other opaque traffic emit only stream lifecycle events
- `--hot-path-observe` adds explicit disabled-by-default markers for plaintext
  Windsurf `GetChatMessage` Connect/protobuf and large-edit request shapes that
  are candidates for future C fast paths; it still forwards bytes unchanged
- `--direct-upstream HOST:PORT --direct-hot-path` enables an opt-in prototype
  fast path for plaintext hot-path candidates only; unmatched traffic still
  goes to `--upstream`, and direct connect failure falls back to `--upstream`
- `SIGINT` and `SIGTERM` request a clean shutdown
- idle connections are closed after `--idle-timeout` seconds, defaulting to `30`
- relay streams are closed after `--max-stream-seconds`, defaulting to `300`

Relay mode appends JSONL lifecycle events to `logs/microproxy_events.jsonl` by
default. Override the path with `--event-log PATH` or `HG_EDGE_EVENT_LOG=PATH`.
Events use the schema documented in `docs/microproxy.md`. Current relay event
names are `stream_started`, `request_seen`, `route_selected`,
`hot_path_candidate`, `stream_finished`, and `upstream_error`. Plaintext HTTP
`request_seen` and `route_selected` details include `method`, `path`, `host`,
`content_type`, `content_length`, `classification`, and `reason`.
Classifications are `model_list`, `auth`, `control`, `chat_completion`,
`large_edit`, `opaque_proto`, or `unknown`. `route_selected.details.route`
is normally `passthrough`; when the explicit direct fast path is enabled and a
plaintext hot-path candidate matches, it is `direct_upstream`. These
foundations do not mutate payloads.

`upstream_error` is transport/failover telemetry only. It records failed
upstream connection attempts so Python and dashboard readers can observe the
condition. For explicit direct fast-path attempts, C can fall back to the
configured Python upstream; it does not choose alternate providers or mutate
traffic.

The Python status summary also derives direct fast-path usage counters from the
event stream. That usage block shows direct, fallback, and passthrough counts
so the operator view can tell whether the fast path is actually moving work.
If the C edge starts reporting its own direct-path status block, the Python
summary will also surface the configured target, active versus cooled-down
state, health state, and any canary counters without changing the read-only
contract.

## Current boundary

`hg-edge` has two control-plane surfaces:

- `./hg.sh microproxy ...` remains a disabled-by-default prototype helper for
  local build, run, stop, and smoke checks. It does not switch live traffic.
- `HG_MICROPROXY_FRONT=1 ./hg.sh start` can place `hg-edge` in front of the
  Python TLS proxy as a raw TCP relay. In that mode Python HTTPS listens on the
  internal port and the C front listens on the configured front endpoint.

`./hg.sh status` and `/hg/microproxy/status` report whether C-front mode is
configured, running, failed, or disabled while a stale/listening front remains.
The relay still forwards bytes unchanged and does not alter proxy routing.

`./hg.sh microproxy run` and `./hg.sh microproxy smoke` accept
`HG_MICROPROXY_HOT_PATH_OBSERVE=1` to pass `--hot-path-observe` to `hg-edge`.
The flag enables telemetry markers only; it does not enable C mutation or live
fast-path handling.

`HG_MICROPROXY_DIRECT_UPSTREAM=HOST:PORT HG_MICROPROXY_DIRECT_HOT_PATH=1`
passes the direct upstream flags for prototype runs. The live front launcher
also understands these environment variables, but they are intentionally unset
by default.
