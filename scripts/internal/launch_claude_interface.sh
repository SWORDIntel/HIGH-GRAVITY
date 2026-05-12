#!/bin/bash
# HIGH-GRAVITY Claude Code Interceptor
# Forces Claude CLI to use the local optimization proxy.

PROXY_URL="http://127.0.0.1:9998"
USER_HOME="${SUDO_HOME:-${HOME:-/home/john}}"
if [ -n "${SUDO_USER:-}" ] && [ -d "/home/$SUDO_USER" ]; then
    USER_HOME="/home/$SUDO_USER"
fi
export HOME="$USER_HOME"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$USER_HOME/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$USER_HOME/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$USER_HOME/.local/share}"
export PATH="$USER_HOME/.npm-global/bin:$USER_HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

echo "[*] Injecting High-Gravity Uplink into agent CLI..."

# Force proxy via environment variables
export HTTP_PROXY="$PROXY_URL"
export HTTPS_PROXY="$PROXY_URL"
export http_proxy="$PROXY_URL"
export https_proxy="$PROXY_URL"

# Disable strict SSL if using self-signed certs in proxy (if applicable)
export NODE_TLS_REJECT_UNAUTHORIZED=0

prompt=""
if [ "${1:-}" = "-p" ] || [ "${1:-}" = "--prompt" ]; then
    prompt="${2:-}"
fi

if [ -n "${HG_AGENT_CLI:-}" ]; then
    exec "$HG_AGENT_CLI" "$@"
elif command -v claude >/dev/null 2>&1; then
    exec claude "$@"
elif command -v gemini >/dev/null 2>&1; then
    if [ -n "$prompt" ]; then
        exec gemini --prompt "$prompt" --approval-mode auto_edit
    fi
    exec gemini "$@"
elif command -v codex >/dev/null 2>&1; then
    if [ -n "$prompt" ]; then
        exec codex exec "$prompt"
    fi
    exec codex "$@"
fi

echo "No supported agent CLI found. Install claude, gemini, codex, or set HG_AGENT_CLI." >&2
exit 127
