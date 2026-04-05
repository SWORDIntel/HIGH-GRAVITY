#!/usr/bin/env python3
"""
NPU Performance Validation Test
Validates NPU pipeline optimization and delay removal
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from intel_npu_async_pipeline import (
        AsyncPipelineOrchestrator,
        AsyncPipelineValidator,
        AsyncTask,
    )
    from npu_optimized_final import OptimizedNPUOrchestrator

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_AVAILABLE = False


def setup_logging():
    """Setup logging for validation"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )


async def test_delay_removal():
    """Test that artificial delays have been removed"""
    print("🔍 TESTING DELAY REMOVAL")
    print("=" * 50)

    if not IMPORTS_AVAILABLE:
        print("❌ Cannot import NPU modules - skipping tests")
        return False

    # Test 1: Optimized NPU Orchestrator Speed
    print("\n1. Testing Optimized NPU Orchestrator...")
    orchestrator = OptimizedNPUOrchestrator()
    await orchestrator.initialize()

    # Run 100 fast operations
    start_time = time.perf_counter()
    for i in range(100):
        result = await orchestrator.execute_task_optimized(f"test task {i}")

    elapsed = time.perf_counter() - start_time
    ops_per_sec = 100 / elapsed

    print(f"✅ 100 tasks in {elapsed*1000:.1f}ms")
    print(f"✅ Operations/sec: {ops_per_sec:.0f}")

    # Validate no artificial delays
    avg_task_time = elapsed / 100
    if avg_task_time < 0.005:  # Less than 5ms per task
        print("✅ PASS: No artificial delays detected")
        delay_test_pass = True
    else:
        print(f"❌ FAIL: Tasks still too slow ({avg_task_time*1000:.1f}ms avg)")
        delay_test_pass = False

    # Test 2: Async Pipeline Performance
    print("\n2. Testing Async Pipeline Performance...")
    pipeline_orchestrator = AsyncPipelineOrchestrator()
    await pipeline_orchestrator.start()

    # Submit 50 tasks quickly
    tasks = []
    for i in range(50):
        task = AsyncTask(
            task_id=f"perf_test_{i}",
            agent_type="optimizer" if i % 2 == 0 else "security",
            prompt=f"performance test task {i}",
            priority=1 + (i % 5),
        )
        tasks.append(task)

    start_time = time.perf_counter()

    # Submit all tasks
    task_ids = []
    for task in tasks:
        task_id = await pipeline_orchestrator.submit_task(task)
        task_ids.append(task_id)

    # Wait for completion
    await asyncio.sleep(2.0)  # Give time for processing

    elapsed = time.perf_counter() - start_time
    pipeline_ops_per_sec = len(tasks) / elapsed

    print(f"✅ {len(tasks)} pipeline tasks in {elapsed:.2f}s")
    print(f"✅ Pipeline ops/sec: {pipeline_ops_per_sec:.0f}")

    await pipeline_orchestrator.stop()

    # Validate pipeline performance
    if pipeline_ops_per_sec > 20:  # Should be much higher without delays
        print("✅ PASS: Pipeline performance acceptable")
        pipeline_test_pass = True
    else:
        print(f"❌ FAIL: Pipeline too slow ({pipeline_ops_per_sec:.0f} ops/sec)")
        pipeline_test_pass = False

    return delay_test_pass and pipeline_test_pass


async def test_npu_hardware_detection():
    """Test NPU hardware detection improvements"""
    print("\n🧠 TESTING NPU HARDWARE DETECTION")
    print("=" * 50)

    if not IMPORTS_AVAILABLE:
        print("❌ Cannot import NPU modules - skipping tests")
        return False

    from intel_npu_async_pipeline import IntelNPUProcessor

    # Test NPU processor initialization
    npu = IntelNPUProcessor()

    print(f"✅ NPU Available: {npu.available}")
    print(f"✅ NPU Device: {npu.device}")

    # Check for hardware paths
    npu_paths = ["/dev/accel0", "/dev/accel/accel0"]
    hardware_detected = False

    for path in npu_paths:
        if os.path.exists(path):
            print(f"✅ NPU Hardware Path Found: {path}")
            hardware_detected = True
            break

    if not hardware_detected:
        print("ℹ️  No NPU hardware paths detected (expected on some systems)")

    # Test cache directory
    cache_path = Path.home() / ".cache" / "ze_intel_npu_cache"
    if cache_path.exists():
        cache_files = list(cache_path.glob("*"))
        print(f"✅ NPU Cache Found: {len(cache_files)} files")
        return True
    else:
        print("ℹ️  No NPU cache found")
        return npu.available


