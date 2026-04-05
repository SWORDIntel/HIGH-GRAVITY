#!/usr/bin/env python3
"""
Lightweight Dynamic Think Mode Selection System
Claude Code Integration - No External Dependencies

Self-contained think mode selection system that works without numpy or OpenVINO,
providing intelligent think mode decisions based on task complexity analysis.

Multi-Agent Coordination:
- COORDINATOR: System integration and orchestration
- DIRECTOR: Strategic planning and decision architecture
- PROJECTORCHESTRATOR: Tactical implementation coordination
- PYTHON-INTERNAL: Python execution and hooks system
- NPU: Neural processing (when available, CPU fallback otherwise)

Copyright (C) 2025 Claude-Backups Framework
License: MIT
"""

import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ThinkModeDecision(Enum):
    """Think mode decision options"""

    NO_THINKING = "no_thinking"
    INTERLEAVED = "interleaved"
    AUTO = "auto"


class TaskComplexity(Enum):
    """Task complexity levels"""

    TRIVIAL = 1
    SIMPLE = 2
    MODERATE = 3
    COMPLEX = 4
    ULTRACOMPLEX = 5


@dataclass
class ThinkModeAnalysis:
    """Think mode analysis result"""

    decision: ThinkModeDecision
    complexity_score: float
    confidence: float
    reasoning: str
    processing_time_ms: float
    agent_recommendations: List[str] = field(default_factory=list)


class LightweightComplexityAnalyzer:
    """Lightweight complexity analysis without external dependencies"""

    def __init__(self):
        self.complexity_patterns = {
            "technical_terms": [
                r"\\b(algorithm|implementation|architecture|system|framework)\\b",
                r"\\b(integration|coordination|optimization|performance)\\b",
                r"\\b(security|compliance|validation|testing)\\b",
                r"\\b(database|API|protocol|interface|driver)\\b",
            ],
            "multi_step": [
                r"\\b(first|then|next|after|finally)\\b",
                r"\\b(step \\d+|phase \\d+|part \\d+)\\b",
                r"\\b(multiple|several|various|different)\\b",
            ],
            "agent_coordination": [
                r"\\b(agent|coordinate|orchestrate|collaborate)\\b",
                r"\\b(multi-agent|agent coordination|parallel|concurrent)\\b",
            ],
            "complexity_indicators": [
                r"\\b(complex|complicated|difficult|challenging)\\b",
                r"\\b(design|plan|strategy|analysis|evaluation)\\b",
                r"\\b(comprehensive|detailed|thorough|extensive)\\b",
            ],
        }

    def analyze_task_complexity(self, task_text: str) -> float:
        """Analyze task complexity using pattern matching"""
        text_lower = task_text.lower()
        complexity_score = 0.0

        # Base complexity from text length
        word_count = len(task_text.split())
        if word_count > 200:
            complexity_score += 0.4
        elif word_count > 100:
            complexity_score += 0.3
        elif word_count > 50:
            complexity_score += 0.2
        elif word_count > 20:
            complexity_score += 0.1

        # Pattern-based complexity analysis
        for category, patterns in self.complexity_patterns.items():
            matches = 0
            for pattern in patterns:
                matches += len(re.findall(pattern, text_lower))

            # Weight different categories
            if category == "technical_terms":
                complexity_score += min(matches * 0.05, 0.3)
            elif category == "multi_step":
                complexity_score += min(matches * 0.1, 0.25)
            elif category == "agent_coordination":
                complexity_score += min(matches * 0.15, 0.3)
            elif category == "complexity_indicators":
                complexity_score += min(matches * 0.08, 0.2)

        # Question complexity
        question_count = task_text.count("?")
        if question_count > 3:
            complexity_score += 0.2
        elif question_count > 1:
            complexity_score += 0.1

        return min(complexity_score, 1.0)


