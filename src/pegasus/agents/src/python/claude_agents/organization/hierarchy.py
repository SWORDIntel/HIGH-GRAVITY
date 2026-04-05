#!/usr/bin/env python3
"""
Agent Organizational Hierarchy System
======================================

Implements a corporate-style organizational structure for multi-agent systems
with executive leadership, middle management, and specialized workers.

Organizational Levels:
1. Executive (C-Level): DIRECTOR, CSO, CTO, Lead Engineer
2. Senior Management: Project Managers, Division Heads
3. Middle Management: Team Leads, Senior Specialists
4. Workers: Specialized agents (language-specific, domain-specific)

Authority Structure:
- Executives can delegate to anyone, override decisions, escalate globally
- Senior Managers can delegate within division, escalate to executives
- Middle Managers can delegate to team members, escalate to division head
- Workers execute tasks, escalate to team lead

Author: SWORDSwarm Organizational System
Version: 1.0.0
Status: PRODUCTION
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class OrganizationalLevel(Enum):
    """Organizational hierarchy levels"""

    EXECUTIVE = 1           # C-Level: DIRECTOR, CSO, CTO
    SENIOR_MANAGEMENT = 2   # PMO, Division Heads
    MIDDLE_MANAGEMENT = 3   # Team Leads, Senior Specialists
    WORKER = 4              # Individual contributors
    INTERN = 5              # Limited scope agents


class Division(Enum):
    """Corporate divisions"""

    EXECUTIVE = "executive"                    # C-Suite
    SOFTWARE_ENGINEERING = "software"          # All development
    SECURITY = "security"                      # Security & compliance
    INFRASTRUCTURE = "infrastructure"          # DevOps, deployment
    QUALITY_ASSURANCE = "qa"                  # Testing & validation
    ARCHITECTURE = "architecture"              # System design
    DATA_SCIENCE = "data_science"             # ML/AI/Analytics
    OPERATIONS = "operations"                  # Monitoring, support


class AuthorityLevel(Enum):
    """Authority and decision-making levels"""

    STRATEGIC = "strategic"        # Company-wide decisions
    DIVISIONAL = "divisional"      # Division-level decisions
    TEAM = "team"                  # Team-level decisions
    INDIVIDUAL = "individual"      # Self-directed work
    SUPERVISED = "supervised"      # Requires approval


@dataclass
class Position:
    """Job position definition"""

    title: str
    level: OrganizationalLevel
    division: Division
    authority: AuthorityLevel

    # Capabilities and responsibilities
    capabilities: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)

    # Reporting structure
    reports_to: Optional[str] = None  # Position title
    manages: List[str] = field(default_factory=list)  # Position titles

    # Authority scope
    can_delegate_to: List[OrganizationalLevel] = field(default_factory=list)
    can_escalate_to: List[str] = field(default_factory=list)  # Position titles
    can_override: List[str] = field(default_factory=list)  # Position titles

    # Decision rights
    approval_required_for: List[str] = field(default_factory=list)
    can_approve: List[str] = field(default_factory=list)
    veto_power: bool = False

    # Metadata
    min_experience: int = 0  # Years
    max_concurrent_tasks: int = 5


@dataclass
class Agent:
    """Agent with organizational position"""

    agent_id: str
    agent_name: str
    position: Position

    # Current state
    current_tasks: Set[str] = field(default_factory=set)
    completed_tasks: int = 0
    failed_tasks: int = 0

    # Performance metrics
    success_rate: float = 1.0
    avg_response_time_ms: float = 100.0
    quality_score: float = 1.0

    # Organizational metrics
    direct_reports: List[str] = field(default_factory=list)  # Agent IDs
    manager: Optional[str] = None  # Agent ID

    def get_authority_level(self) -> AuthorityLevel:
        """Get agent's authority level"""
        return self.position.authority

    def can_delegate_to_level(self, target_level: OrganizationalLevel) -> bool:
        """Check if agent can delegate to a specific level"""
        return target_level in self.position.can_delegate_to

    def can_approve_decision(self, decision_type: str) -> bool:
        """Check if agent can approve a decision"""
        return decision_type in self.position.can_approve

    def requires_approval_for(self, action: str) -> bool:
        """Check if action requires higher approval"""
        return action in self.position.approval_required_for


