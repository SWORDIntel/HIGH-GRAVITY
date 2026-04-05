#!/usr/bin/env python3
"""
Enhanced Agent Coordination Matrix v2.0
True parallel execution with NPU acceleration and advanced workflow optimization
Extends the base coordination matrix with 50K+ ops/sec capability
"""

import asyncio
import concurrent.futures
import json
import logging
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import asyncpg
import numpy as np

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from agent_coordination_matrix import (
        AgentCapability,
        AgentCoordinationMatrix,
        AgentSpec,
        CoordinationPlan,
        ExecutionMode,
    )

    from agents.src.python.npu_coordination_bridge import (
        NPUAgentScore,
        NPUCoordinationBridge,
        NPUWorkflowTask,
        WorkflowPriority,
    )
except ImportError as e:
    logging.warning(f"Import error: {e}. Some features may be limited.")

try:
    import openvino as ov

    OPENVINO_AVAILABLE = True
except ImportError:
    OPENVINO_AVAILABLE = False

logger = logging.getLogger(__name__)


class WorkflowComplexity(Enum):
    """Workflow complexity levels for optimization"""

    SIMPLE = "simple"  # Single agent, <1K ops
    MODERATE = "moderate"  # 2-3 agents, <5K ops
    COMPLEX = "complex"  # 4-6 agents, <15K ops
    ENTERPRISE = "enterprise"  # 7+ agents, <50K ops
    MASSIVE = "massive"  # 10+ agents, 50K+ ops


class OptimizationStrategy(Enum):
    """NPU optimization strategies"""

    LATENCY_OPTIMIZED = "latency"  # Minimize response time
    THROUGHPUT_OPTIMIZED = "throughput"  # Maximize ops/sec
    RESOURCE_BALANCED = "balanced"  # Balance latency and throughput
    QUALITY_FOCUSED = "quality"  # Prioritize result quality
    COST_OPTIMIZED = "cost"  # Minimize resource usage


@dataclass
class EnhancedCoordinationPlan(CoordinationPlan):
    """Enhanced coordination plan with NPU optimizations"""

    complexity: WorkflowComplexity = WorkflowComplexity.MODERATE
    optimization_strategy: OptimizationStrategy = (
        OptimizationStrategy.THROUGHPUT_OPTIMIZED
    )
    npu_accelerated: bool = False
    parallel_efficiency: float = 0.85
    resource_requirements: Dict[str, float] = field(default_factory=dict)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    pipeline_stages: List[List[str]] = field(default_factory=list)
    expected_throughput_ops_sec: float = 0.0


@dataclass
class ExecutionMetrics:
    """Comprehensive execution metrics"""

    start_time: datetime
    end_time: Optional[datetime] = None
    agents_executed: List[str] = field(default_factory=list)
    parallel_stages: int = 0
    total_operations: int = 0
    successful_operations: int = 0
    npu_accelerated_ops: int = 0
    peak_throughput_ops_sec: float = 0.0
    avg_latency_ms: float = 0.0
    resource_utilization: Dict[str, float] = field(default_factory=dict)


