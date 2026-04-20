# Windsurf MITM Fix - Diagnosis & Solution

## Problem Identified

**Cascade requests were bypassing the HIGH-GRAVITY proxy entirely.**

### Root Cause

The original patch (`patch_windsurf_client.py`) was trying to replace dynamic code patterns like:
```javascript
n.push("--inference_api_server_url",A.inferenceApiServerUrl)
```

But Windsurf's code structure changed. The API URLs are now **hardcoded in configuration maps**, not passed dynamically.

### Evidence

1. **Network connections**: Windsurf was connecting directly to `35.223.238.178:443` (Codeium API)
2. **Proxy logs**: Only unleash/telemetry traffic, NO Cascade API calls
3. **MITM log**: Empty (HG_OPT never called because requests never went through proxy)

## Solution Applied

Created `patch_windsurf_urls.py` to patch the **hardcoded default URLs** in the config map:

### URLs Patched

1. **INFERENCE_API_SERVER_URL**: `https://inference.codeium.com` → `http://shield.windsurf.com:9999`
2. **DEFAULT_API_SERVER_URL**: `https://server.codeium.com` → `http://shield.windsurf.com:9999`
3. **DEFAULT_REGISTER_API_SERVER_URL**: `https://register.windsurf.com` → `http://shield.windsurf.com:9999`
4. **EU routes** (2x): `https://eu.windsurf.com/_route/api_server` → `http://shield.windsurf.com:9999`
5. **Fed routes** (2x): `https://windsurf.fedstart.com/_route/api_server` → `http://shield.windsurf.com:9999`

## Next Steps

### 1. Restart Windsurf
```bash
pkill -f windsurf
/usr/share/windsurf-next/windsurf-next &
```

### 2. Verify Proxy Receives Cascade Traffic
```bash
# Watch proxy log
tail -f /mnt/DSMIL/HIGH-GRAVITY/logs/proxy.log | grep "v1/chat"

# In Windsurf: Press Ctrl+L, ask a question
```

### 3. Verify MITM Logging
```bash
# Watch MITM log
tail -f /mnt/DSMIL/HIGH-GRAVITY/logs/cascade_midway.log

# Should see protocol events when using Cascade
```

### 4. Check Network Connections
```bash
# Should see connections to 127.0.0.1:9999, NOT external IPs
lsof -i -n -P | grep windsurf | grep ESTABLISHED
```

## Files Created

- `src/patch_windsurf_urls.py` - URL redirection patch
- `src/patch_windsurf_aggressive.py` - Aggressive logging (for debugging)
- `test_windsurf_integration.sh` - Integration test suite
- `WINDSURF_MITM_FIX.md` - This document

## Expected Behavior After Fix

1. **Proxy logs**: Will show `POST /v1/chat/completions` requests
2. **MITM log**: Will populate with protocol events
3. **Network**: Windsurf connects to `127.0.0.1:9999` only
4. **Khoj**: Context injection will work on Cascade queries

## Diagnosis Commands

```bash
# Test proxy
curl http://shield.windsurf.com:9999/hg/telemetry

# Check patch applied
grep "shield.windsurf.com:9999" /usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js | wc -l
# Should show multiple matches

# Check Windsurf connections
lsof -i -n -P | grep windsurf | grep ESTABLISHED

# Monitor logs
tail -f logs/proxy.log logs/cascade_midway.log
```

## Status

- ✅ URLs patched in extension.js
- ⏳ Waiting for Windsurf restart
- ⏳ Verification pending
