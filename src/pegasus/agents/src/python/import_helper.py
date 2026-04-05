#!/usr/bin/env python3
"""Helper script to update imports in your code"""

# Old import style
# from director_impl import DirectorAgent

# New import style
from claude_agents.implementations.core.director import DirectorAgent

# Quick reference:
IMPORT_MAPPING = {
    # Orchestration
    "production_orchestrator": "claude_agents.orchestration.production_orchestrator",
    "tandem_orchestrator": "claude_agents.orchestration.tandem_orchestrator",
    "agent_registry": "claude_agents.orchestration.agent_registry",
    # Core agents
    "director_impl": "claude_agents.implementations.core.director",
    "architect_impl": "claude_agents.implementations.core.architect",
    "security_impl": "claude_agents.implementations.security.security",
    # Learning
    "learning_orchestrator_bridge": "claude_agents.learning.learning_orchestrator_bridge",
    "postgresql_learning_system": "claude_agents.learning.postgresql_learning_system",
}


def update_import(old_import_line):
    """Convert old import to new format"""
    for old, new in IMPORT_MAPPING.items():
        if old in old_import_line:
            return old_import_line.replace(old, new)
    return old_import_line


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        print(update_import(sys.argv[1]))
    else:
        print("Import mapping reference:")
        for old, new in IMPORT_MAPPING.items():
            print(f"  {old:30} -> {new}")
