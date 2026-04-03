# HIGH-GRAVITY v3.5.0: The Pegasus Update 🐎

The ultimate local identity proxy, optimization shield, and cyber-intelligence gateway for Windsurf.

## New in v3.5.0: The Pegasus Update

### 1. 📡 True Response Streaming (Latency Kill)
*   **Zero-Buffer Architecture:** Real-time chunk forwarding via `iter_any()`. Fixed the "Model provider unreachable" error caused by response buffering.
*   **Synchronous Interception:** Intercepts telemetry and metrics without delaying the core model response stream.

### 2. 🧠 Smart Model Remapping (Multi-Provider Logic)
*   **Dynamic Fallback:** Automatically remaps Claude 3.5 Sonnet, GPT-4o, and Opus requests to **Gemini 2.0 Flash** if only Google API keys are available.
*   **Key-Aware Routing:** Routes traffic based on the prefix (`AIzaSy` vs `sk-ws`) to ensure the correct provider endpoint is hit every time.

### 3. 🔴 Pegasus Cyber-Intelligence Dashboard
*   **NSO Group Aesthetic:** Overhauled UI with deep reds, dark greys, and high-contrast whites for a high-tech surveillance feel.
*   **Enhanced Metrics:** Tracks "Total Intercepts," "Exfiltrated Tokens," and "Active Nodes" with Pegasus-grade precision.
*   **Uplink Monitoring:** Real-time status indicators for the proxy tunnel and background processes.

### 4. 🎭 Shadow Profiles (Session Spoofing)
*   **True Anonymity:** Generates unique machine fingerprints (`sessionId`, `installationId`, `deviceFingerprint`) per API key to prevent provider-side correlation.

### 5. 🚀 Unleash Shield (Elite Feature Activation)
*   **Enterprise SaaS Spoofing:** Locally mocks over 60 high-value feature flags, enabling MCP tools, Web Search, and early access to O3/Gemini 3.0.
*   **Telemetry Absorption:** Silently drops Unleash metrics to keep your usage profile invisible.

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
4.  **Infiltrate Windsurf:** Use the `W` key in the dashboard or restart Windsurf manually to activate full isolation.

## Project Structure
*   `hg.py`: The unified Pegasus Dashboard and process manager.
*   `tools/integration/highgravity_proxy.py`: The core high-performance FastAPI proxy with streaming support.
*   `tools/integration/lsp_shim.sh`: The process-level Bash shield for the language server.
*   `config/windsurf_session_keys.json`: Persistent storage for discovered session keys.
*   `kp14_cache/ghost_cache.db`: The SQLite backend for local semantic caching.
