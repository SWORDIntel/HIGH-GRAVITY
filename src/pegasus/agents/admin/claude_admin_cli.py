#!/usr/bin/env python3
"""
Claude Agent Communication System - Administrative CLI
=========================================================

Comprehensive command-line interface for managing the distributed Claude agent system.
Supports all 28 agent types with performance optimization for 4.2M+ msg/sec throughput.

Features:
- Agent lifecycle management (start/stop/restart/configure)
- Real-time system monitoring and diagnostics
- Configuration management with hot-reload
- User and role management
- Deployment and scaling operations
- Backup and restore functionality
- Performance tuning and optimization

Author: Claude Agent Administration System
Version: 1.0.0 Production
"""

import argparse
import asyncio
import configparser
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import traceback
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party imports
import click
import docker
import jwt
import kubernetes
import prometheus_client
import psutil
import requests
import rich
import websocket
import yaml

# Local imports
from admin_core import (
    AgentManager,
    BackupManager,
    ConfigManager,
    DeploymentManager,
    DiagnosticTools,
    PerformanceOptimizer,
    SystemMonitor,
    UserManager,
)
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, TaskID
from rich.table import Table
from rich.tree import Tree

# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

AGENT_TYPES = [
    "director",
    "project-orchestrator",
    "security",
    "security-chaos",
    "testbed",
    "tui",
    "web",
    "c-internal",
    "python-internal",
    "monitor",
    "optimizer",
    "patcher",
    "pygui",
    "red-team-orchestrator",
    "researcher",
    "docgen",
    "infrastructure",
    "integration",
    "linter",
    "mlops",
    "mobile",
    "constructor",
    "data-science",
    "database",
    "debugger",
    "deployer",
    "api-designer",
    "architect",
]

PERFORMANCE_TARGETS = {
    "throughput_msg_sec": 4200000,
    "latency_p99_ns": 250000,
    "latency_p95_ns": 150000,
    "cpu_utilization": 0.85,
    "memory_utilization": 0.75,
    "network_bandwidth_utilization": 0.80,
}

CONFIG_PATHS = {
    "system": "/etc/claude-agents/system.conf",
    "distributed": "/etc/claude-agents/distributed_config.json",
    "security": "/etc/claude-agents/security_config.json",
    "monitoring": "/etc/claude-agents/monitoring/",
    "backup": "/var/lib/claude-agents/backup/",
}

# ============================================================================
# CORE ADMINISTRATION CLASSES
# ============================================================================


@dataclass
class AgentStatus:
    """Represents the status of a single agent"""

    __slots__ = []
    name: str
    type: str
    state: str
    pid: Optional[int]
    cpu_percent: float
    memory_mb: float
    messages_processed: int
    uptime: timedelta
    last_heartbeat: datetime
    version: str
    health_score: float


@dataclass
class SystemStatus:
    """Represents overall system status"""

    __slots__ = []
    cluster_state: str
    active_nodes: int
    total_agents: int
    active_agents: int
    failed_agents: int
    total_throughput: int
    avg_latency_ns: int
    cpu_utilization: float
    memory_utilization: float
    disk_utilization: float
    network_utilization: float
    uptime: timedelta


