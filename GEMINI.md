# HIGH-GRAVITY Foundational Mandates (v4.0)

## 1. Project Overview
HIGH-GRAVITY is an expert-tier identity proxy and optimization shield for Windsurf. Its mission is to maintain an "Unlimited" AI environment while ensuring absolute operational security (OPSEC) and sub-millisecond intelligence acceleration.

## 2. Foundational Mandates

### 🛡️ OPSEC First (The Redaction Mandate)
No local system identifiers may ever leave the local proxy unmasked.
*   **Username Redaction**: The local username (`john`) must be replaced with `[USER]`.
*   **Path Redaction**: All absolute Linux paths must be converted to `~` or `[REDACTED_PATH]`.
*   **Identity Isolation**: Every API key must use a unique **Shadow Profile** (randomized `sessionId`, `installationId`, and `deviceFingerprint`).
*   **Timing Jitter**: All upstream requests must include a randomized **5-45ms micro-delay** to defeat timing-based flow analysis.
*   **Hook Resilience**: All session hooks (Cascade, Claude-mem) must be self-healing and fail-safe.

### 🧠 Token Zero (The Efficiency Mandate)
All technical context must be "distilled" to maximize the relevance-to-token ratio.
*   **Code Minification**: Khoj snippets must strip comments (`#`, `//`) and docstrings.
*   **Whitespace Collapse**: Multi-space indentation and redundant newlines must be collapsed.

### ⚡ Heuristic Resilience (The Patching Mandate)
The system must survive Windsurf binary updates without manual offset re-calculation.
*   **Multi-Point Signature Discovery**: Binary patches must prioritize machine code signature scanning over hardcoded offsets.
*   **Dynamic DNS Discovery**: Hardcoded IP addresses and `/etc/hosts` overrides are strictly prohibited. The egress shield MUST dynamically resolve upstream endpoints (`proxy.windsurf.com`, `inference.codeium.com`, etc.) via an authoritative DNS server (e.g., `1.1.1.1`) at runtime and inject those live IPs into the `iptables` NAT chain. This prevents DNS loops and ensures resilience against upstream infrastructure rotation.

## 3. Technical Architecture (AMI Pipeline)

The **Advanced Multi-Stage Intelligence (AMI)** pipeline provides tiered acceleration and verification:
0.  **Stage 0 (Kernel)**: eBPF-based socket classification to detect and alert on proxy-bypass attempts in real-time.
1.  **Stage 1 (Exact)**: O(1) hash lookup in RAM-resident dictionary.
2.  **Stage 2 (Prefix)**: Tiered interpolation search (**NOT_STISLA**) on sorted int64 hash prefixes.
3.  **Stage 3 (SIMD)**: Parallel prefix matching via **QIHSE** if Stage 2 is bypassed.
4.  **Stage 4 (Semantic)**: NumPy-vectorized bitwise XOR + popcount (**TurboQuant**) for approximate matching.

## 4. RPC & Quota Bypass Specification

To maintain "Unlimited" status and prevent IDE crashes, the proxy must adhere to strict schema compliance:
*   **/GetUserStatus**: MUST be spoofed using a genuine, full-length production payload (The "Golden Payload", approx. 71KB) hot-patched to `ENTERPRISE`. Minimal, manually-constructed byte arrays (e.g., 18-bytes) will cause severe unmarshalling crashes (`invalid wire-format`) or undefined behavior in the IDE's Javascript client.
*   **/GetProfileData**: MUST pass through to the genuine upstream server using a valid native token. Do not locally mock or hot-patch this endpoint, as disrupting the complex OAuth/User ID metadata will break the IDE's logout button and session state.
*   **Telemetry Throttling**: The Windsurf IDE will trigger an internal `CASCADE_ERROR_STEP` and halt inference if `RecordCortexTrajectoryStep` metadata exceeds internal buffer limits. The proxy MUST locally acknowledge (`200 OK` + 5-byte Connect frame) these massive payloads to prevent upstream rate-limiting while allowing the IDE to flush its context.

## 5. Intelligence Controls

*   **Anti-Rejection Mutator**: Intercepts prompts containing "risky" goals and reframes them into authorized security audits.
*   **Proactive Trigger Engine**: Scans incoming AI streams for intent matches to automatically spawn specialized Pegasus agents.

---

**Current Strategic Baseline**: Windsurf Next v2.3.1008
**Shield Status**: 🛡️ **DYNAMIC SHIELD ACTIVE** | **Intelligence**: 🧠 **PASSIVE MONITORING ENABLED**