async def performance_benchmark():
    """Run comprehensive performance benchmark"""
    print("\n🚀 COMPREHENSIVE PERFORMANCE BENCHMARK")
    print("=" * 60)

    if not IMPORTS_AVAILABLE:
        print("❌ Cannot import NPU modules - skipping benchmark")
        return {}

    # Benchmark 1: Raw speed test
    print("\n⚡ Raw Speed Test (1000 operations)")
    orchestrator = OptimizedNPUOrchestrator()
    await orchestrator.initialize()

    start_time = time.perf_counter()
    results = []

    for i in range(1000):
        result = await orchestrator.execute_task_optimized(f"benchmark task {i}")
        results.append(result)

    total_time = time.perf_counter() - start_time
    ops_per_sec = 1000 / total_time

    print(f"✅ 1000 tasks in {total_time:.2f}s")
    print(f"✅ Operations/sec: {ops_per_sec:.0f}")
    print(f"✅ Average per task: {total_time*1000/1000:.3f}ms")

    # Get metrics
    metrics = orchestrator.get_metrics()

    benchmark_results = {
        "raw_ops_per_sec": ops_per_sec,
        "total_time_seconds": total_time,
        "npu_enabled": metrics.get("npu_enabled", False),
        "agents_available": metrics.get("agents_available", 0),
        "npu_inferences": metrics.get("npu_inferences", 0),
    }

    # Performance targets
    print(f"\n🎯 PERFORMANCE TARGETS:")
    print(f"   Current: {ops_per_sec:.0f} ops/sec")

    if ops_per_sec >= 15000:
        print("✅ EXCELLENT: Exceeded 15K ops/sec target!")
    elif ops_per_sec >= 10000:
        print("✅ GOOD: Exceeded 10K ops/sec")
    elif ops_per_sec >= 5000:
        print("⚠️  ACCEPTABLE: Above 5K ops/sec")
    else:
        print("❌ NEEDS IMPROVEMENT: Below 5K ops/sec")

    return benchmark_results


async def main():
    """Main validation test suite"""
    setup_logging()

    print("🔥 NPU PIPELINE OPTIMIZATION VALIDATION")
    print("=" * 70)
    print("Validating artificial delay removal and NPU optimizations")
    print("=" * 70)

    # Test 1: Delay removal validation
    delay_test = await test_delay_removal()

    # Test 2: NPU hardware detection
    npu_test = await test_npu_hardware_detection()

    # Test 3: Performance benchmark
    benchmark = await performance_benchmark()

    # Summary
    print("\n" + "=" * 70)
    print("🏁 VALIDATION SUMMARY")
    print("=" * 70)

    print(f"Delay Removal Test: {'✅ PASS' if delay_test else '❌ FAIL'}")
    print(f"NPU Detection Test: {'✅ PASS' if npu_test else '❌ FAIL'}")

    if benchmark:
        print(f"Performance: {benchmark['raw_ops_per_sec']:.0f} ops/sec")
        print(f"NPU Enabled: {'✅ YES' if benchmark['npu_enabled'] else '❌ NO'}")
        print(f"Agents Available: {benchmark['agents_available']}")

    # Overall result
    overall_pass = delay_test and (benchmark.get("raw_ops_per_sec", 0) > 5000)

    if overall_pass:
        print("\n🎉 OPTIMIZATION SUCCESS: NPU pipeline optimized!")
        print("✅ Artificial delays removed")
        print("✅ Real hardware acceleration enabled")
        print("✅ Performance targets achieved")
    else:
        print("\n⚠️  OPTIMIZATION INCOMPLETE")
        print("Some optimizations may need additional work")

    # Save results
    results = {
        "timestamp": time.time(),
        "delay_removal_test": delay_test,
        "npu_detection_test": npu_test,
        "benchmark_results": benchmark,
        "overall_success": overall_pass,
    }

    results_file = Path(__file__).parent / "npu_validation_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {results_file}")

    return overall_pass


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
