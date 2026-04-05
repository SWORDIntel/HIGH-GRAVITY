#!/usr/bin/env python3
"""
TANDEM ORCHESTRATION SYSTEM - METRICS AND MONITORING
Advanced metrics collection system for production deployment
Integrates with Prometheus, Grafana, and custom monitoring systems
Provides comprehensive observability for all 31 agents
"""

import asyncio
import json
import logging
import socketserver
import threading
import time
import urllib.parse
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

# HTTP server for metrics endpoint
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil

# Prometheus client for metrics export
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    generate_latest,
    start_http_server,
)

logger = logging.getLogger(__name__)

# ============================================================================
# METRICS DATA STRUCTURES
# ============================================================================


@dataclass
class AgentMetrics:
    """Individual agent performance metrics"""

    agent_name: str
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    last_execution_time: float = 0.0
    health_score: float = 100.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    last_updated: datetime = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


@dataclass
class SystemMetrics:
    """System-wide performance metrics"""

    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    thermal_data: Dict[str, float]
    load_average: List[float]
    active_agents: int
    healthy_agents: int
    total_messages_processed: int
    messages_per_second: float


@dataclass
class CommunicationMetrics:
    """Communication system metrics"""

    total_messages: int = 0
    successful_messages: int = 0
    failed_messages: int = 0
    average_latency: float = 0.0
    max_latency: float = 0.0
    min_latency: float = float("inf")
    throughput: float = 0.0
    queue_depth: int = 0
    active_connections: int = 0


# ============================================================================
# METRICS COLLECTORS
# ============================================================================


class MetricsCollector(ABC):
    """Base class for metrics collectors"""

    @abstractmethod
    async def collect(self) -> Dict[str, Any]:
        """Collect metrics data"""
        pass


class SystemMetricsCollector(MetricsCollector):
    """Collects system-level metrics"""

    def __init__(self):
        self.network_stats_prev = psutil.net_io_counters()
        self.last_collection_time = time.time()

    async def collect(self) -> SystemMetrics:
        """Collect current system metrics"""
        current_time = time.time()
        time_delta = current_time - self.last_collection_time

        # CPU and memory
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Network I/O
        network_stats = psutil.net_io_counters()
        network_io = {
            "bytes_sent": network_stats.bytes_sent - self.network_stats_prev.bytes_sent,
            "bytes_recv": network_stats.bytes_recv - self.network_stats_prev.bytes_recv,
            "packets_sent": network_stats.packets_sent
            - self.network_stats_prev.packets_sent,
            "packets_recv": network_stats.packets_recv
            - self.network_stats_prev.packets_recv,
        }
        self.network_stats_prev = network_stats

        # Thermal data (if available)
        thermal_data = {}
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                for sensor_name, sensor_list in temps.items():
                    for i, sensor in enumerate(sensor_list):
                        thermal_data[f"{sensor_name}_{i}"] = sensor.current
        except Exception as e:
            logger.debug(f"Could not collect thermal data: {e}")

        # Load average (if available)
        load_avg = (
            list(psutil.getloadavg())
            if hasattr(psutil, "getloadavg")
            else [0.0, 0.0, 0.0]
        )

        self.last_collection_time = current_time

        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            network_io=network_io,
            thermal_data=thermal_data,
            load_average=load_avg,
            active_agents=0,  # To be set by orchestrator
            healthy_agents=0,  # To be set by orchestrator
            total_messages_processed=0,  # To be set by orchestrator
            messages_per_second=0.0,  # To be set by orchestrator
        )


class AgentMetricsCollector(MetricsCollector):
    """Collects agent-specific metrics"""

    def __init__(self):
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.execution_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )

    def record_agent_execution(
        self, agent_name: str, execution_time: float, success: bool
    ):
        """Record an agent execution"""
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = AgentMetrics(agent_name=agent_name)

        metrics = self.agent_metrics[agent_name]
        metrics.execution_count += 1
        metrics.last_execution_time = execution_time
        metrics.total_execution_time += execution_time
        metrics.average_execution_time = (
            metrics.total_execution_time / metrics.execution_count
        )

        if success:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1

        # Update health score based on recent performance
        success_rate = metrics.success_count / metrics.execution_count
        metrics.health_score = min(100.0, success_rate * 100.0)

        metrics.last_updated = datetime.now()

        # Store in history for trend analysis
        self.execution_history[agent_name].append(
            {
                "timestamp": time.time(),
                "execution_time": execution_time,
                "success": success,
            }
        )

    def update_agent_resources(
        self, agent_name: str, cpu_usage: float, memory_usage: float
    ):
        """Update agent resource usage"""
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = AgentMetrics(agent_name=agent_name)

        self.agent_metrics[agent_name].cpu_usage = cpu_usage
        self.agent_metrics[agent_name].memory_usage = memory_usage
        self.agent_metrics[agent_name].last_updated = datetime.now()

    async def collect(self) -> Dict[str, AgentMetrics]:
        """Return current agent metrics"""
        return self.agent_metrics.copy()


