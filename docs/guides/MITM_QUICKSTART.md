# MITM Bridge - Quick Start Guide

## What is MITM Bridge?

The MITM (Man-In-The-Middle) Bridge automatically intercepts and optimizes requests to Gemini and Codex APIs. When enabled, it:

1. **Detects** which API service you're calling (Gemini, Codex, or OpenAI)
2. **Upgrades** your models to premium versions automatically
3. **Reduces** rate limit penalties and cooldown periods
4. **Optimizes** request parameters for better performance

## 5-Minute Setup

### Step 1: Enable MITM Bridge

The MITM Bridge is **enabled by default**. Configuration is in `config/settings.yaml`:

```yaml
mitm_mode: "enabled"
mitm_auto_detect: true
mitm_services:
  - gemini
  - codex
  - openai
mitm_inject_premium: true
mitm_reduce_rate_limits: true
```

### Step 2: Start the Proxy

```bash
python tools/integration/highgravity_proxy.py
```

Or use the dashboard:
```bash
python hg.py
```

### Step 3: Verify It's Working

Check telemetry:
```bash
curl http://localhost:9999/hg/telemetry | jq
```

Look for:
```json
{
  "mitm_mode": "enabled",
  "mitm_auto_detect": true,
  "mitm_detected_services": []
}
```

### Step 4: Test Detection

Run the test suite:
```bash
python tests/test_mitm_bridge.py
```

Or manually test with curl:
```bash
# Test Gemini detection
curl -X POST http://localhost:9999/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Host: generativelanguage.googleapis.com" \
  -d '{
    "model": "gemini-pro",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Check if detected
curl http://localhost:9999/hg/telemetry | jq '.mitm_detected_services'
# Should show: ["gemini"]
```

## What Gets Upgraded? (2026)

Upgrades are **tiered** – each mapping exposes a `(fast, deep)` pair and the
bridge picks one per-request based on the original model family and prompt
heuristics (deep-reasoning keywords, long context, etc.).

### Gemini Models (1.5 defunct, 2.0 deprecated)
- `gemini-pro`, `gemini-1.5-pro` → `gemini-2.5-pro` / `gemini-3-pro-preview`
- `gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-2.5-flash` → `gemini-2.5-flash` / `gemini-3-pro-preview`
- `gemini-2.0-flash-lite`, `gemini-2.5-flash-lite` → `gemini-2.5-flash-lite` / `gemini-2.5-pro`
- `gemini-2.5-pro` → `gemini-2.5-pro` / `gemini-3-pro-preview`

### Codex / coding
- `codex`, `davinci-codex`, `code-davinci-002` → `gpt-5.3-codex-spark` / `gpt-5.1-codex-max`
- `cushman-codex`, `code-cushman-001` → `gpt-5.3-codex-spark` / `gpt-5.4-mini`

### OpenAI Chat (GPT-3.5/4.x and o-series)
- `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`, `gpt-4o-mini` → `gpt-5.4-mini` / `gpt-5.4`
- `gpt-4o`, `gpt-4.1` → `gpt-5.4` / `gpt-5.2`
- `o1`, `o3` → `gpt-5.4` / `gpt-5.1-codex-max`
- `o1-mini`, `o3-mini` → `gpt-5.4-mini` / `gpt-5.1-codex-max`

### Codex-Style Thinking Levels (4 tiers)

Mirrors the Codex CLI picker (`gpt-5.1-codex-max` introduced `xhigh` in 2026):

1. **Low** — fast responses, light reasoning · `reasoning_effort=low` · `thinkingBudget=1024`
2. **Medium** — balanced everyday tasks · `reasoning_effort=medium` · `thinkingBudget=8192`
3. **High** (Codex default) — complex problems · `reasoning_effort=high` · `thinkingBudget=24576`
4. **Extra High** — non-latency-sensitive deep work · `reasoning_effort=xhigh` · `thinkingBudget=-1` (dynamic)

The bridge auto-picks based on the tier + prompt heuristics. `xhigh` is only
selected for keywords like `exhaustive`, `formal proof`, `comprehensive audit`,
`root cause analysis`, or prompts > 16k chars. Existing `reasoning_effort` /
`thinkingConfig` on the request are never overwritten.

## How to Use

### Transparent Mode (Recommended)

Just use the proxy - it works automatically:

```python
import requests

# Point your client to the proxy
response = requests.post(
    "http://localhost:9999/v1/chat/completions",
    json={
        "model": "gemini-pro",  # Automatically upgraded!
        "messages": [{"role": "user", "content": "Hello"}]
    }
)
```

### With Windsurf

Set environment variables before launching Windsurf:

```bash
export OPENAI_BASE_URL="http://localhost:9999"
export GOOGLE_API_KEY="your-gemini-key"
windsurf --new-window
```

The proxy will intercept and optimize all API calls.

## Monitoring

### Watch the Logs

```bash
tail -f logs/proxy.log
```

Look for these messages:
```
MITM_BRIDGE: Auto-detected GEMINI service - Intercepting
MITM_BRIDGE: Injected premium model gemini-pro -> gemini-3-pro-preview (match=gemini-pro tier=deep service=gemini)
MITM_BRIDGE: Set thinkingBudget=-1 (tier=deep)
MITM_BRIDGE: Rate limit hit on GEMINI, reduced cooldown=0.5s
```

### Check Telemetry

```bash
# Quick status check
curl -s http://localhost:9999/hg/telemetry | jq '{
  mitm_mode,
  mitm_detected_services,
  mitm_inject_premium,
  active_keys
}'
```

