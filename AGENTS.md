# Repository Guidelines

## Project Structure & Module Organization
HIGH-GRAVITY is a Python and Bash utility suite. Core Python modules live in `src/`, including `proxy.py`, `hg_dashboard.py`, wrappers, and `src/pegasus/`. Shell entrypoints and service controls live in `hg.sh` and `scripts/`; put reusable automation under `scripts/` and menu internals under `scripts/internal/`. Tests live in `tests/`, with ad hoc validation tools in `test_bench/`. Configuration is in `config/`, documentation in `docs/`, examples in `examples/`, and runtime output in `logs/`, `data/`, `kp14_cache/`, and `windsurf_profiles/`. The nested `Ablation/` directory is a separate project with its own guide.

## Build, Test, and Development Commands
- `python3 -m venv .hg_proxy_venv && .hg_proxy_venv/bin/pip install -r requirements.txt`: create the local environment.
- `./hg.sh --help`: list supported management commands.
- `./hg.sh dashboard`: launch the Rich TUI dashboard.
- `./hg.sh doctor`: run diagnostics; some checks require sudo.
- `python -m unittest discover -s tests`: run unit tests based on the current test style.
- `python -m pytest tests`: run the same suite when pytest is available.
- `pre-commit run --all-files`: run configured flake8 checks before submitting changes.

## Coding Style & Naming Conventions
Use Python 3 with 4-space indentation and snake_case for modules, functions, and variables. Keep shell scripts POSIX-aware where practical; Bash is acceptable for existing `hg_*` workflows. Name tests `test_*.py`, keep fixtures local or temporary, and avoid machine-specific paths unless the test is explicitly an integration check. Flake8 is configured in `.pre-commit-config.yaml`.

## Testing Guidelines
Place stable unit tests in `tests/`. Use `unittest` or pytest-compatible assertions, and isolate filesystem state with `tempfile` or `tmp_path`. Tests that require live services, proxies, network state, credentials, or sudo should be marked or kept as smoke scripts.

## Commit & Pull Request Guidelines
Recent history uses concise Conventional Commit prefixes such as `fix:` and `feat:`. Follow that style, for example `fix: handle missing proxy config`. PRs should explain behavior changes, list validation commands, link issues when available, and include screenshots or terminal output for dashboard and CLI UX changes.

## Security & Configuration Tips
Do not commit private keys, real API keys, generated profiles, logs, databases, packet captures, or virtualenvs. Keep sample configuration sanitized, prefer `*.example.json` templates, and review `.gitignore` before adding files under `config/`, `certs/`, or runtime directories.
