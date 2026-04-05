#!/usr/bin/env python3
"""
Enhanced Tandem Orchestrator Examples
Demonstrates the full functionality of the enhanced orchestration system
"""

import asyncio
import json
import logging
from pathlib import Path

# Import the enhanced orchestrator
from claude_agents.orchestration.production_orchestrator import (
    CommandSet,
    CommandStep,
    CommandType,
    ExecutionMode,
    Priority,
    ProductionOrchestrator,
    StandardWorkflows,
)

# Backward compatibility
TandemOrchestrator = ProductionOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_agent_registration():
    """Demonstrate agent registration and discovery"""
    print("🤖 Agent Registration and Discovery Demo")
    print("=" * 50)

    # Initialize orchestrator
    orchestrator = TandemOrchestrator()
    success = await orchestrator.initialize()

    if not success:
        print("❌ Failed to initialize orchestrator")
        return

    # Show registration results
    total_agents = len(orchestrator.agent_registration.registered_agents)
    print(f"✅ Successfully registered {total_agents} agents")

    # Show agent discovery
    discovery = orchestrator.discover_agents()
    print(f"\n📊 Discovery Results:")
    print(f"   Total agents: {discovery['total_agents']}")
    print(
        f"   Available capabilities: {list(discovery['agents_by_capability'].keys())}"
    )

    # Show some agent details
    print(f"\n🔍 Sample Agent Details:")
    sample_agents = [
        "Director",
        "ProjectOrchestrator",
        "Security",
        "Constructor",
        "Architect",
    ]
    for agent in sample_agents:
        if agent in discovery["agent_details"]:
            details = discovery["agent_details"][agent]
            print(f"   {agent}:")
            print(f"     Description: {details['description'][:60]}...")
            print(f"     Capabilities: {details['capabilities']}")
            print(f"     Priority: {details['priority_level']}")

    return orchestrator


async def demo_execution_modes():
    """Demonstrate all 5 execution modes"""
    print("\n⚡ Execution Modes Demo")
    print("=" * 50)

    orchestrator = TandemOrchestrator()
    await orchestrator.initialize()

    execution_modes = [
        (ExecutionMode.INTELLIGENT, "🧠 Intelligent routing"),
        (ExecutionMode.SPEED_CRITICAL, "🚀 Speed critical"),
        (ExecutionMode.REDUNDANT, "🔄 Redundant execution"),
        (ExecutionMode.PYTHON_ONLY, "🐍 Python only"),
        (ExecutionMode.CONSENSUS, "🤝 Consensus required"),
    ]

    results = {}

    for mode, description in execution_modes:
        print(f"\nTesting {description}...")

        # Create a simple command set for testing
        test_command = CommandSet(
            name=f"Test {mode.value}",
            type=CommandType.WORKFLOW,
            mode=mode,
            priority=Priority.HIGH,
            steps=[
                CommandStep(
                    action="test_execution",
                    agent="Monitor",
                    payload={"test_mode": mode.value},
                )
            ],
        )

        try:
            result = await orchestrator.execute_command_set(
                test_command, use_dag_engine=False
            )
            results[mode.value] = result.get("status", "unknown")
            print(f"   Result: {result.get('status', 'unknown')}")
        except Exception as e:
            results[mode.value] = f"error: {e}"
            print(f"   Error: {e}")

    print(f"\n📈 Execution Mode Results:")
    for mode, result in results.items():
        print(f"   {mode}: {result}")


async def demo_dag_execution():
    """Demonstrate DAG-based command execution"""
    print("\n🕸️ DAG Execution Demo")
    print("=" * 50)

    orchestrator = TandemOrchestrator()
    await orchestrator.initialize()

    # Create a complex workflow with dependencies
    complex_workflow = CommandSet(
        name="Complex DAG Workflow",
        type=CommandType.CAMPAIGN,
        mode=ExecutionMode.INTELLIGENT,
        priority=Priority.HIGH,
        parallel_allowed=True,
        steps=[
            CommandStep(
                id="planning",
                action="create_plan",
                agent="Director",
                payload={"project_type": "web_application"},
            ),
            CommandStep(
                id="architecture",
                action="design_architecture",
                agent="Architect",
                payload={"style": "microservices"},
            ),
            CommandStep(
                id="api_design",
                action="design_api",
                agent="APIDesigner",
                payload={"format": "REST"},
            ),
            CommandStep(
                id="database_design",
                action="design_database",
                agent="Database",
                payload={"type": "postgresql"},
            ),
            CommandStep(
                id="implementation",
                action="implement_system",
                agent="Constructor",
                payload={"framework": "fastapi"},
            ),
            CommandStep(
                id="testing",
                action="create_tests",
                agent="Testbed",
                payload={"coverage": 90},
            ),
            CommandStep(
                id="deployment",
                action="deploy_system",
                agent="Deployer",
                payload={"environment": "staging"},
            ),
        ],
        dependencies={
            "architecture": ["planning"],
            "api_design": ["architecture"],
            "database_design": ["architecture"],
            "implementation": ["api_design", "database_design"],
            "testing": ["implementation"],
            "deployment": ["testing"],
        },
    )

    print(f"Executing DAG with {len(complex_workflow.steps)} steps...")
    print(f"Dependencies: {complex_workflow.dependencies}")

    result = await orchestrator.execute_command_set(
        complex_workflow, use_dag_engine=True
    )

    print(f"\n📊 DAG Execution Results:")
    print(f"   Status: {result.get('status', 'unknown')}")
    print(f"   Completed steps: {result.get('completed_steps', 0)}")
    print(f"   Failed steps: {result.get('failed_steps', 0)}")

    if "results" in result:
        print(f"   Step results: {list(result['results'].keys())}")


