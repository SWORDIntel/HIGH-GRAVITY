# HIGH-GRAVITY v3.2

The ultimate local identity proxy and optimization shield for Windsurf.

## New in v3.2: Full Isolation Update

### 1. 🛡️ Complete API Shield (Full Proxy Mode)
*   **Deep Redirection:** Not just inference, but the core API and Feature Flag servers are now redirected to the proxy.
*   **LSP Binary Shield:** A Python shim now wraps the real `language_server_linux_x64` binary, enforcing proxy usage at the process level.
*   **Invisible Limits:** Automatically intercepts `429 Rate Limit` and `401/403 Auth` errors.
*   **Provider-Aware Pooling:** Separates Windsurf session keys (`sk-ws-...`) from LLM provider keys.
*   **💾 Persistent Identity Pool:** Keys discovered in previous sessions are automatically cached and reloaded.

### 2. 👻 The Ghost Cache (SQLite Semantic Matching)
*   **Zero-Latency Retries:** Locally caches successful responses in a SQLite database.
*   **Token Savings:** Dramatically reduces API costs by preventing redundant upstream requests.

### 3. 🔄 Active Validation Loop
*   **Aggressive Recovery:** A dedicated background thread proactively monitors exhausted keys.
*   **Early Comeback:** Keys return to the active pool the moment their rate-limit cooldown expires.

### 4. 📊 Visual Pulse Dashboard
*   **Live Throughput Graph:** Real-time visualization of data "pulse" flowing through the proxy.
*   **Advanced Metrics:** Tracks Ghost Cache hits, Invisible Retries, and per-key health.

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
4.  **Restart Windsurf:** Once the shield is deployed and the proxy is running, restart Windsurf to activate full isolation.

## Project Structure
*   `hg.py`: The unified v3 Dashboard, status monitor, and process manager.
*   `tools/integration/highgravity_proxy.py`: The core high-performance FastAPI proxy.
*   `tools/integration/lsp_shim.py`: The process-level shield for the language server.
*   `config/windsurf_session_keys.json`: Persistent storage for discovered API keys.
*   `kp14_cache/ghost_cache.db`: The SQLite backend for local semantic caching.