class CommunicationMetricsCollector(MetricsCollector):
    """Collects communication system metrics"""

    def __init__(self):
        self.metrics = CommunicationMetrics()
        self.latency_history = deque(maxlen=1000)
        self.message_timestamps = deque(maxlen=10000)
        self.lock = threading.Lock()

    def record_message(self, latency: float, success: bool):
        """Record a communication message"""
        with self.lock:
            current_time = time.time()

            self.metrics.total_messages += 1
            if success:
                self.metrics.successful_messages += 1
            else:
                self.metrics.failed_messages += 1

            # Update latency statistics
            self.latency_history.append(latency)
            if latency > self.metrics.max_latency:
                self.metrics.max_latency = latency
            if latency < self.metrics.min_latency:
                self.metrics.min_latency = latency

            # Calculate average latency
            if self.latency_history:
                self.metrics.average_latency = sum(self.latency_history) / len(
                    self.latency_history
                )

            # Track message timestamps for throughput calculation
            self.message_timestamps.append(current_time)

            # Calculate throughput (messages per second over last 60 seconds)
            cutoff_time = current_time - 60.0
            recent_messages = [
                ts for ts in self.message_timestamps if ts >= cutoff_time
            ]
            self.metrics.throughput = len(recent_messages) / 60.0

    async def collect(self) -> CommunicationMetrics:
        """Return current communication metrics"""
        with self.lock:
            return CommunicationMetrics(**asdict(self.metrics))


# ============================================================================
# PROMETHEUS INTEGRATION
# ============================================================================


