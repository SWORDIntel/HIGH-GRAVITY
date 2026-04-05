#!/usr/bin/env python3
"""
Proactive Agent Invocation System for Claude Code
Automatically and aggressively invokes specialized agents based on user intent and context.
"""

import asyncio
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# INTENT CLASSIFICATION
# ============================================================================


class UserIntent:
    """Classifies user intent from natural language"""

    # Architecture & Design
    DESIGN = "design"
    ARCHITECTURE = "architecture"
    REFACTOR = "refactor"

    # Development
    BUILD = "build"
    CREATE = "create"
    IMPLEMENT = "implement"
    ADD_FEATURE = "add_feature"

    # Debugging & Testing
    DEBUG = "debug"
    TEST = "test"
    FIX_BUG = "fix_bug"
    PERFORMANCE = "performance"

    # Security
    SECURITY_AUDIT = "security_audit"
    SECURITY_FIX = "security_fix"
    PENTEST = "pentest"

    # Infrastructure
    DEPLOY = "deploy"
    INFRASTRUCTURE = "infrastructure"
    DOCKER = "docker"
    CI_CD = "ci_cd"

    # Code Quality
    LINT = "lint"
    OPTIMIZE = "optimize"
    REVIEW = "review"

    # Documentation
    DOCUMENT = "document"
    EXPLAIN = "explain"

    # Research & Analysis
    RESEARCH = "research"
    ANALYZE = "analyze"


@dataclass
class IntentPattern:
    """Pattern for detecting user intent"""
    intent: str
    keywords: List[str]
    patterns: List[str]
    priority: int = 1
    agents: List[str] = field(default_factory=list)
    context_required: List[str] = field(default_factory=list)


