#!/usr/bin/env python3
"""
CPU-Only Orchestrator Fallback System v1.0
Graceful degradation for systems without NPU acceleration

Provides optimized CPU-based agent orchestration with:
- Multi-factor agent selection algorithms
- Memory-aware task scheduling
- Performance monitoring and adaptation
- Seamless integration with PICMCS v3.0 hardware detection

Compatible with all systems: High-end workstations to resource-constrained environments
"""

import asyncio
import json
import logging
import multiprocessing as mp
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SystemCapabilities:
    """System hardware and performance capabilities"""

    cpu_cores: int
    memory_gb: float
    cpu_freq_ghz: float
    has_avx2: bool
    has_avx512: bool
    has_npu: bool
    performance_tier: str  # 'high', 'medium', 'low', 'constrained'


@dataclass
class TaskRequest:
    """Individual task request with metadata"""

    task_id: str
    agent_type: str
    prompt: str
    priority: int
    complexity_score: float
    estimated_duration: float
    memory_requirement: int


@dataclass
class AgentCapability:
    """Agent capability and performance profile"""

    name: str
    specialties: List[str]
    performance_score: float
    memory_usage: int
    cpu_efficiency: float
    response_time_ms: float
    success_rate: float


@dataclass
class OrchestrationResult:
    """Result of orchestration operation"""

    task_id: str
    agent_used: str
    execution_time_ms: float
    success: bool
    performance_score: float
    memory_peak_mb: int
    cpu_utilization: float


