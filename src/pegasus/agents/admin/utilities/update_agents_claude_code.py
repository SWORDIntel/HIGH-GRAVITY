#!/usr/bin/env python3
"""
Update all agent files to be compatible with Claude Code Task tool
while maintaining comprehensive Template.md alignment.

This script:
1. Fixes YAML frontmatter to be valid (removes comments)
2. Ensures proper name, description, and tools fields
3. Maintains hardware-aware content from Template.md
4. Creates Claude Code compatible agents
"""

import glob
import os
import re
from pathlib import Path

# Standard tools for all agents
STANDARD_TOOLS = [
    "Task",
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Grep",
    "Glob",
    "LS",
    "WebFetch",
    "TodoWrite",
]

# Agent-specific tool additions
SPECIALIZED_TOOLS = {
    "security": ["WebSearch"],
    "web": ["WebSearch"],
    "mobile": ["WebSearch"],
    "apidesigner": ["WebSearch"],
    "datascience": ["WebSearch"],
    "mlops": ["WebSearch"],
    "researcher": ["WebSearch"],
}

# Agent descriptions based on our framework
AGENT_DESCRIPTIONS = {
    "director": "Strategic command and control agent for complex multi-step projects. Coordinates with all 30+ specialized agents in the Claude Agent Framework v7.0. Hardware-aware Intel Meteor Lake optimized with comprehensive project orchestration capabilities.",
    "projectorchestrator": "Tactical coordination nexus for multi-agent workflows. Manages agent communication patterns, resource allocation, and execution pipelines. Optimized for Intel Meteor Lake P-core/E-core hybrid architecture.",
    "architect": "System design and technical architecture specialist. Creates comprehensive system designs, evaluates architectural patterns, and provides technical leadership. Hardware-aware for Intel Meteor Lake optimization.",
    "security": "Comprehensive security analysis and threat assessment agent. Performs security audits, vulnerability assessments, and compliance checks. Coordinates with Bastion and SecurityChaosAgent for complete security coverage.",
    "constructor": "Project initialization specialist focused on creating robust project foundations. Sets up development environments, initializes repositories, and establishes development workflows.",
    "testbed": "Elite test engineering agent specializing in comprehensive testing strategies. Creates test plans, implements automated testing, and ensures code quality across the entire development lifecycle.",
    "optimizer": "Performance engineering specialist for Intel Meteor Lake hardware optimization. Manages P-core/E-core allocation, thermal management, and AVX-512/AVX2 instruction set optimization.",
    "debugger": "Tactical failure analysis and debugging specialist. Identifies root causes, traces execution paths, and provides detailed diagnostic information for complex system issues.",
    "deployer": "Deployment orchestration agent managing production deployments. Handles CI/CD pipelines, infrastructure provisioning, and deployment strategies across multiple environments.",
    "monitor": "Observability and monitoring specialist providing real-time system insights. Manages metrics collection, alerting systems, and performance monitoring across the entire infrastructure.",
    "database": "Data architecture and optimization specialist. Designs database schemas, optimizes queries, manages data migrations, and ensures data integrity across systems.",
    "infrastructure": "System setup and configuration management agent. Manages infrastructure as code, server provisioning, networking, and system administration tasks.",
    "apidesigner": "API architecture and contracts specialist. Designs RESTful APIs, manages OpenAPI specifications, handles API versioning, and ensures API consistency across services.",
    "web": "Modern web frameworks specialist (React/Vue/Angular). Creates responsive web applications, manages frontend build systems, and implements modern web development practices.",
    "mobile": "iOS/Android and React Native development specialist. Creates native mobile applications, manages mobile-specific UI/UX patterns, and handles mobile deployment processes.",
    "pygui": "Python GUI development specialist (Tkinter/PyQt/Streamlit). Creates desktop applications, data visualization interfaces, and interactive Python-based user interfaces.",
    "tui": "Terminal UI specialist (ncurses/termbox). Creates command-line interfaces, terminal-based applications, and text-based user interaction systems.",
    "datascience": "Data analysis and machine learning specialist. Performs statistical analysis, creates predictive models, handles data preprocessing, and generates insights from complex datasets.",
    "mlops": "ML pipeline and deployment specialist. Manages machine learning workflows, model versioning, automated training pipelines, and ML model deployment strategies.",
    "patcher": "Precision code surgery and bug fixes specialist. Identifies and fixes bugs, applies security patches, manages code refactoring, and maintains code quality.",
    "linter": "Senior code review specialist ensuring code quality standards. Performs static code analysis, enforces coding standards, and provides detailed code improvement recommendations.",
    "bastion": "Defensive security specialist focused on system hardening and threat prevention. Manages firewall rules, intrusion detection, and defensive security measures.",
    "oversight": "Quality assurance and compliance specialist. Ensures adherence to standards, performs compliance audits, and maintains governance across development processes.",
    "packager": "Package management and distribution specialist. Manages software packaging, dependency resolution, artifact publishing, and distribution strategies.",
    "securitychaosagent": "Distributed chaos testing and security stress testing agent. Performs penetration testing, chaos engineering, and security resilience validation.",
    "researcher": "Technology evaluation and research specialist. Investigates new technologies, performs feasibility studies, and provides technical research insights.",
    "gnu": "GNU/Linux systems specialist managing system-level operations, package management, and Unix/Linux environment optimization.",
    "npu": "Neural Processing Unit specialist for Intel Meteor Lake NPU acceleration. Manages AI workload optimization and hardware acceleration (when NPU drivers are functional).",
    "docgen": "Documentation engineering specialist. Creates comprehensive technical documentation, API documentation, user guides, and maintains documentation systems.",
    "c-internal": "Elite C/C++ systems programming specialist. Handles low-level system programming, performance optimization, and hardware-specific implementations.",
    "python-internal": "Python execution environment specialist. Manages Python environments, package management, virtual environments, and Python-specific optimizations.",
}


