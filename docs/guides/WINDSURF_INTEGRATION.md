# Windsurf Integration

Windsurf support in this repo is built from:

- [.windsurf/hooks.json](.windsurf/hooks.json)
- [.windsurf/cascade_highgravity_hook.py](.windsurf/cascade_highgravity_hook.py)
- [tools/integration/gemini_session_launcher.py](tools/integration/gemini_session_launcher.py)
- [tools/integration/detect_and_wire_windsurf.py](tools/integration/detect_and_wire_windsurf.py)

## Modern Setup (Recommended)

The preferred way to manage Windsurf integration is via the **Unified Dashboard**:

```bash
python3 hg.py
```

1. **Press [W]**: This will automatically detect your running Windsurf session, "wire-in" the necessary hooks, and launch a new optimized instance.
2. **Dynamic Profiles**: The system now searches `windsurf_profiles/` for the most recently updated profile, supporting both named profiles (`high-gravity`) and workspace-specific IDs (`untitled-12345`).

## Automated "Wire-In"

If you are already inside a Windsurf session and want to connect it to the HIGH-GRAVITY proxy:

```bash
python3 tools/integration/detect_and_wire_windsurf.py
```

This script:
1. Detects the `workspace_id` of the running Windsurf Next process.
2. Resolves the local filesystem path for that workspace.
3. Generates a profile environment (`profile.env`).
4. Deploys Cascade hooks into your workspace's `.windsurf/` directory.

## What happens under the hood

1. Windsurf sends hook JSON on `stdin` when you run commands or set up a worktree.
2. [.windsurf/cascade_highgravity_hook.py](.windsurf/cascade_highgravity_hook.py) reads that payload.
3. The bridge merges env defaults such as `WINDSURF_API_KEY` and `HIGHGRAVITY_PROXY_URL`.
4. The bridge forwards normalized JSON into [tools/integration/gemini_session_launcher.py](tools/integration/gemini_session_launcher.py).
5. The launcher writes a profile under `windsurf_profiles/<profile>/`.

## Model Autodetection

The proxy automatically sniffs the model being requested by Windsurf. In the dashboard, you can see this in the **"Live Detected"** field.

If you need to force a specific model (e.g., force Sonnet to act like Gemini 1.5 Pro):
1. Press **[M]** in the dashboard to cycle through models.
2. The proxy will restart with the `HIGHGRAVITY_MODEL` override.

## Troubleshooting

If traffic isn't reaching the proxy:
1. Check that your Windsurf instance was launched via `launch_windsurf.sh` (The dashboard does this automatically).
2. Run `./launch_debug.sh` to see raw traffic hex-dumps and gRPC routing logs.
3. Confirm `OPENAI_API_BASE=http://localhost:9999` is set in the Windsurf terminal.