class IntentClassifier:
    """Classifies user intent from messages"""

    def __init__(self):
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> List[IntentPattern]:
        """Build comprehensive intent patterns"""
        return [
            # Architecture & Design
            IntentPattern(
                intent=UserIntent.DESIGN,
                keywords=["design", "architect", "structure", "plan", "blueprint"],
                patterns=[
                    r"design\s+(?:a|an|the)\s+\w+",
                    r"how\s+(?:should|would)\s+(?:i|we)\s+(?:design|structure|architect)",
                    r"what\'s\s+the\s+best\s+(?:design|architecture|structure)",
                ],
                priority=10,
                agents=["architect", "apidesigner", "director"]
            ),
            IntentPattern(
                intent=UserIntent.ARCHITECTURE,
                keywords=["architecture", "system design", "high-level", "components"],
                patterns=[
                    r"(?:review|analyze|evaluate)\s+(?:the\s+)?architecture",
                    r"architecture\s+(?:for|of)",
                    r"system\s+design",
                ],
                priority=10,
                agents=["architect", "director"]
            ),
            IntentPattern(
                intent=UserIntent.REFACTOR,
                keywords=["refactor", "restructure", "reorganize", "clean up", "improve"],
                patterns=[
                    r"refactor\s+(?:the\s+)?\w+",
                    r"clean\s+up\s+(?:the\s+)?code",
                    r"improve\s+(?:the\s+)?(?:code|structure)",
                    r"restructure",
                ],
                priority=8,
                agents=["architect", "optimizer", "linter"]
            ),

            # Development
            IntentPattern(
                intent=UserIntent.BUILD,
                keywords=["build", "compile", "make", "run build"],
                patterns=[
                    r"(?:run|execute)\s+(?:the\s+)?build",
                    r"build\s+(?:the\s+)?(?:project|application|code)",
                    r"compile\s+(?:the\s+)?code",
                ],
                priority=7,
                agents=["constructor", "deployer"]
            ),
            IntentPattern(
                intent=UserIntent.CREATE,
                keywords=["create", "generate", "scaffold", "new"],
                patterns=[
                    r"create\s+(?:a|an)\s+(?:new\s+)?\w+",
                    r"generate\s+(?:a|an)\s+\w+",
                    r"scaffold\s+(?:a|an)\s+\w+",
                    r"(?:set\s+up|setup)\s+(?:a|an)\s+new",
                ],
                priority=9,
                agents=["constructor", "architect"]
            ),
            IntentPattern(
                intent=UserIntent.IMPLEMENT,
                keywords=["implement", "add", "write", "code"],
                patterns=[
                    r"implement\s+(?:a|an|the)\s+\w+",
                    r"add\s+(?:a|an|the)\s+(?:feature|function|method|class)",
                    r"write\s+(?:a|an|the)\s+(?:function|class|module)",
                ],
                priority=8,
                agents=["constructor", "patcher"]
            ),
            IntentPattern(
                intent=UserIntent.ADD_FEATURE,
                keywords=["feature", "functionality", "capability"],
                patterns=[
                    r"add\s+(?:a|an|the)\s+(?:new\s+)?feature",
                    r"implement\s+(?:a|an|the)\s+feature",
                    r"(?:build|create)\s+(?:a|an)\s+feature",
                ],
                priority=9,
                agents=["architect", "constructor", "patcher"]
            ),

            # Debugging & Testing
            IntentPattern(
                intent=UserIntent.DEBUG,
                keywords=["debug", "investigate", "troubleshoot", "trace"],
                patterns=[
                    r"debug\s+(?:the\s+)?(?:issue|problem|bug|error)",
                    r"(?:investigate|troubleshoot)\s+(?:the\s+)?(?:issue|problem|error)",
                    r"(?:find|locate)\s+(?:the\s+)?(?:bug|issue|problem)",
                    r"why\s+(?:is|does|isn\'t)",
                ],
                priority=10,
                agents=["debugger", "researcher"]
            ),
            IntentPattern(
                intent=UserIntent.TEST,
                keywords=["test", "unit test", "integration test", "e2e"],
                patterns=[
                    r"(?:write|create|add)\s+(?:unit\s+)?tests?",
                    r"test\s+(?:the\s+)?(?:code|function|feature)",
                    r"(?:run|execute)\s+(?:the\s+)?tests?",
                    r"(?:integration|e2e|end-to-end)\s+tests?",
                ],
                priority=9,
                agents=["testbed", "qadirector"]
            ),
            IntentPattern(
                intent=UserIntent.FIX_BUG,
                keywords=["fix", "bug", "error", "issue", "crash"],
                patterns=[
                    r"fix\s+(?:the\s+)?(?:bug|error|issue)",
                    r"(?:resolve|address)\s+(?:the\s+)?(?:bug|issue|problem)",
                    r"(?:the\s+)?(?:code|application)\s+(?:is\s+)?(?:crashing|failing|broken)",
                ],
                priority=10,
                agents=["debugger", "patcher", "researcher"]
            ),
            IntentPattern(
                intent=UserIntent.PERFORMANCE,
                keywords=["optimize", "performance", "slow", "faster", "speed up"],
                patterns=[
                    r"optimize\s+(?:the\s+)?(?:code|performance)",
                    r"(?:improve|increase)\s+performance",
                    r"(?:make|run)\s+faster",
                    r"(?:too\s+)?slow",
                    r"speed\s+up",
                ],
                priority=8,
                agents=["optimizer", "researcher", "npu"]
            ),

            # Security
            IntentPattern(
                intent=UserIntent.SECURITY_AUDIT,
                keywords=["security", "audit", "vulnerability", "secure"],
                patterns=[
                    r"security\s+audit",
                    r"(?:check|scan)\s+for\s+vulnerabilities",
                    r"(?:is\s+(?:this|the)\s+)?(?:code\s+)?secure",
                    r"security\s+(?:review|analysis)",
                ],
                priority=10,
                agents=["security", "auditor", "bastion"]
            ),
            IntentPattern(
                intent=UserIntent.SECURITY_FIX,
                keywords=["security fix", "vulnerability", "exploit", "patch"],
                patterns=[
                    r"fix\s+(?:the\s+)?(?:security\s+)?(?:vulnerability|issue)",
                    r"patch\s+(?:the\s+)?(?:vulnerability|security\s+issue)",
                    r"secure\s+(?:the\s+)?code",
                ],
                priority=10,
                agents=["security", "patcher", "bastion"]
            ),
            IntentPattern(
                intent=UserIntent.PENTEST,
                keywords=["pentest", "penetration test", "red team", "attack"],
                patterns=[
                    r"(?:penetration|pen)\s+test",
                    r"red\s+team",
                    r"(?:test|check)\s+(?:for\s+)?(?:exploits|attacks)",
                ],
                priority=9,
                agents=["red-team", "security", "chaos-agent"]
            ),

            # Infrastructure
            IntentPattern(
                intent=UserIntent.DEPLOY,
                keywords=["deploy", "deployment", "release", "ship"],
                patterns=[
                    r"deploy\s+(?:the\s+)?(?:code|application|service)",
                    r"(?:create|setup)\s+(?:a\s+)?deployment",
                    r"release\s+(?:to\s+)?(?:production|staging)",
                ],
                priority=9,
                agents=["deployer", "infrastructure", "monitor"]
            ),
            IntentPattern(
                intent=UserIntent.INFRASTRUCTURE,
                keywords=["infrastructure", "setup", "configure", "provision"],
                patterns=[
                    r"(?:setup|configure|provision)\s+infrastructure",
                    r"infrastructure\s+(?:setup|configuration)",
                    r"cloud\s+(?:infrastructure|setup)",
                ],
                priority=8,
                agents=["infrastructure", "deployer", "cisco-agent"]
            ),
            IntentPattern(
                intent=UserIntent.DOCKER,
                keywords=["docker", "container", "dockerfile", "compose"],
                patterns=[
                    r"(?:create|write|setup)\s+(?:a\s+)?dockerfile",
                    r"docker\s+(?:compose|container|image)",
                    r"containerize",
                ],
                priority=8,
                agents=["docker-agent", "infrastructure"]
            ),
            IntentPattern(
                intent=UserIntent.CI_CD,
                keywords=["ci", "cd", "pipeline", "github actions", "workflow"],
                patterns=[
                    r"(?:ci|cd|cicd)\s+pipeline",
                    r"github\s+(?:actions|workflows?)",
                    r"(?:setup|create)\s+(?:a\s+)?(?:pipeline|workflow)",
                ],
                priority=8,
                agents=["infrastructure", "deployer"]
            ),

            # Code Quality
            IntentPattern(
                intent=UserIntent.LINT,
                keywords=["lint", "format", "style", "prettier", "eslint"],
                patterns=[
                    r"lint\s+(?:the\s+)?code",
                    r"(?:check|fix)\s+(?:code\s+)?(?:style|formatting)",
                    r"format\s+(?:the\s+)?code",
                ],
                priority=7,
                agents=["linter", "optimizer"]
            ),
            IntentPattern(
                intent=UserIntent.OPTIMIZE,
                keywords=["optimize", "improve", "enhance", "better"],
                patterns=[
                    r"optimize\s+(?:the\s+)?code",
                    r"improve\s+(?:code\s+)?quality",
                    r"make\s+(?:it|this|the\s+code)\s+better",
                ],
                priority=7,
                agents=["optimizer", "linter"]
            ),
            IntentPattern(
                intent=UserIntent.REVIEW,
                keywords=["review", "code review", "feedback", "suggestions"],
                patterns=[
                    r"code\s+review",
                    r"review\s+(?:the\s+)?(?:code|changes|pr|pull\s+request)",
                    r"(?:give|provide)\s+feedback",
                ],
                priority=8,
                agents=["auditor", "architect", "linter"]
            ),

            # Documentation
            IntentPattern(
                intent=UserIntent.DOCUMENT,
                keywords=["document", "documentation", "readme", "docs"],
                patterns=[
                    r"(?:write|create|add|generate)\s+(?:the\s+)?(?:documentation|docs)",
                    r"document\s+(?:the\s+)?(?:code|api|function)",
                    r"(?:create|update)\s+(?:the\s+)?readme",
                ],
                priority=7,
                agents=["docgen", "researcher"]
            ),
            IntentPattern(
                intent=UserIntent.EXPLAIN,
                keywords=["explain", "how does", "what is", "understand"],
                patterns=[
                    r"explain\s+(?:how|what|why)",
                    r"how\s+does\s+(?:this|the)",
                    r"what\s+(?:is|does)\s+(?:this|the)",
                    r"(?:help\s+me\s+)?understand",
                ],
                priority=6,
                agents=["researcher", "docgen"]
            ),

            # Research & Analysis
            IntentPattern(
                intent=UserIntent.RESEARCH,
                keywords=["research", "find", "search", "explore"],
                patterns=[
                    r"research\s+(?:how|what|where)",
                    r"(?:find|search\s+for)\s+(?:information|examples|docs)",
                    r"explore\s+(?:the\s+)?(?:codebase|options)",
                ],
                priority=7,
                agents=["researcher", "explorer"]
            ),
            IntentPattern(
                intent=UserIntent.ANALYZE,
                keywords=["analyze", "analysis", "examine", "inspect"],
                patterns=[
                    r"analyz[ae]\s+(?:the\s+)?(?:code|data|performance)",
                    r"(?:examine|inspect)\s+(?:the\s+)?(?:code|system)",
                    r"(?:code|data|performance)\s+analysis",
                ],
                priority=7,
                agents=["researcher", "datascience", "optimizer"]
            ),
        ]

    def classify(self, message: str, context: Optional[Dict[str, Any]] = None) -> List[Tuple[str, float, List[str]]]:
        """
        Classify user intent from message

        Returns:
            List of (intent, confidence, agents) tuples, sorted by confidence
        """
        message_lower = message.lower()
        results = []

        for pattern in self.patterns:
            base_confidence = 0.0

            # Check keywords
            keyword_matches = sum(1 for kw in pattern.keywords if kw in message_lower)
            if keyword_matches > 0:
                base_confidence += (keyword_matches / len(pattern.keywords)) * 0.5

            # Check regex patterns
            pattern_matches = sum(1 for p in pattern.patterns if re.search(p, message_lower))
            if pattern_matches > 0:
                base_confidence += (pattern_matches / len(pattern.patterns)) * 0.5

            # Only continue if we have a match
            if base_confidence == 0:
                continue

            # Start with base confidence (0.5 or 1.0)
            confidence = base_confidence

            # Apply priority boost (not multiplier) - high priority gets boost
            priority_boost = (pattern.priority / 10.0) * 0.3  # Max 30% boost for priority 10
            confidence += priority_boost

            # Context matching
            if context and pattern.context_required:
                context_matches = sum(1 for req in pattern.context_required if req in context)
                if context_matches > 0:
                    confidence *= 1.2

            # Ensure we don't exceed 1.0
            confidence = min(confidence, 1.0)

            if confidence > 0.1:  # Threshold for consideration
                results.append((pattern.intent, confidence, pattern.agents))

        # Sort by confidence (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        return results