class PrometheusExporter:
    """Exports metrics to Prometheus format"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()

    def _setup_metrics(self):
        """Setup Prometheus metrics"""
        # Agent metrics
        self.agent_executions = Counter(
            "agent_executions_total",
            "Total number of agent executions",
            ["agent_name", "status"],
            registry=self.registry,
        )

        self.agent_execution_duration = Histogram(
            "agent_execution_duration_seconds",
            "Agent execution duration",
            ["agent_name"],
            registry=self.registry,
        )

        self.agent_health_score = Gauge(
            "agent_health_score",
            "Agent health score (0-100)",
            ["agent_name"],
            registry=self.registry,
        )

        self.agent_cpu_usage = Gauge(
            "agent_cpu_usage_percent",
            "Agent CPU usage percentage",
            ["agent_name"],
            registry=self.registry,
        )

        self.agent_memory_usage = Gauge(
            "agent_memory_usage_bytes",
            "Agent memory usage in bytes",
            ["agent_name"],
            registry=self.registry,
        )

        # System metrics
        self.system_cpu_usage = Gauge(
            "system_cpu_usage_percent",
            "System CPU usage percentage",
            registry=self.registry,
        )

        self.system_memory_usage = Gauge(
            "system_memory_usage_percent",
            "System memory usage percentage",
            registry=self.registry,
        )

        self.system_disk_usage = Gauge(
            "system_disk_usage_percent",
            "System disk usage percentage",
            registry=self.registry,
        )

        self.system_load_average = Gauge(
            "system_load_average",
            "System load average",
            ["period"],
            registry=self.registry,
        )

        self.system_temperature = Gauge(
            "system_temperature_celsius",
            "System temperature in Celsius",
            ["sensor"],
            registry=self.registry,
        )

        # Communication metrics
        self.communication_messages = Counter(
            "communication_messages_total",
            "Total communication messages",
            ["status"],
            registry=self.registry,
        )

        self.communication_latency = Histogram(
            "communication_latency_seconds",
            "Communication latency",
            registry=self.registry,
        )

        self.communication_throughput = Gauge(
            "communication_throughput_messages_per_second",
            "Communication throughput",
            registry=self.registry,
        )

    def update_agent_metrics(self, agent_metrics: Dict[str, AgentMetrics]):
        """Update agent metrics in Prometheus"""
        for agent_name, metrics in agent_metrics.items():
            # Update counters
            self.agent_executions.labels(
                agent_name=agent_name, status="success"
            )._value._value = metrics.success_count

            self.agent_executions.labels(
                agent_name=agent_name, status="failure"
            )._value._value = metrics.failure_count

            # Update gauges
            self.agent_health_score.labels(agent_name=agent_name).set(
                metrics.health_score
            )
            self.agent_cpu_usage.labels(agent_name=agent_name).set(metrics.cpu_usage)
            self.agent_memory_usage.labels(agent_name=agent_name).set(
                metrics.memory_usage
            )

            # Update histogram (approximate)
            if metrics.execution_count > 0:
                # This is an approximation since we can't update histograms retroactively
                for _ in range(metrics.execution_count):
                    self.agent_execution_duration.labels(agent_name=agent_name).observe(
                        metrics.average_execution_time
                    )

    def update_system_metrics(self, system_metrics: SystemMetrics):
        """Update system metrics in Prometheus"""
        self.system_cpu_usage.set(system_metrics.cpu_usage)
        self.system_memory_usage.set(system_metrics.memory_usage)
        self.system_disk_usage.set(system_metrics.disk_usage)

        # Load averages
        for i, period in enumerate(["1m", "5m", "15m"]):
            if i < len(system_metrics.load_average):
                self.system_load_average.labels(period=period).set(
                    system_metrics.load_average[i]
                )

        # Temperature sensors
        for sensor_name, temperature in system_metrics.thermal_data.items():
            self.system_temperature.labels(sensor=sensor_name).set(temperature)

    def update_communication_metrics(self, comm_metrics: CommunicationMetrics):
        """Update communication metrics in Prometheus"""
        self.communication_messages.labels(status="success")._value._value = (
            comm_metrics.successful_messages
        )
        self.communication_messages.labels(status="failure")._value._value = (
            comm_metrics.failed_messages
        )
        self.communication_throughput.set(comm_metrics.throughput)

    def generate_metrics(self) -> str:
        """Generate Prometheus metrics output"""
        return generate_latest(self.registry).decode("utf-8")


# ============================================================================
# HTTP METRICS SERVER
# ============================================================================


class MetricsHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for serving metrics"""

    def __init__(self, metrics_manager, *args, **kwargs):
        self.metrics_manager = metrics_manager
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path == "/metrics":
            # Prometheus metrics endpoint
            try:
                metrics_data = (
                    self.metrics_manager.prometheus_exporter.generate_metrics()
                )
                self.send_response(200)
                self.send_header("Content-Type", CONTENT_TYPE_LATEST)
                self.end_headers()
                self.wfile.write(metrics_data.encode("utf-8"))
            except Exception as e:
                logger.error(f"Error serving metrics: {e}")
                self.send_error(500, str(e))

        elif parsed_path.path == "/health":
            # Health check endpoint
            try:
                health_data = self.metrics_manager.get_health_summary()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(health_data, indent=2).encode("utf-8"))
            except Exception as e:
                logger.error(f"Error serving health data: {e}")
                self.send_error(500, str(e))

        elif parsed_path.path == "/status":
            # Detailed status endpoint
            try:
                status_data = self.metrics_manager.get_detailed_status()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(status_data, indent=2, default=str).encode("utf-8")
                )
            except Exception as e:
                logger.error(f"Error serving status data: {e}")
                self.send_error(500, str(e))

        else:
            self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"HTTP {self.address_string()} - {format % args}")


# ============================================================================
# MAIN METRICS MANAGER
# ============================================================================


