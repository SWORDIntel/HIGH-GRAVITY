#!/usr/bin/env python3
"""
Simplified Learning System CLI - Works with existing PostgreSQL schema
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

import psycopg2


class SimpleLearningCLI:
    """Simplified CLI for the enhanced learning system"""

    def __init__(self):
        self.db_config = {
            "host": '${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}database/data/run',
            "port": 5433,
            "database": "claude_auth",
            "user": "claude_auth",
            "password": "claude_auth_pass",
        }

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    async def status(self):
        """Show learning system status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get execution statistics
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_executions,
                    AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                    AVG(duration_seconds) as avg_duration,
                    COUNT(DISTINCT task_type) as unique_task_types,
                    COUNT(*) FILTER (WHERE start_time >= NOW() - INTERVAL '24 hours') as executions_24h
                FROM agent_task_executions
            """
            )
            stats = cursor.fetchone()

            # Get agent performance
            cursor.execute(
                """
                SELECT 
                    agent_name,
                    SUM(success_count) as total_success,
                    SUM(success_count + failure_count) as total_tasks,
                    AVG(avg_response_time) as avg_time
                FROM agent_performance_metrics
                GROUP BY agent_name
                ORDER BY total_success DESC
                LIMIT 5
            """
            )
            top_agents = cursor.fetchall()

            print("=== Enhanced Learning System Status ===")
            print(f"Database: PostgreSQL 17 (Enhanced)")
            print(f"Total Executions: {stats[0] or 0}")
            print(f"Success Rate: {(stats[1] or 0):.1%}")
            print(f"Average Duration: {(stats[2] or 0):.1f}s")
            print(f"Unique Task Types: {stats[3] or 0}")
            print(f"24h Executions: {stats[4] or 0}")

            if top_agents:
                print(f"\nTop Performing Agents:")
                for agent, success, total, avg_time in top_agents:
                    success_rate = success / total if total > 0 else 0
                    print(
                        f"  {agent}: {success_rate:.1%} ({total} tasks, {avg_time or 0:.1f}s avg)"
                    )

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"❌ Error getting status: {e}")

    async def add_sample_data(self, count=3):
        """Add sample learning data for testing"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            sample_executions = [
                {
                    "task_type": "web_development",
                    "description": "Create React authentication system",
                    "agents": ["WEB", "APIDESIGNER", "SECURITY", "TESTBED"],
                    "duration": 67.3,
                    "success": True,
                    "complexity": 3.2,
                },
                {
                    "task_type": "security_audit",
                    "description": "Comprehensive API security review",
                    "agents": ["SECURITY", "SECURITYAUDITOR", "CRYPTOEXPERT"],
                    "duration": 134.7,
                    "success": True,
                    "complexity": 4.5,
                },
                {
                    "task_type": "bug_fix",
                    "description": "Fix memory leak in authentication service",
                    "agents": ["DEBUGGER", "PATCHER", "TESTBED"],
                    "duration": 45.2,
                    "success": True,
                    "complexity": 2.8,
                },
            ]

            for i, exec_data in enumerate(sample_executions[:count]):
                start_time = datetime.now() - timedelta(seconds=exec_data["duration"])
                end_time = datetime.now()

                cursor.execute(
                    """
                    INSERT INTO agent_task_executions (
                        task_type, task_description, agents_invoked, 
                        start_time, end_time, duration_seconds, 
                        success, complexity_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        exec_data["task_type"],
                        exec_data["description"],
                        json.dumps(exec_data["agents"]),
                        start_time,
                        end_time,
                        exec_data["duration"],
                        exec_data["success"],
                        exec_data["complexity"],
                    ),
                )

                # Update agent metrics
                for agent in exec_data["agents"]:
                    cursor.execute(
                        """
                        INSERT INTO agent_performance_metrics (
                            agent_name, task_type, success_count, total_duration, avg_response_time
                        ) VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (agent_name, task_type) DO UPDATE SET
                            success_count = agent_performance_metrics.success_count + %s,
                            total_duration = agent_performance_metrics.total_duration + %s,
                            avg_response_time = (agent_performance_metrics.total_duration + %s) / (agent_performance_metrics.success_count + agent_performance_metrics.failure_count + 1),
                            last_execution = NOW()
                    """,
                        (
                            agent,
                            exec_data["task_type"],
                            1,
                            exec_data["duration"],
                            exec_data["duration"],
                            1,
                            exec_data["duration"],
                            exec_data["duration"],
                        ),
                    )

            conn.commit()
            cursor.close()
            conn.close()

            print(f"✅ Added {count} sample learning records")

        except Exception as e:
            print(f"❌ Error adding sample data: {e}")

    async def predict(self, task_type, complexity=1.0):
        """Predict optimal agents for a task type"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Find best performing agents for this task type
            cursor.execute(
                """
                SELECT 
                    agent_name,
                    success_count,
                    (success_count + failure_count) as total_tasks,
                    avg_response_time,
                    CASE WHEN (success_count + failure_count) > 0 
                         THEN success_count::FLOAT / (success_count + failure_count)
                         ELSE 0 END as success_rate
                FROM agent_performance_metrics
                WHERE task_type = %s 
                    AND (success_count + failure_count) >= 1
                ORDER BY success_rate DESC, success_count DESC
                LIMIT 5
            """,
                (task_type,),
            )

            agents = cursor.fetchall()

            print(f"=== Agent Predictions for '{task_type}' ===")
            print(f"Complexity: {complexity}")

            if agents:
                recommended = [agent[0] for agent in agents]
                print(f"Recommended Agents: {', '.join(recommended)}")

                print(f"\nAgent Performance:")
                for agent, success, total, avg_time, success_rate in agents:
                    print(
                        f"  {agent}: {success_rate:.1%} success ({total} tasks, {avg_time or 0:.1f}s avg)"
                    )

                # Calculate expected metrics
                avg_success_rate = sum(a[4] for a in agents) / len(agents)
                avg_duration = sum(a[3] or 30 for a in agents) / len(agents)
                print(f"\nExpected Success Rate: {avg_success_rate:.1%}")
                print(f"Expected Duration: {avg_duration:.1f}s")
            else:
                # Fallback recommendations
                fallback_agents = {
                    "web_development": ["WEB", "APIDESIGNER", "DATABASE", "TESTBED"],
                    "security_audit": ["SECURITY", "SECURITYAUDITOR", "CRYPTOEXPERT"],
                    "bug_fix": ["DEBUGGER", "PATCHER", "TESTBED", "LINTER"],
                    "deployment": ["DEPLOYER", "INFRASTRUCTURE", "MONITOR"],
                    "performance_optimization": ["OPTIMIZER", "MONITOR", "DATABASE"],
                }.get(task_type, ["DIRECTOR", "PROJECTORCHESTRATOR", "ARCHITECT"])

                print(f"Recommended Agents (fallback): {', '.join(fallback_agents)}")
                print("Note: No historical data available for this task type")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"❌ Error making prediction: {e}")

    async def insights(self, limit=5):
        """Show recent learning insights"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Generate insights from execution data
            cursor.execute(
                """
                WITH task_performance AS (
                    SELECT 
                        task_type,
                        COUNT(*) as execution_count,
                        AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                        AVG(duration_seconds) as avg_duration,
                        MAX(start_time) as last_execution
                    FROM agent_task_executions
                    WHERE start_time >= NOW() - INTERVAL '30 days'
                    GROUP BY task_type
                    HAVING COUNT(*) >= 1
                    ORDER BY execution_count DESC
                )
                SELECT * FROM task_performance LIMIT %s
            """,
                (limit,),
            )

            insights = cursor.fetchall()

            print("=== Learning Insights ===")

            if insights:
                for task_type, count, success_rate, avg_duration, last_exec in insights:
                    confidence = min(0.9, count / 10)

                    print(f"\n• Task Type: {task_type}")
                    print(f"  Executions: {count}")
                    print(f"  Success Rate: {success_rate:.1%}")
                    print(f"  Avg Duration: {avg_duration:.1f}s")
                    print(f"  Confidence: {confidence:.1%}")

                    # Generate recommendations
                    if success_rate < 0.7:
                        print(f"  💡 Consider reviewing {task_type} execution patterns")
                    elif avg_duration > 60:
                        print(f"  💡 {task_type} tasks may benefit from optimization")
                    else:
                        print(f"  ✅ {task_type} performing well")
            else:
                print("No execution data available for insights")
                print("Run 'sample' command to add test data")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"❌ Error generating insights: {e}")

    async def export(self, filename="learning_export.json"):
        """Export learning data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get executions
            cursor.execute(
                """
                SELECT 
                    task_type, task_description, agents_invoked, 
                    duration_seconds, success, complexity_score, start_time
                FROM agent_task_executions
                ORDER BY start_time DESC
                LIMIT 100
            """
            )
            executions = cursor.fetchall()

            # Get agent metrics
            cursor.execute(
                """
                SELECT agent_name, task_type, success_count, failure_count, 
                       total_duration, avg_response_time
                FROM agent_performance_metrics
            """
            )
            metrics = cursor.fetchall()

            export_data = {
                "exported_at": datetime.now().isoformat(),
                "system": "Enhanced PostgreSQL Learning System",
                "database": "PostgreSQL 17",
                "executions": [
                    {
                        "task_type": e[0],
                        "description": e[1],
                        "agents": (
                            json.loads(e[2])
                            if e[2] and isinstance(e[2], str)
                            else (e[2] if isinstance(e[2], list) else [])
                        ),
                        "duration": e[3],
                        "success": e[4],
                        "complexity": e[5],
                        "timestamp": e[6].isoformat() if e[6] else None,
                    }
                    for e in executions
                ],
                "agent_metrics": [
                    {
                        "agent": m[0],
                        "task_type": m[1],
                        "success_count": m[2],
                        "failure_count": m[3],
                        "total_duration": m[4],
                        "avg_response_time": m[5],
                    }
                    for m in metrics
                ],
            }

            with open(filename, "w") as f:
                json.dump(export_data, f, indent=2)

            print(f"✅ Exported learning data to {filename}")
            print(f"  Executions: {len(executions)}")
            print(f"  Agent Metrics: {len(metrics)}")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"❌ Error exporting data: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Enhanced Learning System CLI")
    parser.add_argument(
        "command",
        choices=["status", "insights", "predict", "sample", "export"],
        help="Command to execute",
    )

    parser.add_argument(
        "--task-type", default="web_development", help="Task type for prediction"
    )
    parser.add_argument("--complexity", type=float, default=1.0, help="Task complexity")
    parser.add_argument("--count", type=int, default=3, help="Number of sample records")
    parser.add_argument(
        "--output", default="learning_export.json", help="Export filename"
    )

    args = parser.parse_args()

    cli = SimpleLearningCLI()

    try:
        if args.command == "status":
            await cli.status()
        elif args.command == "insights":
            await cli.insights()
        elif args.command == "predict":
            await cli.predict(args.task_type, args.complexity)
        elif args.command == "sample":
            await cli.add_sample_data(args.count)
        elif args.command == "export":
            await cli.export(args.output)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
