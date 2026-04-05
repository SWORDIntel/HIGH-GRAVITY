#!/usr/bin/env python3
"""
Step 1: Backup and Prepare
Creates a complete backup before reorganization
"""

import os
import sys
import shutil
import tarfile
from pathlib import Path
from datetime import datetime
import json

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import get_python_src_dir
except ImportError:
    # Fallback if path_utilities not available
    def get_python_src_dir():
        return Path(__file__).parent.parent.parent / 'agents' / 'src' / 'python'

def create_backup(base_path: Path) -> Path:
    """Create a complete backup of the current structure"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"python_src_backup_{timestamp}.tar.gz"
    backup_path = base_path.parent / backup_name
    
    print(f"Creating backup: {backup_name}")
    
    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(base_path, arcname="python")
    
    print(f"✅ Backup created: {backup_path}")
    print(f"   Size: {backup_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    return backup_path

def inventory_files(base_path: Path) -> dict:
    """Create an inventory of all files and their properties"""
    inventory = {
        "timestamp": datetime.now().isoformat(),
        "base_path": str(base_path),
        "files": [],
        "stats": {
            "total_files": 0,
            "python_files": 0,
            "impl_files": 0,
            "doc_files": 0,
            "config_files": 0,
            "total_size_bytes": 0
        }
    }
    
    for file_path in base_path.rglob("*"):
        if file_path.is_file() and "venv" not in str(file_path):
            rel_path = file_path.relative_to(base_path)
            
            file_info = {
                "path": str(rel_path),
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "mtime": file_path.stat().st_mtime,
                "type": "unknown"
            }
            
            # Categorize file
            if file_path.suffix == ".py":
                inventory["stats"]["python_files"] += 1
                if "_impl" in file_path.name or "_agent" in file_path.name:
                    file_info["type"] = "implementation"
                    inventory["stats"]["impl_files"] += 1
                else:
                    file_info["type"] = "python"
            elif file_path.suffix == ".md":
                file_info["type"] = "documentation"
                inventory["stats"]["doc_files"] += 1
            elif file_path.suffix in [".yaml", ".yml", ".json", ".txt", ".ini"]:
                file_info["type"] = "config"
                inventory["stats"]["config_files"] += 1
            
            inventory["files"].append(file_info)
            inventory["stats"]["total_files"] += 1
            inventory["stats"]["total_size_bytes"] += file_info["size"]
    
    # Save inventory
    inventory_path = base_path / "file_inventory.json"
    with open(inventory_path, 'w') as f:
        json.dump(inventory, f, indent=2)
    
    print(f"\n📋 File Inventory:")
    print(f"   Total files: {inventory['stats']['total_files']}")
    print(f"   Python files: {inventory['stats']['python_files']}")
    print(f"   Implementation files: {inventory['stats']['impl_files']}")
    print(f"   Documentation files: {inventory['stats']['doc_files']}")
    print(f"   Config files: {inventory['stats']['config_files']}")
    print(f"   Total size: {inventory['stats']['total_size_bytes'] / 1024 / 1024:.2f} MB")
    print(f"\n   Inventory saved to: {inventory_path}")
    
    return inventory

def check_dependencies(base_path: Path) -> dict:
    """Check for active processes or imports using these modules"""
    issues = []
    
    # Check if any Python processes are running from this directory
    import psutil
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any(str(base_path) in arg for arg in cmdline):
                issues.append({
                    "type": "running_process",
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "cmdline": ' '.join(cmdline[:3]) + "..."
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if issues:
        print("\n⚠️  Warning: Found active processes using this directory:")
        for issue in issues:
            print(f"   PID {issue['pid']}: {issue['name']}")
        print("   Consider stopping these before reorganization")
    else:
        print("\n✅ No active processes detected")
    
    return {"issues": issues}

def create_rollback_script(base_path: Path, backup_path: Path):
    """Create a rollback script in case something goes wrong"""
    rollback_script = base_path / "rollback.sh"
    
    script_content = f"""#!/bin/bash
# Rollback script for Python reorganization
# Created: {datetime.now().isoformat()}

echo "Rolling back Python source reorganization..."

# Backup current state (post-reorganization)
mv {base_path} {base_path}_failed_reorg_{datetime.now().strftime('%Y%m%d_%H%M%S')}

# Extract backup
echo "Extracting backup from {backup_path}..."
cd {base_path.parent}
tar -xzf {backup_path.name}

echo "✅ Rollback complete"
echo "Failed reorganization saved to: {base_path}_failed_reorg_*"
"""
    
    rollback_script.write_text(script_content)
    rollback_script.chmod(0o755)
    
    print(f"\n🔄 Rollback script created: {rollback_script}")
    print(f"   Run './rollback.sh' if you need to restore the original structure")

def main():
    """Main backup and preparation"""
    base_path = get_python_src_dir()
    
    print("="*60)
    print("STEP 1: BACKUP AND PREPARATION")
    print("="*60)
    print(f"Base path: {base_path}\n")
    
    # Create backup
    backup_path = create_backup(base_path)
    
    # Create inventory
    inventory = inventory_files(base_path)
    
    # Check dependencies
    dependencies = check_dependencies(base_path)
    
    # Create rollback script
    create_rollback_script(base_path, backup_path)
    
    # Save state for next steps
    state = {
        "step": 1,
        "timestamp": datetime.now().isoformat(),
        "backup_path": str(backup_path),
        "inventory_file": "file_inventory.json",
        "ready_for_reorganization": len(dependencies["issues"]) == 0
    }
    
    state_file = base_path / ".reorganization_state.json"
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
    
    print("\n" + "="*60)
    if state["ready_for_reorganization"]:
        print("✅ READY FOR REORGANIZATION")
        print("\nNext: Run 'reorganize_step2_move.py' to reorganize files")
    else:
        print("⚠️  RESOLVE ISSUES BEFORE CONTINUING")
        print("\nAddress the warnings above, then run 'reorganize_step2_move.py'")
    print("="*60)

if __name__ == "__main__":
    main()