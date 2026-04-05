#!/usr/bin/env python3
"""
Add logical colors to all Claude Agent Framework v7.0 agents
Based on functional categories for visual identification
"""

import os
import re

import yaml

# Professional color scheme for different agent categories
AGENT_COLORS = {
    # Command & Control - Red tones (Leadership)
    "director": "#DC2626",  # Red-600
    "projectorchestrator": "#B91C1C",  # Red-700
    # Security - Orange/Red tones (Security)
    "security": "#EA580C",  # Orange-600
    "bastion": "#C2410C",  # Orange-700
    "securitychaosagent": "#9A3412",  # Orange-800
    "oversight": "#F97316",  # Orange-500
    "cso": "#D97706",  # Orange-600
    "cryptoexpert": "#B45309",  # Orange-700
    "securityauditor": "#92400E",  # Orange-800
    # Core Development - Blue tones (Engineering)
    "architect": "#2563EB",  # Blue-600
    "constructor": "#1D4ED8",  # Blue-700
    "patcher": "#1E40AF",  # Blue-800
    "debugger": "#3B82F6",  # Blue-500
    "testbed": "#1E3A8A",  # Blue-900
    "linter": "#1E40AF",  # Blue-800
    "optimizer": "#2563EB",  # Blue-600
    "leadengineer": "#1D4ED8",  # Blue-700
    "qadirector": "#3730A3",  # Blue-800
    # Infrastructure - Green tones (Systems)
    "infrastructure": "#059669",  # Green-600
    "deployer": "#047857",  # Green-700
    "monitor": "#065F46",  # Green-800
    "packager": "#10B981",  # Green-500
    "gnu": "#16A34A",  # Green-600
    # Specialists - Purple tones (Expertise)
    "apidesigner": "#7C3AED",  # Purple-600
    "database": "#6D28D9",  # Purple-700
    "web": "#5B21B6",  # Purple-800
    "mobile": "#8B5CF6",  # Purple-500
    "pygui": "#7C2D12",  # Purple-700
    "tui": "#581C87",  # Purple-900
    "datascience": "#A855F7",  # Purple-500
    "mlops": "#9333EA",  # Purple-600
    "npu": "#7E22CE",  # Purple-700
    # Internal Systems - Teal tones (Core)
    "c-internal": "#0D9488",  # Teal-600
    "python-internal": "#0F766E",  # Teal-700
    # Support - Gray/Slate tones (Support)
    "researcher": "#475569",  # Slate-600
    "docgen": "#334155",  # Slate-700
    "planner": "#1E293B",  # Slate-800
    "statusline_integration": "#64748B",  # Slate-500
    # Template - Gold (Special)
    "template": "#D97706",  # Amber-600
}


def add_color_to_agent(filepath):
    """Add color field to agent YAML frontmatter"""

    # Read current file
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract agent name from file
    filename = os.path.basename(filepath)
    agent_name = filename.replace(".md", "").lower()

    # Handle special cases
    if agent_name == "projectorchestrator":
        agent_name = "projectorchestrator"
    elif agent_name == "statusline_integration":
        agent_name = "statusline_integration"

    # Get color for this agent
    if agent_name not in AGENT_COLORS:
        print(f"⚠️  No color defined for {agent_name}")
        return False

    color = AGENT_COLORS[agent_name]

    # Check if file has YAML frontmatter
    if not content.startswith("---"):
        print(f"❌ {filename} - No YAML frontmatter found")
        return False

    # Split content into frontmatter and body
    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"❌ {filename} - Invalid YAML frontmatter structure")
        return False

    yaml_content = parts[1].strip()
    body_content = parts[2]

    # Parse existing YAML
    try:
        yaml_data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        print(f"❌ {filename} - YAML parsing error: {e}")
        return False

    # Add color field
    yaml_data["color"] = color

    # Regenerate YAML with proper order
    ordered_yaml = f"""name: {yaml_data['name']}
description: {yaml_data['description']}
color: {yaml_data['color']}
tools:"""

    for tool in yaml_data.get("tools", []):
        ordered_yaml += f"\n  - {tool}"

    # Reconstruct file content
    new_content = f"---\n{ordered_yaml}\n---{body_content}"

    # Write updated content
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ {filename} - Added color {color}")
    return True


