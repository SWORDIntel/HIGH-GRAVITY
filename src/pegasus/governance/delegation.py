import logging
from typing import Dict, List

# Define the Swarm Hierarchy
# Pegasus Swarm Corporate Governance Structure (v4.0)
# DIRECTOR possesses Unilateral Authority over all departments and tiers.
# Department Heads (CSO, CTO, COORDINATOR) manage their own Middle Management (Division Leads).
# Middle Management governs their specialized agents directly.

HIERARCHY = {
    "DIRECTOR": [
        "COORDINATOR", "CSO", "CTO", "ARCHITECT", "SECURITYAUDITOR", "RESEARCHER", 
        "OPTIMIZER", "DIRECTOR"
    ],
    # Department Heads
    "CSO": ["SECURITY_LEAD", "SECURITYCHAOSAGENT"],
    "CTO": ["ARCHITECT_LEAD", "DEVOPS_LEAD"],
    "COORDINATOR": ["RESEARCH_LEAD", "OPS_LEAD"],

    # Middle Management (Division Leads)
    "SECURITY_LEAD": ["SECURITY", "BASTION", "GHOST-PROTOCOL-AGENT", "PROMPT-DEFENDER", "QUANTUMGUARD"],
    "ARCHITECT_LEAD": ["ARCHITECT", "OPTIMIZER", "PACKAGER", "CONSTRUCTOR", "DOCGEN"],
    "DEVOPS_LEAD": ["INFRASTRUCTURE", "DEPLOYER", "DOCKER-AGENT", "PROXMOX-AGENT", "GNU"],
    "RESEARCH_LEAD": ["RESEARCHER", "COMPRESSOR", "SHUFFLER", "MONITOR", "PLANNER", "ORCHESTRATOR", "OVERSIGHT"],
    "LANGUAGE_LEADS": ["PYTHON-INTERNAL", "RUST-INTERNAL-AGENT", "C-INTERNAL", "GO-INTERNAL-AGENT", "JAVA-INTERNAL", "TYPESCRIPT-INTERNAL-AGENT"],

    # Division-specific Worker Agents (The "Engine Room")
    "SECURITY": ["SECURITYAUDITOR", "RED-TEAM"],
    "INFRASTRUCTURE": ["NPU", "DATABASE", "ZFS-INTERNAL"],
    "WEB_MOBILE": ["WEB", "MOBILE", "PYGUI", "TUI"],
    "VOICE": ["VOICE-PROCESSOR", "VOICE-INTERFACE", "VOICE-BIOMETRIC"],
    "QA": ["REVIEWER", "COMPLIANCE", "PROFILER", "DEBUGGER", "TESTBED", "LINTER"]
}

def get_manager_for_role(role: str) -> str:
    """Recursively find the superior for any given agent role."""
    # Unilateral Authority: Director can command anyone
    if role in HIERARCHY["DIRECTOR"]: return "DIRECTOR"

    for manager, subordinates in HIERARCHY.items():
        if role in subordinates:
            return manager

    return "DIRECTOR" # Default escalation to Director

def validate_delegation(source: str, target: str) -> bool:
    """Enforces strict chain of command, with Director Unilateral Override."""
    if source == "DIRECTOR": return True # Unilateral Auth

    # Check if source is a manager of the target
    subordinates = HIERARCHY.get(source, [])
    return target in subordinates


class DelegationEngine:
    def __init__(self):
        self.logger = logging.getLogger("Pegasus-Governance")
        
    def validate_delegation(self, source: str, target: str) -> bool:
        """Enforces chain of command."""
        if source == "HUMAN": return True # Human override
        return target in HIERARCHY.get(source, [])

    def escalate(self, agent_id: str, issue: str):
        self.logger.warning(f"ESCALATION: {agent_id} reported: {issue}")
