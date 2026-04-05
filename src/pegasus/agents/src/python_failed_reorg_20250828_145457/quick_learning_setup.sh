#!/bin/bash
# Quick setup for learning system
export POSTGRES_PORT=5433
python3 "${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/python/setup_learning_system_enhanced.py"