def get_color_name(hex_color):
    """Get human-readable color name from hex"""
    color_names = {
        "#DC2626": "Red-600",
        "#B91C1C": "Red-700",
        "#EA580C": "Orange-600",
        "#C2410C": "Orange-700",
        "#9A3412": "Orange-800",
        "#F97316": "Orange-500",
        "#D97706": "Orange-600",
        "#B45309": "Orange-700",
        "#92400E": "Orange-800",
        "#2563EB": "Blue-600",
        "#1D4ED8": "Blue-700",
        "#1E40AF": "Blue-800",
        "#3B82F6": "Blue-500",
        "#1E3A8A": "Blue-900",
        "#3730A3": "Blue-800",
        "#059669": "Green-600",
        "#047857": "Green-700",
        "#065F46": "Green-800",
        "#10B981": "Green-500",
        "#16A34A": "Green-600",
        "#7C3AED": "Purple-600",
        "#6D28D9": "Purple-700",
        "#5B21B6": "Purple-800",
        "#8B5CF6": "Purple-500",
        "#7C2D12": "Purple-700",
        "#581C87": "Purple-900",
        "#A855F7": "Purple-500",
        "#9333EA": "Purple-600",
        "#7E22CE": "Purple-700",
        "#0D9488": "Teal-600",
        "#0F766E": "Teal-700",
        "#475569": "Slate-600",
        "#334155": "Slate-700",
        "#1E293B": "Slate-800",
        "#64748B": "Slate-500",
    }
    return color_names.get(hex_color, hex_color)


def main():
    """Add colors to all agent files"""

    print("🎨 Adding colors to Claude Agent Framework v7.0 agents")
    print("=" * 60)
    print()

    # Find all agent .md files
    agent_files = []
    for filename in os.listdir("."):
        if filename.endswith(".md") and filename not in [
            "Template.md",
            "README.md",
            "ORGANIZATION.md",
        ]:
            agent_files.append(filename)

    agent_files.sort()

    print(f"Found {len(agent_files)} agent files")
    print()

    # Add colors to each agent
    updated_count = 0
    for filepath in agent_files:
        if add_color_to_agent(filepath):
            updated_count += 1

    print()
    print(f"✅ Successfully added colors to {updated_count}/{len(agent_files)} agents")
    print()

    # Show color scheme summary
    print("🎨 Color Scheme Summary:")
    print("=" * 40)

    categories = {
        "Command & Control": ["director", "projectorchestrator"],
        "Security": [
            "security",
            "bastion",
            "securitychaosagent",
            "oversight",
            "cso",
            "cryptoexpert",
            "securityauditor",
        ],
        "Development": [
            "architect",
            "constructor",
            "patcher",
            "debugger",
            "testbed",
            "linter",
            "optimizer",
            "leadengineer",
            "qadirector",
        ],
        "Infrastructure": ["infrastructure", "deployer", "monitor", "packager", "gnu"],
        "Specialists": [
            "apidesigner",
            "database",
            "web",
            "mobile",
            "pygui",
            "tui",
            "datascience",
            "mlops",
            "npu",
        ],
        "Internal Systems": ["c-internal", "python-internal"],
        "Support": ["researcher", "docgen", "planner", "statusline_integration"],
        "Special": ["template"],
    }

    for category, agents in categories.items():
        print(f"\n{category}:")
        for agent in agents:
            if agent in AGENT_COLORS:
                color = AGENT_COLORS[agent]
                color_name = get_color_name(color)
                print(f"  {agent:20} → {color} ({color_name})")

    print()
    print("Colors follow professional design principles:")
    print("  🔴 Red/Orange: Leadership & Security")
    print("  🔵 Blue: Engineering & Development")
    print("  🟢 Green: Infrastructure & Systems")
    print("  🟣 Purple: Specialized Expertise")
    print("  🟦 Teal: Internal Core Systems")
    print("  ⚫ Gray: Support Functions")


if __name__ == "__main__":
    main()
