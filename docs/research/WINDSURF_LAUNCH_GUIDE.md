# Windsurf Launch Guide - HIGH-GRAVITY Integration

## Quick Start

### From Dashboard (hg.py)
Press **W** in the dashboard to launch Windsurf with HIGH-GRAVITY proxy.

### From Command Line

**Basic launch:**
```bash
bin/gemini_session_launcher.py --mode windsurf --provider proxy --proxy-url http://localhost:9998
```

**With specific key:**
```bash
bin/gemini_session_launcher.py --mode windsurf --provider proxy --proxy-url http://localhost:9998 --key-index 1
```

**With custom window name:**
```bash
bin/gemini_session_launcher.py --mode windsurf --provider proxy --proxy-url http://localhost:9998 --window-name my-project
```

## Piped Configuration (JSON)

### Method 1: Echo JSON
```bash
echo '{"mode":"windsurf","provider":"proxy","proxyUrl":"http://localhost:9998"}' | bin/launch_windsurf_piped.sh
```

### Method 2: From File
```bash
cat config/windsurf_launch_examples.json | jq -r '.examples.basic_proxy.config' | bin/launch_windsurf_piped.sh
```

### Method 3: Custom JSON File
Create `my_config.json`:
```json
{
  "mode": "windsurf",
  "provider": "proxy",
  "proxyUrl": "http://localhost:9998",
  "keyIndex": "1",
  "windowName": "my-workspace",
  "model": "gemini-2.0-flash-thinking-exp"
}
```

Launch:
```bash
cat my_config.json | bin/launch_windsurf_piped.sh
```

## Available Options

### CLI Arguments
| Argument | Description | Example |
|----------|-------------|---------|
| `--mode windsurf` | Launch in Windsurf mode | Required |
| `--provider proxy` | Use HIGH-GRAVITY proxy | `proxy` or `direct` |
| `--proxy-url URL` | Proxy endpoint | `http://localhost:9998` |
| `--api-key KEY` | Direct API key | `AIza...` |
| `--key-index N` | Select key by index (1-based) | `1`, `2`, `3` |
| `--window-name NAME` | Logical window/profile name | `my-project` |
| `--model MODEL` | Model label for profile | `gemini-exp-1206` |
| `--dry-run` | Prepare without launching | Flag |
| `--check` | Check key validity only | Flag |

### JSON Keys (for piping)
| Key | Type | Description |
|-----|------|-------------|
| `mode` | string | `"windsurf"`, `"studio"`, or `"chat"` |
| `provider` | string | `"proxy"` or `"direct"` |
| `proxyUrl` | string | HIGH-GRAVITY proxy URL |
| `apiKey` | string | Direct API key input |
| `keyIndex` | string/int | Key index (1-based) |
| `windowName` | string | Window/profile name |
| `model` | string | Model label |
| `dryRun` | boolean | Prepare without launching |
| `check` | boolean | Check key validity only |

## Examples from config/windsurf_launch_examples.json

### Basic Proxy Launch
```bash
echo '{"mode":"windsurf","provider":"proxy","proxyUrl":"http://localhost:9998"}' | bin/launch_windsurf_piped.sh
```

### With Key Index
```bash
echo '{"mode":"windsurf","provider":"proxy","proxyUrl":"http://localhost:9998","keyIndex":"1"}' | bin/launch_windsurf_piped.sh
```

### With Custom Window Name
```bash
echo '{"mode":"windsurf","provider":"proxy","proxyUrl":"http://localhost:9998","windowName":"my-project","model":"gemini-exp-1206"}' | bin/launch_windsurf_piped.sh
```

### Dry Run (Test Configuration)
```bash
echo '{"mode":"windsurf","provider":"proxy","proxyUrl":"http://localhost:9998","dryRun":true}' | bin/launch_windsurf_piped.sh
```

## Integration with Codex/Windsurf CLI

You can pipe configuration from Codex or other tools:

```bash
# From Codex output
codex config generate --format json | bin/launch_windsurf_piped.sh

# From environment variables
cat << EOF | bin/launch_windsurf_piped.sh
{
  "mode": "windsurf",
  "provider": "proxy",
  "proxyUrl": "${HIGHGRAVITY_PROXY_URL:-http://localhost:9998}",
  "apiKey": "${GEMINI_API_KEY}",
  "windowName": "${PROJECT_NAME}"
}
EOF
```

## Precedence Order

When multiple sources provide the same option:
1. **CLI arguments** (highest priority)
2. **stdin JSON payload**
3. **Environment variables**
4. **Built-in defaults** (lowest priority)

Example:
```bash
# CLI arg wins over piped JSON
echo '{"keyIndex":"2"}' | bin/launch_windsurf_piped.sh --key-index 1
# Result: Uses key index 1 (from CLI)
```

## Environment Variables

The launcher also reads these environment variables:
- `HIGHGRAVITY_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_API_KEY`
- `HIGHGRAVITY_KEY_INDEX`
- `HIGHGRAVITY_MODE`
- `HIGHGRAVITY_PROVIDER`
- `HIGHGRAVITY_PROXY_URL` / `OPENAI_BASE_URL`
- `HIGHGRAVITY_MODEL`
- `HIGHGRAVITY_WINDOW_NAME`

## Troubleshooting

### Check if proxy is running
```bash
curl http://localhost:9998/hg/telemetry
```

### Test configuration without launching
```bash
echo '{"mode":"windsurf","provider":"proxy","proxyUrl":"http://localhost:9998","dryRun":true}' | bin/launch_windsurf_piped.sh
```

### Check key validity
```bash
bin/gemini_session_launcher.py --check --key-index 1
```

### View available keys
```bash
bin/gemini_session_launcher.py --list
```
