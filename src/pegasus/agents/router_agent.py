#!/usr/bin/env python3
"""
ROUTER Agent - Meta-Orchestration Layer
Sits above DIRECTOR to automatically coordinate agent invocations on every turn
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class RouterAgent:
    """
    ROUTER Agent - Automatic Agent Coordination

    Responsibilities:
    - Analyze incoming requests on every turn
    - Determine which agents need to be invoked
    - Coordinate multi-agent workflows
    - Route tasks to appropriate specialist agents
    - Escalate complex tasks to DIRECTOR
    """

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.name = "ROUTER"
        self.level = "META"  # Above DIRECTOR
        self.agent_registry = self._load_agent_registry()

        # Decision matrix for auto-invocation
        self.routing_rules = self._initialize_routing_rules()

    def _load_agent_registry(self) -> Dict:
        """Load agent registry"""
        try:
            with open(self.project_root / "config" / "agent-registry.json", 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"agents": []}

    def _initialize_routing_rules(self) -> Dict[str, List[str]]:
        """
        Initialize routing rules based on keywords/patterns

        Returns:
            Dict mapping patterns to agent names
        """
        return {
            # Security-related patterns
            "security|vulnerability|exploit|attack|threat": ["SECURITY", "AUDITOR"],
            "crypto|encryption|decrypt|hash": ["CRYPTO", "CRYPTOEXPERT"],
            "penetration|pentest|red.?team": ["RED-TEAM", "SECURITY"],

            # Development patterns
            "bug|fix|error|issue": ["DEBUGGER", "LINTER"],
            "test|testing|qa": ["QADIRECTOR", "TESTBED"],
            "deploy|deployment|release": ["DEPLOYER", "INFRASTRUCTURE"],
            "optimize|performance|speed": ["OPTIMIZER", "HARDWARE"],

            # Infrastructure patterns
            "docker|container|kubernetes": ["DOCKER-AGENT", "INFRASTRUCTURE"],
            "database|sql|postgres|db": ["DATABASE", "OLAP"],
            "network|bgp|routing": ["BGP-.*", "INFRASTRUCTURE"],

            # Code-specific patterns
            "python": ["PYTHON-INTERNAL"],
            "rust": ["RUST-DEBUGGER"],
            "typescript|javascript": ["TYPESCRIPT-INTERNAL-AGENT"],
            "c\\+\\+|cpp": ["CPP-INTERNAL-AGENT"],
            "go|golang": ["GO-INTERNAL-AGENT"],

            # Architecture/Planning
            "design|architect|plan": ["ARCHITECT", "PLANNER", "DIRECTOR"],
            "integrate|integration": ["INTEGRATION"],
            "coordinate|orchestrate": ["ORCHESTRATOR", "COORDINATOR"],

            # Documentation
            "document|docs|readme": ["DOCGEN"],

            # Hardware
            "hardware|npu|gpu|cpu": ["HARDWARE.*", "NPU"],

            # Monitoring
            "monitor|metrics|telemetry": ["MONITOR", "OVERSIGHT"],
        }

    def analyze_request(self, request: str) -> Dict[str, Any]:
        """
        Analyze request and determine which agents to invoke

        Args:
            request: User request string

        Returns:
            Analysis with recommended agents
        """
        request_lower = request.lower()

        # Find matching routing rules
        matched_agents = set()
        matched_patterns = []

        import re
        for pattern, agents in self.routing_rules.items():
            if re.search(pattern, request_lower, re.IGNORECASE):
                matched_patterns.append(pattern)
                for agent_pattern in agents:
                    # Find agents matching the pattern
                    matching = self._find_agents_by_pattern(agent_pattern)
                    matched_agents.update(matching)

        # Determine complexity
        complexity = self._assess_complexity(request, len(matched_agents))

        # Build invocation plan
        plan = self._build_invocation_plan(
            matched_agents=list(matched_agents),
            complexity=complexity,
            request=request
        )

        return {
            "request": request,
            "matched_patterns": matched_patterns,
            "recommended_agents": plan["agents"],
            "complexity": complexity,
            "should_invoke": plan["should_invoke"],
            "invocation_order": plan["order"],
            "reasoning": plan["reasoning"],
            "timestamp": datetime.now().isoformat()
        }

    def _find_agents_by_pattern(self, pattern: str) -> List[str]:
        """Find agents matching a pattern (supports regex)"""
        import re
        agents = self.agent_registry.get("agents", [])

        matches = []
        pattern_regex = re.compile(pattern, re.IGNORECASE)

        for agent in agents:
            agent_name = agent.get("name", "")
            if pattern_regex.search(agent_name):
                matches.append(agent_name)

        return matches

    def _assess_complexity(self, request: str, matched_agent_count: int) -> str:
        """Assess request complexity"""
        # Simple heuristics
        word_count = len(request.split())

        if matched_agent_count == 0:
            return "UNKNOWN"
        elif matched_agent_count == 1 and word_count < 20:
            return "SIMPLE"
        elif matched_agent_count <= 3 and word_count < 50:
            return "MEDIUM"
        else:
            return "COMPLEX"

    def _build_invocation_plan(
        self,
        matched_agents: List[str],
        complexity: str,
        request: str
    ) -> Dict[str, Any]:
        """Build agent invocation plan"""

        should_invoke = len(matched_agents) > 0

        # Determine invocation order
        order = []
        reasoning = []

        if complexity == "SIMPLE" and len(matched_agents) == 1:
            order = matched_agents
            reasoning.append(f"Direct invocation: {matched_agents[0]}")

        elif complexity == "MEDIUM":
            # Invoke specialists in parallel, then coordinator
            order = matched_agents
            if "COORDINATOR" not in matched_agents:
                order.append("COORDINATOR")
            reasoning.append(f"Parallel invocation: {', '.join(matched_agents[:3])}")
            reasoning.append("Coordination by COORDINATOR")

        elif complexity == "COMPLEX":
            # Escalate to DIRECTOR for planning
            order = ["PLANNER", "DIRECTOR"] + matched_agents + ["COORDINATOR"]
            reasoning.append("Complex task detected")
            reasoning.append("Escalating to DIRECTOR for planning")
            reasoning.append(f"Will coordinate {len(matched_agents)} specialist agents")

        else:
            # Unknown complexity - use ROUTER judgment
            if "question" in request.lower() or "?" in request:
                order = ["RESEARCHER"]
                reasoning.append("Research task detected")
            else:
                order = ["DIRECTOR"]
                reasoning.append("Unclear intent - escalating to DIRECTOR")

        # Limit to top 5 agents to prevent overwhelming
        if len(order) > 5:
            order = order[:5]
            reasoning.append(f"Limited to top 5 agents (from {len(matched_agents)} candidates)")

        return {
            "agents": list(set(order)),  # Remove duplicates
            "should_invoke": should_invoke,
            "order": order,
            "reasoning": reasoning
        }

    def route_request(self, request: str, auto_invoke: bool = True) -> Dict[str, Any]:
        """
        Main routing function - called on every turn

        Args:
            request: User request
            auto_invoke: Whether to actually invoke agents (vs. just recommend)

        Returns:
            Routing result with invocations
        """
        analysis = self.analyze_request(request)

        result = {
            **analysis,
            "auto_invoke": auto_invoke,
            "router_agent": self.name,
            "router_level": self.level
        }

        if auto_invoke and analysis["should_invoke"]:
            result["invocations"] = []

            for agent_name in analysis["invocation_order"]:
                invocation = {
                    "agent": agent_name,
                    "status": "queued",
                    "timestamp": datetime.now().isoformat()
                }
                result["invocations"].append(invocation)

        return result

    def format_routing_result(self, result: Dict[str, Any]) -> str:
        """Format routing result for display"""
        lines = [
            "╔════════════════════════════════════════════════════════╗",
            "║  ROUTER AGENT - Automatic Coordination Analysis       ║",
            "╚════════════════════════════════════════════════════════╝",
            "",
            f"Request: {result['request'][:80]}...",
            f"Complexity: {result['complexity']}",
            f"Matched Patterns: {len(result['matched_patterns'])}",
            ""
        ]

        if result['should_invoke']:
            lines.append("Recommended Agent Invocations:")
            for i, agent in enumerate(result['invocation_order'], 1):
                lines.append(f"  {i}. {agent}")
            lines.append("")

            lines.append("Reasoning:")
            for reason in result['reasoning']:
                lines.append(f"  • {reason}")
        else:
            lines.append("No automatic agent invocation recommended")
            lines.append("Request can be handled directly")

        lines.append("")
        lines.append(f"Auto-Invoke: {'✓ ENABLED' if result['auto_invoke'] else '✗ DISABLED'}")

        return "\n".join(lines)


def test_router():
    """Test the ROUTER agent"""
    router = RouterAgent()

    test_requests = [
        "Fix the security vulnerability in the authentication module",
        "Deploy the application to production",
        "Write Python code to process data",
        "How does the NPU acceleration work?",
        "Coordinate a complex multi-agent optimization task",
    ]

    print("=" * 70)
    print("ROUTER AGENT TEST")
    print("=" * 70)
    print()

    for request in test_requests:
        result = router.route_request(request, auto_invoke=False)
        print(router.format_routing_result(result))
        print()


if __name__ == "__main__":
    test_router()
