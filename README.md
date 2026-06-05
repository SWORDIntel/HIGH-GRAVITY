# HIGH-GRAVITY

Antigravity-first, observe-only C microproxy and telemetry control plane.

## Quick Start

The root `agy.sh` launcher is the normal operator entrypoint. It manages the
three-account Antigravity wrapper, builds/starts the C microproxy front and
Python TLS observer, and opens a companion live monitor in a tmux pane, terminal
window, or background log when no graphical terminal is available.

```bash
# First-time setup: stage three isolated account profiles and wrapper venv.
./agy.sh bootstrap

# Authenticate the three authorized profiles as documented by the wrapper.
./hg.sh antigravity run --login

# Start proxy/microproxy stack and companion monitor.
./agy.sh launch

# Launch stack, monitor, and run a prompt through account rotation.
./agy.sh run --model standard -- "summarize this repository"

# Resume the last saved command/context.
./agy.sh resume
```

Preview launch actions without touching services:

```bash
./agy.sh plan
```

## Crucial Root Entrypoints

| Path | Purpose |
| --- | --- |
| `agy.sh` | Preferred triple-account Antigravity + microproxy + monitor launcher. |
| `hg.sh` | Full low-level HIGH-GRAVITY control plane. |
| `README.md` | Operator quick start. |
| `AGENTS.md` / `GEMINI.md` | Repository agent guidance. |
| `requirements.txt` | Required Python runtime packages. |
| `requirements-accelerated.txt` | Optional NumPy/psutil acceleration tier. |

Implementation, historical, and detailed operator documentation lives under
`docs/`; runtime output belongs under ignored `logs/` and `data/` paths.

## Launcher Commands

```bash
./agy.sh help
./agy.sh status
./agy.sh monitor
./agy.sh monitor-window
./agy.sh audit --full
./agy.sh stop
```

The monitor refresh interval defaults to two seconds. Override it or disable the
companion window when operating in a Xen domU/headless shell:

```bash
AGY_MONITOR_INTERVAL=5 ./agy.sh launch
AGY_NO_MONITOR_WINDOW=1 ./agy.sh run --model standard -- "task"
```

## Observe-Only Security Defaults

Normal Antigravity launches set traffic mutation, local telemetry ACK, and Khoj
binary injection off. Decrypted JSONL observations contain locally terminated
traffic and must be handled as sensitive evidence. Body samples are redacted by
default in stream exports.

## Documentation

* [Antigravity integration](docs/guides/ANTIGRAVITY_INTEGRATION.md)
* [E2E audit](docs/guides/E2E_AUDIT.md)
* [HMI control plane](docs/guides/HMI_CONTROL_PLANE.md)
* [C microproxy notes](docs/microproxy.md)
* [Procedural HMI directive](docs/reference/PROCEDURAL_HMI_DIRECTIVE.md)

## Verification

```bash
./agy.sh plan
./agy.sh audit --full
python3 -m unittest tests/test_acceleration_fallback.py tests/test_microproxy_events.py tests/test_microproxy_status.py tests/test_usage_command.py
```
