#!/bin/bash
# Dynamic Path Discovery Helper for Claude Agents
# This script provides consistent path resolution across the entire agent ecosystem

# Detect the project root dynamically
if [ -z "$CLAUDE_PROJECT_ROOT" ]; then
    # Try to find project root by looking for characteristic files
    current_dir="$(pwd)"
    script_dir="$(dirname "$(readlink -f "$0")")"

    # Check if we're in the agents directory
    if [ -f "$script_dir/TEMPLATE.md" ] && [ -d "$script_dir/src" ]; then
        export CLAUDE_PROJECT_ROOT="$(dirname "$script_dir")"
        export CLAUDE_AGENTS_ROOT="$script_dir"
    # Check if we're in project root
    elif [ -f "$script_dir/CLAUDE.md" ] && [ -d "$script_dir/agents" ]; then
        export CLAUDE_PROJECT_ROOT="$script_dir"
        export CLAUDE_AGENTS_ROOT="$script_dir/agents"
    # Try going up one level
    elif [ -f "$(dirname "$script_dir")/CLAUDE.md" ]; then
        export CLAUDE_PROJECT_ROOT="$(dirname "$script_dir")"
        export CLAUDE_AGENTS_ROOT="$CLAUDE_PROJECT_ROOT/agents"
    else
        # Fallback: assume standard structure
        export CLAUDE_PROJECT_ROOT="$(dirname "$script_dir")"
        export CLAUDE_AGENTS_ROOT="$script_dir"
    fi
fi

# Set default environment variables if not already set
export CLAUDE_AGENTS_ROOT="${CLAUDE_AGENTS_ROOT:-$CLAUDE_PROJECT_ROOT/agents}"
export CLAUDE_BINARY="${CLAUDE_BINARY:-claude}"
export OPENVINO_ROOT="${OPENVINO_ROOT:-${OPENVINO_ROOT:-/opt/openvino/}}"
export CLAUDE_LOG_DIR="${CLAUDE_LOG_DIR:-${CLAUDE_LOG_DIR:-/var/log/claude-agents/}}"

# Function to resolve agent-relative paths
resolve_agent_path() {
    local relative_path="$1"
    echo "$CLAUDE_AGENTS_ROOT/$relative_path"
}

# Function to resolve project-relative paths
resolve_project_path() {
    local relative_path="$1"
    echo "$CLAUDE_PROJECT_ROOT/$relative_path"
}

# Export functions for use in other scripts
export -f resolve_agent_path
export -f resolve_project_path

# Print current configuration if requested
if [ "$1" = "--show-config" ]; then
    echo "CLAUDE_PROJECT_ROOT: $CLAUDE_PROJECT_ROOT"
    echo "CLAUDE_AGENTS_ROOT: $CLAUDE_AGENTS_ROOT"
    echo "CLAUDE_BINARY: $CLAUDE_BINARY"
    echo "OPENVINO_ROOT: $OPENVINO_ROOT"
    echo "CLAUDE_LOG_DIR: $CLAUDE_LOG_DIR"
fi
