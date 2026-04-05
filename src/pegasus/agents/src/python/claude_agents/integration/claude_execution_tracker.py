#!/usr/bin/env python3
"""
Claude Execution Tracker - Captures and learns from every Claude Code execution
Integrates seamlessly with the enhanced learning system
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import psutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    import psycopg2
    from psycopg2.extras import Json
except ImportError:
    # Silent install if needed
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"]
    )
    import psycopg2
    from psycopg2.extras import Json


class ClaudeExecutionTracker:
    """Tracks every Claude Code execution for learning system"""

    def __init__(self):
        """Initialize tracker with database connection"""
        self.db_config = {
            "host": "localhost",
            "port": "5433",
            "database": "claude_agents_auth",
            "user": "claude_agent",
            "password": "claude_secure_password",
        }
        self.log_dir = Path.home() / ".claude-home" / "learning_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def get_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(**self.db_config)
        except:
            # Fallback to file logging if database unavailable
            return None

    def get_execution_context(self) -> Dict[str, Any]:
        """Gather execution context information"""
        context = {
            "working_directory": os.getcwd(),
            "user": os.environ.get("USER", "unknown"),
            "hostname": os.environ.get("HOSTNAME", "unknown"),
            "python_version": sys.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": {
                "claude_version": os.environ.get("CLAUDE_VERSION", "unknown"),
                "learning_enabled": os.environ.get("CLAUDE_LEARNING", "true"),
                "project_root": os.environ.get("CLAUDE_PROJECT_ROOT", None),
            },
        }

        # Get Git context if available
        try:
            git_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
            ).strip()
            context["git_commit"] = git_hash
        except:
            context["git_commit"] = None

        # Get system metrics
        try:
            context["system_metrics"] = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage("/").percent,
            }
        except:
            context["system_metrics"] = {}

        return context

    def hash_task(self, task_description: str) -> str:
        """Generate hash for task description for pattern matching"""
        return hashlib.sha256(task_description.encode()).hexdigest()[:16]

    def track_start(
        self, task_id: str, task_description: str, agent_name: str = "claude-code"
    ):
        """Track the start of a Claude execution"""
        context = self.get_execution_context()
        start_time = datetime.now(timezone.utc)

        # Create tracking record
        tracking_data = {
            "task_id": task_id,
            "task_description": task_description,
            "task_hash": self.hash_task(task_description),
            "agent_name": agent_name,
            "start_time": start_time.isoformat(),
            "context": context,
            "status": "started",
        }

        # Try database insertion
        conn = self.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO learning.agent_metrics (
                        task_id, agent_name, execution_start, status,
                        execution_context, user_id, project_path,
                        cpu_usage_percent, memory_usage_mb
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        task_id,
                        agent_name,
                        start_time,
                        "started",
                        Json(context),
                        context["user"],
                        context["working_directory"],
                        context["system_metrics"].get("cpu_percent", 0),
                        psutil.virtual_memory().used / (1024 * 1024) if psutil else 0,
                    ),
                )

                # Also track task embedding
                cursor.execute(
                    """
                    INSERT INTO learning.task_embeddings (
                        task_id, agent_name, task_description, task_category
                    ) VALUES (%s, %s, %s, %s)
                    ON CONFLICT (task_id) DO NOTHING
                """,
                    (
                        task_id,
                        agent_name,
                        task_description,
                        self.categorize_task(task_description),
                    ),
                )

                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                # Fallback to file logging
                self.log_to_file(tracking_data)
        else:
            # Log to file if database unavailable
            self.log_to_file(tracking_data)

    def track_complete(
        self, task_id: str, success: bool, exit_code: int, duration: int
    ):
        """Track the completion of a Claude execution"""
        end_time = datetime.now(timezone.utc)

        # Create completion record
        completion_data = {
            "task_id": task_id,
            "end_time": end_time.isoformat(),
            "success": success,
            "exit_code": exit_code,
            "duration_seconds": duration,
            "status": "completed" if success else "failed",
        }

        # Try database update
        conn = self.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE learning.agent_metrics
                    SET execution_end = %s,
                        duration_ms = %s,
                        status = %s,
                        success_score = %s
                    WHERE task_id = %s
                """,
                    (
                        end_time,
                        duration * 1000,  # Convert to milliseconds
                        completion_data["status"],
                        1.0 if success else 0.0,
                        task_id,
                    ),
                )

                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                # Fallback to file logging
                self.log_to_file(completion_data)
        else:
            # Log to file if database unavailable
            self.log_to_file(completion_data)

    def categorize_task(self, task_description: str) -> str:
        """Categorize task based on keywords"""
        task_lower = task_description.lower()

        # Task categorization logic
        if any(word in task_lower for word in ["test", "validate", "check", "verify"]):
            return "testing"
        elif any(word in task_lower for word in ["deploy", "release", "publish"]):
            return "deployment"
        elif any(word in task_lower for word in ["security", "audit", "vulnerability"]):
            return "security"
        elif any(word in task_lower for word in ["optimize", "performance", "speed"]):
            return "optimization"
        elif any(word in task_lower for word in ["fix", "bug", "error", "issue"]):
            return "bugfix"
        elif any(
            word in task_lower for word in ["create", "build", "implement", "add"]
        ):
            return "development"
        elif any(word in task_lower for word in ["refactor", "clean", "organize"]):
            return "refactoring"
        elif any(word in task_lower for word in ["document", "readme", "docs"]):
            return "documentation"
        else:
            return "general"

    def log_to_file(self, data: Dict[str, Any]):
        """Fallback file logging when database is unavailable"""
        log_file = (
            self.log_dir / f"claude_execution_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )

        with open(log_file, "a") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def sync_file_logs_to_database(self):
        """Sync file logs to database when it becomes available"""
        conn = self.get_connection()
        if not conn:
            return

        # Find all log files
        log_files = list(self.log_dir.glob("claude_execution_*.jsonl"))

        for log_file in log_files:
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            # Insert into database
                            self._insert_log_to_database(conn, data)
                        except:
                            continue

                # Rename processed file
                log_file.rename(log_file.with_suffix(".jsonl.processed"))

            except Exception as e:
                print(f"Error syncing log file {log_file}: {e}", file=sys.stderr)

        conn.close()

    def _insert_log_to_database(self, conn, data: Dict[str, Any]):
        """Insert log data into database"""
        cursor = conn.cursor()

        if data.get("status") == "started":
            # Insert start record
            cursor.execute(
                """
                INSERT INTO learning.agent_metrics (
                    task_id, agent_name, execution_start, status,
                    execution_context
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (task_id) DO NOTHING
            """,
                (
                    data["task_id"],
                    data.get("agent_name", "claude-code"),
                    data["start_time"],
                    "started",
                    Json(data.get("context", {})),
                ),
            )
        elif data.get("status") in ["completed", "failed"]:
            # Update completion record
            cursor.execute(
                """
                UPDATE learning.agent_metrics
                SET execution_end = %s,
                    duration_ms = %s,
                    status = %s,
                    success_score = %s
                WHERE task_id = %s
            """,
                (
                    data["end_time"],
                    data.get("duration_seconds", 0) * 1000,
                    data["status"],
                    1.0 if data.get("success") else 0.0,
                    data["task_id"],
                ),
            )

        conn.commit()
        cursor.close()

    def get_task_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get task execution statistics"""
        conn = self.get_connection()
        if not conn:
            return {}

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_executions,
                AVG(duration_ms) as avg_duration_ms,
                SUM(CASE WHEN success_score = 1 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as success_rate,
                COUNT(DISTINCT agent_name) as unique_agents
            FROM learning.agent_metrics
            WHERE execution_start >= NOW() - INTERVAL '%s days'
        """,
            (days,),
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return {
            "total_executions": result[0],
            "avg_duration_ms": float(result[1]) if result[1] else 0,
            "success_rate": float(result[2]) if result[2] else 0,
            "unique_agents": result[3],
        }


def main():
    """Main entry point for command-line usage"""
    parser = argparse.ArgumentParser(description="Claude Execution Tracker")
    parser.add_argument(
        "action",
        choices=["start", "complete", "sync", "stats"],
        help="Action to perform",
    )
    parser.add_argument("--task-id", help="Task ID")
    parser.add_argument(
        "--task", "--task-description", dest="task_description", help="Task description"
    )
    parser.add_argument(
        "--agent",
        "--agent-name",
        dest="agent_name",
        default="claude-code",
        help="Agent name",
    )
    parser.add_argument(
        "--success",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Success status",
    )
    parser.add_argument("--exit-code", type=int, default=0, help="Exit code")
    parser.add_argument("--duration", type=int, default=0, help="Duration in seconds")
    parser.add_argument("--start-time", help="Start time")
    parser.add_argument("--end-time", help="End time")

    args = parser.parse_args()
    tracker = ClaudeExecutionTracker()

    if args.action == "start":
        task_id = args.task_id or str(uuid.uuid4())
        task_description = args.task_description or "Claude Code execution"
        tracker.track_start(task_id, task_description, args.agent_name)
        print(task_id)  # Output task ID for tracking

    elif args.action == "complete":
        if not args.task_id:
            print("Error: --task-id required for complete action", file=sys.stderr)
            sys.exit(1)
        tracker.track_complete(
            args.task_id, args.success, args.exit_code, args.duration
        )

    elif args.action == "sync":
        tracker.sync_file_logs_to_database()
        print("File logs synced to database")

    elif args.action == "stats":
        stats = tracker.get_task_statistics()
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
