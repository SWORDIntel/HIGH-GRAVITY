# Windsurf Integration

Windsurf support in this repo is built from:

- [.windsurf/hooks.json](.windsurf/hooks.json)
- [.windsurf/cascade_highgravity_hook.py](.windsurf/cascade_highgravity_hook.py)
- [tools/integration/gemini_session_launcher.py](tools/integration/gemini_session_launcher.py)

## Fastest setup

Export your key and defaults before opening the repo in Windsurf:

```bash
export WINDSURF_API_KEY='AIzaSy...'
export HIGHGRAVITY_MODE='windsurf'
export HIGHGRAVITY_PROVIDER='proxy'
export HIGHGRAVITY_PROXY_URL='http://localhost:9999'
export HIGHGRAVITY_DRY_RUN='true'
```

Then open this repo in Windsurf and trigger Cascade once.

## What happens

1. Windsurf sends hook JSON on `stdin`.
2. [.windsurf/cascade_highgravity_hook.py](.windsurf/cascade_highgravity_hook.py) reads that payload.
3. The bridge merges env defaults such as `WINDSURF_API_KEY` and `HIGHGRAVITY_PROXY_URL`.
4. The bridge forwards normalized JSON into [tools/integration/gemini_session_launcher.py](tools/integration/gemini_session_launcher.py).
5. The launcher writes a profile under `windsurf_profiles/<profile>/`.

The included hooks run on:

- `post_run_command`
- `post_setup_worktree`

## First-run recommendation

Start with:

```bash
export HIGHGRAVITY_DRY_RUN='true'
```

Then confirm these files were created:

- `windsurf_profiles/<profile>/profile.env`
- `windsurf_profiles/<profile>/profile.json`
- `windsurf_profiles/<profile>/launch_windsurf.sh`

When that looks correct:

```bash
export HIGHGRAVITY_DRY_RUN='false'
```

## Direct launcher test

```bash
python3 tools/integration/gemini_session_launcher.py \
  --api-key "$WINDSURF_API_KEY" \
  --mode windsurf \
  --provider proxy \
  --proxy-url "$HIGHGRAVITY_PROXY_URL" \
  --window-name manual-test \
  --dry-run
```

## Key and config files

The launcher checks for keys in this order:

1. `config/gemini_keys.json`
2. `gemini_keys.json`

Use [config/gemini_keys.example.json](config/gemini_keys.example.json) as your template, or update [config/gemini_keys.json](config/gemini_keys.json) directly.

## Example hook payload

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

- Make sure Windsurf opened this repo root.
- Make sure `WINDSURF_API_KEY`, `HIGHGRAVITY_API_KEY`, or `HIGHGRAVITY_KEY_INDEX` is exported in the shell environment Windsurf inherits.
- Start with `HIGHGRAVITY_DRY_RUN='true'`.

If the hook runs but no profile is created:

- Trigger a Cascade action that fires `post_run_command` or `post_setup_worktree`.
- Run the direct launcher test above.

If the profile is created but launch behavior is wrong:

- Inspect `windsurf_profiles/<profile>/profile.json`.
- Check `HIGHGRAVITY_PROVIDER`, `HIGHGRAVITY_PROXY_URL`, and `WINDSURF_BIN`.
