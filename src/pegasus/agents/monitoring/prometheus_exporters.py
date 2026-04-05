#!/usr/bin/env python3
"""
Prometheus Metrics Exporters for Claude Agent Communication System
Provides comprehensive observability for all 28 agent types and transport layer
"""

import asyncio
import ctypes
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import psutil
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Enum,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
    start_http_server,
)
from prometheus_client.core import REGISTRY

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the ultra-fast protocol library for native metrics
try:
    libufp = ctypes.CDLL("./ultra_fast_protocol_core.so")
except OSError:
    logger.warning("Ultra-fast protocol library not found, using simulation")
    libufp = None

# Agent types from the system
AGENT_TYPES = [
    "DIRECTOR",
    "PROJECT_ORCHESTRATOR",
    "ARCHITECT",
    "CONSTRUCTOR",
    "SECURITY",
    "TESTBED",
    "OPTIMIZER",
    "DEBUGGER",
    "DEPLOYER",
    "MONITOR",
    "DATABASE",
    "ML_OPS",
    "WEB",
    "PATCHER",
    "LINTER",
    "DOCGEN",
    "PACKAGER",
    "API_DESIGNER",
    "C_INTERNAL",
    "PYTHON_INTERNAL",
    "MOBILE",
    "PYGUI",
    "TUI",
    "VOICE_RECOGNITION",
    "VOICE_BIOMETRIC",
    "AUDIO_CAPTURE",
    "VOICE_ORCHESTRATOR",
    "VOICE_ENHANCER",
]


@dataclass
class AgentMetrics:
    """Metrics container for individual agents"""

    __slots__ = []
    name: str
    status: str
    message_count: int
    processing_time: float
    error_count: int
    memory_usage: int
    cpu_usage: float
    queue_depth: int
    last_heartbeat: float


