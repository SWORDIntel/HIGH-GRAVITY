"""
Agent Organizational System
============================

Corporate-style organizational structure for multi-agent systems with
executive leadership, middle management, and specialized workers.

Organizational Hierarchy:
------------------------
1. Executive (C-Level)
   - DIRECTOR: Overall strategic direction
   - CSO: Security and compliance
   - CTO: Technology strategy
   - Lead Engineer: Technical excellence

2. Senior Management
   - PROJECTORCHESTRATOR: Project coordination
   - Division Heads: Software, Security, Infrastructure, QA

3. Middle Management
   - Team Leads: Python, C, Rust, Go, Security, Testing
   - Senior Specialists

4. Workers
   - Language-specific agents: PYTHON-INTERNAL, C-INTERNAL, etc.
   - Domain specialists: DEBUGGER, TESTBED, SECURITY, etc.

Key Features:
-------------
- Chain of command enforcement
- Authority-based approvals
- Division-based organization
- Escalation mechanisms
- Special reporting (e.g., CHAOS → CSO only)

Quick Start:
-----------

```python
from claude_agents.organization import (
    create_standard_organization,
    HierarchicalOrchestrator,
    Agent
)

# Create organization
org = create_standard_organization()

# Create agents and assign to positions
director = Agent(
    agent_id="director_001",
    agent_name="DIRECTOR",
    position=org.positions["DIRECTOR"]
)
org.assign_agent(director)

# Create orchestrator
orchestrator = HierarchicalOrchestrator(org)

# Request work (goes through approval chain)
task_id = orchestrator.request_work(
    description="Implement authentication system",
    required_capabilities=["system_design", "security"],
    requested_by="architect_001",
    priority=Priority.HIGH
)

# Work flows through: Request → Approval → Assignment → Execution
```

For full documentation, see: docs/ORGANIZATIONAL_HIERARCHY.md
"""

from .hierarchy import (
    Agent,
    AuthorityLevel,
    Division,
    OrganizationalChart,
    OrganizationalLevel,
    Position,
    create_standard_organization,
)

from .hierarchical_orchestrator import (
    HierarchicalOrchestrator,
    TaskStatus,
    WorkTask,
)

from .accurate_complete_mapping import (
    create_accurate_complete_organization,
    get_agent_statistics,
)

# Deprecated: Old Phase 1 and Phase 2 mappings (kept for backwards compatibility)
from .complete_agent_mapping import (
    create_complete_organization,
)

from .phase2_complete_mapping import (
    add_phase2_agents,
    create_phase2_complete_organization,
)

__all__ = [
    # Hierarchy
    "Agent",
    "AuthorityLevel",
    "Division",
    "OrganizationalChart",
    "OrganizationalLevel",
    "Position",
    "create_standard_organization",
    # Orchestration
    "HierarchicalOrchestrator",
    "TaskStatus",
    "WorkTask",
    # Accurate Complete Mapping (v3.0 - ALL 88 agents)
    "create_accurate_complete_organization",  # ✅ Accurate: All 88 agents
    "get_agent_statistics",  # Statistics about the organization
    # Deprecated Mappings (backwards compatibility only)
    "create_complete_organization",  # ⚠️ DEPRECATED: Phase 1 (incomplete)
    "add_phase2_agents",  # ⚠️ DEPRECATED: Phase 2 (incomplete)
    "create_phase2_complete_organization",  # ⚠️ DEPRECATED: Phase 2 (incomplete)
]

__version__ = "3.0.0"  # Accurate complete mapping with all 88 agents
__author__ = "SWORDSwarm Organizational System"