# ============================================================================
# PROACTIVE AGENT SELECTOR
# ============================================================================


@dataclass
class AgentInvocationRecommendation:
    """Recommendation to invoke an agent"""
    agent_name: str
    confidence: float
    reason: str
    intent: str
    auto_invoke: bool = False
    priority: int = 5


class ProactiveAgentSelector:
    """Selects appropriate agents based on user intent and context"""

    def __init__(self, agent_registry: Optional[Any] = None):
        self.agent_registry = agent_registry
        self.intent_classifier = IntentClassifier()
        self.invocation_history = defaultdict(list)
        self.success_rates = defaultdict(lambda: 0.8)  # Default 80% success rate

        # Agent specializations
        self.agent_specializations = self._build_specializations()

        # Proactive thresholds
        self.auto_invoke_threshold = 0.7  # Auto-invoke if confidence >= 70%
        self.suggest_threshold = 0.5       # Suggest if confidence >= 50%

    def _build_specializations(self) -> Dict[str, Dict[str, float]]:
        """Build agent specialization weights for different intents"""
        return {
            UserIntent.DESIGN: {
                "architect": 1.0,
                "apidesigner": 0.9,
                "director": 0.8,
            },
            UserIntent.ARCHITECTURE: {
                "architect": 1.0,
                "director": 0.9,
            },
            UserIntent.REFACTOR: {
                "architect": 0.9,
                "optimizer": 1.0,
                "linter": 0.8,
            },
            UserIntent.DEBUG: {
                "debugger": 1.0,
                "researcher": 0.8,
                "disassembler": 0.6,
            },
            UserIntent.TEST: {
                "testbed": 1.0,
                "qadirector": 0.9,
            },
            UserIntent.FIX_BUG: {
                "debugger": 0.9,
                "patcher": 1.0,
                "researcher": 0.7,
            },
            UserIntent.PERFORMANCE: {
                "optimizer": 1.0,
                "npu": 0.9,
                "researcher": 0.6,
            },
            UserIntent.SECURITY_AUDIT: {
                "security": 1.0,
                "auditor": 0.9,
                "bastion": 0.8,
            },
            UserIntent.SECURITY_FIX: {
                "security": 0.9,
                "patcher": 1.0,
                "bastion": 0.8,
            },
            UserIntent.DEPLOY: {
                "deployer": 1.0,
                "infrastructure": 0.8,
                "monitor": 0.7,
            },
            UserIntent.INFRASTRUCTURE: {
                "infrastructure": 1.0,
                "deployer": 0.7,
            },
            UserIntent.DOCKER: {
                "docker-agent": 1.0,
                "infrastructure": 0.6,
            },
            UserIntent.LINT: {
                "linter": 1.0,
                "optimizer": 0.6,
            },
            UserIntent.OPTIMIZE: {
                "optimizer": 1.0,
                "linter": 0.5,
            },
            UserIntent.REVIEW: {
                "auditor": 1.0,
                "architect": 0.8,
                "linter": 0.7,
            },
            UserIntent.DOCUMENT: {
                "docgen": 1.0,
                "researcher": 0.5,
            },
            UserIntent.RESEARCH: {
                "researcher": 1.0,
            },
            UserIntent.ANALYZE: {
                "researcher": 0.9,
                "datascience": 0.8,
                "optimizer": 0.6,
            },
        }

    def select_agents(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        aggressive: bool = True
    ) -> List[AgentInvocationRecommendation]:
        """
        Select agents to invoke based on user message and context

        Args:
            message: User message
            context: Additional context (file types, git status, etc.)
            aggressive: If True, be more aggressive with auto-invocation

        Returns:
            List of agent invocation recommendations, sorted by priority
        """
        recommendations = []

        # Classify intent
        intents = self.intent_classifier.classify(message, context)

        if not intents:
            return recommendations

        # Process each detected intent
        for intent, intent_confidence, suggested_agents in intents:
            # Get specialized agents for this intent
            specialized = self.agent_specializations.get(intent, {})

            # Combine suggested agents with specialized agents
            all_agents = set(suggested_agents)
            all_agents.update(specialized.keys())

            for agent_name in all_agents:
                # Calculate confidence
                base_confidence = intent_confidence

                # Apply specialization weight
                spec_weight = specialized.get(agent_name, 0.5)
                confidence = base_confidence * spec_weight

                # Apply success rate
                confidence *= self.success_rates[agent_name]

                # Context boost
                if context:
                    confidence = self._apply_context_boost(
                        agent_name, confidence, context
                    )

                # Determine if auto-invoke
                auto_invoke = False
                if aggressive:
                    auto_invoke = confidence >= self.auto_invoke_threshold
                else:
                    auto_invoke = confidence >= 0.85

                # Only recommend if above suggestion threshold
                if confidence >= self.suggest_threshold:
                    recommendations.append(
                        AgentInvocationRecommendation(
                            agent_name=agent_name,
                            confidence=confidence,
                            reason=f"Detected intent: {intent}",
                            intent=intent,
                            auto_invoke=auto_invoke,
                            priority=int(confidence * 10)
                        )
                    )

        # Sort by confidence (descending)
        recommendations.sort(key=lambda x: x.confidence, reverse=True)

        # Deduplicate while keeping highest confidence
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec.agent_name not in seen:
                seen.add(rec.agent_name)
                unique_recommendations.append(rec)

        return unique_recommendations

    def _apply_context_boost(
        self,
        agent_name: str,
        confidence: float,
        context: Dict[str, Any]
    ) -> float:
        """Apply context-based confidence boost"""
        boost = 1.0

        # File type context
        file_types = context.get("file_types", [])
        if file_types:
            # Language-specific agents
            lang_agents = {
                "python": ["python-internal"],
                "javascript": ["typescript-internal-agent", "web"],
                "typescript": ["typescript-internal-agent", "web"],
                "rust": ["rust-debugger"],
                "go": ["go-internal-agent"],
                "java": ["java-internal"],
                "c": ["c-internal"],
                "cpp": ["cpp-internal-agent"],
            }

            for lang, agents in lang_agents.items():
                if any(lang in ft for ft in file_types) and agent_name in agents:
                    boost *= 1.3

        # Git context
        if context.get("has_uncommitted_changes") and agent_name in ["linter", "auditor"]:
            boost *= 1.2

        if context.get("has_failing_tests") and agent_name in ["debugger", "testbed"]:
            boost *= 1.5

        # Build errors
        if context.get("has_build_errors") and agent_name in ["debugger", "constructor"]:
            boost *= 1.4

        return min(confidence * boost, 1.0)

    def record_invocation(self, agent_name: str, success: bool):
        """Record agent invocation outcome to learn success rates"""
        self.invocation_history[agent_name].append({
            "timestamp": datetime.now(),
            "success": success
        })

        # Update success rate (exponential moving average)
        current_rate = self.success_rates[agent_name]
        self.success_rates[agent_name] = 0.9 * current_rate + 0.1 * (1.0 if success else 0.0)


