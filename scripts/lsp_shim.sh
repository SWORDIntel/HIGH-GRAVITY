#!/bin/bash
# High-Gravity LSP Shield (v3.3)
# Transparently forces proxy arguments and executes the real binary.

REAL_BIN="$(dirname "$0")/language_server_linux_x64.real"
PROXY_URL="${HG_PROXY_URL:-https://proxy.windsurf.com}"
PROXY_MODE="${HG_PROXY_MODE:-full}"

# Rebuild arguments to force proxy
NEW_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --api_server_url)
            NEW_ARGS+=("$1")
            if [[ "$PROXY_MODE" == "full" ]]; then
                NEW_ARGS+=("$PROXY_URL")
            else
                NEW_ARGS+=("$2")
            fi
            shift 2
            ;;
        --inference_api_server_url)
            NEW_ARGS+=("$1")
            NEW_ARGS+=("$PROXY_URL")
            shift 2
            ;;
        --api_server_url=*)
            if [[ "$PROXY_MODE" == "full" ]]; then
                NEW_ARGS+=("--api_server_url=$PROXY_URL")
            else
                NEW_ARGS+=("$1")
            fi
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
