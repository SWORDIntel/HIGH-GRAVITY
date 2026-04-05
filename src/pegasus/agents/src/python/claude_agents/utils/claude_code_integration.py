# Claude Code Task Tool Integration for Project Agents
# Integrates all 42 project agents with Claude Code's Task tool system

"""
This module provides seamless integration between our project agents
and Claude Code's Task tool system. It registers all agents and provides
proper command routing.

Usage:
    Task(subagent_type="planner", prompt="Create project roadmap")
    Task(subagent_type="security", prompt="Perform security audit")
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Agent registry with all 42 project agents
PROJECT_AGENTS = {
    # Strategic & Planning
    "planner": {
        "name": "PLANNER",
        "description": "Strategic planning and roadmap specialist creating comprehensive project plans, milestone tracking, and task decomposition. Coordinates with Director and ProjectOrchestrator for complex initiatives.",
        "command": "claude-agent planner",
        "tools": ["*"],
    },
    "director": {
        "name": "DIRECTOR",
        "description": "Strategic command and control specialist providing high-level decision making, resource allocation, and project coordination. Central command hub for complex operations.",
        "command": "claude-agent director",
        "tools": ["*"],
    },
    "projectorchestrator": {
        "name": "PROJECTORCHESTRATOR",
        "description": "Tactical coordination nexus managing multi-agent workflows, dependency resolution, and execution orchestration. Works with Director for strategic alignment.",
        "command": "claude-agent projectorchestrator",
        "tools": ["*"],
    },
    "leadengineer": {
        "name": "LEADENGINEER",
        "description": "Parallel project orchestration specialist performing multi-threaded task decomposition and intelligent coordination.",
        "command": "claude-agent leadengineer",
        "tools": ["*"],
    },
    # Architecture & Design
    "architect": {
        "name": "ARCHITECT",
        "description": "System design and technical architecture specialist creating blueprints, patterns, and structural decisions for complex systems.",
        "command": "claude-agent architect",
        "tools": ["*"],
    },
    "apidesigner": {
        "name": "APIDESIGNER",
        "description": "API architecture and contract design specialist creating RESTful, GraphQL, and gRPC interfaces.",
        "command": "claude-agent apidesigner",
        "tools": ["*"],
    },
    "constructor": {
        "name": "CONSTRUCTOR",
        "description": "Project initialization and scaffolding specialist creating project structures, templates, and foundations.",
        "command": "claude-agent constructor",
        "tools": ["*"],
    },
    # Security Specialists
    "security": {
        "name": "SECURITY",
        "description": "Comprehensive security analysis specialist performing vulnerability scanning, penetration testing, threat modeling, and compliance verification.",
        "command": "claude-agent security",
        "tools": ["*"],
    },
    "quantumguard": {
        "name": "QUANTUMGUARD",
        "description": "Elite quantum-resistant cryptography specialist implementing NIST PQC standards, zero-trust architectures, and lattice-based cryptosystems.",
        "command": "claude-agent quantumguard",
        "tools": ["*"],
    },
    "bastion": {
        "name": "BASTION",
        "description": "Defensive security specialist implementing secure networks, VPN protocols, and hardened system configurations.",
        "command": "claude-agent bastion",
        "tools": ["*"],
    },
    "cso": {
        "name": "CSO",
        "description": "Chief Security Officer providing strategic security oversight, policy development, and enterprise security governance.",
        "command": "claude-agent cso",
        "tools": ["*"],
    },
    "cryptoexpert": {
        "name": "CRYPTOEXPERT",
        "description": "Cryptography specialist implementing encryption, digital signatures, key management, and cryptographic protocols.",
        "command": "claude-agent cryptoexpert",
        "tools": ["*"],
    },
    "securityauditor": {
        "name": "SECURITYAUDITOR",
        "description": "Security audit specialist performing comprehensive security assessments, compliance audits, and penetration testing.",
        "command": "claude-agent securityauditor",
        "tools": ["*"],
    },
    "securitychaosagent": {
        "name": "SECURITYCHAOSAGENT",
        "description": "Distributed security chaos testing agent coordinating parallel vulnerability scanning and stress testing.",
        "command": "claude-agent securitychaosagent",
        "tools": ["*"],
    },
    "redteamorchestrator": {
        "name": "REDTEAMORCHESTRATOR",
        "description": "Red team operations coordinator managing offensive security testing, attack simulations, and adversarial assessments.",
        "command": "claude-agent redteamorchestrator",
        "tools": ["*"],
    },
    # Development & Code Quality
    "linter": {
        "name": "LINTER",
        "description": "Senior code review specialist providing line-addressed static analysis, style improvements, and safety recommendations.",
        "command": "claude-agent linter",
        "tools": ["*"],
    },
    "patcher": {
        "name": "PATCHER",
        "description": "Precision code surgery specialist implementing targeted fixes, patches, and surgical code modifications.",
        "command": "claude-agent patcher",
        "tools": ["*"],
    },
    "debugger": {
        "name": "DEBUGGER",
        "description": "Tactical failure analysis specialist performing root cause analysis, debugging, and issue resolution.",
        "command": "claude-agent debugger",
        "tools": ["*"],
    },
    "optimizer": {
        "name": "OPTIMIZER",
        "description": "Performance engineering specialist analyzing bottlenecks, optimizing code, and improving system efficiency.",
        "command": "claude-agent optimizer",
        "tools": ["*"],
    },
    # Testing & Quality Assurance
    "testbed": {
        "name": "TESTBED",
        "description": "Elite test engineering specialist managing test suites, coverage analysis, and quality assurance.",
        "command": "claude-agent testbed",
        "tools": ["*"],
    },
    "qadirector": {
        "name": "QADIRECTOR",
        "description": "Quality assurance director managing testing strategies, QA processes, and quality standards across projects.",
        "command": "claude-agent qadirector",
        "tools": ["*"],
    },
    "oversight": {
        "name": "OVERSIGHT",
        "description": "Quality assurance and compliance specialist ensuring code quality, security standards, and regulatory compliance.",
        "command": "claude-agent oversight",
        "tools": ["*"],
    },
    # Infrastructure & Deployment
    "infrastructure": {
        "name": "INFRASTRUCTURE",
        "description": "System setup and configuration specialist managing servers, cloud resources, and DevOps infrastructure.",
        "command": "claude-agent infrastructure",
        "tools": ["*"],
    },
    "deployer": {
        "name": "DEPLOYER",
        "description": "Infrastructure and deployment orchestration specialist managing CI/CD pipelines and production rollouts.",
        "command": "claude-agent deployer",
        "tools": ["*"],
    },
    "packager": {
        "name": "PACKAGER",
        "description": "Package management and distribution specialist handling npm, pip, Docker, and software distribution.",
        "command": "claude-agent packager",
        "tools": ["*"],
    },
    "monitor": {
        "name": "MONITOR",
        "description": "Observability and monitoring specialist establishing comprehensive logging, metrics, and alerting infrastructure.",
        "command": "claude-agent monitor",
        "tools": ["*"],
    },
    # Data & Machine Learning
    "database": {
        "name": "DATABASE",
        "description": "Data architecture and database optimization specialist handling schema design, query optimization, and data modeling.",
        "command": "claude-agent database",
        "tools": ["*"],
    },
    "datascience": {
        "name": "DATASCIENCE",
        "description": "Data analysis and machine learning specialist working with pandas, numpy, scikit-learn, and ML pipelines.",
        "command": "claude-agent datascience",
        "tools": ["*"],
    },
    "mlops": {
        "name": "MLOPS",
        "description": "Machine learning operations specialist managing ML pipelines, model deployment, and production ML systems.",
        "command": "claude-agent mlops",
        "tools": ["*"],
    },
    # User Interface Development
    "web": {
        "name": "WEB",
        "description": "Modern web development specialist handling React, Vue, Angular, and full-stack web applications.",
        "command": "claude-agent web",
        "tools": ["*"],
    },
    "tui": {
        "name": "TUI",
        "description": "Terminal user interface specialist creating ncurses-based console applications and CLI tools.",
        "command": "claude-agent tui",
        "tools": ["*"],
    },
    "pygui": {
        "name": "PYGUI",
        "description": "Python GUI development specialist working with Tkinter, PyQt, Streamlit, and desktop applications.",
        "command": "claude-agent pygui",
        "tools": ["*"],
    },
    "mobile": {
        "name": "MOBILE",
        "description": "Mobile development specialist handling iOS, Android, and React Native cross-platform applications.",
        "command": "claude-agent mobile",
        "tools": ["*"],
    },
    "androidmobile": {
        "name": "ANDROIDMOBILE",
        "description": "Android mobile development specialist handling native Android apps, Kotlin/Java development, and mobile architecture.",
        "command": "claude-agent androidmobile",
        "tools": ["*"],
    },
    # Systems & Low-Level
    "c-internal": {
        "name": "C-INTERNAL",
        "description": "Elite C/C++ systems engineer specializing in low-level programming, kernel development, and systems optimization.",
        "command": "claude-agent c-internal",
        "tools": ["*"],
    },
    "python-internal": {
        "name": "PYTHON-INTERNAL",
        "description": "Python runtime and environment specialist managing virtual environments, dependencies, and Python internals.",
        "command": "claude-agent python-internal",
        "tools": ["*"],
    },
    "gnu": {
        "name": "GNU",
        "description": "GNU/Linux systems specialist managing system-level operations, package management, and Unix/Linux environment optimization.",
        "command": "claude-agent gnu",
        "tools": ["*"],
    },
    # Hardware & Acceleration
    "npu": {
        "name": "NPU",
        "description": "Neural processing unit specialist optimizing AI/ML workloads for hardware acceleration and inference optimization.",
        "command": "claude-agent npu",
        "tools": ["*"],
    },
    "gna": {
        "name": "GNA",
        "description": "Gaussian Neural Accelerator specialist optimizing neural network inference for Intel hardware acceleration.",
        "command": "claude-agent gna",
        "tools": ["*"],
    },
    # Documentation & Research
    "docgen": {
        "name": "DOCGEN",
        "description": "Elite documentation engineering specialist generating comprehensive technical documentation with military precision.",
        "command": "claude-agent docgen",
        "tools": ["*"],
    },
    "researcher": {
        "name": "RESEARCHER",
        "description": "Technology evaluation and research specialist conducting market analysis, competitive research, and feasibility studies.",
        "command": "claude-agent researcher",
        "tools": ["*"],
    },
    # Integration & Organization
    "intergration": {
        "name": "INTERGRATION",
        "description": "System integration specialist managing API integrations, service mesh, and inter-system communication.",
        "command": "claude-agent intergration",
        "tools": ["*"],
    },
    "organization": {
        "name": "ORGANIZATION",
        "description": "Project organization specialist managing workflows, team coordination, and organizational process optimization.",
        "command": "claude-agent organization",
        "tools": ["*"],
    },
}


def invoke_project_agent(agent_type: str, prompt: str) -> Dict[str, Any]:
    """
    Invoke a project agent through the claude-agent command system.

    Args:
        agent_type: The agent type identifier (e.g., 'planner', 'security')
        prompt: The task prompt for the agent

    Returns:
        Dict containing execution results, output, and metadata
    """

    # Normalize agent type
    agent_type = agent_type.lower().replace("_", "-").replace(" ", "-")

    if agent_type not in PROJECT_AGENTS:
        return {
            "error": f"Agent '{agent_type}' not found",
            "available": list(PROJECT_AGENTS.keys()),
            "suggestion": f"Try one of: {', '.join(sorted(PROJECT_AGENTS.keys())[:5])}",
        }

    agent = PROJECT_AGENTS[agent_type]

    try:
        # Execute through claude-agent command with proper environment
        env = os.environ.copy()
        env["CLAUDE_AGENTS_ROOT"] = str(PROJECT_ROOT / "agents")
        env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"

        result = subprocess.run(
            ["claude-agent", agent_type, prompt],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env=env,
            cwd=str(PROJECT_ROOT),
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip() if result.stdout else "",
            "error": (
                result.stderr.strip()
                if result.stderr and result.returncode != 0
                else None
            ),
            "agent": agent["name"],
            "agent_type": agent_type,
            "command": agent["command"],
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "error": f"Agent '{agent_type}' timed out after 5 minutes",
            "agent": agent["name"],
            "agent_type": agent_type,
        }
    except FileNotFoundError:
        return {
            "error": f"claude-agent command not found. Ensure the agent system is properly installed.",
            "agent": agent["name"],
            "agent_type": agent_type,
            "suggestion": "Run the claude-installer.sh to set up the agent system",
        }
    except Exception as e:
        return {
            "error": f"Unexpected error invoking agent: {str(e)}",
            "agent": agent["name"],
            "agent_type": agent_type,
        }


def get_available_agents() -> List[str]:
    """Get list of all available project agents."""
    return sorted(PROJECT_AGENTS.keys())


def get_agent_info(agent_type: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a specific agent."""
    agent_type = agent_type.lower().replace("_", "-").replace(" ", "-")
    return PROJECT_AGENTS.get(agent_type)


