#!/usr/bin/env python3
"""
Check agent files for Tandem Orchestration compatibility
"""

import json
import os
from pathlib import Path

import yaml


def check_agent_frontmatter(file_path):
    """Check if an agent file has valid YAML frontmatter"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        if not content.startswith('---'):
            return False, "No YAML frontmatter found"
        
        parts = content.split('---', 2)
        if len(parts) < 3:
            return False, "Incomplete YAML frontmatter"
        
        yaml_content = parts[1]
        try:
            frontmatter = yaml.safe_load(yaml_content)
            
            # Check for agent_metadata
            if frontmatter is None:
                return False, "Empty YAML frontmatter"
            
            # Check if it has agent_metadata or is a valid metadata structure
            if 'agent_metadata' in frontmatter:
                metadata = frontmatter['agent_metadata']
                if not isinstance(metadata, dict):
                    return False, f"agent_metadata is not a dict: {type(metadata)}"
            elif isinstance(frontmatter, dict):
                # Could be direct metadata
                metadata = frontmatter
            else:
                return False, f"Invalid frontmatter structure: {type(frontmatter)}"
            
            # Check for required fields
            required_fields = ['name', 'uuid']
            if isinstance(metadata, dict):
                missing = [f for f in required_fields if f not in metadata]
                if missing:
                    return True, f"Warning: Missing fields {missing}, but parseable"
            
            return True, "Valid frontmatter"
            
        except yaml.YAMLError as e:
            return False, f"YAML parse error: {e}"
            
    except Exception as e:
        return False, f"File read error: {e}"

def main():
    agents_dir = Path("${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents")
    
    # Get all .md files
    agent_files = list(agents_dir.glob("*.md"))
    
    # Filter out non-agent files
    excluded = {"Template.md", "README.md", "STATUSLINE_INTEGRATION.md", "Agents Readme.md", "WHERE_I_AM.md"}
    agent_files = [f for f in agent_files if f.name not in excluded]
    
    print(f"Checking {len(agent_files)} agent files for compatibility...\n")
    
    issues = []
    warnings = []
    valid = []
    
    for agent_file in sorted(agent_files):
        is_valid, message = check_agent_frontmatter(agent_file)
        
        if not is_valid:
            issues.append((agent_file.name, message))
            print(f"❌ {agent_file.name}: {message}")
        elif "Warning" in message:
            warnings.append((agent_file.name, message))
            print(f"⚠️  {agent_file.name}: {message}")
        else:
            valid.append(agent_file.name)
            print(f"✅ {agent_file.name}: {message}")
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Valid: {len(valid)} agents")
    print(f"  Warnings: {len(warnings)} agents")
    print(f"  Issues: {len(issues)} agents")
    
    if issues:
        print(f"\nAgents with issues that need fixing:")
        for name, issue in issues:
            print(f"  - {name}: {issue}")
    
    if warnings:
        print(f"\nAgents with warnings (should work but could be improved):")
        for name, warning in warnings:
            print(f"  - {name}: {warning}")
    
    return len(issues) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)