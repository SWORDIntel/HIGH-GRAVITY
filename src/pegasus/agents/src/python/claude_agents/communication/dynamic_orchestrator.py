#!/usr/bin/env python3
"""
Dynamic Agent Communication Orchestrator
=========================================

Orchestrates multi-agent communication with dynamic task allocation.
NOT fire-and-forget: maintains conversation state, tracks task dependencies,
and enables agents to collaborate iteratively on complex problems.

Features:
- Dynamic task allocation based on agent capabilities
- Conversational state management between agents
- Task dependency tracking and resolution
- Iterative problem-solving with feedback loops
- Binary communication layer integration
- Real-time monitoring and visualization

Author: SWORDSwarm Agent Communication System
Version: 1.0.0
Status: PRODUCTION
"""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .binary_translator import (
    BinaryMessageTranslator,
    HumanReadableMessage,
    MessageType,
    Priority,
)

logger = logging.getLogger(__name__)


class TaskState(Enum):
    """Task execution states"""

    PENDING = "pending"
    ALLOCATED = "allocated"
    IN_PROGRESS = "in_progress"
    WAITING_FEEDBACK = "waiting_feedback"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentState(Enum):
    """Agent availability states"""

    IDLE = "idle"
    BUSY = "busy"
    WAITING = "waiting"
    OFFLINE = "offline"


@dataclass
class AgentCapability:
    """Agent capability definition"""

    agent_name: str
    capabilities: List[str]
    max_concurrent_tasks: int = 5
    avg_response_time_ms: float = 100.0
    success_rate: float = 1.0
    specialty_score: Dict[str, float] = field(default_factory=dict)


@dataclass
class ConversationTask:
    """Task within a multi-agent conversation"""

    task_id: str
    description: str
    assigned_agent: Optional[str] = None
    state: TaskState = TaskState.PENDING
    priority: Priority = Priority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    allocated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    feedback_received: List[Dict[str, Any]] = field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 3
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationThread:
    """A conversation thread between multiple agents"""

    thread_id: str
    goal: str
    participating_agents: Set[str] = field(default_factory=set)
    tasks: Dict[str, ConversationTask] = field(default_factory=dict)
    messages: List[HumanReadableMessage] = field(default_factory=list)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    final_result: Optional[Dict[str, Any]] = None