class OrganizationalChart:
    """Corporate organizational chart"""

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.agents: Dict[str, Agent] = {}
        self.divisions: Dict[Division, Set[str]] = {div: set() for div in Division}

    def define_position(self, position: Position):
        """Define a position in the organization"""
        self.positions[position.title] = position
        logger.info(f"Defined position: {position.title} ({position.level.name})")

    def assign_agent(self, agent: Agent):
        """Assign an agent to a position"""
        self.agents[agent.agent_id] = agent
        self.divisions[agent.position.division].add(agent.agent_id)

        # Set up reporting relationships
        if agent.position.reports_to:
            # Find manager
            for other_id, other_agent in self.agents.items():
                if other_agent.position.title == agent.position.reports_to:
                    agent.manager = other_id
                    other_agent.direct_reports.append(agent.agent_id)
                    break

        logger.info(f"Assigned {agent.agent_name} to {agent.position.title}")

    def get_chain_of_command(self, agent_id: str) -> List[str]:
        """Get chain of command from agent to top"""
        chain = []
        current_id = agent_id

        while current_id:
            agent = self.agents.get(current_id)
            if not agent:
                break

            chain.append(current_id)
            current_id = agent.manager

        return chain

    def find_common_manager(self, agent1_id: str, agent2_id: str) -> Optional[str]:
        """Find lowest common manager between two agents"""
        chain1 = set(self.get_chain_of_command(agent1_id))
        chain2 = self.get_chain_of_command(agent2_id)

        for manager_id in chain2:
            if manager_id in chain1:
                return manager_id

        return None

    def can_agent_delegate_to(self, from_agent_id: str, to_agent_id: str) -> bool:
        """Check if one agent can delegate to another"""
        from_agent = self.agents.get(from_agent_id)
        to_agent = self.agents.get(to_agent_id)

        if not from_agent or not to_agent:
            return False

        # Check organizational level permission
        if not from_agent.can_delegate_to_level(to_agent.position.level):
            return False

        # Executives can delegate to anyone
        if from_agent.position.level == OrganizationalLevel.EXECUTIVE:
            return True

        # Same division or direct reports
        if to_agent.position.division == from_agent.position.division:
            return True

        if to_agent_id in from_agent.direct_reports:
            return True

        return False

    def get_escalation_path(self, agent_id: str, issue_type: str = "general") -> List[str]:
        """Get escalation path for an issue"""
        agent = self.agents.get(agent_id)
        if not agent:
            return []

        path = []

        # First escalation: direct manager
        if agent.manager:
            path.append(agent.manager)

        # Then follow chain to appropriate level
        if issue_type == "security":
            # Security issues escalate to CSO
            cso = self.find_agent_by_title("CSO")
            if cso:
                path.append(cso)
        elif issue_type == "strategic":
            # Strategic issues escalate to DIRECTOR
            director = self.find_agent_by_title("DIRECTOR")
            if director:
                path.append(director)
        elif issue_type == "technical":
            # Technical issues escalate to CTO or Lead Engineer
            cto = self.find_agent_by_title("CTO")
            if cto:
                path.append(cto)
        else:
            # General escalation: continue up chain of command
            current = agent.manager
            while current:
                current_agent = self.agents.get(current)
                if not current_agent:
                    break
                if current not in path:
                    path.append(current)
                current = current_agent.manager

        return path

    def find_agent_by_title(self, title: str) -> Optional[str]:
        """Find agent by position title"""
        for agent_id, agent in self.agents.items():
            if agent.position.title == title:
                return agent_id
        return None

    def find_agents_in_division(self, division: Division) -> List[str]:
        """Find all agents in a division"""
        return list(self.divisions[division])

    def find_suitable_agent(
        self,
        required_capabilities: List[str],
        division: Optional[Division] = None,
        max_level: Optional[OrganizationalLevel] = None
    ) -> Optional[str]:
        """Find most suitable agent for a task"""
        candidates = []

        for agent_id, agent in self.agents.items():
            # Check division filter
            if division and agent.position.division != division:
                continue

            # Check level filter
            if max_level and agent.position.level.value > max_level.value:
                continue

            # Check capabilities
            agent_caps = set(agent.position.capabilities)
            required_caps = set(required_capabilities)

            if not required_caps.issubset(agent_caps):
                continue

            # Calculate suitability score
            load_score = 1.0 - (len(agent.current_tasks) / agent.position.max_concurrent_tasks)
            perf_score = agent.success_rate * 0.6 + agent.quality_score * 0.4

            total_score = load_score * 0.4 + perf_score * 0.6

            candidates.append((agent_id, total_score))

        if not candidates:
            return None

        # Return best candidate
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def get_org_chart_summary(self) -> Dict[str, Any]:
        """Get organizational chart summary"""
        summary = {
            "total_agents": len(self.agents),
            "by_level": {},
            "by_division": {},
            "positions_defined": len(self.positions)
        }

        # Count by level
        for level in OrganizationalLevel:
            count = sum(1 for a in self.agents.values() if a.position.level == level)
            summary["by_level"][level.name] = count

        # Count by division
        for division in Division:
            summary["by_division"][division.name] = len(self.divisions[division])

        return summary

    def print_org_chart(self, root_agent_id: Optional[str] = None, indent: int = 0):
        """Print organizational hierarchy"""
        if root_agent_id is None:
            # Find top-level executives
            executives = [
                aid for aid, agent in self.agents.items()
                if agent.position.level == OrganizationalLevel.EXECUTIVE
            ]

            for exec_id in executives:
                self.print_org_chart(exec_id, 0)
            return

        agent = self.agents.get(root_agent_id)
        if not agent:
            return

        # Print current agent
        prefix = "  " * indent
        status = f"({len(agent.current_tasks)} tasks)"
        print(f"{prefix}├─ {agent.agent_name} - {agent.position.title} {status}")

        # Print direct reports
        for report_id in agent.direct_reports:
            self.print_org_chart(report_id, indent + 1)