class LightweightThinkModeSelector:
    """Lightweight think mode selector with no external dependencies"""

    def __init__(self):
        self.logger = self._setup_logging()
        self.analyzer = LightweightComplexityAnalyzer()
        self.config = {
            "complexity_threshold": 0.5,
            "min_word_count_for_thinking": 10,  # Lowered from 30 to 10
            "cache_enabled": True,
            "cache_ttl_seconds": 300,
        }
        self.decision_cache = {}

    def _setup_logging(self) -> logging.Logger:
        """Setup basic logging"""
        logger = logging.getLogger("LightweightThinkMode")
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def analyze_and_decide(self, task_text: str) -> ThinkModeAnalysis:
        """Analyze task and decide on think mode"""
        start_time = time.time()

        # Quick bypass for very short tasks
        if len(task_text.split()) < self.config["min_word_count_for_thinking"]:
            return ThinkModeAnalysis(
                decision=ThinkModeDecision.NO_THINKING,
                complexity_score=0.1,
                confidence=0.9,
                reasoning="Task too short for thinking mode",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        # Analyze complexity
        complexity_score = self.analyzer.analyze_task_complexity(task_text)

        # Determine decision
        if complexity_score >= self.config["complexity_threshold"]:
            decision = ThinkModeDecision.INTERLEAVED
            confidence = min(complexity_score * 1.2, 1.0)
            reasoning = (
                f"High complexity ({complexity_score:.3f}) requires thinking mode"
            )
        else:
            decision = ThinkModeDecision.NO_THINKING
            confidence = 1.0 - complexity_score
            reasoning = (
                f"Low complexity ({complexity_score:.3f}) - direct response sufficient"
            )

        # Agent recommendations
        agent_recommendations = self._get_agent_recommendations(task_text)
        if agent_recommendations:
            decision = ThinkModeDecision.INTERLEAVED
            reasoning += (
                f" + Multi-agent coordination: {', '.join(agent_recommendations[:3])}"
            )

        processing_time = (time.time() - start_time) * 1000

        return ThinkModeAnalysis(
            decision=decision,
            complexity_score=complexity_score,
            confidence=confidence,
            reasoning=reasoning,
            processing_time_ms=processing_time,
            agent_recommendations=agent_recommendations,
        )

    def _get_agent_recommendations(self, task_text: str) -> List[str]:
        """Get agent recommendations based on task content"""
        text_lower = task_text.lower()
        recommendations = []

        agent_patterns = {
            "security": ["security", "vulnerability", "audit", "compliance"],
            "architecture": ["design", "architecture", "system", "framework"],
            "performance": ["optimize", "performance", "speed", "latency"],
            "documentation": ["document", "guide", "manual", "help"],
            "testing": ["test", "validate", "verify", "quality"],
            "deployment": ["deploy", "install", "configure", "setup"],
        }

        for agent, keywords in agent_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                recommendations.append(agent)

        return recommendations[:5]

    def create_claude_hook_output(self, task_text: str) -> Dict[str, Any]:
        """Create Claude Code compatible hook output"""
        analysis = self.analyze_and_decide(task_text)

        return {
            "think_mode": analysis.decision.value,
            "complexity_score": analysis.complexity_score,
            "confidence": analysis.confidence,
            "reasoning": analysis.reasoning,
            "processing_time_ms": analysis.processing_time_ms,
            "agent_recommendations": analysis.agent_recommendations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": "lightweight_think_mode_selector",
            "version": "1.0.0",
        }


def main():
    """Test execution with sample tasks"""
    print("=" * 80)
    print("Lightweight Dynamic Think Mode Selection System")
    print("Claude Code Integration - No External Dependencies")
    print("=" * 80)

    selector = LightweightThinkModeSelector()

    # Test cases
    test_cases = [
        "What is 2 + 2?",
        "Help me debug this Python function.",
        "Design a comprehensive microservices architecture with security, performance monitoring, and multi-agent coordination for a banking system.",
        "Create documentation for the API.",
        "Coordinate multiple agents to implement a complex distributed system with real-time monitoring, security hardening, and cross-platform deployment.",
    ]

    print("\\n📊 Testing Think Mode Decisions:")
    print("-" * 60)

    for i, task in enumerate(test_cases, 1):
        print(f"\\n{i}. Task: {task}")

        analysis = selector.analyze_and_decide(task)

        print(f"   ✅ Decision: {analysis.decision.value}")
        print(f"   📊 Complexity: {analysis.complexity_score:.3f}")
        print(f"   🎯 Confidence: {analysis.confidence:.3f}")
        print(f"   ⏱️ Time: {analysis.processing_time_ms:.1f}ms")
        print(f"   🔍 Reasoning: {analysis.reasoning}")
        if analysis.agent_recommendations:
            print(f"   🤖 Agents: {', '.join(analysis.agent_recommendations)}")

    print(f"\\n🔗 Claude Code Hook Output Test:")
    hook_output = selector.create_claude_hook_output(test_cases[2])
    print(json.dumps(hook_output, indent=2))

    print(f"\\n✅ Lightweight Think Mode Selection System: OPERATIONAL")
    print(f"🚀 Ready for Claude Code integration without external dependencies")


if __name__ == "__main__":
    main()
