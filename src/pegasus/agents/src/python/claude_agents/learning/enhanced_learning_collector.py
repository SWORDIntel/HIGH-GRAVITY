#!/usr/bin/env python3
"""
Enhanced Learning System Data Collector
Collects comprehensive metrics from agent executions and system operations
"""

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
import psutil

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import get_project_root
except ImportError:
    # Fallback if path_utilities not available
    def get_project_root():
        return Path(__file__).parent.parent.parent


try:
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import Json, RealDictCursor
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import Json, RealDictCursor

try:
    import openvino as ov

    OPENVINO_AVAILABLE = True
except ImportError:
    OPENVINO_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EnhancedLearningCollector:
    """Collects and stores comprehensive agent execution metrics"""

    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """Initialize the collector with database configuration"""
        self.db_config = db_config or self._get_default_config()
        self.connection_pool = None
        self.session_id = str(uuid4())
        self.openvino_core = None
        self._init_database_pool()
        self._init_openvino()

    def _get_default_config(self) -> Dict[str, str]:
        """Get default database configuration for Docker container"""
        return {
            "host": "localhost",
            "port": "5433",
            "database": "claude_agents_auth",
            "user": "claude_agent",
            "password": "claude_secure_password",
        }

    def _init_database_pool(self):
        """Initialize PostgreSQL connection pool"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,
                20,
                host=self.db_config["host"],
                port=self.db_config["port"],
                database=self.db_config["database"],
                user=self.db_config["user"],
                password=self.db_config["password"],
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    def _init_openvino(self):
        """Initialize OpenVINO if available"""
        if OPENVINO_AVAILABLE:
            try:
                self.openvino_core = ov.Core()
                devices = self.openvino_core.available_devices
                logger.info(f"OpenVINO initialized with devices: {devices}")
            except Exception as e:
                logger.warning(f"OpenVINO initialization failed: {e}")
                self.openvino_core = None

    def get_connection(self):
        """Get a connection from the pool"""
        return self.connection_pool.getconn()

    def put_connection(self, conn):
        """Return a connection to the pool"""
        self.connection_pool.putconn(conn)

    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Get GPU usage if available
        gpu_usage = self._get_gpu_usage()
        npu_usage = self._get_npu_usage()

        # Network I/O
        net_io = psutil.net_io_counters()

        return {
            "cpu_usage_percent": cpu_percent,
            "memory_usage_mb": memory.used / (1024 * 1024),
            "disk_io_kb": 0,  # Would need to track deltas
            "network_io_kb": (net_io.bytes_sent + net_io.bytes_recv) / 1024,
            "gpu_usage_percent": gpu_usage,
            "npu_usage_percent": npu_usage,
            "system_cpu_usage": cpu_percent,
            "system_memory_usage_gb": memory.used / (1024 * 1024 * 1024),
            "disk_usage_gb": disk.used / (1024 * 1024 * 1024),
        }

    def _get_gpu_usage(self) -> Optional[float]:
        """Get GPU usage percentage"""
        try:
            # Try nvidia-smi for NVIDIA GPUs
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except:
            pass

        # Try Intel GPU monitoring
        try:
            result = subprocess.run(
                ["intel_gpu_top", "-J", "-s", "1"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("engines", {}).get("Render/3D", {}).get("busy", 0)
        except:
            pass

        return None

    def _get_npu_usage(self) -> Optional[float]:
        """Get NPU usage percentage"""
        if self.openvino_core and "NPU" in self.openvino_core.available_devices:
            try:
                # This is a placeholder - actual NPU metrics would need specific APIs
                return 0.0
            except:
                pass
        return None

    def generate_embedding(self, text: str, dimensions: int = 384) -> List[float]:
        """Generate text embedding using simple hash-based approach"""
        # Simple deterministic embedding based on text hash
        # In production, use a proper embedding model
        hash_object = hashlib.sha256(text.encode())
        hash_bytes = hash_object.digest()

        # Extend hash to required dimensions
        np.random.seed(int.from_bytes(hash_bytes[:4], "big"))
        embedding = np.random.randn(dimensions)

        # Normalize to unit vector
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding.tolist()

    async def track_agent_execution(
        self, agent_name: str, task_description: str, execution_context: Dict[str, Any]
    ) -> str:
        """Track an agent execution with comprehensive metrics"""
        task_id = str(uuid4())
        start_time = datetime.now(timezone.utc)

        # Collect initial metrics
        initial_metrics = self.collect_system_metrics()

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Insert agent metrics
            cursor.execute(
                """
                INSERT INTO learning.agent_metrics (
                    agent_name, agent_uuid, task_id, execution_start,
                    status, cpu_usage_percent, memory_usage_mb,
                    gpu_usage_percent, npu_usage_percent,
                    execution_context, user_id, session_id, project_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    agent_name,
                    str(uuid4()),
                    task_id,
                    start_time,
                    "started",
                    initial_metrics["cpu_usage_percent"],
                    initial_metrics["memory_usage_mb"],
                    initial_metrics.get("gpu_usage_percent"),
                    initial_metrics.get("npu_usage_percent"),
                    Json(execution_context),
                    execution_context.get("user_id", "system"),
                    self.session_id,
                    execution_context.get("project_path", os.getcwd()),
                ),
            )

            metric_id = cursor.fetchone()[0]

            # Generate and store task embedding
            embedding = self.generate_embedding(task_description)
            cursor.execute(
                """
                INSERT INTO learning.task_embeddings (
                    task_id, agent_name, task_description, embedding,
                    task_category, complexity_score
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (
                    task_id,
                    agent_name,
                    task_description,
                    embedding,
                    execution_context.get("category", "general"),
                    execution_context.get("complexity", 0.5),
                ),
            )

            conn.commit()
            logger.info(f"Started tracking task {task_id} for agent {agent_name}")

        except Exception as e:
            logger.error(f"Failed to track agent execution: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.put_connection(conn)

        return task_id

    async def complete_agent_execution(
        self,
        task_id: str,
        success: bool,
        error_message: Optional[str] = None,
        output_size: Optional[int] = None,
    ):
        """Complete tracking of an agent execution"""
        end_time = datetime.now(timezone.utc)
        final_metrics = self.collect_system_metrics()

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get start time
            cursor.execute(
                """
                SELECT execution_start FROM learning.agent_metrics
                WHERE task_id = %s
            """,
                (task_id,),
            )

            result = cursor.fetchone()
            if result:
                start_time = result[0]
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                # Update metrics
                cursor.execute(
                    """
                    UPDATE learning.agent_metrics
                    SET execution_end = %s,
                        duration_ms = %s,
                        status = %s,
                        success_score = %s,
                        error_message = %s,
                        output_size_bytes = %s
                    WHERE task_id = %s
                """,
                    (
                        end_time,
                        duration_ms,
                        "completed" if success else "failed",
                        1.0 if success else 0.0,
                        error_message,
                        output_size,
                        task_id,
                    ),
                )

                conn.commit()
                logger.info(f"Completed tracking task {task_id}, success: {success}")

        except Exception as e:
            logger.error(f"Failed to complete agent execution: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.put_connection(conn)

    async def track_agent_interaction(
        self,
        source_agent: str,
        target_agent: str,
        interaction_type: str,
        message_content: str,
        workflow_id: Optional[str] = None,
    ):
        """Track interaction between agents"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO learning.interaction_logs (
                    session_id, source_agent, target_agent,
                    interaction_type, message_content, message_size_bytes,
                    workflow_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    self.session_id,
                    source_agent,
                    target_agent,
                    interaction_type,
                    message_content,
                    len(message_content.encode()),
                    workflow_id,
                ),
            )

            conn.commit()
            logger.info(f"Tracked interaction: {source_agent} -> {target_agent}")

        except Exception as e:
            logger.error(f"Failed to track interaction: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.put_connection(conn)

    async def track_git_operation(
        self,
        operation_type: str,
        repository_path: str,
        files_affected: int,
        lines_changed: int,
        shadowgit_performance: Optional[float] = None,
    ):
        """Track Git operation with Shadowgit performance metrics"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO learning.git_operations_tracking (
                    operation_type, repository_path, files_affected,
                    lines_changed, shadowgit_performance, acceleration_factor
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (
                    operation_type,
                    repository_path,
                    files_affected,
                    lines_changed,
                    shadowgit_performance,
                    (
                        shadowgit_performance / 930000000.0
                        if shadowgit_performance
                        else None
                    ),
                ),
            )

            conn.commit()
            logger.info(f"Tracked Git operation: {operation_type}")

        except Exception as e:
            logger.error(f"Failed to track Git operation: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.put_connection(conn)

    async def collect_system_health(self):
        """Collect and store system health metrics"""
        metrics = self.collect_system_metrics()

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Count active agents (placeholder - would need actual tracking)
            active_agents = 0

            # OpenVINO metrics
            openvino_inference_count = 0
            openvino_latency = None

            cursor.execute(
                """
                INSERT INTO learning.system_health_metrics (
                    db_connections, db_cpu_usage, db_memory_usage_mb,
                    active_agents, system_cpu_usage, system_memory_usage_gb,
                    gpu_utilization, npu_utilization,
                    openvino_inference_count, openvino_avg_latency_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    1,  # Current connection
                    metrics["cpu_usage_percent"],
                    metrics["memory_usage_mb"],
                    active_agents,
                    metrics["system_cpu_usage"],
                    metrics["system_memory_usage_gb"],
                    metrics.get("gpu_usage_percent"),
                    metrics.get("npu_usage_percent"),
                    openvino_inference_count,
                    openvino_latency,
                ),
            )

            conn.commit()
            logger.info("Collected system health metrics")

        except Exception as e:
            logger.error(f"Failed to collect system health: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.put_connection(conn)

    async def update_performance_baselines(self):
        """Update performance baselines for all agents"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Call the PostgreSQL function to update baselines
            cursor.execute("SELECT learning.update_performance_baselines()")

            conn.commit()
            logger.info("Updated performance baselines")

        except Exception as e:
            logger.error(f"Failed to update baselines: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.put_connection(conn)

    def close(self):
        """Close all database connections"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connections closed")


async def main():
    """Test the enhanced learning collector"""
    collector = EnhancedLearningCollector()

    # Test tracking an agent execution
    task_id = await collector.track_agent_execution(
        agent_name="DIRECTOR",
        task_description="Create strategic plan for system optimization",
        execution_context={
            "category": "planning",
            "complexity": 0.8,
            "user_id": "test_user",
            "project_path": str(get_project_root()),
        },
    )

    # Simulate some work
    await asyncio.sleep(1)

    # Complete the execution
    await collector.complete_agent_execution(
        task_id=task_id, success=True, output_size=1024
    )

    # Track an interaction
    await collector.track_agent_interaction(
        source_agent="DIRECTOR",
        target_agent="ARCHITECT",
        interaction_type="task_delegation",
        message_content="Design system architecture for optimization",
    )

    # Track a Git operation
    await collector.track_git_operation(
        operation_type="diff",
        repository_path=str(get_project_root()),
        files_affected=10,
        lines_changed=500,
        shadowgit_performance=930000000.0,
    )

    # Collect system health
    await collector.collect_system_health()

    # Update baselines
    await collector.update_performance_baselines()

    collector.close()
    print("Test completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
