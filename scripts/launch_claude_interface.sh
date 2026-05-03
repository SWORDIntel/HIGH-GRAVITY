#!/bin/bash
# HIGH-GRAVITY Claude Code Interceptor
# Forces Claude CLI to use the local optimization proxy.

PROXY_URL="http://127.0.0.1:9999"

echo "[*] Injecting High-Gravity Uplink into Claude Code..."

# Force proxy via environment variables
export HTTP_PROXY="$PROXY_URL"
export HTTPS_PROXY="$PROXY_URL"
export http_proxy="$PROXY_URL"
export https_proxy="$PROXY_URL"

# Disable strict SSL if using self-signed certs in proxy (if applicable)
export NODE_TLS_REJECT_UNAUTHORIZED=0

# Launch claude cli
exec claude "$@"
