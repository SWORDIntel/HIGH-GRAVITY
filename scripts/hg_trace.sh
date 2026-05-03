#!/bin/bash
# HIGH-GRAVITY Trace Watch
# Focused watcher for the prompt/completion path:
# - UI/session
# - extension host / Cascade
# - ACP auth
# - proxy/completions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SECONDS_TO_WATCH=60
FOLLOW=0
SHOW_NOISE=0
declare -A SEEN_KIND=()
declare -A FIRST_LINE=()
declare -A FIRST_SOURCE=()
declare -A KIND_COUNT=()

usage() {
    cat <<'USAGE'
Usage: ./hg.sh trace [seconds|--follow]
       ./hg.sh doctor --watch [seconds|--follow]

Options:
  --follow      Keep watching until interrupted
  --seconds N   Watch for N seconds (default: 60)
  --show-noise  Also print unleash polling lines
USAGE
}

while [ $# -gt 0 ]; do
    case "$1" in
        --follow|-f)
            FOLLOW=1
            ;;
        --seconds)
            shift
            [ $# -gt 0 ] || { echo "Missing value for --seconds" >&2; exit 1; }
            SECONDS_TO_WATCH="$1"
            ;;
        --show-noise)
            SHOW_NOISE=1
            ;;
        -h|--help|help)
            usage
            exit 0
            ;;
        *)
            if [[ "$1" =~ ^[0-9]+$ ]]; then
                SECONDS_TO_WATCH="$1"
            else
                echo "Unknown option: $1" >&2
                usage
                exit 1
            fi
            ;;
    esac
    shift || true
done

if [ "$FOLLOW" -eq 1 ]; then
    SECONDS_TO_WATCH=0
fi

session_root() {
    local latest
    latest="$(find "$HOME/.config/Windsurf - Next/logs" -maxdepth 1 -type d -name '20*' 2>/dev/null | sort | tail -1)"
    [ -n "$latest" ] && printf '%s\n' "$latest"
}

file_lines() {
    local file="$1"
    [ -f "$file" ] && wc -l < "$file" || echo 0
}

classify_line() {
    local line="$1"
    case "$line" in
        *GetStreamingCompletions*)
            echo "proxy/completion"
            ;;
        *AcknowledgeCascadeCodeEdit*|*GetCodeMapSuggestions*)
            echo "exthost/cascade"
            ;;
        *"[CASCADE TRACE]"*|*"cascade_hook_trace.jsonl"*)
            echo "hook/cascade"
            ;;
        *"agent_action_name"*|*"trajectory_id"*|*"execution_id"*|*"tool_info_keys"*)
            echo "hook/cascade"
            ;;
        *GetUserStatus*|*GetCliTeamSettings*|*GetCliModelConfigs*)
            echo "proxy/auth"
            ;;
        *"Model is disposed!"*|*"file was not found"*|*"ECONNRESET"*|*"unresponsive extension host"*|*"failed to fetch plan info"*|*"Connection failed"*|*"Authentication failed"* )
            echo "error"
            ;;
        *)
            echo ""
            ;;
    esac
}

kind_label() {
    local kind="$1"
    case "$kind" in
        proxy/completion) echo "completion" ;;
        exthost/cascade) echo "cascade" ;;
        hook/cascade) echo "cascade-hook" ;;
        proxy/auth) echo "auth" ;;
        error) echo "error" ;;
        *) echo "$kind" ;;
    esac
}

record_hit() {
    local kind="$1"
    local source="$2"
    local line="$3"

    KIND_COUNT["$kind"]=$(( ${KIND_COUNT["$kind"]:-0} + 1 ))
    if [ -z "${SEEN_KIND["$kind"]+x}" ]; then
        SEEN_KIND["$kind"]=1
        FIRST_SOURCE["$kind"]="$source"
        FIRST_LINE["$kind"]="$line"
        printf '[%s] FIRST %s [%s] %s\n' "$(date +%H:%M:%S)" "$(kind_label "$kind")" "$source" "$line"
    fi
}

