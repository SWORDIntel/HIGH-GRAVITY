#!/usr/bin/env python3
"""
Enhanced Learning Orchestrator Bridge
Advanced integration of learning system with production orchestrator
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

# Import existing components
try:
    from postgresql_learning_system import (
        AgentTaskExecution,
        UltimatePostgreSQLLearningSystem,
    )
    from production_orchestrator import (
        CommandSet,
        CommandStep,
        ExecutionMode,
        ProductionOrchestrator,
    )

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Import warning: {e}")
    IMPORTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class LearningStrategy(Enum):
    """Learning strategy types"""

    CONSERVATIVE = "conservative"  # Prefer proven patterns
    BALANCED = "balanced"  # Balance exploration and exploitation
    EXPERIMENTAL = "experimental"  # Actively explore new patterns
    ADAPTIVE = "adaptive"  # Dynamically adjust based on performance


@dataclass
class ExecutionContext:
    """Enhanced context for task execution"""

    task_id: str
    task_type: str
    description: str
    complexity: float
    priority: int = 1
    deadline: Optional[datetime] = None
    user_context: Dict[str, Any] = field(default_factory=dict)
    parent_task_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningMetrics:
    """Comprehensive learning metrics"""

    success_rate: float
    avg_duration: float
    error_rate: float
    agent_efficiency: Dict[str, float]
    pattern_confidence: float
    adaptation_rate: float
    exploration_rate: float
    model_accuracy: float
    insight_quality: float
    resource_utilization: float


@dataclass
class AgentCapability:
    """Agent capability profile"""

    agent_name: str
    task_types: Set[str]
    success_rate: float
    avg_duration: float
    complexity_range: Tuple[float, float]
    specializations: List[str]
    collaboration_scores: Dict[str, float]  # Scores with other agents
    resource_requirements: Dict[str, float]
    last_updated: datetime


class PatternRecognizer:
    """Advanced pattern recognition for task executions"""

    def __init__(self):
        self.pattern_cache = {}
        self.sequence_patterns = defaultdict(list)
        self.failure_patterns = defaultdict(list)
        self.success_patterns = defaultdict(list)

    def analyze_sequence(self, executions: List[AgentTaskExecution]) -> Dict[str, Any]:
        """Analyze execution sequences for patterns"""
        patterns = {
            "common_sequences": [],
            "failure_indicators": [],
            "success_indicators": [],
            "optimization_opportunities": [],
        }

        # Analyze agent sequences
        for i in range(len(executions) - 2):
            sequence = tuple(executions[i : i + 3])
            sequence_key = self._get_sequence_key(sequence)

            if sequence[-1].success:
                self.success_patterns[sequence_key].append(sequence)
            else:
                self.failure_patterns[sequence_key].append(sequence)

        # Identify common successful patterns
        for key, sequences in self.success_patterns.items():
            if len(sequences) >= 3:  # Minimum occurrences
                success_rate = self._calculate_sequence_success_rate(sequences)
                if success_rate > 0.8:
                    patterns["common_sequences"].append(
                        {
                            "pattern": key,
                            "success_rate": success_rate,
                            "occurrences": len(sequences),
                        }
                    )

        # Identify failure indicators
        for key, sequences in self.failure_patterns.items():
            if len(sequences) >= 2:
                patterns["failure_indicators"].append(
                    {
                        "pattern": key,
                        "failure_rate": len(sequences)
                        / (len(sequences) + len(self.success_patterns.get(key, []))),
                    }
                )

        return patterns

    def _get_sequence_key(self, sequence: Tuple[AgentTaskExecution, ...]) -> str:
        """Generate unique key for execution sequence"""
        agents = [exec.agents_used for exec in sequence]
        task_types = [exec.task_type for exec in sequence]
        return f"{agents}_{task_types}"

    def _calculate_sequence_success_rate(self, sequences: List) -> float:
        """Calculate success rate for sequence pattern"""
        if not sequences:
            return 0.0
        successes = sum(1 for seq in sequences if seq[-1].success)
        return successes / len(sequences)


class AdaptiveLearningEngine:
    """Advanced learning engine with multiple strategies"""

    def __init__(self, strategy: LearningStrategy = LearningStrategy.ADAPTIVE):
        self.strategy = strategy
        self.performance_history = deque(maxlen=100)
        self.exploration_budget = 0.2  # 20% exploration by default
        self.exploitation_threshold = 0.85
        self.learning_rate = 0.1
        self.pattern_recognizer = PatternRecognizer()

    def select_agents(
        self,
        context: ExecutionContext,
        capabilities: List[AgentCapability],
        historical_data: List[AgentTaskExecution],
    ) -> List[str]:
        """Select optimal agents based on learning strategy"""

        if self.strategy == LearningStrategy.CONSERVATIVE:
            return self._conservative_selection(context, capabilities, historical_data)
        elif self.strategy == LearningStrategy.EXPERIMENTAL:
            return self._experimental_selection(context, capabilities, historical_data)
        elif self.strategy == LearningStrategy.BALANCED:
            return self._balanced_selection(context, capabilities, historical_data)
        else:  # ADAPTIVE
            return self._adaptive_selection(context, capabilities, historical_data)

    def _conservative_selection(
        self,
        context: ExecutionContext,
        capabilities: List[AgentCapability],
        historical_data: List[AgentTaskExecution],
    ) -> List[str]:
        """Select agents using proven patterns only"""
        suitable_agents = []

        for cap in capabilities:
            if (
                context.task_type in cap.task_types
                and cap.success_rate > 0.9
                and cap.complexity_range[0]
                <= context.complexity
                <= cap.complexity_range[1]
            ):
                suitable_agents.append((cap.agent_name, cap.success_rate))

        # Sort by success rate and return top agents
        suitable_agents.sort(key=lambda x: x[1], reverse=True)
        return [agent[0] for agent in suitable_agents[:3]]

    def _experimental_selection(
        self,
        context: ExecutionContext,
        capabilities: List[AgentCapability],
        historical_data: List[AgentTaskExecution],
    ) -> List[str]:
        """Actively explore new agent combinations"""
        import random

        # Get all potentially suitable agents
        potential_agents = [
            cap.agent_name
            for cap in capabilities
            if context.task_type in cap.task_types
            or context.complexity >= cap.complexity_range[0]
        ]

        # Mix proven and new combinations
        if random.random() < self.exploration_budget and len(potential_agents) > 3:
            # Explore new combination
            return random.sample(potential_agents, min(3, len(potential_agents)))
        else:
            # Use best known combination with variation
            return self._conservative_selection(context, capabilities, historical_data)

    def _balanced_selection(
        self,
        context: ExecutionContext,
        capabilities: List[AgentCapability],
        historical_data: List[AgentTaskExecution],
    ) -> List[str]:
        """Balance between exploration and exploitation"""
        import random

        # Calculate exploration probability based on recent performance
        recent_success_rate = self._calculate_recent_success_rate()

        if recent_success_rate < 0.7:  # Performance is poor, explore more
            explore_prob = 0.4
        elif recent_success_rate > 0.9:  # Performance is good, exploit more
            explore_prob = 0.1
        else:
            explore_prob = 0.2

        if random.random() < explore_prob:
            return self._experimental_selection(context, capabilities, historical_data)
        else:
            return self._conservative_selection(context, capabilities, historical_data)

    def _adaptive_selection(
        self,
        context: ExecutionContext,
        capabilities: List[AgentCapability],
        historical_data: List[AgentTaskExecution],
    ) -> List[str]:
        """Dynamically adapt strategy based on context and performance"""

        # Analyze recent patterns
        patterns = self.pattern_recognizer.analyze_sequence(historical_data[-10:])

        # Check if we have high-confidence patterns for this task type
        matching_patterns = [
            p
            for p in patterns["common_sequences"]
            if context.task_type in str(p["pattern"])
        ]

        if matching_patterns and matching_patterns[0]["success_rate"] > 0.9:
            # Use proven pattern
            return self._extract_agents_from_pattern(matching_patterns[0]["pattern"])

        # Check task urgency
        if context.priority > 3 or (
            context.deadline and context.deadline - datetime.now() < timedelta(hours=1)
        ):
            # High priority/urgent - use conservative approach
            return self._conservative_selection(context, capabilities, historical_data)

        # Default to balanced approach
        return self._balanced_selection(context, capabilities, historical_data)

    def _calculate_recent_success_rate(self) -> float:
        """Calculate recent success rate from performance history"""
        if not self.performance_history:
            return 0.5  # Default neutral rate

        recent = list(self.performance_history)[-20:]
        successes = sum(1 for p in recent if p.get("success", False))
        return successes / len(recent) if recent else 0.5

    def _extract_agents_from_pattern(self, pattern: str) -> List[str]:
        """Extract agent names from pattern string"""
        # This is a simplified extraction - implement based on actual pattern format
        import re

        agents = re.findall(r"'(\w+)'", pattern)
        return agents[:3] if agents else []

    def update_strategy(self, metrics: LearningMetrics):
        """Update learning strategy based on performance metrics"""
        if self.strategy != LearningStrategy.ADAPTIVE:
            return

        # Dynamically adjust exploration budget
        if metrics.success_rate < 0.6:
            self.exploration_budget = min(0.4, self.exploration_budget + 0.05)
        elif metrics.success_rate > 0.85:
            self.exploration_budget = max(0.1, self.exploration_budget - 0.02)

        # Adjust learning rate based on adaptation rate
        if metrics.adaptation_rate > 0.8:
            self.learning_rate = min(0.3, self.learning_rate * 1.1)
        elif metrics.adaptation_rate < 0.3:
            self.learning_rate = max(0.05, self.learning_rate * 0.9)


class EnhancedLearningOrchestrator:
    """Enhanced orchestrator with advanced learning capabilities"""

    def __init__(self, learning_strategy: LearningStrategy = LearningStrategy.ADAPTIVE):
        if IMPORTS_AVAILABLE:
            self.production_orchestrator = ProductionOrchestrator()
            self.learning_system = UltimatePostgreSQLLearningSystem()
        else:
            self.production_orchestrator = None
            self.learning_system = None

        self.learning_engine = AdaptiveLearningEngine(learning_strategy)
        self.agent_capabilities = {}  # Cache of agent capabilities
        self.execution_cache = {}  # Cache recent execution results
        self.learning_enabled = True
        self.adaptation_threshold = 0.8
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()

        # Performance tracking
        self.performance_window = deque(maxlen=50)
        self.insight_buffer = deque(maxlen=100)

    async def initialize(self):
        """Initialize orchestrator components"""
        if self.production_orchestrator:
            await self.production_orchestrator.initialize()

        # Load agent capabilities
        await self._load_agent_capabilities()

        # Train initial models if we have data
        if self.learning_system and len(self.learning_system.execution_history) > 50:
            await self._async_train_models()

    async def execute_with_learning(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute task with advanced learning enhancement"""

        start_time = time.time()
        execution_id = self._generate_execution_id(context)

        # Check cache for similar recent executions
        cached_result = self._check_execution_cache(context)
        if cached_result:
            logger.info(f"Using cached result for similar execution: {execution_id}")
            return cached_result

        # Get agent recommendations from learning engine
        recommended_agents = await self._get_intelligent_recommendations(context)

        # Create optimized command set
        command_set = await self._create_adaptive_command_set(
            context, recommended_agents
        )

        # Execute with monitoring
        result = await self._execute_with_monitoring(command_set, context)

        # Record and learn from execution
        await self._record_and_learn(context, result, recommended_agents, start_time)

        # Cache successful results
        if result.get("success"):
            self._update_execution_cache(context, result)

        # Check for alerts
        await self._check_alerts(result, context)

        return result

    async def _get_intelligent_recommendations(
        self, context: ExecutionContext
    ) -> List[str]:
        """Get intelligent agent recommendations"""

        recommended_agents = []

        if self.learning_system and self.learning_enabled:
            # Get ML-based recommendations
            ml_agents = self.learning_system.predict_optimal_agents(
                context.task_type, context.complexity
            )

            # Get pattern-based recommendations
            historical_data = self.learning_system.execution_history[-50:]
            pattern_agents = self.learning_engine.select_agents(
                context, list(self.agent_capabilities.values()), historical_data
            )

            # Combine recommendations with weights
            agent_scores = defaultdict(float)
            for agent in ml_agents:
                agent_scores[agent] += 0.6  # ML weight
            for agent in pattern_agents:
                agent_scores[agent] += 0.4  # Pattern weight

            # Sort by score and return top agents
            sorted_agents = sorted(
                agent_scores.items(), key=lambda x: x[1], reverse=True
            )
            recommended_agents = [agent for agent, _ in sorted_agents[:4]]

            logger.info(
                f"Intelligent recommendations for {context.task_type}: {recommended_agents}"
            )

        return recommended_agents

    async def _create_adaptive_command_set(
        self, context: ExecutionContext, recommended_agents: List[str]
    ) -> CommandSet:
        """Create adaptive command set based on context and learning"""

        steps = []

        if recommended_agents:
            # Build steps from recommendations with context-aware parameters
            for i, agent in enumerate(recommended_agents):
                step_params = self._generate_step_parameters(agent, context, i)
                steps.append(
                    CommandStep(
                        agent=agent.lower(),
                        action=self._determine_agent_action(agent, context),
                        parameters=step_params,
                        timeout=self._calculate_step_timeout(agent, context),
                        retry_count=self._determine_retry_count(context.priority),
                    )
                )
        else:
            # Fallback to template-based approach
            steps = await self._get_template_steps(context.task_type)

        # Optimize execution mode
        mode = self._optimize_execution_mode(context)

        # Add orchestration metadata
        metadata = {
            "learning_enhanced": True,
            "recommended_agents": recommended_agents,
            "context_id": context.task_id,
            "strategy": self.learning_engine.strategy.value,
            "confidence": self._calculate_recommendation_confidence(recommended_agents),
        }

        return CommandSet(
            name=f"adaptive_{context.task_type}_{execution_id[:8]}",
            description=context.description,
            mode=mode,
            steps=steps,
            metadata=metadata,
            max_parallel=self._determine_parallelism(context, steps),
            timeout=self._calculate_total_timeout(context, steps),
        )

    def _generate_step_parameters(
        self, agent: str, context: ExecutionContext, step_index: int
    ) -> Dict[str, Any]:
        """Generate context-aware parameters for agent step"""

        base_params = {
            "description": context.description,
            "task_type": context.task_type,
            "complexity": context.complexity,
            "step_index": step_index,
        }

        # Add agent-specific parameters
        if agent.upper() in self.agent_capabilities:
            cap = self.agent_capabilities[agent.upper()]

            # Add specialization hints
            if cap.specializations:
                base_params["specializations"] = cap.specializations

            # Add resource constraints
            if context.constraints.get("resources"):
                base_params["resource_limits"] = {
                    k: v * cap.resource_requirements.get(k, 1.0)
                    for k, v in context.constraints["resources"].items()
                }

        # Add context-specific parameters
        if context.user_context:
            base_params["user_context"] = context.user_context

        if context.parent_task_id:
            base_params["parent_task"] = context.parent_task_id

        return base_params

    def _determine_agent_action(self, agent: str, context: ExecutionContext) -> str:
        """Determine appropriate action for agent based on context"""

        action_mapping = {
            "ARCHITECT": {
                "web_development": "design_system",
                "api_design": "design_api",
                "system_design": "architect_solution",
                "default": "analyze_requirements",
            },
            "SECURITY": {
                "security_audit": "full_security_scan",
                "penetration_test": "penetration_test",
                "compliance_check": "compliance_audit",
                "default": "security_review",
            },
            "TESTBED": {
                "unit_test": "run_unit_tests",
                "integration_test": "run_integration_tests",
                "performance_test": "run_performance_tests",
                "default": "validate_functionality",
            },
        }

        agent_upper = agent.upper()
        if agent_upper in action_mapping:
            return action_mapping[agent_upper].get(
                context.task_type, action_mapping[agent_upper]["default"]
            )

        return "execute_task"

    def _calculate_step_timeout(self, agent: str, context: ExecutionContext) -> int:
        """Calculate appropriate timeout for agent step"""

        base_timeout = 30  # seconds

        # Adjust based on complexity
        complexity_factor = 1 + (context.complexity - 1) * 0.5

        # Adjust based on agent type
        agent_timeouts = {
            "TESTBED": 60,
            "SECURITY": 90,
            "ARCHITECT": 45,
            "CONSTRUCTOR": 60,
        }

        agent_timeout = agent_timeouts.get(agent.upper(), base_timeout)

        return int(agent_timeout * complexity_factor)

    def _determine_retry_count(self, priority: int) -> int:
        """Determine retry count based on priority"""
        if priority >= 4:
            return 3  # High priority - more retries
        elif priority >= 2:
            return 2  # Medium priority
        else:
            return 1  # Low priority

    def _optimize_execution_mode(self, context: ExecutionContext) -> ExecutionMode:
        """Optimize execution mode based on context and learning"""

        # Priority-based optimization
        if context.priority >= 4:
            return ExecutionMode.REDUNDANT  # Maximum reliability

        # Deadline-based optimization
        if context.deadline:
            time_remaining = (context.deadline - datetime.now()).total_seconds()
            if time_remaining < 300:  # Less than 5 minutes
                return ExecutionMode.SPEED_CRITICAL

        # Task type optimization
        mode_mapping = {
            "security_audit": ExecutionMode.REDUNDANT,
            "deployment": ExecutionMode.CONSENSUS,
            "quick_fix": ExecutionMode.SPEED_CRITICAL,
            "research": ExecutionMode.PYTHON_ONLY,
            "web_development": ExecutionMode.INTELLIGENT,
            "data_analysis": ExecutionMode.PYTHON_ONLY,
        }

        return mode_mapping.get(context.task_type, ExecutionMode.INTELLIGENT)

    def _calculate_recommendation_confidence(self, agents: List[str]) -> float:
        """Calculate confidence in agent recommendations"""
        if not agents:
            return 0.0

        confidence_scores = []
        for agent in agents:
            if agent.upper() in self.agent_capabilities:
                cap = self.agent_capabilities[agent.upper()]
                confidence_scores.append(cap.success_rate)

        return (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.5
        )

    def _determine_parallelism(
        self, context: ExecutionContext, steps: List[CommandStep]
    ) -> int:
        """Determine maximum parallelism for execution"""

        # Check for dependencies
        if context.dependencies:
            return 1  # Sequential execution for dependent tasks

        # Check agent compatibility for parallel execution
        parallel_compatible = True
        for i, step in enumerate(steps[:-1]):
            for j, other_step in enumerate(steps[i + 1 :], i + 1):
                if not self._agents_compatible_parallel(step.agent, other_step.agent):
                    parallel_compatible = False
                    break

        if not parallel_compatible:
            return 1

        # Determine based on resource constraints
        if context.constraints.get("max_parallel"):
            return min(len(steps), context.constraints["max_parallel"])

        return min(len(steps), 3)  # Default max parallel

    def _agents_compatible_parallel(self, agent1: str, agent2: str) -> bool:
        """Check if two agents can run in parallel"""

        # Define incompatible pairs
        incompatible_pairs = [
            ("TESTBED", "CONSTRUCTOR"),  # Testing while building
            ("SECURITY", "DEPLOYMENT"),  # Security check during deployment
        ]

        for pair in incompatible_pairs:
            if agent1.upper() in pair and agent2.upper() in pair:
                return False

        return True

    def _calculate_total_timeout(
        self, context: ExecutionContext, steps: List[CommandStep]
    ) -> int:
        """Calculate total timeout for command set"""

        step_timeouts = [step.timeout for step in steps if hasattr(step, "timeout")]

        if self._determine_parallelism(context, steps) > 1:
            # Parallel execution - use max timeout plus buffer
            return max(step_timeouts) + 30 if step_timeouts else 300
        else:
            # Sequential execution - sum of timeouts plus buffer
            return sum(step_timeouts) + 60 if step_timeouts else 600

    async def _execute_with_monitoring(
        self, command_set: CommandSet, context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute command set with comprehensive monitoring"""

        monitoring_task = asyncio.create_task(
            self._monitor_execution(command_set, context)
        )

        try:
            if self.production_orchestrator:
                result = await self.production_orchestrator.execute_command_set(
                    command_set
                )
            else:
                result = await self._fallback_execution(command_set)

            # Add monitoring data to result
            monitoring_data = await monitoring_task
            result["monitoring"] = monitoring_data

            return result

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            monitoring_task.cancel()
            return {
                "success": False,
                "error": str(e),
                "command_set": command_set.name,
                "context": context.task_id,
            }

    async def _monitor_execution(
        self, command_set: CommandSet, context: ExecutionContext
    ) -> Dict[str, Any]:
        """Monitor execution progress and collect metrics"""

        monitoring_data = {
            "start_time": time.time(),
            "checkpoints": [],
            "resource_usage": [],
            "warnings": [],
        }

        while True:
            await asyncio.sleep(5)  # Check every 5 seconds

            # Collect metrics
            checkpoint = {
                "timestamp": time.time(),
                "memory_usage": self._get_memory_usage(),
                "active_agents": self._get_active_agents(),
            }

            monitoring_data["checkpoints"].append(checkpoint)

            # Check for issues
            if checkpoint["memory_usage"] > 0.9:  # 90% memory usage
                monitoring_data["warnings"].append(
                    {
                        "type": "high_memory",
                        "value": checkpoint["memory_usage"],
                        "timestamp": checkpoint["timestamp"],
                    }
                )

        monitoring_data["end_time"] = time.time()
        monitoring_data["total_duration"] = (
            monitoring_data["end_time"] - monitoring_data["start_time"]
        )

        return monitoring_data

    def _get_memory_usage(self) -> float:
        """Get current memory usage (simplified)"""
        # This is a placeholder - implement actual memory monitoring
        import random

        return random.uniform(0.3, 0.7)

    def _get_active_agents(self) -> List[str]:
        """Get list of currently active agents"""
        # This is a placeholder - implement actual agent monitoring
        return []

    async def _record_and_learn(
        self,
        context: ExecutionContext,
        result: Dict[str, Any],
        recommended_agents: List[str],
        start_time: float,
    ):
        """Record execution and trigger learning"""

        duration = time.time() - start_time
        success = result.get("success", False)

        # Record execution
        if self.learning_system:
            execution = AgentTaskExecution(
                task_id=context.task_id,
                task_type=context.task_type,
                agents_used=recommended_agents,
                execution_order=recommended_agents,
                duration=duration,
                success=success,
                error_message=result.get("error"),
                complexity_score=context.complexity,
                metadata={
                    "priority": context.priority,
                    "strategy": self.learning_engine.strategy.value,
                    "monitoring": result.get("monitoring", {}),
                },
            )

            self.learning_system.record_execution(execution)

        # Update performance tracking
        self.performance_window.append(
            {
                "success": success,
                "duration": duration,
                "complexity": context.complexity,
                "task_type": context.task_type,
            }
        )

        # Update learning engine
        self.learning_engine.performance_history.append(
            {"success": success, "task_type": context.task_type}
        )

        # Trigger async learning if conditions are met
        await self._maybe_trigger_learning()

    async def _maybe_trigger_learning(self):
        """Trigger learning cycle if conditions are met"""

        if not self.learning_system:
            return

        # Check various triggers
        triggers = {
            "execution_count": len(self.learning_system.execution_history) % 10 == 0,
            "failure_spike": self._detect_failure_spike(),
            "performance_degradation": self._detect_performance_degradation(),
            "scheduled": self._is_scheduled_learning_time(),
        }

        if any(triggers.values()):
            logger.info(
                f"Triggering learning cycle: {[k for k, v in triggers.items() if v]}"
            )
            asyncio.create_task(self._run_comprehensive_learning())

    def _detect_failure_spike(self) -> bool:
        """Detect sudden increase in failures"""
        if len(self.performance_window) < 10:
            return False

        recent = list(self.performance_window)[-10:]
        recent_failures = sum(1 for p in recent if not p["success"])

        return recent_failures >= 4  # 40% or more failures

    def _detect_performance_degradation(self) -> bool:
        """Detect gradual performance degradation"""
        if len(self.performance_window) < 20:
            return False

        recent = list(self.performance_window)[-10:]
        older = list(self.performance_window)[-20:-10]

        recent_success = sum(1 for p in recent if p["success"]) / 10
        older_success = sum(1 for p in older if p["success"]) / 10

        return recent_success < older_success - 0.2  # 20% degradation

    def _is_scheduled_learning_time(self) -> bool:
        """Check if it's time for scheduled learning"""
        # Run learning at specific intervals (e.g., every hour)
        current_minute = datetime.now().minute
        return current_minute == 0  # Run at the top of each hour

    async def _run_comprehensive_learning(self):
        """Run comprehensive learning cycle"""
        try:
            logger.info("Starting comprehensive learning cycle...")

            # Update agent capabilities
            await self._update_agent_capabilities()

            # Analyze patterns
            if self.learning_system:
                insights = self.learning_system.analyze_patterns()

                # Store high-quality insights
                for insight in insights:
                    if insight.confidence > 0.7:
                        self.insight_buffer.append(insight)

                # Retrain models
                if len(self.learning_system.execution_history) % 50 == 0:
                    await self._async_train_models()

            # Calculate and update metrics
            metrics = await self._calculate_learning_metrics()

            # Update learning strategy
            self.learning_engine.update_strategy(metrics)

            # Update adaptation threshold
            await self._update_adaptation_threshold(metrics)

            # Generate report
            await self._generate_learning_report(metrics)

            logger.info("Comprehensive learning cycle completed")

        except Exception as e:
            logger.error(f"Error in learning cycle: {e}")

    async def _update_agent_capabilities(self):
        """Update agent capability profiles based on recent performance"""

        if not self.learning_system:
            return

        # Analyze recent executions per agent
        agent_performance = defaultdict(list)

        for execution in self.learning_system.execution_history[-100:]:
            for agent in execution.agents_used:
                agent_performance[agent].append(
                    {
                        "success": execution.success,
                        "duration": execution.duration,
                        "complexity": execution.complexity_score,
                        "task_type": execution.task_type,
                    }
                )

        # Update capability profiles
        for agent_name, performances in agent_performance.items():
            if len(performances) >= 5:  # Minimum data for update
                capability = self._calculate_agent_capability(agent_name, performances)
                self.agent_capabilities[agent_name] = capability

    def _calculate_agent_capability(
        self, agent_name: str, performances: List[Dict]
    ) -> AgentCapability:
        """Calculate agent capability from performance data"""

        success_rate = sum(1 for p in performances if p["success"]) / len(performances)
        avg_duration = sum(p["duration"] for p in performances) / len(performances)

        task_types = set(p["task_type"] for p in performances)
        complexities = [p["complexity"] for p in performances]

        return AgentCapability(
            agent_name=agent_name,
            task_types=task_types,
            success_rate=success_rate,
            avg_duration=avg_duration,
            complexity_range=(min(complexities), max(complexities)),
            specializations=list(task_types)[:3],  # Top 3 task types
            collaboration_scores={},  # To be calculated separately
            resource_requirements={"cpu": 1.0, "memory": 1.0},  # Default
            last_updated=datetime.now(),
        )

    async def _async_train_models(self):
        """Train models asynchronously"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor, self.learning_system.train_prediction_models
        )

    async def _calculate_learning_metrics(self) -> LearningMetrics:
        """Calculate comprehensive learning metrics"""

        if not self.performance_window:
            return LearningMetrics(
                success_rate=0.0,
                avg_duration=0.0,
                error_rate=0.0,
                agent_efficiency={},
                pattern_confidence=0.0,
                adaptation_rate=0.0,
                exploration_rate=self.learning_engine.exploration_budget,
                model_accuracy=0.0,
                insight_quality=0.0,
                resource_utilization=0.0,
            )

        recent = list(self.performance_window)

        success_rate = sum(1 for p in recent if p["success"]) / len(recent)
        avg_duration = sum(p["duration"] for p in recent) / len(recent)
        error_rate = 1 - success_rate

        # Calculate agent efficiency
        agent_efficiency = {}
        for agent_name, capability in self.agent_capabilities.items():
            agent_efficiency[agent_name] = capability.success_rate

        # Calculate other metrics
        pattern_confidence = self._calculate_pattern_confidence()
        adaptation_rate = self._calculate_adaptation_rate()
        model_accuracy = await self._calculate_model_accuracy()
        insight_quality = self._calculate_insight_quality()
        resource_utilization = self._calculate_resource_utilization()

        return LearningMetrics(
            success_rate=success_rate,
            avg_duration=avg_duration,
            error_rate=error_rate,
            agent_efficiency=agent_efficiency,
            pattern_confidence=pattern_confidence,
            adaptation_rate=adaptation_rate,
            exploration_rate=self.learning_engine.exploration_budget,
            model_accuracy=model_accuracy,
            insight_quality=insight_quality,
            resource_utilization=resource_utilization,
        )

    def _calculate_pattern_confidence(self) -> float:
        """Calculate confidence in recognized patterns"""
        if not self.insight_buffer:
            return 0.0

        confidences = [insight.confidence for insight in self.insight_buffer]
        return sum(confidences) / len(confidences)

    def _calculate_adaptation_rate(self) -> float:
        """Calculate how quickly system adapts to changes"""
        # Simplified calculation - implement based on actual adaptation metrics
        return 0.7

    async def _calculate_model_accuracy(self) -> float:
        """Calculate model prediction accuracy"""
        # Simplified calculation - implement based on actual model performance
        return 0.85

    def _calculate_insight_quality(self) -> float:
        """Calculate quality of generated insights"""
        if not self.insight_buffer:
            return 0.0

        # Quality based on confidence and recency
        quality_scores = []
        current_time = datetime.now()

        for insight in self.insight_buffer:
            age_hours = (current_time - insight.created_at).total_seconds() / 3600
            recency_factor = max(0, 1 - age_hours / 168)  # Decay over a week
            quality_scores.append(insight.confidence * recency_factor)

        return sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    def _calculate_resource_utilization(self) -> float:
        """Calculate average resource utilization"""
        # Simplified calculation - implement based on actual resource metrics
        return 0.65

    async def _update_adaptation_threshold(self, metrics: LearningMetrics):
        """Update adaptation threshold based on metrics"""

        # Adjust threshold based on success rate and pattern confidence
        if metrics.success_rate > 0.85 and metrics.pattern_confidence > 0.8:
            # High success and confidence - lower threshold to use more patterns
            self.adaptation_threshold = max(0.6, self.adaptation_threshold - 0.05)
        elif metrics.success_rate < 0.6:
            # Low success - raise threshold to be more conservative
            self.adaptation_threshold = min(0.95, self.adaptation_threshold + 0.05)

        logger.info(f"Adaptation threshold updated to {self.adaptation_threshold:.2f}")

    async def _generate_learning_report(self, metrics: LearningMetrics):
        """Generate comprehensive learning report"""

        report = {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "success_rate": f"{metrics.success_rate:.1%}",
                "avg_duration": f"{metrics.avg_duration:.1f}s",
                "error_rate": f"{metrics.error_rate:.1%}",
                "pattern_confidence": f"{metrics.pattern_confidence:.1%}",
                "adaptation_rate": f"{metrics.adaptation_rate:.1%}",
                "exploration_rate": f"{metrics.exploration_rate:.1%}",
                "model_accuracy": f"{metrics.model_accuracy:.1%}",
                "insight_quality": f"{metrics.insight_quality:.1%}",
                "resource_utilization": f"{metrics.resource_utilization:.1%}",
            },
            "top_agents": sorted(
                metrics.agent_efficiency.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "recent_insights": [
                {
                    "type": insight.insight_type,
                    "description": insight.description,
                    "confidence": insight.confidence,
                }
                for insight in list(self.insight_buffer)[-5:]
            ],
            "recommendations": self._generate_recommendations(metrics),
        }

        logger.info(f"Learning Report: {json.dumps(report, indent=2)}")

        # Store report for dashboard
        self.latest_report = report

    def _generate_recommendations(self, metrics: LearningMetrics) -> List[str]:
        """Generate actionable recommendations based on metrics"""

        recommendations = []

        if metrics.success_rate < 0.7:
            recommendations.append(
                "Consider increasing exploration rate to find better patterns"
            )

        if metrics.error_rate > 0.3:
            recommendations.append("Review failing tasks for common patterns")

        if metrics.pattern_confidence < 0.6:
            recommendations.append("Collect more data to improve pattern recognition")

        if metrics.resource_utilization > 0.8:
            recommendations.append(
                "Consider scaling resources or optimizing agent efficiency"
            )

        if metrics.exploration_rate < 0.1:
            recommendations.append(
                "Increase exploration to discover new effective patterns"
            )

        return recommendations

    def _generate_execution_id(self, context: ExecutionContext) -> str:
        """Generate unique execution ID"""
        content = f"{context.task_id}_{context.task_type}_{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()

    def _check_execution_cache(
        self, context: ExecutionContext
    ) -> Optional[Dict[str, Any]]:
        """Check if similar execution exists in cache"""

        # Generate cache key based on task characteristics
        cache_key = f"{context.task_type}_{context.complexity:.1f}"

        if cache_key in self.execution_cache:
            cached = self.execution_cache[cache_key]
            # Check if cache is still valid (less than 1 hour old)
            if time.time() - cached["timestamp"] < 3600:
                return cached["result"]

        return None

    def _update_execution_cache(
        self, context: ExecutionContext, result: Dict[str, Any]
    ):
        """Update execution cache with successful result"""

        cache_key = f"{context.task_type}_{context.complexity:.1f}"
        self.execution_cache[cache_key] = {"result": result, "timestamp": time.time()}

        # Limit cache size
        if len(self.execution_cache) > 100:
            # Remove oldest entries
            sorted_items = sorted(
                self.execution_cache.items(), key=lambda x: x[1]["timestamp"]
            )
            for key, _ in sorted_items[:20]:
                del self.execution_cache[key]

    async def _check_alerts(self, result: Dict[str, Any], context: ExecutionContext):
        """Check for alert conditions"""

        if not result.get("success"):
            if context.priority >= 4:
                await self.alert_manager.send_alert(
                    "HIGH_PRIORITY_FAILURE",
                    f"High priority task {context.task_id} failed",
                    {"context": context, "result": result},
                )

        if result.get("monitoring", {}).get("warnings"):
            for warning in result["monitoring"]["warnings"]:
                if warning["type"] == "high_memory":
                    await self.alert_manager.send_alert(
                        "RESOURCE_WARNING",
                        f"High memory usage detected: {warning['value']:.1%}",
                        warning,
                    )

    async def _load_agent_capabilities(self):
        """Load or initialize agent capabilities"""

        # Default capabilities - in production, load from database
        default_capabilities = {
            "ARCHITECT": AgentCapability(
                agent_name="ARCHITECT",
                task_types={"web_development", "api_design", "system_design"},
                success_rate=0.85,
                avg_duration=30.0,
                complexity_range=(1.0, 5.0),
                specializations=["design", "architecture", "planning"],
                collaboration_scores={"CONSTRUCTOR": 0.9, "TESTBED": 0.8},
                resource_requirements={"cpu": 1.0, "memory": 1.5},
                last_updated=datetime.now(),
            ),
            "CONSTRUCTOR": AgentCapability(
                agent_name="CONSTRUCTOR",
                task_types={"web_development", "api_implementation", "database_setup"},
                success_rate=0.82,
                avg_duration=45.0,
                complexity_range=(1.0, 4.0),
                specializations=["implementation", "coding", "building"],
                collaboration_scores={"ARCHITECT": 0.9, "TESTBED": 0.85},
                resource_requirements={"cpu": 1.5, "memory": 2.0},
                last_updated=datetime.now(),
            ),
            "SECURITY": AgentCapability(
                agent_name="SECURITY",
                task_types={"security_audit", "penetration_test", "compliance_check"},
                success_rate=0.90,
                avg_duration=60.0,
                complexity_range=(2.0, 5.0),
                specializations=["security", "audit", "compliance"],
                collaboration_scores={"TESTBED": 0.8, "SECURITYAUDITOR": 0.95},
                resource_requirements={"cpu": 2.0, "memory": 1.5},
                last_updated=datetime.now(),
            ),
            "TESTBED": AgentCapability(
                agent_name="TESTBED",
                task_types={"testing", "validation", "quality_assurance"},
                success_rate=0.88,
                avg_duration=40.0,
                complexity_range=(1.0, 4.0),
                specializations=["testing", "validation", "qa"],
                collaboration_scores={"CONSTRUCTOR": 0.85, "SECURITY": 0.8},
                resource_requirements={"cpu": 1.2, "memory": 1.0},
                last_updated=datetime.now(),
            ),
        }

        self.agent_capabilities = default_capabilities

    async def _fallback_execution(self, command_set: CommandSet) -> Dict[str, Any]:
        """Enhanced fallback execution when production orchestrator is unavailable"""

        logger.info(f"Executing in fallback mode: {command_set.name}")

        results = []
        total_duration = 0

        for step in command_set.steps:
            step_start = time.time()

            # Simulate execution with realistic delays
            await asyncio.sleep(0.5 + step.parameters.get("complexity", 1.0) * 0.3)

            step_duration = time.time() - step_start
            total_duration += step_duration

            results.append(
                {
                    "agent": step.agent,
                    "action": step.action,
                    "status": "completed",
                    "duration": step_duration,
                    "parameters": step.parameters,
                }
            )

        return {
            "success": True,
            "results": results,
            "total_duration": total_duration,
            "mode": "fallback",
            "command_set": command_set.name,
        }

    async def get_enhanced_dashboard(self) -> Dict[str, Any]:
        """Get enhanced learning system dashboard"""

        base_dashboard = {}

        if self.learning_system:
            base_dashboard = self.learning_system.get_learning_summary()

        # Calculate additional metrics
        current_metrics = await self._calculate_learning_metrics()

        dashboard = {
            **base_dashboard,
            "learning_enabled": self.learning_enabled,
            "adaptation_threshold": self.adaptation_threshold,
            "learning_strategy": self.learning_engine.strategy.value,
            "exploration_budget": self.learning_engine.exploration_budget,
            "current_metrics": {
                "success_rate": f"{current_metrics.success_rate:.1%}",
                "pattern_confidence": f"{current_metrics.pattern_confidence:.1%}",
                "model_accuracy": f"{current_metrics.model_accuracy:.1%}",
                "resource_utilization": f"{current_metrics.resource_utilization:.1%}",
            },
            "agent_capabilities": {
                name: {
                    "success_rate": cap.success_rate,
                    "specializations": list(cap.specializations),
                    "last_updated": cap.last_updated.isoformat(),
                }
                for name, cap in self.agent_capabilities.items()
            },
            "recent_insights": [
                {
                    "type": insight.insight_type,
                    "description": insight.description,
                    "confidence": insight.confidence,
                }
                for insight in list(self.insight_buffer)[-10:]
            ],
            "system_health": self._assess_system_health(current_metrics),
            "recommendations": self._generate_recommendations(current_metrics),
        }

        return dashboard

    def _assess_system_health(self, metrics: LearningMetrics) -> str:
        """Assess overall system health"""

        if metrics.success_rate > 0.85 and metrics.resource_utilization < 0.7:
            return "excellent"
        elif metrics.success_rate > 0.7 and metrics.resource_utilization < 0.85:
            return "good"
        elif metrics.success_rate > 0.5:
            return "fair"
        else:
            return "needs_attention"


class MetricsCollector:
    """Collect and aggregate system metrics"""

    def __init__(self):
        self.metrics = defaultdict(list)
        self.aggregated = {}

    def record(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric value"""
        self.metrics[metric_name].append(
            {"value": value, "timestamp": time.time(), "tags": tags or {}}
        )

    def get_aggregated(
        self, metric_name: str, window_seconds: int = 300
    ) -> Dict[str, float]:
        """Get aggregated metrics for time window"""
        current_time = time.time()
        window_start = current_time - window_seconds

        values = [
            m["value"]
            for m in self.metrics[metric_name]
            if m["timestamp"] > window_start
        ]

        if not values:
            return {}

        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "count": len(values),
        }