class ClaudeAdminCLI:
    """Main administrative CLI class"""

    __slots__ = []

    def __init__(self):
        self.console = Console()
        self.agent_manager = AgentManager()
        self.system_monitor = SystemMonitor()
        self.config_manager = ConfigManager()
        self.user_manager = UserManager()
        self.deployment_manager = DeploymentManager()
        self.backup_manager = BackupManager()
        self.diagnostic_tools = DiagnosticTools()
        self.performance_optimizer = PerformanceOptimizer()

        # Initialize monitoring connections
        self._setup_monitoring()

    def _setup_monitoring(self):
        """Initialize monitoring system connections"""
        try:
            # Prometheus connection
            self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

            # Docker connection
            self.docker_client = docker.from_env()

            # Kubernetes connection (if available)
            try:
                kubernetes.config.load_incluster_config()
                self.k8s_client = kubernetes.client.ApiClient()
            except:
                self.k8s_client = None

        except Exception as e:
            self.console.print(
                f"[yellow]Warning: Some monitoring connections failed: {e}[/yellow]"
            )

    # ============================================================================
    # AGENT LIFECYCLE MANAGEMENT
    # ============================================================================

    @click.group()
    def agents():
        """Agent lifecycle management commands"""
        pass

    @agents.command()
    @click.argument("agent_type", type=click.Choice(AGENT_TYPES))
    @click.option("--config", help="Configuration file path")
    @click.option("--scale", default=1, help="Number of instances to start")
    @click.option("--node", help="Specific node to deploy on")
    def start(
        self, agent_type: str, config: Optional[str], scale: int, node: Optional[str]
    ):
        """Start agent instances"""
        with self.console.status(f"[bold green]Starting {agent_type} agent..."):
            try:
                result = self.agent_manager.start_agent(
                    agent_type=agent_type,
                    config_path=config,
                    scale=scale,
                    target_node=node,
                )

                if result.success:
                    self.console.print(
                        f"[green]✓[/green] {agent_type} started successfully"
                    )
                    self.console.print(f"  Instances: {result.instances_started}")
                    self.console.print(f"  PIDs: {', '.join(map(str, result.pids))}")
                else:
                    self.console.print(
                        f"[red]✗[/red] Failed to start {agent_type}: {result.error}"
                    )

            except Exception as e:
                self.console.print(f"[red]Error starting {agent_type}: {e}[/red]")

    @agents.command()
    @click.argument("agent_type", type=click.Choice(AGENT_TYPES + ["all"]))
    @click.option("--force", is_flag=True, help="Force stop without graceful shutdown")
    def stop(self, agent_type: str, force: bool):
        """Stop agent instances"""
        with self.console.status(f"[bold red]Stopping {agent_type}..."):
            try:
                if agent_type == "all":
                    results = self.agent_manager.stop_all_agents(force=force)
                    for agent_name, result in results.items():
                        status = "✓" if result.success else "✗"
                        color = "green" if result.success else "red"
                        self.console.print(f"[{color}]{status}[/{color}] {agent_name}")
                else:
                    result = self.agent_manager.stop_agent(agent_type, force=force)
                    if result.success:
                        self.console.print(
                            f"[green]✓[/green] {agent_type} stopped successfully"
                        )
                    else:
                        self.console.print(
                            f"[red]✗[/red] Failed to stop {agent_type}: {result.error}"
                        )

            except Exception as e:
                self.console.print(f"[red]Error stopping {agent_type}: {e}[/red]")

    @agents.command()
    @click.argument("agent_type", type=click.Choice(AGENT_TYPES))
    def restart(self, agent_type: str):
        """Restart agent instances with zero downtime"""
        with self.console.status(f"[bold blue]Restarting {agent_type}..."):
            try:
                result = self.agent_manager.restart_agent(
                    agent_type, zero_downtime=True
                )
                if result.success:
                    self.console.print(
                        f"[green]✓[/green] {agent_type} restarted successfully"
                    )
                    self.console.print(f"  Downtime: {result.downtime_ms}ms")
                else:
                    self.console.print(
                        f"[red]✗[/red] Failed to restart {agent_type}: {result.error}"
                    )

            except Exception as e:
                self.console.print(f"[red]Error restarting {agent_type}: {e}[/red]")

    @agents.command()
    @click.option(
        "--format", type=click.Choice(["table", "json", "yaml"]), default="table"
    )
    @click.option("--filter-state", help="Filter by agent state")
    @click.option("--watch", is_flag=True, help="Watch mode - continuous updates")
    def status(self, format: str, filter_state: Optional[str], watch: bool):
        """Display agent status information"""
        if watch:
            self._watch_agent_status(filter_state)
        else:
            self._display_agent_status(format, filter_state)

    def _display_agent_status(self, format: str, filter_state: Optional[str]):
        """Display current agent status"""
        try:
            agents = self.agent_manager.get_all_agent_status()

            if filter_state:
                agents = [a for a in agents if a.state.lower() == filter_state.lower()]

            if format == "table":
                self._display_agent_table(agents)
            elif format == "json":
                self.console.print_json(data=[a.__dict__ for a in agents])
            elif format == "yaml":
                import yaml

                self.console.print(
                    yaml.dump([a.__dict__ for a in agents], default_flow_style=False)
                )

        except Exception as e:
            self.console.print(f"[red]Error retrieving agent status: {e}[/red]")

    def _display_agent_table(self, agents: List[AgentStatus]):
        """Display agents in a formatted table"""
        table = Table(title="Claude Agent System Status")

        table.add_column("Agent", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("State", style="green")
        table.add_column("PID", style="blue")
        table.add_column("CPU%", style="yellow")
        table.add_column("Memory", style="red")
        table.add_column("Messages/s", style="bright_green")
        table.add_column("Uptime", style="bright_blue")
        table.add_column("Health", style="bright_magenta")

        for agent in agents:
            # Color-code states
            if agent.state == "ACTIVE":
                state_color = "[green]ACTIVE[/green]"
            elif agent.state == "DEGRADED":
                state_color = "[yellow]DEGRADED[/yellow]"
            elif agent.state == "FAILED":
                state_color = "[red]FAILED[/red]"
            else:
                state_color = f"[white]{agent.state}[/white]"

            # Format health score with color
            if agent.health_score >= 0.9:
                health_color = "[green]"
            elif agent.health_score >= 0.7:
                health_color = "[yellow]"
            else:
                health_color = "[red]"

            table.add_row(
                agent.name,
                agent.type,
                state_color,
                str(agent.pid) if agent.pid else "N/A",
                f"{agent.cpu_percent:.1f}%",
                f"{agent.memory_mb:.0f}MB",
                f"{agent.messages_processed:,}",
                str(agent.uptime).split(".")[0],  # Remove microseconds
                f"{health_color}{agent.health_score:.2f}[/{health_color[1:-1]}]",
            )

        self.console.print(table)

    def _watch_agent_status(self, filter_state: Optional[str]):
        """Watch agent status in real-time"""
        try:
            with Live(
                self._get_live_table(), refresh_per_second=2, screen=True
            ) as live:
                while True:
                    agents = self.agent_manager.get_all_agent_status()
                    if filter_state:
                        agents = [
                            a for a in agents if a.state.lower() == filter_state.lower()
                        ]

                    # Update the live table
                    table = Table(
                        title=f"Claude Agent System Status - {datetime.now().strftime('%H:%M:%S')}"
                    )
                    table.add_column("Agent", style="cyan", no_wrap=True)
                    table.add_column("State", style="green")
                    table.add_column("CPU%", style="yellow")
                    table.add_column("Memory", style="red")
                    table.add_column("Messages/s", style="bright_green")
                    table.add_column("Health", style="bright_magenta")

                    for agent in agents:
                        state_color = self._get_state_color(agent.state)
                        health_color = self._get_health_color(agent.health_score)

                        table.add_row(
                            agent.name,
                            state_color,
                            f"{agent.cpu_percent:.1f}%",
                            f"{agent.memory_mb:.0f}MB",
                            f"{agent.messages_processed:,}",
                            f"{health_color}{agent.health_score:.2f}[/{health_color[1:-1]}]",
                        )

                    live.update(table)
                    time.sleep(0.5)

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Status monitoring stopped[/yellow]")

    # ============================================================================
    # SYSTEM MONITORING AND DIAGNOSTICS
    # ============================================================================

    @click.group()
    def monitor():
        """System monitoring and diagnostics"""
        pass

    @monitor.command()
    @click.option(
        "--format",
        type=click.Choice(["dashboard", "json", "prometheus"]),
        default="dashboard",
    )
    @click.option("--refresh", default=5, help="Refresh interval in seconds")
    def system(self, format: str, refresh: int):
        """Display comprehensive system monitoring dashboard"""
        if format == "dashboard":
            self._display_system_dashboard(refresh)
        elif format == "json":
            status = self.system_monitor.get_system_status()
            self.console.print_json(data=status.__dict__)
        elif format == "prometheus":
            self._export_prometheus_metrics()

    def _display_system_dashboard(self, refresh: int):
        """Display real-time system dashboard"""
        try:
            with Live(
                self._get_dashboard_layout(),
                refresh_per_second=1 / refresh,
                screen=True,
            ) as live:
                while True:
                    dashboard = self._create_dashboard_layout()
                    live.update(dashboard)
                    time.sleep(refresh)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]System monitoring stopped[/yellow]")

    def _create_dashboard_layout(self):
        """Create the main dashboard layout"""
        # Get current system status
        system_status = self.system_monitor.get_system_status()

        # Create main layout panels
        overview_panel = self._create_overview_panel(system_status)
        performance_panel = self._create_performance_panel()
        agents_panel = self._create_agents_summary_panel()
        alerts_panel = self._create_alerts_panel()

        # Combine into main dashboard
        from rich.columns import Columns
        from rich.layout import Layout

        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3),
        )

        layout["header"].update(
            Panel(
                f"[bold]Claude Agent Communication System Dashboard[/bold] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                style="blue",
            )
        )

        layout["main"].split_row(
            Layout(Columns([overview_panel, performance_panel], equal=True)),
            Layout(Columns([agents_panel, alerts_panel], equal=True)),
        )

        layout["footer"].update(
            Panel(
                f"Throughput: {system_status.total_throughput:,} msg/s | "
                f"Latency: {system_status.avg_latency_ns/1000:.1f}μs | "
                f"Active Agents: {system_status.active_agents}/{system_status.total_agents}",
                style="green",
            )
        )

        return layout

    def _create_overview_panel(self, status: SystemStatus) -> Panel:
        """Create system overview panel"""
        overview_text = f"""[bold]Cluster Status:[/bold] {status.cluster_state}
[bold]Active Nodes:[/bold] {status.active_nodes}
[bold]Total Agents:[/bold] {status.total_agents}
[bold]Active Agents:[/bold] {status.active_agents}
[bold]Failed Agents:[/bold] {status.failed_agents}
[bold]System Uptime:[/bold] {status.uptime}

[bold]Resource Utilization:[/bold]
CPU: {status.cpu_utilization:.1%}
Memory: {status.memory_utilization:.1%}
Disk: {status.disk_utilization:.1%}
Network: {status.network_utilization:.1%}"""

        return Panel(overview_text, title="System Overview", border_style="blue")

    def _create_performance_panel(self) -> Panel:
        """Create performance metrics panel"""
        metrics = self.system_monitor.get_performance_metrics()

        # Create performance bars
        perf_text = f"""[bold]Performance Metrics:[/bold]

Throughput: {metrics.throughput:,} msg/s
Target: {PERFORMANCE_TARGETS['throughput_msg_sec']:,} msg/s
{self._create_progress_bar(metrics.throughput, PERFORMANCE_TARGETS['throughput_msg_sec'])}

Latency P99: {metrics.latency_p99_ns/1000:.1f}μs
Target: {PERFORMANCE_TARGETS['latency_p99_ns']/1000:.1f}μs
{self._create_progress_bar(PERFORMANCE_TARGETS['latency_p99_ns'], metrics.latency_p99_ns, invert=True)}

Message Queue Depth: {metrics.queue_depth:,}
Processing Rate: {metrics.processing_rate:,}/s
Error Rate: {metrics.error_rate:.4%}"""

        return Panel(perf_text, title="Performance Metrics", border_style="green")

    @monitor.command()
    @click.argument("agent_name")
    @click.option("--metrics", multiple=True, help="Specific metrics to display")
    def agent(self, agent_name: str, metrics: tuple):
        """Monitor specific agent performance"""
        try:
            agent_metrics = self.system_monitor.get_agent_metrics(agent_name)
            if not agent_metrics:
                self.console.print(f"[red]Agent '{agent_name}' not found[/red]")
                return

            # Display agent-specific monitoring dashboard
            self._display_agent_metrics(agent_name, agent_metrics, metrics)

        except Exception as e:
            self.console.print(f"[red]Error monitoring agent: {e}[/red]")

    @monitor.command()
    def performance(self):
        """Display detailed performance analysis"""
        try:
            analysis = self.performance_optimizer.analyze_system_performance()

            # Display performance analysis
            self.console.print("\n[bold]Performance Analysis Report[/bold]\n")

            # Current metrics vs targets
            metrics_table = Table(title="Performance Metrics vs Targets")
            metrics_table.add_column("Metric", style="cyan")
            metrics_table.add_column("Current", style="yellow")
            metrics_table.add_column("Target", style="green")
            metrics_table.add_column("Status", style="magenta")

            for metric, current, target, status in analysis.metrics_comparison:
                status_color = (
                    "green"
                    if status == "OK"
                    else "red" if status == "CRITICAL" else "yellow"
                )
                metrics_table.add_row(
                    metric,
                    current,
                    target,
                    f"[{status_color}]{status}[/{status_color}]",
                )

            self.console.print(metrics_table)

            # Bottlenecks and recommendations
            if analysis.bottlenecks:
                self.console.print("\n[bold red]Detected Bottlenecks:[/bold red]")
                for bottleneck in analysis.bottlenecks:
                    self.console.print(f"• {bottleneck}")

            if analysis.recommendations:
                self.console.print(
                    "\n[bold green]Optimization Recommendations:[/bold green]"
                )
                for rec in analysis.recommendations:
                    self.console.print(f"• {rec}")

        except Exception as e:
            self.console.print(f"[red]Error analyzing performance: {e}[/red]")

    # ============================================================================
    # CONFIGURATION MANAGEMENT
    # ============================================================================

    @click.group()
    def config():
        """Configuration management commands"""
        pass

    @config.command()
    @click.argument(
        "component",
        type=click.Choice(["system", "distributed", "security", "monitoring"]),
    )
    @click.option(
        "--format", type=click.Choice(["yaml", "json", "properties"]), default="yaml"
    )
    def show(self, component: str, format: str):
        """Display current configuration"""
        try:
            config = self.config_manager.get_config(component)

            if format == "yaml":
                self.console.print(yaml.dump(config, default_flow_style=False))
            elif format == "json":
                self.console.print_json(data=config)
            elif format == "properties":
                self._display_properties_format(config)

        except Exception as e:
            self.console.print(f"[red]Error loading configuration: {e}[/red]")

    @config.command()
    @click.argument(
        "component",
        type=click.Choice(["system", "distributed", "security", "monitoring"]),
    )
    @click.argument("key")
    @click.argument("value")
    @click.option("--hot-reload", is_flag=True, help="Apply changes without restart")
    def set(self, component: str, key: str, value: str, hot_reload: bool):
        """Set configuration value"""
        try:
            # Parse value as appropriate type
            parsed_value = self._parse_config_value(value)

            result = self.config_manager.set_config_value(
                component=component, key=key, value=parsed_value, hot_reload=hot_reload
            )

            if result.success:
                self.console.print(
                    f"[green]✓[/green] Configuration updated: {key} = {value}"
                )
                if hot_reload and result.applied:
                    self.console.print(
                        "[green]✓[/green] Hot reload applied successfully"
                    )
                elif hot_reload and not result.applied:
                    self.console.print(
                        "[yellow]⚠[/yellow] Hot reload failed, restart required"
                    )
            else:
                self.console.print(
                    f"[red]✗[/red] Failed to update configuration: {result.error}"
                )

        except Exception as e:
            self.console.print(f"[red]Error setting configuration: {e}[/red]")

    @config.command()
    @click.argument(
        "component",
        type=click.Choice(["system", "distributed", "security", "monitoring"]),
    )
    def validate(self, component: str):
        """Validate configuration"""
        try:
            result = self.config_manager.validate_config(component)

            if result.is_valid:
                self.console.print(
                    f"[green]✓[/green] {component} configuration is valid"
                )
            else:
                self.console.print(
                    f"[red]✗[/red] {component} configuration has errors:"
                )
                for error in result.errors:
                    self.console.print(f"  • {error}")

            if result.warnings:
                self.console.print(f"[yellow]⚠[/yellow] Warnings:")
                for warning in result.warnings:
                    self.console.print(f"  • {warning}")

        except Exception as e:
            self.console.print(f"[red]Error validating configuration: {e}[/red]")

    @config.command()
    @click.option("--component", help="Specific component to reload")
    def reload(self, component: Optional[str]):
        """Reload configuration with hot-reload support"""
        try:
            if component:
                result = self.config_manager.hot_reload_config(component)
                if result.success:
                    self.console.print(
                        f"[green]✓[/green] {component} configuration reloaded"
                    )
                else:
                    self.console.print(
                        f"[red]✗[/red] Failed to reload {component}: {result.error}"
                    )
            else:
                # Reload all configurations
                components = ["system", "distributed", "security", "monitoring"]
                for comp in components:
                    result = self.config_manager.hot_reload_config(comp)
                    status = "✓" if result.success else "✗"
                    color = "green" if result.success else "red"
                    self.console.print(f"[{color}]{status}[/{color}] {comp}")

        except Exception as e:
            self.console.print(f"[red]Error reloading configuration: {e}[/red]")

    # ============================================================================
    # USER AND ROLE MANAGEMENT
    # ============================================================================

    @click.group()
    def users():
        """User and role management"""
        pass

    @users.command()
    @click.argument("username")
    @click.option(
        "--role", type=click.Choice(["admin", "operator", "viewer", "developer"])
    )
    @click.option("--permissions", multiple=True, help="Additional permissions")
    @click.option("--email", help="User email address")
    def create(
        self, username: str, role: str, permissions: tuple, email: Optional[str]
    ):
        """Create new user account"""
        try:
            result = self.user_manager.create_user(
                username=username, role=role, permissions=list(permissions), email=email
            )

            if result.success:
                self.console.print(
                    f"[green]✓[/green] User '{username}' created successfully"
                )
                self.console.print(f"  Role: {role}")
                self.console.print(f"  API Key: {result.api_key}")
                if permissions:
                    self.console.print(
                        f"  Additional Permissions: {', '.join(permissions)}"
                    )
            else:
                self.console.print(
                    f"[red]✗[/red] Failed to create user: {result.error}"
                )

        except Exception as e:
            self.console.print(f"[red]Error creating user: {e}[/red]")

    @users.command()
    @click.option("--format", type=click.Choice(["table", "json"]), default="table")
    def list(self, format: str):
        """List all users"""
        try:
            users = self.user_manager.list_users()

            if format == "table":
                table = Table(title="System Users")
                table.add_column("Username", style="cyan")
                table.add_column("Role", style="magenta")
                table.add_column("Status", style="green")
                table.add_column("Last Login", style="blue")
                table.add_column("Permissions", style="yellow")

                for user in users:
                    status_color = "green" if user.is_active else "red"
                    table.add_row(
                        user.username,
                        user.role,
                        f"[{status_color}]{'Active' if user.is_active else 'Disabled'}[/{status_color}]",
                        (
                            user.last_login.strftime("%Y-%m-%d %H:%M")
                            if user.last_login
                            else "Never"
                        ),
                        ", ".join(user.permissions),
                    )

                self.console.print(table)
            elif format == "json":
                self.console.print_json(data=[u.__dict__ for u in users])

        except Exception as e:
            self.console.print(f"[red]Error listing users: {e}[/red]")

    # ============================================================================
    # DEPLOYMENT AND SCALING
    # ============================================================================

    @click.group()
    def deploy():
        """Deployment and scaling operations"""
        pass

    @deploy.command()
    @click.argument("environment", type=click.Choice(["staging", "production", "test"]))
    @click.option("--config", help="Deployment configuration file")
    @click.option("--dry-run", is_flag=True, help="Show what would be deployed")
    def cluster(self, environment: str, config: Optional[str], dry_run: bool):
        """Deploy complete cluster"""
        try:
            deployment_plan = self.deployment_manager.create_deployment_plan(
                environment=environment, config_path=config
            )

            if dry_run:
                self._display_deployment_plan(deployment_plan)
                return

            # Execute deployment
            with Progress() as progress:
                task = progress.add_task(
                    "[green]Deploying cluster...", total=len(deployment_plan.steps)
                )

                for step in deployment_plan.steps:
                    progress.update(task, description=f"[green]{step.description}...")
                    result = self.deployment_manager.execute_step(step)

                    if not result.success:
                        self.console.print(
                            f"[red]✗[/red] Deployment failed at step: {step.description}"
                        )
                        self.console.print(f"  Error: {result.error}")
                        return

                    progress.advance(task)

                self.console.print(
                    f"[green]✓[/green] Cluster deployment completed successfully"
                )

        except Exception as e:
            self.console.print(f"[red]Deployment error: {e}[/red]")

    @deploy.command()
    @click.argument("agent_type", type=click.Choice(AGENT_TYPES))
    @click.option("--scale", type=int, help="Number of instances")
    @click.option(
        "--strategy",
        type=click.Choice(["rolling", "blue-green", "canary"]),
        default="rolling",
    )
    def scale(self, agent_type: str, scale: int, strategy: str):
        """Scale agent instances"""
        try:
            current_scale = self.agent_manager.get_agent_scale(agent_type)

            if scale == current_scale:
                self.console.print(
                    f"[yellow]{agent_type} already at target scale: {scale}[/yellow]"
                )
                return

            action = "up" if scale > current_scale else "down"

            with self.console.status(
                f"[bold blue]Scaling {agent_type} {action} to {scale} instances..."
            ):
                result = self.deployment_manager.scale_agent(
                    agent_type=agent_type, target_scale=scale, strategy=strategy
                )

                if result.success:
                    self.console.print(
                        f"[green]✓[/green] {agent_type} scaled to {scale} instances"
                    )
                    self.console.print(f"  Strategy: {strategy}")
                    self.console.print(f"  Duration: {result.duration_seconds}s")
                else:
                    self.console.print(f"[red]✗[/red] Scaling failed: {result.error}")

        except Exception as e:
            self.console.print(f"[red]Scaling error: {e}[/red]")

    # ============================================================================
    # BACKUP AND RESTORE
    # ============================================================================

    @click.group()
    def backup():
        """Backup and restore operations"""
        pass

    @backup.command()
    @click.option(
        "--type",
        type=click.Choice(["full", "incremental", "config", "data"]),
        default="full",
    )
    @click.option("--destination", help="Backup destination path")
    @click.option("--compress", is_flag=True, default=True, help="Compress backup")
    def create(self, type: str, destination: Optional[str], compress: bool):
        """Create system backup"""
        try:
            backup_config = {
                "type": type,
                "destination": destination
                or f"/var/lib/claude-agents/backup/{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "compress": compress,
                "include_logs": type in ["full", "data"],
                "include_configs": type in ["full", "config"],
                "include_metrics": type == "full",
            }

            with Progress() as progress:
                task = progress.add_task(f"[green]Creating {type} backup...", total=100)

                def progress_callback(percent, description):
                    progress.update(
                        task, completed=percent, description=f"[green]{description}..."
                    )

                result = self.backup_manager.create_backup(
                    config=backup_config, progress_callback=progress_callback
                )

                if result.success:
                    self.console.print(f"[green]✓[/green] Backup created successfully")
                    self.console.print(f"  Path: {result.backup_path}")
                    self.console.print(f"  Size: {result.size_mb:.1f} MB")
                    self.console.print(f"  Duration: {result.duration_seconds}s")
                else:
                    self.console.print(f"[red]✗[/red] Backup failed: {result.error}")

        except Exception as e:
            self.console.print(f"[red]Backup error: {e}[/red]")

    @backup.command()
    @click.argument("backup_path")
    @click.option(
        "--verify", is_flag=True, help="Verify backup integrity before restore"
    )
    @click.option("--selective", help="Restore specific components only")
    def restore(self, backup_path: str, verify: bool, selective: Optional[str]):
        """Restore from backup"""
        try:
            if verify:
                self.console.print("[blue]Verifying backup integrity...[/blue]")
                verification = self.backup_manager.verify_backup(backup_path)
                if not verification.is_valid:
                    self.console.print(
                        f"[red]✗[/red] Backup verification failed: {verification.error}"
                    )
                    return
                self.console.print("[green]✓[/green] Backup integrity verified")

            restore_config = {
                "backup_path": backup_path,
                "selective_restore": selective.split(",") if selective else None,
                "stop_services": True,
                "backup_current": True,
            }

            # Confirm restore operation
            self.console.print(
                f"[yellow]Warning: This will restore system state from {backup_path}[/yellow]"
            )
            if not click.confirm("Continue with restore?"):
                return

            with Progress() as progress:
                task = progress.add_task("[red]Restoring system...", total=100)

                def progress_callback(percent, description):
                    progress.update(
                        task, completed=percent, description=f"[red]{description}..."
                    )

                result = self.backup_manager.restore_backup(
                    config=restore_config, progress_callback=progress_callback
                )

                if result.success:
                    self.console.print(
                        f"[green]✓[/green] Restore completed successfully"
                    )
                    self.console.print(f"  Duration: {result.duration_seconds}s")
                    self.console.print(
                        "[yellow]System restart may be required[/yellow]"
                    )
                else:
                    self.console.print(f"[red]✗[/red] Restore failed: {result.error}")

        except Exception as e:
            self.console.print(f"[red]Restore error: {e}[/red]")

    # ============================================================================
    # DIAGNOSTIC AND TROUBLESHOOTING
    # ============================================================================

    @click.group()
    def diagnose():
        """Diagnostic and troubleshooting tools"""
        pass

    @diagnose.command()
    @click.option(
        "--depth",
        type=click.Choice(["basic", "detailed", "comprehensive"]),
        default="detailed",
    )
    def system(self, depth: str):
        """Run comprehensive system diagnostics"""
        try:
            self.console.print(f"[blue]Running {depth} system diagnostics...[/blue]")

            diagnostics = self.diagnostic_tools.run_system_diagnostics(depth)

            # Display results
            self._display_diagnostic_results(diagnostics)

        except Exception as e:
            self.console.print(f"[red]Diagnostic error: {e}[/red]")

    def _display_diagnostic_results(self, diagnostics):
        """Display diagnostic results in formatted output"""
        # Overall health score
        health_panel = Panel(
            f"[bold]Overall Health Score: {diagnostics.overall_score:.1%}[/bold]\n"
            f"Status: {diagnostics.overall_status}",
            title="System Health",
            border_style=(
                "green"
                if diagnostics.overall_score > 0.8
                else "yellow" if diagnostics.overall_score > 0.6 else "red"
            ),
        )
        self.console.print(health_panel)

        # Component results
        results_table = Table(title="Diagnostic Results")
        results_table.add_column("Component", style="cyan")
        results_table.add_column("Status", style="green")
        results_table.add_column("Score", style="yellow")
        results_table.add_column("Issues", style="red")

        for result in diagnostics.component_results:
            status_color = (
                "green"
                if result.status == "OK"
                else "yellow" if result.status == "WARNING" else "red"
            )
            results_table.add_row(
                result.component,
                f"[{status_color}]{result.status}[/{status_color}]",
                f"{result.score:.1%}",
                str(len(result.issues)),
            )

        self.console.print(results_table)

        # Critical issues
        if diagnostics.critical_issues:
            self.console.print("\n[bold red]Critical Issues:[/bold red]")
            for issue in diagnostics.critical_issues:
                self.console.print(f"  • {issue}")

        # Recommendations
        if diagnostics.recommendations:
            self.console.print("\n[bold green]Recommendations:[/bold green]")
            for rec in diagnostics.recommendations:
                self.console.print(f"  • {rec}")

    @diagnose.command()
    @click.argument("agent_name")
    def agent(self, agent_name: str):
        """Diagnose specific agent issues"""
        try:
            diagnostics = self.diagnostic_tools.diagnose_agent(agent_name)

            if not diagnostics:
                self.console.print(f"[red]Agent '{agent_name}' not found[/red]")
                return

            self._display_agent_diagnostics(agent_name, diagnostics)

        except Exception as e:
            self.console.print(f"[red]Agent diagnostic error: {e}[/red]")


# ============================================================================
# MAIN CLI ENTRY POINT
# ============================================================================


def create_cli():
    """Create the main CLI application"""
    admin = ClaudeAdminCLI()

    @click.group()
    @click.version_option(version="1.0.0")
    def cli():
        """Claude Agent Communication System - Administrative CLI"""
        pass

    # Add command groups
    cli.add_command(admin.agents)
    cli.add_command(admin.monitor)
    cli.add_command(admin.config)
    cli.add_command(admin.users)
    cli.add_command(admin.deploy)
    cli.add_command(admin.backup)
    cli.add_command(admin.diagnose)

    return cli


def main():
    """Main entry point"""
    try:
        cli = create_cli()
        cli()
    except KeyboardInterrupt:
        print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        print(f"[red]Fatal error: {e}[/red]")
        if os.getenv("DEBUG"):
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