### Dashboard View

The HIGH-GRAVITY dashboard (`hg.py`) shows:
- Active MITM mode status
- Detected services in real-time
- Premium model injection events
- Rate limit reduction stats

## Common Use Cases

### Use Case 1: Gemini Pro → Gemini 3 Pro Preview Upgrade

**Scenario:** You have code calling `gemini-pro` (or the defunct `gemini-1.5-pro`) but want to
transparently upgrade to `gemini-3-pro-preview` for deep-reasoning prompts and `gemini-2.5-pro`
for fast ones.

**Without MITM Bridge:**
- Manually change all `gemini-pro` references
- Update configs, environment variables
- Risk breaking existing code

**With MITM Bridge:**
- Keep existing code unchanged
- Automatic upgrade in proxy
- Zero code modifications needed

### Use Case 2: Codex API Migration

**Scenario:** Legacy code using deprecated Codex API.

**Without MITM Bridge:**
- Rewrite all Codex calls to use GPT-4
- Update authentication
- Test thoroughly

**With MITM Bridge:**
- Keep Codex API calls as-is
- Automatic routing to `gpt-5.3-codex-spark` / `gpt-5.1-codex-max` (tier-aware)
- Legacy `max_tokens` rewritten to `max_completion_tokens`
- Seamless migration

### Use Case 3: Rate Limit Handling

**Scenario:** Hitting rate limits frequently on Gemini API.

**Without MITM Bridge:**
- Manual retry logic
- Long cooldown periods (1s+)
- Wasted time waiting

**With MITM Bridge:**
- Automatic rate limit header removal
- Reduced cooldown (0.5s)
- Token pool rotation
- Faster recovery

## Troubleshooting

### Service Not Detected

**Problem:** Requests passing through but not intercepted.

**Check:**
1. Is `mitm_mode: "enabled"`?
2. Is service in `mitm_services` list?
3. Does request match detection patterns?

**Debug:**
```bash
# Enable debug logging
export HG_LOG_LEVEL=DEBUG
python tools/integration/highgravity_proxy.py
```

### Models Not Upgrading

**Problem:** Still using base models.

**Check:**
1. Is `mitm_inject_premium: true`?
2. Is model in premium map?
3. Check proxy logs for injection messages

**Verify:**
```bash
grep "Injected premium model" logs/proxy.log
```

### Still Getting Rate Limited

**Problem:** Rate limits not reduced.

**Check:**
1. Is `mitm_reduce_rate_limits: true`?
2. Do you have multiple API keys?
3. Are keys properly configured?

**Solution:**
Add more keys to `config/api_keys.json` or use token pool.

## Disabling MITM Bridge

### Temporarily

```bash
# Set environment override
export HG_MITM_MODE=disabled
python tools/integration/highgravity_proxy.py
```

### Permanently

Edit `config/settings.yaml`:
```yaml
mitm_mode: "disabled"
```

### Disable Specific Features

```yaml
mitm_inject_premium: false      # Keep original models
mitm_reduce_rate_limits: false  # Standard rate limits
```

### Disable Specific Services

```yaml
mitm_services:
  - openai  # Only OpenAI, not Gemini/Codex
```

## Advanced Tips

### Custom Model Mappings

Want to map different models? Edit `tools/integration/highgravity_proxy.py`:

```python
self.premium_model_map = {
    "your-model-v1": "your-model-v2",
    # Add custom mappings here
}
```

### Multiple Proxies

Run separate proxies for different services:

```bash
# Proxy 1: Gemini only (port 9999)
python tools/integration/highgravity_proxy.py

# Proxy 2: Codex only (port 10000)
HG_PROXY_PORT=10000 python tools/integration/highgravity_proxy.py
```

Configure different `mitm_services` in their configs.

### Integration with Other Tools

The MITM bridge works with:
- **Ghost Cache**: Cached responses bypass MITM
- **Token Pool**: Uses same key rotation
- **Shadow Profiles**: Applies per-key fingerprints
- **Context Compression**: Works before/after MITM

## Performance

MITM Bridge overhead is minimal:

| Operation | Latency |
|-----------|---------|
| Service Detection | < 1ms |
| Model Injection | < 0.1ms |
| Header Modification | < 0.1ms |
| **Total** | **~1-2ms** |

This is negligible compared to network latency (50-200ms) and API processing time (500ms-5s).

## Security Notes

- MITM bridge runs **locally only**
- Never exposes API keys
- All traffic stays on localhost
- No external connections for detection
- Uses same security as main proxy

## Next Steps

1. Read full documentation: `docs/guides/MITM_BRIDGE.md`
2. Run comprehensive tests: `python tests/test_mitm_bridge.py`
3. Check integration guide: `docs/guides/WINDSURF_INTEGRATION.md`
4. Monitor dashboard: `python hg.py`

## Getting Help

- Check logs: `tail -f logs/proxy.log`
- Run telemetry: `curl http://localhost:9999/hg/telemetry`
- Test suite: `python tests/test_mitm_bridge.py`
- Full docs: `docs/guides/MITM_BRIDGE.md`

---

**Quick Reference Card:**

```bash
# Start proxy with MITM bridge
python tools/integration/highgravity_proxy.py

# Check status
curl http://localhost:9999/hg/telemetry | jq

# Test detection
python tests/test_mitm_bridge.py

# Monitor logs
tail -f logs/proxy.log | grep MITM

# Disable temporarily
export HG_MITM_MODE=disabled

# Enable debug mode
export HG_LOG_LEVEL=DEBUG
```
