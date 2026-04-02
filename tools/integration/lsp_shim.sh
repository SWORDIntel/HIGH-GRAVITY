#!/bin/bash
# High-Gravity LSP Shield (v3.3)
# Transparently forces proxy arguments and executes the real binary.

REAL_BIN="$(dirname "$0")/language_server_linux_x64.real"
PROXY_URL="http://localhost:9999"

# Rebuild arguments to force proxy
NEW_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --api_server_url|--inference_api_server_url)
            NEW_ARGS+=("$1")
            NEW_ARGS+=("$PROXY_URL")
            shift 2
            ;;
        --api_server_url=*)
            NEW_ARGS+=("--api_server_url=$PROXY_URL")
            shift
            ;;
        --inference_api_server_url=*)
            NEW_ARGS+=("--inference_api_server_url=$PROXY_URL")
            shift
            ;;
        *)
            NEW_ARGS+=("$1")
            shift
            ;;
    esac
done

# Execute real binary, replacing this shell process
exec "$REAL_BIN" "${NEW_ARGS[@]}"