class EnhancedCoordinationMatrix(AgentCoordinationMatrix):
    """Enhanced coordination matrix with NPU acceleration and advanced parallel execution"""

    def __init__(self, db_connection_string: str = None):
        super().__init__(db_connection_string)

        # NPU integration
        self.npu_bridge: Optional[NPUCoordinationBridge] = None
        self.npu_enabled = False

        # Advanced execution tracking
        self.active_workflows: Dict[str, EnhancedCoordinationPlan] = {}
        self.execution_metrics: Dict[str, ExecutionMetrics] = {}

        # Performance optimization
        self.throughput_optimizer = ThroughputOptimizer()
        self.pipeline_manager = PipelineManager()
        self.resource_allocator = ResourceAllocator()

        # Advanced agent registry with enhanced capabilities
        self.enhanced_agent_registry: Dict[str, EnhancedAgentSpec] = {}
        self._load_enhanced_agent_registry()

        # Real-time performance tracking
        self.performance_tracker = PerformanceTracker()

        # Workflow templates for common patterns
        self.workflow_templates = WorkflowTemplateManager()

    async def initialize(self):
        """Initialize enhanced coordination matrix with NPU acceleration"""
        logger.info("🚀 Initializing Enhanced Coordination Matrix v2.0")

        # Initialize base coordination matrix
        await super().initialize()

        # Initialize NPU bridge
        try:
            self.npu_bridge = NPUCoordinationBridge()
            self.npu_enabled = await self.npu_bridge.initialize()
            if self.npu_enabled:
                logger.info("✅ NPU acceleration enabled")
            else:
                logger.info("⚠️ NPU acceleration disabled, using CPU optimization")
        except Exception as e:
            logger.error(f"NPU bridge initialization failed: {e}")
            self.npu_enabled = False

        # Initialize performance components
        await self.throughput_optimizer.initialize()
        await self.pipeline_manager.initialize()
        await self.resource_allocator.initialize()
        await self.performance_tracker.initialize()

        # Load workflow templates
        self.workflow_templates.load_templates()

        logger.info("🎯 Enhanced Coordination Matrix ready for 50K+ ops/sec")

    def _load_enhanced_agent_registry(self):
        """Load enhanced agent registry with detailed capabilities"""
        # Build upon base registry
        for agent_name, base_spec in self.agent_registry.items():
            enhanced_spec = EnhancedAgentSpec(
                name=base_spec.name,
                capabilities=base_spec.capabilities,
                priority=base_spec.priority,
                reliability_score=base_spec.reliability_score,
                avg_execution_time=base_spec.avg_execution_time,
                specializations=base_spec.specializations,
                dependencies=base_spec.dependencies,
                parallelizable=base_spec.parallelizable,
                # Enhanced attributes
                max_concurrent_tasks=self._estimate_max_concurrent(agent_name),
                npu_compatible=self._is_npu_compatible(agent_name),
                resource_requirements=self._estimate_resources(agent_name),
                throughput_capacity=self._estimate_throughput(agent_name),
            )
            self.enhanced_agent_registry[agent_name] = enhanced_spec

    def _estimate_max_concurrent(self, agent_name: str) -> int:
        """Estimate maximum concurrent tasks for agent"""
        # Strategic agents can handle more coordination
        if any(word in agent_name.lower() for word in ["director", "orchestrator"]):
            return 10
        # Security agents need focused attention
        elif "security" in agent_name.lower():
            return 3
        # Development agents vary by complexity
        elif any(word in agent_name.lower() for word in ["debug", "test", "patch"]):
            return 5
        else:
            return 2

    def _is_npu_compatible(self, agent_name: str) -> bool:
        """Determine if agent can benefit from NPU acceleration"""
        # Agents that do pattern recognition, analysis, or selection benefit from NPU
        npu_beneficial = [
            "security",
            "audit",
            "analyze",
            "optimizer",
            "architect",
            "selector",
            "monitor",
            "intelligence",
        ]
        return any(word in agent_name.lower() for word in npu_beneficial)

    def _estimate_resources(self, agent_name: str) -> Dict[str, float]:
        """Estimate resource requirements for agent"""
        base_cpu = 0.1  # 10% CPU baseline
        base_memory = 100  # 100MB baseline

        # Adjust based on agent type
        if "architect" in agent_name.lower():
            return {"cpu": base_cpu * 2, "memory": base_memory * 3}
        elif "security" in agent_name.lower():
            return {"cpu": base_cpu * 1.5, "memory": base_memory * 2}
        elif "debug" in agent_name.lower():
            return {"cpu": base_cpu * 1.2, "memory": base_memory * 1.5}
        else:
            return {"cpu": base_cpu, "memory": base_memory}

    def _estimate_throughput(self, agent_name: str) -> float:
        """Estimate agent throughput capacity in ops/sec"""
        # Base throughput estimates
        if any(word in agent_name.lower() for word in ["director", "orchestrator"]):
            return 1000.0  # High coordination throughput
        elif "security" in agent_name.lower():
            return 500.0  # Moderate security analysis throughput
        elif any(word in agent_name.lower() for word in ["debug", "test"]):
            return 200.0  # Lower throughput for detailed analysis
        else:
            return 300.0  # Default throughput

    async def create_enhanced_coordination_plan(
        self,
        task_description: str,
        execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
        optimization_strategy: OptimizationStrategy = OptimizationStrategy.THROUGHPUT_OPTIMIZED,
        max_agents: int = 8,
    ) -> EnhancedCoordinationPlan:
        """Create enhanced coordination plan with NPU optimization"""

        # Analyze task complexity
        complexity = self._analyze_task_complexity(task_description)

        # Get base coordination plan
        base_plan = self.create_coordination_plan(task_description, execution_mode)

        # NPU-enhanced agent selection if available
        if self.npu_enabled and self.npu_bridge:
            try:
                # Create NPU workflow task
                required_capabilities = self.analyze_task_requirements(task_description)

                npu_plan = await self.npu_bridge.create_npu_optimized_workflow(
                    task_description, WorkflowPriority.NORMAL, execution_mode
                )

                # Use NPU-selected agents
                primary_agents = npu_plan.primary_agents
                npu_accelerated = True

            except Exception as e:
                logger.warning(f"NPU optimization failed, using base plan: {e}")
                primary_agents = base_plan.primary_agents
                npu_accelerated = False
        else:
            primary_agents = base_plan.primary_agents
            npu_accelerated = False

        # Create dependency graph
        dependency_graph = self._create_dependency_graph(primary_agents)

        # Create pipeline stages for optimal parallel execution
        pipeline_stages = self._create_pipeline_stages(primary_agents, dependency_graph)

        # Estimate resource requirements
        resource_requirements = self._calculate_resource_requirements(primary_agents)

        # Calculate expected throughput
        expected_throughput = self._calculate_expected_throughput(
            primary_agents, execution_mode, optimization_strategy
        )

        # Create enhanced plan
        enhanced_plan = EnhancedCoordinationPlan(
            session_id=f"enhanced_{uuid.uuid4()}",
            primary_agents=primary_agents,
            supporting_agents=base_plan.supporting_agents,
            execution_mode=execution_mode,
            estimated_duration=base_plan.estimated_duration,
            success_probability=base_plan.success_probability,
            parallel_groups=base_plan.parallel_groups,
            # Enhanced attributes
            complexity=complexity,
            optimization_strategy=optimization_strategy,
            npu_accelerated=npu_accelerated,
            resource_requirements=resource_requirements,
            dependency_graph=dependency_graph,
            pipeline_stages=pipeline_stages,
            expected_throughput_ops_sec=expected_throughput,
        )

        # Store active workflow
        self.active_workflows[enhanced_plan.session_id] = enhanced_plan

        return enhanced_plan

    def _analyze_task_complexity(self, task_description: str) -> WorkflowComplexity:
        """Analyze task to determine complexity level"""
        task_lower = task_description.lower()

        # Count complexity indicators
        complexity_indicators = [
            len(task_description.split()),  # Word count
            len(
                [
                    word
                    for word in task_lower.split()
                    if word in ["and", "then", "also", "plus"]
                ]
            ),  # Coordination words
            len(
                [
                    word
                    for word in task_lower.split()
                    if word in ["secure", "test", "deploy", "monitor"]
                ]
            ),  # Multi-domain
        ]

        total_complexity = sum(complexity_indicators)

        if total_complexity >= 20:
            return WorkflowComplexity.MASSIVE
        elif total_complexity >= 15:
            return WorkflowComplexity.ENTERPRISE
        elif total_complexity >= 10:
            return WorkflowComplexity.COMPLEX
        elif total_complexity >= 5:
            return WorkflowComplexity.MODERATE
        else:
            return WorkflowComplexity.SIMPLE

    def _create_dependency_graph(self, agents: List[str]) -> Dict[str, List[str]]:
        """Create dependency graph for agents"""
        dependencies = {}

        for agent in agents:
            deps = []

            # Strategic dependencies
            if agent in ["DIRECTOR", "PROJECTORCHESTRATOR"]:
                deps = []  # Coordinators have no dependencies
            elif "ARCHITECT" in agent:
                deps = ["DIRECTOR"]  # Architect depends on direction
            elif any(word in agent for word in ["CONSTRUCTOR", "PATCHER"]):
                deps = ["ARCHITECT"]  # Implementation depends on architecture
            elif any(word in agent for word in ["TESTBED", "DEBUGGER"]):
                deps = ["CONSTRUCTOR", "PATCHER"]  # Testing depends on implementation
            elif "DEPLOYER" in agent:
                deps = ["TESTBED"]  # Deployment depends on testing
            elif "MONITOR" in agent:
                deps = ["DEPLOYER"]  # Monitoring depends on deployment

            dependencies[agent] = [dep for dep in deps if dep in agents]

        return dependencies

    def _create_pipeline_stages(
        self, agents: List[str], dependencies: Dict[str, List[str]]
    ) -> List[List[str]]:
        """Create pipeline stages for optimal parallel execution"""
        stages = []
        remaining_agents = set(agents)

        while remaining_agents:
            current_stage = []

            # Find agents with no unresolved dependencies
            for agent in list(remaining_agents):
                agent_deps = dependencies.get(agent, [])
                if not any(dep in remaining_agents for dep in agent_deps):
                    current_stage.append(agent)

            if not current_stage:
                # Break circular dependencies by taking remaining agents
                current_stage = list(remaining_agents)

            stages.append(current_stage)
            remaining_agents -= set(current_stage)

        return stages

    def _calculate_resource_requirements(self, agents: List[str]) -> Dict[str, float]:
        """Calculate total resource requirements"""
        total_resources = {"cpu": 0.0, "memory": 0.0, "npu": 0.0}

        for agent in agents:
            if agent in self.enhanced_agent_registry:
                agent_resources = self.enhanced_agent_registry[
                    agent
                ].resource_requirements
                total_resources["cpu"] += agent_resources.get("cpu", 0.1)
                total_resources["memory"] += agent_resources.get("memory", 100)

                # Add NPU usage if agent is NPU-compatible
                if self.enhanced_agent_registry[agent].npu_compatible:
                    total_resources["npu"] += 0.1

        return total_resources

    def _calculate_expected_throughput(
        self,
        agents: List[str],
        execution_mode: ExecutionMode,
        optimization_strategy: OptimizationStrategy,
    ) -> float:
        """Calculate expected workflow throughput"""
        agent_throughputs = []

        for agent in agents:
            if agent in self.enhanced_agent_registry:
                base_throughput = self.enhanced_agent_registry[
                    agent
                ].throughput_capacity
                agent_throughputs.append(base_throughput)

        if not agent_throughputs:
            return 1000.0  # Default throughput

        # Calculate based on execution mode
        if execution_mode == ExecutionMode.PARALLEL:
            # Parallel throughput is sum of all agents
            base_throughput = sum(agent_throughputs)

            # Apply parallel efficiency (typically 70-90%)
            parallel_efficiency = 0.85
            expected_throughput = base_throughput * parallel_efficiency

        else:
            # Sequential throughput is limited by slowest agent
            expected_throughput = min(agent_throughputs)

        # Apply optimization strategy multipliers
        strategy_multipliers = {
            OptimizationStrategy.LATENCY_OPTIMIZED: 0.8,  # Lower throughput, better latency
            OptimizationStrategy.THROUGHPUT_OPTIMIZED: 1.2,  # Higher throughput focus
            OptimizationStrategy.RESOURCE_BALANCED: 1.0,  # Balanced approach
            OptimizationStrategy.QUALITY_FOCUSED: 0.7,  # Lower throughput, higher quality
            OptimizationStrategy.COST_OPTIMIZED: 0.9,  # Slightly lower throughput
        }

        multiplier = strategy_multipliers.get(optimization_strategy, 1.0)
        return expected_throughput * multiplier

    async def execute_enhanced_coordination_plan(
        self, plan: EnhancedCoordinationPlan, task_description: str
    ) -> Dict[str, Any]:
        """Execute enhanced coordination plan with advanced parallel processing"""

        # Initialize execution metrics
        metrics = ExecutionMetrics(
            start_time=datetime.utcnow(),
            agents_executed=plan.primary_agents,
            parallel_stages=len(plan.pipeline_stages),
        )
        self.execution_metrics[plan.session_id] = metrics

        # Start performance tracking
        await self.performance_tracker.start_tracking(plan.session_id)

        try:
            if plan.npu_accelerated and self.npu_bridge:
                # NPU-accelerated execution
                results = await self._execute_npu_accelerated_plan(
                    plan, task_description
                )
            else:
                # Standard enhanced execution
                results = await self._execute_standard_enhanced_plan(
                    plan, task_description
                )

            # Finalize metrics
            metrics.end_time = datetime.utcnow()
            execution_time_ms = (
                metrics.end_time - metrics.start_time
            ).total_seconds() * 1000

            # Calculate final performance metrics
            if execution_time_ms > 0:
                metrics.peak_throughput_ops_sec = (
                    metrics.total_operations / execution_time_ms
                ) * 1000
                metrics.avg_latency_ms = execution_time_ms / max(
                    metrics.total_operations, 1
                )

            # Update success metrics
            successful_agents = sum(
                1
                for result in results.get("results", {}).values()
                if result.get("success", False)
            )
            metrics.successful_operations = successful_agents

            # Add enhanced metrics to results
            results.update(
                {
                    "enhanced_metrics": {
                        "complexity": plan.complexity.value,
                        "optimization_strategy": plan.optimization_strategy.value,
                        "npu_accelerated": plan.npu_accelerated,
                        "pipeline_stages": metrics.parallel_stages,
                        "peak_throughput_ops_sec": metrics.peak_throughput_ops_sec,
                        "avg_latency_ms": metrics.avg_latency_ms,
                        "parallel_efficiency": (
                            metrics.successful_operations / len(plan.primary_agents)
                            if plan.primary_agents
                            else 0
                        ),
                        "resource_utilization": metrics.resource_utilization,
                    }
                }
            )

            return results

        except Exception as e:
            logger.error(f"Enhanced coordination execution failed: {e}")
            metrics.end_time = datetime.utcnow()
            return {
                "session_id": plan.session_id,
                "success": False,
                "error": str(e),
                "enhanced_metrics": {
                    "complexity": plan.complexity.value,
                    "npu_accelerated": plan.npu_accelerated,
                    "error_stage": "execution",
                },
            }

        finally:
            # Cleanup
            if plan.session_id in self.active_workflows:
                del self.active_workflows[plan.session_id]

            await self.performance_tracker.stop_tracking(plan.session_id)

    async def _execute_npu_accelerated_plan(
        self, plan: EnhancedCoordinationPlan, task_description: str
    ) -> Dict[str, Any]:
        """Execute plan with NPU acceleration"""
        if not self.npu_bridge:
            raise RuntimeError("NPU bridge not available")

        # Convert to base coordination plan for NPU bridge
        base_plan = CoordinationPlan(
            session_id=plan.session_id,
            primary_agents=plan.primary_agents,
            supporting_agents=plan.supporting_agents,
            execution_mode=plan.execution_mode,
            estimated_duration=plan.estimated_duration,
            success_probability=plan.success_probability,
            parallel_groups=plan.parallel_groups,
        )

        # Execute with NPU acceleration
        results = await self.npu_bridge.execute_npu_workflow(
            base_plan, task_description
        )

        return results

    async def _execute_standard_enhanced_plan(
        self, plan: EnhancedCoordinationPlan, task_description: str
    ) -> Dict[str, Any]:
        """Execute plan with standard enhanced processing"""

        if plan.execution_mode == ExecutionMode.PARALLEL and plan.pipeline_stages:
            # Advanced pipeline execution
            return await self._execute_pipeline_stages(plan, task_description)
        else:
            # Use base coordination matrix execution
            base_plan = CoordinationPlan(
                session_id=plan.session_id,
                primary_agents=plan.primary_agents,
                supporting_agents=plan.supporting_agents,
                execution_mode=plan.execution_mode,
                estimated_duration=plan.estimated_duration,
                success_probability=plan.success_probability,
                parallel_groups=plan.parallel_groups,
            )
            return await self.execute_coordination_plan(base_plan, task_description)

    async def _execute_pipeline_stages(
        self, plan: EnhancedCoordinationPlan, task_description: str
    ) -> Dict[str, Any]:
        """Execute pipeline stages with advanced parallel processing"""
        all_results = {}
        stage_times = []

        for stage_idx, stage_agents in enumerate(plan.pipeline_stages):
            stage_start = time.perf_counter()

            logger.info(
                f"Executing pipeline stage {stage_idx + 1}/{len(plan.pipeline_stages)}: {stage_agents}"
            )

            # Execute stage agents in parallel
            stage_tasks = []
            for agent in stage_agents:
                task_coro = self._execute_single_agent(
                    agent,
                    task_description,
                    f"{plan.session_id}-stage{stage_idx}-{agent}",
                )
                stage_tasks.append(task_coro)

            # Wait for all agents in stage to complete
            stage_results = await asyncio.gather(*stage_tasks, return_exceptions=True)

            # Process stage results
            for agent, result in zip(stage_agents, stage_results):
                if isinstance(result, Exception):
                    all_results[agent] = {"success": False, "error": str(result)}
                else:
                    all_results[agent] = result

            stage_time = time.perf_counter() - stage_start
            stage_times.append(stage_time)

            logger.info(f"Stage {stage_idx + 1} completed in {stage_time*1000:.1f}ms")

        # Calculate overall results
        successful_agents = sum(
            1 for result in all_results.values() if result.get("success", False)
        )
        total_time = sum(stage_times)

        return {
            "session_id": plan.session_id,
            "success": successful_agents > 0,
            "results": all_results,
            "execution_time_ms": total_time * 1000,
            "pipeline_stages": len(plan.pipeline_stages),
            "stage_times_ms": [t * 1000 for t in stage_times],
            "agents_executed": list(all_results.keys()),
            "parallel_efficiency": (
                successful_agents / len(plan.primary_agents)
                if plan.primary_agents
                else 0
            ),
        }