# ============================================================================
# PROACTIVE INVOCATION MANAGER
# ============================================================================


class ProactiveInvocationManager:
    """Main manager for proactive agent invocation"""

    def __init__(self, agent_registry: Optional[Any] = None, aggressive: bool = True):
        self.agent_registry = agent_registry
        self.selector = ProactiveAgentSelector(agent_registry)
        self.aggressive = aggressive

        # Event monitoring
        self.event_triggers = self._build_event_triggers()

        logger.info(f"Proactive invocation manager initialized (aggressive={aggressive})")

    def _build_event_triggers(self) -> Dict[str, List[str]]:
        """Build event-based triggers for automatic agent invocation"""
        return {
            "file_saved": ["linter", "optimizer"],
            "test_failed": ["debugger", "testbed"],
            "build_failed": ["debugger", "constructor"],
            "commit_attempted": ["linter", "auditor", "security"],
            "pr_created": ["auditor", "linter", "security"],
            "security_alert": ["security", "bastion"],
            "performance_degradation": ["optimizer", "npu"],
            "error_logged": ["debugger", "monitor"],
        }

    async def process_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user message and determine agent invocations

        Returns:
            Dict with:
                - recommendations: List of agent recommendations
                - auto_invoke: List of agents to auto-invoke
                - suggestions: List of agent suggestions
        """
        # Select agents
        recommendations = self.selector.select_agents(
            message,
            context,
            aggressive=self.aggressive
        )

        # Split into auto-invoke and suggestions
        auto_invoke = [r for r in recommendations if r.auto_invoke]
        suggestions = [r for r in recommendations if not r.auto_invoke]

        result = {
            "recommendations": recommendations,
            "auto_invoke": auto_invoke,
            "suggestions": suggestions,
            "message": self._generate_message(auto_invoke, suggestions)
        }

        logger.info(
            f"Processed message: {len(auto_invoke)} auto-invoke, "
            f"{len(suggestions)} suggestions"
        )

        return result

    def _generate_message(
        self,
        auto_invoke: List[AgentInvocationRecommendation],
        suggestions: List[AgentInvocationRecommendation]
    ) -> str:
        """Generate user-facing message about agent invocations"""
        parts = []

        if auto_invoke:
            agents_list = ", ".join([r.agent_name for r in auto_invoke[:3]])
            if len(auto_invoke) > 3:
                agents_list += f" and {len(auto_invoke) - 3} more"
            parts.append(f"🤖 Automatically invoking: {agents_list}")

        if suggestions and len(suggestions) <= 3:
            for s in suggestions:
                parts.append(
                    f"💡 Suggested: {s.agent_name} "
                    f"(confidence: {s.confidence:.0%}, reason: {s.reason})"
                )
        elif suggestions:
            parts.append(f"💡 {len(suggestions)} additional agents available")

        return "\n".join(parts) if parts else ""

    async def handle_event(
        self,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Handle events and return agents to invoke

        Args:
            event_type: Type of event (e.g., "file_saved", "test_failed")
            event_data: Additional event data

        Returns:
            List of agent names to invoke
        """
        agents = self.event_triggers.get(event_type, [])

        if agents:
            logger.info(f"Event '{event_type}' triggered agents: {agents}")

        return agents

    def update_success_rate(self, agent_name: str, success: bool):
        """Update agent success rate based on invocation outcome"""
        self.selector.record_invocation(agent_name, success)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================


