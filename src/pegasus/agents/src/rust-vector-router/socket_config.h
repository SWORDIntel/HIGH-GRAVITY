#ifndef SOCKET_CONFIG_H
#define SOCKET_CONFIG_H

// Runtime socket path (not in /tmp due to noexec)
#define SOCKET_PATH "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../06-BUILD-RUNTIME/runtime/claude_agent_bridge.sock"
#define FALLBACK_SOCKET_PATH "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../06-BUILD-RUNTIME/runtime/agent_bridge.sock"

#endif
