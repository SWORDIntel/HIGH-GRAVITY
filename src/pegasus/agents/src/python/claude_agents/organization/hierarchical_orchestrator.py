#!/usr/bin/env python3
"""
Hierarchical Multi-Agent Orchestrator
======================================

Corporate-style orchestration system that respects organizational hierarchy,
chain of command, and authority levels. Tasks flow through proper channels,
escalations go up the chain, and approvals come from appropriate levels.

Key Features:
- Respects organizational hierarchy
- Enforces chain of command
- Automatic escalation to appropriate authority
- Approval workflows based on position
- Division-based task routing
- Special reporting structures (e.g., CHAOS → CSO only)

Author: SWORDSwarm Organizational System
Version: 1.0.0
Status: PRODUCTION
"""

import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from .hierarchy import (
    Agent,
    AuthorityLevel,
    Division,
    OrganizationalChart,
    OrganizationalLevel,
    Position,
    create_standard_organization,
)

from ..communication.binary_translator import (
    HumanReadableMessage,
    MessageType,
    Priority,
)

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""

    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class WorkTask:
    """Work task with organizational context"""

    task_id: str
    description: str
    required_capabilities: List[str]
    priority: Priority = Priority.MEDIUM

    # Organizational context
    requested_by: Optional[str] = None  # Agent ID
    assigned_to: Optional[str] = None  # Agent ID
    approved_by: List[str] = field(default_factory=list)  # Agent IDs
    reviewed_by: List[str] = field(default_factory=list)  # Agent IDs

    # Status tracking
    status: TaskStatus = TaskStatus.PENDING_APPROVAL
    requires_approval: bool = False
    approval_level: Optional[AuthorityLevel] = None

    # Execution
    dependencies: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    escalated_to: Optional[str] = None  # Agent ID

    # Results
    result: Optional[Dict[str, Any]] = None
    feedback: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class HierarchicalOrchestrator:
    """
    Orchestrator that respects corporate hierarchy and chain of command
    """

    def __init__(self, org_chart: Optional[OrganizationalChart] = None):
        self.org_chart = org_chart or create_standard_organization()

        # Task management
        self.tasks: Dict[str, WorkTask] = {}
        self.pending_approvals: Dict[str, List[str]] = defaultdict(list)  # Agent ID -> Task IDs

        # Conversation tracking
        self.conversations: Dict[str, List[HumanReadableMessage]] = defaultdict(list)

        # Statistics
        self.stats = {
            "tasks_created": 0,
            "tasks_approved": 0,
            "tasks_rejected": 0,
            "tasks_escalated": 0,
            "tasks_completed": 0,
            "approvals_requested": 0,
            "chain_of_command_followed": 0,
        }

    def request_work(
        self,
        description: str,
        required_capabilities: List[str],
        requested_by: str,
        priority: Priority = Priority.MEDIUM,
        target_division: Optional[Division] = None,
        requires_approval: bool = None,
    ) -> str:
        """
        Request work through proper organizational channels

        Args:
            description: Task description
            required_capabilities: Required capabilities
            requested_by: Agent ID requesting work
            priority: Task priority
            target_division: Target division for work
            requires_approval: Whether approval is required (auto-detected if None)

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())

        requester = self.org_chart.agents.get(requested_by)
        if not requester:
            raise ValueError(f"Unknown agent: {requested_by}")

        # Auto-detect approval requirement based on requester's authority
        if requires_approval is None:
            # Workers and middle management need approval for most tasks
            requires_approval = requester.position.level.value >= OrganizationalLevel.MIDDLE_MANAGEMENT.value

        # Determine approval level needed
        approval_level = None
        if requires_approval:
            if priority == Priority.CRITICAL:
                approval_level = AuthorityLevel.STRATEGIC
            elif priority == Priority.HIGH:
                approval_level = AuthorityLevel.DIVISIONAL
            else:
                approval_level = AuthorityLevel.TEAM

        task = WorkTask(
            task_id=task_id,
            description=description,
            required_capabilities=required_capabilities,
            priority=priority,
            requested_by=requested_by,
            requires_approval=requires_approval,
            approval_level=approval_level,
            status=TaskStatus.PENDING_APPROVAL if requires_approval else TaskStatus.APPROVED,
        )

        self.tasks[task_id] = task
        self.stats["tasks_created"] += 1

        logger.info(
            f"Work requested by {requester.agent_name}: '{description}' "
            f"(requires_approval={requires_approval}, level={approval_level})"
        )

        # If requires approval, route to appropriate authority
        if requires_approval:
            self._route_for_approval(task_id)
        else:
            # Auto-approve and assign
            task.status = TaskStatus.APPROVED
            self._assign_task(task_id, target_division)

        return task_id

    def _route_for_approval(self, task_id: str):
        """Route task to appropriate approver"""
        task = self.tasks[task_id]
        requester = self.org_chart.agents[task.requested_by]

        # Find appropriate approver in chain of command
        approver_id = self._find_approver(requester.agent_id, task.approval_level)

        if approver_id:
            self.pending_approvals[approver_id].append(task_id)
            self.stats["approvals_requested"] += 1
            logger.info(
                f"Task {task_id} routed to {self.org_chart.agents[approver_id].agent_name} for approval"
            )
        else:
            logger.warning(f"No approver found for task {task_id}, auto-approving")
            task.status = TaskStatus.APPROVED
            self._assign_task(task_id)

    def _find_approver(
        self, agent_id: str, required_authority: Optional[AuthorityLevel]
    ) -> Optional[str]:
        """Find appropriate approver in chain of command"""
        agent = self.org_chart.agents.get(agent_id)
        if not agent:
            return None

        # Follow chain of command upward
        current_id = agent.manager

        while current_id:
            current_agent = self.org_chart.agents.get(current_id)
            if not current_agent:
                break

            # Check if this manager has appropriate authority
            if required_authority is None:
                return current_id

            if current_agent.position.authority.value <= required_authority.value:
                return current_id

            current_id = current_agent.manager

        return None

    def approve_task(self, task_id: str, approver_id: str, approved: bool, feedback: str = ""):
        """
        Approve or reject a task

        Args:
            task_id: Task ID
            approver_id: Approver's agent ID
            approved: Whether approved
            feedback: Optional feedback
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        approver = self.org_chart.agents.get(approver_id)
        if not approver:
            logger.error(f"Approver {approver_id} not found")
            return

        # Verify approver has authority
        if not self._can_approve(approver_id, task):
            logger.error(
                f"{approver.agent_name} does not have authority to approve this task"
            )
            return

        task.approved_by.append(approver_id)

        if approved:
            task.status = TaskStatus.APPROVED
            self.stats["tasks_approved"] += 1
            logger.info(f"Task {task_id} approved by {approver.agent_name}")

            # Remove from pending approvals
            if task_id in self.pending_approvals[approver_id]:
                self.pending_approvals[approver_id].remove(task_id)

            # Assign task
            self._assign_task(task_id)

        else:
            task.status = TaskStatus.REJECTED
            task.feedback.append({
                "from": approver_id,
                "feedback": feedback,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "rejected"
            })
            self.stats["tasks_rejected"] += 1
            logger.info(f"Task {task_id} rejected by {approver.agent_name}: {feedback}")

    def _can_approve(self, approver_id: str, task: WorkTask) -> bool:
        """Check if agent can approve task"""
        approver = self.org_chart.agents.get(approver_id)
        if not approver:
            return False

        # Check authority level
        if task.approval_level:
            return approver.position.authority.value <= task.approval_level.value

        return True

    def _assign_task(self, task_id: str, preferred_division: Optional[Division] = None):
        """Assign task to suitable agent"""
        task = self.tasks[task_id]

        # Find suitable agent
        agent_id = self.org_chart.find_suitable_agent(
            task.required_capabilities,
            division=preferred_division,
        )

        if not agent_id:
            logger.warning(f"No suitable agent found for task {task_id}")
            task.status = TaskStatus.BLOCKED
            task.blockers.append("no_suitable_agent")
            return

        agent = self.org_chart.agents[agent_id]

        # Verify requester can delegate to this agent
        if task.requested_by:
            if not self.org_chart.can_agent_delegate_to(task.requested_by, agent_id):
                logger.warning(
                    f"Requester {task.requested_by} cannot delegate to {agent_id}, escalating"
                )
                self._escalate_task(task_id, "delegation_not_allowed")
                return

        # Assign task
        task.assigned_to = agent_id
        task.status = TaskStatus.ASSIGNED
        task.assigned_at = datetime.now(timezone.utc)

        agent.current_tasks.add(task_id)

        logger.info(f"Task {task_id} assigned to {agent.agent_name} ({agent.position.title})")

        # Send task message
        self._send_task_message(task_id)

    def _send_task_message(self, task_id: str):
        """Send task assignment message"""
        task = self.tasks[task_id]
        if not task.assigned_to:
            return

        assignee = self.org_chart.agents[task.assigned_to]
        requester = self.org_chart.agents.get(task.requested_by) if task.requested_by else None

        message = HumanReadableMessage(
            message_id=self._generate_message_id(),
            message_type=MessageType.TASK.name,
            priority=task.priority.name,
            source_agent=requester.agent_name if requester else "ORCHESTRATOR",
            target_agents=[assignee.agent_name],
            payload={
                "task_id": task_id,
                "description": task.description,
                "required_capabilities": task.required_capabilities,
                "approved_by": [
                    self.org_chart.agents[aid].agent_name for aid in task.approved_by
                ],
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        conversation_id = task_id
        self.conversations[conversation_id].append(message)

    def start_task(self, task_id: str, agent_id: str):
        """Mark task as in progress"""
        task = self.tasks.get(task_id)
        if not task or task.assigned_to != agent_id:
            return

        task.status = TaskStatus.IN_PROGRESS
        logger.info(f"Task {task_id} started by {self.org_chart.agents[agent_id].agent_name}")

    def complete_task(self, task_id: str, agent_id: str, result: Dict[str, Any]):
        """Complete a task"""
        task = self.tasks.get(task_id)
        if not task or task.assigned_to != agent_id:
            logger.error(f"Invalid task completion: {task_id} by {agent_id}")
            return

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        task.result = result

        agent = self.org_chart.agents[agent_id]
        agent.current_tasks.discard(task_id)
        agent.completed_tasks += 1

        self.stats["tasks_completed"] += 1

        logger.info(f"Task {task_id} completed by {agent.agent_name}")

        # Send completion message
        self._send_completion_message(task_id)

    def _send_completion_message(self, task_id: str):
        """Send task completion message"""
        task = self.tasks[task_id]
        if not task.assigned_to:
            return

        assignee = self.org_chart.agents[task.assigned_to]

        # Send to requester if exists
        targets = []
        if task.requested_by:
            requester = self.org_chart.agents[task.requested_by]
            targets.append(requester.agent_name)

        # Send to approvers
        for approver_id in task.approved_by:
            approver = self.org_chart.agents[approver_id]
            if approver.agent_name not in targets:
                targets.append(approver.agent_name)

        if not targets:
            targets = ["ORCHESTRATOR"]

        message = HumanReadableMessage(
            message_id=self._generate_message_id(),
            message_type=MessageType.RESULT.name,
            priority=task.priority.name,
            source_agent=assignee.agent_name,
            target_agents=targets,
            payload={
                "task_id": task_id,
                "status": "completed",
                "result": task.result,
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        conversation_id = task_id
        self.conversations[conversation_id].append(message)

    def escalate_task(
        self, task_id: str, escalating_agent_id: str, reason: str, issue_type: str = "general"
    ):
        """
        Escalate task up the chain of command

        Args:
            task_id: Task ID
            escalating_agent_id: Agent escalating
            reason: Escalation reason
            issue_type: Type of issue (general, security, technical, strategic)
        """
        self._escalate_task(task_id, reason, escalating_agent_id, issue_type)

    def _escalate_task(
        self,
        task_id: str,
        reason: str,
        escalating_agent_id: Optional[str] = None,
        issue_type: str = "general"
    ):
        """Internal escalation logic"""
        task = self.tasks[task_id]

        # Determine who is escalating
        if escalating_agent_id:
            escalator_id = escalating_agent_id
        elif task.assigned_to:
            escalator_id = task.assigned_to
        elif task.requested_by:
            escalator_id = task.requested_by
        else:
            logger.error(f"Cannot escalate task {task_id}: no agent context")
            return

        # Get escalation path
        escalation_path = self.org_chart.get_escalation_path(escalator_id, issue_type)

        if not escalation_path:
            logger.error(f"No escalation path found for {escalator_id}")
            return

        # Escalate to first person in path
        escalated_to = escalation_path[0]

        task.status = TaskStatus.ESCALATED
        task.escalated_to = escalated_to
        task.feedback.append({
            "from": escalator_id,
            "action": "escalated",
            "reason": reason,
            "escalated_to": escalated_to,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        self.stats["tasks_escalated"] += 1
        self.stats["chain_of_command_followed"] += 1

        escalator = self.org_chart.agents[escalator_id]
        escalated_to_agent = self.org_chart.agents[escalated_to]

        logger.info(
            f"Task {task_id} escalated from {escalator.agent_name} "
            f"to {escalated_to_agent.agent_name} ({escalated_to_agent.position.title})"
        )

        # Send escalation message
        self._send_escalation_message(task_id, escalator_id, escalated_to, reason)

    def _send_escalation_message(
        self, task_id: str, from_agent_id: str, to_agent_id: str, reason: str
    ):
        """Send escalation message"""
        from_agent = self.org_chart.agents[from_agent_id]
        to_agent = self.org_chart.agents[to_agent_id]

        message = HumanReadableMessage(
            message_id=self._generate_message_id(),
            message_type=MessageType.REQUEST.name,
            priority=Priority.HIGH.name,
            source_agent=from_agent.agent_name,
            target_agents=[to_agent.agent_name],
            payload={
                "action": "escalation",
                "task_id": task_id,
                "reason": reason,
                "escalation_level": to_agent.position.level.name,
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        conversation_id = task_id
        self.conversations[conversation_id].append(message)

    def provide_feedback(
        self,
        task_id: str,
        from_agent_id: str,
        feedback: Dict[str, Any],
    ):
        """Provide feedback on a task"""
        task = self.tasks.get(task_id)
        if not task:
            return

        from_agent = self.org_chart.agents.get(from_agent_id)
        if not from_agent:
            return

        task.feedback.append({
            "from": from_agent_id,
            "feedback": feedback,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Send feedback message
        if task.assigned_to:
            to_agent = self.org_chart.agents[task.assigned_to]

            message = HumanReadableMessage(
                message_id=self._generate_message_id(),
                message_type=MessageType.RESPONSE.name,
                priority=Priority.MEDIUM.name,
                source_agent=from_agent.agent_name,
                target_agents=[to_agent.agent_name],
                payload={
                    "task_id": task_id,
                    "action": "feedback",
                    "feedback": feedback,
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            self.conversations[task_id].append(message)

        logger.info(f"Feedback provided on task {task_id} by {from_agent.agent_name}")

    def get_task_conversation(self, task_id: str) -> List[HumanReadableMessage]:
        """Get all messages related to a task"""
        return self.conversations.get(task_id, [])

    def get_pending_approvals(self, agent_id: str) -> List[WorkTask]:
        """Get tasks pending approval by an agent"""
        task_ids = self.pending_approvals.get(agent_id, [])
        return [self.tasks[tid] for tid in task_ids if tid in self.tasks]

    def get_agent_workload(self, agent_id: str) -> Dict[str, Any]:
        """Get agent's current workload"""
        agent = self.org_chart.agents.get(agent_id)
        if not agent:
            return {}

        current_tasks = [
            self.tasks[tid] for tid in agent.current_tasks if tid in self.tasks
        ]

        return {
            "agent_name": agent.agent_name,
            "position": agent.position.title,
            "current_tasks": len(current_tasks),
            "max_concurrent": agent.position.max_concurrent_tasks,
            "utilization": len(current_tasks) / agent.position.max_concurrent_tasks,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "status": t.status.value,
                    "priority": t.priority.name,
                }
                for t in current_tasks
            ],
            "pending_approvals": len(self.pending_approvals.get(agent_id, [])),
        }

    def get_division_status(self, division: Division) -> Dict[str, Any]:
        """Get status of a division"""
        agent_ids = self.org_chart.find_agents_in_division(division)
        agents = [self.org_chart.agents[aid] for aid in agent_ids]

        total_tasks = sum(len(a.current_tasks) for a in agents)
        total_completed = sum(a.completed_tasks for a in agents)

        return {
            "division": division.name,
            "total_agents": len(agents),
            "active_tasks": total_tasks,
            "completed_tasks": total_completed,
            "agents": [
                {
                    "name": a.agent_name,
                    "position": a.position.title,
                    "tasks": len(a.current_tasks),
                }
                for a in agents
            ],
        }

    def _generate_message_id(self) -> int:
        """Generate unique message ID"""
        import time
        return int(time.time() * 1000000) % (2**32)

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return dict(self.stats)


__all__ = [
    "TaskStatus",
    "WorkTask",
    "HierarchicalOrchestrator",
]
