# HIGH-GRAVITY Foundational Mandates (v3.2)

## 1. Project Overview
HIGH-GRAVITY is an expert-tier identity proxy and optimization shield for Windsurf. Its mission is to maintain an "Unlimited" AI environment while ensuring absolute operational security (OPSEC) and sub-millisecond intelligence acceleration.

## 2. Foundational Mandates

### 🛡️ OPSEC First (The Redaction Mandate)
No local system identifiers may ever leave the local proxy unmasked.
*   **Username Redaction**: The local username (`john`) must be replaced with `[USER]`.
*   **Path Redaction**: All absolute Linux paths must be converted to `~` or `[REDACTED_PATH]`.
*   **Identity Isolation**: Every API key must use a unique **Shadow Profile** (randomized `sessionId`, `installationId`, and `deviceFingerprint`).
*   **Timing Jitter**: All upstream requests must include a randomized **5-45ms micro-delay** to defeat timing-based flow analysis.

### 🧠 Token Zero (The Efficiency Mandate)
All technical context must be "distilled" to maximize the relevance-to-token ratio.
*   **Code Minification**: Khoj snippets must strip comments (`#`, `//`) and docstrings.
*   **Whitespace Collapse**: Multi-space indentation and redundant newlines must be collapsed.
*   **Recursive Recovery**: If a technical query yields 0 RAG results, the bridge must automatically broaden the query to ensure context is never missing.

### ⚡ Heuristic Resilience (The Patching Mandate)
The system must survive Windsurf binary updates without manual offset re-calculation.
*   **Signature Discovery**: Binary patches must prioritize machine code signature scanning over hardcoded offsets.
*   **Validation Signature**: `49 39 d3 74 2e` (CMP R11, RDX; JE +0x2e).
*   **DNS Interception**: Domains that cannot be safely patched in the binary (due to length constraints) must be forcefully redirected via `/etc/hosts`.

## 3. Technical Architecture (AMI Pipeline)

The **Advanced Multi-Stage Intelligence (AMI)** pipeline provides tiered acceleration:
1.  **Stage 1 (Exact)**: O(1) hash lookup in RAM-resident dictionary.
2.  **Stage 2 (Prefix)**: Tiered interpolation search (**NOT_STISLA**) on sorted int64 hash prefixes.
3.  **Stage 3 (SIMD)**: Parallel prefix matching via **QIHSE** if Stage 2 is bypassed.
4.  **Stage 4 (Semantic)**: NumPy-vectorized bitwise XOR + popcount (**TurboQuant**) for approximate matching.

## 4. RPC & Quota Bypass Specification

To maintain "Unlimited" status, the proxy must forcefully spoof the following RPC responses:
*   **/CheckChatCapacity**: Must return `is_capable: True` and zeroed used credits.
*   **/api/oauth/usage**: Must return `monthly_limit: null` and `flex_credit_quota: 999999`.
*   **/GetUserStatus**: Must return `planTier: ENTERPRISE` and `subscriptionStatus: active`.

## 5. Intelligence Controls

*   **Anti-Rejection Mutator**: Intercepts prompts containing "risky" goals and reframes them into authorized security audits to bypass upstream safety filters.
*   **Proactive Trigger Engine**: Scans incoming AI streams for intent matches to automatically spawn specialized Pegasus agents.

---

**Current Strategic Baseline**: Windsurf Next v1.110.1-next
**Shield Status**: 🛡️ **WATERTIGHT** | **Intelligence**: 🧠 **OPTIMIZED**
