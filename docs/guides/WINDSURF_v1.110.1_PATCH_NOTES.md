# Windsurf v1.110.1-next Patch Notes

**Date**: May 9, 2026
**Status**: DEPLOYED

## Summary
The latest update to Windsurf Next (v1.110.1-next) introduced changes to the `language_server_linux_x64` binary that shifted the domain validation offsets. HIGH-GRAVITY has been updated to support this version with multi-point binary patching.

## Technical Details

### Binary Offsets
The domain validation logic, which prevents connections to non-standard domains (like `proxy.windsurf.com`), has moved. We now patch three distinct verification points to ensure complete coverage.

| Patch Point | Offset (v1.110.1-next) | Old Offset (v1.100.x) | Logic |
|-------------|-------------------------|------------------------|-------|
| Validation #1 | `0x818b87d` | `0x818e12d` | `JE +0x2e` → `NOP NOP` |
| Validation #2 | `0x818ba9d` | N/A | `JE +0x2e` → `NOP NOP` |
| Validation #3 | `0x81973fd` | N/A | `JE +0x2e` → `NOP NOP` |

### URL Replacements
The 26-byte and 29-byte URL slots remain compatible with previous patches:
- `https://server.codeium.com` → `https://proxy.windsurf.com`
- `https://inference.codeium.com` → `https://inferapi.windsurf.com`

### Host Redirection (New)
We discovered additional hardcoded endpoints within the new binary that are NOT patched directly due to byte-length constraints. To prevent the language server from bypassing the HIGH-GRAVITY proxy, the unified patcher now adds the following domains to `/etc/hosts`:
- `server.codeium.com`
- `inference.codeium.com`
- `server.self-serve.windsurf.com`
- `unleash.codeium.com`
- `southcentral-lb.codeium.com`
- `api.codeium.com`

## Verification
The `hg.sh verify` command and the Pegasus Dashboard have been updated to check the new primary offset (`0x818b87d`).

### Successful Patch State:
```
Verifying binary: language_server_linux_x64
  [✓] Already patched: https://proxy.windsurf.com
  [✓] Already patched: https://inferapi.windsurf.com
  [✓] Byte patch already applied @ 0x818b87d  (NOP domain validation branch #1)
  [✓] Byte patch already applied @ 0x818ba9d  (NOP domain validation branch #2)
  [✓] Byte patch already applied @ 0x81973fd  (NOP domain validation branch #3)
```

## How to Apply
1. Pull the latest HIGH-GRAVITY changes.
2. Run the unified patcher:
   ```bash
   ./hg.sh patch
   ```
3. Restart Windsurf Next.
