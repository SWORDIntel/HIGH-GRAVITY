#!/bin/bash
# HIGH-GRAVITY Shell Aliases
# Source this file: source hg_aliases.sh

HG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Dashboard
alias hg="$HG_ROOT/hg.sh"

# Windsurf launchers
alias hg-windsurf="$HG_ROOT/bin/gemini_session_launcher.py --mode windsurf --provider proxy --proxy-url http://localhost:9998"
alias hg-windsurf-k1="$HG_ROOT/bin/gemini_session_launcher.py --mode windsurf --provider proxy --proxy-url http://localhost:9998 --key-index 1"
alias hg-windsurf-k2="$HG_ROOT/bin/gemini_session_launcher.py --mode windsurf --provider proxy --proxy-url http://localhost:9998 --key-index 2"
alias hg-windsurf-k3="$HG_ROOT/bin/gemini_session_launcher.py --mode windsurf --provider proxy --proxy-url http://localhost:9998 --key-index 3"

# Gemini launchers
alias hg-studio="$HG_ROOT/bin/gemini_session_launcher.py --mode studio"
alias hg-studio-k1="$HG_ROOT/bin/gemini_session_launcher.py --mode studio --key-index 1"
alias hg-studio-k2="$HG_ROOT/bin/gemini_session_launcher.py --mode studio --key-index 2"
alias hg-chat="$HG_ROOT/bin/gemini_session_launcher.py --mode chat"
alias hg-chat-k1="$HG_ROOT/bin/gemini_session_launcher.py --mode chat --key-index 1"
alias hg-chat-k2="$HG_ROOT/bin/gemini_session_launcher.py --mode chat --key-index 2"

# Piped launcher
alias hg-pipe="$HG_ROOT/scripts/internal/launch_windsurf_piped.sh"

# Utilities
alias hg-keys="$HG_ROOT/bin/gemini_session_launcher.py --list"
alias hg-check="$HG_ROOT/bin/gemini_session_launcher.py --check"
alias hg-status="curl -s http://localhost:9998/hg/telemetry | jq"
alias hg-patch="python3 $HG_ROOT/src/patch_all.py"

# Proxy control
alias hg-proxy-start="python3 $HG_ROOT/tools/integration/highgravity_proxy.py &"
alias hg-proxy-stop="pkill -f highgravity_proxy.py"

# Quick launch functions
hg-launch() {
    local config="${1:-basic}"
    cat "$HG_ROOT/config/windsurf_launch_examples.json" | jq -r ".examples.$config.config" | $HG_ROOT/scripts/internal/launch_windsurf_piped.sh
}

hg-launch-json() {
    echo "$1" | $HG_ROOT/scripts/internal/launch_windsurf_piped.sh
}

echo "HIGH-GRAVITY aliases loaded!"
echo "Available commands:"
echo "  hg                     - Launch dashboard"
echo "  hg-windsurf            - Launch Windsurf with proxy"
echo "  hg-windsurf-k1/k2/k3   - Launch Windsurf with specific key"
echo "  hg-studio              - Launch Gemini AI Studio"
echo "  hg-studio-k1/k2        - Launch Studio with specific key"
echo "  hg-chat                - Launch Gemini Chat"
echo "  hg-chat-k1/k2          - Launch Chat with specific key"
echo "  hg-pipe                - Piped JSON launcher"
echo "  hg-keys                - List available keys"
echo "  hg-check               - Check key validity"
echo "  hg-status              - Check proxy status"
echo "  hg-patch               - Patch Windsurf client"
echo "  hg-launch <example>    - Launch from example config"
echo "  hg-launch-json '{...}' - Launch from JSON string"
