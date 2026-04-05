---
name: Reorganization Plan
---
# Python Source Code Reorganization Plan

## Current Issues
- 70+ files in single directory with no clear hierarchy
- Mixed purposes: implementations, utilities, configs, docs
- No package structure (`__init__.py` files)
- Difficult imports and module discovery
- Virtual environment mixed with source code

## Proposed Package Structure

```
agents/src/python/
├── __init__.py                    # Main package init
├── claude_agents/                 # Main package
│   ├── __init__.py               # Package exports
│   │
│   ├── implementations/          # Agent implementations
│   │   ├── __init__.py
│   │   ├── core/                # Core agents
│   │   │   ├── __init__.py
│   │   │   ├── director.py
│   │   │   ├── architect.py
│   │   │   ├── constructor.py
│   │   │   └── ...
│   │   │
│   │   ├── security/            # Security agents
│   │   │   ├── __init__.py
│   │   │   ├── security.py
│   │   │   ├── bastion.py
│   │   │   ├── cso.py
│   │   │   └── ...
│   │   │
│   │   ├── development/         # Development agents
│   │   │   ├── __init__.py
│   │   │   ├── debugger.py
│   │   │   ├── linter.py
│   │   │   ├── testbed.py
│   │   │   └── ...
│   │   │
│   │   ├── language/            # Language-specific agents
│   │   │   ├── __init__.py
│   │   │   ├── python_internal.py
│   │   │   ├── c_internal.py
│   │   │   ├── rust.py
│   │   │   ├── matlab.py
│   │   │   └── ...
│   │   │
│   │   ├── infrastructure/      # Infrastructure agents
│   │   │   ├── __init__.py
│   │   │   ├── docker.py
│   │   │   ├── deployer.py
│   │   │   ├── monitor.py
│   │   │   └── ...
│   │   │
│   │   ├── platform/            # Platform agents
│   │   │   ├── __init__.py
│   │   │   ├── web.py
│   │   │   ├── mobile.py
│   │   │   ├── tui.py
│   │   │   ├── pygui.py
│   │   │   └── ...
│   │   │
│   │   └── specialized/         # Specialized agents
│   │       ├── __init__.py
│   │       ├── quantum.py
│   │       ├── mlops.py
│   │       ├── datascience.py
│   │       └── ...
│   │
│   ├── orchestration/            # Orchestration systems
│   │   ├── __init__.py
│   │   ├── tandem_orchestrator.py
│   │   ├── production_orchestrator.py
│   │   ├── agent_registry.py
│   │   ├── database_orchestrator.py
│   │   └── learning_orchestrator.py
│   │
│   ├── bridges/                  # Bridge and integration modules
│   │   ├── __init__.py
│   │   ├── binary_bridge.py
│   │   ├── claude_bridge.py
│   │   ├── learning_bridge.py
│   │   └── protocol_server.py
│   │
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── base_agent.py        # Base agent class
│   │   ├── agent_loader.py
│   │   ├── health_monitor.py
│   │   ├── cache.py
│   │   └── metrics.py
│   │
│   ├── utils/                    # Utility functions
│   │   ├── __init__.py
│   │   ├── parallel.py          # Parallel processing
│   │   ├── async_io.py
│   │   ├── cpu_affinity.py
│   │   └── helpers.py
│   │
│   ├── voice/                    # Voice system
│   │   ├── __init__.py
│   │   ├── voice_input.py
│   │   ├── voice_toggle.py
│   │   └── quick_voice.py
│   │
│   └── cli/                      # CLI tools
│       ├── __init__.py
│       ├── learning_cli.py
│       ├── simple_cli.py
│       └── status.py
│
├── config/                       # Configuration files
│   ├── __init__.py
│   ├── logging.yaml
│   ├── requirements.txt
│   └── settings.py
│
├── tests/                        # Test files
│   ├── __init__.py
│   ├── test_agents/
│   ├── test_orchestration/
│   └── test_integration.py
│
├── docs/                         # Documentation (move .md files)
│   ├── ARCHITECTURE.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── ...
│
├── scripts/                      # Standalone scripts
│   ├── install_integration.py
│   ├── create_missing_agents.py
│   └── analyze_status.py
│
└── venv_production/             # Keep separate (not in package)
```

## Key Benefits

1. **Clear Organization**: Each module type has its own directory
2. **Proper Imports**: 
   ```python
   from claude_agents.implementations.core import Director
   from claude_agents.orchestration import TandemOrchestrator
   from claude_agents.utils.parallel import ParallelExecutor
   ```
3. **Module Discovery**: `__init__.py` files expose public APIs
4. **Namespace Isolation**: No more naming conflicts
5. **Easy Testing**: Test structure mirrors source structure
6. **Better IDE Support**: IDEs can understand package structure

## Implementation Steps

### Phase 1: Create Directory Structure
```bash
# Create main package directories
mkdir -p claude_agents/{implementations,orchestration,bridges,core,utils,voice,cli}
mkdir -p claude_agents/implementations/{core,security,development,language,infrastructure,platform,specialized}
mkdir -p {config,tests,docs,scripts}
```

### Phase 2: Move Files to Appropriate Locations
- Move `*_impl.py` files to `implementations/` subdirectories
- Move orchestration files to `orchestration/`
- Move bridge files to `bridges/`
- Move utility files to `utils/`
- Move voice files to `voice/`
- Move CLI files to `cli/`

### Phase 3: Create `__init__.py` Files
Each `__init__.py` will expose the public API:

```python
# claude_agents/__init__.py
"""Claude Agent Framework - Main Package"""

__version__ = "8.0.0"

# Core exports
from .core.base_agent import BaseAgent
from .core.agent_loader import AgentLoader

# Orchestration exports  
from .orchestration import TandemOrchestrator, ProductionOrchestrator

# Quick agent access
from .implementations import get_agent, list_agents

__all__ = [
    'BaseAgent',
    'AgentLoader', 
    'TandemOrchestrator',
    'ProductionOrchestrator',
    'get_agent',
    'list_agents',
]
```

### Phase 4: Update Imports
Update all files to use new import paths:
```python
# Old
from director_impl import DirectorAgent

# New
from claude_agents.implementations.core import DirectorAgent
```

### Phase 5: Create Setup.py
```python
from setuptools import setup, find_packages

setup(
    name="claude-agents",
    version="8.0.0",
    packages=find_packages(),
    install_requires=[
        # List from requirements.txt
    ],
    entry_points={
        'console_scripts': [
            'claude-agent=claude_agents.cli.main:main',
        ],
    },
)
```

## Migration Script
Create automated migration script to handle the reorganization without breaking existing code.

## Backward Compatibility
- Keep symlinks for critical files during transition
- Provide compatibility layer with deprecation warnings
- Document migration path for external dependencies