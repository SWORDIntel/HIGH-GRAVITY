# RE-INSTALLATION & RE-WIRING GUIDE

This guide explains how to re-apply the HIGH-GRAVITY optimizations to a new Windsurf installation or after a Windsurf update.

## 1. Client-Side Midway Control
To enable redirection to the local proxy and activate multi-model token optimization (Canonical Ordering & Context Stripping), you must patch the Windsurf `extension.js`.

### Automatic Patching (All Versions)
The system now automatically detects all Windsurf installations (Stable, Next, Insiders) and applies the patches to each. Run the auto-modifier script:
```bash
./tools/integration/auto_modifier.sh
```
*Note: This requires sudo permissions to write to `/usr/share/`.*

### Persistent Auto-Modifier
To ensure patches are re-applied automatically after Windsurf updates itself, you can install a systemd timer:
```bash
./tools/integration/auto_modifier.sh --install
```
This will set up a background task that re-scans and patches all Windsurf versions every hour.

---

## 2. Multi-Version Support
HIGH-GRAVITY is verified to work with:
- **Windsurf Stable** (`/usr/share/windsurf`)
- **Windsurf Next** (`/usr/share/windsurf-next`)
- **Windsurf Insiders** (if found in standard paths)

### What the Patch Does:
- **Redirection:** Forces Windsurf to use `http://localhost:9999` for all inference requests.
- **Deduplication:** Tracks large context blocks and avoids re-sending them if they haven't changed.
- **Canonical Ordering:** Alphabetically sorts context files to maximize backend cache hits (90% discount on Sonnet/DeepSeek/Opus).
- **Tagging:** Injects cache hints (`highgravity_cache: true`) for the proxy layer.
- **Protocol Interception:** Wraps the core `sendUserCascadeMessage` logic to provide "Midway Control."

---

## 2. Universal Optimization Proxy
The proxy server (`tools/integration/highgravity_proxy.py`) handles the backend logic for cost reduction and identity protection.

### Key Features:
- **Identity Cloaking:** Automatically randomizes `deviceFingerprint` and `installationId` to prevent account-level tracking and throttling.
- **Tier Spoofing:** Impersonates the "Enterprise" plan tier to maximize request priority.
- **Auth Mirroring:** Extracts the authentic Windsurf session key (`v10`) from incoming requests and mirrors it to upstream providers (Anthropic/OpenAI/Google).
- **Multi-Model Routing:** Dynamically routes traffic based on the model UID (Claude, GPT, Gemini, DeepSeek).

### Launching the Proxy:
```bash
python3 tools/integration/highgravity_proxy.py
```

### Automatic Wiring
Open Windsurf to the project you want to wire, then run:
```bash
./tools/integration/detect_and_wire_windsurf.py
```
This script will:
1. Detect your running Windsurf session.
2. Deploy the required hooks to that project's `.windsurf` directory.
3. Generate a HIGH-GRAVITY profile in `windsurf_profiles/`.

---

## 3. Launching
Always launch Windsurf through the HIGH-GRAVITY wrapper to ensure environment variables are correctly inherited:

```bash
# Interactive selection
./launch.py

# Or use a project-specific script
./windsurf_profiles/<project-id>/launch_windsurf.sh
```

---

## 4. Troubleshooting
If optimizations are not appearing in your proxy logs:
1. **Verify Patch:** Check if `/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js.original` exists.
2. **Check Logs:** Monitor the midway intercept log: `tail -f logs/cascade_midway.log`.
3. **Restart:** Ensure Windsurf was fully closed (all processes killed) before restarting.