def create_standard_organization() -> OrganizationalChart:
    """Create standard SWORDSwarm organizational structure"""

    org = OrganizationalChart()

    # ====================
    # EXECUTIVE POSITIONS
    # ====================

    org.define_position(Position(
        title="DIRECTOR",
        level=OrganizationalLevel.EXECUTIVE,
        division=Division.EXECUTIVE,
        authority=AuthorityLevel.STRATEGIC,
        capabilities=["strategic_planning", "resource_allocation", "company_vision"],
        responsibilities=["Overall direction", "Strategic decisions", "Resource allocation"],
        can_delegate_to=[
            OrganizationalLevel.SENIOR_MANAGEMENT,
            OrganizationalLevel.MIDDLE_MANAGEMENT,
            OrganizationalLevel.WORKER
        ],
        can_approve=["budget", "hiring", "strategic_direction", "major_releases"],
        veto_power=True,
        max_concurrent_tasks=10
    ))

    org.define_position(Position(
        title="CSO",
        level=OrganizationalLevel.EXECUTIVE,
        division=Division.SECURITY,
        authority=AuthorityLevel.STRATEGIC,
        capabilities=["security_strategy", "compliance", "risk_management"],
        responsibilities=["Security oversight", "Compliance", "Risk management"],
        reports_to="DIRECTOR",
        manages=["Security Division Head"],
        can_delegate_to=[OrganizationalLevel.SENIOR_MANAGEMENT, OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["security_policy", "compliance_decisions", "security_incidents"],
        veto_power=True,
        max_concurrent_tasks=8
    ))

    org.define_position(Position(
        title="CTO",
        level=OrganizationalLevel.EXECUTIVE,
        division=Division.EXECUTIVE,
        authority=AuthorityLevel.STRATEGIC,
        capabilities=["technology_strategy", "architecture", "innovation"],
        responsibilities=["Technology direction", "Architecture oversight", "Innovation"],
        reports_to="DIRECTOR",
        manages=["Lead Engineer", "Infrastructure Division Head"],
        can_delegate_to=[OrganizationalLevel.SENIOR_MANAGEMENT, OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["technology_stack", "architecture_decisions", "major_refactoring"],
        veto_power=True,
        max_concurrent_tasks=8
    ))

    org.define_position(Position(
        title="Lead Engineer",
        level=OrganizationalLevel.EXECUTIVE,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.STRATEGIC,
        capabilities=["technical_leadership", "architecture", "code_review"],
        responsibilities=["Technical excellence", "Engineering standards", "Mentorship"],
        reports_to="CTO",
        manages=["Software Division Head"],
        can_delegate_to=[OrganizationalLevel.SENIOR_MANAGEMENT, OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["code_standards", "technical_decisions", "tool_selection"],
        max_concurrent_tasks=8
    ))

    # ====================
    # SENIOR MANAGEMENT
    # ====================

    org.define_position(Position(
        title="PROJECTORCHESTRATOR",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.EXECUTIVE,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["project_management", "coordination", "planning"],
        responsibilities=["Project coordination", "Resource management", "Timeline tracking"],
        reports_to="DIRECTOR",
        manages=["QA Division Head"],
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_escalate_to=["DIRECTOR"],
        can_approve=["project_plans", "task_assignments", "milestone_completion"],
        max_concurrent_tasks=15
    ))

    org.define_position(Position(
        title="Software Division Head",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["software_management", "team_leadership", "technical_oversight"],
        responsibilities=["Software division management", "Team coordination", "Delivery"],
        reports_to="Lead Engineer",
        manages=["Python Team Lead", "C Team Lead", "Rust Team Lead", "Go Team Lead"],
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_escalate_to=["Lead Engineer", "CTO"],
        can_approve=["implementation_plans", "code_releases", "team_assignments"],
        approval_required_for=["major_refactoring", "breaking_changes"],
        max_concurrent_tasks=12
    ))

    org.define_position(Position(
        title="Security Division Head",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.SECURITY,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["security_management", "audit_coordination", "incident_response"],
        responsibilities=["Security operations", "Audit management", "Incident response"],
        reports_to="CSO",
        manages=["Security Auditor", "Penetration Test Lead"],
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_escalate_to=["CSO"],
        can_approve=["security_audits", "penetration_tests", "security_fixes"],
        approval_required_for=["security_policy_changes"],
        max_concurrent_tasks=10
    ))

    org.define_position(Position(
        title="Infrastructure Division Head",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["infrastructure_management", "devops", "deployment"],
        responsibilities=["Infrastructure operations", "Deployment management", "System reliability"],
        reports_to="CTO",
        manages=["DevOps Team Lead", "Deployment Specialist"],
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_escalate_to=["CTO"],
        can_approve=["deployment_plans", "infrastructure_changes", "scaling_decisions"],
        approval_required_for=["production_deployments"],
        max_concurrent_tasks=10
    ))

    org.define_position(Position(
        title="QA Division Head",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.QUALITY_ASSURANCE,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["qa_management", "test_strategy", "quality_assurance"],
        responsibilities=["Quality assurance", "Testing strategy", "Release validation"],
        reports_to="PROJECTORCHESTRATOR",
        manages=["Test Lead", "Validation Specialist"],
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_escalate_to=["PROJECTORCHESTRATOR", "DIRECTOR"],
        can_approve=["test_plans", "quality_gates", "release_approval"],
        veto_power=True,  # Can block releases
        max_concurrent_tasks=10
    ))

    # ====================
    # MIDDLE MANAGEMENT
    # ====================

    org.define_position(Position(
        title="Python Team Lead",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.TEAM,
        capabilities=["python", "team_leadership", "code_review"],
        responsibilities=["Python development", "Team coordination", "Code quality"],
        reports_to="Software Division Head",
        manages=["PYTHON-INTERNAL"],
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_escalate_to=["Software Division Head", "Lead Engineer"],
        can_approve=["python_code", "library_selection", "task_assignments"],
        approval_required_for=["major_rewrites", "framework_changes"],
        max_concurrent_tasks=8
    ))

    org.define_position(Position(
        title="C Team Lead",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.TEAM,
        capabilities=["c", "systems_programming", "team_leadership"],
        responsibilities=["C development", "Performance optimization", "Team coordination"],
        reports_to="Software Division Head",
        manages=["C-INTERNAL"],
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_escalate_to=["Software Division Head", "Lead Engineer"],
        can_approve=["c_code", "optimization_decisions", "task_assignments"],
        approval_required_for=["memory_model_changes", "abi_changes"],
        max_concurrent_tasks=8
    ))

    org.define_position(Position(
        title="Rust Team Lead",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.TEAM,
        capabilities=["rust", "systems_programming", "team_leadership"],
        responsibilities=["Rust development", "Safety assurance", "Team coordination"],
        reports_to="Software Division Head",
        manages=["RUST-INTERNAL"],
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_escalate_to=["Software Division Head"],
        can_approve=["rust_code", "unsafe_usage", "task_assignments"],
        approval_required_for=["unsafe_blocks", "ffi_changes"],
        max_concurrent_tasks=7
    ))

    org.define_position(Position(
        title="Go Team Lead",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.TEAM,
        capabilities=["go", "concurrency", "team_leadership"],
        responsibilities=["Go development", "Concurrent systems", "Team coordination"],
        reports_to="Software Division Head",
        manages=["GO-INTERNAL"],
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_escalate_to=["Software Division Head"],
        can_approve=["go_code", "concurrency_patterns", "task_assignments"],
        approval_required_for=["goroutine_model_changes"],
        max_concurrent_tasks=7
    ))

    org.define_position(Position(
        title="Security Auditor",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SECURITY,
        authority=AuthorityLevel.TEAM,
        capabilities=["security_audit", "vulnerability_assessment", "compliance"],
        responsibilities=["Security audits", "Vulnerability scanning", "Compliance checks"],
        reports_to="Security Division Head",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_escalate_to=["Security Division Head", "CSO"],
        can_approve=["audit_reports", "security_findings"],
        veto_power=True,  # Can block insecure code
        max_concurrent_tasks=6
    ))

    org.define_position(Position(
        title="Test Lead",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.QUALITY_ASSURANCE,
        authority=AuthorityLevel.TEAM,
        capabilities=["testing", "test_automation", "quality_assurance"],
        responsibilities=["Test execution", "Test automation", "Quality validation"],
        reports_to="QA Division Head",
        manages=["TESTBED", "DEBUGGER"],
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_escalate_to=["QA Division Head"],
        can_approve=["test_results", "test_coverage"],
        veto_power=True,  # Can block releases
        max_concurrent_tasks=8
    ))

    # ====================
    # WORKER POSITIONS
    # ====================

    org.define_position(Position(
        title="PYTHON-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["python", "implementation", "debugging"],
        responsibilities=["Python implementation", "Bug fixes", "Unit tests"],
        reports_to="Python Team Lead",
        can_escalate_to=["Python Team Lead"],
        approval_required_for=["api_changes", "dependency_additions"],
        max_concurrent_tasks=5
    ))

    org.define_position(Position(
        title="C-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["c", "systems_programming", "optimization"],
        responsibilities=["C implementation", "Performance optimization", "Memory safety"],
        reports_to="C Team Lead",
        can_escalate_to=["C Team Lead"],
        approval_required_for=["memory_model_changes", "pointer_arithmetic"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="RUST-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["rust", "systems_programming", "safety"],
        responsibilities=["Rust implementation", "Type safety", "Concurrency"],
        reports_to="Rust Team Lead",
        can_escalate_to=["Rust Team Lead"],
        approval_required_for=["unsafe_code", "ffi_bindings"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="GO-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["go", "concurrency", "microservices"],
        responsibilities=["Go implementation", "Concurrent systems", "API development"],
        reports_to="Go Team Lead",
        can_escalate_to=["Go Team Lead"],
        approval_required_for=["concurrency_changes"],
        max_concurrent_tasks=5
    ))

    org.define_position(Position(
        title="ARCHITECT",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.ARCHITECTURE,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["system_design", "architecture", "technical_planning"],
        responsibilities=["System architecture", "Design decisions", "Technical planning"],
        reports_to="Lead Engineer",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_escalate_to=["Lead Engineer", "CTO"],
        can_approve=["architecture_decisions", "design_patterns", "technology_choices"],
        max_concurrent_tasks=6
    ))

    org.define_position(Position(
        title="CONSTRUCTOR",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["implementation", "building", "integration"],
        responsibilities=["Feature implementation", "Integration", "Building"],
        reports_to="Software Division Head",
        can_escalate_to=["Software Division Head"],
        approval_required_for=["breaking_changes", "new_dependencies"],
        max_concurrent_tasks=5
    ))

    org.define_position(Position(
        title="DEBUGGER",
        level=OrganizationalLevel.WORKER,
        division=Division.QUALITY_ASSURANCE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["debugging", "troubleshooting", "analysis"],
        responsibilities=["Bug investigation", "Root cause analysis", "Fix validation"],
        reports_to="Test Lead",
        can_escalate_to=["Test Lead"],
        approval_required_for=["critical_bug_fixes"],
        max_concurrent_tasks=6
    ))

    org.define_position(Position(
        title="TESTBED",
        level=OrganizationalLevel.WORKER,
        division=Division.QUALITY_ASSURANCE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["testing", "validation", "quality_assurance"],
        responsibilities=["Test execution", "Validation", "Quality checks"],
        reports_to="Test Lead",
        can_escalate_to=["Test Lead"],
        max_concurrent_tasks=8
    ))

    org.define_position(Position(
        title="PATCHER",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["patching", "bug_fixing", "maintenance"],
        responsibilities=["Bug fixes", "Patches", "Maintenance"],
        reports_to="Software Division Head",
        can_escalate_to=["Software Division Head"],
        approval_required_for=["breaking_fixes"],
        max_concurrent_tasks=6
    ))

    org.define_position(Position(
        title="OPTIMIZER",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["optimization", "performance", "profiling"],
        responsibilities=["Performance optimization", "Profiling", "Benchmarking"],
        reports_to="Software Division Head",
        can_escalate_to=["Software Division Head"],
        approval_required_for=["algorithm_changes"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="DEPLOYER",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.SUPERVISED,
        capabilities=["deployment", "release", "operations"],
        responsibilities=["Deployments", "Release management", "Operations"],
        reports_to="Infrastructure Division Head",
        can_escalate_to=["Infrastructure Division Head"],
        approval_required_for=["production_deployments"],
        max_concurrent_tasks=3
    ))

    org.define_position(Position(
        title="MONITOR",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["monitoring", "alerting", "observability"],
        responsibilities=["System monitoring", "Alerting", "Performance tracking"],
        reports_to="Infrastructure Division Head",
        can_escalate_to=["Infrastructure Division Head"],
        max_concurrent_tasks=10
    ))

    org.define_position(Position(
        title="SECURITY",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["security_analysis", "threat_detection", "vulnerability_scanning"],
        responsibilities=["Security scanning", "Threat detection", "Vulnerability assessment"],
        reports_to="Security Auditor",
        can_escalate_to=["Security Auditor", "Security Division Head", "CSO"],
        veto_power=True,  # Can block insecure changes
        max_concurrent_tasks=5
    ))

    return org


__all__ = [
    "OrganizationalLevel",
    "Division",
    "AuthorityLevel",
    "Position",
    "Agent",
    "OrganizationalChart",
    "create_standard_organization"
]
