#!/usr/bin/env python3
"""
Import Fixer for Claude Agent Framework
Fixes import statements after directory reorganization
"""

import glob
import os
import re


def fix_imports_in_file(file_path, moved_files_map):
    """Fix imports in a single Python file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Fix imports of moved files
        for old_path, new_path in moved_files_map.items():
            old_module = old_path.replace('/', '.').replace('.py', '')
            new_module = new_path.replace('/', '.').replace('.py', '')
            
            # Fix various import patterns
            patterns = [
                (f'import {old_module}', f'import {new_module}'),
                (f'from {old_module}', f'from {new_module}'),
                (f'import {os.path.basename(old_path).replace(".py", "")}', 
                 f'from {os.path.dirname(new_module).replace(".", "/")} import {os.path.basename(new_module)}')
            ]
            
            for old_pattern, new_pattern in patterns:
                content = re.sub(re.escape(old_pattern), new_pattern, content)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✓ Fixed imports in {file_path}")
            return True
        
    except Exception as e:
        print(f"✗ Error fixing {file_path}: {e}")
        return False
    
    return False

def main():
    agents_dir = "${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents"
    
    # Map of moved files (old_path -> new_path relative to agents_dir)
    moved_files = {
        "claude_agent_bridge.py": "03-BRIDGES/claude_agent_bridge.py",
        "bridge_monitor.py": "03-BRIDGES/bridge_monitor.py",
        "agent_server.py": "03-BRIDGES/agent_server.py",
        "test_agent_communication.py": "03-BRIDGES/test_agent_communication.py",
        "auto_integrate.py": "03-BRIDGES/auto_integrate.py",
        "VOICE_INPUT_SYSTEM.py": "03-BRIDGES/VOICE_INPUT_SYSTEM.py",
        "VOICE_TOGGLE.py": "03-BRIDGES/VOICE_TOGGLE.py",
        "quick_voice.py": "03-BRIDGES/quick_voice.py",
        "DEVELOPMENT_CLUSTER_DIRECT.py": "08-ADMIN-TOOLS/DEVELOPMENT_CLUSTER_DIRECT.py",
        "CLAUDE_BOOT_INIT.py": "08-ADMIN-TOOLS/CLAUDE_BOOT_INIT.py",
        "OPTIMAL_PATH_EXECUTION.py": "08-ADMIN-TOOLS/OPTIMAL_PATH_EXECUTION.py",
        "UPDATE_AGENTS_INTEGRATION.py": "08-ADMIN-TOOLS/UPDATE_AGENTS_INTEGRATION.py",
        "INTEGRATION_EXAMPLE.py": "08-ADMIN-TOOLS/INTEGRATION_EXAMPLE.py",
        "HYBRID_INTEGRATION_DEMO.py": "08-ADMIN-TOOLS/HYBRID_INTEGRATION_DEMO.py",
        "BRIDGE_TO_BINARY_TRANSITION.py": "08-ADMIN-TOOLS/BRIDGE_TO_BINARY_TRANSITION.py",
    }
    
    print("Fixing imports in Python files...")
    
    # Find all Python files and fix their imports
    python_files = glob.glob(os.path.join(agents_dir, "**", "*.py"), recursive=True)
    fixed_count = 0
    
    for py_file in python_files:
        if fix_imports_in_file(py_file, moved_files):
            fixed_count += 1
    
    print(f"\nFixed imports in {fixed_count} files")
    print("Import fixing completed!")

if __name__ == "__main__":
    main()
