# HIGH-GRAVITY v3.0

The ultimate local identity proxy and optimization shield for Windsurf.

## New in v3.0: The Shield & Ghost Update

### 1. 🛡️ API Key Shield (Multi-Identity Pooling)
*   **Invisible Limits:** Automatically intercepts `429 Rate Limit` and `401/403 Auth` errors.
*   **Provider-Aware Pooling:** Separates Windsurf session keys (`sk-ws-...`) from LLM provider keys (Gemini/Anthropic).
*   **Silent Retries:** Swaps identities and retries requests in the background. You never see a limit popup again.
*   **Sticky Routing:** Uses one key until it fails, reducing unnecessary rotation noise.
*   **💾 Persistent Identity Pool:** Keys discovered in previous sessions are now automatically cached and reloaded, ensuring a robust, growing pool of identities.

### 2. 👻 The Ghost Cache (SQLite Semantic Matching)
*   **Zero-Latency Retries:** Locally caches successful responses in a SQLite database. Repeated queries or identical large context files are served instantly from disk.
*   **Token Savings:** Dramatically reduces API costs by preventing redundant upstream requests for identical prompts.

### 3. 🔄 Active Validation Loop
*   **Aggressive Recovery:** A dedicated background thread proactively monitors exhausted keys.
*   **Early Comeback:** Keys return to the active pool the moment their rate-limit cooldown expires, maximizing availability.

### 4. 📊 Visual Pulse Dashboard
*   **Live Throughput Graph:** Real-time visualization of data "pulse" flowing through the proxy.
*   **Advanced Metrics:** Tracks Ghost Cache hits, Invisible Retries, and per-key health directly on the integrated `hg.py` dashboard.

## Installation & Usage

1.  **Dependencies:** Ensure `rich`, `fastapi`, `uvicorn`, and `aiohttp` are installed.
2.  **Config:** Add your keys to `config/gemini_keys.json` or simply launch Windsurf—the proxy will harvest and persist your session keys automatically.
3.  **Launch:**
    ```bash
    python3 hg.py
    ```
4.  **Integration:** The proxy listens on `127.0.0.1:9999`. Ensure your Windsurf profile is configured to use this as its upstream gateway.

## Project Structure
*   `hg.py`: The unified v3 Dashboard, status monitor, and process manager.
*   `tools/integration/highgravity_proxy.py`: The core high-performance FastAPI proxy implementation.
*   `config/windsurf_session_keys.json`: Persistent storage for discovered API keys.
*   `kp14_cache/ghost_cache.db`: The SQLite backend for local semantic caching.
