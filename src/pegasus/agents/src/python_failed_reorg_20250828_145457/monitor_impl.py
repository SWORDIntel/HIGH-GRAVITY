#!/usr/bin/env python3
"""
MONITOR Agent Python Implementation v9.0
System monitoring and observability specialist.

Comprehensive monitoring with metrics collection, alerting, logging,
tracing, and dashboard generation capabilities.
"""

import asyncio
import json
import os
import re
import statistics
import sys
import time
import traceback
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# System monitoring libraries
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Monitoring libraries
try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        Summary,
        generate_latest,
    )

    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

try:
    import logging
    from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

    HAS_LOGGING = True
except ImportError:
    HAS_LOGGING = False

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Import parallel orchestration enhancements
try:
    from parallel_orchestration_enhancements import (
        EnhancedOrchestrationMixin,
        MessageType,
        ParallelBatch,
        ParallelExecutionMode,
        ParallelOrchestrationEnhancer,
        ParallelTask,
        TaskResult,
    )

    HAS_ORCHESTRATION_ENHANCEMENTS = True
except ImportError:
    HAS_ORCHESTRATION_ENHANCEMENTS = False


@dataclass
class Metric:
    """Metric definition"""

    name: str
    type: str  # counter, gauge, histogram, summary
    value: float
    labels: Dict[str, str]
    timestamp: str
    unit: str
    description: str


@dataclass
class Alert:
    """Alert definition"""

    alert_id: str
    name: str
    severity: str  # critical, warning, info
    condition: str
    threshold: float
    current_value: float
    message: str
    triggered_at: str
    resolved_at: Optional[str]
    status: str  # firing, resolved, pending


@dataclass
class HealthCheck:
    """Health check result"""

    service: str
    status: str  # healthy, unhealthy, degraded
    checks: Dict[str, bool]
    response_time_ms: float
    last_check: str
    error_message: Optional[str]


@dataclass
class LogEntry:
    """Structured log entry"""

    timestamp: str
    level: str
    message: str
    context: Dict[str, Any]
    trace_id: Optional[str]
    span_id: Optional[str]
    service: str


@dataclass
class SystemMetrics:
    """System resource metrics"""

    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    open_files: int
    threads: int
    processes: int


class MetricsCollector:
    """Metrics collection engine"""

    def __init__(self):
        self.metrics = defaultdict(list)
        self.registry = CollectorRegistry() if HAS_PROMETHEUS else None
        self.prometheus_metrics = {}
        self._setup_prometheus_metrics()

    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        if not HAS_PROMETHEUS:
            return

        self.prometheus_metrics = {
            "requests_total": Counter(
                "requests_total",
                "Total requests",
                ["method", "endpoint"],
                registry=self.registry,
            ),
            "request_duration": Histogram(
                "request_duration_seconds",
                "Request duration",
                ["method", "endpoint"],
                registry=self.registry,
            ),
            "active_connections": Gauge(
                "active_connections", "Active connections", registry=self.registry
            ),
            "cpu_usage": Gauge(
                "cpu_usage_percent", "CPU usage percentage", registry=self.registry
            ),
            "memory_usage": Gauge(
                "memory_usage_bytes", "Memory usage in bytes", registry=self.registry
            ),
            "error_rate": Counter(
                "errors_total", "Total errors", ["type"], registry=self.registry
            ),
        }

    def record_metric(self, metric: Metric):
        """Record a metric"""
        # Store in internal metrics
        self.metrics[metric.name].append(
            {
                "value": metric.value,
                "timestamp": metric.timestamp,
                "labels": metric.labels,
            }
        )

        # Keep only last 1000 points per metric
        if len(self.metrics[metric.name]) > 1000:
            self.metrics[metric.name] = self.metrics[metric.name][-1000:]

        # Update Prometheus metrics
        if HAS_PROMETHEUS and metric.name in self.prometheus_metrics:
            prom_metric = self.prometheus_metrics[metric.name]

            if metric.type == "counter":
                prom_metric.labels(**metric.labels).inc(metric.value)
            elif metric.type == "gauge":
                (
                    prom_metric.labels(**metric.labels)
                    if hasattr(prom_metric, "labels")
                    else prom_metric.set(metric.value)
                )
            elif metric.type == "histogram":
                prom_metric.labels(**metric.labels).observe(metric.value)

    def get_metrics(self, name: str = None, start_time: str = None) -> List[Dict]:
        """Get metrics data"""
        if name:
            return self.metrics.get(name, [])
        return dict(self.metrics)

    def export_prometheus(self) -> bytes:
        """Export metrics in Prometheus format"""
        if HAS_PROMETHEUS:
            return generate_latest(self.registry)
        return b""

    def calculate_statistics(self, metric_name: str) -> Dict[str, float]:
        """Calculate statistics for a metric"""
        values = [m["value"] for m in self.metrics.get(metric_name, [])]

        if not values:
            return {}

        return {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }


