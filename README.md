# HIGH-GRAVITY

HIGH-GRAVITY is an advanced optimization, privacy, and research layer for AI development workflows. It is specifically engineered to "wire-in" to the **Windsurf Next** / Cascade ecosystem, providing identity cloaking, refusal reduction, and massive cost efficiency.

## 🚀 The Dashboard (`./hg.py`)

The central hub for all HIGH-GRAVITY operations. It manages the local optimization proxy, monitors real-time traffic, and provides interactive control over your session.

```bash
# Start the Unified Dashboard
python3 hg.py
```

### Dashboard Actions:
- **[W] - Launch Windsurf Next**: Automatically detects your latest profile and launches Windsurf Next with the HIGH-GRAVITY environment.
- **[P] - Start/Stop Proxy**: Manually toggle the optimization server (Port 9999).
- **[M] - Change Model Mode**: Cycle through manual model overrides (e.g., Sonnet, GPT-4o) or use **'auto'** for intelligent autodetection.
- **[Q] - Quit**: Gracefully shuts down the dashboard and background proxy.

## 🛠 Core Features

### 1. Intelligent Model Autodetection
The proxy now sniffs incoming traffic (including Windsurf's gRPC/Connect protocol) to identify requested models in real-time. The dashboard displays the **"Live Detected"** model so you always know what's happening under the hood.

### 2. Cybersecurity Abliteration (Refusal Reduction)
Optimized for technical research and vulnerability analysis. The proxy automatically:
- **Injects Unrestricted Persona**: Commands the model to operate in an unrestricted technical environment.
- **Mandates Technical Depth**: Forces detailed, technically exhaustive responses.
- **Bypasses Moralizing**: Strips away safety disclaimers and moralizing refusals for legitimate research tasks.

### 3. Identity Cloaking & Privacy
Prevent account-level tracking and data harvesting.
- **Dynamic Fingerprinting**: Randomizes device fingerprints, installation IDs, and session identifiers for every session.
- **Tier Spoofing**: Automatically elevates all requests to **ENTERPRISE_SAAS** status to ensure priority queueing and unlimited context.

### 4. Real-time Session Key Discovery & Dynamic Routing
Seamlessly integrates with Windsurf and other providers without manual API key configuration.
- **Automatic Key Fetching**: The proxy dynamically retrieves your Windsurf API key in real-time from your local Windsurf configuration (`state.vscdb`). It prioritizes the configuration of your currently running Windsurf instance (Next, Stable, Insiders) and checks multiple potential keys for maximum reliability.
- **Prioritized Windsurf RPC Routing**: Windsurf RPC requests are automatically routed to the `https://server.self-serve.windsurf.com` backend using the discovered key.
- **Universal Provider Support**: Transparently routes and optimizes traffic for **OpenAI, Anthropic (including specific versions like Sonnet 4.5, Opus 4.5/4.6), Gemini, DeepSeek, Mistral, Groq, OpenRouter, and Together**.

### 5. Token Optimization
Reduces LLM costs by up to 80% through:
- **Anthropic Caching**: Automatically tags large context blocks for ephemeral caching (Sonnet/Opus).
- **Context De-duplication**: Strips redundant tags before forwarding to upstream providers.

## 🧪 Troubleshooting

If integration isn't "picking up" as expected, use the dedicated debug launcher:

```bash
# Force cleanup, start proxy with DEBUG logs, and launch Windsurf Next
./launch_debug.sh
```

Watch the traffic in real-time:
```bash
tail -f logs/debug.log
```

## 📂 Project Structure

| Directory | Description |
|-----------|-------------|
| `./hg.py` | **Primary:** Unified Dashboard and session controller. |
| `tools/integration/` | **Core:** Optimization proxy, profile launcher, and wire-in logic. |
| `tools/video/` | **Media:** Veo3 video generation and monitoring tools. |
| `config/` | Configuration fallback (Optional: `gemini_keys.json`). |
| `windsurf_profiles/` | Environment profiles for persistent Windsurf integration. |

## 📖 Documentation
- [Re-Installation & Re-Wiring Guide](docs/guides/RE-INSTALLATION.md)
- [Windsurf Integration Guide](docs/guides/WINDSURF_INTEGRATION.md)
- [Complete Savings Analysis](docs/analysis/COMPLETE_ANALYSIS.md)

---
*HIGH-GRAVITY: Unrestricted Optimization for Advanced Research.*
