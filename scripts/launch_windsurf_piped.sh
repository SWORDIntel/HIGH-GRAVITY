#!/bin/bash
# Launch Windsurf with HIGH-GRAVITY proxy using piped configuration
# Usage examples:
#   echo '{"mode":"windsurf","provider":"proxy"}' | ./launch_windsurf_piped.sh
#   cat config.json | ./launch_windsurf_piped.sh
#   ./launch_windsurf_piped.sh --mode windsurf --provider proxy

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="$SCRIPT_DIR/gemini_session_launcher.py"

# If stdin is a pipe, pass it through with --stdin-format json
if [ ! -t 0 ]; then
    python3 "$LAUNCHER" --stdin-format json "$@"
else
    # No pipe, just use CLI args
    python3 "$LAUNCHER" "$@"
fi