class PrometheusAgentExporter:
    """Main Prometheus metrics exporter for agent system"""

    __slots__ = []

    def __init__(self, port: int = 8000):
        self.port = port
        self.registry = CollectorRegistry()

        # Transport Layer Metrics (Ultra-Fast Protocol)
        self.transport_messages_total = Counter(
            "agent_transport_messages_total",
            "Total messages processed by transport layer",
            ["direction", "msg_type", "priority"],
            registry=self.registry,
        )

        self.transport_bytes_total = Counter(
            "agent_transport_bytes_total",
            "Total bytes processed by transport layer",
            ["direction"],
            registry=self.registry,
        )

        self.transport_latency = Histogram(
            "agent_transport_latency_seconds",
            "Message transport latency",
            ["msg_type", "priority"],
            buckets=[
                0.001,
                0.005,
                0.01,
                0.025,
                0.05,
                0.075,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
            ],
            registry=self.registry,
        )

        self.transport_throughput = Gauge(
            "agent_transport_throughput_mps",
            "Current transport throughput in messages per second",
            registry=self.registry,
        )

        self.transport_errors_total = Counter(
            "agent_transport_errors_total",
            "Transport layer errors",
            ["error_type", "severity"],
            registry=self.registry,
        )

        # Agent-specific metrics
        self.agent_status = Enum(
            "agent_status",
            "Current status of agent",
            ["agent_id", "agent_type"],
            states=["idle", "running", "completed", "failed", "blocked"],
            registry=self.registry,
        )

        self.agent_messages_processed = Counter(
            "agent_messages_processed_total",
            "Total messages processed by agent",
            ["agent_id", "agent_type", "source_agent", "action"],
            registry=self.registry,
        )

        self.agent_processing_time = Histogram(
            "agent_processing_time_seconds",
            "Time spent processing messages",
            ["agent_id", "agent_type", "action"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0],
            registry=self.registry,
        )

        self.agent_queue_depth = Gauge(
            "agent_queue_depth",
            "Current message queue depth",
            ["agent_id", "agent_type"],
            registry=self.registry,
        )

        self.agent_resource_usage = Gauge(
            "agent_resource_usage",
            "Resource usage by agent",
            ["agent_id", "agent_type", "resource"],
            registry=self.registry,
        )

        self.agent_errors = Counter(
            "agent_errors_total",
            "Total errors by agent",
            ["agent_id", "agent_type", "error_type"],
            registry=self.registry,
        )

        # System-wide metrics
        self.system_active_agents = Gauge(
            "system_active_agents",
            "Number of active agents by type",
            ["agent_type"],
            registry=self.registry,
        )

        self.system_message_flow = Gauge(
            "system_message_flow",
            "Message flow between agent types",
            ["source_type", "target_type"],
            registry=self.registry,
        )

        # Performance metrics
        self.performance_bottlenecks = Gauge(
            "performance_bottlenecks",
            "Performance bottleneck indicators",
            ["bottleneck_type", "severity"],
            registry=self.registry,
        )

        self.capacity_utilization = Gauge(
            "capacity_utilization_ratio",
            "System capacity utilization",
            ["resource_type"],
            registry=self.registry,
        )

        # Health metrics
        self.agent_health_score = Gauge(
            "agent_health_score",
            "Agent health score (0-100)",
            ["agent_id", "agent_type"],
            registry=self.registry,
        )

        self.failure_prediction_score = Gauge(
            "failure_prediction_score",
            "Failure prediction score (0-100)",
            ["agent_id", "agent_type"],
            registry=self.registry,
        )

        # Message flow visualization metrics
        self.message_flow_matrix = Gauge(
            "message_flow_matrix",
            "Message flow between specific agents",
            ["source_agent", "target_agent", "message_type"],
            registry=self.registry,
        )

        # Cache for metrics updates
        self._metrics_cache = {}
        self._last_update = 0

    async def start_server(self):
        """Start the Prometheus metrics HTTP server"""
        try:
            start_http_server(self.port, registry=self.registry)
            logger.info(f"Prometheus metrics server started on port {self.port}")

            # Start metrics collection loop
            asyncio.create_task(self._collect_metrics_loop())

        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")

    async def _collect_metrics_loop(self):
        """Main metrics collection loop"""
        while True:
            try:
                await self._collect_transport_metrics()
                await self._collect_agent_metrics()
                await self._collect_system_metrics()
                await self._collect_performance_metrics()
                await self._update_health_metrics()

                await asyncio.sleep(1.0)  # Collect every second

            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(5.0)

    async def _collect_transport_metrics(self):
        """Collect ultra-fast protocol transport metrics"""
        if libufp:
            # Get native stats from C library
            stats = self._get_native_transport_stats()

            # Update transport metrics
            self.transport_throughput.set(stats.get("throughput_mps", 0))

            # Message type breakdown
            for msg_type, count in stats.get("message_types", {}).items():
                for priority in ["critical", "high", "medium", "low"]:
                    self.transport_messages_total.labels(
                        direction="sent", msg_type=msg_type, priority=priority
                    ).inc(count.get(priority, 0))

            # Latency histogram
            for msg_type, latencies in stats.get("latencies", {}).items():
                for priority, latency in latencies.items():
                    self.transport_latency.labels(
                        msg_type=msg_type, priority=priority
                    ).observe(
                        latency / 1e9
                    )  # Convert ns to seconds

        else:
            # Simulate metrics for development
            self.transport_throughput.set(4200000)  # 4.2M messages/sec

    async def _collect_agent_metrics(self):
        """Collect metrics for all agents"""
        agent_metrics = await self._get_agent_metrics()

        for agent_id, metrics in agent_metrics.items():
            agent_type = metrics.get("type", "unknown")

            # Update agent status
            self.agent_status.labels(agent_id=agent_id, agent_type=agent_type).state(
                metrics.get("status", "unknown")
            )

            # Update resource usage
            self.agent_resource_usage.labels(
                agent_id=agent_id, agent_type=agent_type, resource="cpu"
            ).set(metrics.get("cpu_usage", 0))

            self.agent_resource_usage.labels(
                agent_id=agent_id, agent_type=agent_type, resource="memory"
            ).set(metrics.get("memory_usage", 0))

            # Update queue depth
            self.agent_queue_depth.labels(agent_id=agent_id, agent_type=agent_type).set(
                metrics.get("queue_depth", 0)
            )

            # Update health score
            self.agent_health_score.labels(
                agent_id=agent_id, agent_type=agent_type
            ).set(self._calculate_health_score(metrics))

    async def _collect_system_metrics(self):
        """Collect system-wide metrics"""
        # Count active agents by type
        agent_counts = {}
        agent_metrics = await self._get_agent_metrics()

        for agent_id, metrics in agent_metrics.items():
            agent_type = metrics.get("type", "unknown")
            if metrics.get("status") in ["running", "idle"]:
                agent_counts[agent_type] = agent_counts.get(agent_type, 0) + 1

        for agent_type in AGENT_TYPES:
            self.system_active_agents.labels(agent_type=agent_type).set(
                agent_counts.get(agent_type, 0)
            )

        # Capacity utilization
        self.capacity_utilization.labels(resource_type="cpu").set(psutil.cpu_percent())
        self.capacity_utilization.labels(resource_type="memory").set(
            psutil.virtual_memory().percent
        )
        self.capacity_utilization.labels(resource_type="network").set(
            self._get_network_utilization()
        )

    async def _collect_performance_metrics(self):
        """Collect performance and bottleneck metrics"""
        # Detect bottlenecks
        bottlenecks = self._detect_bottlenecks()

        for bottleneck_type, severity in bottlenecks.items():
            self.performance_bottlenecks.labels(
                bottleneck_type=bottleneck_type, severity=severity
            ).set(1 if severity > 0.7 else 0)

    async def _update_health_metrics(self):
        """Update health and failure prediction metrics"""
        agent_metrics = await self._get_agent_metrics()

        for agent_id, metrics in agent_metrics.items():
            agent_type = metrics.get("type", "unknown")

            # Calculate failure prediction score
            failure_score = self._predict_failure(metrics)
            self.failure_prediction_score.labels(
                agent_id=agent_id, agent_type=agent_type
            ).set(failure_score)

    def _get_native_transport_stats(self) -> dict:
        """Get transport statistics from native C library"""
        if not libufp:
            return {}

        # This would call into the C library to get real stats
        # For now, return simulated data
        return {
            "throughput_mps": 4200000,
            "message_types": {
                "REQUEST": {
                    "critical": 1000,
                    "high": 5000,
                    "medium": 10000,
                    "low": 20000,
                },
                "RESPONSE": {
                    "critical": 800,
                    "high": 4000,
                    "medium": 8000,
                    "low": 15000,
                },
                "BROADCAST": {"critical": 100, "high": 200, "medium": 500, "low": 1000},
            },
            "latencies": {
                "REQUEST": {
                    "critical": 100000,
                    "high": 200000,
                    "medium": 500000,
                    "low": 1000000,
                },
                "RESPONSE": {
                    "critical": 80000,
                    "high": 150000,
                    "medium": 300000,
                    "low": 800000,
                },
            },
        }

    async def _get_agent_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get current metrics for all agents"""
        # This would integrate with the actual agent system
        # For now, return simulated data
        metrics = {}

        for i, agent_type in enumerate(AGENT_TYPES):
            agent_id = f"{agent_type.lower()}_{i:03d}"
            metrics[agent_id] = {
                "type": agent_type,
                "status": "running" if i % 4 != 0 else "idle",
                "cpu_usage": min(100, max(0, 20 + (i * 7) % 80)),
                "memory_usage": min(100, max(10, 30 + (i * 5) % 60)),
                "queue_depth": max(0, (i * 3) % 50),
                "error_rate": (i * 0.1) % 5,
                "last_heartbeat": time.time() - (i % 30),
                "processing_time": 0.1 + (i * 0.05) % 2.0,
            }

        return metrics

    def _calculate_health_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate health score for an agent (0-100)"""
        score = 100.0

        # Deduct for high resource usage
        if metrics.get("cpu_usage", 0) > 80:
            score -= 20
        elif metrics.get("cpu_usage", 0) > 60:
            score -= 10

        # Deduct for high memory usage
        if metrics.get("memory_usage", 0) > 90:
            score -= 20
        elif metrics.get("memory_usage", 0) > 70:
            score -= 10

        # Deduct for queue backup
        queue_depth = metrics.get("queue_depth", 0)
        if queue_depth > 100:
            score -= 30
        elif queue_depth > 50:
            score -= 15

        # Deduct for errors
        error_rate = metrics.get("error_rate", 0)
        score -= min(40, error_rate * 8)

        # Deduct for stale heartbeat
        last_heartbeat = metrics.get("last_heartbeat", time.time())
        heartbeat_age = time.time() - last_heartbeat
        if heartbeat_age > 60:  # More than 1 minute
            score -= 50
        elif heartbeat_age > 30:  # More than 30 seconds
            score -= 25

        return max(0, score)

    def _predict_failure(self, metrics: Dict[str, Any]) -> float:
        """Predict failure probability for an agent (0-100)"""
        failure_score = 0.0

        # High resource usage increases failure probability
        cpu_usage = metrics.get("cpu_usage", 0)
        memory_usage = metrics.get("memory_usage", 0)

        if cpu_usage > 90 or memory_usage > 95:
            failure_score += 40
        elif cpu_usage > 80 or memory_usage > 85:
            failure_score += 20

        # Error rate trend
        error_rate = metrics.get("error_rate", 0)
        failure_score += min(30, error_rate * 6)

        # Queue backup
        queue_depth = metrics.get("queue_depth", 0)
        if queue_depth > 200:
            failure_score += 30
        elif queue_depth > 100:
            failure_score += 15

        # Slow processing
        processing_time = metrics.get("processing_time", 0)
        if processing_time > 10:
            failure_score += 20
        elif processing_time > 5:
            failure_score += 10

        return min(100, failure_score)

    def _detect_bottlenecks(self) -> Dict[str, float]:
        """Detect system performance bottlenecks"""
        bottlenecks = {}

        # CPU bottleneck
        cpu_usage = psutil.cpu_percent()
        if cpu_usage > 90:
            bottlenecks["cpu"] = 1.0
        elif cpu_usage > 80:
            bottlenecks["cpu"] = 0.8
        else:
            bottlenecks["cpu"] = 0.0

        # Memory bottleneck
        memory_usage = psutil.virtual_memory().percent
        if memory_usage > 95:
            bottlenecks["memory"] = 1.0
        elif memory_usage > 85:
            bottlenecks["memory"] = 0.8
        else:
            bottlenecks["memory"] = 0.0

        # Network bottleneck
        network_util = self._get_network_utilization()
        if network_util > 90:
            bottlenecks["network"] = 1.0
        elif network_util > 80:
            bottlenecks["network"] = 0.8
        else:
            bottlenecks["network"] = 0.0

        # Message queue bottleneck
        bottlenecks["message_queue"] = (
            0.0  # Would be calculated from actual queue metrics
        )

        return bottlenecks

    def _get_network_utilization(self) -> float:
        """Get network utilization percentage"""
        try:
            # This is a simplified calculation
            net_io = psutil.net_io_counters()
            # Would need to track over time for real utilization
            return min(
                100, (net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024) % 100
            )
        except:
            return 0.0

    def record_message(
        self,
        source_agent: str,
        target_agent: str,
        message_type: str,
        processing_time: float,
    ):
        """Record a message processing event"""
        # Extract agent types
        source_type = (
            source_agent.split("_")[0] if "_" in source_agent else source_agent
        )
        target_type = (
            target_agent.split("_")[0] if "_" in target_agent else target_agent
        )

        # Update metrics
        self.agent_messages_processed.labels(
            agent_id=target_agent,
            agent_type=target_type,
            source_agent=source_agent,
            action=message_type,
        ).inc()

        self.agent_processing_time.labels(
            agent_id=target_agent, agent_type=target_type, action=message_type
        ).observe(processing_time)

        # Update message flow matrix
        self.message_flow_matrix.labels(
            source_agent=source_agent,
            target_agent=target_agent,
            message_type=message_type,
        ).inc()