class AlertManager:
    """Manage system alerts"""

    def __init__(self):
        self.alerts = deque(maxlen=100)
        self.alert_handlers = {}

    async def send_alert(
        self, alert_type: str, message: str, data: Dict[str, Any] = None
    ):
        """Send an alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.alerts.append(alert)
        logger.warning(f"Alert: {alert_type} - {message}")

        # Execute registered handlers
        if alert_type in self.alert_handlers:
            for handler in self.alert_handlers[alert_type]:
                await handler(alert)

    def register_handler(self, alert_type: str, handler):
        """Register alert handler"""
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []
        self.alert_handlers[alert_type].append(handler)

    def get_recent_alerts(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        return list(self.alerts)[-count:]


# Test and demonstration
if __name__ == "__main__":

    async def demo():
        # Initialize orchestrator with adaptive strategy
        orchestrator = EnhancedLearningOrchestrator(
            learning_strategy=LearningStrategy.ADAPTIVE
        )
        await orchestrator.initialize()

        # Demo task contexts
        tasks = [
            ExecutionContext(
                task_id="task_001",
                task_type="web_development",
                description="Create responsive landing page with contact form",
                complexity=2.5,
                priority=2,
                deadline=datetime.now() + timedelta(hours=2),
                user_context={"framework": "React", "style": "modern"},
                constraints={"max_parallel": 2},
            ),
            ExecutionContext(
                task_id="task_002",
                task_type="security_audit",
                description="Comprehensive security audit of API endpoints",
                complexity=3.5,
                priority=4,
                user_context={"scope": "full", "compliance": "OWASP"},
                constraints={"resources": {"cpu": 2.0, "memory": 4.0}},
            ),
            ExecutionContext(
                task_id="task_003",
                task_type="bug_fix",
                description="Fix authentication token expiration issue",
                complexity=1.5,
                priority=3,
                deadline=datetime.now() + timedelta(minutes=30),
                parent_task_id="task_001",
            ),
            ExecutionContext(
                task_id="task_004",
                task_type="deployment",
                description="Deploy application to production environment",
                complexity=2.0,
                priority=5,
                dependencies=["task_001", "task_003"],
                constraints={"environment": "production"},
            ),
        ]

        # Execute tasks
        for context in tasks:
            print(f"\n{'='*60}")
            print(f"Executing: {context.description}")
            print(
                f"Type: {context.task_type}, Complexity: {context.complexity}, Priority: {context.priority}"
            )

            result = await orchestrator.execute_with_learning(context)

            print(f"Result: {'SUCCESS' if result.get('success') else 'FAILED'}")
            if result.get("monitoring"):
                print(f"Duration: {result['monitoring'].get('total_duration', 0):.1f}s")
            if result.get("error"):
                print(f"Error: {result['error']}")

        # Display dashboard
        print(f"\n{'='*60}")
        print("=== ENHANCED LEARNING DASHBOARD ===")
        dashboard = await orchestrator.get_enhanced_dashboard()

        print(f"\nSystem Health: {dashboard['system_health'].upper()}")
        print(f"Learning Strategy: {dashboard['learning_strategy']}")
        print(f"Adaptation Threshold: {dashboard['adaptation_threshold']:.2f}")
        print(f"Exploration Budget: {dashboard['exploration_budget']:.1%}")

        print("\nCurrent Metrics:")
        for metric, value in dashboard["current_metrics"].items():
            print(f"  {metric}: {value}")

        print("\nTop Agent Capabilities:")
        for agent, cap in list(dashboard["agent_capabilities"].items())[:3]:
            print(f"  {agent}:")
            print(f"    Success Rate: {cap['success_rate']:.1%}")
            print(f"    Specializations: {', '.join(cap['specializations'])}")

        if dashboard.get("recent_insights"):
            print("\nRecent Insights:")
            for insight in dashboard["recent_insights"][:3]:
                print(f"  - [{insight['type']}] {insight['description'][:60]}...")
                print(f"    Confidence: {insight['confidence']:.1%}")

        if dashboard.get("recommendations"):
            print("\nRecommendations:")
            for rec in dashboard["recommendations"]:
                print(f"  • {rec}")

    # Run demo
    asyncio.run(demo())
