#!/bin/bash
export POSTGRES_PORT=5433
export POSTGRES_DB=claude_auth
export POSTGRES_USER=claude_auth
export POSTGRES_PASSWORD=claude_auth_pass

echo "Learning System Status"
echo "====================="
python3 "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/python/learning_cli.py" status
