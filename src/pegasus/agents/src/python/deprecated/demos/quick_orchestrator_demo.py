#!/usr/bin/env python3
"""
Quick Orchestrator Demo v1.0
Simple demonstration of best orchestrator selection

HOW TO RUN AND DYNAMICALLY SELECT BEST:
1. python3 quick_orchestrator_demo.py --auto
2. python3 quick_orchestrator_demo.py --benchmark
3. python3 quick_orchestrator_demo.py --compare-all
"""

import asyncio
import argparse
import time
from typing import Dict, Any

# Import orchestrator systems
try:
    from unified_orchestrator_system import UnifiedOrchestrator, TaskRequest, OrchestrationResult
    from cpu_orchestrator_fallback import CPUOrchestrator
    from hardware_detection_unified import HardwareDetector
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

async def run_simple_demo():
    """Simple demo showing automatic best selection"""
    print("🚀 Quick Orchestrator Demo - Automatic Best Selection")
    print("=" * 60)

    # 1. Hardware Detection
    print("🔍 Step 1: Hardware Detection")
    detector = HardwareDetector()
    caps = detector.get_capabilities()
    config = detector.get_orchestration_config()

    print(f"   System: {caps.cpu_brand}")
    print(f"   Performance Tier: {caps.performance_tier.upper()}")
    print(f"   NPU Available: {'✅' if caps.has_npu else '❌'}")
    print(f"   OpenVINO: {'✅' if caps.openvino_available else '❌'}")
    print(f"   Recommended Mode: {caps.orchestrator_mode}")

    # 2. Orchestrator Selection
    print(f"\n⚙️  Step 2: Orchestrator Initialization")

    if caps.orchestrator_mode == 'npu' and caps.has_npu:
        print("   🎯 Selecting: Unified Orchestrator (NPU mode)")
        orchestrator = UnifiedOrchestrator()
    else:
        print("   🎯 Selecting: CPU Orchestrator (optimized)")
        orchestrator = CPUOrchestrator()

    # 3. Quick Test
    print(f"\n🧪 Step 3: Performance Test")

    test_tasks = [
        TaskRequest(
            task_id="demo_001",
            agent_type="optimizer",
            prompt="optimize system performance",
            priority=1,
            complexity_score=0.5,
            estimated_duration=1.0,
            memory_requirement=50
        ),
        TaskRequest(
            task_id="demo_002",
            agent_type="security",
            prompt="security audit analysis",
            priority=1,
            complexity_score=0.7,
            estimated_duration=1.5,
            memory_requirement=75
        )
    ]

    start_time = time.time()

    if hasattr(orchestrator, 'process_workflow'):
        results = await orchestrator.process_workflow(test_tasks)
    else:
        results = []
        for task in test_tasks:
            result = await orchestrator.execute_task(task)
            results.append(result)

    total_time = time.time() - start_time
    successful = sum(1 for r in results if r.success)

    print(f"   📊 Results: {successful}/{len(results)} successful in {total_time:.2f}s")
    print(f"   ⚡ Performance: {len(results)/total_time:.1f} tasks/sec")

    for result in results:
        status = "✅" if result.success else "❌"
        print(f"   {status} {result.task_id}: {result.agent_used} ({result.execution_time_ms:.1f}ms)")

    # 4. Recommendation
    print(f"\n🎯 Recommendation:")
    print(f"   Best Mode: {caps.orchestrator_mode}")
    print(f"   Max Concurrent Tasks: {config.max_concurrent_tasks}")
    print(f"   Memory Limit: {config.memory_limit_mb} MB")
    print(f"   Max Concurrent: {config.max_concurrent_tasks} tasks")

