# HIGHGRAVITY

HIGHGRAVITY is an optimization layer for AI development workflows, specifically targeting Windsurf/Cascade and Gemini-driven media generation.

## 🚀 Quick Start

### 1. Unified Launcher & Midway Control
Use the root-level `launch.py` for all operations. For permanent "Midway" control (redirection & token optimization), you must patch the Windsurf client.

```bash
# Auto-Patch all Windsurf versions (Stable & Next)
./tools/integration/auto_modifier.sh

# Interactive mode (Select keys, modes, and launch)
./launch.py
```

### 2. Token Optimization & Identity Cloaking
HIGHGRAVITY provides an 80% cost reduction and enhanced privacy by intercepting traffic midway.
- **Canonical Ordering:** Alphabetically sorts context to maximize backend cache hits (Opus/Sonnet/DeepSeek).
- **Context Stripping:** Deduplicates large file blocks across session turns.
- **Identity Cloaking:** Randomizes fingerprints and IDs to prevent account-level tracking.
- **Tier Spoofing:** Impersonates Enterprise-tier priority for all requests.
- **Universal Models:** Optimized for **Claude 3.5 Sonnet**, **Claude 3 Opus**, **DeepSeek V3/R1**, **Gemini 1.5 Pro**, and **GPT-4o**.

### 3. Quick Integration
HIGHGRAVITY bridges Windsurf through an optimized proxy.

- **Auto-Wire:** Run `./tools/integration/detect_and_wire_windsurf.py` while Windsurf is open.
- **Manual Launch:** `./launch.py --mode windsurf --window-name my-project`

## 🎬 Veo Video Generation
Generate high-fidelity video using Gemini/Veo models with automatic key rotation.

```bash
# Generate video from a prompt
./tools/video/veo3_video_generator.py --prompt "Cinematic orbit of a futuristic city"

# Check status of pending jobs
./tools/video/check_video_status.py
```

## 📂 Project Structure

| Directory | Description |
|-----------|-------------|
| `tools/integration/` | **Core:** Launcher and Windsurf/Cascade wiring logic. |
| `tools/video/` | **Media:** Veo3 video generation and monitoring tools. |
| `tools/keys/` | **Security:** API key validation and health check utilities. |
| `config/` | Configuration templates (`gemini_keys.json`). |
| `docs/` | Technical analysis and detailed integration guides. |
| `windsurf_profiles/` | Generated environment profiles for Windsurf sessions. |

## 🛠 Advanced Usage

### Key Management
The system rotates through keys in `config/gemini_keys.json`. You can test all keys for validity:
```bash
./tools/keys/test_all_keys.py
```

### Savings Analysis
Based on internal modeling, the Windsurf + HIGHGRAVITY path delivers significant savings:
- **Windsurf alone:** ~15% reduction
- **Combined:** ~80% reduction ($36/mo → $7.20/mo per dev)
- *See `docs/analysis/COMPLETE_ANALYSIS.md` for details.*

### 📖 Documentation
- [Re-Installation & Re-Wiring Guide](docs/guides/RE-INSTALLATION.md)
- [Windsurf Integration Guide](docs/guides/WINDSURF_INTEGRATION.md)
- [Technical Analysis](docs/analysis/COMPLETE_ANALYSIS.md)

---
*Maintained by the HIGHGRAVITY team.*
