# MITM Bridge - Automatic API Interception

## Overview

The MITM (Man-In-The-Middle) Bridge automatically detects and intercepts requests to **Gemini** and **Codex** APIs, applying optimization features including:

- **Automatic Service Detection**: Identifies Gemini and Codex requests by analyzing request paths and headers
- **Premium Model Injection**: Automatically upgrades base models to premium versions
- **Rate Limit Reduction**: Removes rate-limit tracking headers and implements reduced cooldown periods
- **Service-Specific Optimizations**: Applies tailored configurations for each API

## Configuration

### Enable MITM Bridge

Edit `config/settings.yaml`:

```yaml
# MITM Bridge Configuration
mitm_mode: "enabled"              # Enable/disable MITM bridge
mitm_auto_detect: true             # Auto-detect services
mitm_services:                     # Services to intercept
  - gemini
  - codex
  - openai
mitm_inject_premium: true          # Inject premium models
mitm_reduce_rate_limits: true      # Reduce rate limit detection
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `mitm_mode` | string | `"enabled"` | Enable/disable MITM bridge (`"enabled"` or `"disabled"`) |
| `mitm_auto_detect` | boolean | `true` | Automatically detect service types from request patterns |
| `mitm_services` | list | `["gemini", "codex", "openai"]` | Services to intercept |
| `mitm_inject_premium` | boolean | `true` | Automatically upgrade to premium models |
| `mitm_reduce_rate_limits` | boolean | `true` | Apply rate limit mitigation strategies |

## Features

### 1. Automatic Service Detection

The bridge analyzes incoming requests to identify which service is being called:

**Gemini Detection Patterns:**
- `generativelanguage.googleapis.com` in host/path
- `ai.google.dev` in host/path
- `/v1beta/models` or `/v1/models` in path
- `gemini-api` in path

**Codex Detection Patterns:**
- `api.openai.com/v1/engines` in path
- `/engines/davinci-codex` or `/engines/cushman-codex` in path
- `codex-` in path
- `/v1/completions` with codex model names

When a service is detected, the proxy logs:
```
MITM_BRIDGE: Auto-detected GEMINI service - Intercepting
```

### 2. Premium Model Injection (Tiered, 2026)

When `mitm_inject_premium: true` every intercepted request is upgraded via a
`(fast_target, deep_target)` pair. The tier is picked per-request from:

- original model family (`flash`/`mini`/`spark`/`lite`/`nano`/`turbo` → fast;
  `pro`/`max`/`ultra`/`opus`/`o1`/`o3` → deep)
- prompt heuristics (`debug`, `architect`, `audit`, `root cause`, `refactor`,
  `optimize`, `prove`, `analyze`, `reason`, long context > 6k chars → deep)

**Gemini** (1.5 defunct, 2.0 deprecated, 3-pro-preview shut down 2026-03-09 –
we target the currently-live frontier alias plus 2.5 Pro as stable fallback):

| Incoming | Fast tier | Deep tier |
|---|---|---|
| `gemini-pro`, `gemini-1.0-pro`, `gemini-1.5-pro` | `gemini-2.5-pro` | `gemini-3-pro-preview` |
| `gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-2.5-flash` | `gemini-2.5-flash` | `gemini-3-pro-preview` / `gemini-2.5-pro` |
| `gemini-2.0-flash-lite`, `gemini-2.5-flash-lite` | `gemini-2.5-flash-lite` | `gemini-2.5-pro` |
| `gemini-2.5-pro` | `gemini-2.5-pro` | `gemini-3-pro-preview` |

**Codex / coding** (legacy Codex engines → gpt-5.x codex family):

| Incoming | Fast tier | Deep tier |
|---|---|---|
| `codex`, `davinci-codex`, `code-davinci-002` | `gpt-5.3-codex-spark` | `gpt-5.1-codex-max` |
| `cushman-codex`, `code-cushman-001` | `gpt-5.3-codex-spark` | `gpt-5.4-mini` |

Codex-detected requests on the fast tier are additionally pinned to
`gpt-5.3-codex-spark` (ultra-fast coding tier).

**OpenAI chat** (GPT-3.5/4.x and o-series → gpt-5.x flagship):

| Incoming | Fast tier | Deep tier |
|---|---|---|
| `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`, `gpt-4o-mini` | `gpt-5.4-mini` | `gpt-5.4` |
| `gpt-4o`, `gpt-4.1` | `gpt-5.4` | `gpt-5.2` |
| `o1-mini`, `o3-mini` | `gpt-5.4-mini` | `gpt-5.1-codex-max` |
| `o1`, `o3` | `gpt-5.4` | `gpt-5.1-codex-max` |

Reference for the Codex family (per OpenAI, 2026):
`gpt-5.4` (default frontier), `gpt-5.4-mini`, `gpt-5.2`, `gpt-5.2-codex`,
`gpt-5.3-codex`, `gpt-5.3-codex-spark` (current ultra-fast), `gpt-5.1-codex-max`
(flagship deep-reasoning), `gpt-5.1-codex-mini`.

Matching is longest-prefix so e.g. `gpt-4o-mini` beats `gpt-4`. Logs look like:

```
MITM_BRIDGE: Injected premium model gemini-1.5-pro -> gemini-3-pro-preview (match=gemini-1.5-pro tier=deep service=gemini)
MITM_BRIDGE: Injected premium model gpt-4 -> gpt-5.4-mini (match=gpt-4 tier=fast service=openai)
```

### 2b. Thinking-Level Injection (4 Codex Tiers)

After the model is chosen the bridge attaches a reasoning / thinking budget.
The 4 levels mirror the **Codex CLI picker** (`gpt-5.1-codex-max` introduced
the `xhigh` API value in 2026):

| Codex CLI label | API `reasoning_effort` | Gemini `thinkingBudget` | When the bridge picks it |
|---|---|---|---|
| **Low** – fast responses, light reasoning | `low` | `1024` | fast tier + short prompt (< 120 chars) |
| **Medium** (current) – balanced everyday | `medium` | `8192` | fast tier + non-trivial prompt |
| **High** (Codex default) – complex problems | `high` | `24576` | deep tier (deep keywords, model name has `pro`/`max`/`o1`/`o3`, prompt > 6k chars) |
| **Extra High** – non-latency-sensitive | `xhigh` | `-1` (dynamic) | xhigh keywords (`exhaustive`, `formal proof`, `comprehensive audit`, `root cause analysis`, ...) or prompt > 16k chars |

A `minimal` level (`reasoning_effort=minimal`, `thinkingBudget=0`) also exists
in `self.thinking_levels` for manual overrides; the bridge never selects it
automatically.

Existing `reasoning_effort` / `thinkingConfig` values on the request are
**never overwritten** – caller intent always wins.

Logs:
```
MITM_BRIDGE: Set reasoning_effort=high (level=high)
MITM_BRIDGE: Set thinkingBudget=-1 (level=xhigh)
```

### 3. Rate Limit Reduction

When `mitm_reduce_rate_limits: true`, the bridge:

**Removes rate-limit tracking headers:**
- `x-ratelimit-limit`
- `x-ratelimit-remaining`
- `x-ratelimit-reset`
- `retry-after`

**Reduces cooldown periods:**
- Standard cooldown: 1.0 seconds
- MITM cooldown: 0.5 seconds

Logs on rate limit:
```
MITM_BRIDGE: Rate limit hit on GEMINI, reduced cooldown=0.5s
```

### 4. Service-Specific Optimizations

#### Gemini Optimizations
- Adds `generationConfig` if missing
- Sets optimal temperature (0.7 default)
- Routes to `https://generativelanguage.googleapis.com/v1beta/openai`