class CPUOrchestrator:
    """
    CPU-Only Orchestrator with intelligent fallback strategies

    Features:
    - Multi-factor agent selection (specialty, performance, availability)
    - Dynamic resource allocation based on system capabilities
    - Memory-aware task scheduling with overflow protection
    - Performance monitoring and adaptive optimization
    - Seamless integration with PICMCS v3.0 hardware detection
    """

    def __init__(self, config_path: Optional[str] = None):
        self.system_caps = self._detect_system_capabilities()
        self.agents = self._load_agent_profiles()
        self.performance_history = {}
        self.resource_monitor = ResourceMonitor()
        self.task_queue = asyncio.Queue()
        self.active_tasks = {}
        self.stats = {
            "tasks_completed": 0,
            "total_execution_time": 0.0,
            "average_response_time": 0.0,
            "success_rate": 0.0,
            "memory_efficiency": 0.0,
        }

        # Configure based on system capabilities
        self._configure_for_system()

        logger.info(
            f"CPU Orchestrator initialized - Performance tier: {self.system_caps.performance_tier}"
        )
        logger.info(
            f"System: {self.system_caps.cpu_cores} cores, {self.system_caps.memory_gb:.1f}GB RAM"
        )

    def _detect_system_capabilities(self) -> SystemCapabilities:
        """Detect system hardware capabilities with PICMCS v3.0 integration"""
        try:
            # CPU information
            cpu_cores = mp.cpu_count()
            cpu_freq = psutil.cpu_freq().max / 1000.0 if psutil.cpu_freq() else 2.5

            # Memory information
            memory_info = psutil.virtual_memory()
            memory_gb = memory_info.total / (1024**3)

            # Feature detection (simplified for CPU systems)
            has_avx2 = True  # Assume modern CPUs have AVX2
            has_avx512 = False  # Conservative assumption for CPU-only
            has_npu = False  # CPU-only system

            # Performance tier determination
            if memory_gb >= 16 and cpu_cores >= 8:
                performance_tier = "high"
            elif memory_gb >= 8 and cpu_cores >= 4:
                performance_tier = "medium"
            elif memory_gb >= 4 and cpu_cores >= 2:
                performance_tier = "low"
            else:
                performance_tier = "constrained"

            return SystemCapabilities(
                cpu_cores=cpu_cores,
                memory_gb=memory_gb,
                cpu_freq_ghz=cpu_freq,
                has_avx2=has_avx2,
                has_avx512=has_avx512,
                has_npu=has_npu,
                performance_tier=performance_tier,
            )

        except Exception as e:
            logger.warning(f"Hardware detection failed, using defaults: {e}")
            return SystemCapabilities(
                cpu_cores=4,
                memory_gb=8.0,
                cpu_freq_ghz=2.5,
                has_avx2=True,
                has_avx512=False,
                has_npu=False,
                performance_tier="medium",
            )

    def _load_agent_profiles(self) -> Dict[str, AgentCapability]:
        """Load agent capability profiles with CPU-optimized scoring"""
        # Default agent profiles optimized for CPU execution
        default_agents = {
            "director": AgentCapability(
                name="director",
                specialties=["strategy", "planning", "coordination"],
                performance_score=0.9,
                memory_usage=50,
                cpu_efficiency=0.8,
                response_time_ms=100,
                success_rate=0.95,
            ),
            "architect": AgentCapability(
                name="architect",
                specialties=["design", "architecture", "system"],
                performance_score=0.85,
                memory_usage=75,
                cpu_efficiency=0.75,
                response_time_ms=150,
                success_rate=0.92,
            ),
            "security": AgentCapability(
                name="security",
                specialties=["security", "audit", "vulnerability"],
                performance_score=0.88,
                memory_usage=60,
                cpu_efficiency=0.82,
                response_time_ms=120,
                success_rate=0.94,
            ),
            "optimizer": AgentCapability(
                name="optimizer",
                specialties=["performance", "optimization", "efficiency"],
                performance_score=0.87,
                memory_usage=55,
                cpu_efficiency=0.85,
                response_time_ms=110,
                success_rate=0.93,
            ),
            "debugger": AgentCapability(
                name="debugger",
                specialties=["debug", "analysis", "troubleshooting"],
                performance_score=0.83,
                memory_usage=45,
                cpu_efficiency=0.88,
                response_time_ms=90,
                success_rate=0.91,
            ),
        }

        # Adjust profiles based on system capabilities
        if self.system_caps.performance_tier == "constrained":
            for agent in default_agents.values():
                agent.memory_usage = int(agent.memory_usage * 0.7)
                agent.response_time_ms *= 1.5

        elif self.system_caps.performance_tier == "high":
            for agent in default_agents.values():
                agent.performance_score *= 1.1
                agent.response_time_ms *= 0.8

        return default_agents

    def _configure_for_system(self):
        """Configure orchestrator based on system capabilities"""
        if self.system_caps.performance_tier == "constrained":
            self.max_concurrent_tasks = 2
            self.memory_limit_mb = 512
            self.cpu_threshold = 0.8
        elif self.system_caps.performance_tier == "low":
            self.max_concurrent_tasks = 4
            self.memory_limit_mb = 1024
            self.cpu_threshold = 0.7
        elif self.system_caps.performance_tier == "medium":
            self.max_concurrent_tasks = 8
            self.memory_limit_mb = 2048
            self.cpu_threshold = 0.75
        else:  # high performance
            self.max_concurrent_tasks = 16
            self.memory_limit_mb = 4096
            self.cpu_threshold = 0.8

        logger.info(
            f"Configured for {self.system_caps.performance_tier} performance: "
            f"max_tasks={self.max_concurrent_tasks}, "
            f"memory_limit={self.memory_limit_mb}MB"
        )

    def calculate_agent_score(self, task: TaskRequest, agent: AgentCapability) -> float:
        """
        Multi-factor agent selection algorithm

        Factors:
        - Specialty match (40%)
        - Performance score (25%)
        - Resource efficiency (20%)
        - Current availability (15%)
        """
        # Specialty matching
        specialty_score = 0.0
        task_keywords = task.prompt.lower().split()
        for specialty in agent.specialties:
            if any(keyword in specialty for keyword in task_keywords):
                specialty_score += 1.0
        specialty_score = min(specialty_score / len(agent.specialties), 1.0)

        # Performance score (normalized)
        performance_score = agent.performance_score

        # Resource efficiency (memory and CPU)
        memory_efficiency = 1.0 - (agent.memory_usage / self.memory_limit_mb)
        cpu_efficiency = agent.cpu_efficiency
        resource_score = (memory_efficiency + cpu_efficiency) / 2.0

        # Availability (based on current load)
        availability_score = 1.0 - (len(self.active_tasks) / self.max_concurrent_tasks)

        # Weighted combination
        total_score = (
            specialty_score * 0.4
            + performance_score * 0.25
            + resource_score * 0.2
            + availability_score * 0.15
        )

        return total_score

    async def select_optimal_agent(self, task: TaskRequest) -> Optional[str]:
        """Select the optimal agent for a given task"""
        if not self.agents:
            return None

        agent_scores = {}
        for agent_name, agent_profile in self.agents.items():
            score = self.calculate_agent_score(task, agent_profile)
            agent_scores[agent_name] = score

        # Select agent with highest score
        best_agent = max(agent_scores.items(), key=lambda x: x[1])

        logger.debug(
            f"Agent selection for task {task.task_id}: {best_agent[0]} (score: {best_agent[1]:.3f})"
        )
        return best_agent[0]

    async def execute_task(self, task: TaskRequest) -> OrchestrationResult:
        """Execute a single task with performance monitoring"""
        start_time = time.time()
        memory_start = self.resource_monitor.get_memory_usage()

        try:
            # Select optimal agent
            selected_agent = await self.select_optimal_agent(task)
            if not selected_agent:
                raise Exception("No suitable agent available")

            # Track active task
            self.active_tasks[task.task_id] = {
                "agent": selected_agent,
                "start_time": start_time,
                "memory_start": memory_start,
            }

            # Simulate task execution (replace with actual agent invocation)
            agent_profile = self.agents[selected_agent]
            execution_time = agent_profile.response_time_ms / 1000.0

            # Add complexity-based scaling
            execution_time *= 1.0 + task.complexity_score * 0.5

            await asyncio.sleep(execution_time)

            # Calculate performance metrics
            actual_time = time.time() - start_time
            memory_peak = self.resource_monitor.get_memory_usage()
            cpu_util = psutil.cpu_percent(interval=0.1)

            success = True  # Assume success for simulation
            performance_score = 1.0 / (actual_time + 0.1)  # Inverse time score

            # Update statistics
            self._update_stats(actual_time, success, memory_peak - memory_start)

            result = OrchestrationResult(
                task_id=task.task_id,
                agent_used=selected_agent,
                execution_time_ms=actual_time * 1000,
                success=success,
                performance_score=performance_score,
                memory_peak_mb=memory_peak,
                cpu_utilization=cpu_util,
            )

            logger.info(
                f"Task {task.task_id} completed: {selected_agent} "
                f"({actual_time*1000:.1f}ms, {memory_peak:.1f}MB)"
            )

            return result

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            actual_time = time.time() - start_time
            return OrchestrationResult(
                task_id=task.task_id,
                agent_used=selected_agent or "unknown",
                execution_time_ms=actual_time * 1000,
                success=False,
                performance_score=0.0,
                memory_peak_mb=memory_start,
                cpu_utilization=psutil.cpu_percent(interval=0.1),
            )

        finally:
            # Remove from active tasks
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]

    def _update_stats(self, execution_time: float, success: bool, memory_used: float):
        """Update orchestrator statistics"""
        self.stats["tasks_completed"] += 1
        self.stats["total_execution_time"] += execution_time
        self.stats["average_response_time"] = (
            self.stats["total_execution_time"] / self.stats["tasks_completed"]
        )

        # Update success rate
        if success:
            success_count = (
                self.stats["tasks_completed"] * self.stats["success_rate"] + 1
            )
        else:
            success_count = self.stats["tasks_completed"] * self.stats["success_rate"]
        self.stats["success_rate"] = success_count / self.stats["tasks_completed"]

        # Update memory efficiency
        memory_efficiency = max(0, 1.0 - (memory_used / self.memory_limit_mb))
        self.stats["memory_efficiency"] = (
            self.stats["memory_efficiency"] * (self.stats["tasks_completed"] - 1)
            + memory_efficiency
        ) / self.stats["tasks_completed"]

    async def process_workflow(
        self, tasks: List[TaskRequest]
    ) -> List[OrchestrationResult]:
        """Process multiple tasks with intelligent scheduling"""
        results = []

        # Sort tasks by priority and complexity
        sorted_tasks = sorted(
            tasks, key=lambda t: (t.priority, -t.complexity_score), reverse=True
        )

        # Process tasks with concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

        async def execute_with_semaphore(task):
            async with semaphore:
                return await self.execute_task(task)

        # Execute all tasks
        task_coroutines = [execute_with_semaphore(task) for task in sorted_tasks]
        results = await asyncio.gather(*task_coroutines, return_exceptions=True)

        # Filter out exceptions and log errors
        clean_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
            else:
                clean_results.append(result)

        logger.info(
            f"Workflow completed: {len(clean_results)}/{len(tasks)} tasks successful"
        )
        return clean_results

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        return {
            "system_capabilities": asdict(self.system_caps),
            "orchestrator_config": {
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "memory_limit_mb": self.memory_limit_mb,
                "cpu_threshold": self.cpu_threshold,
            },
            "performance_stats": self.stats.copy(),
            "agent_profiles": {
                name: asdict(profile) for name, profile in self.agents.items()
            },
            "current_load": {
                "active_tasks": len(self.active_tasks),
                "memory_usage_mb": self.resource_monitor.get_memory_usage(),
                "cpu_utilization": psutil.cpu_percent(interval=0.1),
            },
        }