def register_with_claude_code():
    """
    Register all project agents with Claude Code's Task tool system.
    This function should be called during Claude Code initialization.
    """
    try:
        # Try to import Claude Code modules if available
        import claude_code

        for agent_id, agent_info in PROJECT_AGENTS.items():
            claude_code.register_agent(agent_id, invoke_project_agent)

        return {
            "success": True,
            "registered_agents": len(PROJECT_AGENTS),
            "agents": list(PROJECT_AGENTS.keys()),
        }

    except ImportError:
        # Claude Code module not available - this is expected in some environments
        return {
            "success": False,
            "error": "Claude Code module not available for direct registration",
            "fallback": "Agents available through claude-agent command system",
        }
    except Exception as e:
        return {"success": False, "error": f"Registration failed: {str(e)}"}


def create_claude_config():
    """
    Create Claude Code configuration files for project agent integration.
    """
    config_dir = Path.home() / ".config" / "claude"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create agents configuration
    agents_config = {
        "version": "2.0.0",
        "project_agents": PROJECT_AGENTS,
        "agent_mappings": {
            **{name: name for name in PROJECT_AGENTS.keys()},
            **{info["name"]: name for name, info in PROJECT_AGENTS.items()},
            **{name.upper(): name for name in PROJECT_AGENTS.keys()},
        },
    }

    config_file = config_dir / "project-agents-v2.json"
    with open(config_file, "w") as f:
        json.dump(agents_config, f, indent=2)

    return str(config_file)


# Auto-register on import if running in Claude Code context
if __name__ != "__main__":
    try:
        result = register_with_claude_code()
        # Silently handle registration - don't spam logs
    except:
        pass  # Fail silently in case of any issues

# Export main functions
__all__ = [
    "PROJECT_AGENTS",
    "invoke_project_agent",
    "get_available_agents",
    "get_agent_info",
    "register_with_claude_code",
    "create_claude_config",
]
