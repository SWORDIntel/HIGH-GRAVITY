# Microproxy Event Stream

The microproxy passive observer writes append-only JSONL events. Each line is one
complete JSON object. Producers must never rewrite prior rows; consumers should
tail the file and tolerate future additive fields.

This document defines schema version `1`, implemented by
`src/microproxy/events.py`.

## Ownership Boundary

The next C microproxy phase keeps a narrow runtime contract:

- C owns transport: socket accept/connect/relay behavior, byte-for-byte
  forwarding, stream lifecycle events, upstream connection failure telemetry,
  and bounded plaintext request classification.
- C may emit advisory fast-path telemetry such as `hot_path_candidate`, but it
  must not mutate request or response payloads.
- Python owns intelligence: model/provider policy, prompt and response
  inspection, Khoj context extraction/injection, request/response mutation, and
  any semantic decision that requires payload understanding.

In event terms, current `hg-edge` producers are expected to emit transport and
classification rows (`stream_started`, `request_seen`, `route_selected`,
`hot_path_candidate`, `stream_finished`, `upstream_error`). Mutation rows such
as `mutation_applied` and `khoj_injected` are reserved for Python-side
intelligence/mutation components unless a future design explicitly moves that
responsibility.

## Envelope

Every event has these top-level fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `schema_version` | integer | yes | Current value is `1`. |
| `event` | string | yes | One of the event names below. |
| `ts` | string | yes | UTC RFC 3339 timestamp, for example `2026-05-11T10:00:00.000Z`. |
| `request_id` | string | yes | Stable id shared by events for one proxied request. |
| `details` | object | yes | Event-specific payload. |
| `sequence` | integer | no | Monotonic producer-local sequence number. |
| `connection_id` | string | no | Connection/session id when available. |
| `stream_id` | string | no | Stream id when useful for indexing. |
| `trace_id` | string | no | Cross-service trace id when available. |
| `service` | string | no | Logical producer name, for example `microproxy`. |

Additional top-level or `details` fields are allowed if they are JSON
serializable. Required fields for an existing event name must not be removed or
renamed.

## Event Names

The supported event names are:

| Event | Required `details` fields | Purpose |
| --- | --- | --- |
| `request_seen` | `method`, `path` | The observer saw an inbound request. Plaintext HTTP producers should add `host` and `classification` when available. |
| `route_selected` | `route` | A routing decision was selected or observed. Plaintext HTTP producers should add `method`, `path`, `host`, and `classification` when available. |
| `stream_started` | `stream_id` | A response or upstream stream began. |
| `stream_finished` | `stream_id`, `status_code` | A stream completed. |
| `hot_path_candidate` | `candidate`, `route` | The relay observed a request shape eligible for a future C fast path. This is advisory only and must not imply payload mutation. |
| `proto_observed` | `proto` | The observer identified a protocol or content framing. |
| `mutation_applied` | `mutation` | A Python-side request or response mutation was applied. C relay producers must not emit this for passive transport events. |
| `khoj_injected` | `injection_id` | Python-side Khoj context was injected into a request. C relay producers must not emit this for passive transport events. |
| `upstream_error` | `upstream`, `error_type`, `message` | An upstream call failed. |

## Example Rows

```json
{"details":{"classification":"chat_completion","content_length":0,"content_type":"application/json","host":"api.openai.com","method":"POST","path":"/v1/chat/completions","reason":"chat_completion_endpoint"},"event":"request_seen","request_id":"req-1","schema_version":1,"ts":"2026-05-11T10:00:00.000Z"}
{"details":{"classification":"chat_completion","content_length":0,"content_type":"application/json","host":"api.openai.com","method":"POST","path":"/v1/chat/completions","reason":"chat_completion_endpoint","route":"passthrough"},"event":"route_selected","request_id":"req-1","schema_version":1,"ts":"2026-05-11T10:00:00.010Z"}
{"details":{"proto":"grpc"},"event":"proto_observed","request_id":"req-1","schema_version":1,"ts":"2026-05-11T10:00:00.020Z"}
{"details":{"stream_id":"stream-1","status_code":200},"event":"stream_finished","request_id":"req-1","schema_version":1,"ts":"2026-05-11T10:00:01.000Z"}
```

## Helper API

`src/microproxy/events.py` exposes:

- `make_event(...)`: build and validate an event envelope.
- `validate_event(event)`: validate schema version, event name, envelope fields,
  event-specific required `details`, and JSON serializability.
- `event_to_jsonl(event)` / `event_from_jsonl(line)`: serialize and parse one
  JSONL row.
