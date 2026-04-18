# HIGH-GRAVITY: Pegasus-Grade Autonomous Swarm & Proxy

## 🏁 Overview
HIGH-GRAVITY is a decentralized, high-performance cyber-intelligence gateway and autonomous agent mesh. It transforms standard AI interfaces into a coordinated swarm of 112+ specialized operatives, governed by a corporate-style hierarchy and hardened by quantum-inspired search and binary-level stealth protocols.

---

## 🏗️ System Architecture

### 1. The Pegasus Swarm (Intelligence Layer)
- **112+ Specialized Agents**: Organized into 12 functional divisions (Security, DevOps, Data Science, Language, etc.).
- **Corporate Governance**: Chain-of-command enforcement via `DelegationEngine` and real-time intervention via `VetoEngine`.
- **State Superposition**: Global memory-state synchronization across agents via high-speed RAM-disk checkpoints.

### 2. High-Gravity Proxy (Orchestration Layer)
- **Omni-Routing**: Intelligent model rotation between 16+ high-performance Claude and Gemini keys.
- **Geo-Distributed Network**: Integrated Mullvad WireGuard rotation (545+ global exit nodes) with Key-Tunnel Parity.
- **Autodidact Learning**: Real-time continuous training using the `autoresearch` loop, learning from every interaction.

### 3. Binary Infrastructure (Performance Layer)
- **UFP (Ultra-Fast Protocol)**: Lock-free binary communication bridge between proxy and agents (4.2M msg/sec).
- **QIHSE Acceleration**: Quantum-inspired Hilbert Space Expansion for sub-millisecond codebase indexing and retrieval.
- **MEMSHADOW (MSNET) Integration**: Gold Standard DPI evasion, traffic analysis resistance, and decentralized DHT discovery.

---

## 🚀 Deployment

### Core Launch
To initialize the High-Gravity control plane and the Pegasus Swarm:
```bash
python3 hg.py
```

### 8. 📊 Cybernetic Dashboard (`hg.py`)
*   **Full-Stack Monitor:** Live panels for proxy core, MITM bridge, premium upgrades (per-service + per-tier), Codex 4-tier reasoning distribution, rate-limit hits, and a recent-events feed.
*   **Per-Service Status Pills:** `GEMINI` / `CODEX` / `OPENAI` light up green the moment the bridge intercepts them, dim when enabled-but-idle, red when disabled.
*   **Inline Controls:** `C` clear ghost cache, `R` rotate keys, `Q` quit.

### 9. 🔄 MITM Bridge (API Auto-Interception)
*   **Automatic Service Detection:** Intelligently detects Gemini, Codex, and OpenAI requests by analyzing paths and headers.
*   **Tiered Premium Model Injection (2026):** Each legacy model maps to a `(fast, deep)` pair. Gemini `pro`/`1.5-pro` → `gemini-2.5-pro` / `gemini-3-pro-preview`; Codex `davinci-codex` → `gpt-5.3-codex-spark` / `gpt-5.1-codex-max`; OpenAI `gpt-4`/`gpt-4o` → `gpt-5.4-mini` / `gpt-5.4`.
*   **4-Tier Codex Reasoning Injection:** Per-request `reasoning_effort` (`low` / `medium` / `high` / `xhigh`) mirrors the Codex CLI picker, with matching Gemini `thinkingConfig.thinkingBudget` (`1024` / `8192` / `24576` / dynamic `-1`). `xhigh` is opted into via keywords like `exhaustive`, `formal proof`, `root cause analysis`.
*   **Rate Limit Reduction:** Removes rate-limit tracking headers and implements reduced cooldown periods (0.5s vs 1.0s).
*   **Seamless Integration:** Works transparently with Ghost Cache, Token Pool, Shadow Profiles, and all other HIGH-GRAVITY features.

---

## 🛡️ Hardening & Compliance
- **CNSA 2.0 Compliant**: Mandatory SHA-384 hashing for all data-at-rest and identity fingerprints.
- **MSNET Swarm**: Decentralized DHT discovery and DPI-evasive communication via the integrated `memshadow` protocol.
- **Telemetry Black-Hole**: Intercepts and mocks provider-side telemetry (Statsig, GrowthBook, Datadog) to preserve stealth.
- **Node Identity**: Current host is designated as a high-authority **HG-NODE** in the global MSHW mesh.

## 🚀 Quick Setup

1. **Quick Setup (Recommended):**
   ```bash
   ./scripts/hiz_setup.sh
   ```
   Follow the interactive menu to patch, wire, and launch. 

2. **Full Documentation:**
   See `docs/guides/HIZ_4_DUMMIES.md` for a comprehensive walkthrough.

3. **Manual Override:**
   If you need specific control, you can still run components individually:
   - **Deploy Shield:** `bash tools/integration/deploy_lsp_shim.sh`
   - **Launch Dashboard:** `python3 hg.py`
   - **Wire Project:** `python3 tools/integration/detect_and_wire_windsurf.py`

4. **Restart Windsurf:** Once the proxy is running, restart Windsurf to activate full isolation.

---

## 📂 Repository Structure
- `src/pegasus/`: Core swarm logic, agent divisions, and governance.
- `lib/protocols/`: Binary bridges for UFP and MEMSHADOW.
- `bin/`: Infiltration and launch scripts.
- `config/`: Hardened key storage and network configurations.
- `logs/`: High-resolution audit trails and proxy telemetry.

**Copyright © 2026 HIGH-GRAVITY Systems | Pegasus-Phase Operational**
