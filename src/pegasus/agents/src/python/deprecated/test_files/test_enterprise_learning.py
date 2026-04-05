#!/usr/bin/env python3
"""
Enterprise Learning System Test v1.0
Test the 5-layer enterprise architecture
"""

from enterprise_learning_orchestrator import initialize_enterprise_learning, AgentExecution, WorkflowPattern, PerformanceMetric
import uuid
import time
import sys

def test_enterprise_system():
    """Test enterprise learning system with real data"""
    print("🔥 TESTING ENTERPRISE LEARNING SYSTEM")

    # Initialize enterprise system
    orchestrator = initialize_enterprise_learning()
    if not orchestrator:
        print("❌ Failed to initialize enterprise system")
        return False

    print("✅ Enterprise system initialized")

    # Test Layer 1: Agent Executions
    print("\n📊 Testing Layer 1: Agent Executions")
    for i in range(10):
        execution = AgentExecution(
            agent_name=f"TEST_AGENT_{i % 3}",
            task_type="unit_test",
            execution_time_ms=50 + (i * 10),
            memory_usage_mb=100 + i,
            cpu_usage_percent=15.5 + i,
            success=True,
            session_id=str(uuid.uuid4()),
            user_id="test_user"
        )

        result = orchestrator.record_agent_execution(execution)
        if result:
            print(f"   ✅ Recorded execution {i+1}/10")
        else:
            print(f"   ❌ Failed execution {i+1}/10")

    # Test Layer 2: Workflow Patterns
    print("\n🔄 Testing Layer 2: Workflow Patterns")
    for i in range(5):
        pattern = WorkflowPattern(
            workflow_id=str(uuid.uuid4()),
            pattern_type="test_workflow",
            agent_sequence=[f"AGENT_{j}" for j in range(2, 5)],
            total_duration_ms=500 + (i * 100),
            success_rate=0.90 + (i * 0.02),
            complexity_score=3 + i,
            parallel_execution=i % 2 == 0
        )

        result = orchestrator.record_workflow_pattern(pattern)
        if result:
            print(f"   ✅ Recorded workflow {i+1}/5")
        else:
            print(f"   ❌ Failed workflow {i+1}/5")

    # Test Layer 4: Performance Metrics
    print("\n⚡ Testing Layer 4: Performance Metrics")
    for i in range(20):
        metric = PerformanceMetric(
            metric_category="test_performance",
            metric_name=f"test_metric_{i % 5}",
            metric_value=100.0 + i,
            unit="ms",
            agent_name=f"AGENT_{i % 3}",
            severity_level=1 + (i % 3)
        )

        result = orchestrator.record_performance_metric(metric)
        if result:
            print(f"   ✅ Recorded metric {i+1}/20")
        else:
            print(f"   ❌ Failed metric {i+1}/20")

    # Wait for background processing
    print("\n⏳ Waiting for background processing (5 seconds)...")
    time.sleep(5)

    # Check enterprise dashboard
    print("\n📈 Enterprise Dashboard:")
    try:
        dashboard = orchestrator.get_enterprise_dashboard()
        print(f"   🎯 Queue Status: {dashboard.get('queue_status', 'No data')}")
        print(f"   📊 Agent Performance: {dashboard.get('agent_performance', 'No data')}")
        print(f"   🏆 Top Agents: {len(dashboard.get('top_agents', []))} agents")
    except Exception as e:
        print(f"   ❌ Dashboard error: {e}")

    # Graceful shutdown
    orchestrator.shutdown()
    print("\n✅ Enterprise Learning System test complete")
    return True

if __name__ == "__main__":
    success = test_enterprise_system()
    sys.exit(0 if success else 1)