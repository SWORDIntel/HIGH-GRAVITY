# HIGH-GRAVITY Project Architecture

## Overview
HIGH-GRAVITY is a high-performance identity proxy, optimization shield, and intelligence gateway designed for the Windsurf editor. It provides a secure and efficient way to interact with AI models while maintaining total user privacy and unlocking enterprise-tier capabilities.

## Expert-Tier Systems (v3.2)

### 1. The Expert Shield
The shield operates at multiple layers to ensure maximum OPSEC and reliability:
*   **DNS Redirection**: Forces all Codeium and Windsurf telemetry/feature-flag domains to `127.0.0.1`, sealing all traffic leaks.
*   **CSEC Sentinel**: A real-time sanitization engine that redacts system paths, usernames, and local identifiers from AI prompts.
*   **Upstream Jitter**: Randomized micro-delays (5-45ms) that defeat timing-based proxy detection and traffic fingerprinting.
*   **Shadow Profiles**: Per-key isolation of sessions, installation IDs, and device fingerprints to prevent account cross-linking by upstream providers.

### 2. Multi-Stage Intelligence (AMI)
The intelligence layer uses a tiered acceleration pipeline for sub-millisecond lookups:
*   **Tier 1: NOT_STISLA**: Ultra-fast interpolation search on sorted hash prefixes.
*   **Tier 2: QIHSE**: SIMD-parallel search fallback for large-scale exact matching.
*   **Tier 3: TurboQuant**: A NumPy-vectorized ANN engine using bitwise XOR and popcount for semantic similarity matching.
*   **Deep RAG**: The Khoj bridge now features **Deep Intelligence Recovery**, automatically broadening queries and minifying code snippets to maximize token efficiency.

### 3. Anti-Rejection Engine
To prevent upstream models from refusing technical objectives:
*   **Trigger Obfuscation**: Replaces risky keywords (e.g., `bypass` → `traversal`) with benign technical synonyms.
*   **Semantic Reframing**: Automatically wraps sensitive prompts in an authorized "Security and Architectural Audit" context.

## Building and Running

### Commands
*   **Launch Dashboard**: `./hg.sh` (defaults to menu, or use `./hg.sh dashboard`).
*   **Full Start**: `./hg.sh start` (patches, starts proxy, starts RAG).
*   **Deep Audit**: `./hg.sh doctor` (verifies DNS, patches, and routing).

### Components
*   **Pegasus Dashboard**: Terminal-based Rich TUI for real-time control.
*   **FastAPI Proxy**: Zero-buffer streaming architecture for low-latency relay.
*   **Pegasus Swarm**: Collection of proactive agents monitoring the AI stream.

## Engineering Standards
*   **OPSEC First**: No identifiers or system data should ever leave the local proxy unmasked.
*   **Token Efficiency**: Technical context must be minified and whitespace-collapsed before injection.
*   **Heuristic Resilience**: All binary patches must support automated offset discovery to survive editor updates.

**Latest Verified Version**: Windsurf Next v1.110.1-next