async def demo_agent_health_monitoring():
    """Demonstrate agent health monitoring"""
    print("\n🏥 Agent Health Monitoring Demo")
    print("=" * 50)

    orchestrator = TandemOrchestrator()
    await orchestrator.initialize()

    # Get initial health status
    health = orchestrator.agent_registration.get_agent_health_status()

    print(f"📊 Health Status:")
    print(f"   Total agents: {health['total_agents']}")
    print(f"   Healthy agents: {health['healthy_agents']}")
    print(f"   Unhealthy agents: {health['unhealthy_agents']}")

    # Show health for critical agents
    critical_agents = ["Director", "ProjectOrchestrator", "Security"]
    print(f"\n🔍 Critical Agent Health:")

    for agent in critical_agents:
        if agent in health["agents"]:
            agent_health = health["agents"][agent]
            status_emoji = "✅" if agent_health["healthy"] else "❌"
            print(
                f"   {status_emoji} {agent}: {agent_health['health_score']}/100 ({agent_health['status']})"
            )


async def demo_capability_based_routing():
    """Demonstrate capability-based agent routing"""
    print("\n🎯 Capability-Based Routing Demo")
    print("=" * 50)

    orchestrator = TandemOrchestrator()
    await orchestrator.initialize()

    # Test different capability searches
    capabilities_to_test = ["design", "test", "deploy", "monitor", "secure"]

    for capability in capabilities_to_test:
        agents = orchestrator.agent_registration.get_agents_by_capability(capability)
        print(f"🔍 Agents with '{capability}' capability: {agents}")


async def demo_standard_workflows():
    """Demonstrate standard pre-built workflows"""
    print("\n📋 Standard Workflows Demo")
    print("=" * 50)

    orchestrator = TandemOrchestrator()
    await orchestrator.initialize()

    # Test document generation workflow
    doc_workflow = StandardWorkflows.create_document_generation_workflow()
    print(f"📝 Document Generation Workflow:")
    print(f"   Steps: {len(doc_workflow.steps)}")
    print(f"   Mode: {doc_workflow.mode.value}")
    print(f"   Dependencies: {len(doc_workflow.dependencies)}")

    # Execute the workflow
    result = await orchestrator.execute_command_set(doc_workflow)
    print(f"   Execution result: {result.get('status', 'unknown')}")

    # Test security audit workflow
    security_workflow = StandardWorkflows.create_security_audit_workflow()
    print(f"\n🛡️ Security Audit Workflow:")
    print(f"   Steps: {len(security_workflow.steps)}")
    print(f"   Mode: {security_workflow.mode.value}")
    print(f"   Priority: {security_workflow.priority.name}")

    result = await orchestrator.execute_command_set(security_workflow)
    print(f"   Execution result: {result.get('status', 'unknown')}")


async def demo_performance_metrics():
    """Demonstrate performance metrics collection"""
    print("\n📈 Performance Metrics Demo")
    print("=" * 50)

    orchestrator = TandemOrchestrator()
    await orchestrator.initialize()

    # Execute a few operations to generate metrics
    for i in range(3):
        await orchestrator.invoke_agent("Monitor", f"health_check_{i}")

    # Get comprehensive metrics
    metrics = orchestrator.get_metrics()

    print(f"📊 System Metrics:")
    print(f"   Registered agents: {metrics.get('registered_agents', 0)}")
    print(
        f"   Binary bridge connected: {metrics.get('binary_bridge_connected', False)}"
    )
    print(f"   Python messages processed: {metrics.get('python_msgs_processed', 0)}")
    print(f"   C messages processed: {metrics.get('c_msgs_processed', 0)}")
    print(f"   Active campaigns: {metrics.get('active_campaigns', 0)}")
    print(f"   Command history size: {metrics.get('history_size', 0)}")

    # Show execution statistics
    if metrics.get("execution_stats"):
        print(f"\n📈 Execution Statistics:")
        for stat_key, stat_value in metrics["execution_stats"].items():
            print(f"   {stat_key}: {stat_value}")


async def main():
    """Run all demonstrations"""
    print("🚀 Enhanced Tandem Orchestrator - Complete Demonstration")
    print("=" * 70)

    try:
        # Run all demo functions
        await demo_agent_registration()
        await demo_execution_modes()
        await demo_dag_execution()
        await demo_agent_health_monitoring()
        await demo_capability_based_routing()
        await demo_standard_workflows()
        await demo_performance_metrics()

        print(f"\n✅ All demonstrations completed successfully!")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