class OpenTelemetryIntegration:
    """OpenTelemetry tracing integration for the agent system"""

    __slots__ = []

    def __init__(self):
        self.tracer = None
        self._setup_tracing()

    def _setup_tracing(self):
        """Set up OpenTelemetry tracing"""
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            # Configure tracer
            trace.set_tracer_provider(TracerProvider())
            self.tracer = trace.get_tracer(__name__)

            # Configure Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
            )

            # Add span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)

            logger.info("OpenTelemetry tracing configured")

        except ImportError:
            logger.warning("OpenTelemetry not available, skipping tracing setup")

    def trace_message_flow(
        self,
        source_agent: str,
        target_agent: str,
        message_type: str,
        correlation_id: str,
    ):
        """Create a trace span for message flow"""
        if not self.tracer:
            return None

        span = self.tracer.start_span(f"agent_message_{message_type}")
        span.set_attribute("source.agent", source_agent)
        span.set_attribute("target.agent", target_agent)
        span.set_attribute("message.type", message_type)
        span.set_attribute("correlation.id", correlation_id)

        return span


# Main application
async def main():
    """Main application entry point"""
    logger.info("Starting Claude Agent Communication System Monitoring")

    # Create exporter
    exporter = PrometheusAgentExporter(port=8000)

    # Start metrics server
    await exporter.start_server()

    # Keep running
    try:
        while True:
            await asyncio.sleep(60)
            logger.info("Monitoring system running...")
    except KeyboardInterrupt:
        logger.info("Shutting down monitoring system")


if __name__ == "__main__":
    asyncio.run(main())