async def run_benchmark():
    """Quick benchmark of available orchestrators"""
    print("🏁 Quick Orchestrator Benchmark")
    print("=" * 40)

    # Test tasks
    benchmark_tasks = [
        TaskRequest(
            task_id=f"bench_{i}",
            agent_type="optimizer",
            prompt="benchmark test task",
            priority=1,
            complexity_score=0.5,
            estimated_duration=1.0,
            memory_requirement=50
        )
        for i in range(5)
    ]

    results = {}

    # Test CPU Orchestrator
    print("📊 Testing CPU Orchestrator...")
    cpu_orchestrator = CPUOrchestrator()
    start_time = time.time()
    cpu_results = await cpu_orchestrator.process_workflow(benchmark_tasks)
    cpu_time = time.time() - start_time
    cpu_success = sum(1 for r in cpu_results if r.success)
    cpu_score = (cpu_success / len(benchmark_tasks)) * (len(benchmark_tasks) / cpu_time)
    results['CPU Orchestrator'] = cpu_score

    # Test Unified Orchestrator
    print("📊 Testing Unified Orchestrator...")
    unified_orchestrator = UnifiedOrchestrator()
    start_time = time.time()
    unified_results = await unified_orchestrator.process_workflow(benchmark_tasks)
    unified_time = time.time() - start_time
    unified_success = sum(1 for r in unified_results if r.success)
    unified_score = (unified_success / len(benchmark_tasks)) * (len(benchmark_tasks) / unified_time)
    results['Unified Orchestrator'] = unified_score

    # Display results
    print(f"\n🏆 Benchmark Results:")
    for name, score in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"   {name}: {score:.2f} score")

    best = max(results.items(), key=lambda x: x[1])
    print(f"\n🥇 Winner: {best[0]} (score: {best[1]:.2f})")

    return results

async def run_comparison():
    """Compare all orchestrator modes"""
    print("⚖️  Complete Orchestrator Comparison")
    print("=" * 50)

    detector = HardwareDetector()
    caps = detector.get_capabilities()

    print(f"System: {caps.cpu_brand} ({caps.cpu_cores} cores, {caps.total_memory_gb:.1f}GB)")
    print(f"NPU: {'✅' if caps.has_npu else '❌'}, OpenVINO: {'✅' if caps.openvino_available else '❌'}")

    # Test different modes
    modes = ['auto', 'npu', 'cpu_optimized', 'cpu_basic']
    test_task = TaskRequest(
        task_id="comparison_test",
        agent_type="optimizer",
        prompt="performance comparison test",
        priority=1,
        complexity_score=0.5,
        estimated_duration=1.0,
        memory_requirement=50
    )

    results = {}

    for mode in modes:
        print(f"\n🧪 Testing {mode} mode...")

        try:
            if mode == 'auto':
                # Use hardware detection recommendation
                if caps.orchestrator_mode == 'npu':
                    orchestrator = UnifiedOrchestrator()
                else:
                    orchestrator = CPUOrchestrator()
            elif mode in ['npu', 'cpu_optimized', 'cpu_basic']:
                orchestrator = UnifiedOrchestrator(force_mode=mode)

            start_time = time.time()
            result = await orchestrator.execute_task(test_task)
            execution_time = time.time() - start_time

            if result.success:
                score = 1.0 / execution_time
                results[mode] = score
                print(f"   ✅ Success: {execution_time*1000:.1f}ms (score: {score:.2f})")
            else:
                results[mode] = 0.0
                print(f"   ❌ Failed")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[mode] = 0.0

    # Show comparison
    print(f"\n📊 Mode Comparison:")
    for mode, score in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"   {mode}: {score:.2f}")

    best_mode = max(results.items(), key=lambda x: x[1])
    print(f"\n🏆 Best Mode: {best_mode[0]} (score: {best_mode[1]:.2f})")

    return results

async def main():
    parser = argparse.ArgumentParser(description='Quick Orchestrator Demo')
    parser.add_argument('--auto', action='store_true', help='Run automatic selection demo (default)')
    parser.add_argument('--benchmark', action='store_true', help='Run orchestrator benchmark')
    parser.add_argument('--compare-all', action='store_true', help='Compare all modes')

    args = parser.parse_args()

    if args.benchmark:
        await run_benchmark()
    elif args.compare_all:
        await run_comparison()
    else:
        # Default to auto mode when no specific flags are provided
        await run_simple_demo()

if __name__ == "__main__":
    print("🚀 HOW TO RUN AND DYNAMICALLY SELECT BEST ORCHESTRATOR:")
    print("1. python3 quick_orchestrator_demo.py          # Auto mode (default)")
    print("2. python3 quick_orchestrator_demo.py --benchmark")
    print("3. python3 quick_orchestrator_demo.py --compare-all")
    print()

    asyncio.run(main())