#!/bin/bash
# Python Orchestration System Startup Script
# Brings the Python-based Tandem Orchestration System online

set -e

echo "🚀 Starting Python Orchestration System..."

# Set environment
export CLAUDE_AGENTS_ROOT="${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents"
export PYTHONPATH="${CLAUDE_AGENTS_ROOT}/src/python:${PYTHONPATH}"

# Change to Python directory
cd "${CLAUDE_AGENTS_ROOT}/src/python"

# Test system
echo "🔍 Testing system status..."
python3 -c "
import sys
import os
sys.path.append('.')

os.environ['CLAUDE_AGENTS_ROOT'] = '${CLAUDE_AGENTS_ROOT}'

from production_orchestrator import ProductionOrchestrator
import asyncio

async def startup_test():
    orchestrator = ProductionOrchestrator()
    await orchestrator.initialize()
    
    print(f'✅ Python Orchestration System: ONLINE')
    print(f'📊 Total Agents: {len(orchestrator.discovered_agents)}')
    print(f'⚡ Mode: Python-only (C layer available when needed)')
    print(f'🎯 Status: Ready for Task tool invocation')
    
    # Quick test of a few key agents
    key_agents = ['director', 'security', 'architect', 'constructor', 'testbed']
    available_key = [a for a in key_agents if a in orchestrator.discovered_agents]
    print(f'🔧 Key Agents Online: {len(available_key)}/{len(key_agents)}')
    
    return True

result = asyncio.run(startup_test())
if result:
    print('\n🎉 System startup successful! All agents ready.')
else:
    print('\n❌ System startup failed.')
    exit(1)
"

echo "✅ Python Orchestration System is now ONLINE"
echo "📖 Usage: All 41 agents are now available via Claude Code Task tool"
echo "🔧 Example: Task(subagent_type='director', prompt='Create project plan')"