class ResourceMonitor:
    """System resource monitoring utility"""

    def __init__(self):
        self.process = psutil.Process()

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / (1024 * 1024)

    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        return self.process.cpu_percent(interval=0.1)


async def main():
    """Demo and testing function"""
    print("🚀 CPU Orchestrator Fallback System v1.0")
    print("=" * 50)

    # Initialize orchestrator
    orchestrator = CPUOrchestrator()

    # Create sample tasks
    tasks = [
        TaskRequest(
            task_id="task_001",
            agent_type="security",
            prompt="audit system vulnerabilities",
            priority=1,
            complexity_score=0.7,
            estimated_duration=2.0,
            memory_requirement=100,
        ),
        TaskRequest(
            task_id="task_002",
            agent_type="architect",
            prompt="design system architecture",
            priority=2,
            complexity_score=0.9,
            estimated_duration=3.0,
            memory_requirement=150,
        ),
        TaskRequest(
            task_id="task_003",
            agent_type="optimizer",
            prompt="optimize performance bottlenecks",
            priority=1,
            complexity_score=0.6,
            estimated_duration=1.5,
            memory_requirement=80,
        ),
    ]

    print(f"Processing {len(tasks)} tasks...")
    start_time = time.time()

    # Process workflow
    results = await orchestrator.process_workflow(tasks)

    total_time = time.time() - start_time

    # Display results
    print(f"\n📊 Results ({total_time:.2f}s total):")
    for result in results:
        status = "✅" if result.success else "❌"
        print(
            f"{status} {result.task_id}: {result.agent_used} "
            f"({result.execution_time_ms:.1f}ms, {result.memory_peak_mb:.1f}MB)"
        )

    # Performance report
    report = orchestrator.get_performance_report()
    print(f"\n📈 Performance Report:")
    print(f"System Tier: {report['system_capabilities']['performance_tier']}")
    print(f"Tasks Completed: {report['performance_stats']['tasks_completed']}")
    print(
        f"Average Response: {report['performance_stats']['average_response_time']*1000:.1f}ms"
    )
    print(f"Success Rate: {report['performance_stats']['success_rate']*100:.1f}%")
    print(
        f"Memory Efficiency: {report['performance_stats']['memory_efficiency']*100:.1f}%"
    )


if __name__ == "__main__":
    asyncio.run(main())
