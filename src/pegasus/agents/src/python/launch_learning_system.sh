#!/bin/bash
# Quick launcher for the learning system

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "../../venv" ]; then
    source ../../venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
elif [ -f "../../.env" ]; then
    export $(cat ../../.env | grep -v '^#' | xargs)
fi

# Launch the PostgreSQL learning system
python3 postgresql_learning_system.py "$@"
