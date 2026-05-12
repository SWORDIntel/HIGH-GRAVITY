#!/bin/bash
# High-Gravity LSP Shield (v3.4)
# Transparently forces proxy arguments and executes the real binary.

REAL_BIN="$(dirname "$0")/language_server_linux_x64.real"
PROXY_URL="${HG_PROXY_URL:-https://proxy.windsurf.com}"
PROXY_MODE="${HG_PROXY_MODE:-full}"
UNIQUE_DATABASE="${HG_LSP_UNIQUE_DATABASE:-1}"

# Rebuild arguments to force proxy
NEW_ARGS=()
DB_ARG_INDEX=-1
WORKSPACE_ID=""
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
        --database_dir)
            NEW_ARGS+=("$1")
            DB_ARG_INDEX=${#NEW_ARGS[@]}
            NEW_ARGS+=("$2")
            shift 2
            ;;
        --database_dir=*)
            DB_ARG_INDEX=${#NEW_ARGS[@]}
            NEW_ARGS+=("$1")
            shift
            ;;
        --workspace_id)
            NEW_ARGS+=("$1")
            WORKSPACE_ID="$2"
            NEW_ARGS+=("$2")
            shift 2
            ;;
        --workspace_id=*)
            WORKSPACE_ID="${1#--workspace_id=}"
            NEW_ARGS+=("$1")
            shift
            ;;
        *)
            NEW_ARGS+=("$1")
            shift
            ;;
    esac
done

if [[ "$UNIQUE_DATABASE" =~ ^(1|true|TRUE|yes|YES|on|ON)$ ]] &&
   [[ "$DB_ARG_INDEX" -ge 0 ]] &&
   [[ -n "$WORKSPACE_ID" ]]; then
    if command -v sha256sum >/dev/null 2>&1; then
        DB_SUFFIX="$(printf '%s' "$WORKSPACE_ID" | sha256sum | awk '{print substr($1,1,16)}')"
    else
        DB_SUFFIX="$(printf '%s' "$WORKSPACE_ID" | cksum | awk '{print $1}')"
    fi
    if [[ "${NEW_ARGS[$DB_ARG_INDEX]}" == --database_dir=* ]]; then
        DB_PATH="${NEW_ARGS[$DB_ARG_INDEX]#--database_dir=}"
        NEW_ARGS[$DB_ARG_INDEX]="--database_dir=${DB_PATH}.${DB_SUFFIX}"
    else
        DB_PATH="${NEW_ARGS[$DB_ARG_INDEX]}"
        NEW_ARGS[$DB_ARG_INDEX]="${DB_PATH}.${DB_SUFFIX}"
    fi
fi

# Execute real binary, replacing this shell process
exec "$REAL_BIN" "${NEW_ARGS[@]}"
