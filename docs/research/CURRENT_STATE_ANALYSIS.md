# HIGH-GRAVITY v3.2: Current State Analysis & Intelligence Recovery Plan

## 1. Executive Summary
The transition to Windsurf Next v1.110.1 introduced a mandatory binary protobuf protocol (`application/connect+proto`) for all critical RPCs. Our initial attempt to force the client back to JSON successfully enabled the intelligence layer (RAG/Cache) but caused a complete failure of the authentication and seat management subsystems, which have strict wire-format validation.

Currently, the system is in a "Relay-Only" state for binary traffic, which is stable for usage but lacks the expert-tier local intelligence features (Khoj RAG, TurboQuant Caching, Prompt Mutation).

## 2. Identified Problems

### A. The "Initializing Intelligence Layer" Hang
- **Symptom:** UI hangs or shows an initialization spinner indefinitely.
- **Root Cause:** In `src/proxy.py`, the `PROTO_SNIFF` logic uses a synchronous `re.findall` on potentially multi-megabyte request bodies. When a large plan or codebase is sent, this blocks the entire async event loop, delaying the LS heartbeat and causing the frontend to freeze.

### B. "Model Provider Unreachable" (Routing & Framing)
- **Symptom:** AI functions fail immediately with an "Unreachable" or "501 Not Implemented" error.
- **Root Cause 1 (Misrouting):** Metadata RPCs (like `GetModelStatuses`) were being incorrectly classified as "Inference" and sent to the inference cluster, which does not know how to handle them.
- **Root Cause 2 (Loopback):** The client targets `proxy.windsurf.com` (redirected to 127.0.0.1). The proxy was then trying to fetch from `https://proxy.windsurf.com`, creating an infinite loop.
- **Root Cause 3 (Framing):** Injected responses were being wrapped in gRPC-web framing even when the client requested raw binary protobuf, causing parse failures.

### C. "invalid wire-format" (Binary Corruption)
- **Symptom:** "Failed to log in: unmarshal into *seat_management_pb.GetUserStatusResponse: proto: cannot parse invalid wire-format data".
- **Root Cause:** An aggressive binary replacement (`b"FREE" -> b"PRO_"`) was corrupting random bytes in the protobuf stream that happened to match that 4-byte sequence.

## 3. Planned Fixes (Intelligence Recovery)

### Phase 1: Surgical Binary Intelligence
- **Protobuf Appender:** Implement a `BinaryProtoEncoder` that can surgically append new `ChatMessage` objects to the end of a binary `GetChatMessageRequest` without re-encoding the entire payload.
- **Binary Cache:** Hash the entire binary request body to enable sub-millisecond replay of cached binary completions.

### Phase 2: Async Forensics
- **Non-blocking Sniffing:** Move binary text extraction to a background thread to prevent UI hangs.
- **Targeted RAG:** Only trigger Khoj searches when the sniffer finds a high-confidence query marker in the binary stream.

### Phase 3: Perfected Routing
- **Native Target Selection:** Follow the client's intended `:authority` but resolve it to the real public IP using a local `ForceIPResolver`, breaking all loopbacks and 404s.

## 4. Emergency Action: Full Unpatch
To provide a clean slate for debugging, the system is being reverted to a **Zero-Touch** state.
- **Files:** All core JS and binary files restored from `.original` backups.
- **Networking:** `/etc/hosts` and `iptables` redirects purged.
- **Authentication:** All injected headers removed.

## 5. Protobuf Protocol Discovery (Bit-Perfect)
We have successfully cracked open the `application/connect+proto` traffic for `GetChatMessage`.

### GetChatMessageRequest (Top Level):
- **Tag 1 (Length-delimited)**: Metadata (OS, API Key, JWT).
- **Tag 2 (String)**: System Prompt ("You are Cascade...").
- **Tag 3 (Message, repeated)**: Conversation History.

### ChatMessage (Inside Tag 3):
- **Tag 2 (Enum)**: Role (1=USER, 2=ASSISTANT, 3=SYSTEM).
- **Tag 3 (String)**: Content.

### Injection Strategy:
To inject Khoj context, we will append a new **Tag 3** message to the end of the byte stream. This is valid because Tag 3 is a `repeated` field in Protobuf.