print_delta() {
    local label="$1"
    local file="$2"
    local previous="$3"
    local current="$4"
    local delta
    local line
    local kind

    [ "$current" -gt "$previous" ] || return 0

    delta="$(tail -n "$((current - previous))" "$file" 2>/dev/null || true)"
    [ -n "$delta" ] || return 0

    while IFS= read -r line; do
        [ -n "$line" ] || continue

        if [ "$SHOW_NOISE" -eq 0 ]; then
            case "$line" in
                *"/unleash/client/metrics"*|*"/unleash/client/features"*|*"/unleash/client/register"*)
                    continue
                    ;;
            esac
        fi

        kind="$(classify_line "$line")"
        if [ -n "$kind" ]; then
            record_hit "$kind" "$label" "$line"
        elif [ "$SHOW_NOISE" -eq 1 ]; then
            printf '[%s] %s %s\n' "$(date +%H:%M:%S)" "$label" "$line"
        fi
    done <<< "$delta"
}

echo -e "${CYAN}HIGH-GRAVITY Trace Watch${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

current_session=""
declare -A FILES
declare -A COUNTS

start_session_watch() {
    local root="$1"
    FILES=(
        [proxy]="logs/proxy.log"
        [proxy_https]="logs/proxy_https.log"
        [cascade_midway]="logs/cascade_midway.log"
        [cascade_hook]="logs/cascade_hook_trace.jsonl"
        [renderer]="$root/window1/renderer.log"
        [main]="$root/main.log"
        [exthost]="$root/window1/exthost/codeium.windsurf/Windsurf.log"
        [acp]="$root/window1/exthost/codeium.windsurf/Windsurf ACP summary-agent.log"
        [network]="$root/window1/network.log"
        [edit]="$root/editSessions.log"
    )

    COUNTS=()
    echo -e "${GREEN}Active session:${NC} $(basename "$root")"
    echo -e "${GREEN}Watching:${NC}"
    printf '  %s\n' "${FILES[proxy]}" "${FILES[proxy_https]}" "${FILES[cascade_midway]}" "${FILES[cascade_hook]}" "${FILES[renderer]}" "${FILES[main]}" "${FILES[exthost]}" "${FILES[acp]}" "${FILES[network]}" "${FILES[edit]}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    for label in "${!FILES[@]}"; do
        COUNTS["$label"]="$(file_lines "${FILES[$label]}")"
    done
}

start_ts="$(date +%s)"

while :; do
    latest="$(session_root || true)"
    if [ -z "${latest:-}" ]; then
        sleep 2
        continue
    fi

    if [ "$current_session" != "$latest" ]; then
        current_session="$latest"
        start_session_watch "$current_session"
    fi

    for label in "${!FILES[@]}"; do
        file="${FILES[$label]}"
        current="$(file_lines "$file")"
        previous="${COUNTS[$label]:-0}"
        if [ "$current" -gt "$previous" ]; then
            print_delta "$label" "$file" "$previous" "$current"
            COUNTS["$label"]="$current"
        fi
    done

    if [ "$SECONDS_TO_WATCH" -gt 0 ]; then
        now="$(date +%s)"
        if [ $((now - start_ts)) -ge "$SECONDS_TO_WATCH" ]; then
            break
        fi
    fi

    sleep 2
done

echo ""
echo -e "${CYAN}Trace Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "${#SEEN_KIND[@]}" -eq 0 ]; then
    echo "No meaningful prompt/completion events observed."
else
    for kind in "${!SEEN_KIND[@]}"; do
        printf '%s: seen %s time(s), first from %s\n' \
            "$(kind_label "$kind")" \
            "${KIND_COUNT["$kind"]:-0}" \
            "${FIRST_SOURCE["$kind"]:-unknown}"
    done | sort
    echo ""
    echo "First-hit lines:"
    for kind in "${!SEEN_KIND[@]}"; do
        printf '  [%s] %s\n' "$(kind_label "$kind")" "${FIRST_LINE["$kind"]:-}"
    done | sort
fi