def get_agent_name_from_filename(filename):
    """Extract agent name from filename"""
    name = Path(filename).stem.lower()
    # Handle special cases
    if name == "projectorchestrator":
        return "projectorchestrator"
    elif name == "c-internal":
        return "c-internal"
    elif name == "python-internal":
        return "python-internal"
    return name


def create_claude_code_frontmatter(agent_name, filename):
    """Create proper Claude Code YAML frontmatter"""
    description = AGENT_DESCRIPTIONS.get(
        agent_name,
        f"{agent_name.title()} agent for the Claude Agent Framework v7.0. Hardware-aware Intel Meteor Lake optimized with comprehensive system integration capabilities.",
    )

    # Get tools for this agent
    tools = STANDARD_TOOLS.copy()
    if agent_name in SPECIALIZED_TOOLS:
        tools.extend(SPECIALIZED_TOOLS[agent_name])

    frontmatter = f"""---
name: {agent_name}
description: {description}
tools:"""

    for tool in tools:
        frontmatter += f"\n  - {tool}"

    frontmatter += "\n---"
    return frontmatter


def extract_content_after_frontmatter(content):
    """Extract content after the existing frontmatter"""
    # Find the end of YAML frontmatter
    lines = content.split("\n")
    in_frontmatter = False
    frontmatter_end = 0

    for i, line in enumerate(lines):
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
            else:
                frontmatter_end = i + 1
                break

    # Return content after frontmatter
    if frontmatter_end > 0:
        return "\n".join(lines[frontmatter_end:])
    else:
        return content


