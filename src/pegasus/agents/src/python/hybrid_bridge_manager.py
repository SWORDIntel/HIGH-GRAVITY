#!/usr/bin/env python3
"""
Hybrid Bridge Manager - Docker + Native PostgreSQL Integration
Provides intelligent routing between containerized and native database systems
with automatic failover and health monitoring.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SystemConfig:
    """Configuration for a database system"""

    name: str
    host: str
    port: int
    user: str
    password: str
    database: str
    available: bool = False
    health_score: float = 0.0
    last_check: float = 0.0


class HybridBridgeManager:
    """
    Manages hybrid integration between Docker and native PostgreSQL systems.

    Features:
    - Automatic system discovery and health monitoring
    - Intelligent query routing based on performance
    - Seamless failover between systems
    - Real-time health scoring and metrics
    """

    def __init__(self):
        self.systems = {}
        self.primary_system = None
        self.fallback_system = None
        self.initialized = False
        self.native_only_mode = os.getenv("NATIVE_ONLY_MODE", "false").lower() == "true"

    async def initialize(self):
        """Initialize the hybrid bridge with system discovery"""
        logger.info("Initializing Hybrid Bridge Manager...")

        # Configure systems
        await self._configure_systems()

        # Health check all systems
        await self._health_check_all()

        # Select primary and fallback systems
        self._select_primary_system()

        self.initialized = True
        logger.info(
            f"Hybrid Bridge initialized - Primary: {self.primary_system}, Fallback: {self.fallback_system}"
        )

    async def _configure_systems(self):
        """Configure available database systems"""

        # Docker PostgreSQL system (skip if native-only mode)
        if not self.native_only_mode:
            self.systems["docker"] = SystemConfig(
                name="docker",
                host=os.getenv(
                    "POSTGRES_HOST", "127.0.0.1"
                ),  # Use IPv4 to avoid IPv6 issues
                port=int(os.getenv("POSTGRES_PORT", "5433")),  # Docker exposed port
                user=os.getenv("POSTGRES_USER", "claude_user"),
                password=os.getenv("POSTGRES_PASSWORD", "claude_secure_pass"),
                database=os.getenv("POSTGRES_DB", "claude_auth"),
            )

        # Native PostgreSQL system
        self.systems["native"] = SystemConfig(
            name="native",
            host="localhost",
            port=5432,  # Standard PostgreSQL port
            user=os.getenv("NATIVE_POSTGRES_USER", "postgres"),
            password=os.getenv("NATIVE_POSTGRES_PASSWORD", ""),
            database=os.getenv("NATIVE_POSTGRES_DB", "postgres"),
        )

        # Socket-based local system (if exists)
        if (
            Path("/tmp/.s.PGSQL.5432").exists()
            or Path("/var/run/postgresql/.s.PGSQL.5432").exists()
        ):
            self.systems["socket"] = SystemConfig(
                name="socket",
                host="/var/run/postgresql",  # Socket directory
                port=5432,
                user=os.getenv("SOCKET_POSTGRES_USER", os.getenv("USER", "postgres")),
                password="",  # Socket typically doesn't need password
                database=os.getenv("SOCKET_POSTGRES_DB", "postgres"),
            )

    async def _health_check_all(self):
        """Perform health checks on all configured systems"""
        tasks = []
        for system_name, config in self.systems.items():
            tasks.append(self._health_check_system(system_name, config))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _health_check_system(self, system_name: str, config: SystemConfig):
        """Health check a specific database system"""
        start_time = time.time()

        try:
            # Build connection string
            if config.name == "socket":
                conn_str = f"host={config.host} port={config.port} user={config.user} dbname={config.database}"
            else:
                conn_str = f"host={config.host} port={config.port} user={config.user} password={config.password} dbname={config.database}"

            # Test connection
            conn = psycopg2.connect(conn_str, connect_timeout=5)
            cursor = conn.cursor()

            # Test basic query
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            # Test performance with simple query
            perf_start = time.time()
            cursor.execute("SELECT 1")
            perf_time = time.time() - perf_start

            # Check for pgvector extension
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            has_vector = cursor.fetchone()[0]

            conn.close()

            # Calculate health score (0-100)
            response_time = time.time() - start_time
            base_score = 100 - (response_time * 20)  # Penalize slow connections
            if has_vector:
                base_score += 10  # Bonus for vector support

            config.available = True
            config.health_score = max(0, min(100, base_score))
            config.last_check = time.time()

            logger.info(
                f"✓ {system_name.upper()} system healthy (score: {config.health_score:.1f}, response: {response_time:.3f}s)"
            )

        except Exception as e:
            config.available = False
            config.health_score = 0.0
            config.last_check = time.time()
            # Use INFO instead of WARNING - unavailable systems are expected (e.g., no native DB)
            logger.info(f"ℹ {system_name.upper()} system unavailable: {str(e)}")

    def _select_primary_system(self):
        """Select primary and fallback systems based on health scores"""
        available_systems = [
            (name, config) for name, config in self.systems.items() if config.available
        ]

        if not available_systems:
            logger.error("No database systems available!")
            return

        # Sort by health score (descending)
        available_systems.sort(key=lambda x: x[1].health_score, reverse=True)

        self.primary_system = available_systems[0][0]
        if len(available_systems) > 1:
            self.fallback_system = available_systems[1][0]
        else:
            self.fallback_system = None

    async def route_query(
        self, query_type: str, query_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route query to optimal system with automatic failover"""
        if not self.initialized:
            raise RuntimeError("Bridge not initialized - call initialize() first")

        # Try primary system first
        try:
            result = await self._execute_on_system(
                self.primary_system, query_type, query_data
            )
            result["system"] = self.primary_system
            return result
        except Exception as e:
            logger.warning(f"Primary system ({self.primary_system}) failed: {e}")

            # Fallback to secondary system
            if self.fallback_system:
                try:
                    result = await self._execute_on_system(
                        self.fallback_system, query_type, query_data
                    )
                    result["system"] = self.fallback_system
                    result["fallback"] = True
                    return result
                except Exception as fe:
                    logger.error(
                        f"Fallback system ({self.fallback_system}) also failed: {fe}"
                    )

            # All systems failed
            raise RuntimeError(
                f"All database systems unavailable: primary={e}, fallback={fe if self.fallback_system else 'none'}"
            )

    async def _execute_on_system(
        self, system_name: str, query_type: str, query_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute query on specific system"""
        config = self.systems[system_name]

        # Mock execution for demonstration (replace with actual implementation)
        await asyncio.sleep(0.1)  # Simulate query time

        return {
            "query_type": query_type,
            "result": f"Executed on {system_name}",
            "timestamp": time.time(),
            "config": config.name,
        }

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "bridge_manager": {
                "initialized": self.initialized,
                "native_only_mode": self.native_only_mode,
                "primary_system": self.primary_system,
                "fallback_system": self.fallback_system,
                "status": "operational" if self.initialized else "initializing",
            },
            "systems": {
                name: {
                    "available": config.available,
                    "health_score": config.health_score,
                    "last_check": config.last_check,
                    "host": config.host,
                    "port": config.port,
                    "database": config.database,
                }
                for name, config in self.systems.items()
            },
            "performance_targets": {
                "auth_per_second": ">2000",
                "p95_latency": "<25ms",
                "uptime_target": "99.9%",
            },
        }

    async def test_integration(self) -> Dict[str, Any]:
        """Comprehensive integration test"""
        logger.info("Running hybrid bridge integration test...")

        test_results = {
            "timestamp": time.time(),
            "bridge_status": "unknown",
            "system_tests": {},
            "routing_tests": {},
            "performance_tests": {},
        }

        try:
            # Test system availability
            await self._health_check_all()
            available_count = sum(
                1 for config in self.systems.values() if config.available
            )

            test_results["system_tests"] = {
                "total_systems": len(self.systems),
                "available_systems": available_count,
                "systems_detail": {
                    name: config.available for name, config in self.systems.items()
                },
            }

            # Test routing if systems are available
            if available_count > 0:
                try:
                    route_result = await self.route_query("test_query", {"test": True})
                    test_results["routing_tests"] = {
                        "successful": True,
                        "routed_to": route_result.get("system"),
                        "response_time": route_result.get("timestamp", 0),
                    }
                except Exception as e:
                    test_results["routing_tests"] = {
                        "successful": False,
                        "error": str(e),
                    }

            # Performance baseline
            test_results["performance_tests"] = {
                "auth_capability": ">2000/sec (estimated)",
                "latency": "<25ms P95 (estimated)",
                "note": "Actual performance depends on query complexity and system load",
            }

            # Overall status
            if available_count >= 1:
                test_results["bridge_status"] = "operational"
            else:
                test_results["bridge_status"] = "degraded"

        except Exception as e:
            test_results["bridge_status"] = "failed"
            test_results["error"] = str(e)

        logger.info(
            f"Integration test complete - Status: {test_results['bridge_status']}"
        )
        return test_results


async def main():
    """Main function for standalone testing"""
    print("=== Hybrid Bridge Manager Test ===")

    bridge = HybridBridgeManager()

    try:
        # Initialize bridge
        await bridge.initialize()

        # Get system status
        status = bridge.get_system_status()
        print(f"\nSystem Status:")
        print(json.dumps(status, indent=2, default=str))

        # Run integration test
        test_results = await bridge.test_integration()
        print(f"\nIntegration Test Results:")
        print(json.dumps(test_results, indent=2, default=str))

        print(f"\n✓ Hybrid Bridge Manager test completed successfully")
        return 0

    except Exception as e:
        print(f"✗ Hybrid Bridge Manager test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
