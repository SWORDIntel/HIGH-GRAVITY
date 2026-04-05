#!/usr/bin/env python3
"""
Automated Python source reorganization script
Reorganizes the flat src/python directory into a proper package structure
"""

import os
import shutil
from pathlib import Path
import re
from typing import Dict, List, Set, Tuple
import json


# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import (
        get_project_root, get_agents_dir, get_database_dir,
        get_python_src_dir, get_shadowgit_paths, get_database_config
    )
except ImportError:
    # Fallback if path_utilities not available
    def get_project_root():
        return Path(__file__).parent.parent.parent
    def get_agents_dir():
        return get_project_root() / 'agents'
    def get_database_dir():
        return get_project_root() / 'database'
    def get_python_src_dir():
        return get_agents_dir() / 'src' / 'python'
    def get_shadowgit_paths():
        home_dir = Path.home()
        return {'root': home_dir / 'shadowgit'}
    def get_database_config():
        return {
            'host': 'localhost', 'port': 5433,
            'database': 'claude_agents_auth',
            'user': 'claude_agent', 'password': 'claude_auth_pass'
        }
class SourceReorganizer:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.claude_agents_path = base_path / "claude_agents"
        
        # File categorization mappings
        self.agent_categories = {
            'core': ['director', 'architect', 'constructor', 'patcher', 
                    'debugger', 'testbed', 'linter', 'optimizer'],
            'security': ['security', 'bastion', 'cso', 'cryptoexpert', 
                        'quantumguard', 'redteam', 'chaos', 'ghost_protocol',
                        'cognitive_defense', 'nsa', 'bgp'],
            'development': ['debugger', 'linter', 'testbed', 'patcher', 
                           'qadirector', 'auditor'],
            'language': ['python-internal', 'c_internal', 'rust', 'go', 
                        'java', 'typescript', 'matlab', 'sql_internal'],
            'infrastructure': ['docker', 'deployer', 'infrastructure', 
                              'monitor', 'packager', 'proxmox', 'cisco', 'ddwrt'],
            'platform': ['web', 'mobile', 'androidmobile', 'tui', 'pygui', 
                        'apidesigner', 'database'],
            'specialized': ['quantum', 'mlops', 'datascience', 'npu', 'gna', 
                           'researcher', 'planner', 'docgen', 'leadengineer']
        }
        
        # Files to move to specific locations
        self.file_mappings = {
            'orchestration': ['orchestrator', 'tandem', 'production_orchestrator',
                             'agent_registry', 'database_orchestrator', 
                             'learning_orchestrator'],
            'bridges': ['bridge', 'protocol_server', 'connector'],
            'core': ['base_agent', 'agent_loader', 'agent_dynamic_loader',
                    'health', 'cache', 'metric'],
            'utils': ['parallel', 'async_io', 'cpu_affinity', 'helper',
                     'set_cpu_affinity', 'meteor_lake'],
            'voice': ['voice', 'VOICE'],
            'cli': ['cli', 'learning_cli', 'simple_learning_cli']
        }
        
        self.created_dirs = set()
        self.moved_files = []
        self.created_inits = []
        
    def create_directory_structure(self):
        """Create the new package directory structure"""
        print("Creating directory structure...")
        
        # Main package directories
        dirs = [
            self.claude_agents_path,
            self.claude_agents_path / "implementations",
            self.claude_agents_path / "orchestration",
            self.claude_agents_path / "bridges", 
            self.claude_agents_path / "core",
            self.claude_agents_path / "utils",
            self.claude_agents_path / "voice",
            self.claude_agents_path / "cli",
        ]
        
        # Implementation subdirectories
        for category in self.agent_categories.keys():
            dirs.append(self.claude_agents_path / "implementations" / category)
        
        # Other directories
        dirs.extend([
            self.base_path / "config",
            self.base_path / "tests",
            self.base_path / "docs",
            self.base_path / "scripts",
            self.base_path / "deprecated",  # For old files
        ])
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            self.created_dirs.add(str(dir_path))
            print(f"  Created: {dir_path.relative_to(self.base_path)}")
            
    def categorize_file(self, filename: str) -> Tuple[str, str]:
        """Determine category and subcategory for a file"""
        filename_lower = filename.lower()
        
        # Check if it's an implementation file
        if '_impl.py' in filename or '_agent' in filename:
            # Remove _impl.py suffix for matching
            agent_name = filename.replace('_impl.py', '').replace('_agent.py', '')
            agent_name = agent_name.replace('enhanced_', '').replace('.py', '')
            
            # Find matching category
            for category, agents in self.agent_categories.items():
                for agent in agents:
                    if agent in agent_name.lower():
                        return ('implementations', category)
            
            # Default to specialized if no match
            return ('implementations', 'specialized')
        
        # Check other file mappings
        for category, patterns in self.file_mappings.items():
            for pattern in patterns:
                if pattern in filename_lower:
                    return (category, '')
                    
        # Check for specific file types
        if filename.endswith('.md'):
            return ('docs', '')
        elif 'test' in filename_lower:
            return ('tests', '')
        elif any(x in filename_lower for x in ['install', 'create', 'analyze', 'fix', 'check']):
            return ('scripts', '')
        elif filename.endswith('.yaml') or filename.endswith('.yml') or filename.endswith('.txt'):
            return ('config', '')
            
        # Default to utils
        return ('utils', '')
        
    def move_files(self):
        """Move files to their new locations"""
        print("\nMoving files to new locations...")
        
        # Get all Python files in the current directory
        python_files = list(self.base_path.glob("*.py"))
        
        for file_path in python_files:
            if file_path.name == "reorganize_structure.py":
                continue  # Don't move this script
                
            category, subcategory = self.categorize_file(file_path.name)
            
            # Determine target directory
            if category == 'implementations' and subcategory:
                target_dir = self.claude_agents_path / category / subcategory
            elif category in ['docs', 'tests', 'scripts', 'config']:
                target_dir = self.base_path / category
            else:
                target_dir = self.claude_agents_path / category
                
            # Clean up filename
            new_name = file_path.name
            new_name = new_name.replace('_impl.py', '.py')
            new_name = new_name.replace('enhanced_', '')
            new_name = new_name.replace('-', '_')  # Python module names can't have hyphens
            
            target_path = target_dir / new_name
            
            # Move file (or copy for safety)
            shutil.copy2(file_path, target_path)
            self.moved_files.append((str(file_path.relative_to(self.base_path)), 
                                    str(target_path.relative_to(self.base_path))))
            print(f"  Moved: {file_path.name} -> {target_path.relative_to(self.base_path)}")
            
    def create_init_files(self):
        """Create __init__.py files with appropriate exports"""
        print("\nCreating __init__.py files...")
        
        # Main package init
        main_init = self.claude_agents_path / "__init__.py"
        main_init.write_text('''"""Claude Agent Framework - Main Package"""

__version__ = "8.0.0"

# Core exports
from .core.base_agent import BaseAgent
from .core.agent_loader import AgentLoader

# Orchestration exports  
from .orchestration.tandem_orchestrator import TandemOrchestrator
from .orchestration.production_orchestrator import ProductionOrchestrator
from .orchestration.agent_registry import AgentRegistry

# Utility exports
from .utils.parallel import ParallelExecutor
from .utils.helpers import setup_logging

__all__ = [
    'BaseAgent',
    'AgentLoader', 
    'TandemOrchestrator',
    'ProductionOrchestrator',
    'AgentRegistry',
    'ParallelExecutor',
    'setup_logging',
]
''')
        self.created_inits.append(str(main_init.relative_to(self.base_path)))
        
        # Create __init__.py for each directory
        for dir_path in self.created_dirs:
            dir_path = Path(dir_path)
            if 'claude_agents' in str(dir_path) or dir_path.parent == self.base_path:
                init_file = dir_path / "__init__.py"
                if not init_file.exists():
                    module_name = dir_path.name.replace('_', ' ').title()
                    init_content = f'''"""{module_name} Module"""

# Auto-import all Python modules in this directory
import os
from pathlib import Path

__all__ = []

# Get directory of this file
module_dir = Path(__file__).parent

# Import all .py files (except __init__.py)
for file in module_dir.glob("*.py"):
    if file.name != "__init__.py" and not file.name.startswith("_"):
        module_name = file.stem
        __all__.append(module_name)
        
        # Dynamic import
        exec(f"from . import {{module_name}}")

# For subdirectories, import them as subpackages
for subdir in module_dir.iterdir():
    if subdir.is_dir() and not subdir.name.startswith('_'):
        if (subdir / "__init__.py").exists():
            __all__.append(subdir.name)
            exec(f"from . import {{subdir.name}}")
'''
                    init_file.write_text(init_content)
                    self.created_inits.append(str(init_file.relative_to(self.base_path)))
                    
    def update_imports(self):
        """Update import statements in moved files"""
        print("\nUpdating import statements...")
        
        # This would be complex to do automatically, so we'll create a mapping file
        import_map = {}
        
        for old_path, new_path in self.moved_files:
            old_module = Path(old_path).stem
            new_module_parts = Path(new_path).parts
            
            # Skip non-Python files
            if not new_path.endswith('.py'):
                continue
                
            # Build new import path
            if 'claude_agents' in new_module_parts:
                idx = new_module_parts.index('claude_agents')
                import_path = '.'.join(new_module_parts[idx:-1]) + '.' + Path(new_path).stem
                import_map[old_module] = import_path
                
        # Save import mapping
        mapping_file = self.base_path / "import_mapping.json"
        with open(mapping_file, 'w') as f:
            json.dump(import_map, f, indent=2)
            
        print(f"  Import mapping saved to: {mapping_file}")
        
    def create_setup_py(self):
        """Create setup.py for the package"""
        print("\nCreating setup.py...")
        
        setup_content = '''from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements_file = Path(__file__).parent / "config" / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
else:
    requirements = []

setup(
    name="claude-agents",
    version="8.0.0",
    description="Claude Agent Framework - Comprehensive Agent System",
    author="Claude Agent Framework Team",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'claude-agent=claude_agents.cli.main:main',
            'claude-orchestrate=claude_agents.orchestration.cli:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
'''
        setup_file = self.base_path / "setup.py"
        setup_file.write_text(setup_content)
        print(f"  Created: {setup_file.relative_to(self.base_path)}")
        
    def create_compatibility_layer(self):
        """Create backward compatibility symlinks"""
        print("\nCreating compatibility layer...")
        
        compat_dir = self.base_path / "compat"
        compat_dir.mkdir(exist_ok=True)
        
        # Create a compatibility module that redirects imports
        compat_init = compat_dir / "__init__.py"
        compat_content = '''"""Backward compatibility layer - DEPRECATED"""

import warnings
import sys
from pathlib import Path

# Add new package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

warnings.warn(
    "Direct imports from src/python are deprecated. "
    "Please use 'from claude_agents.implementations import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import mapping for backward compatibility
from claude_agents.implementations.core import (
    director as director_impl,
    architect as architect_impl,
    constructor as constructor_impl,
)

from claude_agents.implementations.security import (
    security as security_impl,
    bastion as bastion_impl,
)

# Add more mappings as needed
'''
        compat_init.write_text(compat_content)
        print(f"  Created compatibility layer at: {compat_dir.relative_to(self.base_path)}")
        
    def create_summary(self):
        """Create a summary of the reorganization"""
        print("\n" + "="*60)
        print("REORGANIZATION COMPLETE")
        print("="*60)
        
        summary = {
            "created_directories": len(self.created_dirs),
            "moved_files": len(self.moved_files),
            "created_init_files": len(self.created_inits),
            "timestamp": str(Path.cwd()),
        }
        
        # Save summary
        summary_file = self.base_path / "reorganization_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        print(f"\nSummary:")
        print(f"  - Created {summary['created_directories']} directories")
        print(f"  - Moved {summary['moved_files']} files")
        print(f"  - Created {summary['created_init_files']} __init__.py files")
        print(f"\nSummary saved to: {summary_file}")
        
        # Create migration guide
        migration_guide = self.base_path / "MIGRATION_GUIDE.md"
        guide_content = f"""# Migration Guide

## Old Import Pattern
```python
from director_impl import DirectorAgent
from security_impl import SecurityAgent
```

## New Import Pattern
```python
from claude_agents.implementations.core import DirectorAgent
from claude_agents.implementations.security import SecurityAgent
```

## Package Structure
- All agent implementations are now in `claude_agents/implementations/`
- Orchestration code is in `claude_agents/orchestration/`
- Utilities are in `claude_agents/utils/`
- Bridge code is in `claude_agents/bridges/`

## Installation
```bash
cd agents/src/python
pip install -e .
```

## Files Moved
Total files moved: {len(self.moved_files)}

See `import_mapping.json` for complete mapping.
"""
        migration_guide.write_text(guide_content)
        print(f"\nMigration guide saved to: {migration_guide}")

def main():
    """Main execution"""
    base_path = Path(str(get_project_root() / "agents/src/python")
    
    print("Python Source Reorganization Tool")
    print("="*60)
    print(f"Base path: {base_path}")
    print()
    
    # Confirm before proceeding
    response = input("This will reorganize the entire src/python directory. Continue? [y/N]: ")
    if response.lower() != 'y':
        print("Aborted.")
        return
        
    reorganizer = SourceReorganizer(base_path)
    
    # Execute reorganization
    reorganizer.create_directory_structure()
    reorganizer.move_files()
    reorganizer.create_init_files()
    reorganizer.update_imports()
    reorganizer.create_setup_py()
    reorganizer.create_compatibility_layer()
    reorganizer.create_summary()
    
    print("\n✅ Reorganization complete!")
    print("\nNext steps:")
    print("1. Review the new structure in claude_agents/")
    print("2. Check import_mapping.json for import updates needed")
    print("3. Run tests to ensure everything works")
    print("4. Update any external scripts that import from this package")

if __name__ == "__main__":
    main()