- `append_event(path, event)`: append a validated row to a JSONL file.
- `iter_events(path_or_stream, skip_invalid=False)`: yield validated rows from
  a file or stream. Tailers can set `skip_invalid=True` to keep reading past
  malformed rows.
- `read_events(path_or_stream, skip_invalid=False)`: return validated rows plus
  an `invalid_rows` count for control-plane readers that need explicit skip
  accounting.
- `summarize_events(events)`: count validated events by event name.
- `summarize_requests(events)`: count distinct request ids observed overall and
  in `request_seen`, `route_selected`, `stream_started`, `stream_finished`, and
  `upstream_error` events.
- `summarize_routes(events)`: count `route_selected` events by route and by
  optional `details.classification` or `details.route_class`. If neither field
  is present, the route name is used as the classification.
- `summarize_stream_lifecycle(events)`: summarize `stream_started` and
  `stream_finished` rows, including open streams, status code counts, streams
  that finished without a prior start event, and duration in milliseconds when
  timestamps are parseable.
- `summarize_upstream_errors(events)`: count `upstream_error` rows by upstream,
  error type, and request id.
- `summarize_observer_events(events)`: combine event, request, route, stream
  lifecycle, and upstream error summaries from one validated event iterable.

These helpers are passive schema support only. They do not alter live proxy
routing, service startup, dashboard display, or Khoj extraction.

## Passive Connect/protobuf Helper

`src/microproxy/proto_observer.py` contains fixture-tested Python helpers for a
future observer sidecar. The module is intentionally offline-only: it accepts
byte copies from a caller, returns parsed metadata or an event dictionary, and
does not connect to sockets, write event files, mutate payloads, or wire into
`hg-edge`.

The helper API exposes:

- `parse_connect_frames(body, max_frame_bytes=...)`: parse complete Connect
  envelope frames. A Connect frame is a one-byte flag followed by a four-byte
  big-endian payload length. Incomplete trailing data is ignored for bounded
  snapshots, and oversized declared lengths raise before allocation.
- `gzip_decompress_copy(payload, max_output_bytes=...)`: decompress a gzip
  payload into a bounded copy. This is used only when the Connect compressed
  flag (`0x01`) is present.
- `extract_length_delimited_utf8_strings(protobuf_bytes, ...)`: walk protobuf
  wire data and return useful wire type `2` UTF-8 strings, deduplicated and
  capped.
- `observe_connect_proto(body, request_id=..., ...)`: build a validated
  `proto_observed` event with `details.proto = "connect+proto"`,
  Connect frame counts, gzip frame counts, frame flags/lengths, and extracted
  strings when present.

Example:

```python
from microproxy.proto_observer import observe_connect_proto

event = observe_connect_proto(
    body_copy,
    request_id="req-1",
    content_type="application/connect+proto",
    direction="request",
)
```

## hg-edge Relay Sniffing

The `hg-edge` relay appends events to `--event-log PATH`, or to
`HG_EDGE_EVENT_LOG` / `logs/microproxy_events.jsonl` when no path is provided.
It forwards all bytes unchanged.

For plaintext HTTP prototype traffic, `hg-edge` sniffs only the first ready
client-to-upstream buffer. When that buffer contains a complete HTTP request
line, it emits `request_seen` and `route_selected` with method, path, Host, and
one of these classifications: `model_list`, `auth`, `control`,
`chat_completion`, `large_edit`, `opaque_proto`, or `unknown`. The sniff is
bounded to the relay read buffer and does not wait for additional bytes.

Classification is intentionally shallow. It exists to make C relay telemetry
actionable and to identify safe future fast-path candidates; it is not model
policy, prompt understanding, provider failover selection, or mutation logic.
Those behaviors remain Python responsibilities.

For TLS and other opaque traffic, `hg-edge` does not parse protocol payloads and
emits only `stream_started` and `stream_finished` rows.

When `--hot-path-observe` is explicitly enabled, plaintext HTTP sniffing also
emits `hot_path_candidate` for Windsurf `POST
/exa.api_server_pb.ApiServerService/GetChatMessage` requests to
`proxy.windsurf.com`, for other recognized chat-completion endpoints, and for
large mutating request shapes. This marks stream shapes intended for later C
relay fast paths while keeping the prototype disabled by default and
byte-for-byte passthrough.

