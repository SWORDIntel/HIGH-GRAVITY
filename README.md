# HIGH-GRAVITY v3.0

The ultimate local identity proxy and optimization shield for Windsurf.

## New in v3.0: The Shield & Ghost Update

### 1. 🛡️ API Key Shield (Multi-Identity Pooling)
*   **Invisible Limits:** Automatically intercepts `429 Rate Limit` and `401/403 Auth` errors.
*   **Provider-Aware Pooling:** Separates Windsurf session keys (`sk-ws-...`) from LLM provider keys (Gemini/Anthropic).
*   **Silent Retries:** Swaps identities and retries requests in the background. You never see a limit popup again.
*   **Sticky Routing:** Uses one key until it fails, reducing unnecessary rotation noise.

### 2. 👻 The Ghost Cache (SQLite Semantic Matching)
*   **Zero-Latency Retries:** Locally caches successful responses. Repeated queries or identical large context files are served instantly from disk.
*   **Token Savings:** Reduces API costs by never sending the same large prompt twice in an hour.

### 3. 🔄 Active Validation Loop
*   **Aggressive Recovery:** Background validation thread pings exhausted keys every 30s.
*   **Early Comeback:** Keys return to the active pool the second their limit clears, ignoring arbitrary timers.

### 4. 📊 Visual Pulse Dashboard
*   **Live Throughput Graph:** Real-time visualization of data flowing through the proxy.
*   **Efficiency Metrics:** Tracks Ghost Cache hits and Invisible Retries directly on the home screen.

## Installation & Usage

1.  **Dependencies:** Ensure `rich`, `fastapi`, `uvicorn`, and `aiohttp` are installed.
2.  **Config:** Add your keys to `config/gemini_keys.json` or just launch Windsurf—the proxy will harvest your session keys automatically.
3.  **Launch:**
    ```bash
    python3 hg.py
    ```
4.  **Integration:** The proxy listens on `127.0.0.1:9999`. Ensure your Windsurf profile is wired to use it as the upstream gateway.

## Project Structure
*   `hg.py`: The unified v3 Dashboard and process manager.
*   `tools/integration/highgravity_proxy.py`: The core high-performance FastAPI proxy.
*   `kp14_cache/ghost_cache.db`: The SQLite backend for local semantic caching.