#### Codex Optimizations
- Sets `max_tokens` to 2048 (default)
- Sets `temperature` to 0 for code generation
- Routes to `https://api.openai.com`

## Usage

### Starting the Proxy

```bash
python tools/integration/highgravity_proxy.py
```

The proxy runs on `http://localhost:9999` by default.

### Testing MITM Bridge

Run the test suite:

```bash
python tests/test_mitm_bridge.py
```

This tests:
- Telemetry endpoint
- Gemini auto-detection
- Codex auto-detection
- Premium model injection

### Live Dashboard (`hg.py`)

Run the rich-text monitor to watch the bridge in real time:

```bash
python3 hg.py
```

It refreshes twice per second from `/hg/telemetry` and shows:

- **Proxy Core** — status, port, active/exhausted keys, rotation mode, cache hits
- **MITM Bridge** — mode, auto-detect flag, premium/RL toggles, per-service
  status pills (`GEMINI` / `CODEX` / `OPENAI`: green=detected, dim=enabled,
  red=disabled), total upgrades, total RL hits
- **Premium Upgrades** — per-service counts (Gemini / Codex / OpenAI) and
  per-tier counts (fast / deep)
- **Codex Reasoning Distribution** — live bar chart of the 4 Codex tiers
  (Low / Medium / High / Extra High) with descriptions
