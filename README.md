# HIGHGRAVITY

HIGHGRAVITY contains local tooling for Gemini key management, Windsurf/Cascade integration, and Veo video workflows.

## Repo hygiene

Live keys and generated outputs are intentionally excluded from version control.

- Use [gemini_keys.example.json](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/gemini_keys.example.json) as the template for your local `gemini_keys.json`
- `veo3_outputs/` and `windsurf_profiles/` are generated at runtime

## Windsurf quick start

This repo already includes workspace hooks in [.windsurf/hooks.json](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/.windsurf/hooks.json) and a hook bridge in [.windsurf/cascade_highgravity_hook.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/.windsurf/cascade_highgravity_hook.py).

Set your key and defaults before opening the repo in Windsurf:

```bash
export WINDSURF_API_KEY='AIzaSy...'
export HIGHGRAVITY_MODE='windsurf'
export HIGHGRAVITY_PROVIDER='proxy'
export HIGHGRAVITY_PROXY_URL='http://localhost:9999'
export HIGHGRAVITY_DRY_RUN='true'
```

Then open the repo in Windsurf and trigger Cascade once. The launcher will create a profile under `windsurf_profiles/<profile>/`.

## Supported Windsurf key variables

Any of these can supply the API key:

- `WINDSURF_API_KEY`
- `HIGHGRAVITY_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `HIGHGRAVITY_KEY_INDEX`

Priority is:

1. CLI args
2. `stdin` payload
3. environment variables

## Supported Windsurf and Cascade variables

The Windsurf bridge and launcher understand these variables:

| Variable | Purpose |
|----------|---------|
| `WINDSURF_API_KEY` | Preferred Windsurf-specific API key alias |
| `HIGHGRAVITY_API_KEY` | Generic HIGHGRAVITY key alias |
| `GEMINI_API_KEY` | Gemini key alias |
| `GOOGLE_API_KEY` | Google key alias |
| `OPENAI_API_KEY` | OpenAI-compatible key alias |
| `HIGHGRAVITY_KEY_INDEX` | Use a key from `gemini_keys.json` by index |
| `HIGHGRAVITY_MODE` | Launch mode, typically `windsurf` |
| `HIGHGRAVITY_PROVIDER` | Provider mode, typically `proxy` or `direct` |
| `HIGHGRAVITY_PROXY_URL` | Proxy URL for Windsurf/OpenAI-compatible routing |
| `OPENAI_BASE_URL` | Alias for proxy URL |
| `OPENAI_API_BASE` | Alias for proxy URL |
| `HIGHGRAVITY_MODEL` | Model label recorded in generated profile |
| `HIGHGRAVITY_WINDOW_NAME` | Explicit profile/window name |
| `HIGHGRAVITY_MONITOR` | Monitoring duration in seconds |
| `HIGHGRAVITY_CHECK` | Check key validity only |
| `HIGHGRAVITY_DRY_RUN` | Generate artifacts without launching Windsurf |
| `HIGHGRAVITY_NEW_WINDOW` | Control whether `--new-window` is passed |
| `WINDSURF_BIN` | Override the Windsurf executable |
| `WINDSURF_BINARY` | Alias for Windsurf executable path/name |

Cascade-prefixed aliases are also supported by the launcher for non-interactive use:

- `CASCADE_API_KEY`
- `CASCADE_KEY_INDEX`
- `CASCADE_MODE`
- `CASCADE_PROVIDER`
- `CASCADE_PROXY_URL`
- `CASCADE_MODEL`
- `CASCADE_WINDOW_NAME`
- `CASCADE_MONITOR`
- `CASCADE_CHECK`
- `CASCADE_DRY_RUN`
- `CASCADE_NEW_WINDOW`

## Main files

- [gemini_session_launcher.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/gemini_session_launcher.py)
- [WINDSURF_INTEGRATION.md](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/WINDSURF_INTEGRATION.md)
- [veo3_video_generator.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/veo3_video_generator.py)
- [VEO3_README.md](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/VEO3_README.md)
