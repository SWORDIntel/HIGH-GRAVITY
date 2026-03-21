# HIGHGRAVITY

HIGHGRAVITY is a repo for Windsurf/Cascade integration, Gemini key-driven tooling, and Veo video workflow scripts.

## Layout

- [.windsurf/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/.windsurf) workspace hook integration
- [scripts/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts) operator scripts and entry points
- [tests/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/tests) automated tests
- [docs/guides/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/docs/guides) usage docs
- [docs/analysis/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/docs/analysis) longer analysis docs
- [config/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/config) config templates
- [examples/](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/examples) sample prompts and example content

## Quick start

1. Update [config/gemini_keys.json](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/config/gemini_keys.json) or replace it from [config/gemini_keys.example.json](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/config/gemini_keys.example.json).
2. The launcher will prompt to add keys if no usable key file is present in interactive mode.
3. For Windsurf, export the vars below before opening the repo.

```bash
export WINDSURF_API_KEY='AIzaSy...'
export HIGHGRAVITY_MODE='windsurf'
export HIGHGRAVITY_PROVIDER='proxy'
export HIGHGRAVITY_PROXY_URL='http://localhost:9999'
export HIGHGRAVITY_DRY_RUN='true'
```

## Main entry points

- [scripts/gemini_session_launcher.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/gemini_session_launcher.py)
- [scripts/veo3_video_generator.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/scripts/veo3_video_generator.py)
- [docs/guides/WINDSURF_INTEGRATION.md](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/docs/guides/WINDSURF_INTEGRATION.md)
- [docs/guides/VEO3_README.md](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/docs/guides/VEO3_README.md)

## Windsurf variables

Any of these can supply the API key:

- `WINDSURF_API_KEY`
- `HIGHGRAVITY_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `HIGHGRAVITY_KEY_INDEX`

Supported Windsurf and Cascade env vars:

| Variable | Purpose |
|----------|---------|
| `WINDSURF_API_KEY` | Preferred Windsurf-specific API key alias |
| `HIGHGRAVITY_API_KEY` | Generic HIGHGRAVITY API key alias |
| `GEMINI_API_KEY` | Gemini key alias |
| `GOOGLE_API_KEY` | Google key alias |
| `OPENAI_API_KEY` | OpenAI-compatible key alias |
| `HIGHGRAVITY_KEY_INDEX` | Use a key from `config/gemini_keys.json` or `gemini_keys.json` by index |
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

## Repo hygiene

Live keys and generated outputs are intentionally excluded from version control.

- Keep active keys in `config/gemini_keys.json` or `gemini_keys.json`
- `veo3_outputs/` and `windsurf_profiles/` are generated at runtime
- `key_test_results.json` is generated output
