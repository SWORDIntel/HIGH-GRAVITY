#!/bin/bash
# HIGH-GRAVITY Pegasus Dashboard Launcher
# This script launches the Pegasus Dashboard.

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set the project root
PROJECT_ROOT="$DIR/.."

# Launch the Pegasus Dashboard
exec python3 "$PROJECT_ROOT/hg.py" "$@"
