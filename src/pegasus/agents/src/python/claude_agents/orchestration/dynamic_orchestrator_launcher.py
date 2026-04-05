#!/usr/bin/env python3
"""
Dynamic Orchestrator Launcher v1.0
Automatic best orchestrator selection with real-time optimization

Provides intelligent orchestrator management:
- Real-time hardware monitoring and performance assessment
- Dynamic orchestrator switching based on workload and system state
- Automatic fallback with performance preservation
- Zero-configuration optimal performance selection
- Integration with all orchestrator systems (NPU, CPU, Unified)

Usage:
    python3 dynamic_orchestrator_launcher.py [--mode auto|npu|cpu] [--monitor] [--benchmark]
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Import our orchestrator systems
try:
    from cpu_orchestrator_fallback import CPUOrchestrator
    from hardware_detection_unified import HardwareDetector
    from unified_orchestrator_system import (
        OrchestrationResult,
        TaskRequest,
        UnifiedOrchestrator,
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all orchestrator modules are available")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("orchestrator_launcher.log"),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class LauncherConfig:
    """Dynamic launcher configuration"""

    mode: str  # 'auto', 'npu', 'cpu_optimized', 'cpu_basic'
    monitoring_enabled: bool
    monitoring_interval: float
    performance_threshold: float
    auto_switch_enabled: bool
    fallback_enabled: bool
    benchmark_on_start: bool


@dataclass
class PerformanceMetrics:
    """Real-time performance metrics"""

    ops_per_sec: float
    avg_response_time_ms: float
    success_rate: float
    memory_usage_mb: float
    cpu_utilization: float
    temperature_celsius: Optional[float]
    orchestrator_mode: str
    timestamp: float


class DynamicOrchestratorLauncher:
    """
    Dynamic orchestrator launcher with real-time optimization

    Features:
    - Automatic best orchestrator selection based on real-time performance
    - Dynamic switching between NPU/CPU modes based on workload
    - Continuous performance monitoring and optimization
    - Automatic fallback with seamless performance preservation
    - Zero-configuration optimal performance selection
    """

    def __init__(self, config: LauncherConfig):
        self.config = config
        self.current_orchestrator = None
        self.hardware_detector = HardwareDetector()
        self.capabilities = self.hardware_detector.get_capabilities()

        # Performance tracking
        self.performance_history = []
        self.current_metrics = None
        self.switch_count = 0
        self.start_time = time.time()

        # Available orchestrators
        self.available_orchestrators = {}
        self.orchestrator_performance = {}

        # Monitoring
        self.monitoring_task = None
        self.shutdown_event = asyncio.Event()

        # Initialize orchestrators
        self._initialize_orchestrators()

        logger.info(f"🚀 Dynamic Orchestrator Launcher initialized")
        logger.info(
            f"Hardware: {self.capabilities.performance_tier} tier, NPU: {'✅' if self.capabilities.has_npu else '❌'}"
        )

    def _initialize_orchestrators(self):
        """Initialize all available orchestrators"""
        try:
            # Initialize unified orchestrator (handles NPU/CPU automatically)
            self.available_orchestrators["unified"] = UnifiedOrchestrator()
            self.orchestrator_performance["unified"] = {"score": 1.0, "stability": 1.0}
            logger.info("✅ Unified orchestrator initialized")

            # Initialize CPU-only orchestrator as backup
            self.available_orchestrators["cpu"] = CPUOrchestrator()
            self.orchestrator_performance["cpu"] = {"score": 0.8, "stability": 0.95}
            logger.info("✅ CPU orchestrator initialized")

            # Set initial orchestrator based on mode
            if self.config.mode == "auto":
                self.current_orchestrator = self._select_best_orchestrator()
            elif self.config.mode in ["npu", "cpu_optimized", "cpu_basic"]:
                self.current_orchestrator = self.available_orchestrators["unified"]
            else:
                self.current_orchestrator = self.available_orchestrators["cpu"]

            logger.info(
                f"🎯 Selected orchestrator: {type(self.current_orchestrator).__name__}"
            )

        except Exception as e:
            logger.error(f"❌ Orchestrator initialization failed: {e}")
            # Fallback to CPU orchestrator
            self.current_orchestrator = CPUOrchestrator()
            self.available_orchestrators["fallback"] = self.current_orchestrator

    def _select_best_orchestrator(self) -> Any:
        """Select the best orchestrator based on current conditions"""
        best_orchestrator = None
        best_score = 0.0

        for name, orchestrator in self.available_orchestrators.items():
            perf = self.orchestrator_performance[name]

            # Calculate composite score
            score = perf["score"] * perf["stability"]

            # Adjust for hardware capabilities
            if name == "unified" and self.capabilities.has_npu:
                score *= 1.5  # Prefer unified with NPU
            elif name == "cpu" and not self.capabilities.has_npu:
                score *= 1.2  # Prefer CPU-only on non-NPU systems

            # Adjust for current system load
            try:
                import psutil

                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_percent = psutil.virtual_memory().percent

                if cpu_percent > 80:
                    score *= 0.8  # Reduce score under high CPU load
                if memory_percent > 85:
                    score *= 0.7  # Reduce score under high memory pressure
            except:
                pass

            if score > best_score:
                best_score = score
                best_orchestrator = orchestrator

        logger.info(f"📊 Best orchestrator selected with score: {best_score:.2f}")
        return best_orchestrator or self.available_orchestrators["cpu"]

    async def execute_task(self, task: TaskRequest) -> OrchestrationResult:
        """Execute task with dynamic orchestrator selection"""
        start_time = time.time()

        try:
            # Execute with current orchestrator
            result = await self.current_orchestrator.execute_task(task)

            # Update performance metrics
            execution_time = time.time() - start_time
            self._update_performance_metrics(result, execution_time)

            # Check if orchestrator switch is needed
            if self.config.auto_switch_enabled:
                await self._check_orchestrator_switch()

            return result

        except Exception as e:
            logger.warning(f"⚠️ Current orchestrator failed: {e}")

            # Try fallback orchestrator
            if self.config.fallback_enabled:
                logger.info("🔄 Attempting fallback orchestrator")
                fallback_orchestrator = self._get_fallback_orchestrator()

                if (
                    fallback_orchestrator
                    and fallback_orchestrator != self.current_orchestrator
                ):
                    try:
                        result = await fallback_orchestrator.execute_task(task)

                        # Switch to fallback if successful
                        self.current_orchestrator = fallback_orchestrator
                        self.switch_count += 1
                        logger.info(f"✅ Switched to fallback orchestrator")

                        execution_time = time.time() - start_time
                        self._update_performance_metrics(result, execution_time)
                        return result

                    except Exception as fallback_error:
                        logger.error(
                            f"❌ Fallback orchestrator also failed: {fallback_error}"
                        )

            # Return error result if all orchestrators fail
            return OrchestrationResult(
                task_id=task.task_id,
                agent_used="error",
                execution_time_ms=(time.time() - start_time) * 1000,
                success=False,
                performance_score=0.0,
                memory_peak_mb=0,
                cpu_utilization=0.0,
            )

    def _get_fallback_orchestrator(self) -> Optional[Any]:
        """Get the best fallback orchestrator"""
        current_type = type(self.current_orchestrator).__name__

        # Return different orchestrator type as fallback
        for name, orchestrator in self.available_orchestrators.items():
            if type(orchestrator).__name__ != current_type:
                return orchestrator

        return None

    async def process_workflow(
        self, tasks: List[TaskRequest]
    ) -> List[OrchestrationResult]:
        """Process workflow with dynamic optimization"""
        logger.info(f"🚀 Processing workflow with {len(tasks)} tasks")
        start_time = time.time()

        # Pre-workflow orchestrator selection
        if self.config.auto_switch_enabled:
            await self._check_orchestrator_switch()

        try:
            # Use current orchestrator's workflow processing if available
            if hasattr(self.current_orchestrator, "process_workflow"):
                results = await self.current_orchestrator.process_workflow(tasks)
            else:
                # Process tasks individually with dynamic selection
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
            return []

    def _update_performance_metrics(
        self, result: OrchestrationResult, execution_time: float
    ):
        """Update performance metrics for current orchestrator"""
        try:
            import psutil

            memory_usage = psutil.Process().memory_info().rss / (1024 * 1024)
            cpu_utilization = psutil.cpu_percent(interval=0.1)

            # Try to get temperature
            temperature = None
            try:
                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for sensor_name, sensor_list in temps.items():
                            if sensor_list:
                                temperature = sensor_list[0].current
                                break
            except:
                pass

            # Calculate performance metrics
            ops_per_sec = 1.0 / execution_time if execution_time > 0 else 0.0

            metrics = PerformanceMetrics(
                ops_per_sec=ops_per_sec,
                avg_response_time_ms=result.execution_time_ms,
                success_rate=1.0 if result.success else 0.0,
                memory_usage_mb=memory_usage,
                cpu_utilization=cpu_utilization,
                temperature_celsius=temperature,
                orchestrator_mode=type(self.current_orchestrator).__name__,
                timestamp=time.time(),
            )

            self.current_metrics = metrics
            self.performance_history.append(metrics)

            # Keep only recent history (last 100 measurements)
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]

            # Update orchestrator performance score
            self._update_orchestrator_score(result.success, execution_time)

        except Exception as e:
            logger.debug(f"Performance metrics update failed: {e}")

    def _update_orchestrator_score(self, success: bool, execution_time: float):
        """Update performance score for current orchestrator"""
        current_name = None
        for name, orchestrator in self.available_orchestrators.items():
            if orchestrator == self.current_orchestrator:
                current_name = name
                break

        if current_name and current_name in self.orchestrator_performance:
            perf = self.orchestrator_performance[current_name]

            # Update score based on performance
            if success:
                # Reward fast execution
                time_score = min(1.0, 1.0 / (execution_time + 0.1))
                perf["score"] = perf["score"] * 0.9 + time_score * 0.1
                perf["stability"] = min(1.0, perf["stability"] * 0.95 + 0.05)
            else:
                # Penalize failures
                perf["score"] *= 0.8
                perf["stability"] *= 0.9

    async def _check_orchestrator_switch(self):
        """Check if orchestrator should be switched for better performance"""
        if len(self.performance_history) < 5:
            return  # Need enough data

        # Calculate recent performance
        recent_metrics = self.performance_history[-5:]
        avg_ops_per_sec = sum(m.ops_per_sec for m in recent_metrics) / len(
            recent_metrics
        )
        avg_success_rate = sum(m.success_rate for m in recent_metrics) / len(
            recent_metrics
        )

        # Check if performance is below threshold
        if (
            avg_success_rate < 0.8
            or avg_ops_per_sec < self.config.performance_threshold
        ):
            logger.info(
                f"📉 Performance below threshold: {avg_ops_per_sec:.1f} ops/sec, {avg_success_rate*100:.1f}% success"
            )

            # Select potentially better orchestrator
            better_orchestrator = self._select_best_orchestrator()

            if better_orchestrator != self.current_orchestrator:
                logger.info(f"🔄 Switching orchestrator for better performance")
                self.current_orchestrator = better_orchestrator
                self.switch_count += 1

    async def start_monitoring(self):
        """Start real-time performance monitoring"""
        if not self.config.monitoring_enabled:
            return

        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("📊 Performance monitoring started")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while not self.shutdown_event.is_set():
            try:
                # Log current status
                if self.current_metrics:
                    logger.info(
                        f"📈 {self.current_metrics.orchestrator_mode}: "
                        f"{self.current_metrics.ops_per_sec:.1f} ops/sec, "
                        f"{self.current_metrics.success_rate*100:.1f}% success, "
                        f"{self.current_metrics.memory_usage_mb:.1f}MB, "
                        f"{self.current_metrics.cpu_utilization:.1f}% CPU"
                    )

                # Check for orchestrator switch
                if self.config.auto_switch_enabled:
                    await self._check_orchestrator_switch()

                await asyncio.sleep(self.config.monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Monitoring error: {e}")
                await asyncio.sleep(self.config.monitoring_interval)

    async def benchmark_orchestrators(self) -> Dict[str, float]:
        """Benchmark all available orchestrators"""
        logger.info("🏁 Starting orchestrator benchmark")

        benchmark_tasks = [
            TaskRequest(
                task_id=f"benchmark_{i}",
                agent_type="optimizer",
                prompt="optimize system performance",
                priority=1,
                complexity_score=0.5,
                estimated_duration=1.0,
                memory_requirement=50,
            )
            for i in range(10)
        ]

        results = {}

        for name, orchestrator in self.available_orchestrators.items():
            logger.info(f"📊 Benchmarking {name} orchestrator")
            start_time = time.time()
            successful_tasks = 0

            # Temporarily switch to this orchestrator
            original_orchestrator = self.current_orchestrator
            self.current_orchestrator = orchestrator

            try:
                for task in benchmark_tasks:
                    result = await self.execute_task(task)
                    if result.success:
                        successful_tasks += 1

                total_time = time.time() - start_time
                score = (successful_tasks / len(benchmark_tasks)) * (
                    len(benchmark_tasks) / total_time
                )
                results[name] = score

                logger.info(
                    f"✅ {name}: {score:.2f} score ({successful_tasks}/{len(benchmark_tasks)} successful)"
                )

            except Exception as e:
                logger.error(f"❌ Benchmark failed for {name}: {e}")
                results[name] = 0.0
            finally:
                # Restore original orchestrator
                self.current_orchestrator = original_orchestrator

        logger.info(
            f"🏆 Benchmark complete. Best: {max(results.items(), key=lambda x: x[1])}"
        )
        return results

    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report"""
        uptime = time.time() - self.start_time

        return {
            "launcher_config": asdict(self.config),
            "hardware_capabilities": asdict(self.capabilities),
            "current_orchestrator": type(self.current_orchestrator).__name__,
            "available_orchestrators": list(self.available_orchestrators.keys()),
            "orchestrator_performance": self.orchestrator_performance,
            "current_metrics": (
                asdict(self.current_metrics) if self.current_metrics else None
            ),
            "performance_history_size": len(self.performance_history),
            "switch_count": self.switch_count,
            "uptime_seconds": uptime,
            "monitoring_active": self.monitoring_task is not None
            and not self.monitoring_task.done(),
        }

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🔄 Shutting down dynamic orchestrator launcher")

        self.shutdown_event.set()

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("✅ Shutdown complete")


