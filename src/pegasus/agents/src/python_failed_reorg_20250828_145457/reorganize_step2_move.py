#!/usr/bin/env python3
"""
Step 2: Move and Reorganize Files
Moves files to new structure with minimal disruption
Preserves all critical paths for orchestration and learning systems
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import (
        get_agents_dir,
        get_database_config,
        get_database_dir,
        get_project_root,
        get_python_src_dir,
        get_shadowgit_paths,
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
class SafeReorganizer:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.claude_agents_path = base_path / "claude_agents"
        self.moved_files = []
        self.symlinks_created = []
        self.errors = []
        
        # Critical files that must maintain their paths
        self.critical_files = [
            "production_orchestrator.py",
            "tandem_orchestrator.py",
            "agent_registry.py",
            "database_orchestrator.py",
            "learning_orchestrator_bridge.py",
            "postgresql_learning_system.py",
            "test_tandem_system.py",
            "test_learning_integration.py",
            "launch_learning_system.sh",
            "tandem-orchestrator.service"
        ]
        
        # Files used by orchestration directory
        self.orchestration_deps = [
            "production_orchestrator.py",
            "tandem_orchestrator.py", 
            "agent_registry.py",
            "database_orchestrator.py",
            "orchestrator_metrics.py",
            "config.json"
        ]
        
        # Map categories
        self.category_map = {
            'implementations/core': [
                'director', 'architect', 'constructor', 'patcher',
                'debugger', 'testbed', 'linter', 'optimizer'
            ],
            'implementations/security': [
                'security', 'bastion', 'cso', 'cryptoexpert', 'quantumguard',
                'redteam', 'chaos', 'securitychaos', 'securityauditor',
                'ghost_protocol', 'cognitive_defense', 'nsa', 'bgp', 'apt41',
                'psyops', 'prompt'
            ],
            'implementations/development': [
                'debugger', 'linter', 'testbed', 'patcher', 'qadirector', 
                'auditor', 'oversight', 'intergration'
            ],
            'implementations/language': [
                'python-internal', 'python_internal', 'c_internal', 'rust',
                'go', 'java', 'typescript', 'kotlin', 'assembly', 'matlab',
                'sql_internal', 'zig', 'carbon'
            ],
            'implementations/infrastructure': [
                'docker', 'deployer', 'infrastructure', 'monitor', 'packager',
                'proxmox', 'cisco', 'ddwrt', 'iot'
            ],
            'implementations/platform': [
                'web', 'mobile', 'androidmobile', 'tui', 'pygui',
                'apidesigner', 'database'
            ],
            'implementations/specialized': [
                'quantum', 'mlops', 'datascience', 'npu', 'gna',
                'researcher', 'planner', 'docgen', 'leadengineer',
                'organization', 'orchestrator', 'wrapper'
            ],
            'orchestration': [
                'orchestrator', 'tandem', 'production_orchestrator',
                'agent_registry', 'database_orchestrator',
                'learning_orchestrator', 'orchestrator_metrics'
            ],
            'bridges': [
                'bridge', 'protocol_server', 'connector', 'claude_agent_bridge',
                'binary_bridge', 'hybrid_bridge', 'statusline_bridge'
            ],
            'core': [
                'base_agent', 'agent_loader', 'agent_dynamic_loader',
                'health', 'cache', 'metric', 'agent_protocol'
            ],
            'utils': [
                'parallel', 'async_io', 'cpu_affinity', 'helper',
                'meteor_lake', 'intelligent_cache', 'universal_helper'
            ],
            'voice': [
                'voice', 'VOICE', 'quick_voice'
            ],
            'cli': [
                'cli', 'learning_cli', 'simple_learning'
            ],
            'learning': [
                'learning', 'postgresql_learning', 'integrated_learning',
                'learning_config', 'launch_learning'
            ],
            'config': [
                'logging.yaml', 'requirements', '.env', 'config.json',
                'settings', 'manifest.json', 'registered_agents.json'
            ],
            'tests': [
                'test_', 'check_agent', 'analyze_agent'
            ],
            'scripts': [
                'install', 'create_missing', 'fix_agent', 'analyze',
                'check_'
            ],
            'docs': [
                '.md'
            ]
        }
        
    def check_state(self) -> bool:
        """Check if step 1 was completed"""
        state_file = self.base_path / ".reorganization_state.json"
        if not state_file.exists():
            print("❌ Error: Step 1 not completed. Run reorganize_step1_backup.py first")
            return False
            
        with open(state_file) as f:
            state = json.load(f)
            
        if state.get("step") != 1:
            print("❌ Error: Invalid state. Run step 1 first")
            return False
            
        print(f"✅ Found backup: {state['backup_path']}")
        return True
        
    def create_structure(self):
        """Create the new directory structure"""
        print("\n📁 Creating directory structure...")
        
        dirs = [
            self.claude_agents_path,
            self.claude_agents_path / "implementations",
            self.claude_agents_path / "implementations" / "core",
            self.claude_agents_path / "implementations" / "security",
            self.claude_agents_path / "implementations" / "development",
            self.claude_agents_path / "implementations" / "language",
            self.claude_agents_path / "implementations" / "infrastructure",
            self.claude_agents_path / "implementations" / "platform",
            self.claude_agents_path / "implementations" / "specialized",
            self.claude_agents_path / "orchestration",
            self.claude_agents_path / "bridges",
            self.claude_agents_path / "core",
            self.claude_agents_path / "utils",
            self.claude_agents_path / "voice",
            self.claude_agents_path / "cli",
            self.claude_agents_path / "learning",
            self.base_path / "config",
            self.base_path / "tests",
            self.base_path / "scripts",
            self.base_path / "docs",
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            
    def categorize_file(self, file_path: Path) -> str:
        """Determine the category for a file"""
        filename = file_path.name.lower()
        
        # Check each category
        for category, patterns in self.category_map.items():
            for pattern in patterns:
                if pattern in filename:
                    return category
                    
        # Default categories based on file type
        if '_impl.py' in filename or '_agent' in filename:
            return 'implementations/specialized'
        elif filename.endswith('.md'):
            return 'docs'
        elif filename.endswith(('.yaml', '.yml', '.json', '.txt', '.ini')):
            return 'config'
        elif 'test' in filename:
            return 'tests'
        else:
            return 'utils'
            
    def move_file_safely(self, src: Path, category: str) -> bool:
        """Move a file and create symlink for compatibility"""
        # Determine destination
        if category.startswith('implementations/'):
            dest_dir = self.claude_agents_path / category
        elif category in ['orchestration', 'bridges', 'core', 'utils', 'voice', 'cli', 'learning']:
            dest_dir = self.claude_agents_path / category
        else:
            dest_dir = self.base_path / category
            
        # Clean filename
        clean_name = src.name
        clean_name = clean_name.replace('-', '_')  # Python modules can't have hyphens
        
        dest = dest_dir / clean_name
        
        try:
            # Copy file (preserve original for now)
            if src.is_file():
                shutil.copy2(src, dest)
                self.moved_files.append((str(src), str(dest)))
                
                # Create symlink in original location for compatibility
                if src.name in self.critical_files or src.name in self.orchestration_deps:
                    # Keep original for critical files
                    print(f"   ⚠️  Kept original: {src.name} (critical file)")
                else:
                    # Create symlink
                    src.unlink()
                    src.symlink_to(dest)
                    self.symlinks_created.append(str(src))
                    
                return True
        except Exception as e:
            self.errors.append(f"Failed to move {src}: {e}")
            return False
            
    def reorganize_files(self):
        """Reorganize all Python files"""
        print("\n📦 Reorganizing files...")
        
        # Get all Python files
        python_files = list(self.base_path.glob("*.py"))
        
        # Skip reorganization scripts themselves
        skip_files = [
            "reorganize_step1_backup.py",
            "reorganize_step2_move.py", 
            "reorganize_step3_update.py",
            "reorganize_structure.py",
            "reorganize_master.py"
        ]
        
        for file_path in python_files:
            if file_path.name in skip_files:
                continue
                
            category = self.categorize_file(file_path)
            self.move_file_safely(file_path, category)
            
        print(f"   Moved {len(self.moved_files)} files")
        print(f"   Created {len(self.symlinks_created)} symlinks")
        
    def create_init_files(self):
        """Create __init__.py files for all packages"""
        print("\n📝 Creating __init__.py files...")
        
        # Main claude_agents __init__
        main_init = self.claude_agents_path / "__init__.py"
        main_init.write_text('''"""Claude Agent Framework - Organized Package Structure"""

__version__ = "8.0.0"

# Import organization modules
from .orchestration import *
from .core import *
from .utils import *

# Make implementations accessible
from .implementations import get_agent, list_agents

__all__ = ['get_agent', 'list_agents']
''')
        
        # Create __init__ for each subdirectory
        for subdir in self.claude_agents_path.rglob("*"):
            if subdir.is_dir() and not subdir.name.startswith('__'):
                init_file = subdir / "__init__.py"
                if not init_file.exists():
                    init_file.write_text(f'"""{"} {subdir.name.title()} Module"""\n\n')
                    
        # Also create __init__ for external orchestration directory
        external_orch_dir = Path(str(get_project_root() / "orchestration")
        if external_orch_dir.exists():
            external_init = external_orch_dir / "__init__.py"
            if not external_init.exists():
                external_init.write_text('''"""Claude Agent Framework - Orchestration Module"""

# Import core orchestration components
try:
    from .production_orchestrator import ProductionOrchestrator
    from .tandem_orchestrator import TandemOrchestrator
    from .agent_registry import AgentRegistry
    from .database_orchestrator import DatabaseOrchestrator
    from .orchestrator_metrics import OrchestratorMetrics
except ImportError as e:
    # Fallback if not all modules are available
    pass

__all__ = [
    'ProductionOrchestrator',
    'TandemOrchestrator', 
    'AgentRegistry',
    'DatabaseOrchestrator',
    'OrchestratorMetrics'
]
''')
                print(f"   ✅ Created __init__.py for external orchestration directory")
                    
    def update_orchestration_imports(self):
        """Update critical orchestration files to work with new structure"""
        print("\n🔧 Updating orchestration system imports...")
        
        # Check orchestration directory
        orch_dir = Path(str(get_project_root() / "orchestration")
        if orch_dir.exists():
            print(f"   Found orchestration directory: {orch_dir}")
            
            # Create symlinks to orchestration files
            for orch_file in self.orchestration_deps:
                src = self.claude_agents_path / "orchestration" / orch_file
                if src.exists():
                    dest = orch_dir / orch_file
                    if not dest.exists():
                        try:
                            dest.symlink_to(src)
                            print(f"   ✅ Linked: {orch_file}")
                        except:
                            pass
                            
    def save_mapping(self):
        """Save file mapping for step 3"""
        mapping = {
            "timestamp": datetime.now().isoformat(),
            "moved_files": self.moved_files,
            "symlinks": self.symlinks_created,
            "errors": self.errors,
            "critical_files_preserved": self.critical_files
        }
        
        mapping_file = self.base_path / "file_mapping.json"
        with open(mapping_file, 'w') as f:
            json.dump(mapping, f, indent=2)
            
        print(f"\n📋 Mapping saved to: {mapping_file}")
        
    def update_state(self):
        """Update reorganization state"""
        state_file = self.base_path / ".reorganization_state.json"
        with open(state_file) as f:
            state = json.load(f)
            
        state["step"] = 2
        state["timestamp_step2"] = datetime.now().isoformat()
        state["files_moved"] = len(self.moved_files)
        state["symlinks_created"] = len(self.symlinks_created)
        state["errors"] = len(self.errors)
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

def main():
    """Main reorganization"""
    base_path = Path(str(get_project_root() / "agents/src/python")
    
    print("="*60)
    print("STEP 2: FILE REORGANIZATION")
    print("="*60)
    
    reorganizer = SafeReorganizer(base_path)
    
    # Check state
    if not reorganizer.check_state():
        sys.exit(1)
        
    # Execute reorganization
    reorganizer.create_structure()
    reorganizer.reorganize_files()
    reorganizer.create_init_files()
    reorganizer.update_orchestration_imports()
    reorganizer.save_mapping()
    reorganizer.update_state()
    
    # Report results
    print("\n" + "="*60)
    if reorganizer.errors:
        print(f"⚠️  COMPLETED WITH {len(reorganizer.errors)} ERRORS")
        for error in reorganizer.errors[:5]:
            print(f"   {error}")
    else:
        print("✅ REORGANIZATION COMPLETE")
        
    print(f"\n📊 Summary:")
    print(f"   Files moved: {len(reorganizer.moved_files)}")
    print(f"   Symlinks created: {len(reorganizer.symlinks_created)}")
    print(f"   Critical files preserved: {len(reorganizer.critical_files)}")
    
    print("\nNext: Run 'reorganize_step3_update.py' to update imports")
    print("="*60)

if __name__ == "__main__":
    main()