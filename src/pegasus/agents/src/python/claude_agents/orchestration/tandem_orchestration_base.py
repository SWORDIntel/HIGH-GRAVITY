#!/usr/bin/env python3
"""
Tandem Orchestration Base Module v1.0
=====================================

Core foundation for integrating all 39 existing agents with production-grade
tandem orchestration capabilities. Designed using patterns from DIRECTOR,
PROJECTORCHESTRATOR, PYTHON-INTERNAL, and MLOPS agents.

Key Features:
- Bidirectional orchestrator communication
- Circuit breaker pattern for resilience
- Message queue system for async operations
- Performance profiling and metrics
- Inter-agent communication protocol
- Error recovery and retry mechanisms
- Health monitoring and diagnostics

Author: Claude Code Framework
Version: 1.0.0
Status: PRODUCTION
"""

import asyncio
import json
import logging
import queue
import threading
import time
import traceback
import uuid
import weakref
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Tandem execution modes"""

    INTELLIGENT = "intelligent"  # Python orchestrates, C executes when available
    PYTHON_ONLY = "python_only"  # Fallback when C unavailable
    REDUNDANT = "redundant"  # Both layers for critical operations
    CONSENSUS = "consensus"  # Both must agree on results
    SPEED_CRITICAL = "speed_critical"  # C layer only for maximum performance


class CircuitBreakerState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class TaskPriority(Enum):
    """Task priority levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class HealthStatus(Enum):
    """Agent health statuses"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class AgentTask:
    """Represents a task for agent execution"""

    id: str
    action: str
    context: Dict[str, Any]
    priority: TaskPriority = TaskPriority.MEDIUM
    timeout: int = 300
    retry_count: int = 0
    max_retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class InterAgentMessage:
    """Message for inter-agent communication"""

    id: str
    source_agent: str
    target_agent: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timeout: int = 30
    correlation_id: Optional[str] = None


@dataclass
class MetricsSnapshot:
    """Performance metrics snapshot"""

    timestamp: datetime
    execution_count: int
    success_count: int
    error_count: int
    avg_execution_time: float
    cpu_usage: float
    memory_usage: float
    cache_hit_rate: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.execution_count == 0:
            return 1.0
        return self.success_count / self.execution_count


class CircuitBreaker:
    """Circuit breaker pattern implementation"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self._lock = threading.RLock()

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info("Circuit breaker half-open, attempting reset")
                else:
                    raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return True
        return (
            datetime.now(timezone.utc) - self.last_failure_time
        ).total_seconds() > self.recovery_timeout

    def _on_success(self):
        """Handle successful execution"""
        with self._lock:
            self.failure_count = 0
            self.state = CircuitBreakerState.CLOSED

    def _on_failure(self):
        """Handle failed execution"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now(timezone.utc)

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )


class MessageQueue:
    """Async message queue for inter-agent communication"""

    def __init__(self, maxsize: int = 1000):
        self._queue = asyncio.Queue(maxsize=maxsize)
        self._message_handlers = {}
        self._running = False
        self._processor_task = None

    async def start(self):
        """Start message processing"""
        if self._running:
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._process_messages())
        logger.info("Message queue started")

    async def stop(self):
        """Stop message processing"""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Message queue stopped")

    async def send_message(self, message: InterAgentMessage):
        """Send message to queue"""
        await self._queue.put(message)

    def register_handler(self, message_type: str, handler: Callable):
        """Register message handler"""
        self._message_handlers[message_type] = handler

    async def _process_messages(self):
        """Process messages from queue"""
        while self._running:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                # Find handler
                handler = self._message_handlers.get(message.message_type)
                if handler:
                    try:
                        await handler(message)
                    except Exception as e:
                        logger.error(f"Error processing message {message.id}: {e}")
                else:
                    logger.warning(
                        f"No handler for message type: {message.message_type}"
                    )

                # Mark task done
                self._queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in message processor: {e}")


class PerformanceProfiler:
    """Performance monitoring and profiling"""

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.execution_times = deque(maxlen=window_size)
        self.memory_samples = deque(maxlen=window_size)
        self.cpu_samples = deque(maxlen=window_size)

        # Counters
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.cache_hits = 0
        self.cache_misses = 0

        # Process monitoring
        self.process = psutil.Process()

    def record_execution(self, duration: float, success: bool):
        """Record execution metrics"""
        self.execution_times.append(duration)
        self.total_executions += 1

        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1

        # Sample system metrics
        try:
            self.cpu_samples.append(self.process.cpu_percent())
            self.memory_samples.append(
                self.process.memory_info().rss / 1024 / 1024
            )  # MB
        except:
            pass

    def get_metrics(self) -> MetricsSnapshot:
        """Get current performance metrics"""
        now = datetime.now(timezone.utc)

        avg_execution_time = (
            sum(self.execution_times) / len(self.execution_times)
            if self.execution_times
            else 0.0
        )
        avg_cpu = (
            sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0.0
        )
        avg_memory = (
            sum(self.memory_samples) / len(self.memory_samples)
            if self.memory_samples
            else 0.0
        )

        cache_total = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / cache_total if cache_total > 0 else 0.0

        return MetricsSnapshot(
            timestamp=now,
            execution_count=self.total_executions,
            success_count=self.successful_executions,
            error_count=self.failed_executions,
            avg_execution_time=avg_execution_time,
            cpu_usage=avg_cpu,
            memory_usage=avg_memory,
            cache_hit_rate=cache_hit_rate,
        )

    def get_percentiles(
        self, percentiles: List[int] = [50, 75, 90, 95, 99]
    ) -> Dict[str, float]:
        """Calculate execution time percentiles"""
        if not self.execution_times:
            return {}

        sorted_times = sorted(self.execution_times)
        result = {}

        for p in percentiles:
            index = int(len(sorted_times) * (p / 100))
            result[f"p{p}"] = sorted_times[min(index, len(sorted_times) - 1)]

        return result


class OrchestratorBridge(ABC):
    """Abstract interface for orchestrator communication"""

    @abstractmethod
    async def register_agent(self, agent_id: str, capabilities: Dict[str, Any]) -> bool:
        """Register agent with orchestrator"""
        pass

    @abstractmethod
    async def deregister_agent(self, agent_id: str) -> bool:
        """Deregister agent from orchestrator"""
        pass

    @abstractmethod
    async def send_message(
        self, target_agent: str, message: InterAgentMessage
    ) -> Dict[str, Any]:
        """Send message to another agent"""
        pass

    @abstractmethod
    async def request_delegation(
        self, target_agent: str, task: AgentTask
    ) -> Dict[str, Any]:
        """Request task delegation to another agent"""
        pass

    @abstractmethod
    async def report_health(
        self, agent_id: str, health_status: HealthStatus, metrics: MetricsSnapshot
    ) -> bool:
        """Report agent health to orchestrator"""
        pass

    @abstractmethod
    async def get_agent_capabilities(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get capabilities of another agent"""
        pass