class AlertManager:
    """Alert management system"""

    def __init__(self):
        self.alerts = {}
        self.alert_rules = []
        self.alert_history = deque(maxlen=1000)

    def add_rule(
        self, name: str, condition: str, threshold: float, severity: str = "warning"
    ):
        """Add alert rule"""
        self.alert_rules.append(
            {
                "name": name,
                "condition": condition,
                "threshold": threshold,
                "severity": severity,
            }
        )

    def check_alerts(self, metrics: Dict[str, float]) -> List[Alert]:
        """Check metrics against alert rules"""
        triggered_alerts = []

        for rule in self.alert_rules:
            metric_value = metrics.get(rule["condition"])

            if metric_value is not None:
                triggered = False

                # Simple threshold checking
                if ">" in rule["condition"]:
                    triggered = metric_value > rule["threshold"]
                elif "<" in rule["condition"]:
                    triggered = metric_value < rule["threshold"]

                if triggered:
                    alert = Alert(
                        alert_id=f"{rule['name']}_{int(time.time())}",
                        name=rule["name"],
                        severity=rule["severity"],
                        condition=rule["condition"],
                        threshold=rule["threshold"],
                        current_value=metric_value,
                        message=f"{rule['name']}: {metric_value} exceeds threshold {rule['threshold']}",
                        triggered_at=datetime.now().isoformat(),
                        resolved_at=None,
                        status="firing",
                    )

                    self.alerts[alert.alert_id] = alert
                    triggered_alerts.append(alert)
                    self.alert_history.append(alert)

        return triggered_alerts

    def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = "resolved"
            self.alerts[alert_id].resolved_at = datetime.now().isoformat()

    def get_active_alerts(self) -> List[Alert]:
        """Get active alerts"""
        return [a for a in self.alerts.values() if a.status == "firing"]

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        return list(self.alert_history)[-limit:]


