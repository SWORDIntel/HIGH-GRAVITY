#!/usr/bin/env python3
"""
Unified Orchestrator System v1.0
Automatic NPU/CPU fallback with seamless performance optimization

Provides intelligent orchestrator selection:
- Automatic hardware detection and capability assessment
- Seamless NPU → CPU fallback for maximum compatibility
- Performance optimization for all hardware tiers
- Zero-configuration operation with intelligent defaults
- Integration with PICMCS v3.0 8-level hardware fallback

Compatible with all systems: NPU-enabled workstations to constrained environments
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Import our orchestrator systems
try:
    from cpu_orchestrator_fallback import (
        CPUOrchestrator,
        OrchestrationResult,
        TaskRequest,
    )
    from hardware_detection_unified import (
        HardwareCapabilities,
        HardwareDetector,
        OrchestrationConfig,
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(
        "Please ensure cpu_orchestrator_fallback.py and hardware_detection_unified.py are in the same directory"
    )
    sys.exit(1)

# Try to import NPU orchestrator (may not be available on all systems)
try:
    from npu_optimized_final import NPUOrchestrator

    NPU_AVAILABLE = True
except ImportError:
    NPU_AVAILABLE = False
    print("ℹ️  NPU orchestrator not available, using CPU-only mode")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class UnifiedConfig:
    """Unified orchestrator configuration"""

    selected_mode: str  # 'npu', 'cpu_optimized', 'cpu_basic', 'memory_constrained'
    primary_orchestrator: str  # 'NPUOrchestrator', 'CPUOrchestrator'
    fallback_enabled: bool
    hardware_tier: str
    performance_target: float  # ops/sec
    memory_limit_mb: int
    max_concurrent_tasks: int


@dataclass
class SystemStatus:
    """Real-time system status"""

    orchestrator_mode: str
    hardware_detected: bool
    npu_available: bool
    performance_ops_sec: float
    memory_usage_mb: float
    cpu_utilization: float
    active_tasks: int
    success_rate: float
    uptime_seconds: float


class UnifiedOrchestrator:
    """
    Unified orchestrator with automatic NPU/CPU fallback

    Features:
    - Automatic hardware detection and orchestrator selection
    - Seamless fallback from NPU to CPU when needed
    - Performance monitoring and adaptive optimization
    - Zero-configuration operation with intelligent defaults
    - Real-time system status and health monitoring
    """

    def __init__(self, force_mode: Optional[str] = None):
        self.start_time = time.time()
        self.force_mode = force_mode
        self.hardware_detector = HardwareDetector()
        self.capabilities = self.hardware_detector.get_capabilities()
        self.config = self._determine_configuration()

        # Initialize the selected orchestrator
        self.primary_orchestrator = None
        self.fallback_orchestrator = None
        self.current_mode = self.config.selected_mode

        self._initialize_orchestrators()

        # Performance tracking
        self.stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_execution_time": 0.0,
            "npu_tasks": 0,
            "cpu_tasks": 0,
            "fallback_events": 0,
        }

        logger.info(
            f"🚀 Unified Orchestrator initialized: {self.config.selected_mode} mode"
        )
        logger.info(
            f"Hardware: {self.capabilities.performance_tier} tier, {self.capabilities.cpu_cores} cores, {self.capabilities.total_memory_gb:.1f}GB"
        )

    def _determine_configuration(self) -> UnifiedConfig:
        """Determine optimal configuration based on hardware capabilities"""
        orchestrator_config = self.hardware_detector.get_orchestration_config()

        # Override with force mode if specified
        if self.force_mode:
            selected_mode = self.force_mode
            logger.info(f"🔧 Force mode enabled: {self.force_mode}")
        else:
            selected_mode = self.capabilities.orchestrator_mode

        # Determine primary orchestrator
        if selected_mode == "npu" and NPU_AVAILABLE and self.capabilities.has_npu:
            primary_orchestrator = "NPUOrchestrator"
            performance_target = 25000.0  # 25K ops/sec for NPU
        else:
            primary_orchestrator = "CPUOrchestrator"
            # Adjust performance target based on hardware tier
            if self.capabilities.performance_tier == "ultra":
                performance_target = 5000.0
            elif self.capabilities.performance_tier == "high":
                performance_target = 2500.0
            elif self.capabilities.performance_tier == "medium":
                performance_target = 1000.0
            elif self.capabilities.performance_tier == "low":
                performance_target = 500.0
            else:  # constrained
                performance_target = 100.0

        return UnifiedConfig(
            selected_mode=selected_mode,
            primary_orchestrator=primary_orchestrator,
            fallback_enabled=True,
            hardware_tier=self.capabilities.performance_tier,
            performance_target=performance_target,
            memory_limit_mb=orchestrator_config.memory_limit_mb,
            max_concurrent_tasks=orchestrator_config.max_concurrent_tasks,
        )

    def _initialize_orchestrators(self):
        """Initialize primary and fallback orchestrators"""
        try:
            # Initialize primary orchestrator
            if self.config.primary_orchestrator == "NPUOrchestrator" and NPU_AVAILABLE:
                self.primary_orchestrator = NPUOrchestrator()
                logger.info("✅ NPU Orchestrator initialized as primary")
            else:
                self.primary_orchestrator = CPUOrchestrator()
                logger.info("✅ CPU Orchestrator initialized as primary")

            # Always initialize CPU orchestrator as fallback
            if self.config.fallback_enabled and not isinstance(
                self.primary_orchestrator, CPUOrchestrator
            ):
                self.fallback_orchestrator = CPUOrchestrator()
                logger.info("✅ CPU Orchestrator initialized as fallback")

        except Exception as e:
            logger.error(f"❌ Primary orchestrator initialization failed: {e}")
            # Fallback to CPU orchestrator
            self.primary_orchestrator = CPUOrchestrator()
            self.config.selected_mode = "cpu_fallback"
            self.stats["fallback_events"] += 1
            logger.warning("⚠️  Falling back to CPU orchestrator")

    async def execute_task(self, task: TaskRequest) -> OrchestrationResult:
        """Execute a single task with automatic fallback"""
        start_time = time.time()
        self.stats["total_tasks"] += 1

        try:
            # Try primary orchestrator first
            result = await self._execute_with_orchestrator(
                self.primary_orchestrator, task
            )

            # Track which orchestrator was used
            if isinstance(self.primary_orchestrator, CPUOrchestrator):
                self.stats["cpu_tasks"] += 1
            else:
                self.stats["npu_tasks"] += 1

            if result.success:
                self.stats["successful_tasks"] += 1
            else:
                self.stats["failed_tasks"] += 1

            execution_time = time.time() - start_time
            self.stats["total_execution_time"] += execution_time

            return result

        except Exception as e:
            logger.warning(
                f"⚠️  Primary orchestrator failed for task {task.task_id}: {e}"
            )

            # Try fallback if available
            if self.fallback_orchestrator:
                logger.info(f"🔄 Attempting fallback for task {task.task_id}")
                self.stats["fallback_events"] += 1

                try:
                    result = await self._execute_with_orchestrator(
                        self.fallback_orchestrator, task
                    )
                    self.stats["cpu_tasks"] += 1

                    if result.success:
                        self.stats["successful_tasks"] += 1
                    else:
                        self.stats["failed_tasks"] += 1

                    execution_time = time.time() - start_time
                    self.stats["total_execution_time"] += execution_time

                    # Mark as fallback execution
                    result.agent_used += " (fallback)"
                    return result

                except Exception as fallback_error:
                    logger.error(
                        f"❌ Fallback orchestrator also failed: {fallback_error}"
                    )

            # If all else fails, return error result
            self.stats["failed_tasks"] += 1
            execution_time = time.time() - start_time
            self.stats["total_execution_time"] += execution_time

            return OrchestrationResult(
                task_id=task.task_id,
                agent_used="error",
                execution_time_ms=execution_time * 1000,
                success=False,
                performance_score=0.0,
                memory_peak_mb=0,
                cpu_utilization=0.0,
            )

    async def _execute_with_orchestrator(
        self, orchestrator, task: TaskRequest
    ) -> OrchestrationResult:
        """Execute task with specific orchestrator"""
        if hasattr(orchestrator, "execute_task"):
            return await orchestrator.execute_task(task)
        elif hasattr(orchestrator, "process_task"):
            return await orchestrator.process_task(task)
        else:
            # Fallback for orchestrators with different interfaces
            raise Exception(
                f"Orchestrator {type(orchestrator)} has unsupported interface"
            )

    async def process_workflow(
        self, tasks: List[TaskRequest]
    ) -> List[OrchestrationResult]:
        """Process multiple tasks with intelligent scheduling and fallback"""
        logger.info(f"🚀 Processing workflow with {len(tasks)} tasks")
        start_time = time.time()

        # Use primary orchestrator's workflow processing if available
        try:
            if hasattr(self.primary_orchestrator, "process_workflow"):
                results = await self.primary_orchestrator.process_workflow(tasks)
            else:
                # Process tasks individually
                results = []
                for task in tasks:
                    result = await self.execute_task(task)
                    results.append(result)

            workflow_time = time.time() - start_time
            success_count = sum(1 for r in results if r.success)

            logger.info(
                f"✅ Workflow completed: {success_count}/{len(tasks)} successful in {workflow_time:.2f}s"
            )
            return results

        except Exception as e:
            logger.error(f"❌ Workflow processing failed: {e}")

            # Fallback to individual task processing
            if self.fallback_orchestrator:
                logger.info("🔄 Attempting workflow fallback")
                self.stats["fallback_events"] += 1

                results = []
                for task in tasks:
                    try:
                        result = await self._execute_with_orchestrator(
                            self.fallback_orchestrator, task
                        )
                        result.agent_used += " (workflow_fallback)"
                        results.append(result)
                    except Exception as task_error:
                        logger.error(
                            f"❌ Fallback task {task.task_id} failed: {task_error}"
                        )
                        results.append(
                            OrchestrationResult(
                                task_id=task.task_id,
                                agent_used="error",
                                execution_time_ms=0,
                                success=False,
                                performance_score=0.0,
                                memory_peak_mb=0,
                                cpu_utilization=0.0,
                            )
                        )

                return results

            return []

    def get_system_status(self) -> SystemStatus:
        """Get real-time system status"""
        uptime = time.time() - self.start_time
        success_rate = (
            self.stats["successful_tasks"] / max(self.stats["total_tasks"], 1)
        ) * 100

        # Calculate performance ops/sec
        if self.stats["total_execution_time"] > 0:
            ops_per_sec = self.stats["total_tasks"] / self.stats["total_execution_time"]
        else:
            ops_per_sec = 0.0

        # Get current resource usage
        try:
            import psutil

            memory_usage = psutil.Process().memory_info().rss / (1024 * 1024)
            cpu_utilization = psutil.cpu_percent(interval=0.1)
        except:
            memory_usage = 0.0
            cpu_utilization = 0.0

        return SystemStatus(
            orchestrator_mode=self.current_mode,
            hardware_detected=True,
            npu_available=self.capabilities.has_npu and NPU_AVAILABLE,
            performance_ops_sec=ops_per_sec,
            memory_usage_mb=memory_usage,
            cpu_utilization=cpu_utilization,
            active_tasks=0,  # Would need to track active tasks
            success_rate=success_rate,
            uptime_seconds=uptime,
        )

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        status = self.get_system_status()

        return {
            "unified_config": asdict(self.config),
            "hardware_capabilities": asdict(self.capabilities),
            "system_status": asdict(status),
            "performance_stats": {
                "total_tasks": self.stats["total_tasks"],
                "successful_tasks": self.stats["successful_tasks"],
                "failed_tasks": self.stats["failed_tasks"],
                "success_rate_percent": status.success_rate,
                "average_ops_per_sec": status.performance_ops_sec,
                "npu_task_percentage": (
                    self.stats["npu_tasks"] / max(self.stats["total_tasks"], 1)
                )
                * 100,
                "cpu_task_percentage": (
                    self.stats["cpu_tasks"] / max(self.stats["total_tasks"], 1)
                )
                * 100,
                "fallback_events": self.stats["fallback_events"],
                "total_execution_time": self.stats["total_execution_time"],
                "uptime_seconds": status.uptime_seconds,
            },
            "orchestrator_info": {
                "primary_type": type(self.primary_orchestrator).__name__,
                "fallback_available": self.fallback_orchestrator is not None,
                "fallback_type": (
                    type(self.fallback_orchestrator).__name__
                    if self.fallback_orchestrator
                    else None
                ),
            },
        }

    def save_performance_report(self, filepath: str):
        """Save performance report to file"""
        report = self.get_performance_report()
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"📊 Performance report saved to {filepath}")


async def main():
    """Demo and testing function"""
    print("🚀 Unified Orchestrator System v1.0")
    print("=" * 60)

    # Test different modes
    test_modes = [None, "npu", "cpu_optimized", "cpu_basic"]

    for test_mode in test_modes:
        print(f"\n🧪 Testing mode: {test_mode or 'AUTO-DETECT'}")
        print("-" * 40)

        # Initialize orchestrator
        orchestrator = UnifiedOrchestrator(force_mode=test_mode)

        # Create sample tasks
        tasks = [
            TaskRequest(
                task_id=f"task_{test_mode or 'auto'}_001",
                agent_type="security",
                prompt="audit system vulnerabilities and compliance",
                priority=1,
                complexity_score=0.7,
                estimated_duration=2.0,
                memory_requirement=100,
            ),
            TaskRequest(
                task_id=f"task_{test_mode or 'auto'}_002",
                agent_type="architect",
                prompt="design scalable microservices architecture",
                priority=2,
                complexity_score=0.9,
                estimated_duration=3.0,
                memory_requirement=150,
            ),
            TaskRequest(
                task_id=f"task_{test_mode or 'auto'}_003",
                agent_type="optimizer",
                prompt="optimize database query performance",
                priority=1,
                complexity_score=0.6,
                estimated_duration=1.5,
                memory_requirement=80,
            ),
        ]

        # Process workflow
        start_time = time.time()
        results = await orchestrator.process_workflow(tasks)
        total_time = time.time() - start_time

        # Display results
        print(f"📊 Results ({total_time:.2f}s total):")
        for result in results:
            status = "✅" if result.success else "❌"
            print(
                f"{status} {result.task_id}: {result.agent_used} "
                f"({result.execution_time_ms:.1f}ms, {result.memory_peak_mb:.1f}MB)"
            )

        # System status
        status = orchestrator.get_system_status()
        print(f"\n📈 System Status:")
        print(f"Mode: {status.orchestrator_mode}")
        print(f"Performance: {status.performance_ops_sec:.1f} ops/sec")
        print(f"Success Rate: {status.success_rate:.1f}%")
        print(f"NPU Available: {'✅' if status.npu_available else '❌'}")

        # Save report for auto-detect mode
        if test_mode is None:
            report_path = f"unified_orchestrator_report.json"
            orchestrator.save_performance_report(report_path)
            print(f"💾 Report saved to: {report_path}")

        print()

    print("🎉 All mode tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