class MockOrchestratorBridge(OrchestratorBridge):
    """Mock implementation for testing and fallback"""

    def __init__(self):
        self.registered_agents = {}
        self.message_log = []

    async def register_agent(self, agent_id: str, capabilities: Dict[str, Any]) -> bool:
        """Register agent with mock orchestrator"""
        self.registered_agents[agent_id] = capabilities
        logger.info(f"Mock: Registered agent {agent_id}")
        return True

    async def deregister_agent(self, agent_id: str) -> bool:
        """Deregister agent from mock orchestrator"""
        if agent_id in self.registered_agents:
            del self.registered_agents[agent_id]
            logger.info(f"Mock: Deregistered agent {agent_id}")
            return True
        return False

    async def send_message(
        self, target_agent: str, message: InterAgentMessage
    ) -> Dict[str, Any]:
        """Send message via mock orchestrator"""
        self.message_log.append((target_agent, message))
        logger.info(f"Mock: Message sent to {target_agent}")
        return {"status": "delivered", "message_id": message.id}

    async def request_delegation(
        self, target_agent: str, task: AgentTask
    ) -> Dict[str, Any]:
        """Mock task delegation"""
        logger.info(f"Mock: Task delegated to {target_agent}: {task.action}")
        return {
            "status": "accepted",
            "task_id": task.id,
            "estimated_completion": datetime.now(timezone.utc) + timedelta(minutes=5),
        }

    async def report_health(
        self, agent_id: str, health_status: HealthStatus, metrics: MetricsSnapshot
    ) -> bool:
        """Mock health reporting"""
        logger.debug(f"Mock: Health report from {agent_id}: {health_status.value}")
        return True

    async def get_agent_capabilities(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get mock agent capabilities"""
        return self.registered_agents.get(agent_id)


class TandemOrchestrationBase:
    """Base class for tandem orchestration integration"""

    def __init__(
        self, agent_name: str, orchestrator_bridge: Optional[OrchestratorBridge] = None
    ):
        self.agent_name = agent_name
        self.agent_id = f"{agent_name}_{uuid.uuid4().hex[:8]}"

        # Core components
        self.orchestrator_bridge = orchestrator_bridge or MockOrchestratorBridge()
        self.circuit_breaker = CircuitBreaker()
        self.message_queue = MessageQueue()
        self.profiler = PerformanceProfiler()

        # Execution context
        self.execution_mode = ExecutionMode.PYTHON_ONLY
        self.capabilities = self._define_capabilities()
        self.performance_profile = self._create_performance_profile()

        # State management
        self.is_running = False
        self.health_status = HealthStatus.UNKNOWN
        self.pending_requests = {}
        self.active_tasks = {}

        # Cache
        self.cache = {}
        self.cache_ttl = {}
        self.default_cache_ttl = 300  # 5 minutes

        # Metrics
        self.metrics = {
            "total_commands": 0,
            "success": 0,
            "errors": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "delegated_tasks": 0,
            "received_delegations": 0,
        }

        # Health monitoring
        self._health_check_interval = 30  # seconds
        self._health_check_task = None
        self._last_health_report = None

    async def initialize(self) -> bool:
        """Initialize orchestration components"""
        try:
            # Start message queue
            await self.message_queue.start()

            # Register message handlers
            self._register_message_handlers()

            # Register with orchestrator
            success = await self.orchestrator_bridge.register_agent(
                self.agent_id, self.capabilities
            )

            if success:
                self.health_status = HealthStatus.HEALTHY
                self.is_running = True

                # Start health monitoring
                self._health_check_task = asyncio.create_task(
                    self._health_monitor_loop()
                )

                logger.info(f"Agent {self.agent_name} initialized successfully")
                return True
            else:
                logger.error(f"Failed to register agent {self.agent_name}")
                return False

        except Exception as e:
            logger.error(f"Error initializing agent {self.agent_name}: {e}")
            self.health_status = HealthStatus.UNHEALTHY
            return False

    async def shutdown(self):
        """Graceful shutdown"""
        try:
            self.is_running = False

            # Stop health monitoring
            if self._health_check_task:
                self._health_check_task.cancel()

            # Stop message queue
            await self.message_queue.stop()

            # Deregister from orchestrator
            await self.orchestrator_bridge.deregister_agent(self.agent_id)

            logger.info(f"Agent {self.agent_name} shut down gracefully")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def execute_with_orchestration(
        self, command: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute command with full orchestration support"""
        if not self.is_running:
            raise RuntimeError("Agent not initialized")

        start_time = time.time()
        success = False

        try:
            # Create task
            task = AgentTask(
                id=str(uuid.uuid4()),
                action=command.get("action", "default"),
                context=command,
                timeout=command.get("timeout", 300),
            )

            # Add to active tasks
            self.active_tasks[task.id] = task
            task.started_at = datetime.now(timezone.utc)

            # Execute with circuit breaker
            result = await self.circuit_breaker.call(
                self._execute_command_internal, task
            )

            # Mark as completed
            task.completed_at = datetime.now(timezone.utc)
            success = True

            # Update metrics
            execution_time = time.time() - start_time
            self.metrics["total_commands"] += 1
            self.metrics["success"] += 1
            self.profiler.record_execution(execution_time, True)

            return {
                "status": "success",
                "result": result,
                "task_id": task.id,
                "execution_time": execution_time,
                "agent_id": self.agent_id,
            }

        except Exception as e:
            execution_time = time.time() - start_time
            self.metrics["errors"] += 1
            self.profiler.record_execution(execution_time, False)

            logger.error(f"Command execution failed: {e}")

            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_time": execution_time,
                "agent_id": self.agent_id,
            }

        finally:
            # Clean up active tasks
            if "task" in locals():
                self.active_tasks.pop(task.id, None)

    async def delegate_to_agent(
        self, target_agent: str, task_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delegate task to another agent"""
        try:
            task = AgentTask(
                id=str(uuid.uuid4()),
                action=task_spec.get("action"),
                context=task_spec.get("context", {}),
                priority=TaskPriority(task_spec.get("priority", "medium")),
                timeout=task_spec.get("timeout", 300),
            )

            result = await self.orchestrator_bridge.request_delegation(
                target_agent, task
            )
            self.metrics["delegated_tasks"] += 1

            return result

        except Exception as e:
            logger.error(f"Delegation to {target_agent} failed: {e}")
            return {"status": "error", "error": str(e)}

    async def send_inter_agent_message(
        self, target_agent: str, message_type: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send message to another agent"""
        message = InterAgentMessage(
            id=str(uuid.uuid4()),
            source_agent=self.agent_id,
            target_agent=target_agent,
            message_type=message_type,
            payload=payload,
        )

        return await self.orchestrator_bridge.send_message(target_agent, message)

    def get_cache(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            self.metrics["cache_misses"] += 1
            return None

        # Check TTL
        if key in self.cache_ttl:
            if datetime.now(timezone.utc) > self.cache_ttl[key]:
                del self.cache[key]
                del self.cache_ttl[key]
                self.metrics["cache_misses"] += 1
                return None

        self.metrics["cache_hits"] += 1
        self.profiler.cache_hits += 1
        return self.cache[key]

    def set_cache(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        self.cache[key] = value
        if ttl or self.default_cache_ttl:
            ttl_seconds = ttl or self.default_cache_ttl
            self.cache_ttl[key] = datetime.now(timezone.utc) + timedelta(
                seconds=ttl_seconds
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics"""
        base_metrics = dict(self.metrics)
        profiler_metrics = self.profiler.get_metrics()
        percentiles = self.profiler.get_percentiles()

        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "health_status": self.health_status.value,
            "execution_mode": self.execution_mode.value,
            "active_tasks": len(self.active_tasks),
            "cache_size": len(self.cache),
            "base_metrics": base_metrics,
            "performance": {
                "success_rate": profiler_metrics.success_rate,
                "avg_execution_time": profiler_metrics.avg_execution_time,
                "cpu_usage": profiler_metrics.cpu_usage,
                "memory_usage_mb": profiler_metrics.memory_usage,
                "cache_hit_rate": profiler_metrics.cache_hit_rate,
            },
            "percentiles": percentiles,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Abstract methods to be implemented by subclasses
    @abstractmethod
    async def _execute_command_internal(self, task: AgentTask) -> Dict[str, Any]:
        """Execute agent-specific command logic"""
        pass

    @abstractmethod
    def _define_capabilities(self) -> Dict[str, Any]:
        """Define agent capabilities"""
        pass

    def _create_performance_profile(self) -> Dict[str, Any]:
        """Create performance profile"""
        return {
            "expected_latency_ms": 100,
            "max_concurrent_tasks": 10,
            "memory_usage_mb": 100,
            "cpu_intensity": "medium",
            "supports_parallel_execution": True,
            "cache_enabled": True,
        }

    def _register_message_handlers(self):
        """Register handlers for different message types"""
        self.message_queue.register_handler(
            "delegation", self._handle_delegation_message
        )
        self.message_queue.register_handler(
            "health_check", self._handle_health_check_message
        )
        self.message_queue.register_handler(
            "metrics_request", self._handle_metrics_request_message
        )

    async def _handle_delegation_message(self, message: InterAgentMessage):
        """Handle incoming delegation message"""
        try:
            payload = message.payload
            task = AgentTask(
                id=payload.get("task_id", str(uuid.uuid4())),
                action=payload.get("action"),
                context=payload.get("context", {}),
                timeout=payload.get("timeout", 300),
            )

            result = await self._execute_command_internal(task)
            self.metrics["received_delegations"] += 1

            # Send response back
            response = InterAgentMessage(
                id=str(uuid.uuid4()),
                source_agent=self.agent_id,
                target_agent=message.source_agent,
                message_type="delegation_response",
                payload={"task_id": task.id, "status": "completed", "result": result},
                correlation_id=message.id,
            )

            await self.message_queue.send_message(response)

        except Exception as e:
            logger.error(f"Error handling delegation: {e}")

    async def _handle_health_check_message(self, message: InterAgentMessage):
        """Handle health check message"""
        health_data = {
            "agent_id": self.agent_id,
            "status": self.health_status.value,
            "metrics": self.get_metrics(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        response = InterAgentMessage(
            id=str(uuid.uuid4()),
            source_agent=self.agent_id,
            target_agent=message.source_agent,
            message_type="health_response",
            payload=health_data,
            correlation_id=message.id,
        )

        await self.message_queue.send_message(response)

    async def _handle_metrics_request_message(self, message: InterAgentMessage):
        """Handle metrics request message"""
        metrics_data = self.get_metrics()

        response = InterAgentMessage(
            id=str(uuid.uuid4()),
            source_agent=self.agent_id,
            target_agent=message.source_agent,
            message_type="metrics_response",
            payload=metrics_data,
            correlation_id=message.id,
        )

        await self.message_queue.send_message(response)

    async def _health_monitor_loop(self):
        """Health monitoring loop"""
        while self.is_running:
            try:
                await asyncio.sleep(self._health_check_interval)

                # Determine health status
                metrics = self.profiler.get_metrics()

                if metrics.success_rate < 0.5:
                    self.health_status = HealthStatus.UNHEALTHY
                elif metrics.success_rate < 0.9:
                    self.health_status = HealthStatus.DEGRADED
                else:
                    self.health_status = HealthStatus.HEALTHY

                # Report to orchestrator
                await self.orchestrator_bridge.report_health(
                    self.agent_id, self.health_status, metrics
                )

                self._last_health_report = datetime.now(timezone.utc)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                self.health_status = HealthStatus.UNHEALTHY


# Export the main class and supporting types
__all__ = [
    "TandemOrchestrationBase",
    "OrchestratorBridge",
    "MockOrchestratorBridge",
    "AgentTask",
    "InterAgentMessage",
    "MetricsSnapshot",
    "ExecutionMode",
    "TaskPriority",
    "HealthStatus",
    "CircuitBreakerState",
]
