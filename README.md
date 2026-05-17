# HIGH-GRAVITY

Windsurf proxy control plane, local intelligence layer, C edge relay, and operator dashboards.

HIGH-GRAVITY sits between Windsurf Next and upstream provider endpoints. The current runtime is designed around a conservative rule: **the proxy stack can be restarted independently, and Windsurf is left alone unless you explicitly choose a full start/stop command**.

## Current Capabilities

- C microproxy front on `:443` forwarding to the Python HTTPS proxy on `:9443`.
- HTTP control/compatibility proxy on `:9998`.
- Proxy-only restart paths that do not stop or launch Windsurf.
- Inference gate modes: `cache-first`, `cache-only`, `confirm`, `block`, and `local-only`.
- Exact and canonical response cache telemetry.
- Local ACK handling for high-frequency telemetry/reporting paths.
- Khoj RAG integration with token injected/saved counters.
- Pegasus swarm trigger/result telemetry.
- Rich TUI dashboard plus procedural HMI dashboard/status path.
- C-edge stream lifecycle, backpressure, and direct-egress visibility.
- GPU/OpenVINO/NCS2 acceleration probes for Khoj.

## Layout

| Path | Purpose |
| --- | --- |
| `hg.sh` | Main CLI entrypoint. |
| `src/proxy.py` | Python proxy, inference gate, usage spoofing, cache, Khoj/Pegasus integration. |
| `src/microproxy/` | C edge relay, event schema, proto observer, tests. |
| `src/hmi/` | Procedural C++/Vulkan HMI telemetry pipeline and runner. |
| `src/pegasus/` | Pegasus swarm and Khoj integration helpers. |
| `scripts/internal/` | Start/stop/status/dashboard/control helper scripts. |
| `tests/` | Unit and integration-style regression tests. |
| `docs/` | Operator and architecture notes. |
| `logs/`, `data/`, `kp14_cache/`, `windsurf_profiles/` | Runtime output. Do not commit generated contents. |

## Install

```bash
git clone https://github.com/SWORDIntel/HIGH-GRAVITY
cd HIGH-GRAVITY
python3 -m venv .hg_proxy_venv
.hg_proxy_venv/bin/pip install -r requirements.txt
```

If the virtualenv is missing, `./hg.sh` will try to bootstrap the core Python dependencies.

## Normal Operation

Start the management menu:

```bash
./hg.sh
```

Start or restart only the proxy stack with the C front enabled:

```bash
./hg.sh restart-proxy-c cache-first
```

This is the preferred live-debug command. It stops/restarts:

- HTTP proxy on `9998`
- Python HTTPS proxy on `9443`
- C microproxy front on `443`
- proxy watchdog

It does **not** stop Windsurf.

## Inference Modes

The upstream inference gate is controlled by `HG_UPSTREAM_INFERENCE_MODE` or the optional mode argument:

```bash
./hg.sh start-proxy-c cache-first
./hg.sh restart-proxy-c cache-only
./hg.sh restart-proxy-c confirm
./hg.sh restart-proxy-c block
./hg.sh restart-proxy-c local-only
```

| Mode | Behavior |
| --- | --- |
| `cache-first` | Default. Replay cache hits locally; forward cache misses upstream. Preserves normal Windsurf capability. |
| `cache-only` | Replay cache hits; block misses locally. Useful for usage-control testing. |
| `confirm` | Block misses with explicit gate telemetry. |
| `block` | Block upstream inference misses. |
| `local-only` | Alias-style local-only behavior for no-upstream testing. |

The menu exposes these under `Start C Proxy Mode` and `Restart C Proxy Mode`.

## Dashboards

Rich TUI:

```bash
./hg.sh dashboard
```

The TUI shows:

- proxy status
- inference mode
- response cache hit/store counts
- upstream gate forward/miss/block counts
- local ACK counts
- Khoj token injected/saved counters
- Pegasus swarm quality
- C edge and routing status
- acceleration status

