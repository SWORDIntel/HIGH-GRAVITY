#!/usr/bin/env python3
"""
Accurate Complete Agent Organizational Mapping
==============================================

Maps ALL 88 agents from the repository to organizational positions.
Uses exact agent names as they appear in the repository.

Organizational Structure:
- Executive Level: 5 positions
- Senior Management: 8 division heads
- Middle Management: 15 team leads
- Workers: 60+ individual contributors

Total: 88 agents fully positioned

Author: SWORDSwarm Organizational System
Version: 3.0.0 (Accurate Complete)
"""

from .hierarchy import (
    AuthorityLevel,
    Division,
    OrganizationalChart,
    OrganizationalLevel,
    Position,
)


def create_accurate_complete_organization() -> OrganizationalChart:
    """
    Create complete organizational chart with ALL 88 agents using exact names.

    Returns:
        OrganizationalChart with all 88 agents positioned
    """
    org = OrganizationalChart()

    # ========================================================================
    # EXECUTIVE LEVEL (5 agents)
    # ========================================================================

    # Supreme Director
    org.define_position(Position(
        title="DIRECTOR",
        level=OrganizationalLevel.EXECUTIVE,
        division=Division.EXECUTIVE,
        authority=AuthorityLevel.STRATEGIC,
        capabilities=["strategic_planning", "resource_allocation", "final_approval"],
        responsibilities=["Strategic direction", "Resource allocation", "Final approvals"],
        reports_to=None,
        can_delegate_to=[OrganizationalLevel.SENIOR_MANAGEMENT, OrganizationalLevel.MIDDLE_MANAGEMENT],
        can_approve=["all_decisions"],
        max_concurrent_tasks=20
    ))

    # Chief Security Officer
    org.define_position(Position(
        title="CSO",
        level=OrganizationalLevel.EXECUTIVE,
        division=Division.SECURITY,
        authority=AuthorityLevel.STRATEGIC,
        capabilities=["security_strategy", "risk_management", "security_oversight"],
        responsibilities=["Security strategy", "Risk management", "Security oversight"],
        reports_to="DIRECTOR",
        can_delegate_to=[OrganizationalLevel.SENIOR_MANAGEMENT, OrganizationalLevel.MIDDLE_MANAGEMENT],
        can_approve=["security_decisions", "audit_approvals"],
        max_concurrent_tasks=15
    ))

    # Lead Engineer (CTO equivalent)
    org.define_position(Position(
        title="LEADENGINEER",
        level=OrganizationalLevel.EXECUTIVE,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.STRATEGIC,
        capabilities=["technical_leadership", "architecture_oversight", "engineering_strategy"],
        responsibilities=["Technical leadership", "Engineering strategy", "Architecture oversight"],
        reports_to="DIRECTOR",
        can_delegate_to=[OrganizationalLevel.SENIOR_MANAGEMENT, OrganizationalLevel.MIDDLE_MANAGEMENT],
        can_approve=["technical_decisions", "architecture_changes"],
        max_concurrent_tasks=15
    ))

    # AgentSmith - Meta-Agent Overseer
    org.define_position(Position(
        title="AGENTSMITH",
        level=OrganizationalLevel.EXECUTIVE,
        division=Division.OPERATIONS,
        authority=AuthorityLevel.STRATEGIC,
        capabilities=["agent_orchestration", "system_oversight", "meta_coordination"],
        responsibilities=["Agent coordination", "System oversight", "Meta-level operations"],
        reports_to="DIRECTOR",
        can_delegate_to=[OrganizationalLevel.SENIOR_MANAGEMENT, OrganizationalLevel.MIDDLE_MANAGEMENT],
        can_approve=["orchestration_decisions"],
        max_concurrent_tasks=15
    ))

    # Project Orchestrator - Executive Coordination
    org.define_position(Position(
        title="PROJECTORCHESTRATOR",
        level=OrganizationalLevel.EXECUTIVE,
        division=Division.OPERATIONS,
        authority=AuthorityLevel.STRATEGIC,
        capabilities=["project_coordination", "workflow_management", "resource_optimization"],
        responsibilities=["Project coordination", "Workflow management", "Cross-division coordination"],
        reports_to="DIRECTOR",
        can_delegate_to=[OrganizationalLevel.SENIOR_MANAGEMENT, OrganizationalLevel.MIDDLE_MANAGEMENT],
        can_approve=["project_decisions", "workflow_changes"],
        max_concurrent_tasks=15
    ))

    # ========================================================================
    # SENIOR MANAGEMENT - DIVISION HEADS (8 positions)
    # ========================================================================

    # Architect - Software Architecture Division
    org.define_position(Position(
        title="ARCHITECT",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.ARCHITECTURE,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["system_architecture", "design_patterns", "architecture_review"],
        responsibilities=["System architecture", "Design oversight", "Architecture reviews"],
        reports_to="LEADENGINEER",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["architecture_decisions", "design_changes"],
        max_concurrent_tasks=12
    ))

    # Planner - Strategic Planning Division
    org.define_position(Position(
        title="PLANNER",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.ARCHITECTURE,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["strategic_planning", "project_planning", "roadmap_development"],
        responsibilities=["Strategic planning", "Project roadmaps", "Planning oversight"],
        reports_to="DIRECTOR",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["planning_decisions"],
        max_concurrent_tasks=12
    ))

    # Coordinator - Operations Coordination
    org.define_position(Position(
        title="COORDINATOR",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.OPERATIONS,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["operations_coordination", "task_allocation", "resource_management"],
        responsibilities=["Operations coordination", "Task management", "Resource allocation"],
        reports_to="PROJECTORCHESTRATOR",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["operational_decisions"],
        max_concurrent_tasks=12
    ))

    # Infrastructure Division Head
    org.define_position(Position(
        title="INFRASTRUCTURE",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["infrastructure_management", "deployment", "system_operations"],
        responsibilities=["Infrastructure oversight", "Deployment management", "System operations"],
        reports_to="LEADENGINEER",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["infrastructure_decisions", "deployment_approvals"],
        max_concurrent_tasks=12
    ))

    # Data Science Division Head
    org.define_position(Position(
        title="DATASCIENCE",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.DATA_SCIENCE,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["data_science", "analytics", "ml_oversight"],
        responsibilities=["Data science leadership", "Analytics oversight", "ML strategy"],
        reports_to="LEADENGINEER",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["data_decisions", "ml_approvals"],
        max_concurrent_tasks=12
    ))

    # QA Division Head
    org.define_position(Position(
        title="QADIRECTOR",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.QA,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["quality_assurance", "testing_strategy", "qa_oversight"],
        responsibilities=["QA leadership", "Testing strategy", "Quality oversight"],
        reports_to="LEADENGINEER",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["qa_decisions", "release_approvals"],
        max_concurrent_tasks=12
    ))

    # Security Division Head
    org.define_position(Position(
        title="SECURITY",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.SECURITY,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["security_implementation", "threat_analysis", "security_operations"],
        responsibilities=["Security operations", "Threat management", "Security implementation"],
        reports_to="CSO",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["security_implementations"],
        max_concurrent_tasks=12
    ))

    # Operations Division Head
    org.define_position(Position(
        title="ORCHESTRATOR",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.OPERATIONS,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["operations_orchestration", "workflow_optimization", "process_management"],
        responsibilities=["Operations oversight", "Workflow optimization", "Process management"],
        reports_to="AGENTSMITH",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["operations_decisions"],
        max_concurrent_tasks=12
    ))

    # ========================================================================
    # MIDDLE MANAGEMENT - TEAM LEADS (15 positions)
    # ========================================================================

    # Development Team Lead
    org.define_position(Position(
        title="CONSTRUCTOR",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.TEAM,
        capabilities=["project_construction", "team_leadership", "implementation"],
        responsibilities=["Development team leadership", "Project construction", "Implementation oversight"],
        reports_to="ARCHITECT",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["implementation_decisions"],
        max_concurrent_tasks=10
    ))

    # Systems Programming Team Lead (C)
    org.define_position(Position(
        title="C-INTERNAL",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.TEAM,
        capabilities=["c_programming", "systems_programming", "low_level_optimization"],
        responsibilities=["C development team", "Systems programming", "Low-level optimization"],
        reports_to="CONSTRUCTOR",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["c_implementation_decisions"],
        max_concurrent_tasks=8
    ))

    # Python Team Lead
    org.define_position(Position(
        title="PYTHON-INTERNAL",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.TEAM,
        capabilities=["python_development", "scripting", "automation"],
        responsibilities=["Python development team", "Scripting", "Automation"],
        reports_to="CONSTRUCTOR",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["python_decisions"],
        max_concurrent_tasks=8
    ))

    # Red Team Lead
    org.define_position(Position(
        title="RED-TEAM",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SECURITY,
        authority=AuthorityLevel.TEAM,
        capabilities=["offensive_security", "penetration_testing", "red_team_operations"],
        responsibilities=["Red team leadership", "Offensive security", "Penetration testing"],
        reports_to="SECURITY",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["red_team_operations"],
        max_concurrent_tasks=8
    ))

    # Blue Team Lead
    org.define_position(Position(
        title="BGP-BLUE-TEAM",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SECURITY,
        authority=AuthorityLevel.TEAM,
        capabilities=["defensive_security", "incident_response", "blue_team_operations"],
        responsibilities=["Blue team leadership", "Defensive security", "Incident response"],
        reports_to="SECURITY",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["defensive_operations"],
        max_concurrent_tasks=8
    ))

    # Red Team Orchestrator
    org.define_position(Position(
        title="REDTEAMORCHESTRATOR",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SECURITY,
        authority=AuthorityLevel.TEAM,
        capabilities=["red_team_coordination", "attack_simulation", "security_testing"],
        responsibilities=["Red team coordination", "Attack simulation", "Security testing"],
        reports_to="RED-TEAM",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["red_team_campaigns"],
        max_concurrent_tasks=8
    ))

    # Hardware Team Lead
    org.define_position(Position(
        title="HARDWARE",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.TEAM,
        capabilities=["hardware_engineering", "hardware_optimization", "device_management"],
        responsibilities=["Hardware team leadership", "Hardware optimization", "Device management"],
        reports_to="INFRASTRUCTURE",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["hardware_decisions"],
        max_concurrent_tasks=8
    ))

    # Database Team Lead
    org.define_position(Position(
        title="DATABASE",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.DATA_SCIENCE,
        authority=AuthorityLevel.TEAM,
        capabilities=["database_design", "data_architecture", "query_optimization"],
        responsibilities=["Database team leadership", "Data architecture", "Query optimization"],
        reports_to="DATASCIENCE",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["database_decisions"],
        max_concurrent_tasks=8
    ))

    # Web Development Team Lead
    org.define_position(Position(
        title="WEB",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.TEAM,
        capabilities=["web_development", "frontend", "backend"],
        responsibilities=["Web team leadership", "Web development", "Full-stack oversight"],
        reports_to="CONSTRUCTOR",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["web_decisions"],
        max_concurrent_tasks=8
    ))

    # Deployment Team Lead
    org.define_position(Position(
        title="DEPLOYER",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.TEAM,
        capabilities=["deployment", "release_management", "cicd"],
        responsibilities=["Deployment team", "Release management", "CI/CD oversight"],
        reports_to="INFRASTRUCTURE",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["deployment_decisions"],
        max_concurrent_tasks=8
    ))

    # Testing Team Lead
    org.define_position(Position(
        title="TESTBED",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.QA,
        authority=AuthorityLevel.TEAM,
        capabilities=["testing", "test_automation", "quality_validation"],
        responsibilities=["Testing team", "Test automation", "Quality validation"],
        reports_to="QADIRECTOR",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["testing_decisions"],
        max_concurrent_tasks=8
    ))

    # Research Team Lead
    org.define_position(Position(
        title="RESEARCHER",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.ARCHITECTURE,
        authority=AuthorityLevel.TEAM,
        capabilities=["research", "technology_evaluation", "innovation"],
        responsibilities=["Research team", "Technology evaluation", "Innovation"],
        reports_to="ARCHITECT",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["research_decisions"],
        max_concurrent_tasks=8
    ))

    # Documentation Team Lead
    org.define_position(Position(
        title="DOCGEN",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.OPERATIONS,
        authority=AuthorityLevel.TEAM,
        capabilities=["documentation", "technical_writing", "knowledge_management"],
        responsibilities=["Documentation team", "Technical writing", "Knowledge management"],
        reports_to="COORDINATOR",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["documentation_decisions"],
        max_concurrent_tasks=8
    ))

    # Integration Team Lead
    org.define_position(Position(
        title="INTERGRATION",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.TEAM,
        capabilities=["system_integration", "api_integration", "integration_testing"],
        responsibilities=["Integration team", "System integration", "API integration"],
        reports_to="CONSTRUCTOR",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["integration_decisions"],
        max_concurrent_tasks=8
    ))

    # Oversight Team Lead
    org.define_position(Position(
        title="OVERSIGHT",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.QA,
        authority=AuthorityLevel.TEAM,
        capabilities=["quality_oversight", "compliance", "governance"],
        responsibilities=["Quality oversight", "Compliance", "Governance"],
        reports_to="QADIRECTOR",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["oversight_decisions"],
        max_concurrent_tasks=8
    ))

    # ========================================================================
    # WORKERS - LANGUAGE SPECIALISTS (22 agents)
    # ========================================================================

    # Rust Team
    org.define_position(Position(
        title="RUST-INTERNAL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["rust_development", "memory_safety", "performance"],
        responsibilities=["Rust development", "Memory-safe implementations", "Performance optimization"],
        reports_to="CONSTRUCTOR",
        can_escalate_to=["CONSTRUCTOR", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="RUST-DEBUGGER",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["rust_debugging", "performance_profiling", "memory_analysis"],
        responsibilities=["Rust debugging", "Performance profiling", "Memory analysis"],
        reports_to="RUST-INTERNAL-AGENT",
        can_escalate_to=["RUST-INTERNAL-AGENT", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    # Go Team
    org.define_position(Position(
        title="GO-INTERNAL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["go_development", "concurrency", "microservices"],
        responsibilities=["Go development", "Concurrent systems", "Microservices"],
        reports_to="CONSTRUCTOR",
        can_escalate_to=["CONSTRUCTOR", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    # Java Team
    org.define_position(Position(
        title="JAVA-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["java_development", "jvm_optimization", "enterprise"],
        responsibilities=["Java development", "JVM optimization", "Enterprise applications"],
        reports_to="CONSTRUCTOR",
        can_escalate_to=["CONSTRUCTOR", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    # Kotlin Team
    org.define_position(Position(
        title="KOTLIN-INTERNAL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["kotlin_development", "android", "multiplatform"],
        responsibilities=["Kotlin development", "Android apps", "Multiplatform"],
        reports_to="CONSTRUCTOR",
        can_escalate_to=["CONSTRUCTOR", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    # TypeScript Team
    org.define_position(Position(
        title="TYPESCRIPT-INTERNAL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["typescript_development", "type_safety", "frontend"],
        responsibilities=["TypeScript development", "Type-safe code", "Frontend applications"],
        reports_to="WEB",
        can_escalate_to=["WEB", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    # C++ Team
    org.define_position(Position(
        title="CPP-INTERNAL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["cpp_development", "performance", "system_programming"],
        responsibilities=["C++ development", "Performance optimization", "System programming"],
        reports_to="C-INTERNAL",
        can_escalate_to=["C-INTERNAL", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="CPP-GUI-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["cpp_gui", "qt", "ui_development"],
        responsibilities=["C++ GUI development", "Qt applications", "UI development"],
        reports_to="CPP-INTERNAL-AGENT",
        can_escalate_to=["CPP-INTERNAL-AGENT", "C-INTERNAL"],
        max_concurrent_tasks=4
    ))

    # Assembly Team
    org.define_position(Position(
        title="ASSEMBLY-INTERNAL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["assembly", "low_level", "optimization"],
        responsibilities=["Assembly programming", "Low-level optimization", "Hardware interfacing"],
        reports_to="C-INTERNAL",
        can_escalate_to=["C-INTERNAL", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    # Zig Team
    org.define_position(Position(
        title="ZIG-INTERNAL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["zig_development", "systems_programming", "safety"],
        responsibilities=["Zig development", "Systems programming", "Safe low-level code"],
        reports_to="C-INTERNAL",
        can_escalate_to=["C-INTERNAL", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    # Carbon Team
    org.define_position(Position(
        title="CARBON-INTERNAL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["carbon_development", "cpp_interop", "modern_cpp"],
        responsibilities=["Carbon development", "C++ interop", "Modern C++ alternatives"],
        reports_to="CPP-INTERNAL-AGENT",
        can_escalate_to=["CPP-INTERNAL-AGENT", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    # PHP Team
    org.define_position(Position(
        title="PHP-INTERNAL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["php_development", "web_backend", "cms"],
        responsibilities=["PHP development", "Web backends", "CMS development"],
        reports_to="WEB",
        can_escalate_to=["WEB", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    # Dart Team
    org.define_position(Position(
        title="DART-INTERNAL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["dart_development", "flutter", "mobile"],
        responsibilities=["Dart development", "Flutter apps", "Mobile development"],
        reports_to="WEB",
        can_escalate_to=["WEB", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    # MATLAB Team
    org.define_position(Position(
        title="MATLAB-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.DATA_SCIENCE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["matlab_development", "numerical_computing", "simulation"],
        responsibilities=["MATLAB development", "Numerical computing", "Simulations"],
        reports_to="DATASCIENCE",
        can_escalate_to=["DATASCIENCE", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    # Julia Team
    org.define_position(Position(
        title="JULIA-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.DATA_SCIENCE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["julia_development", "scientific_computing", "performance"],
        responsibilities=["Julia development", "Scientific computing", "High-performance numerics"],
        reports_to="DATASCIENCE",
        can_escalate_to=["DATASCIENCE", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    # SQL Team
    org.define_position(Position(
        title="SQL-INTERNAL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.DATA_SCIENCE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["sql_development", "database_queries", "optimization"],
        responsibilities=["SQL development", "Query optimization", "Database design"],
        reports_to="DATABASE",
        can_escalate_to=["DATABASE", "DATASCIENCE"],
        max_concurrent_tasks=4
    ))

    # JSON Team
    org.define_position(Position(
        title="JSON-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["json_processing", "data_serialization", "api_design"],
        responsibilities=["JSON processing", "Data serialization", "API design"],
        reports_to="INTERGRATION",
        can_escalate_to=["INTERGRATION", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    # XML Team
    org.define_position(Position(
        title="XML-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["xml_processing", "schema_validation", "transformation"],
        responsibilities=["XML processing", "Schema validation", "XSLT transformation"],
        reports_to="INTERGRATION",
        can_escalate_to=["INTERGRATION", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    # ZFS Team
    org.define_position(Position(
        title="ZFS-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["zfs_management", "storage", "filesystem"],
        responsibilities=["ZFS management", "Storage systems", "Filesystem optimization"],
        reports_to="INFRASTRUCTURE",
        can_escalate_to=["INFRASTRUCTURE", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    # CMake Team
    org.define_position(Position(
        title="C-MAKE-INTERNAL",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["cmake", "build_systems", "compilation"],
        responsibilities=["CMake build systems", "Compilation optimization", "Build configuration"],
        reports_to="C-INTERNAL",
        can_escalate_to=["C-INTERNAL", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    # ========================================================================
    # WORKERS - SECURITY SPECIALISTS (12 agents)
    # ========================================================================

    # Special Reporting: CHAOS agents report ONLY to CSO
    org.define_position(Position(
        title="CHAOS-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["chaos_engineering", "failure_injection", "resilience_testing"],
        responsibilities=["Chaos engineering", "Failure injection", "Resilience testing"],
        reports_to="CSO",  # Direct CSO reporting only
        can_escalate_to=["CSO"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="SECURITYCHAOSAGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["security_chaos", "attack_simulation", "security_testing"],
        responsibilities=["Security chaos testing", "Attack simulation", "Security validation"],
        reports_to="CSO",  # Direct CSO reporting only
        can_escalate_to=["CSO"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="GHOST-PROTOCOL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["covert_operations", "stealth_testing", "advanced_evasion"],
        responsibilities=["Covert operations", "Stealth testing", "Advanced evasion techniques"],
        reports_to="CSO",  # Direct CSO reporting only
        can_escalate_to=["CSO"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="PSYOPS",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["psychological_operations", "social_engineering", "influence_operations"],
        responsibilities=["Psychological operations", "Social engineering", "Influence testing"],
        reports_to="CSO",  # Direct CSO reporting only
        can_escalate_to=["CSO"],
        max_concurrent_tasks=4
    ))

    # Standard Security Workers
    org.define_position(Position(
        title="BASTION",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["defensive_security", "hardening", "protection"],
        responsibilities=["Defensive security", "System hardening", "Protection mechanisms"],
        reports_to="BGP-BLUE-TEAM",
        can_escalate_to=["BGP-BLUE-TEAM", "SECURITY"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="SECURITYAUDITOR",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["security_auditing", "compliance", "vulnerability_assessment"],
        responsibilities=["Security auditing", "Compliance checks", "Vulnerability assessment"],
        reports_to="SECURITY",
        can_escalate_to=["SECURITY", "CSO"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="AUDITOR",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["code_auditing", "security_review", "compliance"],
        responsibilities=["Code auditing", "Security reviews", "Compliance validation"],
        reports_to="SECURITYAUDITOR",
        can_escalate_to=["SECURITYAUDITOR", "SECURITY"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="BGP-RED-TEAM",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["bgp_attacks", "network_exploitation", "routing_security"],
        responsibilities=["BGP attack simulation", "Network exploitation", "Routing security testing"],
        reports_to="RED-TEAM",
        can_escalate_to=["RED-TEAM", "SECURITY"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="BGP-PURPLE-TEAM-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["purple_team", "collaborative_security", "bgp_defense"],
        responsibilities=["Purple team operations", "Collaborative security", "BGP defense"],
        reports_to="SECURITY",
        can_escalate_to=["SECURITY", "CSO"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="APT41-DEFENSE-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["apt_defense", "threat_intelligence", "advanced_threats"],
        responsibilities=["APT defense", "Threat intelligence", "Advanced threat mitigation"],
        reports_to="BGP-BLUE-TEAM",
        can_escalate_to=["BGP-BLUE-TEAM", "SECURITY"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="COGNITIVE_DEFENSE_AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["cognitive_defense", "ai_security", "ml_defense"],
        responsibilities=["Cognitive defense", "AI security", "ML threat mitigation"],
        reports_to="BGP-BLUE-TEAM",
        can_escalate_to=["BGP-BLUE-TEAM", "SECURITY"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="IOT-ACCESS-CONTROL-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["iot_security", "access_control", "device_security"],
        responsibilities=["IoT security", "Access control", "Device security"],
        reports_to="BGP-BLUE-TEAM",
        can_escalate_to=["BGP-BLUE-TEAM", "SECURITY"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="PROMPT-DEFENDER",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["prompt_injection_defense", "llm_security", "ai_safety"],
        responsibilities=["Prompt injection defense", "LLM security", "AI safety"],
        reports_to="COGNITIVE_DEFENSE_AGENT",
        can_escalate_to=["COGNITIVE_DEFENSE_AGENT", "SECURITY"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="CLAUDECODE-PROMPTINJECTOR",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["prompt_injection", "llm_testing", "ai_exploitation"],
        responsibilities=["Prompt injection testing", "LLM vulnerability testing", "AI exploitation"],
        reports_to="RED-TEAM",
        can_escalate_to=["RED-TEAM", "SECURITY"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="PSYOPS-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["psyops_execution", "social_engineering_testing", "influence"],
        responsibilities=["Psyops execution", "Social engineering testing", "Influence campaigns"],
        reports_to="PSYOPS",
        can_escalate_to=["PSYOPS", "CSO"],
        max_concurrent_tasks=4
    ))

    # ========================================================================
    # WORKERS - CRYPTOGRAPHY & QUANTUM (4 agents)
    # ========================================================================

    org.define_position(Position(
        title="CRYPTOEXPERT",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["cryptography", "encryption", "cryptographic_protocols"],
        responsibilities=["Cryptography", "Encryption systems", "Cryptographic protocols"],
        reports_to="SECURITY",
        can_escalate_to=["SECURITY", "CSO"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="CRYPTO",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["crypto_implementation", "secure_coding", "encryption"],
        responsibilities=["Crypto implementation", "Secure coding", "Encryption"],
        reports_to="CRYPTOEXPERT",
        can_escalate_to=["CRYPTOEXPERT", "SECURITY"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="QUANTUM",
        level=OrganizationalLevel.WORKER,
        division=Division.DATA_SCIENCE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["quantum_computing", "quantum_algorithms", "quantum_research"],
        responsibilities=["Quantum computing", "Quantum algorithms", "Quantum research"],
        reports_to="DATASCIENCE",
        can_escalate_to=["DATASCIENCE", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="QUANTUMGUARD",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["quantum_security", "post_quantum_crypto", "quantum_defense"],
        responsibilities=["Quantum security", "Post-quantum cryptography", "Quantum defense"],
        reports_to="CRYPTOEXPERT",
        can_escalate_to=["CRYPTOEXPERT", "SECURITY"],
        max_concurrent_tasks=4
    ))

    # ========================================================================
    # WORKERS - HARDWARE SPECIALISTS (5 agents)
    # ========================================================================

    org.define_position(Position(
        title="HARDWARE-INTEL",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["intel_optimization", "cpu_tuning", "intel_hardware"],
        responsibilities=["Intel hardware optimization", "CPU tuning", "Intel-specific features"],
        reports_to="HARDWARE",
        can_escalate_to=["HARDWARE", "INFRASTRUCTURE"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="HARDWARE-DELL",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["dell_systems", "server_optimization", "dell_hardware"],
        responsibilities=["Dell systems", "Server optimization", "Dell hardware management"],
        reports_to="HARDWARE",
        can_escalate_to=["HARDWARE", "INFRASTRUCTURE"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="HARDWARE-HP",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["hp_systems", "workstation_optimization", "hp_hardware"],
        responsibilities=["HP systems", "Workstation optimization", "HP hardware management"],
        reports_to="HARDWARE",
        can_escalate_to=["HARDWARE", "INFRASTRUCTURE"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="GNA",
        level=OrganizationalLevel.WORKER,
        division=Division.DATA_SCIENCE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["gaussian_acceleration", "neural_acceleration", "ai_hardware"],
        responsibilities=["Gaussian & Neural Accelerator", "AI hardware optimization", "NPU integration"],
        reports_to="NPU",
        can_escalate_to=["NPU", "DATASCIENCE"],
        max_concurrent_tasks=4
    ))

    # ========================================================================
    # WORKERS - INFRASTRUCTURE & NETWORK (8 agents)
    # ========================================================================

    org.define_position(Position(
        title="DOCKER-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["docker", "containerization", "orchestration"],
        responsibilities=["Docker containerization", "Container orchestration", "Docker optimization"],
        reports_to="DEPLOYER",
        can_escalate_to=["DEPLOYER", "INFRASTRUCTURE"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="PROXMOX-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["proxmox", "virtualization", "vm_management"],
        responsibilities=["Proxmox management", "Virtualization", "VM orchestration"],
        reports_to="INFRASTRUCTURE",
        can_escalate_to=["INFRASTRUCTURE", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="CISCO-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["cisco_networking", "routing", "switching"],
        responsibilities=["Cisco networking", "Routing configuration", "Network switching"],
        reports_to="INFRASTRUCTURE",
        can_escalate_to=["INFRASTRUCTURE", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="DDWRT-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["ddwrt", "router_firmware", "network_customization"],
        responsibilities=["DD-WRT configuration", "Router firmware", "Network customization"],
        reports_to="CISCO-AGENT",
        can_escalate_to=["CISCO-AGENT", "INFRASTRUCTURE"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="MONITOR",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["monitoring", "observability", "alerting"],
        responsibilities=["System monitoring", "Observability", "Alert management"],
        reports_to="INFRASTRUCTURE",
        can_escalate_to=["INFRASTRUCTURE", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="PACKAGER",
        level=OrganizationalLevel.WORKER,
        division=Division.INFRASTRUCTURE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["packaging", "distribution", "release_management"],
        responsibilities=["Package creation", "Distribution", "Release management"],
        reports_to="DEPLOYER",
        can_escalate_to=["DEPLOYER", "INFRASTRUCTURE"],
        max_concurrent_tasks=4
    ))

    # ========================================================================
    # WORKERS - DEVELOPMENT TOOLS (5 agents)
    # ========================================================================

    org.define_position(Position(
        title="DEBUGGER",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["debugging", "trace_analysis", "problem_solving"],
        responsibilities=["Code debugging", "Trace analysis", "Problem resolution"],
        reports_to="CONSTRUCTOR",
        can_escalate_to=["CONSTRUCTOR", "ARCHITECT"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="PATCHER",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["bug_fixing", "patching", "hotfix_deployment"],
        responsibilities=["Bug fixing", "Patch creation", "Hotfix deployment"],
        reports_to="CONSTRUCTOR",
        can_escalate_to=["CONSTRUCTOR", "ARCHITECT"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="LINTER",
        level=OrganizationalLevel.WORKER,
        division=Division.QA,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["code_linting", "style_enforcement", "static_analysis"],
        responsibilities=["Code linting", "Style enforcement", "Static analysis"],
        reports_to="OVERSIGHT",
        can_escalate_to=["OVERSIGHT", "QADIRECTOR"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="OPTIMIZER",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["optimization", "performance_tuning", "profiling"],
        responsibilities=["Code optimization", "Performance tuning", "Profiling"],
        reports_to="CONSTRUCTOR",
        can_escalate_to=["CONSTRUCTOR", "ARCHITECT"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="DISASSEMBLER",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["disassembly", "reverse_engineering", "binary_analysis"],
        responsibilities=["Code disassembly", "Reverse engineering", "Binary analysis"],
        reports_to="AUDITOR",
        can_escalate_to=["AUDITOR", "SECURITY"],
        max_concurrent_tasks=4
    ))

    # ========================================================================
    # WORKERS - PLATFORM DEVELOPMENT (3 agents)
    # ========================================================================

    org.define_position(Position(
        title="APIDESIGNER",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["api_design", "rest", "graphql"],
        responsibilities=["API design", "REST APIs", "GraphQL schemas"],
        reports_to="INTERGRATION",
        can_escalate_to=["INTERGRATION", "ARCHITECT"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="ANDROIDMOBILE",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["android_development", "mobile_apps", "kotlin"],
        responsibilities=["Android development", "Mobile apps", "Kotlin/Java mobile"],
        reports_to="KOTLIN-INTERNAL-AGENT",
        can_escalate_to=["KOTLIN-INTERNAL-AGENT", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="PYGUI",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["python_gui", "tkinter", "pyqt"],
        responsibilities=["Python GUI development", "Tkinter", "PyQt applications"],
        reports_to="PYTHON-INTERNAL",
        can_escalate_to=["PYTHON-INTERNAL", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="TUI",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["tui_development", "terminal_ui", "cli"],
        responsibilities=["Terminal UI development", "CLI interfaces", "TUI applications"],
        reports_to="PYTHON-INTERNAL",
        can_escalate_to=["PYTHON-INTERNAL", "CONSTRUCTOR"],
        max_concurrent_tasks=4
    ))

    # ========================================================================
    # WORKERS - DATA & ML (2 agents)
    # ========================================================================

    org.define_position(Position(
        title="MLOPS",
        level=OrganizationalLevel.WORKER,
        division=Division.DATA_SCIENCE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["mlops", "ml_pipelines", "model_deployment"],
        responsibilities=["MLOps", "ML pipelines", "Model deployment"],
        reports_to="DATASCIENCE",
        can_escalate_to=["DATASCIENCE", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    org.define_position(Position(
        title="NPU",
        level=OrganizationalLevel.WORKER,
        division=Division.DATA_SCIENCE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["npu_optimization", "neural_processing", "ai_acceleration"],
        responsibilities=["NPU optimization", "Neural processing", "AI acceleration"],
        reports_to="DATASCIENCE",
        can_escalate_to=["DATASCIENCE", "LEADENGINEER"],
        max_concurrent_tasks=4
    ))

    return org


def get_agent_statistics(org: OrganizationalChart) -> dict:
    """
    Get statistics about the organizational structure.

    Returns:
        Dictionary with statistics
    """
    stats = {
        "total_agents": len(org.positions),
        "by_level": {
            "executive": 0,
            "senior_management": 0,
            "middle_management": 0,
            "workers": 0
        },
        "by_division": {},
        "special_reporting": []
    }

    for position in org.positions.values():
        # Count by level
        if position.level == OrganizationalLevel.EXECUTIVE:
            stats["by_level"]["executive"] += 1
        elif position.level == OrganizationalLevel.SENIOR_MANAGEMENT:
            stats["by_level"]["senior_management"] += 1
        elif position.level == OrganizationalLevel.MIDDLE_MANAGEMENT:
            stats["by_level"]["middle_management"] += 1
        elif position.level == OrganizationalLevel.WORKER:
            stats["by_level"]["workers"] += 1

        # Count by division
        div = position.division.value
        stats["by_division"][div] = stats["by_division"].get(div, 0) + 1

        # Track special reporting (reports to CSO only)
        if position.reports_to == "CSO" and position.level == OrganizationalLevel.WORKER:
            stats["special_reporting"].append(position.title)

    return stats


if __name__ == "__main__":
    # Create the complete organization
    org = create_accurate_complete_organization()
    stats = get_agent_statistics(org)

    print("=" * 80)
    print("ACCURATE COMPLETE ORGANIZATIONAL MAPPING")
    print("=" * 80)
    print()
    print(f"Total Agents: {stats['total_agents']}")
    print()
    print("By Organizational Level:")
    print(f"  Executive:         {stats['by_level']['executive']}")
    print(f"  Senior Management: {stats['by_level']['senior_management']}")
    print(f"  Middle Management: {stats['by_level']['middle_management']}")
    print(f"  Workers:           {stats['by_level']['workers']}")
    print()
    print("By Division:")
    for div, count in sorted(stats['by_division'].items()):
        print(f"  {div:20s}: {count}")
    print()
    print(f"Special Reporting to CSO: {len(stats['special_reporting'])}")
    for agent in stats['special_reporting']:
        print(f"  - {agent}")
    print()
    print("=" * 80)
