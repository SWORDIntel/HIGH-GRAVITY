# Windsurf HIGH-GRAVITY Patcher v2.0 Guide

## Overview

The enhanced patcher now includes command-line flags, built-in verification, and better user experience.

## New Features in v2.0

### 1. Command-Line Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--force` | `-f` | Force re-patch even if already patched |
| `--verify` | `-v` | Verify patches without modifying files |
| `--list` | `-l` | List Windsurf installations and exit |
| `--quiet` | `-q` | Minimal output (for scripting) |
| `--help` | `-h` | Show help message |

### 2. Color-Coded Output

- 🟢 **Green**: Success messages
- 🟡 **Yellow**: Warnings
- 🔴 **Red**: Errors
- 🔵 **Blue**: Info/headers

### 3. Built-in Verification

Checks 5 critical patches:
- ✓ INFERENCE_API_SERVER_URL
- ✓ DEFAULT_API_SERVER_URL
- ✓ DEFAULT_REGISTER_API_SERVER_URL
- ✓ Unleash
- ✓ HG_OPT function

### 4. Exit Codes

- `0`: Success (all patches applied/verified)
- `1`: Failure (some patches failed)

## Usage Examples

### Basic Patching

```bash
python3 src/patch_windsurf_client.py
```

**Output:**
```
╔════════════════════════════════════════════════════════════╗
║     Windsurf HIGH-GRAVITY Patcher v2.0                     ║
╚════════════════════════════════════════════════════════════╝

[*] Found 1 Windsurf installation(s).
[*] Patching: /usr/share/windsurf-next/.../extension.js
    [✓] Hardcoded INFERENCE_API_SERVER_URL redirected.
    [✓] Hardcoded DEFAULT_API_SERVER_URL redirected.
    ...
    [✓] Successfully updated resources

[✓] Patching complete: 1/1 successful

[!] Please restart Windsurf for changes to take effect
```

### Verify Patches

Check if patches are applied without modifying:

```bash
python3 src/patch_windsurf_client.py --verify
```

**Output:**
```
[*] Patching: /usr/share/windsurf-next/.../extension.js
    - Already patched. Use --force to re-patch.
    ✓ INFERENCE_API_SERVER_URL
    ✓ DEFAULT_API_SERVER_URL
    ✓ DEFAULT_REGISTER_API_SERVER_URL
    ✓ Unleash
    ✓ HG_OPT function

    Total proxy references: 10

[✓] Verification complete: 1/1 passed
```

### Force Re-patch

Re-apply patches even if already applied:

```bash
python3 src/patch_windsurf_client.py --force
```

**Use case**: After Windsurf updates that may have overwritten patches.

### List Installations

Find all Windsurf installations:

```bash
python3 src/patch_windsurf_client.py --list
```

**Output:**
```
[*] Found 1 Windsurf installation(s).
  - /usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js
```

### Quiet Mode (Scripting)

Minimal output for automation:

```bash
python3 src/patch_windsurf_client.py --quiet
echo "Exit code: $?"
```

## Workflow Integration

### Automated Patching Script

```bash
#!/bin/bash
# Auto-patch after Windsurf updates

cd /mnt/DSMIL/HIGH-GRAVITY

# Check if patches are needed
if ! python3 src/patch_windsurf_client.py --verify --quiet; then
    echo "Patches missing, applying..."
    python3 src/patch_windsurf_client.py
    
    # Restart Windsurf
    pkill -f windsurf
    /usr/share/windsurf-next/windsurf-next &
fi
```

### CI/CD Integration

```bash
# In deployment script
python3 src/patch_windsurf_client.py --quiet
if [ $? -ne 0 ]; then
    echo "Patching failed!"
    exit 1
fi
```

## What Gets Patched

### 1. Hardcoded URLs (5 patches)

| URL | Patched To |
|-----|------------|
| `https://inference.codeium.com` | `http://shield.windsurf.com:9998` |
| `https://server.codeium.com` | `http://shield.windsurf.com:9998` |
| `https://register.windsurf.com` | `http://shield.windsurf.com:9998` |
| `https://eu.windsurf.com/_route/api_server` | `http://shield.windsurf.com:9998` |
| `https://windsurf.fedstart.com/_route/api_server` | `http://shield.windsurf.com:9998` |

### 2. Feature Flags

- Unleash: `https://unleash.codeium.com/api/` → `http://shield.windsurf.com:9998/unleash/`

### 3. MITM Hooks

- Injects `globalThis.HG_OPT` function
- Wraps protocol send calls
- Logs to `logs/cascade_midway.log`

## Verification Checklist

After patching, verify:

```bash
# 1. Run verification
python3 src/patch_windsurf_client.py --verify

# 2. Check proxy references
grep -c "shield.windsurf.com:9998" /usr/share/windsurf-next/.../extension.js
# Should show: 10

# 3. Check no external URLs remain
grep -c "inference.codeium.com\|server.codeium.com" /usr/share/windsurf-next/.../extension.js
# Should show: 0

# 4. Restart Windsurf
pkill -f windsurf
/usr/share/windsurf-next/windsurf-next &

# 5. Test Cascade
# Press Ctrl+L, ask a question
# Watch: tail -f logs/cascade_midway.log
```

## Troubleshooting

### "Already patched" but verification fails

```bash
# Force re-patch
python3 src/patch_windsurf_client.py --force
```

### Windsurf updated and patches lost

```bash
# Check if patches present
python3 src/patch_windsurf_client.py --verify

# If failed, re-patch
python3 src/patch_windsurf_client.py
```

### Multiple Windsurf installations

```bash
# List all
python3 src/patch_windsurf_client.py --list

# Patcher handles all automatically
python3 src/patch_windsurf_client.py
```

## Comparison: v1.0 vs v2.0

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Basic patching | ✓ | ✓ |
| Command-line flags | ✗ | ✓ |
| Verification mode | ✗ | ✓ |
| Color output | ✗ | ✓ |
| Exit codes | ✗ | ✓ |
| Force mode | ✗ | ✓ |
| List installs | ✗ | ✓ |
| Quiet mode | ✗ | ✓ |
| Built-in help | ✗ | ✓ |

## Related Tools

- `verify_windsurf_patches.sh` - Standalone verification script
- `test_windsurf_integration.sh` - Full integration test
- `patch_windsurf_urls.py` - URL-only patcher (legacy)
- `patch_windsurf_aggressive.py` - Debug logging

## Version History

- **v2.0** (2026-04-20): Added flags, verification, colors, exit codes
- **v1.0** (2026-04-19): Initial release with 8 patches

## Support

For issues or questions:
1. Run verification: `python3 src/patch_windsurf_client.py --verify`
2. Check logs: `tail -f logs/proxy.log logs/cascade_midway.log`
3. Review: `WINDSURF_MITM_FIX.md`