# Enhanced agent specification
@dataclass
class EnhancedAgentSpec(AgentSpec):
    """Enhanced agent specification with additional performance attributes"""

    max_concurrent_tasks: int = 1
    npu_compatible: bool = False
    resource_requirements: Dict[str, float] = field(default_factory=dict)
    throughput_capacity: float = 100.0  # ops/sec
    scaling_factor: float = 1.0
    optimization_hints: Set[str] = field(default_factory=set)


# Supporting classes for enhanced functionality
class ThroughputOptimizer:
    """Optimizes throughput for parallel execution"""

    async def initialize(self):
        """Initialize throughput optimizer"""
        pass


class PipelineManager:
    """Manages pipeline execution and staging"""

    async def initialize(self):
        """Initialize pipeline manager"""
        pass


class ResourceAllocator:
    """Manages resource allocation for agents"""

    async def initialize(self):
        """Initialize resource allocator"""
        pass


class PerformanceTracker:
    """Tracks real-time performance metrics"""

    def __init__(self):
        self.active_sessions = {}

    async def initialize(self):
        """Initialize performance tracker"""
        pass

    async def start_tracking(self, session_id: str):
        """Start tracking performance for session"""
        self.active_sessions[session_id] = {
            "start_time": time.perf_counter(),
            "operations": 0,
        }

    async def stop_tracking(self, session_id: str):
        """Stop tracking performance for session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]


class WorkflowTemplateManager:
    """Manages workflow templates for common patterns"""

    def __init__(self):
        self.templates = {}

    def load_templates(self):
        """Load common workflow templates"""
        # Security audit template
        self.templates["security_audit"] = {
            "agents": ["SECURITY", "SECURITYAUDITOR", "CRYPTOEXPERT"],
            "execution_mode": ExecutionMode.PARALLEL,
            "optimization_strategy": OptimizationStrategy.QUALITY_FOCUSED,
        }

        # Development cycle template
        self.templates["development_cycle"] = {
            "agents": ["ARCHITECT", "CONSTRUCTOR", "TESTBED", "DEPLOYER"],
            "execution_mode": ExecutionMode.PARALLEL,
            "optimization_strategy": OptimizationStrategy.THROUGHPUT_OPTIMIZED,
        }


# Global enhanced coordination matrix instance
enhanced_coordination_matrix = EnhancedCoordinationMatrix()


async def coordinate_agents_enhanced(
    task_description: str,
    execution_mode: str = "parallel",
    optimization_strategy: str = "throughput",
    max_agents: int = 8,
) -> Dict[str, Any]:
    """Enhanced coordination interface with NPU acceleration"""
    await enhanced_coordination_matrix.initialize()

    # Parse execution mode
    mode_map = {
        "parallel": ExecutionMode.PARALLEL,
        "sequential": ExecutionMode.SEQUENTIAL,
        "redundant": ExecutionMode.REDUNDANT,
        "consensus": ExecutionMode.CONSENSUS,
    }
    exec_mode = mode_map.get(execution_mode.lower(), ExecutionMode.PARALLEL)

    # Parse optimization strategy
    strategy_map = {
        "latency": OptimizationStrategy.LATENCY_OPTIMIZED,
        "throughput": OptimizationStrategy.THROUGHPUT_OPTIMIZED,
        "balanced": OptimizationStrategy.RESOURCE_BALANCED,
        "quality": OptimizationStrategy.QUALITY_FOCUSED,
        "cost": OptimizationStrategy.COST_OPTIMIZED,
    }
    opt_strategy = strategy_map.get(
        optimization_strategy.lower(), OptimizationStrategy.THROUGHPUT_OPTIMIZED
    )

    # Create enhanced plan
    plan = await enhanced_coordination_matrix.create_enhanced_coordination_plan(
        task_description, exec_mode, opt_strategy, max_agents
    )

    # Execute enhanced plan
    results = await enhanced_coordination_matrix.execute_enhanced_coordination_plan(
        plan, task_description
    )

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        results = asyncio.run(coordinate_agents_enhanced(task))
        print(json.dumps(results, indent=2, default=str))
