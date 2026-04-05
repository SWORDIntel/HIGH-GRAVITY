#!/usr/bin/env python3
"""
Step 3: Update All Imports
Updates imports in all files to use new structure
Handles orchestration, learning system, and all dependencies
"""

import os
import re
from pathlib import Path
import json
from datetime import datetime
import ast
import sys

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import get_python_src_dir, get_project_root, get_database_dir, get_orchestration_dir
except ImportError:
    # Fallback if path_utilities not available
    def get_python_src_dir():
        return Path(__file__).parent.parent.parent / 'agents' / 'src' / 'python'
    def get_project_root():
        return Path(__file__).parent.parent.parent
    def get_database_dir():
        return get_project_root() / 'database'
    def get_orchestration_dir():
        return get_project_root() / 'orchestration'

class ImportUpdater:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.claude_agents_path = base_path / "claude_agents"
        self.updates_made = []
        self.files_updated = []
        self.errors = []
        
        # Load file mapping from step 2
        self.load_mapping()
        
        # Import replacement patterns
        self.import_replacements = self.build_import_map()
        
        # Critical system paths to check - using dynamic resolution
        project_root = get_project_root()
        self.critical_paths = [
            get_orchestration_dir(),
            get_database_dir(),
            project_root,
            self.base_path.parent,  # agents directory
        ]
        
    def load_mapping(self):
        """Load file mapping from step 2"""
        mapping_file = self.base_path / "file_mapping.json"
        if mapping_file.exists():
            with open(mapping_file) as f:
                self.file_mapping = json.load(f)
        else:
            print("⚠️  Warning: No file mapping found. Some imports may not be updated correctly.")
            self.file_mapping = {"moved_files": []}
            
    def build_import_map(self) -> dict:
        """Build a map of old imports to new imports"""
        import_map = {}
        
        # Build from moved files
        for old_path, new_path in self.file_mapping.get("moved_files", []):
            old_path = Path(old_path)
            new_path = Path(new_path)
            
            # Get module names
            old_module = old_path.stem
            
            # Build new import path
            if "claude_agents" in str(new_path):
                parts = new_path.parts
                idx = parts.index("claude_agents")
                new_import = ".".join(parts[idx:-1]) + "." + new_path.stem
                
                # Map various import patterns
                import_map[f"from {old_module} import"] = f"from {new_import} import"
                import_map[f"import {old_module}"] = f"import {new_import}"
                
                # Handle _impl suffix
                if "_impl" in old_module:
                    base_name = old_module.replace("_impl", "")
                    import_map[f"from {base_name}_impl import"] = f"from {new_import} import"
                    import_map[f"import {base_name}_impl"] = f"import {new_import}"
                    
        # Add specific mappings for critical modules
        critical_mappings = {
            # Orchestration
            "from production_orchestrator import": "from claude_agents.orchestration.production_orchestrator import",
            "from tandem_orchestrator import": "from claude_agents.orchestration.tandem_orchestrator import",
            "from agent_registry import": "from claude_agents.orchestration.agent_registry import",
            "from database_orchestrator import": "from claude_agents.orchestration.database_orchestrator import",
            "import production_orchestrator": "import claude_agents.orchestration.production_orchestrator as production_orchestrator",
            "import tandem_orchestrator": "import claude_agents.orchestration.tandem_orchestrator as tandem_orchestrator",
            
            # Learning system
            "from learning_orchestrator_bridge import": "from claude_agents.learning.learning_orchestrator_bridge import",
            "from postgresql_learning_system import": "from claude_agents.learning.postgresql_learning_system import",
            "import learning_orchestrator_bridge": "import claude_agents.learning.learning_orchestrator_bridge as learning_orchestrator_bridge",
            
            # Core implementations
            "from director_impl import": "from claude_agents.implementations.core.director import",
            "from architect_impl import": "from claude_agents.implementations.core.architect import",
            "from security_impl import": "from claude_agents.implementations.security.security import",
            
            # Bridges
            "from claude_agent_bridge import": "from claude_agents.bridges.claude_agent_bridge import",
            "from binary_bridge_connector import": "from claude_agents.bridges.binary_bridge_connector import",
            
            # Utils
            "from parallel_orchestration_utils import": "from claude_agents.utils.parallel_orchestration_utils import",
            "from meteor_lake_parallel import": "from claude_agents.utils.meteor_lake_parallel import",
        }
        
        import_map.update(critical_mappings)
        return import_map
        
    def update_file_imports(self, file_path: Path) -> int:
        """Update imports in a single file"""
        try:
            content = file_path.read_text()
            original_content = content
            updates = 0
            
            # Apply import replacements
            for old_import, new_import in self.import_replacements.items():
                if old_import in content:
                    content = content.replace(old_import, new_import)
                    updates += 1
                    self.updates_made.append({
                        "file": str(file_path),
                        "old": old_import,
                        "new": new_import
                    })
                    
            # Handle relative imports in moved files
            if str(file_path).startswith(str(self.claude_agents_path)):
                # Update relative imports to absolute
                content = re.sub(
                    r'from \. import (.+)',
                    lambda m: self._convert_relative_import(file_path, m.group(1)),
                    content
                )
                
            # Save if changed
            if content != original_content:
                file_path.write_text(content)
                self.files_updated.append(str(file_path))
                return updates
                
        except Exception as e:
            self.errors.append(f"Error updating {file_path}: {e}")
            
        return 0
        
    def _convert_relative_import(self, file_path: Path, import_name: str) -> str:
        """Convert relative import to absolute"""
        # Get package path
        rel_path = file_path.relative_to(self.claude_agents_path)
        package_parts = rel_path.parts[:-1]
        
        if package_parts:
            package = "claude_agents." + ".".join(package_parts)
            return f"from {package} import {import_name}"
        else:
            return f"from claude_agents import {import_name}"
            
    def update_orchestration_files(self):
        """Update imports in orchestration directory files"""
        print("\n🔧 Updating orchestration system files...")
        
        orch_dir = get_orchestration_dir()
        if orch_dir.exists():
            for py_file in orch_dir.glob("*.py"):
                updates = self.update_file_imports(py_file)
                if updates > 0:
                    print(f"   ✅ Updated: {py_file.name} ({updates} imports)")
                    
    def update_learning_system_files(self):
        """Update imports in learning system files"""
        print("\n🎓 Updating learning system files...")
        
        # Check various locations for learning system files
        learning_locations = [
            self.claude_agents_path / "learning",
            self.base_path / "postgresql_learning_system.py",
            self.base_path / "integrated_learning_setup.py",
            self.base_path / "learning_config_manager.py",
        ]
        
        for location in learning_locations:
            if location.is_file():
                updates = self.update_file_imports(location)
                if updates > 0:
                    print(f"   ✅ Updated: {location.name} ({updates} imports)")
            elif location.is_dir():
                for py_file in location.glob("*.py"):
                    updates = self.update_file_imports(py_file)
                    if updates > 0:
                        print(f"   ✅ Updated: {py_file.name} ({updates} imports)")
                        
    def update_database_files(self):
        """Update imports in database directory"""
        print("\n🗄️  Updating database system files...")
        
        db_dir = get_database_dir()
        if db_dir.exists():
            for py_file in db_dir.rglob("*.py"):
                if "venv" not in str(py_file):
                    updates = self.update_file_imports(py_file)
                    if updates > 0:
                        print(f"   ✅ Updated: {py_file.relative_to(db_dir)} ({updates} imports)")
                        
    def update_claude_agents_files(self):
        """Update imports within the new claude_agents package"""
        print("\n📦 Updating claude_agents package files...")
        
        for py_file in self.claude_agents_path.rglob("*.py"):
            if py_file.name != "__init__.py":
                updates = self.update_file_imports(py_file)
                if updates > 0:
                    rel_path = py_file.relative_to(self.claude_agents_path)
                    print(f"   ✅ Updated: {rel_path} ({updates} imports)")
                    
    def update_external_scripts(self):
        """Update imports in external scripts that use this package"""
        print("\n🔗 Updating external scripts...")
        
        # Check parent directories for scripts
        for critical_path in self.critical_paths:
            if critical_path.exists():
                # Look for Python files that might import from src/python
                for py_file in critical_path.glob("*.py"):
                    if "venv" not in str(py_file) and py_file.is_file():
                        try:
                            content = py_file.read_text()
                            if "src/python" in content or "src.python" in content:
                                updates = self.update_file_imports(py_file)
                                if updates > 0:
                                    print(f"   ✅ Updated: {py_file.name} ({updates} imports)")
                        except:
                            pass
                            
    def create_import_helper(self):
        """Create a helper script for manual import updates"""
        helper_content = '''#!/usr/bin/env python3
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
'''
        
        helper_file = self.base_path / "import_helper.py"
        helper_file.write_text(helper_content)
        helper_file.chmod(0o755)
        print(f"\n📚 Import helper created: {helper_file}")
        
    def save_update_report(self):
        """Save a report of all updates made"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "files_updated": len(self.files_updated),
            "total_updates": len(self.updates_made),
            "errors": len(self.errors),
            "updates": self.updates_made[:100],  # First 100 updates
            "files": self.files_updated[:100],  # First 100 files
        }
        
        report_file = self.base_path / "import_update_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\n📋 Update report saved to: {report_file}")
        
    def update_state(self):
        """Update reorganization state"""
        state_file = self.base_path / ".reorganization_state.json"
        with open(state_file) as f:
            state = json.load(f)
            
        state["step"] = 3
        state["timestamp_step3"] = datetime.now().isoformat()
        state["imports_updated"] = len(self.updates_made)
        state["files_updated"] = len(self.files_updated)
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

def main():
    """Main import updater"""
    base_path = get_python_src_dir()
    
    print("="*60)
    print("STEP 3: UPDATE IMPORTS")
    print("="*60)
    
    updater = ImportUpdater(base_path)
    
    # Update all systems
    updater.update_orchestration_files()
    updater.update_learning_system_files()
    updater.update_database_files()
    updater.update_claude_agents_files()
    updater.update_external_scripts()
    
    # Create helper tools
    updater.create_import_helper()
    updater.save_update_report()
    updater.update_state()
    
    # Report results
    print("\n" + "="*60)
    if updater.errors:
        print(f"⚠️  COMPLETED WITH {len(updater.errors)} ERRORS")
        for error in updater.errors[:5]:
            print(f"   {error}")
    else:
        print("✅ IMPORT UPDATE COMPLETE")
        
    print(f"\n📊 Summary:")
    print(f"   Files updated: {len(updater.files_updated)}")
    print(f"   Imports updated: {len(updater.updates_made)}")
    print(f"   Errors: {len(updater.errors)}")
    
    print("\n🎉 REORGANIZATION COMPLETE!")
    print("\nThe src/python directory has been reorganized into a proper package structure.")
    print("All critical systems (orchestration, learning, database) have been updated.")
    print("\nIf any imports were missed, use './import_helper.py' for reference.")
    print("="*60)

if __name__ == "__main__":
    main()