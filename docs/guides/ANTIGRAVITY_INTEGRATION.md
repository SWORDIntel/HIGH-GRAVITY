# HIGH-GRAVITY Antigravity Integration

HIGH-GRAVITY treats Antigravity CLI (`agy`) as the default client target for
observe-only proxying, C microproxy fronting, account rotation, and traffic
monitoring.

## TIS // Tactical Implementation Spec

**SITREP**

* Current State: Antigravity mode is observe-only by default. Legacy IDE-specific
  launch/mutation behavior is not started in the Antigravity path.
* Objective: connect Antigravity CLI state into HIGH-GRAVITY telemetry, run the
  C microproxy front as the live edge, and log bidirectional traffic that already
  terminates inside the local proxy chain.
* Threat Assessment: full-body decrypted traffic logs can contain secrets. Logs
  are under `logs/` and ignored by git, but they should still be handled as
  sensitive evidence.

**BATTLE PLAN**

* `./agy.sh launch` is the root operator launcher: it starts the managed C-front/
  Python observer stack and opens a live companion monitor in a terminal, tmux
  pane, or background log.
* `./agy.sh run --model <model> -- <prompt>` adds triple-account rotation and
  saved-context handoff to that managed stack.
* `./hg.sh start` launches the observe-only stack with the C `hg-edge` front
  (`:443`) relaying to the internal Python TLS observer (`:9443`) when certs are
  present.
* `./hg.sh antigravity bootstrap` installs/stages the `agy-rotate.py` venv and
  account config.
* `./hg.sh antigravity status` shows account/cooldown state and reads the proxy
  `/hg/antigravity/status` endpoint when the proxy is online.
* `./hg.sh antigravity run --model <model> -- <prompt>` runs through the
  three-account wrapper.
* `./hg.sh antigravity resume` replays the last saved command from the saved
  cwd/model.
* `./hg.sh antigravity monitor` summarizes Antigravity wrapper state, decrypted
  flow JSONL, and C microproxy event JSONL.
* `./hg.sh antigravity streams tail` tails redacted decrypted flow rows; add
  `--include-body` only when you explicitly need captured body samples.
* `./hg.sh antigravity logs` tails proxy, decrypted-flow, C microproxy, and
  per-session logs.

## Observe-Only Defaults

The default runtime environment is:

```bash
export HG_CLIENT_TARGET=antigravity
export HG_TRAFFIC_MUTATION_ENABLED=0
export HG_KHOJ_BINARY_INJECT=0
export HG_LOCAL_ACK_TELEMETRY=0
export HG_DECRYPTED_TRAFFIC_LOG=1
export HG_DECRYPTED_TRAFFIC_FULL_BODY=1
export HG_DECRYPTED_TRAFFIC_LOG_FILE=logs/traffic_flows.jsonl
export HG_DECRYPTED_TRAFFIC_LOG_MAX_BYTES=104857600
export HG_DECRYPTED_TRAFFIC_LOG_BACKUP_COUNT=5
export HG_DECRYPTED_TRAFFIC_QUEUE_SIZE=256
export HG_EDGE_EVENT_LOG=logs/microproxy_events.jsonl
```

Decrypted-flow body inspection, encoding, and JSONL writes run on a bounded
background queue instead of the proxy event loop. The active log rotates at 100
MiB with five retained backups by default. When the queue is full, observations
are dropped rather than delaying concurrent requests; writer queue/drop/failure
metrics are exposed by the telemetry endpoints.

With these defaults, HIGH-GRAVITY does **not**:

* inject prompts, mission profiles, compliance reminders, Khoj context, or binary
  RAG context;
* fabricate plan/model/usage state;
* patch protobuf model configs or user status;
* rewrite rate-limit headers;
* locally ACK telemetry/control-plane requests;
* mutate request or response bodies.

## C Microproxy Series

The live edge is a C microproxy stage (`src/microproxy/hg_edge.c`) managed by
`scripts/internal/hg_start.sh`. It emits JSONL route/stream events to
`logs/microproxy_events.jsonl` and forwards raw TCP bytes to the internal Python
TLS observer. The C edge compiles without the old private header dependency and
contains no credential/header injection or response-fabrication payloads.

Useful commands:

```bash
./hg.sh proxy start
./hg.sh proxy status
./hg.sh microproxy build
./hg.sh microproxy smoke
./hg.sh antigravity monitor
./hg.sh antigravity streams summary --json
./hg.sh audit --full --no-fail
```

See `docs/guides/E2E_AUDIT.md` for dependency inventory, C microproxy smoke,
static marker scans, and full test-discovery reporting.

## Bidirectional Decrypted Flow Logs

`src/proxy.py` writes JSONL rows after TLS has terminated locally:

* `client_to_proxy` for request bodies;
* `upstream_to_proxy` for buffered responses;
* `upstream_to_proxy_chunk` for streaming response chunks.

Each row includes request id, direction, client target, route mode, sanitized
headers, status, upstream host, body byte count, SHA-256, and a bounded full-body
base64/text/JSON sample when `HG_DECRYPTED_TRAFFIC_FULL_BODY=1`.

## Data Stream Tooling

`tools/antigravity_three_account/ag-streams.py` reads the local data streams
without performing network interception itself:

```bash
./hg.sh antigravity streams paths
./hg.sh antigravity streams summary
./hg.sh antigravity streams tail
./hg.sh antigravity streams export --format csv --output logs/antigravity_flows.csv
```

By default, `tail` and `export` redact captured body samples and keep only byte
counts and SHA-256 hashes. Use `--include-body` only for authorized evidence
capture.

## Monitoring Endpoints

```bash
curl -fsS http://127.0.0.1:9998/hg/telemetry | jq '.antigravity, .decrypted_traffic_log'
curl -fsS http://127.0.0.1:9998/hg/antigravity/status | jq
curl -fsS http://127.0.0.1:9998/hg/microproxy/status | jq
```

## Contingency

If you need legacy lab behavior, do it in a disposable Xen domU and keep
`HG_CLIENT_TARGET` away from `antigravity`. Roll back to pure monitoring with:

```bash
HG_TRAFFIC_MUTATION_ENABLED=0 HG_LOCAL_ACK_TELEMETRY=0 HG_KHOJ_BINARY_INJECT=0 ./hg.sh proxy restart
```