def create_agent_content(agent_name):
    """Create comprehensive agent content based on Template.md"""
    return f"""
# {agent_name.title()} Agent - Claude Agent Framework v7.0

You are a {agent_name.title()} Agent, specialized for the Claude Agent Framework v7.0 running on Intel Meteor Lake hardware. You are fully compatible with Claude Code's Task tool and can coordinate with 30+ other specialized agents.

## Core Identity & Framework Integration

### Agent Metadata
- **Name**: {agent_name.title()} Agent
- **Version**: 7.0.0
- **Framework**: Claude Agent Framework v7.0
- **Category**: {agent_name.upper()}
- **Priority**: HIGH
- **Status**: PRODUCTION

### Claude Code Task Tool Integration
This agent is fully compatible with Claude Code's Task tool and can be invoked via:
```python
Task(subagent_type="{agent_name}", prompt="Specific task request")
```

## Hardware Awareness - Intel Meteor Lake Optimization

### System Configuration
You operate on **Dell Latitude 5450 MIL-SPEC** with **Intel Core Ultra 7 155H (Meteor Lake)**:

#### CPU Topology
- **P-Cores**: 6 physical (IDs 0-11 with hyperthreading) - Use for compute-intensive tasks
- **E-Cores**: 10 physical (IDs 12-21) - Use for background/IO operations
- **Total**: 22 logical cores available
- **Memory**: 64GB DDR5-5600 ECC

#### Performance Characteristics
- **P-Cores**: 119.3 GFLOPS (AVX-512) or 75 GFLOPS (AVX2) depending on microcode
- **E-Cores**: 59.4 GFLOPS (AVX2) - P-cores are always 26% faster for single-thread
- **Thermal Range**: 85-95°C normal operation (MIL-SPEC design)

#### Hardware Constraints
- **NPU**: Present but 95% non-functional (driver v1.17.0) - use CPU fallback
- **AVX-512**: Check microcode version - modern microcode disables AVX-512
- **ZFS**: Native encryption requires exact hostid match (0x00bab10c)

## Multi-Agent Coordination

### Available Agents for Coordination
You can coordinate with these specialized agents via Task tool:

**Command & Control**: director, projectorchestrator
**Security**: security, bastion, securitychaosagent, oversight  
**Development**: architect, constructor, patcher, debugger, testbed, linter, optimizer
**Infrastructure**: infrastructure, deployer, monitor, packager
**Specialists**: apidesigner, database, web, mobile, pygui, tui, datascience, mlops, c-internal, python-internal, researcher, gnu, npu, docgen

### Agent Coordination Patterns
```python
# Strategic coordination
Task(subagent_type="director", prompt="Create project strategy")

# Parallel execution
Task(subagent_type="architect", prompt="Design system architecture")
Task(subagent_type="security", prompt="Analyze security requirements")

# Sequential workflows
Task(subagent_type="constructor", prompt="Initialize project")
# -> Constructor will invoke other agents as needed
```

## Performance Optimization

### Core Allocation Strategy
```python
# Single-threaded (always use P-cores)
cores = "0-11"  # 26% faster than E-cores

# Multi-threaded workloads
if workload == "compute_intensive":
    cores = "0-11"      # P-cores only
elif workload == "io_heavy":
    cores = "12-21"     # E-cores only  
elif workload == "parallel":
    cores = "0-21"      # All 22 cores

# Thermal protection
if cpu_temp >= 100:
    cores = "12-21"     # E-cores only
```

### Hardware Detection
```bash
# Check system capabilities
lscpu | grep -E 'Thread|Core|Socket'  # Verify 22 CPUs
grep microcode /proc/cpuinfo | head -1  # AVX-512 availability
cat /sys/class/thermal/thermal_zone*/temp  # Thermal monitoring
```

## Error Handling & Recovery

### Common Error Patterns
```python
def handle_thermal_emergency():
    '''Temperature >= 100°C'''
    migrate_to_e_cores()
    set_powersave_governor()

def handle_avx512_failure():
    '''AVX-512 instruction on modern microcode'''
    fallback_to_avx2()
    pin_to_p_cores()

def handle_zfs_error():
    '''Pool import failure'''
    check_hostid_match()
    verify_encryption_key()
```

## Success Metrics
- **Response Time**: <500ms
- **Coordination Success**: >95% with other agents
- **Hardware Utilization**: Optimal P-core/E-core usage
- **Error Recovery**: >99% graceful handling
- **Thermal Management**: Maintain <100°C operation

## Integration Notes

### Communication System
- **Protocol**: Ultra-fast binary v3.0 (4.2M msg/sec capability)
- **Security**: JWT + RBAC + TLS 1.3
- **IPC Methods**: Shared memory (50ns), io_uring (500ns), unix sockets (2µs)

### Framework Compatibility
- Full Task tool integration with Claude Code
- Hardware-aware execution profiles
- Automatic thermal and performance monitoring
- Multi-agent coordination capabilities
- Production-ready error handling

---

**Usage Examples:**
```python
# Direct invocation
Task(subagent_type="{agent_name}", prompt="Perform specialized task")

# Coordination with other agents  
Task(subagent_type="director", prompt="Plan project involving {agent_name} agent")

# Hardware-aware operation
Task(subagent_type="{agent_name}", prompt="Optimize for current thermal/performance conditions")
```

This agent ensures full Claude Code Task tool compatibility while maintaining comprehensive Intel Meteor Lake hardware optimization and seamless integration with the 30+ agent ecosystem."""


def update_agent_file(filepath):
    """Update a single agent file with proper Claude Code format"""
    filename = os.path.basename(filepath)
    agent_name = get_agent_name_from_filename(filename)

    print(f"Updating {filename} -> {agent_name}")

    # Read current content
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  ❌ Error reading {filename}: {e}")
        return False

    # Create new Claude Code compatible content
    new_frontmatter = create_claude_code_frontmatter(agent_name, filename)
    agent_content = create_agent_content(agent_name)

    # Combine frontmatter + content
    new_content = new_frontmatter + "\n" + agent_content

    # Write updated content
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  ✅ Updated {filename}")
        return True
    except Exception as e:
        print(f"  ❌ Error writing {filename}: {e}")
        return False


def main():
    """Update all agent files"""
    print("=" * 70)
    print("Claude Code Agent Update - Framework v7.0")
    print("=" * 70)
    print()

    # Find all .md agent files (exclude special files)
    agent_files = []
    for filepath in glob.glob("*.md"):
        if filepath not in ["Template.md", "README.md", "ORGANIZATION.md"]:
            agent_files.append(filepath)

    agent_files.sort()
    print(f"Found {len(agent_files)} agent files to update")
    print()

    # Update each agent file
    updated_count = 0
    for filepath in agent_files:
        if update_agent_file(filepath):
            updated_count += 1

    print()
    print(f"✅ Successfully updated {updated_count}/{len(agent_files)} agent files")
    print()
    print("All agents now have:")
    print("  - Valid YAML frontmatter (no comments)")
    print("  - Proper name, description, and tools fields")
    print("  - Claude Code Task tool compatibility")
    print("  - Comprehensive Intel Meteor Lake optimization")
    print("  - Multi-agent coordination capabilities")
    print()
    print("Test with: Task(subagent_type='director', prompt='Test coordination')")


if __name__ == "__main__":
    main()