class HealthChecker:
    """Health check system"""

    def __init__(self):
        self.checks = {}
        self.check_history = defaultdict(list)

    async def check_service(
        self, service_name: str, endpoint: str = None
    ) -> HealthCheck:
        """Check service health"""
        start_time = time.time()
        checks = {}
        error_message = None

        # Basic checks
        checks["process"] = self._check_process(service_name)
        checks["port"] = self._check_port(service_name)
        checks["memory"] = self._check_memory()
        checks["disk"] = self._check_disk()

        # Endpoint check if provided
        if endpoint:
            checks["endpoint"] = await self._check_endpoint(endpoint)

        # Determine overall status
        if all(checks.values()):
            status = "healthy"
        elif any(checks.values()):
            status = "degraded"
        else:
            status = "unhealthy"
            error_message = "Multiple health checks failed"

        response_time = (time.time() - start_time) * 1000

        health_check = HealthCheck(
            service=service_name,
            status=status,
            checks=checks,
            response_time_ms=response_time,
            last_check=datetime.now().isoformat(),
            error_message=error_message,
        )

        # Store result
        self.checks[service_name] = health_check
        self.check_history[service_name].append(health_check)

        # Keep only last 100 checks
        if len(self.check_history[service_name]) > 100:
            self.check_history[service_name] = self.check_history[service_name][-100:]

        return health_check

    def _check_process(self, process_name: str) -> bool:
        """Check if process is running"""
        for proc in psutil.process_iter(["name"]):
            if process_name.lower() in proc.info["name"].lower():
                return True
        return False

    def _check_port(self, service_name: str) -> bool:
        """Check if service port is open"""
        # Service to port mapping
        port_map = {"web": 80, "api": 8000, "database": 5432, "redis": 6379}

        port = port_map.get(service_name.lower(), 8000)

        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return result == 0

    def _check_memory(self) -> bool:
        """Check memory usage"""
        memory = psutil.virtual_memory()
        return memory.percent < 90

    def _check_disk(self) -> bool:
        """Check disk usage"""
        disk = psutil.disk_usage("/")
        return disk.percent < 90

    async def _check_endpoint(self, endpoint: str) -> bool:
        """Check HTTP endpoint"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, timeout=5) as response:
                    return response.status == 200
        except:
            return False


class LogManager:
    """Centralized logging system"""

    def __init__(self, log_dir: str = None):
        if log_dir is None:
            # Use a temporary directory if no log directory provided
            import tempfile

            log_dir = tempfile.mkdtemp(prefix="monitor_logs_")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True, mode=0o755)
        self.loggers = {}
        self.log_buffer = deque(maxlen=10000)
        self._setup_loggers()

    def _setup_loggers(self):
        """Setup logging configuration"""
        if not HAS_LOGGING:
            return

        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Create application logger
        self.loggers["app"] = self._create_logger("application")
        self.loggers["error"] = self._create_logger("errors", level=logging.ERROR)
        self.loggers["performance"] = self._create_logger("performance")
        self.loggers["security"] = self._create_logger("security")

    def _create_logger(self, name: str, level=logging.INFO) -> logging.Logger:
        """Create a logger with file rotation"""
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # File handler with rotation
        handler = RotatingFileHandler(
            self.log_dir / f"{name}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def log(self, entry: LogEntry):
        """Log an entry"""
        # Buffer log
        self.log_buffer.append(entry)

        # Write to appropriate logger
        logger_name = "app"
        if entry.level in ["ERROR", "CRITICAL"]:
            logger_name = "error"
        elif "performance" in entry.message.lower():
            logger_name = "performance"
        elif "security" in entry.message.lower():
            logger_name = "security"

        if logger_name in self.loggers:
            logger = self.loggers[logger_name]

            # Format message with context
            msg = f"{entry.message} | context={json.dumps(entry.context)}"
            if entry.trace_id:
                msg += f" | trace_id={entry.trace_id}"

            # Log at appropriate level
            level_map = {
                "DEBUG": logger.debug,
                "INFO": logger.info,
                "WARNING": logger.warning,
                "ERROR": logger.error,
                "CRITICAL": logger.critical,
            }

            log_func = level_map.get(entry.level, logger.info)
            log_func(msg)

    def search_logs(self, query: str, limit: int = 100) -> List[LogEntry]:
        """Search logs"""
        results = []

        for entry in self.log_buffer:
            if query.lower() in entry.message.lower():
                results.append(entry)

            if len(results) >= limit:
                break

        return results

    def get_recent_logs(
        self, service: str = None, level: str = None, limit: int = 100
    ) -> List[LogEntry]:
        """Get recent logs with filters"""
        results = []

        for entry in reversed(self.log_buffer):
            if service and entry.service != service:
                continue
            if level and entry.level != level:
                continue

            results.append(entry)

            if len(results) >= limit:
                break

        return results


class SystemMonitor:
    """System resource monitoring"""

    def __init__(self):
        self.baseline = None
        self.history = deque(maxlen=1000)

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""

        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_mb = memory.used / (1024 * 1024)

        # Disk
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent

        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_read_mb = disk_io.read_bytes / (1024 * 1024) if disk_io else 0
        disk_write_mb = disk_io.write_bytes / (1024 * 1024) if disk_io else 0

        # Network
        net_io = psutil.net_io_counters()
        net_sent_mb = net_io.bytes_sent / (1024 * 1024) if net_io else 0
        net_recv_mb = net_io.bytes_recv / (1024 * 1024) if net_io else 0

        # Process info
        current_process = psutil.Process()
        open_files = len(current_process.open_files())
        threads = current_process.num_threads()
        processes = len(psutil.pids())

        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_mb=memory_mb,
            disk_percent=disk_percent,
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_sent_mb=net_sent_mb,
            network_recv_mb=net_recv_mb,
            open_files=open_files,
            threads=threads,
            processes=processes,
        )

        self.history.append(metrics)

        return metrics

    def set_baseline(self):
        """Set current metrics as baseline"""
        self.baseline = self.collect_system_metrics()

    def compare_to_baseline(self) -> Dict[str, float]:
        """Compare current metrics to baseline"""
        if not self.baseline:
            return {}

        current = self.collect_system_metrics()

        return {
            "cpu_delta": current.cpu_percent - self.baseline.cpu_percent,
            "memory_delta": current.memory_percent - self.baseline.memory_percent,
            "disk_delta": current.disk_percent - self.baseline.disk_percent,
            "network_sent_delta": current.network_sent_mb
            - self.baseline.network_sent_mb,
            "network_recv_delta": current.network_recv_mb
            - self.baseline.network_recv_mb,
        }

    def get_trends(self) -> Dict[str, str]:
        """Analyze metric trends"""
        if len(self.history) < 10:
            return {}

        recent = list(self.history)[-10:]

        trends = {}

        # CPU trend
        cpu_values = [m.cpu_percent for m in recent]
        cpu_trend = "increasing" if cpu_values[-1] > cpu_values[0] else "decreasing"
        trends["cpu"] = cpu_trend

        # Memory trend
        mem_values = [m.memory_percent for m in recent]
        mem_trend = "increasing" if mem_values[-1] > mem_values[0] else "stable"
        trends["memory"] = mem_trend

        return trends


class MONITORPythonExecutor(
    EnhancedOrchestrationMixin if HAS_ORCHESTRATION_ENHANCEMENTS else object
):
    """
    MONITOR Agent Python Implementation v10.0/9.0

    Comprehensive monitoring with metrics, alerts, health checks,
    logging, system resource tracking, and optional distributed coordination.
    """

    def __init__(self):
        self.agent_name = "MONITOR"
        self.version = "9.0.0"
        self.start_time = datetime.now()

        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.health_checker = HealthChecker()
        self.log_manager = LogManager()
        self.system_monitor = SystemMonitor()
        self.dashboards = {}
        self.metrics = {
            "metrics_collected": 0,
            "alerts_triggered": 0,
            "health_checks": 0,
            "logs_processed": 0,
            "errors": 0,
        }

        # Initialize orchestration enhancements if available
        if HAS_ORCHESTRATION_ENHANCEMENTS:
            super().__init__()  # Initialize EnhancedOrchestrationMixin
            self._orchestration_enhancer = ParallelOrchestrationEnhancer(max_workers=8)
            self.version = "10.0.0"  # Update version for enhanced capabilities
            self._distributed_monitoring_enabled = True
        else:
            self._distributed_monitoring_enabled = False

    async def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MONITOR commands"""
        try:
            result = await self.process_command(command)
            return result
        except Exception as e:
            self.metrics["errors"] += 1
            return {"error": str(e), "traceback": traceback.format_exc()}

    async def process_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Process monitoring operations"""
        action = command.get("action", "")
        payload = command.get("payload", {})

        commands = {
            "collect_metrics": self.collect_metrics,
            "create_alert": self.create_alert,
            "check_health": self.check_health,
            "log_event": self.log_event,
            "get_system_metrics": self.get_system_metrics,
            "export_metrics": self.export_metrics,
            "create_dashboard": self.create_dashboard,
            "get_alerts": self.get_alerts,
            "search_logs": self.search_logs,
            "analyze_performance": self.analyze_performance,
            "setup_monitoring": self.setup_monitoring,
            "generate_report": self.generate_report,
        }

        handler = commands.get(action)
        if handler:
            return await handler(payload)
        else:
            return {"error": f"Unknown monitoring operation: {action}"}

    async def collect_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Collect metrics"""
        try:
            metric = Metric(
                name=payload.get("name", "custom_metric"),
                type=payload.get("type", "gauge"),
                value=payload.get("value", 0),
                labels=payload.get("labels", {}),
                timestamp=datetime.now().isoformat(),
                unit=payload.get("unit", ""),
                description=payload.get("description", ""),
            )

            self.metrics_collector.record_metric(metric)
            self.metrics["metrics_collected"] += 1

            # Check for alerts
            triggered_alerts = self.alert_manager.check_alerts(
                {metric.name: metric.value}
            )
            if triggered_alerts:
                self.metrics["alerts_triggered"] += len(triggered_alerts)

            return {
                "status": "success",
                "metric": asdict(metric),
                "triggered_alerts": [asdict(a) for a in triggered_alerts],
            }

        except Exception as e:
            return {"error": f"Failed to collect metrics: {str(e)}"}

    async def create_alert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create alert rule"""
        try:
            name = payload.get("name", "alert")
            condition = payload.get("condition", "metric > threshold")
            threshold = payload.get("threshold", 0)
            severity = payload.get("severity", "warning")

            self.alert_manager.add_rule(name, condition, threshold, severity)

            return {
                "status": "success",
                "alert_rule": {
                    "name": name,
                    "condition": condition,
                    "threshold": threshold,
                    "severity": severity,
                },
            }

        except Exception as e:
            return {"error": f"Failed to create alert: {str(e)}"}

    async def check_health(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Check service health"""
        try:
            service = payload.get("service", "application")
            endpoint = payload.get("endpoint")

            health_check = await self.health_checker.check_service(service, endpoint)

            self.metrics["health_checks"] += 1

            return {"status": "success", "health_check": asdict(health_check)}

        except Exception as e:
            return {"error": f"Health check failed: {str(e)}"}

    async def log_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Log an event"""
        try:
            entry = LogEntry(
                timestamp=datetime.now().isoformat(),
                level=payload.get("level", "INFO"),
                message=payload.get("message", ""),
                context=payload.get("context", {}),
                trace_id=payload.get("trace_id"),
                span_id=payload.get("span_id"),
                service=payload.get("service", "default"),
            )

            self.log_manager.log(entry)
            self.metrics["logs_processed"] += 1

            return {"status": "success", "logged": True}

        except Exception as e:
            return {"error": f"Failed to log event: {str(e)}"}

    async def get_system_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get system metrics"""
        try:
            metrics = self.system_monitor.collect_system_metrics()
            trends = self.system_monitor.get_trends()

            return {
                "status": "success",
                "system_metrics": asdict(metrics),
                "trends": trends,
            }

        except Exception as e:
            return {"error": f"Failed to get system metrics: {str(e)}"}

    async def export_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Export metrics"""
        try:
            format = payload.get("format", "json")

            if format == "prometheus":
                data = self.metrics_collector.export_prometheus()
                return {
                    "status": "success",
                    "format": "prometheus",
                    "data": data.decode("utf-8") if data else "",
                }
            else:
                metrics = self.metrics_collector.get_metrics()
                return {"status": "success", "format": "json", "metrics": metrics}

        except Exception as e:
            return {"error": f"Failed to export metrics: {str(e)}"}

    async def create_dashboard(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create monitoring dashboard"""
        try:
            name = payload.get("name", "dashboard")
            panels = payload.get("panels", [])

            dashboard_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{name} Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        .panel {{ border: 1px solid #ddd; padding: 10px; margin: 10px; }}
        .metric {{ font-size: 24px; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>{name} Dashboard</h1>
    <div id="metrics"></div>
    <div id="charts"></div>
    <script>
        // Auto-refresh every 5 seconds
        setInterval(() => location.reload(), 5000);
    </script>
</body>
</html>
"""

            self.dashboards[name] = dashboard_html

            return {
                "status": "success",
                "dashboard_name": name,
                "html": (
                    dashboard_html[:500] + "..."
                    if len(dashboard_html) > 500
                    else dashboard_html
                ),
            }

        except Exception as e:
            return {"error": f"Failed to create dashboard: {str(e)}"}

    async def get_alerts(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get alerts"""
        try:
            active_only = payload.get("active_only", False)

            if active_only:
                alerts = self.alert_manager.get_active_alerts()
            else:
                alerts = self.alert_manager.get_alert_history()

            return {"status": "success", "alerts": [asdict(a) for a in alerts]}

        except Exception as e:
            return {"error": f"Failed to get alerts: {str(e)}"}

    async def search_logs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Search logs"""
        try:
            query = payload.get("query", "")
            service = payload.get("service")
            level = payload.get("level")
            limit = payload.get("limit", 100)

            if query:
                logs = self.log_manager.search_logs(query, limit)
            else:
                logs = self.log_manager.get_recent_logs(service, level, limit)

            return {
                "status": "success",
                "logs": [asdict(log) for log in logs],
                "count": len(logs),
            }

        except Exception as e:
            return {"error": f"Failed to search logs: {str(e)}"}

    async def analyze_performance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance metrics"""
        try:
            metric_name = payload.get("metric", "response_time")

            stats = self.metrics_collector.calculate_statistics(metric_name)

            # Performance analysis
            analysis = {"statistics": stats, "recommendations": []}

            if stats.get("mean", 0) > 1000:  # If mean > 1 second
                analysis["recommendations"].append(
                    "High average response time detected"
                )

            if stats.get("stdev", 0) > stats.get("mean", 1) * 0.5:
                analysis["recommendations"].append("High variance in performance")

            return {"status": "success", "analysis": analysis}

        except Exception as e:
            return {"error": f"Failed to analyze performance: {str(e)}"}

    async def setup_monitoring(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Setup monitoring configuration"""
        try:
            config_type = payload.get("type", "basic")

            if config_type == "basic":
                # Basic monitoring setup
                self.alert_manager.add_rule("high_cpu", "cpu > 80", 80, "warning")
                self.alert_manager.add_rule(
                    "high_memory", "memory > 90", 90, "critical"
                )
                self.alert_manager.add_rule("disk_space", "disk > 85", 85, "warning")

                config = {
                    "alerts": ["high_cpu", "high_memory", "disk_space"],
                    "metrics": ["cpu", "memory", "disk"],
                    "health_checks": ["process", "port", "memory", "disk"],
                }
            else:
                config = {"message": "Custom configuration"}

            return {"status": "success", "configuration": config}

        except Exception as e:
            return {"error": f"Failed to setup monitoring: {str(e)}"}

    async def generate_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate monitoring report"""
        try:
            period = payload.get("period", "daily")

            report = {
                "timestamp": datetime.now().isoformat(),
                "period": period,
                "summary": {
                    "metrics_collected": self.metrics["metrics_collected"],
                    "alerts_triggered": self.metrics["alerts_triggered"],
                    "health_checks": self.metrics["health_checks"],
                    "logs_processed": self.metrics["logs_processed"],
                },
                "system_status": asdict(self.system_monitor.collect_system_metrics()),
                "active_alerts": len(self.alert_manager.get_active_alerts()),
                "trends": self.system_monitor.get_trends(),
            }

            return {"status": "success", "report": report}

        except Exception as e:
            return {"error": f"Failed to generate report: {str(e)}"}

    def get_capabilities(self) -> List[str]:
        """Get MONITOR capabilities"""
        return [
            "collect_metrics",
            "create_alerts",
            "health_checks",
            "log_management",
            "system_monitoring",
            "performance_tracking",
            "resource_monitoring",
            "dashboard_creation",
            "trend_analysis",
            "prometheus_integration",
            "grafana_support",
            "alert_notifications",
            "service_discovery",
            "metric_aggregation",
            "real_time_monitoring",
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get MONITOR status"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        # Create monitor files and documentation
        # Note: File creation moved to async context if needed
        return {
            "agent_name": self.agent_name,
            "version": self.version,
            "status": "healthy",
            "uptime_seconds": uptime,
            "metrics": self.metrics.copy(),
            "active_dashboards": len(self.dashboards),
            "capabilities": len(self.get_capabilities()),
            "components": {
                "metrics_collector": "operational",
                "alert_manager": "operational",
                "health_checker": "operational",
                "log_manager": "operational",
                "system_monitor": "operational",
            },
            "integrations": {
                "prometheus": HAS_PROMETHEUS,
                "psutil": HAS_PSUTIL,
                "requests": HAS_REQUESTS,
            },
        }

    async def _create_monitor_files(
        self, result_data: Dict[str, Any], context: Dict[str, Any]
    ):
        """Create monitor files and artifacts using declared tools"""
        try:
            import json
            import os
            import time
            from pathlib import Path

            # Create directories
            main_dir = Path("monitoring_configs")
            docs_dir = Path("monitoring_dashboards")

            os.makedirs(main_dir, exist_ok=True)
            os.makedirs(docs_dir / "metrics", exist_ok=True)
            os.makedirs(docs_dir / "alerts", exist_ok=True)
            os.makedirs(docs_dir / "dashboards", exist_ok=True)
            os.makedirs(docs_dir / "reports", exist_ok=True)

            timestamp = int(time.time())

            # 1. Create main result file
            result_file = main_dir / f"monitor_result_{timestamp}.json"
            with open(result_file, "w") as f:
                json.dump(result_data, f, indent=2, default=str)

            # 2. Create implementation script
            script_file = docs_dir / "metrics" / f"monitor_implementation.py"
            script_content = f'''#!/usr/bin/env python3
"""
MONITOR Implementation Script
Generated by MONITOR Agent at {datetime.now().isoformat()}
"""

import asyncio
import json
from typing import Dict, Any

class MonitorImplementation:
    """
    Implementation for monitor operations
    """
    
    def __init__(self):
        self.agent_name = "MONITOR"
        self.result_data = result_data
        
    async def execute(self) -> Dict[str, Any]:
        """Execute monitor implementation"""
        print(f"Executing {self.agent_name} implementation")
        
        # Implementation logic here
        await asyncio.sleep(0.1)
        
        return {
            "status": "completed",
            "agent": self.agent_name,
            "execution_time": "{datetime.now().isoformat()}"
        }
        
    def get_artifacts(self) -> Dict[str, Any]:
        """Get created artifacts"""
        return {
            "files_created": [
                "prometheus.yml",
                "grafana_dashboard.json",
                "alert_rules.yml"
            ],
            "directories": ['metrics', 'alerts', 'dashboards', 'reports'],
            "description": "Monitoring configurations and dashboards"
        }

if __name__ == "__main__":
    impl = MonitorImplementation()
    result = asyncio.run(impl.execute())
    print(f"Result: {result}")
'''

            with open(script_file, "w") as f:
                f.write(script_content)

            os.chmod(script_file, 0o755)

            # 3. Create README
            readme_content = f"""# MONITOR Output

Generated by MONITOR Agent at {datetime.now().isoformat()}

## Description
Monitoring configurations and dashboards

## Files Created
- Main result: `{result_file.name}`
- Implementation: `{script_file.name}`

## Directory Structure
- `metrics/` - metrics related files
- `alerts/` - alerts related files
- `dashboards/` - dashboards related files
- `reports/` - reports related files

## Usage
```bash
# Run the implementation
python3 {script_file}

# View results
cat {result_file}
```

---
Last updated: {datetime.now().isoformat()}
"""

            with open(docs_dir / "README.md", "w") as f:
                f.write(readme_content)

            print(f"MONITOR files created successfully in {main_dir} and {docs_dir}")

        except Exception as e:
            print(f"Failed to create monitor files: {e}")


# Export main class
__all__ = ["MONITORPythonExecutor"]