`--direct-upstream HOST:PORT --direct-hot-path` enables the first opt-in C fast
path. The relay peeks at the first plaintext client buffer before connecting
upstream; when the request is a hot-path candidate or `large_edit`, it connects
to the direct endpoint and emits `route_selected.details.route` as
`direct_upstream`. Otherwise it connects to the normal `--upstream` Python path.
If the direct endpoint connect fails, the relay emits `upstream_error` for that
direct attempt and falls back to the normal Python upstream with
`route_selected.details.route` as `python_fallback`. This does not decrypt TLS,
mutate payloads, or select providers. Live TLS traffic remains opaque unless a
future TLS-aware mode is added.

`upstream_error` is the C relay's failover telemetry boundary. It reports
transport failures such as upstream connect errors so Python/dashboard
consumers can observe them. It does not mean C selected an alternate provider or
rewrote a request; provider failover policy remains Python-owned.

The status summary also computes direct fast-path usage from route telemetry.
That usage block reports how many requests were sent to `direct_upstream`,
how many fell back to the Python path, and how many stayed on the normal
passthrough route.

## Read-Only Summary Tool

`tools/read_microproxy_events.py` reads an append-only JSONL event file and
prints a concise observer summary:

```bash
python3 tools/read_microproxy_events.py path/to/events.jsonl
python3 tools/read_microproxy_events.py --json path/to/events.jsonl
python3 tools/read_microproxy_events.py --skip-invalid --missing-ok --json logs/microproxy-events.jsonl
```

By default, malformed rows fail fast with a validation error that includes the
line number from `iter_events`. Use `--skip-invalid` for tailing partially
written or mixed files where the reader should ignore malformed rows and report
the skipped count in `reader.invalid_rows`. Use `--missing-ok` when a dashboard
or control-plane poller should treat an event file that has not been created yet
as an empty stream.

The JSON shape is intentionally stable for later dashboard/control-plane
consumers:

- `reader`: source path, whether the file existed, valid row count, and skipped
  invalid row count.
- `events`: counts for every schema event name.
- `requests`: distinct request-id counts overall and by key lifecycle buckets.
- `routes`: route totals, route classifications, and latest route metadata per
  request id.
- `streams`: start/finish/open counts, status-code counts, and per-stream
  lifecycle details.
- `upstream_errors`: totals by upstream, error type, and request id.

The text output contains the same high-level counts for terminals. The tool is
file-based and read-only; it does not connect to the proxy or mutate runtime
state.

## Python Control-Plane Status Endpoint

The Python proxy exposes a read-only status endpoint for control-plane callers:

```bash
curl http://127.0.0.1:9998/hg/microproxy/status
```

The endpoint reads `logs/microproxy_events.jsonl` by default using the helpers
in `src/microproxy/events.py`. Set `HG_MICROPROXY_EVENTS_FILE` or
`HG_EDGE_EVENT_LOG` before starting the Python proxy to point it at a different
event file. A missing event file is treated as an empty stream, not an error.

The JSON response includes:

- `reader`: source path, `source_exists`, valid row count, skipped invalid row
  count, and any read error.
- `events`: counts for each schema event name.
- `routes`: route totals, classifications, and latest route metadata per
  request id.
- `streams`: stream start, finish, open, status-code, and lifecycle details.
- `upstream_errors`: totals by upstream, error type, and request id.
- `prototype.pid`: configured pid-file path, pid-file existence, pid value,
  whether that pid is running, and whether the pid file appears stale.
- `prototype.front_pid` / `front`: the configured C front pid file, whether
  `HG_MICROPROXY_FRONT` is enabled, whether the front process is running, the
  intended listen/upstream endpoints, and a compact mode such as
  `python_tls_direct`, `c_front_active`, `c_front_failed`, or
  `c_front_disabled_but_running`.
- `direct_fast_path`: the configured direct target, whether the fast path is
  configured, active, or cooled down, the reported health state, direct usage
  counters, and optional canary counters when the C edge reports them.
- `live_traffic`: explicit flags showing whether the Python TLS path is direct,
  whether the C front relay is configured, whether it is actually running, and
  the failure reason when C-front mode is enabled but the relay is down. The
  direct-path fields also mirror the target, configured/active/cooled-down
  state, health state, usage counters, and fallback count for quick operator
  scanning.

The pid file defaults to `logs/microproxy.pid` and can be overridden with
`HG_MICROPROXY_PID_FILE` before starting the Python proxy. The C-front pid file
defaults to `logs/microproxy_front.pid` and can be overridden with
`HG_MICROPROXY_FRONT_PID_FILE`. This endpoint only reads files and probes the pid
with `kill(pid, 0)`. It does not build, start, stop, route, or mutate
microproxy traffic.

The direct-mode terminal status helper prints the same direct-path block in a
compact form, including the direct target, state, health, fallback count, and
any optional canary counters.
