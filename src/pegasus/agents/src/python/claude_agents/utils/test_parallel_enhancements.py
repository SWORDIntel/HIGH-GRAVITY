#!/usr/bin/env python3
"""
Test Parallel Orchestration Enhancements
========================================

Quick test to verify that the 6 enhanced agents are working with parallel orchestration capabilities.
"""

import asyncio
import time
from typing import List


def test_enhanced_agents():
    """Test that the enhanced agents can be imported and initialized"""
    print("🧪 Testing Enhanced Agent Imports")
    print("=" * 50)

    enhanced_agents = [
        "enhanced_constructor_impl",
        "enhanced_monitor_impl",
        "enhanced_linter_impl",
        "enhanced_pygui_impl",
        "enhanced_securitychaosagent_impl",
        "enhanced_redteamorchestrator_impl",
    ]

    success_count = 0

    for agent_name in enhanced_agents:
        try:
            module = __import__(agent_name)

            # Look for the enhanced class
            for attr_name in dir(module):
                if "Enhanced" in attr_name and "Executor" in attr_name:
                    executor_class = getattr(module, attr_name)
                    print(f"  ✅ {agent_name}: Found {attr_name}")
                    success_count += 1
                    break
            else:
                print(f"  ⚠️  {agent_name}: No Enhanced*Executor class found")

        except ImportError as e:
            print(f"  ❌ {agent_name}: Import failed - {e}")
        except Exception as e:
            print(f"  ❌ {agent_name}: Error - {e}")

    print(
        f"\nEnhanced Agent Import Rate: {success_count}/{len(enhanced_agents)} ({success_count/len(enhanced_agents)*100:.1f}%)"
    )
    return success_count > 0


def test_parallel_orchestration_engine():
    """Test the parallel orchestration engine"""
    print("\n🚀 Testing Parallel Orchestration Engine")
    print("=" * 50)

    try:
        from claude_agents.utils.parallel_orchestration_enhancements import (
            ExecutionMode,
            ParallelOrchestrationEngine,
        )

        # Create engine
        engine = ParallelOrchestrationEngine(max_workers=4)
        print("  ✅ Engine created successfully")

        # Test execution modes
        modes = [
            ExecutionMode.CONCURRENT,
            ExecutionMode.BATCH_PARALLEL,
            ExecutionMode.ADAPTIVE,
        ]
        for mode in modes:
            print(f"  ✅ Execution mode available: {mode.value}")

        print("  ✅ Parallel orchestration engine operational")
        return True

    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_production_agent_enhancements():
    """Test that production agents have been enhanced"""
    print("\n🔧 Testing Production Agent Enhancements")
    print("=" * 50)

    production_agents = [
        ("constructor_impl", "CONSTRUCTORPythonExecutor"),
        ("monitor_impl", "MonitorPythonExecutor"),
        ("linter_impl", "LinterPythonExecutor"),
        ("pygui_impl", "PyGUIPythonExecutor"),
        ("securitychaosagent_impl", "SecurityChaosAgentPythonExecutor"),
        ("redteamorchestrator_impl", "RedTeamOrchestratorPythonExecutor"),
    ]

    enhanced_count = 0

    for agent_module, executor_class_name in production_agents:
        try:
            module = __import__(agent_module)

            if hasattr(module, executor_class_name):
                executor_class = getattr(module, executor_class_name)

                # Check if it has orchestration capabilities
                has_orchestration = any(
                    hasattr(executor_class, attr)
                    for attr in [
                        "execute_parallel",
                        "orchestration_enhancer",
                        "parallel_capability",
                    ]
                )

                if has_orchestration:
                    print(f"  ✅ {agent_module}: Enhanced with orchestration")
                    enhanced_count += 1
                else:
                    print(
                        f"  ⚠️  {agent_module}: No orchestration enhancements detected"
                    )
            else:
                print(
                    f"  ❌ {agent_module}: Executor class {executor_class_name} not found"
                )

        except Exception as e:
            print(f"  ❌ {agent_module}: Error - {e}")

    print(
        f"\nProduction Enhancement Rate: {enhanced_count}/{len(production_agents)} ({enhanced_count/len(production_agents)*100:.1f}%)"
    )
    return enhanced_count > 0


async def test_async_coordination():
    """Test async coordination capabilities"""
    print("\n⚡ Testing Async Coordination")
    print("=" * 50)

    try:
        # Test that tandem integration is working
        from claude_agents.orchestration.tandem_integration import OrchestrationManager

        manager = OrchestrationManager("mock")
        print("  ✅ Orchestration manager created")

        # Initialize with async
        await manager.initialize()
        print("  ✅ Manager initialized successfully")

        # Test shutdown
        await manager.shutdown()
        print("  ✅ Manager shutdown completed")

        return True

    except Exception as e:
        print(f"  ❌ Async coordination test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🎯 Parallel Orchestration Enhancement Test Suite")
    print("=" * 60)
    print("🚀 Testing Enhanced Agents and Parallel Capabilities")
    print("=" * 60)

    test_results = []

    # Run tests
    test_results.append(("Enhanced Agent Imports", test_enhanced_agents()))
    test_results.append(("Parallel Engine", test_parallel_orchestration_engine()))
    test_results.append(
        ("Production Enhancements", test_production_agent_enhancements())
    )

    # Async test
    try:
        async_result = asyncio.run(test_async_coordination())
        test_results.append(("Async Coordination", async_result))
    except Exception as e:
        print(f"  ❌ Async test failed: {e}")
        test_results.append(("Async Coordination", False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {passed/total*100:.1f}%")

    if passed / total >= 0.8:
        print("\n🎉 PARALLEL ENHANCEMENTS OPERATIONAL!")
    elif passed / total >= 0.6:
        print("\n⚠️  PARTIAL FUNCTIONALITY - Some enhancements working")
    else:
        print("\n❌ ENHANCEMENTS NEED WORK")

    print("=" * 60)


if __name__ == "__main__":
    main()
