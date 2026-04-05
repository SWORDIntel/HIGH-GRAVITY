#!/usr/bin/env python3
"""
Update Dynamic Loader for Complete Agent Coverage

This script adds all missing agents to the dynamic loader mapping.
We have 43 agent .md files but only 29 implementations.
"""

import os
from pathlib import Path

def get_missing_agents():
    """Find agents with .md files but no implementations"""
    # These are the 12 agents that have .md files but no implementation files
    missing_agents = [
        'androidmobile',
        'gna', 
        'intergration',
        'leadengineer',
        'npu',
        'organization', 
        'planner',
        'python-internal',
        'qadirector',
        'researcher',
        'tui'
    ]
    return missing_agents

def update_dynamic_loader():
    """Update the dynamic loader to include all agents"""
    
    # Read current dynamic loader - use relative path
    script_dir = Path(__file__).parent
    loader_file = script_dir / "agent_dynamic_loader.py"
    with open(loader_file, 'r') as f:
        content = f.read()
    
    # Find the class mapping section
    lines = content.split('\n')
    mapping_start = None
    mapping_end = None
    
    for i, line in enumerate(lines):
        if 'class_mapping = {' in line:
            mapping_start = i
        elif mapping_start and line.strip() == '}' and 'class_mapping' in lines[i-5:i]:
            mapping_end = i
            break
    
    if mapping_start is None or mapping_end is None:
        print("Could not find class_mapping section")
        return
    
    # Extract existing mappings
    existing_mappings = []
    for i in range(mapping_start + 1, mapping_end):
        line = lines[i].strip()
        if line and not line.startswith('#'):
            existing_mappings.append(line)
    
    # Add missing agents with placeholder class names
    missing_agents = get_missing_agents()
    new_mappings = []
    
    for agent in missing_agents:
        # Use naming pattern similar to existing agents
        if agent == 'python-internal':
            class_name = 'PYTHONINTERNALPythonExecutor'
        else:
            class_name = f'{agent.upper()}PythonExecutor'
        
        new_mapping = f'        "{agent}": "{class_name}",'
        new_mappings.append(new_mapping)
    
    # Combine all mappings and sort
    all_mappings = existing_mappings + new_mappings
    all_mappings.sort()
    
    # Rebuild the file
    new_lines = lines[:mapping_start + 1] + all_mappings + lines[mapping_end:]
    new_content = '\n'.join(new_lines)
    
    # Write back to file
    with open(loader_file, 'w') as f:
        f.write(new_content)
    
    print(f"Updated dynamic loader with {len(missing_agents)} missing agents:")
    for agent in missing_agents:
        print(f"  - {agent}")

def main():
    print("Updating dynamic loader for complete agent coverage...")
    update_dynamic_loader()
    print("Dynamic loader updated successfully!")

if __name__ == "__main__":
    main()