#!/usr/bin/env python3
"""
Standardize all Claude Agent Framework v7.0 agent names to CAPITAL LETTERS
Updates both file names and internal YAML name fields for consistency
"""

import os
import re
import shutil
from pathlib import Path

import yaml

# Mapping of current names to standardized CAPITAL names
AGENT_NAME_MAPPING = {
    # Current filename -> Standard CAPITAL name
    "APIDesigner.md": "APIDESIGNER.md",
    "Architect.md": "ARCHITECT.md",
    "Bastion.md": "BASTION.md",
    "CSO.md": "CSO.md",  # Already caps
    "Constructor.md": "CONSTRUCTOR.md",
    "CryptoExpert.md": "CRYPTOEXPERT.md",
    "DataScience.md": "DATASCIENCE.md",
    "Database.md": "DATABASE.md",
    "Debugger.md": "DEBUGGER.md",
    "Deployer.md": "DEPLOYER.md",
    "Director.md": "DIRECTOR.md",
    "Docgen.md": "DOCGEN.md",
    "GNU.md": "GNU.md",  # Already caps
    "Infrastructure.md": "INFRASTRUCTURE.md",
    "LeadEngineer.md": "LEADENGINEER.md",
    "Linter.md": "LINTER.md",
    "MLOps.md": "MLOPS.md",
    "Mobile.md": "MOBILE.md",
    "Monitor.md": "MONITOR.md",
    "NPU.md": "NPU.md",  # Already caps
    "Optimizer.md": "OPTIMIZER.md",
    "Oversight.md": "OVERSIGHT.md",
    "PLANNER.md": "PLANNER.md",  # Already caps
    "Packager.md": "PACKAGER.md",
    "Patcher.md": "PATCHER.md",
    "ProjectOrchestrator.md": "PROJECTORCHESTRATOR.md",
    "PyGUI.md": "PYGUI.md",
    "QADirector.md": "QADIRECTOR.md",
    "RESEARCHER.md": "RESEARCHER.md",  # Already caps
    "STATUSLINE_INTEGRATION.md": "STATUSLINE_INTEGRATION.md",  # Already caps
    "Security.md": "SECURITY.md",
    "SecurityAuditor.md": "SECURITYAUDITOR.md",
    "SecurityChaosAgent.md": "SECURITYCHAOSAGENT.md",
    "TUI.md": "TUI.md",  # Already caps
    "Testbed.md": "TESTBED.md",
    "Web.md": "WEB.md",
    "c-internal.md": "C-INTERNAL.md",
    "python-internal.md": "PYTHON-INTERNAL.md",
}

# YAML name field mapping (lowercase for claude-code compatibility)
YAML_NAME_MAPPING = {
    "apidesigner": "apidesigner",
    "architect": "architect",
    "bastion": "bastion",
    "cso": "cso",
    "constructor": "constructor",
    "cryptoexpert": "cryptoexpert",
    "datascience": "datascience",
    "database": "database",
    "debugger": "debugger",
    "deployer": "deployer",
    "director": "director",
    "docgen": "docgen",
    "gnu": "gnu",
    "infrastructure": "infrastructure",
    "leadengineer": "leadengineer",
    "linter": "linter",
    "mlops": "mlops",
    "mobile": "mobile",
    "monitor": "monitor",
    "npu": "npu",
    "optimizer": "optimizer",
    "oversight": "oversight",
    "planner": "planner",
    "packager": "packager",
    "patcher": "patcher",
    "projectorchestrator": "projectorchestrator",
    "pygui": "pygui",
    "qadirector": "qadirector",
    "researcher": "researcher",
    "statusline_integration": "statusline_integration",
    "security": "security",
    "securityauditor": "securityauditor",
    "securitychaosagent": "securitychaosagent",
    "tui": "tui",
    "testbed": "testbed",
    "web": "web",
    "c-internal": "c-internal",
    "python-internal": "python-internal",
}


