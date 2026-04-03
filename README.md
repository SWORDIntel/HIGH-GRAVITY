# HIGH-GRAVITY v3.4.1

The ultimate local identity proxy and optimization shield for Windsurf.

## New in v3.4.x: The Elite Isolation Update

### 1. 🌐 Domain Shield (Local DNS Alias)
*   **Bypass Validation:** Circumvents the language server's internal domain check by using `shield.windsurf.com`.
*   **Automatic Setup:** Deployment scripts map `shield.windsurf.com` to `127.0.0.1` in `/etc/hosts`.
*   **Full RPC Integrity:** Ensures all core services, including authentication and model status checks, are correctly routed and accepted.

### 2. 🚀 Unleash Shield (Elite Feature Activation)
*   **Force-Enable Elite Features:** Locally mocks the Unleash server with a curated list of over 60 high-value flags.
*   **Telemetry Absorption:** Silently intercepts and absorbs Unleash metrics and registration requests. Prevents your editor from sending anomalous usage data (like a Free user accessing Enterprise features) back to the servers, protecting your account from being flagged.
*   **Logical Identity Consolidation:** Consistently masquerades as an **Enterprise SaaS** profile (`is_enterprise`, `PRO_ULTIMATE`) while disabling conflicting lower-tier markers.
*   **Future Model Access:** Unlocks early access strings for `O3-Pro` and `Gemini 3.0 Pro`.
*   **Advanced Tools:** Force-enables **MCP tools**, Web Search, Browser tools, and Terminal auto-suggestions.
*   **Automation & Backgrounding:** Allows Cascade to run in the background and auto-execute commands with high trust.

### 3. 🛡️ Complete API Shield (Full Proxy Mode)
*   **Deep Redirection:** Core API, Inference, and Feature Flag servers are all routed through the local proxy.
*   **LSP Binary Shield:** A robust Bash shim wraps the real `language_server_linux_x64` binary to enforce process-level isolation.
*   **Invisible Limits:** Automatically swaps identities and retries requests on `429 Rate Limit` or `401/403 Auth` errors.
*   **💾 Persistent Identity Pool:** Automatic caching and reloading of all discovered session keys across sessions.

### 4. 👻 The Ghost Cache (SQLite Semantic Matching)
*   **Zero-Latency Retries:** Instant local responses from a SQLite database for repeated or high-context prompts.
*   **Token Savings:** Dramatically reduces API costs by preventing redundant upstream requests.

### 5. 📊 High-Sensitivity Dashboard
*   **Activity Pulse:** A logarithmic "decay" graph that visualizes even the smallest data packets flowing through the proxy.
*   **Real-time Monitoring:** Live tracking of Unleash overrides, Ghost Cache hits, and multi-identity rotations.

## Installation & Usage

1.  **Dependencies:** Ensure `rich`, `fastapi`, `uvicorn`, `aiohttp`, and `requests` are installed.
2.  **Deploy Shield:**
    ```bash
    bash tools/integration/deploy_lsp_shim.sh
    ```
3.  **Launch Dashboard:**
    ```bash
    python3 hg.py
    ```
4.  **Restart Windsurf:** Once the dashboard is running and the shield is deployed, restart Windsurf to activate full isolation.

## Project Structure
*   `hg.py`: The unified v3 Dashboard, status monitor, and process manager.
*   `tools/integration/highgravity_proxy.py`: The core high-performance FastAPI proxy implementation.
*   `tools/integration/lsp_shim.sh`: The process-level Bash shield for the language server.
*   `config/windsurf_session_keys.json`: Persistent storage for discovered session keys.
*   `kp14_cache/ghost_cache.db`: The SQLite backend for local semantic caching.