class OrchestratorMetricsManager:
    """Main metrics management system"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Initialize collectors
        self.system_collector = SystemMetricsCollector()
        self.agent_collector = AgentMetricsCollector()
        self.comm_collector = CommunicationMetricsCollector()

        # Initialize Prometheus exporter
        self.prometheus_exporter = PrometheusExporter()

        # HTTP server for metrics endpoint
        self.http_server = None
        self.metrics_thread = None

        # Collection settings
        self.collection_interval = self.config.get("collection_interval", 30)
        self.running = False

        # Historical data storage
        self.system_history = deque(maxlen=1000)
        self.agent_history = defaultdict(lambda: deque(maxlen=1000))

    async def start(self):
        """Start the metrics collection system"""
        logger.info("Starting Orchestrator Metrics Manager")

        self.running = True

        # Start HTTP server
        self._start_http_server()

        # Start collection loop
        asyncio.create_task(self._collection_loop())

        logger.info("Metrics Manager started successfully")

    async def stop(self):
        """Stop the metrics collection system"""
        logger.info("Stopping Orchestrator Metrics Manager")

        self.running = False

        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()

        logger.info("Metrics Manager stopped")

    def _start_http_server(self):
        """Start HTTP server for metrics endpoints"""
        port = self.config.get("prometheus", {}).get("port", 8090)
        host = self.config.get("prometheus", {}).get("host", "0.0.0.0")

        def handler(*args, **kwargs):
            return MetricsHTTPHandler(self, *args, **kwargs)

        self.http_server = HTTPServer((host, port), handler)

        def serve_forever():
            logger.info(f"Metrics server starting on {host}:{port}")
            self.http_server.serve_forever()

        self.metrics_thread = threading.Thread(target=serve_forever, daemon=True)
        self.metrics_thread.start()

    async def _collection_loop(self):
        """Main metrics collection loop"""
        while self.running:
            try:
                # Collect system metrics
                system_metrics = await self.system_collector.collect()
                self.system_history.append(system_metrics)
                self.prometheus_exporter.update_system_metrics(system_metrics)

                # Collect agent metrics
                agent_metrics = await self.agent_collector.collect()
                self.prometheus_exporter.update_agent_metrics(agent_metrics)

                # Collect communication metrics
                comm_metrics = await self.comm_collector.collect()
                self.prometheus_exporter.update_communication_metrics(comm_metrics)

                logger.debug("Metrics collection cycle completed")

            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")

            await asyncio.sleep(self.collection_interval)

    # Public API methods

    def record_agent_execution(
        self, agent_name: str, execution_time: float, success: bool
    ):
        """Record an agent execution"""
        self.agent_collector.record_agent_execution(agent_name, execution_time, success)

    def record_communication(self, latency: float, success: bool):
        """Record a communication event"""
        self.comm_collector.record_message(latency, success)

    def update_agent_resources(
        self, agent_name: str, cpu_usage: float, memory_usage: float
    ):
        """Update agent resource usage"""
        self.agent_collector.update_agent_resources(agent_name, cpu_usage, memory_usage)

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        agent_metrics = self.agent_collector.agent_metrics

        healthy_agents = sum(1 for m in agent_metrics.values() if m.health_score >= 80)
        total_agents = len(agent_metrics)

        overall_health = "healthy"
        if total_agents > 0:
            health_ratio = healthy_agents / total_agents
            if health_ratio < 0.7:
                overall_health = "critical"
            elif health_ratio < 0.9:
                overall_health = "warning"

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_health": overall_health,
            "agents": {
                "total": total_agents,
                "healthy": healthy_agents,
                "unhealthy": total_agents - healthy_agents,
            },
            "system": {
                "cpu_usage": (
                    self.system_history[-1].cpu_usage if self.system_history else 0
                ),
                "memory_usage": (
                    self.system_history[-1].memory_usage if self.system_history else 0
                ),
            },
        }

    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed system status"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system_metrics": (
                asdict(self.system_history[-1]) if self.system_history else {}
            ),
            "agent_metrics": {
                name: asdict(metrics)
                for name, metrics in self.agent_collector.agent_metrics.items()
            },
            "communication_metrics": asdict(self.comm_collector.metrics),
            "collection_stats": {
                "system_samples": len(self.system_history),
                "agent_count": len(self.agent_collector.agent_metrics),
                "collection_interval": self.collection_interval,
                "running": self.running,
            },
        }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import yaml

    # Load configuration
    config_path = Path(__file__).parent / "config" / "production.yaml"
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    # Create and start metrics manager
    async def main():
        metrics_manager = OrchestratorMetricsManager(config.get("monitoring", {}))
        await metrics_manager.start()

        # Keep running
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            await metrics_manager.stop()

    asyncio.run(main())
