# Windsurf MITM Fix - Root Cause Analysis

## Problem

**Cascade requests bypass HIGH-GRAVITY proxy** even with all patches applied.

## Root Cause

The **language server binary** (`language_server_linux_x64`) has **hardcoded URLs** compiled into it:
- `https://server.codeium.com`
- `https://inference.codeium.com`
- `https://server.self-serve.windsurf.com`

These cannot be patched by modifying `extension.js` because they're in the compiled binary.

## Evidence

Process 7673 (language server) shows:
```bash
--api_server_url https://server.self-serve.windsurf.com  # ❌ NOT patched
--inference_api_server_url http://shield.windsurf.com:9999  # ✅ Patched
```

Network connections show:
```
192.168.1.76:41144->35.223.238.178:443  # Direct to Codeium API
```

## Why Patches Didn't Work

1. **Extension.js patches**: Only affect the extension, not the language server binary
2. **DNS redirect (/etc/hosts)**: Breaks HTTPS because proxy is HTTP on port 9999
3. **Language server args**: Some args come from extension (patched), others from binary (hardcoded)

## Solutions (In Order of Complexity)

### Solution 1: Proxy Must Handle HTTPS (RECOMMENDED)

Make HIGH-GRAVITY proxy listen on port 443 with HTTPS, then use /etc/hosts:

```bash
# /etc/hosts
127.0.0.1 server.codeium.com
127.0.0.1 inference.codeium.com
127.0.0.1 server.self-serve.windsurf.com
```

**Pros**: Clean, works for all traffic
**Cons**: Requires proxy to handle TLS termination

### Solution 2: Transparent Proxy with iptables + HTTPS

Use iptables to redirect port 443 traffic + make proxy handle HTTPS:

```bash
iptables -t nat -A OUTPUT -p tcp -d 35.223.238.178 --dport 443 \
  -j REDIRECT --to-port 9999
```

**Pros**: No DNS changes needed
**Cons**: Requires root, proxy must handle HTTPS

### Solution 3: Replace Language Server Binary

Patch the binary itself to change hardcoded URLs:

```bash
sed -i 's/server.codeium.com/shield.windsurf.com/g' language_server_linux_x64
```

**Pros**: Direct fix
**Cons**: Binary patching is fragile, breaks signatures

### Solution 4: HTTP Proxy Environment Variables

Set system-wide proxy:

```bash
export HTTP_PROXY=http://127.0.0.1:9999
export HTTPS_PROXY=http://127.0.0.1:9999
```

**Pros**: Standard approach
**Cons**: Language server may not respect these

## Current Status

- ✅ Extension patches applied (8 patches)
- ✅ MITM hooks installed (HG_OPT)
- ❌ Language server still bypassing proxy
- ❌ MITM log empty (0 Cascade calls)
- ⚠️  /etc/hosts redirect removed (caused failures)

## Recommended Next Steps

1. **Update proxy.py to handle HTTPS on port 443**
   - Add TLS termination
   - Self-signed cert for localhost
   - Listen on both 9999 (HTTP) and 443 (HTTPS)

2. **Add /etc/hosts entries** (after proxy supports HTTPS)
   ```
   127.0.0.1 server.codeium.com
   127.0.0.1 inference.codeium.com
   127.0.0.1 server.self-serve.windsurf.com
   ```

3. **Restart Windsurf**

4. **Verify**:
   ```bash
   # Should show connections to 127.0.0.1:443
   lsof -i -n -P | grep windsurf | grep 443
   
   # Should populate with events
   tail -f logs/cascade_midway.log
   ```

## Alternative: Accept Current Limitation

If HTTPS proxy is too complex, we can:
- Accept that language server bypasses proxy
- Only intercept extension-level traffic
- Use Khoj integration for context (works independently)

## Files to Modify

1. `src/proxy.py` - Add HTTPS support
2. `/etc/hosts` - Add DNS redirects (after HTTPS works)
3. `hg_start.sh` - Update to handle HTTPS proxy

## Technical Details

**Why /etc/hosts failed**:
```
Language server: https://server.codeium.com
  → DNS: 127.0.0.1
  → Tries: https://127.0.0.1:443
  → Proxy: Only listening on HTTP :9999
  → Result: Connection refused
```

**What we need**:
```
Language server: https://server.codeium.com
  → DNS: 127.0.0.1
  → Connects: https://127.0.0.1:443
  → Proxy: HTTPS listener on :443
  → Forwards: To real API or handles locally
  → Result: Success + MITM logging
```
