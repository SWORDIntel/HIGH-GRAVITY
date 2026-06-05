# HIGH-GRAVITY E2E Audit

## TIS // Tactical Implementation Spec

**SITREP**

* Current State: HIGH-GRAVITY has Python, Bash, and C microproxy components with
  environment-sensitive dependencies.
* Objective: provide a non-destructive audit that inventories dependencies,
  builds/checks the C edge, exercises Antigravity stream tooling, runs focused
  unit tests, and optionally runs full test discovery.
* Threat Assessment: reports can include local paths, command output, and test
  telemetry. They are written under ignored `logs/audit/` and should be handled
  as operational evidence.

**BATTLE PLAN**

```bash
# Focused audit; exits non-zero if required checks fail.
./hg.sh audit

# Full audit; includes unittest discovery and still writes reports if failures occur.
./hg.sh audit --full --no-fail

# Avoid localhost smoke traffic when only dependency inventory is needed.
./hg.sh audit --skip-smoke --no-fail
```

## What It Checks

* Python import availability for `requirements.txt` and the Antigravity wrapper
  requirements.
* Required tools: `bash`, `python3`, `make`, and `cc`.
* Optional operator tools: `curl`, `jq`, `shellcheck`, `pip-audit`, `docker`, Xen
  `xl`, `zfs`, and `aria2c`.
* Python syntax for proxy/dashboard and Antigravity tools.
* Bash syntax for the launch/control scripts.
* `make -C src/microproxy check`.
* `./hg.sh antigravity streams paths` and `summary --json`.
* `./hg.sh microproxy smoke` with localhost fixture traffic.
* Focused root-launcher, XDG-path, rotating-flow-log, C-edge relay, microproxy, and acceleration-fallback unit tests.
* `--full` adds strict `python3 -m unittest discover -s tests`; any full-suite failure now fails the audit instead of being silently treated as informational.
* Static marker scans for `eval`, `exec`, `pickle.load(s)`, unsafe `yaml.load`,
  and C microproxy credential-injection markers.

## Output

Each run writes:

* `logs/audit/hg_e2e_audit_<UTC>.json`
* `logs/audit/hg_e2e_audit_<UTC>.md`

The console prints a compact JSON summary with report paths and failed required
checks.

## Dependency Tiers

The audit intentionally does **not** install packages. Core runtime dependencies
are declared in `requirements.txt`. NumPy and psutil are optional acceleration/
Pegasus dependencies in `requirements-accelerated.txt`; when unavailable, the
proxy uses correctness-preserving stdlib fallbacks and disables ANN/native search
acceleration. Install the accelerated tier when a package mirror is available:

```bash
python3 -m venv .hg_proxy_venv && .hg_proxy_venv/bin/pip install -r requirements.txt -r requirements-accelerated.txt
```

## Contingency

If PyPI is blocked by a proxy, install from a local wheelhouse or Debian package
mirror, then rerun:

```bash
./hg.sh audit --full --no-fail
```
