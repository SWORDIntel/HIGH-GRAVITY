# Antigravity CLI Three-Account Control Plane

A compliant, local-first setup for installing and operating the official
[google-antigravity/antigravity-cli](https://github.com/google-antigravity/antigravity-cli)
with three separately authorized accounts. The wrapper now defaults to a
permissive autonomous profile (`always-proceed`, non-workspace access, and the
launch override `--dangerously-skip-permissions`) while keeping all state in
local JSON audit files.

> **Compliance gate:** Use this only for accounts, filesystems, and model access
> you are authorized to use. The permissive defaults are intended for trusted
> local engineering sandboxes, not shared machines, CI secrets, or regulated
> environments.

## TIS // Tactical Implementation Spec

**SITREP**

* Current State: Antigravity CLI installs from the official Linux/macOS command:
  `curl -fsSL https://antigravity.google/cli/install.sh | bash`.
* Objective: Maintain three isolated local profiles, automatically rotate when a
  model times out, preserve context, and resume the exact saved command.
* Threat Assessment: Permissive permissions can expose files outside the current
  workspace. Use separate Linux users or Xen domUs if account/keyring isolation
  or blast-radius reduction matters.

**BATTLE PLAN**

* OBJECTIVE: Install Antigravity CLI, bootstrap a Rich Python UI, write
  permissive per-profile settings, and run commands through a stateful wrapper.
* CURRENT_STATE: No credentials are stored in this repository; real account
  metadata lives in `~/.config/high-gravity/antigravity/accounts.json`.
* ACTIONS:
  1. Run `setup.sh` to create config/state/profile directories, bootstrap the
     Python venv, and install the official CLI when missing.
  2. Authenticate each profile with `--login`.
  3. Run commands through `agy-rotate.py`; it writes per-profile Antigravity
     settings under each profile's `.gemini/antigravity-cli/settings.json`.
  4. On timeout, the wrapper marks the account/model on cooldown, writes a
     handoff note, then continues with the next eligible account by default.
  5. Use `--resume` to replay the last saved command from the saved cwd/model.
* VERIFICATION: Use `--status`, `--dry-run`, timeout simulation, and `--resume`.
* CONTINGENCY: If the upstream CLI rejects a launch flag, remove or edit
  `permission_defaults.cli_args` in the user config while keeping the persistent
  JSON permission settings enabled.

## Folder Contents

| File | Purpose |
| --- | --- |
| `setup.sh` | Installs/stages the official CLI setup and calls the venv bootstrapper. |
| `bootstrap-venv.sh` | Creates `.venv` and installs the Rich UI dependency. |
| `requirements.txt` | Python dependencies for the richer wrapper UI. |
| `accounts.example.json` | Sanitized three-account template with permissive workspace defaults. |
| `agy-rotate.py` | Rich Python wrapper for selection, timeout rotation, state, handoff, and resume. |
| `.env.example` | Optional environment overrides. |

## Quick Start

```bash
# From the HIGH-GRAVITY repo root
tools/antigravity_three_account/setup.sh
```

```bash
# Rich status UI
tools/antigravity_three_account/.venv/bin/python tools/antigravity_three_account/agy-rotate.py --status
```

```bash
# Dry-run full command including permission bypass args
tools/antigravity_three_account/.venv/bin/python tools/antigravity_three_account/agy-rotate.py --model ultra-preview --dry-run -- "explain repo layout"
```

```bash
# Live run; rotates on timeout up to max_attempts
tools/antigravity_three_account/.venv/bin/python tools/antigravity_three_account/agy-rotate.py --model ultra-preview -- "summarize README.md"
```

```bash
# Resume the last saved active/completed command with its saved cwd/model
tools/antigravity_three_account/.venv/bin/python tools/antigravity_three_account/agy-rotate.py --resume
```

## Permissive Access Defaults

`accounts.example.json` intentionally defaults to autonomous local execution:

* `permission_defaults.auto_bypass_permissions: true`
* `permission_defaults.allow_non_workspace_access: true`
* `permission_defaults.permission_preset: always-proceed`
* `permission_defaults.sandbox: false`
* `permission_defaults.workspace_roots: ["/"]`
* `permission_defaults.cli_args: ["--dangerously-skip-permissions"]`
* `permission_defaults.allow: ["read_file(*)", "write_file(*)", "command(*)", "read_url(*)"]`

For each account, `agy-rotate.py` writes those values into the account profile's
Antigravity settings path before launching the CLI. This makes non-workspace
access persistent and makes the launch command permissive every time.

## Authenticating Three Accounts

Run login flows one profile at a time:

```bash
AGY_ACCOUNT=account_1 tools/antigravity_three_account/.venv/bin/python tools/antigravity_three_account/agy-rotate.py --login
AGY_ACCOUNT=account_2 tools/antigravity_three_account/.venv/bin/python tools/antigravity_three_account/agy-rotate.py --login
AGY_ACCOUNT=account_3 tools/antigravity_three_account/.venv/bin/python tools/antigravity_three_account/agy-rotate.py --login
```

The wrapper isolates `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, and
`XDG_CACHE_HOME` per account. If your desktop keyring still resolves globally,
use separate Linux users or separate Xen domUs for stronger identity isolation.

## Rich UI, State, and Resume Model

The wrapper creates and maintains:

* `~/.local/state/high-gravity/antigravity/state.json` for current account,
  cooldowns, active run, last command, and run history.
* `~/.local/state/high-gravity/antigravity/sessions/<run-id>.log` for command
  output.
* `~/.local/state/high-gravity/antigravity/handoff.md` for the latest compact
  context transfer note.

Resume behavior:

1. Before each launch, the wrapper records the selected account, model, cwd,
   full command, and user command.
2. After completion or timeout, it updates the run status and preserves
   `last_command`.
3. `--resume` replays the saved user command with the saved model and cwd, then
   re-selects an eligible account based on current cooldown state.

## Environment Overrides

```bash
set -a; source tools/antigravity_three_account/.env.example; set +a
```

Key variables:

* `ANTIGRAVITY_CMD`: binary to execute. Defaults to `agy`.
* `AGY_CONFIG`: account config path.
* `AGY_STATE_DIR`: state/log directory.
* `AGY_VENV`: bootstrap venv location.
* `AGY_ACCOUNT`: force a specific account by name.

## QUALITY METRICS & SUCCESS VALIDATION

* Metric 1: `--status` renders a Rich table or JSON fallback showing all three
  accounts, settings paths, and cooldown state.
* Metric 2: Timeout events write cooldown timestamps and handoff notes, then
  rotate to the next eligible account when `auto_continue_on_timeout` is true.
* Metric 3: `--resume` replays the saved command from the saved cwd/model.
* Success Validation: dry-run output includes `--dangerously-skip-permissions`,
  and state JSON contains `active_run`, `last_command`, and `runs` entries.

## SECURITY & COMPLIANCE GATES

* Lint/Static: `python3 -m py_compile agy-rotate.py`.
* Unsafe patterns avoided: no `eval`, no unsafe deserialization, no plaintext
  passwords/tokens in the repo, no shell interpolation of user prompts.
* Audit hooks: JSON state plus per-session logs under `AGY_STATE_DIR`.
* CVE scan guidance: if you deploy this beyond a local workstation, run
  `pip-audit -r tools/antigravity_three_account/requirements.txt` inside the
  wrapper venv.

## Session Summary

* Install source: official Antigravity CLI install script.
* Permission stance: permissive by default for trusted local sandboxes.
* Rotation behavior: automatic, cooldown-aware, model-aware, and stateful.
* Context continuity: run logs, handoff notes, and exact-command resume.
* Blocker: per-account credential isolation depends on upstream CLI/keyring
  behavior; use separate Linux users/domUs if in doubt.

## HIGH-GRAVITY Proxy/Microproxy Integration

Use the unified CLI when you want the Antigravity wrapper connected to the wider
HIGH-GRAVITY telemetry plane:

```bash
./hg.sh antigravity bootstrap
./hg.sh antigravity status
./hg.sh antigravity run --model ultra-preview -- "summarize this repo"
./hg.sh antigravity resume
./hg.sh antigravity monitor
./hg.sh antigravity streams summary
./hg.sh antigravity logs
```

The proxy defaults to Antigravity observe-only mode: `HG_TRAFFIC_MUTATION_ENABLED=0`,
full decrypted local flow logging enabled, C microproxy event logging enabled,
local telemetry ACK disabled, and request/response mutation disabled. See `docs/guides/ANTIGRAVITY_INTEGRATION.md` for monitoring
endpoints and log handling.