def create_launcher_config(args) -> LauncherConfig:
    """Create launcher configuration from command line arguments"""
    return LauncherConfig(
        mode=args.mode,
        monitoring_enabled=args.monitor,
        monitoring_interval=5.0,  # 5 seconds
        performance_threshold=100.0,  # 100 ops/sec minimum
        auto_switch_enabled=args.mode == "auto",
        fallback_enabled=True,
        benchmark_on_start=args.benchmark,
    )


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Dynamic Orchestrator Launcher v1.0")
    parser.add_argument(
        "--mode",
        choices=["auto", "npu", "cpu_optimized", "cpu_basic"],
        default="auto",
        help="Orchestrator selection mode",
    )
    parser.add_argument(
        "--monitor", action="store_true", help="Enable real-time performance monitoring"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run orchestrator benchmarks on startup",
    )
    parser.add_argument(
        "--tasks", type=int, default=5, help="Number of test tasks to run"
    )

    args = parser.parse_args()

    print("🚀 Dynamic Orchestrator Launcher v1.0")
    print("=" * 60)

    # Create launcher
    config = create_launcher_config(args)
    launcher = DynamicOrchestratorLauncher(config)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("📡 Received shutdown signal")
        asyncio.create_task(launcher.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start monitoring if enabled
        if config.monitoring_enabled:
            await launcher.start_monitoring()

        # Run benchmark if requested
        if config.benchmark_on_start:
            benchmark_results = await launcher.benchmark_orchestrators()
            print(f"\n🏆 Benchmark Results:")
            for name, score in sorted(
                benchmark_results.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {name}: {score:.2f}")

        # Run test tasks
        print(f"\n🧪 Running {args.tasks} test tasks...")

        test_tasks = [
            TaskRequest(
                task_id=f"test_task_{i}",
                agent_type=["security", "architect", "optimizer", "debugger"][i % 4],
                prompt=f"test task {i} with dynamic orchestrator selection",
                priority=1,
                complexity_score=0.5 + (i % 3) * 0.2,
                estimated_duration=1.0 + (i % 2),
                memory_requirement=50 + (i % 5) * 20,
            )
            for i in range(args.tasks)
        ]

        # Process tasks
        start_time = time.time()
        results = await launcher.process_workflow(test_tasks)
        total_time = time.time() - start_time

        # Display results
        print(f"\n📊 Results ({total_time:.2f}s total):")
        success_count = 0
        for result in results:
            status = "✅" if result.success else "❌"
            if result.success:
                success_count += 1
            print(
                f"{status} {result.task_id}: {result.agent_used} "
                f"({result.execution_time_ms:.1f}ms)"
            )

        print(f"\n📈 Summary:")
        print(
            f"Success Rate: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)"
        )
        print(f"Average Speed: {len(results)/total_time:.1f} tasks/sec")
        print(f"Orchestrator Switches: {launcher.switch_count}")

        # Show status report
        status = launcher.get_status_report()
        print(f"\n🎯 Current Orchestrator: {status['current_orchestrator']}")
        print(
            f"Available Orchestrators: {', '.join(status['available_orchestrators'])}"
        )
        if status["current_metrics"]:
            metrics = status["current_metrics"]
            print(
                f"Current Performance: {metrics['ops_per_sec']:.1f} ops/sec, "
                f"{metrics['success_rate']*100:.1f}% success"
            )

        # Save status report
        report_path = "dynamic_orchestrator_status.json"
        with open(report_path, "w") as f:
            json.dump(status, f, indent=2)
        print(f"💾 Status report saved to: {report_path}")

        # Keep monitoring running if enabled
        if config.monitoring_enabled and not launcher.shutdown_event.is_set():
            print(f"\n📊 Monitoring active (press Ctrl+C to stop)...")
            await launcher.shutdown_event.wait()

    except KeyboardInterrupt:
        print("\n🔄 Shutdown requested")
    except Exception as e:
        logger.error(f"❌ Launcher error: {e}")
    finally:
        await launcher.shutdown()
        print("👋 Dynamic Orchestrator Launcher stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
