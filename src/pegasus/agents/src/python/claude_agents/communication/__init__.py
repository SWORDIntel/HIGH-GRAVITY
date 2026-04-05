"""
Dynamic Agent Communication Module
===================================

This module provides conversational multi-agent communication with dynamic
task allocation. Unlike traditional fire-and-forget messaging, agents maintain
shared context, provide feedback, and iterate on solutions collaboratively.

Key Features:
- Binary ↔ Human-readable message translation
- Dynamic task allocation based on agent capabilities
- Iterative feedback loops between agents
- Task dependency tracking and resolution
- Conversation state management
- Integration with ultra-fast binary protocol (4.2M msg/sec)

Components:
-----------
- BinaryMessageTranslator: Translates between binary and human formats
- DynamicOrchestrator: Orchestrates multi-agent conversations
- Message types and priority levels

Quick Start:
-----------

```python
from claude_agents.communication import (
    DynamicOrchestrator,
    BinaryMessageTranslator,
    MessageType,
    Priority
)

# Create orchestrator
orchestrator = DynamicOrchestrator(enable_binary_communication=True)
await orchestrator.start()

# Register agents
orchestrator.register_agent(
    "ARCHITECT",
    capabilities=["system_design", "architecture"]
)

# Create conversation
thread_id = orchestrator.create_conversation(
    goal="Design authentication system",
    initial_tasks=[
        {
            "description": "Design auth architecture",
            "priority": "HIGH",
            "context": {"required_capabilities": ["system_design"]}
        }
    ]
)

# Allocate task (orchestrator picks best agent)
await orchestrator.allocate_task(thread_id, task_id)

# Send feedback for iteration
await orchestrator.send_feedback(
    thread_id, task_id, "SECURITY",
    {"action": "revise", "suggestions": ["Add rate limiting"]}
)

# Complete task
await orchestrator.complete_task(
    thread_id, task_id,
    {"design": "OAuth2 + JWT + Rate Limiter"}
)

# Get transcript
transcript = orchestrator.get_conversation_transcript(thread_id)
print(transcript)
```

For full documentation, see: docs/DYNAMIC_AGENT_COMMUNICATION.md
"""

from .binary_translator import (
    BinaryMessageTranslator,
    BinaryMessage,
    HumanReadableMessage,
    MessageType,
    Priority,
    binary_to_human,
    human_to_binary,
    format_conversation,
)

from .dynamic_orchestrator import (
    DynamicOrchestrator,
    ConversationThread,
    ConversationTask,
    AgentCapability,
    TaskState,
    AgentState,
)

__all__ = [
    # Translation
    "BinaryMessageTranslator",
    "BinaryMessage",
    "HumanReadableMessage",
    "MessageType",
    "Priority",
    "binary_to_human",
    "human_to_binary",
    "format_conversation",
    # Orchestration
    "DynamicOrchestrator",
    "ConversationThread",
    "ConversationTask",
    "AgentCapability",
    "TaskState",
    "AgentState",
]

__version__ = "1.0.0"
__author__ = "SWORDSwarm Agent Communication System"