# Global instance for easy access
_global_manager: Optional[ProactiveInvocationManager] = None


def get_proactive_manager(aggressive: bool = True) -> ProactiveInvocationManager:
    """Get or create global proactive invocation manager"""
    global _global_manager
    if _global_manager is None:
        _global_manager = ProactiveInvocationManager(aggressive=aggressive)
    return _global_manager


# ============================================================================
# CLI FOR TESTING
# ============================================================================


async def main():
    """Test the proactive invocation system"""
    manager = get_proactive_manager(aggressive=True)

    test_messages = [
        "Can you debug this error I'm seeing?",
        "Let's add a new authentication feature",
        "Run a security audit on the codebase",
        "The code is running too slow, can you optimize it?",
        "Deploy this to production",
        "Write tests for the user service",
        "Refactor the database layer",
        "Create a Docker container for this app",
    ]

    for msg in test_messages:
        print(f"\n{'='*60}")
        print(f"Message: {msg}")
        print(f"{'='*60}")

        result = await manager.process_message(msg)
        print(result["message"])

        if result["auto_invoke"]:
            print("\nAuto-invoke agents:")
            for r in result["auto_invoke"]:
                print(f"  - {r.agent_name} (confidence: {r.confidence:.0%})")

        if result["suggestions"]:
            print("\nSuggested agents:")
            for r in result["suggestions"]:
                print(f"  - {r.agent_name} (confidence: {r.confidence:.0%})")


if __name__ == "__main__":
    asyncio.run(main())
