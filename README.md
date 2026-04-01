# HIGH-GRAVITY

HIGH-GRAVITY is an advanced optimization, privacy, and research layer for AI development workflows. It is specifically engineered to "wire-in" to the **Windsurf Next** / Cascade ecosystem, providing identity cloaking, refusal reduction, and massive cost efficiency.

## 🚀 The Dashboard (`./hg.py`)

The central hub for all HIGH-GRAVITY operations. It manages the local optimization proxy, monitors real-time traffic, and provides interactive control over your session.

```bash
# Start the Unified Dashboard
./hg.py
```

### Dashboard Actions:
- **[W] - Launch Windsurf Next**: Launches Windsurf with the HIGH-GRAVITY profile environment pre-loaded.
- **[P] - Start/Stop Proxy**: Manually toggle the optimization server (Port 9999).
- **[Q] - Quit**: Gracefully shuts down the dashboard and background proxy.

## 🛠 Core Features

### 1. Cybersecurity Abliteration (Refusal Reduction)
Optimized for technical research and vulnerability analysis. The proxy automatically:
- **Injects Unrestricted Persona**: Commands the model to operate in an unrestricted technical environment.
- **Mandates Technical Depth**: Forces detailed, technically exhaustive responses.
- **Bypasses Moralizing**: Strips away safety disclaimers and moralizing refusals for legitimate research tasks.

### 2. Identity Cloaking & Privacy
Prevent account-level tracking and data harvesting.
- **Dynamic Fingerprinting**: Randomizes device fingerprints, installation IDs, and session identifiers for every session.
- **Tier Spoofing**: Automatically elevates all requests to **ENTERPRISE_SAAS** status to ensure priority queueing and unlimited context.

### 3. Dynamic Session Discovery
No more manual key management.
- **Auto-Discovery**: The proxy captures authentic session keys directly from Windsurf traffic as they appear.
- **Universal Provider Support**: Transparently routes and optimizes traffic for **OpenAI, Anthropic, Gemini, DeepSeek, Mistral, Groq, OpenRouter, and Together**.

### 4. Token Optimization
Reduces LLM costs by up to 80% through:
- **Anthropic Caching**: Automatically tags large context blocks for ephemeral caching (Sonnet/Opus).
- **Context De-duplication**: Strips redundant tags before forwarding to upstream providers.

## 🎬 Veo Video Generation
High-fidelity video generation using Gemini/Veo models with automatic key rotation.

```bash
# Generate video from a prompt
./tools/video/veo3_video_generator.py --prompt "Cinematic orbit of a futuristic city"
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
