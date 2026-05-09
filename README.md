# HIGH-GRAVITY

**Windsurf Proxy & Enhancement Suite**

Intercept, enhance, and optimize Windsurf AI completions with local caching, key rotation, enterprise features, and RAG integration.

---

## Features

✅ **Multi-Key Rotation** — 19+ API keys with automatic round-robin rotation  
✅ **Local Caching** — TurboQuant-compressed vector cache for instant completions  
✅ **Enterprise Spoof** — Unlock all premium features (unlimited context, MCP tools, web search)  
✅ **Unlimited Quota** — Force-bypass usage tracking and "Weekly Quota Exhausted" warnings  
✅ **LSP Shield** — Deep Language Server interception via binary wrapper  
✅ **Khoj RAG** — Local codebase search and context injection  
✅ **Live Dashboard** — Real-time telemetry, logs, and TUI control  

---

## Quick Start

### 1. Install
```bash
git clone <repo-url> HIGH-GRAVITY
cd HIGH-GRAVITY
./hg.sh  # Launches dashboard
```

### 2. Control (Hotkeys)
Once the dashboard is open:
*   Press **`S`** to Start All (Patch + Proxies + Windsurf)
*   Press **`X`** to Stop All
*   Press **`P`** to Deep Patch
*   Press **`U`** to Undo Patch (Unpatch)
*   Press **`L`** to View Live Logs

### 3. CLI Usage
```bash
./hg.sh start       # Quick start all services
./hg.sh stop        # Emergency shutdown
./hg.sh patch       # Apply all binary/JS/host patches
./hg.sh unpatch     # Restore original files
./hg.sh status      # CLI status check
./hg.sh trace       # Watch AI completion routing
```

---

## Architecture

```
┌─────────────┐
│  Windsurf   │
└──────┬──────┘
       │ (patched binary + JS + LSP Shield)
       ↓
┌─────────────────────────────────┐
│  HIGH-GRAVITY Proxy             │
│  ├─ HTTP  :9998                 │
│  ├─ HTTPS :443                  │
│  ├─ Key Rotation (19 keys)      │
│  ├─ Enterprise & Quota Bypass   │
│  └─ TurboQuant Cache            │
└──────┬──────────────────────────┘
       │
       ├─→ Codeium API (upstream)
       │
       └─→ LLM Providers (Gemini/Anthropic keys)
```

---

## Components

### Core Scripts

| File | Purpose |
|------|---------|
| `./hg.sh` | Unified entrypoint & TUI dashboard |
| `hg_dashboard.py` | Rich TUI dashboard logic |
| `scripts/install.sh` | One-click installation of all dependencies |
| `src/patch_all.py` | Unified patcher (binary + JS + hosts + iptables) |
| `src/proxy.py` | Main optimization proxy |

### Services

**Unified Dashboard (`./hg.sh`):**
- Real-time telemetry for 19 discovery keys
- Cache performance and TurboQuant ratios
- System health (Patches, Iptables, Docker)
- Integrated log viewer

**Khoj Runtime (auto-start with `./hg.sh start`):**
- Runs on `127.0.0.1:42110` via Docker
- Uses persistent disk state under `/tank/khoj` when `/tank` exists
- Health is checked by HTTP success (`/api/health`), not a fixed JSON body

**LSP Shield:**
- Transparent binary wrapper for the Language Server
- Force-injects proxy arguments into every request
- Prevents binary updates from breaking interception

---

## File Structure

```
HIGH-GRAVITY/
├── hg.sh                         # Unified Entrypoint
├── hg_dashboard.py               # TUI Dashboard logic
├── scripts/                      # ALL management & utility scripts
├── src/
│   ├── patch_all.py              # Unified patcher
│   ├── proxy.py                  # Main proxy server
│   └── pegasus/                  # Intelligence & RAG layers
├── logs/                         # Service and audit logs
├── certs/                        # Multi-domain TLS certificates
└── archive/                      # Retired artifacts
```

---

## Credits

- **TurboQuant** — Vector compression algorithm
- **Khoj** — Local RAG engine
- **FastAPI** — Proxy framework
- **Rich** — Dashboard UI

---

## License

MIT

---

## Support

For issues or questions:
1. Check logs in `logs/`
2. Run `./hg.sh verify` to verify status
3. Run `./hg.sh dashboard` for real-time diagnostics
4. Review [docs/research/KHOJ_WINDSURF_INTEGRATION.md](docs/research/KHOJ_WINDSURF_INTEGRATION.md) for Khoj setup

---

**Status:** ✅ Fully operational with 21 keys, TurboQuant cache, enterprise features, and Khoj RAG.
