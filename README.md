# HIGH-GRAVITY v3.5.0

The ultimate local identity proxy and optimization shield for Windsurf.

## New in v3.5.x: The Phantom Isolation Update

### 1. 🎭 Shadow Profiles (Session Spoofing)
*   **True Anonymity:** Generates entirely unique machine fingerprints (`sessionId`, `installationId`, `deviceFingerprint`) per API key.
*   **Unlinkable Identities:** Upstream providers can no longer correlate your different API keys to the same developer machine. 

### 2. 🗜️ Token Vault (Context Compression & Analytics)
*   **Semantic Compression:** Safely strips unnecessary whitespace from JSON text payloads before sending them upstream, squeezing more context into your limits.
*   **Real-time Analytics:** The dashboard now displays exactly how many tokens the Ghost Cache has saved you, along with a live dollar-value estimate ($15/1M token benchmark).

### 3. 📚 Cascade Memory Injection (Local RAG)
*   **Automated Rule Injection:** Automatically reads `.highgravity_rules` from your project root and seamlessly appends it to the AI's system prompt.
*   **Persistent Context:** Forces the AI to strictly adhere to your architectural guidelines and coding standards without eating up your chat box space.

### 4. 🌐 Domain Shield (Local DNS Alias)
*   **Bypass Validation:** Circumvents the language server's internal domain check by using `shield.windsurf.com`.
*   **Automatic Setup:** Deployment scripts map `shield.windsurf.com` to `127.0.0.1` in `/etc/hosts`.

### 5. 🚀 Unleash Shield (Elite Feature Activation)
*   **Force-Enable Elite Features:** Locally mocks the Unleash server with a curated list of over 60 high-value flags.
*   **Telemetry Absorption:** Silently intercepts and absorbs Unleash metrics to prevent your editor from sending anomalous usage data.
*   **Future Model Access:** Unlocks early access strings for `O3-Pro` and `Gemini 3.0 Pro`.
*   **Advanced Tools:** Force-enables **MCP tools**, Web Search, Browser tools, and Terminal auto-suggestions.

### 6. 🛡️ Complete API Shield (Full Proxy Mode)
*   **LSP Binary Shield:** A robust Bash shim wraps the real `language_server_linux_x64` binary to enforce process-level isolation.
*   **Invisible Limits:** Automatically swaps identities and retries requests on `429 Rate Limit` or `401/403 Auth` errors.

### 7. 👻 The Ghost Cache (SQLite Semantic Matching)
*   **Zero-Latency Retries:** Instant local responses from a SQLite database for repeated or high-context prompts.

### 8. 📊 High-Sensitivity Dashboard
*   **Cybernetic Pulse:** A high-framerate, animated waveform graph tracks active packets and throughput in real-time.

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