class DynamicOrchestrator:
    """
    Dynamic orchestrator for multi-agent conversations with iterative task allocation
    """

    def __init__(self, enable_binary_communication: bool = True):
        self.enable_binary = enable_binary_communication
        self.translator = BinaryMessageTranslator()

        # Agent registry
        self.agents: Dict[str, AgentCapability] = {}
        self.agent_states: Dict[str, AgentState] = {}
        self.agent_current_tasks: Dict[str, Set[str]] = defaultdict(set)

        # Conversation threads
        self.conversations: Dict[str, ConversationThread] = {}

        # Message routing
        self.message_queue: deque = deque()
        self.response_callbacks: Dict[str, Callable] = {}

        # Statistics
        self.stats = {
            "conversations_created": 0,
            "tasks_allocated": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "messages_sent": 0,
            "feedback_loops": 0,
            "average_iterations_per_task": 0.0,
        }

        # Running state
        self.is_running = False
        self._message_processor_task = None

    async def start(self):
        """Start the orchestrator"""
        if self.is_running:
            return

        self.is_running = True
        self._message_processor_task = asyncio.create_task(self._process_messages())
        logger.info("Dynamic Orchestrator started")

    async def stop(self):
        """Stop the orchestrator"""
        self.is_running = False

        if self._message_processor_task:
            self._message_processor_task.cancel()
            try:
                await self._message_processor_task
            except asyncio.CancelledError:
                pass

        logger.info("Dynamic Orchestrator stopped")

    def register_agent(
        self,
        agent_name: str,
        capabilities: List[str],
        max_concurrent_tasks: int = 5,
        specialty_scores: Optional[Dict[str, float]] = None,
    ):
        """
        Register an agent with the orchestrator

        Args:
            agent_name: Name of the agent
            capabilities: List of capabilities (e.g., ["code_analysis", "debugging"])
            max_concurrent_tasks: Maximum concurrent tasks
            specialty_scores: Optional specialty scores for capabilities
        """
        capability = AgentCapability(
            agent_name=agent_name,
            capabilities=capabilities,
            max_concurrent_tasks=max_concurrent_tasks,
            specialty_score=specialty_scores or {},
        )

        self.agents[agent_name] = capability
        self.agent_states[agent_name] = AgentState.IDLE
        self.agent_current_tasks[agent_name] = set()

        logger.info(
            f"Registered agent '{agent_name}' with capabilities: {', '.join(capabilities)}"
        )

    def create_conversation(
        self, goal: str, initial_tasks: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Create a new conversation thread

        Args:
            goal: The overall goal of the conversation
            initial_tasks: Optional list of initial tasks

        Returns:
            Conversation thread ID
        """
        thread_id = str(uuid.uuid4())

        conversation = ConversationThread(thread_id=thread_id, goal=goal)

        # Add initial tasks
        if initial_tasks:
            for task_spec in initial_tasks:
                task_id = str(uuid.uuid4())
                task = ConversationTask(
                    task_id=task_id,
                    description=task_spec.get("description", ""),
                    priority=Priority[task_spec.get("priority", "MEDIUM")],
                    dependencies=task_spec.get("dependencies", []),
                    context=task_spec.get("context", {}),
                )
                conversation.tasks[task_id] = task

        self.conversations[thread_id] = conversation
        self.stats["conversations_created"] += 1

        logger.info(f"Created conversation '{thread_id}' with goal: {goal}")
        return thread_id

    async def allocate_task(
        self, thread_id: str, task_id: str, preferred_agent: Optional[str] = None
    ) -> bool:
        """
        Dynamically allocate a task to the most suitable agent

        Args:
            thread_id: Conversation thread ID
            task_id: Task ID to allocate
            preferred_agent: Optional preferred agent name

        Returns:
            True if task was allocated successfully
        """
        conversation = self.conversations.get(thread_id)
        if not conversation:
            logger.error(f"Conversation '{thread_id}' not found")
            return False

        task = conversation.tasks.get(task_id)
        if not task:
            logger.error(f"Task '{task_id}' not found in conversation '{thread_id}'")
            return False

        # Check task dependencies
        for dep_id in task.dependencies:
            dep_task = conversation.tasks.get(dep_id)
            if not dep_task or dep_task.state != TaskState.COMPLETED:
                logger.info(
                    f"Task '{task_id}' has unmet dependency '{dep_id}', deferring allocation"
                )
                return False

        # Find best agent for the task
        if preferred_agent and preferred_agent in self.agents:
            agent_name = preferred_agent
        else:
            agent_name = self._find_best_agent(task)

        if not agent_name:
            logger.warning(f"No suitable agent found for task '{task_id}'")
            return False

        # Allocate task
        task.assigned_agent = agent_name
        task.state = TaskState.ALLOCATED
        task.allocated_at = datetime.now(timezone.utc)

        self.agent_current_tasks[agent_name].add(task_id)
        conversation.participating_agents.add(agent_name)

        # Send task message to agent
        await self._send_task_message(thread_id, task_id, agent_name)

        self.stats["tasks_allocated"] += 1

        logger.info(f"Allocated task '{task_id}' to agent '{agent_name}'")
        return True

    async def send_feedback(
        self, thread_id: str, task_id: str, feedback_agent: str, feedback: Dict[str, Any]
    ):
        """
        Send feedback on a task from another agent (enables iteration)

        Args:
            thread_id: Conversation thread ID
            task_id: Task ID
            feedback_agent: Name of agent providing feedback
            feedback: Feedback content
        """
        conversation = self.conversations.get(thread_id)
        if not conversation:
            return

        task = conversation.tasks.get(task_id)
        if not task:
            return

        # Record feedback
        task.feedback_received.append(
            {
                "from": feedback_agent,
                "feedback": feedback,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # If task needs iteration
        if task.iteration_count < task.max_iterations:
            task.state = TaskState.WAITING_FEEDBACK
            task.iteration_count += 1

            # Send feedback message to assigned agent
            await self._send_feedback_message(thread_id, task_id, feedback_agent, feedback)

            self.stats["feedback_loops"] += 1

            logger.info(
                f"Feedback sent for task '{task_id}' from '{feedback_agent}' (iteration {task.iteration_count})"
            )

    async def complete_task(
        self, thread_id: str, task_id: str, result: Dict[str, Any]
    ):
        """
        Mark a task as completed with results

        Args:
            thread_id: Conversation thread ID
            task_id: Task ID
            result: Task result data
        """
        conversation = self.conversations.get(thread_id)
        if not conversation:
            return

        task = conversation.tasks.get(task_id)
        if not task:
            return

        task.state = TaskState.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        task.result = result

        # Free up agent
        if task.assigned_agent:
            self.agent_current_tasks[task.assigned_agent].discard(task_id)

        self.stats["tasks_completed"] += 1

        # Update average iterations
        total_iterations = sum(
            t.iteration_count for t in conversation.tasks.values() if t.state == TaskState.COMPLETED
        )
        completed_count = sum(
            1 for t in conversation.tasks.values() if t.state == TaskState.COMPLETED
        )
        if completed_count > 0:
            self.stats["average_iterations_per_task"] = total_iterations / completed_count

        logger.info(
            f"Task '{task_id}' completed by '{task.assigned_agent}' after {task.iteration_count} iterations"
        )

        # Check for dependent tasks
        await self._check_and_allocate_dependent_tasks(thread_id, task_id)

        # Check if conversation is complete
        await self._check_conversation_completion(thread_id)

    def _find_best_agent(self, task: ConversationTask) -> Optional[str]:
        """
        Find the best agent for a task based on capabilities and load

        Args:
            task: Task to allocate

        Returns:
            Agent name or None
        """
        # Extract required capabilities from task context
        required_caps = task.context.get("required_capabilities", [])

        # Score each agent
        agent_scores = []

        for agent_name, capability in self.agents.items():
            # Check if agent is available
            if self.agent_states[agent_name] == AgentState.OFFLINE:
                continue

            current_load = len(self.agent_current_tasks[agent_name])
            if current_load >= capability.max_concurrent_tasks:
                continue

            # Calculate capability match score
            cap_match = 0
            if required_caps:
                matched_caps = set(required_caps) & set(capability.capabilities)
                cap_match = len(matched_caps) / len(required_caps)
            else:
                # No specific requirements, any capable agent works
                cap_match = 1.0

            if cap_match == 0:
                continue

            # Calculate load score (lower is better)
            load_score = 1.0 - (current_load / capability.max_concurrent_tasks)

            # Calculate overall score
            total_score = (cap_match * 0.6) + (load_score * 0.2) + (capability.success_rate * 0.2)

            agent_scores.append((agent_name, total_score))

        if not agent_scores:
            return None

        # Sort by score and return best agent
        agent_scores.sort(key=lambda x: x[1], reverse=True)
        return agent_scores[0][0]

    async def _send_task_message(self, thread_id: str, task_id: str, agent_name: str):
        """Send task allocation message to agent"""
        conversation = self.conversations[thread_id]
        task = conversation.tasks[task_id]

        message = HumanReadableMessage(
            message_id=self._generate_message_id(),
            message_type=MessageType.TASK.name,
            priority=task.priority.name,
            source_agent="ORCHESTRATOR",
            target_agents=[agent_name],
            payload={
                "thread_id": thread_id,
                "task_id": task_id,
                "description": task.description,
                "context": task.context,
                "shared_context": conversation.shared_context,
                "dependencies_results": self._get_dependency_results(conversation, task),
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        conversation.messages.append(message)
        self.message_queue.append(message)
        self.stats["messages_sent"] += 1

        # Update task state
        task.state = TaskState.IN_PROGRESS

        logger.debug(f"Sent task message to '{agent_name}' for task '{task_id}'")

    async def _send_feedback_message(
        self, thread_id: str, task_id: str, feedback_agent: str, feedback: Dict[str, Any]
    ):
        """Send feedback message"""
        conversation = self.conversations[thread_id]
        task = conversation.tasks[task_id]

        if not task.assigned_agent:
            return

        message = HumanReadableMessage(
            message_id=self._generate_message_id(),
            message_type=MessageType.RESPONSE.name,
            priority=Priority.HIGH.name,
            source_agent=feedback_agent,
            target_agents=[task.assigned_agent],
            payload={
                "thread_id": thread_id,
                "task_id": task_id,
                "feedback": feedback,
                "iteration": task.iteration_count,
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        conversation.messages.append(message)
        self.message_queue.append(message)
        self.stats["messages_sent"] += 1

    def _get_dependency_results(
        self, conversation: ConversationThread, task: ConversationTask
    ) -> Dict[str, Any]:
        """Get results from task dependencies"""
        results = {}

        for dep_id in task.dependencies:
            dep_task = conversation.tasks.get(dep_id)
            if dep_task and dep_task.result:
                results[dep_id] = dep_task.result

        return results

    async def _check_and_allocate_dependent_tasks(self, thread_id: str, completed_task_id: str):
        """Check and allocate tasks that depend on the completed task"""
        conversation = self.conversations[thread_id]

        for task_id, task in conversation.tasks.items():
            if task.state == TaskState.PENDING and completed_task_id in task.dependencies:
                await self.allocate_task(thread_id, task_id)

    async def _check_conversation_completion(self, thread_id: str):
        """Check if conversation is complete"""
        conversation = self.conversations[thread_id]

        all_tasks_done = all(
            task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)
            for task in conversation.tasks.values()
        )

        if all_tasks_done:
            conversation.completed_at = datetime.now(timezone.utc)

            # Compile final result
            conversation.final_result = {
                "goal": conversation.goal,
                "tasks_completed": sum(
                    1 for t in conversation.tasks.values() if t.state == TaskState.COMPLETED
                ),
                "tasks_failed": sum(
                    1 for t in conversation.tasks.values() if t.state == TaskState.FAILED
                ),
                "participating_agents": list(conversation.participating_agents),
                "duration_seconds": (
                    conversation.completed_at - conversation.created_at
                ).total_seconds(),
                "task_results": {
                    task_id: task.result
                    for task_id, task in conversation.tasks.items()
                    if task.result
                },
            }

            logger.info(f"Conversation '{thread_id}' completed: {conversation.final_result}")

    async def _process_messages(self):
        """Process message queue"""
        while self.is_running:
            try:
                if self.message_queue:
                    message = self.message_queue.popleft()

                    # Optionally convert to binary for transmission
                    if self.enable_binary:
                        binary_data = self.translator.human_to_binary(message)
                        logger.debug(
                            f"Message {message.message_id} encoded to {len(binary_data)} bytes"
                        )

                    # In real implementation, would send via network/IPC
                    # For now, just log
                    logger.debug(
                        f"Processing message {message.message_id}: {message.message_type} from {message.source_agent} to {message.target_agents}"
                    )

                await asyncio.sleep(0.01)

            except Exception as e:
                logger.error(f"Error processing message: {e}")

    def _generate_message_id(self) -> int:
        """Generate unique message ID"""
        return int(time.time() * 1000000) % (2**32)

    def get_conversation_summary(self, thread_id: str) -> Dict[str, Any]:
        """Get summary of a conversation"""
        conversation = self.conversations.get(thread_id)
        if not conversation:
            return {}

        return {
            "thread_id": thread_id,
            "goal": conversation.goal,
            "status": "completed"
            if conversation.completed_at
            else "in_progress",
            "participating_agents": list(conversation.participating_agents),
            "total_tasks": len(conversation.tasks),
            "completed_tasks": sum(
                1 for t in conversation.tasks.values() if t.state == TaskState.COMPLETED
            ),
            "total_messages": len(conversation.messages),
            "created_at": conversation.created_at.isoformat(),
            "completed_at": conversation.completed_at.isoformat()
            if conversation.completed_at
            else None,
        }

    def get_conversation_transcript(self, thread_id: str) -> str:
        """Get formatted conversation transcript"""
        conversation = self.conversations.get(thread_id)
        if not conversation:
            return "Conversation not found"

        return self.translator.format_conversation(conversation.messages)

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return dict(self.stats)
