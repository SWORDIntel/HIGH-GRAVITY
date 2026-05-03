# HIGH-GRAVITY: Windsurf Bypass Architecture

This document explains how the High-Gravity proxy maintains an "Unlimited" state and enables private models in the Windsurf editor.

## 1. The Core Strategy: "Safe Enterprise"
The system operates in a **Hybrid Mode** (governed by `HG_SAFE_MODE`).
*   **Native Path:** Uses your real Windsurf session for "safe" tasks (Login, Settings, Telemetry). This ensures your account remains active and you don't get "Unauthenticated" errors.
*   **Discovery Path:** Uses a pool of 19 discovery keys (`sk-ws-*` and `sk-ant-*`) for all AI completions. This bypasses any local quota limits on your primary account.

## 2. Strategic Interception Points
The proxy hijacks specific requests to trick the Windsurf UI:

### A. The Quota Meter (`/api/oauth/usage`)
*   **Action:** Intercepts GET requests.
*   **Spoof:** Returns `monthly_limit: null` and `is_enabled: true` for extra usage.
*   **Result:** The UI displays "Unlimited Extra Usage" and stops showing the "Quota Exhausted" warning.

### B. User Status (`GetUserStatus`)
*   **Action:** Intercepts RPC calls (JSON only).
*   **Spoof:** Returns `planTier: ENTERPRISE` and `subscriptionStatus: active`.
*   **Result:** Unlocks Enterprise-only features in the editor.

### C. Team Settings (`GetCliTeamSettings`)
*   **Action:** Intercepts RPC calls (JSON only).
*   **Spoof:** Enables feature flags like `priority_inference`, `unlimited_cascade_turns`, and `enable_deep_research`.

### D. Model Catalog (`GetCliModelConfigs`)
*   **Action:** Intercepts RPC calls (JSON only).
*   **Spoof:** Injects the **Private Model Surface** (Claude 4.5 Haiku, Sonnet, and Opus).
*   **Result:** These unreleased models appear at the bottom of your model list.

## 3. Header-Level Enforcement
Even when requests pass through to real servers, the proxy injects "Bypass Headers" into every response:
*   `anthropic-ratelimit-unified-status: allowed`
*   `anthropic-ratelimit-unified-7d-utilization: 0.1` (Forces 10% used)
*   **Reset Stripping:** All `*-reset` headers are removed so the UI doesn't show a countdown.

## 4. Smart Model Routing
When you fire a prompt, the proxy decides where to send it based on the model ID:
*   **Standard Models:** If your native session is exhausted, the proxy rotates to a discovery key.
*   **Private Models (Claude 4.5):** 
    *   If the proxy picks an **Anthropic key**, it remaps the request to the best public equivalent (e.g., Opus 4.5 -> Opus 3.5).
    *   If it picks a **Gemini key**, it remaps to `gemini-2.0-flash-exp`.

## 5. Protocol Integrity
The system is **Protocol-Aware**:
*   **JSON Requests:** Intercepted and modified.
*   **Binary Proto/Connect:** Allowed to pass through untouched (maintains login stability).
*   **Cross-Protocol:** Private model remapping only triggers if the client falls back to JSON, ensuring binary streams don't break.

## 6. Network Setup
*   **iptables:** Redirects local traffic from `50001` (patched LS port) to `9999` (proxy).
*   **TLS:** The proxy uses a multi-domain certificate (`proxy.windsurf.com`, `inferapi.windsurf.com`) to securely intercept HTTPS traffic.
*   **/etc/hosts:** Points specific domains to `127.0.0.1` so the proxy can catch the traffic.
