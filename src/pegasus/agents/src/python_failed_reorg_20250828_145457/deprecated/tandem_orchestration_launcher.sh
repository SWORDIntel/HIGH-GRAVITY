#!/bin/bash
# Minimal Tandem Orchestrator Launcher
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CLAUDE_AGENTS_ROOT="${CLAUDE_AGENTS_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
export PYTHONPATH="${CLAUDE_AGENTS_ROOT}/src/python:${PYTHONPATH}"

echo "Starting Tandem Orchestration System..."
cd "${CLAUDE_AGENTS_ROOT}/src/python"

python3 -c "
import asyncio
from production_orchestrator import ProductionOrchestrator

async def start():
    orchestrator = ProductionOrchestrator()
    await orchestrator.initialize()
    print(f'✓ System online with {len(orchestrator.list_available_agents())} agents')

asyncio.run(start())
"