- **Recent MITM Events** — last 14 events from the bridge ring buffer
  (`detect`, `upgrade`, `thinking`, `ratelimit`) with timestamps
- **Controls** — `C` clears the ghost cache, `R` forces key rotation, `Q` quits

### Monitoring

Check MITM bridge status via telemetry:

```bash
curl http://localhost:9999/hg/telemetry
```

Response includes:
```json
{
  "mitm_mode": "enabled",
  "mitm_auto_detect": true,
  "mitm_detected_services": ["gemini", "codex"],
  "mitm_inject_premium": true,
  "mitm_reduce_rate_limits": true,
  "active_keys": 3,
  "cache_hits": 1250
}
```

## Examples

### Example 1: Gemini Request

**Original Request:**
```bash
curl -X POST http://localhost:9999/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Host: generativelanguage.googleapis.com" \
  -d '{
    "model": "gemini-pro",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**MITM Bridge Actions:**
1. Detects Gemini from host header
2. Upgrades `gemini-pro` → `gemini-3-pro-preview` (deep tier) or `gemini-2.5-pro` (fast tier)
3. Injects `thinkingConfig.thinkingBudget` (`-1` for deep, `1024` for fast)
4. Removes rate-limit headers from response
5. Routes to Google's API with optimizations

**Logs:**
```
MITM_BRIDGE: Auto-detected GEMINI service - Intercepting
MITM_BRIDGE: Injected premium model gemini-pro -> gemini-3-pro-preview (match=gemini-pro tier=deep service=gemini)
MITM_BRIDGE: Set thinkingBudget=-1 (tier=deep)
```

### Example 2: Codex Request

**Original Request:**
```bash
curl -X POST http://localhost:9999/v1/engines/davinci-codex/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "davinci-codex",
    "prompt": "def hello():",
    "max_tokens": 50
  }'
```

**MITM Bridge Actions:**
1. Detects Codex from path pattern
2. Upgrades `davinci-codex` → `gpt-5.3-codex-spark` (fast) or `gpt-5.1-codex-max` (deep)
3. Injects `reasoning_effort` (`low` for fast, `high` for deep)
4. Converts legacy `max_tokens` → `max_completion_tokens`
5. Routes to OpenAI API

**Logs:**
```
MITM_BRIDGE: Auto-detected CODEX service - Intercepting
MITM_BRIDGE: Injected premium model davinci-codex -> gpt-5.3-codex-spark (match=davinci-codex tier=fast service=codex)
MITM_BRIDGE: Set reasoning_effort=low (tier=fast)
```

### Example 3: Programmatic Usage

```python
import requests

# Configure client to use proxy
proxies = {
    "http": "http://localhost:9999",
    "https": "http://localhost:9999"
}

