#!/usr/bin/env python3
"""
Phase 2: Complete Agent Organizational Mapping
===============================================

Adds ALL remaining 47+ agents to the organizational structure.
This completes the full 91-agent corporate hierarchy.

New Additions in Phase 2:
- 4 Hardware specialists (HARDWARE-INTEL, HARDWARE-DELL, HARDWARE-HP, GNA)
- 14 Additional language agents (PHP, C++, MATLAB, Dart, Carbon, Assembly, etc.)
- 10 Advanced security agents (APT41, BGP teams, GHOST-PROTOCOL, etc.)
- 5 Infrastructure agents (DOCKER, PROXMOX, CISCO, DDWRT, etc.)
- 4 Quantum & crypto agents
- 10+ Specialized tools and agents

Total System: 91+ agents fully positioned

Author: SWORDSwarm Organizational System
Version: 2.0.0 (Phase 2)
"""

from .hierarchy import (
    AuthorityLevel,
    Division,
    OrganizationalChart,
    OrganizationalLevel,
    Position,
)
from .complete_agent_mapping import create_complete_organization


def add_phase2_agents(org: OrganizationalChart) -> OrganizationalChart:
    """
    Add Phase 2 agents (47+ additional agents) to existing organization

    Args:
        org: Existing organizational chart (from Phase 1)

    Returns:
        Updated organizational chart with all agents
    """

    # ========================================================================
    # NEW DIVISION: HARDWARE ENGINEERING
    # ========================================================================

    # Create Hardware Division Head position
    org.define_position(Position(
        title="Hardware Division Head",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.INFRASTRUCTURE,  # Or create new HARDWARE division
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["hardware_engineering", "embedded_systems", "hardware_optimization"],
        responsibilities=["Hardware engineering", "Device optimization", "Hardware-software integration"],
        reports_to="CTO",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["hardware_decisions", "optimization_strategies"],
        max_concurrent_tasks=10
    ))

    # Hardware specialists
    for hw_agent in [
        ("HARDWARE-INTEL", "intel_optimization", "Intel hardware optimization"),
        ("HARDWARE-DELL", "dell_systems", "Dell systems integration"),
        ("HARDWARE-HP", "hp_systems", "HP systems integration"),
        ("HARDWARE", "general_hardware", "General hardware engineering"),
    ]:
        agent_name, capability, description = hw_agent
        org.define_position(Position(
            title=agent_name,
            level=OrganizationalLevel.WORKER,
            division=Division.INFRASTRUCTURE,
            authority=AuthorityLevel.INDIVIDUAL,
            capabilities=[capability, "hardware_optimization", "performance_tuning"],
            responsibilities=[description, "Hardware optimization", "Performance tuning"],
            reports_to="Hardware Division Head",
            can_escalate_to=["Hardware Division Head", "CTO"],
            max_concurrent_tasks=4
        ))

    # GNA - Gaussian & Neural Accelerator (special AI hardware)
    org.define_position(Position(
        title="GNA",
        level=OrganizationalLevel.WORKER,
        division=Division.DATA_SCIENCE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["gaussian_acceleration", "neural_acceleration", "ai_hardware"],
        responsibilities=["AI hardware acceleration", "Neural network optimization", "GNA integration"],
        reports_to="DATA-SCIENCE",
        can_escalate_to=["DATA-SCIENCE"],
        max_concurrent_tasks=4
    ))

    # ========================================================================
    # ADDITIONAL LANGUAGE AGENTS (14 new language specialists)
    # ========================================================================

    # Create C++ Team Lead
    org.define_position(Position(
        title="C++ Team Lead",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.TEAM,
        capabilities=["cpp", "object_oriented", "template_programming"],
        responsibilities=["C++ development", "Team coordination", "Code quality"],
        reports_to="Software Division Head",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["cpp_code", "template_designs"],
        max_concurrent_tasks=8
    ))

    # C++ agents
    for cpp_agent in [
        ("CPP-INTERNAL-AGENT", ["cpp", "stl", "boost"], "C++ implementation"),
        ("CPP-GUI-INTERNAL", ["cpp_gui", "qt", "wxwidgets"], "C++ GUI development"),
    ]:
        agent_name, capabilities, description = cpp_agent
        org.define_position(Position(
            title=agent_name,
            level=OrganizationalLevel.WORKER,
            division=Division.SOFTWARE_ENGINEERING,
            authority=AuthorityLevel.INDIVIDUAL,
            capabilities=capabilities,
            responsibilities=[description, "Implementation", "Testing"],
            reports_to="C++ Team Lead",
            can_escalate_to=["C++ Team Lead"],
            approval_required_for=["api_changes"],
            max_concurrent_tasks=5
        ))

    # Additional language specialists (report to Software Division Head)
    language_agents = [
        ("PHP-INTERNAL-AGENT", ["php", "web_backend"], "PHP development"),
        ("MATLAB-INTERNAL", ["matlab", "scientific_computing"], "MATLAB development"),
        ("DART-INTERNAL-AGENT", ["dart", "flutter"], "Dart/Flutter development"),
        ("CARBON-INTERNAL-AGENT", ["carbon", "modern_cpp_alternative"], "Carbon language development"),
        ("ASSEMBLY-INTERNAL-AGENT", ["assembly", "x86", "arm"], "Assembly language programming"),
        ("ZIG-INTERNAL-AGENT", ["zig", "systems_programming"], "Zig development"),
        ("JULIA-INTERNAL", ["julia", "scientific_computing"], "Julia development"),
        ("SQL-INTERNAL-AGENT", ["sql", "database", "queries"], "SQL specialist"),
        ("TYPESCRIPT-INTERNAL-AGENT", ["typescript", "javascript"], "TypeScript development"),
        ("JSON-INTERNAL", ["json", "data_formats"], "JSON processing specialist"),
        ("XML-INTERNAL", ["xml", "data_formats"], "XML processing specialist"),
        ("ZFS-INTERNAL", ["zfs", "filesystem"], "ZFS filesystem specialist"),
    ]

    for agent_name, capabilities, description in language_agents:
        org.define_position(Position(
            title=agent_name,
            level=OrganizationalLevel.WORKER,
            division=Division.SOFTWARE_ENGINEERING,
            authority=AuthorityLevel.INDIVIDUAL,
            capabilities=capabilities,
            responsibilities=[description, "Implementation", "Debugging"],
            reports_to="Software Division Head",
            can_escalate_to=["Software Division Head"],
            approval_required_for=["breaking_changes"],
            max_concurrent_tasks=5
        ))

    # ========================================================================
    # ADVANCED SECURITY AGENTS (10+ new security specialists)
    # ========================================================================

    # Red Team Lead (offensive security)
    org.define_position(Position(
        title="Red Team Lead",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SECURITY,
        authority=AuthorityLevel.TEAM,
        capabilities=["offensive_security", "penetration_testing", "exploit_development"],
        responsibilities=["Offensive security", "Penetration testing", "Red team operations"],
        reports_to="Security Division Head",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["penetration_tests", "security_assessments"],
        max_concurrent_tasks=6
    ))

    # Blue Team Lead (defensive security)
    org.define_position(Position(
        title="Blue Team Lead",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SECURITY,
        authority=AuthorityLevel.TEAM,
        capabilities=["defensive_security", "incident_response", "threat_hunting"],
        responsibilities=["Defensive security", "Incident response", "Blue team operations"],
        reports_to="Security Division Head",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["security_controls", "incident_response_plans"],
        max_concurrent_tasks=6
    ))

    # Advanced security agents
    advanced_security = [
        ("APT41-DEFENSE-AGENT", "Red Team Lead", ["apt_defense", "advanced_threats"], "APT41 defense specialist"),
        ("COGNITIVE_DEFENSE_AGENT", "Security Division Head", ["cognitive_security", "social_engineering_defense"], "Cognitive security defense"),
        ("BGP-BLUE-TEAM", "Blue Team Lead", ["bgp_security", "network_defense"], "BGP blue team operations"),
        ("BGP-RED-TEAM", "Red Team Lead", ["bgp_attacks", "network_penetration"], "BGP red team operations"),
        ("BGP-PURPLE-TEAM-AGENT", "Security Division Head", ["bgp_security", "combined_ops"], "BGP purple team (red+blue)"),
        ("RED-TEAM", "Red Team Lead", ["offensive_security", "penetration_testing"], "General red team operations"),
        ("REDTEAMORCHESTRATOR", "Red Team Lead", ["red_team_coordination", "attack_campaigns"], "Red team orchestration"),
        ("GHOST-PROTOCOL-AGENT", "CSO", ["covert_operations", "advanced_evasion"], "Ghost protocol operations (CSO only)"),
        ("IOT-ACCESS-CONTROL-AGENT", "Security Division Head", ["iot_security", "access_control"], "IoT security specialist"),
        ("PROMPT-DEFENDER", "Security Division Head", ["prompt_injection_defense", "ai_security"], "AI prompt security"),
    ]

    for agent_name, reports_to, capabilities, description in advanced_security:
        org.define_position(Position(
            title=agent_name,
            level=OrganizationalLevel.WORKER,
            division=Division.SECURITY,
            authority=AuthorityLevel.INDIVIDUAL,
            capabilities=capabilities,
            responsibilities=[description, "Security operations", "Threat mitigation"],
            reports_to=reports_to,
            can_escalate_to=[reports_to, "CSO"],
            max_concurrent_tasks=4
        ))

    # ========================================================================
    # SPECIALIZED INFRASTRUCTURE AGENTS (5 new)
    # ========================================================================

    infrastructure_agents = [
        ("DOCKER-AGENT", ["docker", "containers", "orchestration"], "Docker containerization"),
        ("PROXMOX-AGENT", ["proxmox", "virtualization", "hypervisor"], "Proxmox virtualization"),
        ("CISCO-AGENT", ["cisco", "networking", "routing"], "Cisco networking"),
        ("DDWRT-AGENT", ["ddwrt", "router_firmware", "networking"], "DD-WRT router management"),
        ("C-MAKE-INTERNAL", ["cmake", "build_systems", "compilation"], "CMake build specialist"),
    ]

    for agent_name, capabilities, description in infrastructure_agents:
        org.define_position(Position(
            title=agent_name,
            level=OrganizationalLevel.WORKER,
            division=Division.INFRASTRUCTURE,
            authority=AuthorityLevel.INDIVIDUAL,
            capabilities=capabilities,
            responsibilities=[description, "Infrastructure management", "Configuration"],
            reports_to="Infrastructure Division Head",
            can_escalate_to=["Infrastructure Division Head"],
            max_concurrent_tasks=5
        ))

    # ========================================================================
    # QUANTUM & CRYPTOGRAPHY DIVISION (4 agents)
    # ========================================================================

    # Quantum & Crypto Lead
    org.define_position(Position(
        title="Quantum & Crypto Lead",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SECURITY,
        authority=AuthorityLevel.TEAM,
        capabilities=["quantum_computing", "cryptography", "post_quantum_crypto"],
        responsibilities=["Quantum computing", "Cryptographic security", "Post-quantum readiness"],
        reports_to="CSO",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["crypto_implementations", "quantum_strategies"],
        max_concurrent_tasks=6
    ))

    quantum_crypto_agents = [
        ("QUANTUM", ["quantum_computing", "quantum_algorithms"], "Quantum computing specialist"),
        ("QUANTUMGUARD", ["quantum_security", "post_quantum_crypto"], "Quantum security guard"),
        ("CRYPTO", ["cryptography", "encryption", "protocols"], "Cryptography specialist"),
        ("CRYPTOEXPERT", ["advanced_cryptography", "crypto_analysis"], "Advanced cryptography expert"),
    ]

    for agent_name, capabilities, description in quantum_crypto_agents:
        org.define_position(Position(
            title=agent_name,
            level=OrganizationalLevel.WORKER,
            division=Division.SECURITY,
            authority=AuthorityLevel.INDIVIDUAL,
            capabilities=capabilities,
            responsibilities=[description, "Cryptographic operations", "Security analysis"],
            reports_to="Quantum & Crypto Lead",
            can_escalate_to=["Quantum & Crypto Lead", "CSO"],
            max_concurrent_tasks=4
        ))

    # ========================================================================
    # SPECIALIZED TOOLS & AGENTS (10+)
    # ========================================================================

    # DISASSEMBLER - Reverse engineering
    org.define_position(Position(
        title="DISASSEMBLER",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["disassembly", "reverse_engineering", "binary_analysis"],
        responsibilities=["Binary disassembly", "Reverse engineering", "Malware analysis"],
        reports_to="Security Division Head",
        can_escalate_to=["Security Division Head", "CSO"],
        max_concurrent_tasks=4
    ))

    # RUST-DEBUGGER - Specialized Rust debugging
    org.define_position(Position(
        title="RUST-DEBUGGER",
        level=OrganizationalLevel.WORKER,
        division=Division.QUALITY_ASSURANCE,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["rust_debugging", "memory_safety_analysis", "borrow_checker"],
        responsibilities=["Rust debugging", "Memory safety analysis", "Borrow checker issues"],
        reports_to="OVERSIGHT",
        can_escalate_to=["OVERSIGHT"],
        max_concurrent_tasks=5
    ))

    # AUDITOR - General auditing
    org.define_position(Position(
        title="AUDITOR",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.QUALITY_ASSURANCE,
        authority=AuthorityLevel.TEAM,
        capabilities=["auditing", "compliance", "quality_assurance"],
        responsibilities=["General auditing", "Compliance checks", "Quality audits"],
        reports_to="OVERSIGHT",
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["audit_reports"],
        max_concurrent_tasks=8
    ))

    # AGENTSMITH - Meta-agent (manages other agents)
    org.define_position(Position(
        title="AGENTSMITH",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.EXECUTIVE,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["agent_management", "meta_coordination", "agent_optimization"],
        responsibilities=["Agent management", "Meta-coordination", "Agent performance"],
        reports_to="COORDINATOR",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["agent_assignments", "agent_optimizations"],
        max_concurrent_tasks=15
    ))

    # PSYOPS & PSYOPS-AGENT - Psychological operations
    org.define_position(Position(
        title="PSYOPS",
        level=OrganizationalLevel.MIDDLE_MANAGEMENT,
        division=Division.SECURITY,
        authority=AuthorityLevel.TEAM,
        capabilities=["psychological_operations", "social_engineering_defense", "influence_operations"],
        responsibilities=["PsyOps defense", "Social engineering countermeasures", "Influence analysis"],
        reports_to="CSO",  # Sensitive operations
        can_delegate_to=[OrganizationalLevel.WORKER],
        can_approve=["psyops_strategies"],
        max_concurrent_tasks=6
    ))

    org.define_position(Position(
        title="PSYOPS-AGENT",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["psyops_execution", "social_engineering_testing"],
        responsibilities=["PsyOps execution", "Social engineering testing", "Influence operations"],
        reports_to="PSYOPS",
        can_escalate_to=["PSYOPS", "CSO"],
        max_concurrent_tasks=4
    ))

    # QADIRECTOR - QA leadership
    org.define_position(Position(
        title="QADIRECTOR",
        level=OrganizationalLevel.SENIOR_MANAGEMENT,
        division=Division.QUALITY_ASSURANCE,
        authority=AuthorityLevel.DIVISIONAL,
        capabilities=["qa_leadership", "quality_strategy", "testing_excellence"],
        responsibilities=["QA direction", "Quality strategy", "Testing excellence"],
        reports_to="OVERSIGHT",
        can_delegate_to=[OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["qa_strategies", "quality_standards"],
        veto_power=True,  # Can block low-quality releases
        max_concurrent_tasks=10
    ))

    # CLAUDECODE-PROMPTINJECTOR - AI/LLM security testing
    org.define_position(Position(
        title="CLAUDECODE-PROMPTINJECTOR",
        level=OrganizationalLevel.WORKER,
        division=Division.SECURITY,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["prompt_injection", "llm_security_testing", "ai_red_teaming"],
        responsibilities=["LLM security testing", "Prompt injection testing", "AI red teaming"],
        reports_to="Red Team Lead",
        can_escalate_to=["Red Team Lead", "Security Division Head"],
        max_concurrent_tasks=4
    ))

    # LEADENGINEER - Technical leadership (also an executing agent, not just position)
    org.define_position(Position(
        title="LEADENGINEER",
        level=OrganizationalLevel.EXECUTIVE,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.STRATEGIC,
        capabilities=["technical_leadership", "architecture", "engineering_excellence"],
        responsibilities=["Technical leadership", "Engineering standards", "Architectural oversight"],
        reports_to="CTO",
        can_delegate_to=[OrganizationalLevel.SENIOR_MANAGEMENT, OrganizationalLevel.MIDDLE_MANAGEMENT, OrganizationalLevel.WORKER],
        can_approve=["technical_standards", "architecture_decisions"],
        max_concurrent_tasks=10
    ))

    # ANDROIDMOBILE - Specific Android mobile development
    org.define_position(Position(
        title="ANDROIDMOBILE",
        level=OrganizationalLevel.WORKER,
        division=Division.SOFTWARE_ENGINEERING,
        authority=AuthorityLevel.INDIVIDUAL,
        capabilities=["android", "mobile", "java", "kotlin"],
        responsibilities=["Android development", "Mobile apps", "Google Play deployment"],
        reports_to="Software Division Head",
        can_escalate_to=["Software Division Head"],
        max_concurrent_tasks=5
    ))

    return org


def create_phase2_complete_organization() -> OrganizationalChart:
    """
    Create complete organizational structure with ALL agents (Phase 1 + Phase 2)

    Returns:
        OrganizationalChart with all 91+ agents
    """
    # Start with Phase 1 organization
    org = create_complete_organization()

    # Add Phase 2 agents
    org = add_phase2_agents(org)

    return org


__all__ = ["add_phase2_agents", "create_phase2_complete_organization"]
