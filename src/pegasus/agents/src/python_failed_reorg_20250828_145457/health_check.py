#!/usr/bin/env python3
"""
Health Check System for Tandem Orchestration System
Provides comprehensive health monitoring and status reporting
"""

import asyncio
import json
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import psutil


@dataclass
class HealthStatus:
    service: str
    status: str  # healthy, warning, critical, unknown
    score: float  # 0-100
    message: str
    timestamp: datetime
    details: Dict[str, Any]


class SystemHealthChecker:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(
            os.environ.get("CLAUDE_AGENTS_ROOT", "."), "config", "$1"
        )
        self.checks = []

    async def check_orchestrator_health(self) -> HealthStatus:
        """Check main orchestrator service health"""
        try:
            # Check if orchestrator process is running
            orchestrator_running = any(
                "production_orchestrator" in p.name().lower()
                for p in psutil.process_iter(["name", "cmdline"])
            )

            if not orchestrator_running:
                return HealthStatus(
                    service="orchestrator",
                    status="critical",
                    score=0,
                    message="Orchestrator process not running",
                    timestamp=datetime.now(),
                    details={"process_found": False},
                )

            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                status = "warning"
                score = 60
                message = f"High memory usage: {memory.percent:.1f}%"
            else:
                status = "healthy"
                score = 100 - memory.percent
                message = f"Memory usage normal: {memory.percent:.1f}%"

            return HealthStatus(
                service="orchestrator",
                status=status,
                score=score,
                message=message,
                timestamp=datetime.now(),
                details={
                    "memory_percent": memory.percent,
                    "memory_available": memory.available,
                    "process_found": True,
                },
            )

        except Exception as e:
            return HealthStatus(
                service="orchestrator",
                status="critical",
                score=0,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)},
            )

    async def check_agent_registry_health(self) -> HealthStatus:
        """Check agent registration system health"""
        try:
            # Check if agent files are accessible
            agents_dir = Path(__file__).parent.parent.parent
            agent_files = list(agents_dir.glob("*.md"))

            if len(agent_files) < 30:
                return HealthStatus(
                    service="agent_registry",
                    status="warning",
                    score=50,
                    message=f"Only {len(agent_files)} agent files found",
                    timestamp=datetime.now(),
                    details={"agent_count": len(agent_files)},
                )

            return HealthStatus(
                service="agent_registry",
                status="healthy",
                score=100,
                message=f"All {len(agent_files)} agent files accessible",
                timestamp=datetime.now(),
                details={"agent_count": len(agent_files)},
            )

        except Exception as e:
            return HealthStatus(
                service="agent_registry",
                status="critical",
                score=0,
                message=f"Agent registry check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)},
            )

    async def check_system_resources(self) -> HealthStatus:
        """Check system resource utilization"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Calculate overall score
            cpu_score = max(0, 100 - cpu)
            memory_score = max(0, 100 - memory.percent)
            disk_score = max(0, 100 - disk.percent)
            overall_score = (cpu_score + memory_score + disk_score) / 3

            if overall_score > 80:
                status = "healthy"
            elif overall_score > 60:
                status = "warning"
            else:
                status = "critical"

            return HealthStatus(
                service="system_resources",
                status=status,
                score=overall_score,
                message=f"System resources: CPU {cpu:.1f}%, MEM {memory.percent:.1f}%, DISK {disk.percent:.1f}%",
                timestamp=datetime.now(),
                details={
                    "cpu_percent": cpu,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "load_average": (
                        psutil.getloadavg() if hasattr(psutil, "getloadavg") else None
                    ),
                },
            )

        except Exception as e:
            return HealthStatus(
                service="system_resources",
                status="critical",
                score=0,
                message=f"Resource check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)},
            )

    async def run_all_checks(self) -> List[HealthStatus]:
        """Run all health checks concurrently"""
        checks = await asyncio.gather(
            self.check_orchestrator_health(),
            self.check_agent_registry_health(),
            self.check_system_resources(),
            return_exceptions=True,
        )

        # Filter out exceptions
        valid_checks = [check for check in checks if isinstance(check, HealthStatus)]
        return valid_checks

    def generate_health_report(self, checks: List[HealthStatus]) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        overall_score = (
            sum(check.score for check in checks) / len(checks) if checks else 0
        )

        critical_count = sum(1 for check in checks if check.status == "critical")
        warning_count = sum(1 for check in checks if check.status == "warning")
        healthy_count = sum(1 for check in checks if check.status == "healthy")

        if critical_count > 0:
            overall_status = "critical"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "overall_score": round(overall_score, 2),
            "summary": {
                "total_checks": len(checks),
                "healthy": healthy_count,
                "warning": warning_count,
                "critical": critical_count,
            },
            "checks": [
                {
                    "service": check.service,
                    "status": check.status,
                    "score": check.score,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat(),
                    "details": check.details,
                }
                for check in checks
            ],
        }


async def main():
    """Main health check execution"""
    checker = SystemHealthChecker()
    checks = await checker.run_all_checks()
    report = checker.generate_health_report(checks)

    print(json.dumps(report, indent=2))

    # Exit with appropriate code
    if report["overall_status"] == "critical":
        exit(2)
    elif report["overall_status"] == "warning":
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    asyncio.run(main())
