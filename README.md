# HIGHGRAVITY

HIGHGRAVITY is a small operator repo built around two workflows:

- Windsurf/Cascade integration through repo-local hooks and a launcher
- Gemini-key-driven Veo video generation utilities

The repo is structured so the root explains the system, while the detailed guides live under `docs/`.

## How It Works

### Windsurf flow

The Windsurf path is driven by three pieces:

1. [.windsurf/hooks.json](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/.windsurf/hooks.json) registers workspace hooks for Cascade.
2. [.windsurf/cascade_highgravity_hook.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/.windsurf/cascade_highgravity_hook.py) reads native hook JSON from `stdin`, merges environment defaults, and forwards normalized input to the launcher.
3. [scripts/gemini_session_launcher.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/gemini_session_launcher.py) resolves keys and options, generates a Windsurf profile, and can optionally launch Windsurf with that profile.

Operationally, the flow is:

1. Windsurf fires a Cascade hook such as `post_run_command`.
2. The hook bridge receives the Windsurf payload on `stdin`.
3. The bridge fills in any missing values from env vars like `WINDSURF_API_KEY` or `HIGHGRAVITY_PROXY_URL`.
4. The launcher normalizes those values with this precedence:
   `CLI > stdin > environment > defaults`
5. The launcher writes a profile into `windsurf_profiles/<profile>/`:
   `profile.env`, `profile.json`, and `launch_windsurf.sh`

This means the repo works both from interactive CLI use and directly from Windsurf/Cascade without extra wrapper glue.

### Veo flow

The Veo side is simpler:

1. [scripts/veo3_video_generator.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/veo3_video_generator.py) loads Gemini keys, rotates through them, submits Veo jobs, monitors progress, and downloads results.
2. [scripts/check_video_status.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/check_video_status.py) checks long-running operation status.
3. [scripts/test_veo3.sh](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/test_veo3.sh) is a smoke-test entry point.

Generated files land in `veo3_outputs/`, which is intentionally ignored by git.

## Repo Layout

- [.windsurf/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/.windsurf)
  Windsurf/Cascade workspace integration
- [scripts/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts)
  Runtime scripts and entry points
- [tests/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/tests)
  Automated verification
- [docs/guides/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/docs/guides)
  Usage documentation
- [docs/analysis/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/docs/analysis)
  Longer analysis/reference docs
- [config/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/config)
  Config templates and current key file
- [examples/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/examples)
  Sample prompts and example content

## Keys And Config

The scripts look for Gemini keys in this order:

1. `config/gemini_keys.json`
2. `gemini_keys.json`

Template:

- [config/gemini_keys.example.json](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/config/gemini_keys.example.json)

Current repo state also includes:

- [config/gemini_keys.json](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/config/gemini_keys.json)

If no usable key file is present and you run the launcher interactively, it will prompt you to create one.

## Windsurf Quick Start

Export the defaults you want Windsurf to inherit before opening this repo:

```bash
export WINDSURF_API_KEY='AIzaSy...'
export HIGHGRAVITY_MODE='windsurf'
export HIGHGRAVITY_PROVIDER='proxy'
export HIGHGRAVITY_PROXY_URL='http://localhost:9999'
export HIGHGRAVITY_DRY_RUN='true'
```

Then:

1. Open this repo in Windsurf.
2. Trigger a Cascade action.
3. Confirm `windsurf_profiles/<profile>/` was created.
4. Once the generated profile looks right, switch `HIGHGRAVITY_DRY_RUN` to `false`.

Manual launcher test:

```bash
python3 scripts/gemini_session_launcher.py \
  --api-key "$WINDSURF_API_KEY" \
  --mode windsurf \
  --provider proxy \
  --proxy-url "$HIGHGRAVITY_PROXY_URL" \
  --window-name manual-test \
  --dry-run
```

## Supported Windsurf And Cascade Variables

Any of these can provide the key:

- `WINDSURF_API_KEY`
- `HIGHGRAVITY_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `HIGHGRAVITY_KEY_INDEX`

The launcher and hook bridge understand:

| Variable | Purpose |
|----------|---------|
| `WINDSURF_API_KEY` | Preferred Windsurf-specific API key alias |
| `HIGHGRAVITY_API_KEY` | Generic HIGHGRAVITY key alias |
| `GEMINI_API_KEY` | Gemini key alias |
| `GOOGLE_API_KEY` | Google key alias |
| `OPENAI_API_KEY` | OpenAI-compatible key alias |
| `HIGHGRAVITY_KEY_INDEX` | Use a key by index from the key file |
| `HIGHGRAVITY_MODE` | Launch mode, usually `windsurf` |
| `HIGHGRAVITY_PROVIDER` | Provider mode, usually `proxy` or `direct` |
| `HIGHGRAVITY_PROXY_URL` | Proxy endpoint for generated profiles |
| `OPENAI_BASE_URL` | Alias for proxy endpoint |
| `OPENAI_API_BASE` | Alias for proxy endpoint |
| `HIGHGRAVITY_MODEL` | Model label written into generated profiles |
| `HIGHGRAVITY_WINDOW_NAME` | Explicit window/profile name |
| `HIGHGRAVITY_MONITOR` | Monitoring duration in seconds |
| `HIGHGRAVITY_CHECK` | Check key validity only |
| `HIGHGRAVITY_DRY_RUN` | Generate artifacts without launching Windsurf |
| `HIGHGRAVITY_NEW_WINDOW` | Control whether `--new-window` is passed |
| `WINDSURF_BIN` | Override the Windsurf executable |
| `WINDSURF_BINARY` | Alias for Windsurf executable path |
| `CASCADE_API_KEY` | Cascade-prefixed API key alias |
| `CASCADE_KEY_INDEX` | Cascade-prefixed key index |
| `CASCADE_MODE` | Cascade-prefixed mode |
| `CASCADE_PROVIDER` | Cascade-prefixed provider |
| `CASCADE_PROXY_URL` | Cascade-prefixed proxy URL |
| `CASCADE_MODEL` | Cascade-prefixed model |
| `CASCADE_WINDOW_NAME` | Cascade-prefixed profile/window name |
| `CASCADE_MONITOR` | Cascade-prefixed monitor duration |
| `CASCADE_CHECK` | Cascade-prefixed check flag |
| `CASCADE_DRY_RUN` | Cascade-prefixed dry-run flag |
| `CASCADE_NEW_WINDOW` | Cascade-prefixed new-window flag |

## Veo Quick Start

Single prompt:

```bash
python3 scripts/veo3_video_generator.py \
  --prompt "A cat playing piano in a jazz club"
```

Batch prompts:

```bash
python3 scripts/veo3_video_generator.py \
  --prompts-file examples/example_prompts.txt
```

Smoke test:

```bash
bash scripts/test_veo3.sh
```

## Main Entry Points

- [scripts/gemini_session_launcher.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/gemini_session_launcher.py)
- [scripts/veo3_video_generator.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/veo3_video_generator.py)
- [scripts/check_video_status.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/check_video_status.py)
- [scripts/test_all_keys.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/test_all_keys.py)

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

- [docs/guides/WINDSURF_INTEGRATION.md](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/docs/guides/WINDSURF_INTEGRATION.md)
- [docs/guides/VEO3_README.md](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/docs/guides/VEO3_README.md)

## Notes

- `veo3_outputs/`, `windsurf_profiles/`, and `key_test_results.json` are generated at runtime.
- The launcher masks keys in terminal output, but generated profile files still contain live secrets.
- This repo now contains the current `config/gemini_keys.json` because you asked for it to be committed and published.
