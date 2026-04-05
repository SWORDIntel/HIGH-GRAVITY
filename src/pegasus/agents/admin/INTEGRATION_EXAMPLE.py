#!/usr/bin/env python3
"""
Example: How new agents automatically integrate with the communication system
This demonstrates the auto-integration capability for future agents
"""

import asyncio
import sys

sys.path.append('${CLAUDE_AGENTS_ROOT:-$(dirname "$0")}/../src/python')

# Import the auto-integration module
from 03-BRIDGES.auto_integrate import (
    auto_integration,
    integrate_with_claude_agent_system,
)


async def main():
    """
    Example of how any new agent can automatically integrate
    with the Claude Agent Communication System
    """
    
    print("=" * 60)
    print("Claude Agent Auto-Integration Example")
    print("=" * 60)
    print()
    
    # STEP 1: Integrate a new custom agent
    print("1. Integrating new custom agent...")
    my_agent = integrate_with_claude_agent_system(
        agent_name="example_agent",
        agent_type="CUSTOM"
    )
    print()
    
    # STEP 2: The agent is now automatically part of the system
    print("2. Agent capabilities:")
    print(f"   - Can send messages to all 31 system agents")
    print(f"   - Receives messages via pub/sub and RPC")
    print(f"   - Participates in work queue distribution")
    print(f"   - Full RBAC security integration")
    print(f"   - Automatic health monitoring")
    print()
    
    # STEP 3: Send a test message
    print("3. Testing communication...")
    from ENHANCED_AGENT_INTEGRATION import AgentMessage, Priority

    # Create a message to the Director agent
    test_message = AgentMessage(
        source_agent="example_agent",
        target_agents=["director", "monitor"],
        action="introduction",
        payload={
            "message": "Hello! I'm a new agent joining the system.",
            "capabilities": ["example", "demonstration"],
            "request": "Please acknowledge my integration"
        },
        priority=Priority.MEDIUM,
        requires_ack=True
    )
    
    # Send the message
    try:
        result = await auto_integration.system.send_message(test_message)
        print(f"   ✓ Message sent successfully!")
        print(f"   Response: {result}")
    except Exception as e:
        print(f"   ⚠ Communication test failed: {e}")
    print()
    
    # STEP 4: Subscribe to events
    print("4. Subscribing to system events...")
    
    async def handle_event(message):
        """Handle incoming events"""
        print(f"   Received event: {message.action} from {message.source_agent}")
    
    # Subscribe to topics
    await auto_integration.system.subscribe("system.updates", handle_event)
    await auto_integration.system.subscribe("tasks.available", handle_event)
    print("   ✓ Subscribed to system events")
    print()
    
    # STEP 5: Register capabilities
    print("5. Registering agent capabilities...")
    capabilities = {
        "name": "example_agent",
        "version": "1.0.0",
        "capabilities": [
            "example_processing",
            "demonstration",
            "testing"
        ],
        "performance": {
            "max_throughput": "1000 msg/sec",
            "avg_latency": "10ms"
        }
    }
    
    # Register with discovery service
    await auto_integration.system.register_capabilities("example_agent", capabilities)
    print("   ✓ Capabilities registered with discovery service")
    print()
    
    # STEP 6: Demonstrate work queue participation
    print("6. Participating in work queue...")
    
    async def process_work_item(work):
        """Process work from the queue"""
        print(f"   Processing work item: {work['id']}")
        # Simulate work
        await asyncio.sleep(0.1)
        return {"status": "completed", "result": "example_result"}
    
    # Join work queue
    await auto_integration.system.join_work_queue(
        "example_queue",
        process_work_item
    )
    print("   ✓ Joined work queue 'example_queue'")
    print()
    
    print("=" * 60)
    print("Integration Complete!")
    print("=" * 60)
    print()
    print("This agent is now fully integrated with:")
    print("  • Ultra-fast binary protocol (4.2M msg/sec)")
    print("  • All 31 system agents")
    print("  • RBAC security system")
    print("  • Monitoring and metrics")
    print("  • Health checks and failover")
    print()
    print("To integrate your own agent, simply call:")
    print('  integrate_with_claude_agent_system("your_agent_name")')
    print()

# Helper function for automatic integration in any Python script
def auto_integrate_this_script(script_name):
    """
    Call this function at the top of any Python script to automatically
    integrate it as an agent in the Claude Communication System
    
    Example:
        from 08-ADMIN-TOOLS.INTEGRATION_EXAMPLE import 03-BRIDGES.auto_integrate_this_script
        agent = auto_integrate_this_script(__file__)
    """
    import os
    agent_name = os.path.basename(script_name).replace('.py', '')
    return integrate_with_claude_agent_system(agent_name, "CUSTOM")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())