Hotkeys include:

| Key | Action |
| --- | --- |
| `S` | Start all services. |
| `X` | Stop all services. |
| `P` | Patch. |
| `R` | Repatch. |
| `U` | Unpatch files. |
| `D` | Doctor. |
| `W` | Launch Windsurf wrapper. |
| `H` | HMI dashboard path. |
| `K` | Khoj reindex. |
| `A` | Khoj acceleration probe. |
| `G` | Restart Khoj acceleration stack. |
| `C` | Clear cache. |
| `Y` | Clear control-plane cache. |
| `1` | Restart C proxy in `cache-first`. |
| `2` | Restart C proxy in `cache-only`. |
| `3` | Restart C proxy in `confirm`. |
| `4` | Restart C proxy in `block`. |
| `5` | Restart C proxy in `local-only`. |

Procedural HMI:

```bash
./hg.sh hmi status
./hg.sh hmi check
./hg.sh hmi run
./hg.sh hmi-dashboard
```

Launch Procedural HMI Dashboard with `./hg.sh hmi-dashboard` or the TUI
hotkey. **`H`**: Launch Procedural HMI Dashboard.

The HMI telemetry pipeline consumes the same core counters as the TUI: proxy mode, response cache, upstream gate, local ACK, Khoj, Pegasus, C-edge streams, and acceleration state.

## Status And Usage

Quick status:

```bash
./hg.sh status
```

Status reports:

- HTTP proxy, HTTPS proxy, C front
- current inference mode
- response cache hit/store counts
- upstream gate forwards/misses/blocks
- local ACK count and avoided bytes
- Khoj health and acceleration
- Pegasus activity
- proxy/Khoj watchdogs
- Windsurf routing and direct-egress sockets

Usage snapshot:

```bash
./hg.sh usage -j
```

Watch quota/inference lifecycle:

```bash
./hg.sh watch-quota
```

Throughput baseline:

```bash
./hg.sh throughput
```

Kernel/socket observer:

```bash
./hg.sh ebpf status
./hg.sh ebpf start trace-tcp 3600
./hg.sh ebpf stop
./hg.sh ebpf observe 15
./hg.sh ebpf trace-tcp 10
```

The eBPF path is observational. It does not restart Windsurf, restart the proxy,
alter routing, modify quota/accounting responses, or change iptables. When
`bpftrace` or kernel BTF is missing, `observe` falls back to bounded `ss`
sampling so direct socket behavior can still be compared against proxy
telemetry. The managed observer commands write `logs/ebpf_status.json`,
`logs/ebpf_observer.pid`, and `logs/ebpf_events.jsonl`; they only control that
observer process group.

Offline eBPF event helpers in `src/ebpf_events.py` classify socket destinations
without requiring live kernel probes:

| Route class | Meaning |
| --- | --- |
| `local_proxy` | Loopback traffic to the Python/control proxy, such as `9443` or `9998`. |
| `expected_proxy_front` | Loopback traffic to the expected HTTPS/C-edge front, normally port `443`. |
| `direct_upstream` | Remote TLS egress on port `443`, which bypasses the local proxy path. |
| `unknown` | Missing, malformed, or non-HTTPS remote destinations that cannot be classified. |

Retry storms are summarized as bursts of repeated attempts for the same process
and destination within a bounded window. The default summary uses a 20 second
window and a threshold of 5 attempts; focused tests can override both values.

Two concurrent Windsurf sessions are considered visible only when eBPF rows
preserve at least two distinct session/window identifiers and each required
session has at least one classified route observation. This keeps session-level
diagnostics separate from aggregate direct-egress counts.

## C Edge

The C edge lives in `src/microproxy/` and is built by the proxy start path. It owns hot-path relay behavior:

- TLS relay listener
- request classification events
- stream lifecycle events
- quota/connect-error stream signal observation
- active stream cap and backpressure events
- direct fast-path observation hooks

Build and smoke-test manually:

```bash
./hg.sh microproxy build
./hg.sh microproxy smoke
./hg.sh microproxy status
```

Read event logs:

```bash
python3 tools/read_microproxy_events.py --skip-invalid logs/microproxy_events.jsonl
```

## Khoj And Acceleration

Khoj is used as the local second-brain/RAG layer. It can inject compact context where useful and reports token pressure through proxy telemetry.

Commands:

```bash
./hg.sh khoj status
./hg.sh khoj reindex
./hg.sh khoj accel
./hg.sh hmi status
```

Acceleration probes cover CUDA, OpenVINO, and NCS2/Myriad visibility. See:

- `docs/guides/NCS2_RECOVERY.md`
- `scripts/internal/khoj_accel_status.py`
- `scripts/internal/khoj_ncs2_recover.py`

## Patch And Routing Commands

```bash
./hg.sh patch
./hg.sh repatch
./hg.sh unpatch
./hg.sh egress status
./hg.sh egress on
```

`unpatch` restores binary and JavaScript files to their original state.
**v4.0 Update**: We no longer use brittle `/etc/hosts` overrides. The `./hg.sh egress on` command now utilizes **Dynamic DNS Discovery** (`dig @1.1.1.1`) to resolve live production IPs at runtime, injecting them into the `HG-WINDSURF-EGRESS` iptables chain. This ensures the intercept shield remains perfectly synchronized with upstream load balancer rotations.

## Testing

Core test commands:

```bash
python -m unittest discover -s tests
python -m pytest tests
```

Focused checks used during recent work:

```bash
python3 -m py_compile src/proxy.py src/hg_dashboard.py
bash -n hg.sh scripts/internal/hg_start.sh scripts/internal/hg_status.sh scripts/internal/hg_hmi.sh
make -C src/hmi check
.hg_proxy_venv/bin/python -m pytest -q \
  tests/test_proxy_shared_metrics.py \
  tests/test_microproxy_edge.py \
  tests/test_microproxy_events.py \
  tests/test_hmi_control_plane.py \
  tests/test_usage_command.py
```

## Operational Rules

- Use `./hg.sh restart-proxy-c cache-first` for live proxy changes.
- Do not kill Windsurf when only proxy behavior is being changed.
- Keep generated certificates, logs, captures, databases, virtualenvs, and local profiles out of commits.
- Treat `logs/`, `data/`, `certs/`, `kp14_cache/`, and `windsurf_profiles/` as runtime areas unless a file is explicitly a sanitized template or source artifact.
- When diagnosing two Windsurf sessions, watch C-edge stream and backpressure counters first.

## Troubleshooting

Provider unreachable:

```bash
./hg.sh status
curl -s http://127.0.0.1:9998/hg/telemetry | python3 -m json.tool
python3 tools/read_microproxy_events.py --skip-invalid logs/microproxy_events.jsonl
```

High usage climb:

```bash
./hg.sh usage -j
./hg.sh dashboard
./hg.sh restart-proxy-c cache-first
```

Concurrent sessions slow or unreachable:

```bash
./hg.sh status
./hg.sh microproxy status
./hg.sh ebpf observe 15
python3 tools/read_microproxy_events.py --skip-invalid logs/microproxy_events.jsonl
```

HMI runtime does not launch:

```bash
./hg.sh hmi status
./hg.sh hmi check
```

## Current Default Ports

| Component | Port |
| --- | --- |
| C microproxy front | `443` |
| Python HTTPS proxy | `9443` |
| HTTP/control proxy | `9998` |
| Khoj | `42110` |

## Commit Hygiene

Before pushing:

```bash
git diff --check
python3 -m py_compile src/proxy.py src/hg_dashboard.py
bash -n hg.sh scripts/internal/*.sh
```

Do not commit:

- private keys
- generated cert serials/CSRs
- real API keys
- runtime logs
- packet captures
- local virtualenvs
- generated Windsurf profiles
