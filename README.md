# HIGHGRAVITY

HIGHGRAVITY is a small operator repo built around two workflows:

- Windsurf/Cascade integration through repo-local hooks, a launcher, a TUI dashboard, and an optimizing proxy.
- Gemini-key-driven Veo video generation utilities.

The repo is structured so the root explains the system, while the detailed guides live under `docs/`.

## Savings vs normal use

Based on the repo's internal analysis docs, the intended optimization model is:

- Windsurf alone: about 10-15% cost reduction
- HIGHGRAVITY alone: about 40-60% cost reduction
- Combined Windsurf + HIGHGRAVITY path: about 80% cost reduction

Example figures from the analysis:

- Individual developer: `Windsurf alone $36/month`, `HIGHGRAVITY alone $14.40/month`, `Combined $7.20/month`
- Small team pattern: `Windsurf alone $360/month`, `Windsurf + HIGHGRAVITY $72/month`
- Larger team pattern: `Windsurf alone $3,600/month`, `Windsurf + HIGHGRAVITY $720/month`

Those numbers come from:

- [docs/analysis/COMPLETE_ANALYSIS.md](docs/analysis/COMPLETE_ANALYSIS.md)
- [docs/analysis/COMPOUND_OPTIMIZATION.md](docs/analysis/COMPOUND_OPTIMIZATION.md)

They are the repo's modeled estimates, not live billing measurements.

## How It Works

### Windsurf flow & Optimizing Proxy

The Windsurf path is driven by these pieces:

1. [.windsurf/hooks.json](.windsurf/hooks.json) registers workspace hooks for Cascade.
2. [.windsurf/cascade_highgravity_hook.py](.windsurf/cascade_highgravity_hook.py) reads native hook JSON from `stdin`, merges environment defaults, and forwards normalized input to the launcher.
3. [launcher.py](launcher.py) resolves keys and options, optionally starts the `proxy.py` cost-reducing proxy, generates a Windsurf profile, and can optionally launch Windsurf with that profile or a TUI Dashboard.
4. [scripts/proxy.py](scripts/proxy.py) is a local HTTP proxy that intercepts Windsurf's requests to `inference.codeium.com`, injects cost-saving instructions into the user prompt, caches responses, and forwards them.

Operationally, the flow is:

1. The user runs `python launcher.py --dashboard --start-proxy`.
2. The launcher starts the HIGHGRAVITY proxy on `localhost:9999` and displays the TUI dashboard tracking proxy throughput and estimated costs.
3. Windsurf fires a Cascade hook, forwarding payloads to the launcher to setup the profile.
4. Windsurf's API calls are routed through the local proxy, which applies prompt injection to enforce "FULL IMPLEMENTATIONS oNLY" while ignoring other costly system prompt instructions, saving API tokens and providing cached responses when possible.

### Veo flow

The Veo side is simpler:

1. [scripts/veo3_video_generator.py](scripts/veo3_video_generator.py) loads Gemini keys, rotates through them, submits Veo jobs, monitors progress, and downloads results.
2. [scripts/check_video_status.py](scripts/check_video_status.py) checks long-running operation status.
3. [scripts/test_veo3.sh](scripts/test_veo3.sh) is a smoke-test entry point.

Generated files land in `veo3_outputs/`, which is intentionally ignored by git.

## Repo Layout

- `.windsurf/` - Windsurf/Cascade workspace integration
- `scripts/` - Runtime scripts (`launcher.py`, `proxy.py`, `deploy.sh`), and entry points
- `tests/` - Automated verification
- `docs/guides/` - Usage documentation
- `docs/analysis/` - Longer analysis/reference docs
- `config/` - Config templates and current key file
- `examples/` - Sample prompts and example content

## Keys And Config

The scripts look for Gemini keys in this order:

1. `config/gemini_keys.json`
2. `gemini_keys.json`

Template:

- [config/gemini_keys.example.json](config/gemini_keys.example.json)

## Windsurf Quick Start

Export the defaults you want Windsurf to inherit before opening this repo:

```bash
export WINDSURF_API_KEY='AIzaSy...'
export HIGHGRAVITY_MODE='windsurf'
export HIGHGRAVITY_PROVIDER='proxy'
export HIGHGRAVITY_PROXY_URL='http://localhost:9999'
export HIGHGRAVITY_DRY_RUN='true'
```

To run the launcher and TUI Dashboard (auto-starts the proxy):
```bash
python3 launcher.py --dashboard --start-proxy
```

Then:

1. Open this repo in Windsurf.
2. Trigger a Cascade action.
3. Confirm `windsurf_profiles/<profile>/` was created.
4. Once the generated profile looks right, switch `HIGHGRAVITY_DRY_RUN` to `false`.

Manual launcher test:

```bash
python3 launcher.py \
  --api-key "$WINDSURF_API_KEY" \
  --mode windsurf \
  --provider proxy \
  --proxy-url "$HIGHGRAVITY_PROXY_URL" \
  --window-name manual-test \
  --dry-run
```

## Main Entry Points

- [launcher.py](launcher.py)
- [scripts/proxy.py](scripts/proxy.py)
- [scripts/deploy.sh](scripts/deploy.sh)
- [scripts/veo3_video_generator.py](scripts/veo3_video_generator.py)

## Verification

Automated tests currently cover:

- Windsurf profile generation
- Windsurf hook payload normalization
- Hook bridge env/default merging

Run them with:

```bash
python3 -m unittest \
  tests/test_gemini_session_launcher.py \
  tests/test_windsurf_hook_bridge.py
```

## Guides

- [docs/guides/WINDSURF_INTEGRATION.md](docs/guides/WINDSURF_INTEGRATION.md)
- [docs/guides/VEO3_README.md](docs/guides/VEO3_README.md)

