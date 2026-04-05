#!/usr/bin/env python3
"""
Analyze which agents have Python implementations vs which are missing
"""

import os
from pathlib import Path


def get_all_agents():
    """Get list of all agent definition files"""
    # Go up two levels: python -> src -> agents
    agents_dir = Path(__file__).parent.parent.parent.absolute()
    agent_files = []

    print(f"Debug: Looking for agents in {agents_dir}")

    for md_file in agents_dir.glob("*.md"):
        if md_file.name not in [
            "Template.md",
            "Agents Readme.md",
            "WHERE_I_AM.md",
            "TEMPLATE.md",
        ]:
            agent_name = md_file.stem
            agent_files.append(agent_name.lower())

    return sorted(agent_files)


def get_python_implementations():
    """Get list of agents with Python implementations"""
    python_dir = Path(__file__).parent
    impl_files = []

    for impl_file in python_dir.glob("*_impl.py"):
        agent_name = impl_file.stem.replace("_impl", "")
        impl_files.append(agent_name.lower())

    return sorted(impl_files)


def analyze_production_orchestrator_routing():
    """Check which agents are routed in production orchestrator"""
    orchestrator_file = Path(__file__).parent / "production_orchestrator.py"

    if not orchestrator_file.exists():
        return []

    with open(orchestrator_file, "r") as f:
        content = f.read()

    # Find agents in _invoke_real_agent method
    routed_agents = []
    lines = content.split("\n")
    in_real_agent_method = False

    for line in lines:
        if "def _invoke_real_agent" in line:
            in_real_agent_method = True
        elif in_real_agent_method and line.strip().startswith("def "):
            break
        elif in_real_agent_method and "elif agent_name ==" in line:
            # Extract agent name from line like: elif agent_name == "optimizer":
            import re

            match = re.search(r'agent_name == "([^"]+)"', line)
            if match:
                routed_agents.append(match.group(1))

    return sorted(routed_agents)


def main():
    print("🔍 Agent Implementation Status Analysis")
    print("=" * 60)

    all_agents = get_all_agents()
    python_implementations = get_python_implementations()
    routed_agents = analyze_production_orchestrator_routing()

    print(f"📊 Summary:")
    print(f"   Total Agents: {len(all_agents)}")
    print(f"   Python Implementations: {len(python_implementations)}")
    print(f"   Orchestrator Routing: {len(routed_agents)}")

    # Find missing implementations
    missing_implementations = set(all_agents) - set(python_implementations)

    # Find implementations not routed
    not_routed = set(python_implementations) - set(routed_agents)

    print(
        f"\n🚫 Agents Missing Python Implementations ({len(missing_implementations)}):"
    )
    for agent in sorted(missing_implementations):
        print(f"   - {agent.upper()}")

    print(f"\n⚠️ Agents with Implementations but Not Routed ({len(not_routed)}):")
    for agent in sorted(not_routed):
        print(f"   - {agent.upper()}")

    print(
        f"\n✅ Agents Fully Implemented and Routed ({len(set(python_implementations) & set(routed_agents))}):"
    )
    implemented_and_routed = set(python_implementations) & set(routed_agents)
    for agent in sorted(implemented_and_routed):
        print(f"   - {agent.upper()}")

    # Check for critical missing agents
    critical_agents = [
        "architect",
        "constructor",
        "debugger",
        "deployer",
        "infrastructure",
        "linter",
        "patcher",
        "packager",
        "oversight",
        "bastion",
        "tui",
        "researcher",
        "planner",
    ]

    missing_critical = set(critical_agents) & missing_implementations

    if missing_critical:
        print(f"\n🚨 CRITICAL Missing Implementations ({len(missing_critical)}):")
        for agent in sorted(missing_critical):
            print(f"   - {agent.upper()}")

    # Categorize missing agents by type
    categories = {
        "Development": ["architect", "constructor", "debugger", "linter", "patcher"],
        "Infrastructure": ["deployer", "infrastructure", "packager"],
        "Security": [
            "bastion",
            "oversight",
            "cryptoexpert",
            "cso",
            "securityauditor",
            "securitychaosagent",
            "redteamorchestrator",
        ],
        "UI/Interface": ["tui", "androidmobile"],
        "Planning": ["planner", "researcher", "qadirector", "leadengineer"],
        "System": [
            "c-internal",
            "python-internal",
            "gna",
            "npu",
            "statusline_integration",
        ],
        "Organization": ["organization", "intergration"],
    }

    print(f"\n📋 Missing Implementations by Category:")
    for category, agents in categories.items():
        missing_in_category = set(agents) & missing_implementations
        if missing_in_category:
            print(f"   {category}: {len(missing_in_category)} missing")
            for agent in sorted(missing_in_category):
                print(f"     - {agent.upper()}")


if __name__ == "__main__":
    main()
