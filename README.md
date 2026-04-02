# HIGH-GRAVITY v3.3.4

The ultimate local identity proxy and optimization shield for Windsurf.

## New in v3.3.4: The Elite Feature Update

### 1. 🚀 Unleash Shield (Elite Feature Activation)
*   **Force-Enable Elite Features:** The proxy now mocks the Unleash server with a curated list of over 60 high-value flags.
*   **Future Model Access:** Early activation strings for `O3-Pro` and `Gemini 3.0 Pro`.
*   **Advanced Tools:** Unlocks MCP tool support, Web Search tools, Browser tools, and Terminal auto-suggestions.
*   **Enterprise Tier Bypassing:** Force-enables `PRO_ULTIMATE` and `ENTERPRISE_SAAS` status locally.
*   **Automation & Backgrounding:** Allows Cascade to run in the background and auto-execute commands with increased trust.

### 2. 🛡️ Complete API Shield (Full Proxy Mode)
*   **Deep Redirection:** Core API, Inference, and Feature Flag servers are all routed through the proxy.
*   **LSP Binary Shield:** A Python shim wraps the real `language_server_linux_x64` binary to enforce process-level isolation.
*   **Invisible Limits:** Automatically swaps identities and retries requests on `429 Rate Limit` or `401/403 Auth` errors.
*   **💾 Persistent Identity Pool:** Automatic caching and reloading of all discovered session keys.

### 3. 👻 The Ghost Cache (SQLite Semantic Matching)
*   **Zero-Latency Retries:** Instant responses from a local SQLite database for repeated or high-context prompts.
*   **Token Savings:** Prevents redundant upstream requests, reducing API costs.

### 4. 📊 High-Sensitivity Dashboard
*   **Activity Pulse:** A new logarithmic "decay" graph that visualizes even the smallest data packets flowing through the proxy.
*   **Real-time Monitoring:** Tracks Unleash overrides, Ghost Cache hits, and Identity rotations live.

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
4.  **Restart Windsurf:** After deployment, restart Windsurf to activate full network isolation and the feature shield.

## Project Structure
*   `hg.py`: The unified v3 Dashboard and process manager.
*   `tools/integration/highgravity_proxy.py`: The core high-performance FastAPI proxy.
*   `tools/integration/lsp_shim.py`: Process-level shield for the language server.
*   `config/windsurf_session_keys.json`: Persistent storage for session keys.
*   `kp14_cache/ghost_cache.db`: SQLite backend for local caching.
