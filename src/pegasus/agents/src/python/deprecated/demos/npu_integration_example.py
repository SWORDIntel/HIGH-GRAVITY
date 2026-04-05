#!/usr/bin/env python3
"""
NPU INTEGRATION EXAMPLE
Practical examples of using NPU acceleration with the orchestrator

This script shows how to:
1. Initialize NPU acceleration seamlessly
2. Use NPU-accelerated agent selection
3. Execute workflows with intelligent optimization
4. Monitor performance and adapt automatically
5. Handle fallbacks gracefully

Usage Examples:
  python3 npu_integration_example.py --demo basic
  python3 npu_integration_example.py --demo performance
  python3 npu_integration_example.py --demo workflow
  python3 npu_integration_example.py --benchmark
"""

import asyncio
import argparse
import logging
import time
from typing import Dict, List, Any

# Import NPU components
try:
    from npu_orchestrator_bridge import NPUOrchestratorBridge, get_npu_bridge
    from npu_accelerated_orchestrator import NPUMode
    from production_orchestrator import StandardWorkflows, CommandSet, CommandStep, ExecutionMode, Priority
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"Import error: {e}")
    print("Please ensure NPU acceleration is installed.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NPUIntegrationExample:
    """Practical examples of NPU integration"""

    def __init__(self):
        self.bridge = None

    async def initialize(self, npu_mode: NPUMode = NPUMode.ADAPTIVE) -> bool:
        """Initialize NPU bridge"""
        if not IMPORTS_AVAILABLE:
            print("❌ NPU components not available")
            return False

        print(f"🚀 Initializing NPU Bridge (mode: {npu_mode.value})...")

        self.bridge = NPUOrchestratorBridge(npu_mode, enable_fallback=True)
        success = await self.bridge.initialize()

        if success:
            status = self.bridge.get_status()
            npu_available = status.get('npu_available', False)
            agent_count = len(self.bridge.get_agent_list())

            print(f"✅ Bridge initialized successfully!")
            print(f"   NPU Hardware: {'Available' if npu_available else 'Simulated'}")
            print(f"   Available Agents: {agent_count}")
            print(f"   Mode: {npu_mode.value}")
            return True
        else:
            print("❌ Bridge initialization failed")
            return False

    async def basic_demo(self):
        """Basic NPU acceleration demonstration"""
        print("\n" + "="*50)
        print("📊 BASIC NPU ACCELERATION DEMO")
        print("="*50)

        if not await self.initialize():
            return

        # Example 1: Simple agent invocation with NPU intelligence
        print("\n1️⃣ Intelligent Agent Invocation")
        print("-" * 30)

        start_time = time.time()
        result = await self.bridge.invoke_agent(
            'director',
            'analyze_task',
            {
                'task': 'Optimize database performance for high-traffic web application',
                'context': {
                    'environment': 'production',
                    'urgency': 'high',
                    'resources': 'limited'
                }
            }
        )
        execution_time = time.time() - start_time

        print(f"Task analyzed in {execution_time*1000:.1f}ms")
        print(f"Result: {result.get('status', 'unknown')}")

        # Example 2: Workflow execution
        print("\n2️⃣ Workflow Execution")
        print("-" * 30)

        workflow_steps = [
            {'agent': 'security', 'action': 'scan_vulnerabilities'},
            {'agent': 'optimizer', 'action': 'analyze_performance'},
            {'agent': 'monitor', 'action': 'check_system_health'}
        ]

        start_time = time.time()
        workflow_result = await self.bridge.execute_workflow(workflow_steps)
        workflow_time = time.time() - start_time

        print(f"Workflow completed in {workflow_time:.2f}s")
        print(f"Status: {workflow_result.get('status', 'unknown')}")

        # Example 3: System status
        print("\n3️⃣ System Status")
        print("-" * 30)

        metrics = self.bridge.get_metrics()
        print(f"Bridge Status: Operational")

        if 'npu_metrics' in metrics:
            npu_metrics = metrics['npu_metrics']
            print(f"NPU Utilization: {npu_metrics.get('utilization', 0):.1%}")
            print(f"NPU Operations: {npu_metrics.get('inference_count', 0)}")

    async def performance_demo(self):
        """Performance comparison demonstration"""
        print("\n" + "="*50)
        print("⚡ PERFORMANCE COMPARISON DEMO")
        print("="*50)

        # Initialize both NPU and CPU-only modes
        print("Initializing NPU and CPU modes...")

        npu_bridge = NPUOrchestratorBridge(NPUMode.FULL_ACCELERATION)
        cpu_bridge = NPUOrchestratorBridge(NPUMode.DISABLED)

        await npu_bridge.initialize()
        await cpu_bridge.initialize()

        # Performance test tasks
        test_tasks = [
            "Analyze security vulnerabilities in microservices architecture",
            "Optimize database queries for reporting dashboard",
            "Deploy machine learning model to production cluster",
            "Debug performance bottleneck in authentication service",
            "Generate comprehensive system documentation"
        ]

        print(f"\n🏁 Running {len(test_tasks)} tasks on both modes...")
        print(f"{'Task':<50} {'NPU (ms)':<10} {'CPU (ms)':<10} {'Speedup'}")
        print("-" * 80)

        total_npu_time = 0
        total_cpu_time = 0

        for i, task in enumerate(test_tasks, 1):
            # NPU execution
            npu_start = time.time()
            npu_result = await npu_bridge.invoke_agent('director', 'execute_task', {'task': task})
            npu_time = time.time() - npu_start
            total_npu_time += npu_time

            # CPU execution
            cpu_start = time.time()
            cpu_result = await cpu_bridge.invoke_agent('director', 'execute_task', {'task': task})
            cpu_time = time.time() - cpu_start
            total_cpu_time += cpu_time

            speedup = cpu_time / npu_time if npu_time > 0 else 1.0

            print(f"{task[:45]:<50} {npu_time*1000:<10.1f} {cpu_time*1000:<10.1f} {speedup:.1f}x")

        # Summary
        overall_speedup = total_cpu_time / total_npu_time if total_npu_time > 0 else 1.0
        print("-" * 80)
        print(f"{'TOTAL':<50} {total_npu_time*1000:<10.1f} {total_cpu_time*1000:<10.1f} {overall_speedup:.1f}x")

        print(f"\n📊 Performance Summary:")
        print(f"   NPU Total Time: {total_npu_time*1000:.1f}ms")
        print(f"   CPU Total Time: {total_cpu_time*1000:.1f}ms")
        print(f"   Overall Speedup: {overall_speedup:.1f}x")
        print(f"   NPU Efficiency: {(overall_speedup-1)*100:.1f}% improvement")

    async def workflow_demo(self):
        """Complex workflow demonstration"""
        print("\n" + "="*50)
        print("🏗️ COMPLEX WORKFLOW DEMO")
        print("="*50)

        if not await self.initialize(NPUMode.ADAPTIVE):
            return

        print("Creating comprehensive deployment workflow...")

        # Create complex workflow
        deployment_workflow = CommandSet(
            name="production_deployment_workflow",
            description="Complete production deployment with security, testing, and monitoring",
            steps=[
                CommandStep(
                    agent="security",
                    action="security_scan",
                    params={"depth": "comprehensive", "environment": "production"}
                ),
                CommandStep(
                    agent="testbed",
                    action="run_integration_tests",
                    params={"suite": "full", "parallel": True},
                    dependencies=["security"]
                ),
                CommandStep(
                    agent="deployer",
                    action="blue_green_deployment",
                    params={"environment": "production", "strategy": "blue_green"},
                    dependencies=["testbed"]
                ),
                CommandStep(
                    agent="monitor",
                    action="setup_monitoring",
                    params={"alerts": True, "dashboards": True},
                    dependencies=["deployer"]
                ),
                CommandStep(
                    agent="infrastructure",
                    action="verify_infrastructure",
                    params={"health_checks": True, "performance_baseline": True},
                    dependencies=["monitor"]
                )
            ],
            mode=ExecutionMode.INTELLIGENT,  # Let NPU optimize
            priority=Priority.HIGH,
            timeout=300.0
        )

        print(f"Workflow: {deployment_workflow.name}")
        print(f"Steps: {len(deployment_workflow.steps)}")
        print(f"Mode: {deployment_workflow.mode.value}")

        # Execute workflow
        print("\n🚀 Executing workflow with NPU optimization...")
        start_time = time.time()

        result = await self.bridge.execute_command_set(deployment_workflow)

        execution_time = time.time() - start_time

        # Analyze results
        status = result.get('status', 'unknown')
        execution_method = result.get('execution_method', 'unknown')

        print(f"\n📊 Workflow Results:")
        print(f"   Status: {status}")
        print(f"   Execution Time: {execution_time:.2f}s")
        print(f"   Method: {execution_method}")
        print(f"   NPU Optimized: {'✅' if 'npu' in execution_method else '❌'}")

        # Show bridge metrics
        bridge_metrics = result.get('bridge_metrics', {})
        if bridge_metrics:
            perf_gain = bridge_metrics.get('performance_gain', 1.0)
            print(f"   Performance Gain: {perf_gain:.1f}x")

        # Show individual step results
        if 'results' in result:
            print(f"\n📋 Step Results:")
            for i, step_result in enumerate(result['results'][:5], 1):  # Show first 5
                step_status = 'completed' if step_result.get('status') != 'failed' else 'failed'
                print(f"   {i}. {step_status}")

    async def benchmark(self):
        """Comprehensive benchmark"""
        print("\n" + "="*50)
        print("🏆 COMPREHENSIVE BENCHMARK")
        print("="*50)

        if not await self.initialize(NPUMode.FULL_ACCELERATION):
            return

        # Benchmark parameters
        operations_per_test = 50
        concurrent_operations = 10
        test_duration = 30  # seconds

        print(f"Benchmark Parameters:")
        print(f"   Operations per test: {operations_per_test}")
        print(f"   Concurrent operations: {concurrent_operations}")
        print(f"   Test duration: {test_duration}s")

        # Benchmark 1: Agent selection speed
        print(f"\n🎯 Benchmark 1: Agent Selection Speed")
        print(f"-" * 40)

        selection_times = []
        available_agents = self.bridge.get_agent_list()[:10]  # Use first 10 agents

        for i in range(operations_per_test):
            task = f"Benchmark task {i}: optimize system performance"

            start_time = time.time()
            result = await self.bridge.invoke_agent('director', 'select_agent', {
                'task': task,
                'available_agents': available_agents
            })
            selection_time = time.time() - start_time
            selection_times.append(selection_time)

            if (i + 1) % 10 == 0:
                print(f"   Completed {i + 1}/{operations_per_test} selections...")

        avg_selection_time = sum(selection_times) / len(selection_times)
        min_selection_time = min(selection_times)
        max_selection_time = max(selection_times)

        print(f"   Average: {avg_selection_time*1000:.2f}ms")
        print(f"   Min: {min_selection_time*1000:.2f}ms")
        print(f"   Max: {max_selection_time*1000:.2f}ms")
        print(f"   Target (<1ms): {'✅' if avg_selection_time < 0.001 else '❌'}")

        # Benchmark 2: Throughput test
        print(f"\n⚡ Benchmark 2: Throughput Test")
        print(f"-" * 40)

        operations_completed = 0
        benchmark_start = time.time()

        print(f"   Running for {test_duration} seconds...")

        while time.time() - benchmark_start < test_duration:
            # Create batch of concurrent operations
            tasks = []
            for i in range(concurrent_operations):
                task = self.bridge.invoke_agent('optimizer', 'quick_operation', {
                    'operation_id': f"benchmark_{operations_completed}_{i}",
                    'timestamp': time.time()
                })
                tasks.append(task)

            # Execute batch
            await asyncio.gather(*tasks, return_exceptions=True)
            operations_completed += concurrent_operations

            # Brief pause
            await asyncio.sleep(0.001)

        benchmark_time = time.time() - benchmark_start
        throughput = operations_completed / benchmark_time

        print(f"   Operations completed: {operations_completed}")
        print(f"   Throughput: {throughput:.1f} ops/sec")
        print(f"   Target (20K ops/sec): {throughput/20000:.1%}")

        # Final metrics
        print(f"\n📊 Final System Metrics:")
        metrics = self.bridge.get_metrics()

        if 'npu_metrics' in metrics:
            npu_metrics = metrics['npu_metrics']
            print(f"   NPU Utilization: {npu_metrics.get('utilization', 0):.1%}")
            print(f"   NPU Inference Count: {npu_metrics.get('inference_count', 0)}")
            print(f"   NPU Avg Time: {npu_metrics.get('avg_inference_time_ms', 0):.2f}ms")

        if 'base_metrics' in metrics:
            base_metrics = metrics['base_metrics']
            print(f"   Total Operations: {base_metrics.get('python_msgs_processed', 0)}")
            print(f"   System Uptime: {base_metrics.get('uptime_seconds', 0):.1f}s")

async def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(description='NPU Integration Examples')
    parser.add_argument('--demo', choices=['basic', 'performance', 'workflow'],
                       help='Run specific demonstration')
    parser.add_argument('--benchmark', action='store_true',
                       help='Run comprehensive benchmark')
    parser.add_argument('--all', action='store_true',
                       help='Run all demonstrations and benchmark')

    args = parser.parse_args()

    example = NPUIntegrationExample()

    try:
        if args.demo == 'basic' or args.all:
            await example.basic_demo()

        if args.demo == 'performance' or args.all:
            await example.performance_demo()

        if args.demo == 'workflow' or args.all:
            await example.workflow_demo()

        if args.benchmark or args.all:
            await example.benchmark()

        if not any([args.demo, args.benchmark, args.all]):
            # Default: run basic demo
            print("Running basic demo (use --help for more options)")
            await example.basic_demo()

    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Unexpected error")

if __name__ == "__main__":
    asyncio.run(main())