def standardize_agent_name_in_file(filepath, new_filepath):
    """Update YAML name field to match standardized format"""

    # Read current file
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if file has YAML frontmatter
    if not content.startswith("---"):
        print(f"⚠️  {os.path.basename(filepath)} - No YAML frontmatter found")
        return False

    # Split content into frontmatter and body
    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"❌ {os.path.basename(filepath)} - Invalid YAML frontmatter structure")
        return False

    yaml_content = parts[1].strip()
    body_content = parts[2]

    # Parse existing YAML
    try:
        yaml_data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        print(f"❌ {os.path.basename(filepath)} - YAML parsing error: {e}")
        return False

    # Get original name for lookup
    old_name = yaml_data.get("name", "")

    # Find standardized name (keep YAML names lowercase for Task tool compatibility)
    if old_name in YAML_NAME_MAPPING:
        new_name = YAML_NAME_MAPPING[old_name]
    else:
        # Convert filename to lowercase name
        base_name = os.path.basename(new_filepath).replace(".md", "").lower()
        new_name = base_name

    # Update YAML data
    yaml_data["name"] = new_name

    # Regenerate YAML with proper order
    ordered_yaml = f"""name: {yaml_data['name']}
description: {yaml_data['description']}
color: {yaml_data.get('color', '#000000')}
tools:"""

    for tool in yaml_data.get("tools", []):
        ordered_yaml += f"\n  - {tool}"

    # Reconstruct file content
    new_content = f"---\n{ordered_yaml}\n---{body_content}"

    # Write to new file path
    with open(new_filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(
        f"✅ {os.path.basename(filepath)} → {os.path.basename(new_filepath)} (name: {new_name})"
    )
    return True


def main():
    """Standardize all agent file names and internal names"""

    print("🔤 Standardizing Claude Agent Framework v7.0 agent names to CAPITALS")
    print("=" * 70)
    print()

    # Find all agent .md files
    agent_files = []
    for filename in os.listdir("."):
        if filename.endswith(".md") and filename in AGENT_NAME_MAPPING:
            agent_files.append(filename)

    agent_files.sort()

    print(f"Found {len(agent_files)} agent files to standardize")
    print()

    renamed_count = 0
    updated_count = 0

    # Process each agent file
    for old_filename in agent_files:
        new_filename = AGENT_NAME_MAPPING[old_filename]

        # Skip if already correct name
        if old_filename == new_filename:
            # Still need to check/update YAML content
            if standardize_agent_name_in_file(old_filename, old_filename):
                updated_count += 1
            continue

        # Check if target file already exists
        if os.path.exists(new_filename):
            print(f"⚠️  {new_filename} already exists, skipping {old_filename}")
            continue

        # Update content and rename file
        if standardize_agent_name_in_file(old_filename, new_filename):
            # Remove old file after successful creation
            os.remove(old_filename)
            renamed_count += 1
            updated_count += 1

    print()
    print(f"✅ Successfully renamed {renamed_count} files")
    print(f"✅ Successfully updated {updated_count} agent configurations")
    print()

    # Show standardization summary
    print("🔤 Standardization Summary:")
    print("=" * 40)
    print()

    categories = {
        "Command & Control": ["DIRECTOR", "PROJECTORCHESTRATOR"],
        "Security": [
            "SECURITY",
            "BASTION",
            "SECURITYCHAOSAGENT",
            "OVERSIGHT",
            "CSO",
            "CRYPTOEXPERT",
            "SECURITYAUDITOR",
        ],
        "Development": [
            "ARCHITECT",
            "CONSTRUCTOR",
            "PATCHER",
            "DEBUGGER",
            "TESTBED",
            "LINTER",
            "OPTIMIZER",
            "LEADENGINEER",
            "QADIRECTOR",
        ],
        "Infrastructure": ["INFRASTRUCTURE", "DEPLOYER", "MONITOR", "PACKAGER", "GNU"],
        "Specialists": [
            "APIDESIGNER",
            "DATABASE",
            "WEB",
            "MOBILE",
            "PYGUI",
            "TUI",
            "DATASCIENCE",
            "MLOPS",
            "NPU",
        ],
        "Internal Systems": ["C-INTERNAL", "PYTHON-INTERNAL"],
        "Support": ["RESEARCHER", "DOCGEN", "PLANNER", "STATUSLINE_INTEGRATION"],
    }

    for category, agents in categories.items():
        print(f"\n{category}:")
        for agent in agents:
            filename = f"{agent}.md"
            if os.path.exists(filename):
                print(f"  ✅ {agent}")
            else:
                print(f"  ❌ {agent} (missing)")

    print()
    print("All agent names now follow CAPITAL LETTER standard for:")
    print("  📁 Consistent file naming")
    print("  🔍 Easy identification")
    print("  📊 Professional appearance")
    print("  🔧 Tool integration compatibility")


if __name__ == "__main__":
    main()
