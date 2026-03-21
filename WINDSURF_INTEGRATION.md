# Windsurf Integration

This repo already includes the Windsurf hook wiring:

- [.windsurf/hooks.json](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/.windsurf/hooks.json)
- [.windsurf/cascade_highgravity_hook.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/.windsurf/cascade_highgravity_hook.py)
- [gemini_session_launcher.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/gemini_session_launcher.py)

## Fastest setup

From the repo root, export one key source and the proxy defaults before opening Windsurf:

```bash
export WINDSURF_API_KEY='AIzaSy...'
export HIGHGRAVITY_MODE='windsurf'
export HIGHGRAVITY_PROVIDER='proxy'
export HIGHGRAVITY_PROXY_URL='http://localhost:9999'
export HIGHGRAVITY_DRY_RUN='false'
```

Then open this repo in Windsurf. Cascade will automatically run the workspace hooks in [.windsurf/hooks.json](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/.windsurf/hooks.json).

## What the hook does

1. Windsurf sends hook context as JSON on `stdin`.
2. [.windsurf/cascade_highgravity_hook.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/.windsurf/cascade_highgravity_hook.py) reads that JSON.
3. The bridge merges env defaults like `HIGHGRAVITY_API_KEY` and `HIGHGRAVITY_PROXY_URL`.
4. The bridge forwards normalized JSON into [gemini_session_launcher.py](/media/john/593d876a-4036-4255-bd45-33baba503068/DSMILSystem/tools/HIGHGRAVITY/gemini_session_launcher.py).
5. The launcher writes a Windsurf profile under `windsurf_profiles/<profile>/`.

The included hooks run on:

- `post_run_command`
- `post_setup_worktree`

## Recommended first run

Use dry-run first so Windsurf generates the profile without launching another editor instance:

```bash
export HIGHGRAVITY_DRY_RUN='true'
```

After that, trigger Cascade once and confirm these files were created:

- `windsurf_profiles/<profile>/profile.env`
- `windsurf_profiles/<profile>/profile.json`
- `windsurf_profiles/<profile>/launch_windsurf.sh`

If that looks correct, switch back to:

```bash
export HIGHGRAVITY_DRY_RUN='false'
```

## Easiest non-hook test

If you want to test the launcher directly outside Windsurf:

```bash
python3 gemini_session_launcher.py \
  --api-key "$HIGHGRAVITY_API_KEY" \
  --mode windsurf \
  --provider proxy \
  --proxy-url "$HIGHGRAVITY_PROXY_URL" \
  --window-name manual-test \
  --dry-run
```

## Supported inputs

The launcher accepts inputs in this order:

1. CLI args
2. JSON or `KEY=VALUE` data on `stdin`
3. Environment variables

That means Cascade can pass native hook JSON on `stdin`, while you keep secrets and defaults in your shell env instead of hard-coding them in `hooks.json`.

## Useful environment variables

Minimal:

- `WINDSURF_API_KEY`
- `HIGHGRAVITY_API_KEY`
- `HIGHGRAVITY_MODE`
- `HIGHGRAVITY_PROVIDER`
- `HIGHGRAVITY_PROXY_URL`
- `HIGHGRAVITY_DRY_RUN`

Also supported:

- `HIGHGRAVITY_KEY_INDEX`
- `HIGHGRAVITY_MODEL`
- `HIGHGRAVITY_WINDOW_NAME`
- `HIGHGRAVITY_MONITOR`
- `HIGHGRAVITY_CHECK`
- `HIGHGRAVITY_NEW_WINDOW`
- `WINDSURF_BIN`
- `WINDSURF_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_API_BASE`

## Full variable list

| Variable | Purpose |
|----------|---------|
| `WINDSURF_API_KEY` | Preferred Windsurf-specific API key alias |
| `HIGHGRAVITY_API_KEY` | Generic HIGHGRAVITY API key alias |
| `GEMINI_API_KEY` | Gemini key alias |
| `GOOGLE_API_KEY` | Google key alias |
| `OPENAI_API_KEY` | OpenAI-compatible key alias |
| `HIGHGRAVITY_KEY_INDEX` | Use a key from `gemini_keys.json` by index |
| `HIGHGRAVITY_MODE` | Launch mode, usually `windsurf` |
| `HIGHGRAVITY_PROVIDER` | Provider mode, usually `proxy` or `direct` |
| `HIGHGRAVITY_PROXY_URL` | Proxy endpoint for generated Windsurf profiles |
| `OPENAI_BASE_URL` | Alias for proxy endpoint |
| `OPENAI_API_BASE` | Alias for proxy endpoint |
| `HIGHGRAVITY_MODEL` | Model label recorded in the generated profile |
| `HIGHGRAVITY_WINDOW_NAME` | Explicit profile/window name |
| `HIGHGRAVITY_MONITOR` | Monitoring duration in seconds |
| `HIGHGRAVITY_CHECK` | Check key validity only |
| `HIGHGRAVITY_DRY_RUN` | Write profiles without launching Windsurf |
| `HIGHGRAVITY_NEW_WINDOW` | Control whether `--new-window` is passed |
| `WINDSURF_BIN` | Override Windsurf executable |
| `WINDSURF_BINARY` | Alias for Windsurf executable |
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

## Example hook payload

Windsurf hook input looks like JSON on `stdin`. The launcher can consume flat JSON or hook-shaped JSON such as:

```json
{
  "agent_action_name": "post_run_command",
  "trajectory_id": "traj-123",
  "execution_id": "exec-456",
  "tool_info": {
    "command_line": "echo hello",
    "cwd": "/workspace/project",
    "variables": {
      "apiKey": "AIzaSy...",
      "mode": "windsurf",
      "provider": "proxy",
      "proxyUrl": "http://localhost:9999",
      "dryRun": true
    }
  }
}
```

## Troubleshooting

If nothing happens:

- Make sure Windsurf opened this repo, not a different folder.
- Make sure `WINDSURF_API_KEY`, `HIGHGRAVITY_API_KEY`, or `HIGHGRAVITY_KEY_INDEX` is exported in the shell environment Windsurf inherits.
- Start with `HIGHGRAVITY_DRY_RUN='true'` to avoid nested launches while testing.

If the hook runs but no profile is created:

- Trigger a Cascade action that fires `post_run_command` or `post_setup_worktree`.
- Run the direct CLI test above to confirm the launcher works outside Windsurf.

If the profile is created but launch behavior is wrong:

- Inspect `windsurf_profiles/<profile>/profile.json`.
- Check `HIGHGRAVITY_PROVIDER`, `HIGHGRAVITY_PROXY_URL`, and `WINDSURF_BIN`.

## Notes

- The bridge script keeps `hooks.json` simple and avoids brittle inline shell quoting.
- Profile env and metadata files are written with `0600` permissions.
- The launcher masks keys in terminal output, but the generated profile files still contain live secrets, so treat `windsurf_profiles/` as sensitive.