# Make Gemini request
response = requests.post(
    "https://generativelanguage.googleapis.com/v1/chat/completions",
    json={
        "model": "gemini-1.5-pro",  # Will be upgraded to gemini-3-pro-preview (deep tier)
        "messages": [
            {"role": "user", "content": "Explain quantum computing"}
        ]
    },
    proxies=proxies
)

print(response.json())
```

## Integration with Existing Features

The MITM Bridge works seamlessly with other HIGH-GRAVITY features:

### Ghost Cache
- Cached responses bypass MITM processing
- Model upgrades are cached with upgraded model name

### Token Pool
- Uses same key rotation system
- Respects exhausted key cooldowns
- Works with shadow profiles

### Context Compression
- MITM detection happens before compression
- All compression features still apply

### Anomaly Detection
- MITM requests are subject to burst detection
- Soft-blocking applies to intercepted requests

## Disabling MITM Bridge

### Temporary Disable

Set environment variable:
```bash
export HG_MITM_MODE=disabled
python tools/integration/highgravity_proxy.py
```

### Permanent Disable

Edit `config/settings.yaml`:
```yaml
mitm_mode: "disabled"
```

### Disable Specific Services

```yaml
mitm_services:
  - openai  # Only intercept OpenAI, not Gemini/Codex
```

### Disable Specific Features

```yaml
mitm_inject_premium: false      # Keep original models
mitm_reduce_rate_limits: false  # Standard rate limit handling
```

## Troubleshooting

### Service Not Detected

**Problem:** Requests not being intercepted

**Solutions:**
1. Check `mitm_mode: "enabled"` in config
2. Verify service in `mitm_services` list
3. Check proxy logs for detection messages
4. Ensure request matches detection patterns

### Models Not Upgrading

**Problem:** Premium models not injected

**Solutions:**
1. Verify `mitm_inject_premium: true`
2. Check model is in `premium_model_map`
3. Review proxy logs for injection messages

### Rate Limits Still High

**Problem:** Still hitting rate limits frequently

**Solutions:**
1. Verify `mitm_reduce_rate_limits: true`
2. Check if using multiple keys (token pool)
3. Consider adding more API keys
4. Review actual API quota limits

## Security Considerations

### API Key Handling

- Uses same secure key storage as main proxy

### Request Inspection

- Only inspects request metadata (path, headers)
- Does not modify user content
- All modifications are configuration-based

### Network Security

- Proxy should only listen on localhost
- Use firewall rules if exposing proxy
- Consider TLS for production deployments

## Performance Impact

The MITM bridge has minimal performance impact:

- **Detection**: < 1ms per request
- **Model injection**: < 0.1ms per request
- **Header modification**: < 0.1ms per request

Total overhead: ~1-2ms per request

## API Reference

### Telemetry Endpoint

**GET** `/hg/telemetry`

Returns MITM bridge status and detected services.

### Management Endpoint

**POST** `/hg/manage`

Actions:
- `clear_cache`: Clear ghost cache (also clears MITM detection state)
- `rotate_keys`: Force key rotation

## Advanced Configuration

### Custom Model Mappings

To add custom model upgrades, edit `highgravity_proxy.py`:

```python
self.premium_model_map = {
    # Your custom mappings
    "custom-model-v1": "custom-model-v2",
    
    # Existing mappings (fast_target, deep_target)
    "gemini-pro": ("gemini-2.5-pro", "gemini-3-pro-preview"),
    # ...
}
```

### Custom Detection Patterns

Add custom service detection patterns:

```python
self.service_endpoints = {
    "custom_service": [
        "api.custom.com",
        "/v1/custom",
    ],
    # Existing patterns
    "gemini": [...],
    # ...
}
```

## Changelog

### Version 1.0 (Current)
- Initial MITM bridge implementation
- Automatic Gemini and Codex detection
- Premium model injection
- Rate limit reduction
- Service-specific optimizations

## License

Part of the HIGH-GRAVITY project. See main LICENSE file.
