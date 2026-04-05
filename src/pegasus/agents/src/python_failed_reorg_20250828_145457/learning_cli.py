#!/usr/bin/env python3
"""
Learning System CLI - Interactive tool for managing agent learning
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from learning_orchestrator_bridge import (
        EnhancedLearningOrchestrator,
        ExecutionContext,
        LearningStrategy,
    )
    from postgresql_learning_system import (
        AgentTaskExecution,
        TaskContext,
        UltimatePostgreSQLLearningSystem,
    )

    IMPORTS_AVAILABLE = True
    ULTIMATE_SYSTEM_AVAILABLE = True
except ImportError:
    try:
        from learning_orchestrator_bridge import (
            EnhancedLearningOrchestrator,
            ExecutionContext,
            LearningStrategy,
        )
        from postgresql_learning_system import (
            AgentTaskExecution,
            PostgreSQLLearningSystem,
        )

        IMPORTS_AVAILABLE = True
        ULTIMATE_SYSTEM_AVAILABLE = False
    except ImportError as e:
        print(f"Warning: Learning system modules not available: {e}")
        IMPORTS_AVAILABLE = False
        ULTIMATE_SYSTEM_AVAILABLE = False


class LearningCLI:
    """Command-line interface for the learning system"""

    def __init__(self):
        if IMPORTS_AVAILABLE and ULTIMATE_SYSTEM_AVAILABLE:
            # Use the ultimate learning system with local database
            db_config = {
                "host": '${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}database/data/run',
                "port": 5433,
                "database": "claude_auth",
                "user": "claude_auth",
                "password": "claude_auth_pass",
            }
            self.learning_system = UltimatePostgreSQLLearningSystem(db_config)
            self.orchestrator = EnhancedLearningOrchestrator()
            self.is_ultimate = True
        elif IMPORTS_AVAILABLE:
            # Fallback to basic system
            self.learning_system = PostgreSQLLearningSystem()
            self.orchestrator = EnhancedLearningOrchestrator()
            self.is_ultimate = False
        else:
            self.learning_system = None
            self.orchestrator = None
            self.is_ultimate = False

    async def status(self):
        """Show learning system status"""
        if not self.learning_system:
            print("Learning system not available")
            return

        if self.is_ultimate:
            await self.learning_system.initialize()
            dashboard = await self.learning_system.get_ultimate_dashboard()
            stats = dashboard.get("statistics", {})
            health = dashboard.get("system_health", {})

            print("=== Ultimate Agent Learning System Status ===")
            print(f"Version: {dashboard.get('version', 'unknown')}")
            print(f"Status: {dashboard.get('status', 'unknown')}")
            print(f"Total Executions: {stats.get('total_executions', 0)}")
            print(f"Success Rate: {stats.get('overall_success_rate', 0):.1%}")
            print(f"Average Duration: {stats.get('avg_duration', 0):.1f}s")
            print(f"24h Executions: {stats.get('executions_24h', 0)}")
            print(f"Unique Task Types: {stats.get('unique_task_types', 0)}")
            print(f"Total Anomalies: {stats.get('total_anomalies', 0)}")

            print(f"\nSystem Health:")
            print(f"  Database: {health.get('database_integration', 'unknown')}")
            print(f"  ML Available: {'✅' if health.get('ml_available') else '❌'}")
            print(f"  Learning Mode: {health.get('learning_mode', 'unknown')}")
            print(f"  Learning Tables: {len(health.get('learning_tables', []))}")

            if dashboard.get("agent_leaderboard"):
                print(f"\nTop Performing Agents:")
                for agent in dashboard["agent_leaderboard"][:5]:
                    print(
                        f"  {agent['agent_name']}: {agent['success_rate']:.1%} ({agent['total_invocations']} tasks)"
                    )

        else:
            # Fallback to basic status
            print("=== Basic Learning System Status ===")
            print("Status: Basic system - upgrade to ultimate system for full features")

    async def insights(self, limit=10):
        """Show recent learning insights"""
        if not self.learning_system:
            print("Learning system not available")
            return

        if self.is_ultimate:
            await self.learning_system.initialize()
            dashboard = await self.learning_system.get_ultimate_dashboard()
            insights = dashboard.get("recent_insights", [])[:limit]

            print(f"=== Recent Learning Insights (Last {len(insights)}) ===")
            for i, insight in enumerate(insights, 1):
                created_at = datetime.fromisoformat(
                    insight["created_at"].replace("Z", "+00:00")
                )
                age = datetime.now() - created_at.replace(tzinfo=None)
                print(
                    f"\n{i}. [{insight['insight_type'].upper()}] Confidence: {insight['confidence_score']:.2f}"
                )
                print(f"   {insight['title']}")
                print(f"   Age: {age.days}d {age.seconds//3600}h ago")
                if insight.get("category"):
                    print(f"   Category: {insight['category']}")
        else:
            # Fallback for basic system
            print("=== Basic Learning System Insights ===")
            print("Upgrade to ultimate system for comprehensive insights")

    async def analyze(self):
        """Run learning analysis"""
        if not self.learning_system:
            print("Learning system not available")
            return

        print("Running learning analysis...")
        insights = self.learning_system.analyze_patterns()

        if insights:
            print(f"Generated {len(insights)} new insights:")
            for insight in insights:
                print(
                    f"  - {insight.description} (confidence: {insight.confidence:.2f})"
                )
        else:
            print("No new insights generated (may need more execution data)")

        # Train models if enough data
        if len(self.learning_system.execution_history) >= 50:
            print("Training prediction models...")
            self.learning_system.train_prediction_models()
            print("Model training complete")
        else:
            needed = 50 - len(self.learning_system.execution_history)
            print(f"Need {needed} more executions before training models")

    async def predict(self, task_type, complexity=1.0):
        """Predict optimal agents for a task"""
        if not self.learning_system:
            print("Learning system not available")
            return

        if self.is_ultimate:
            await self.learning_system.initialize()
            agents = await self.learning_system.get_optimal_agents(
                task_type, complexity
            )

            # Get detailed recommendation
            task_context = TaskContext(
                task_id=f"cli_pred_{task_type}",
                task_type=task_type,
                description=f"CLI prediction for {task_type}",
                complexity_score=complexity,
                priority=5,
                deadline=None,
                user_context={},
            )

            recommendation = (
                await self.learning_system.get_agent_recommendation_with_confidence(
                    task_context
                )
            )

            print(f"=== Ultimate Agent Predictions for '{task_type}' ===")
            print(f"Complexity: {complexity}")
            print(f"Recommended Agents: {', '.join(agents)}")

            primary = recommendation.get("primary_recommendation", {})
            print(f"Expected Success Rate: {primary.get('expected_success', 0):.1%}")
            print(f"Expected Duration: {primary.get('expected_duration', 0):.1f}s")
            print(f"Confidence: {primary.get('confidence', 0):.1%}")

            if primary.get("risk_factors"):
                print(f"\nRisk Factors:")
                for risk in primary["risk_factors"]:
                    print(f"  • {risk}")

            if recommendation.get("alternatives"):
                print(f"\nAlternative Approaches:")
                for i, alt in enumerate(recommendation["alternatives"][:2], 1):
                    print(
                        f"  {i}. {', '.join(alt['agents'])} (success: {alt['expected_success_rate']:.1%})"
                    )
        else:
            print("=== Basic Agent Predictions ===")
            print("Upgrade to ultimate system for ML-powered predictions")

    async def simulate(self, task_type, count=5):
        """Simulate task executions for testing"""
        if not self.orchestrator:
            print("Orchestrator not available")
            return

        print(f"Simulating {count} executions of type '{task_type}'...")

        await self.orchestrator.initialize()

        for i in range(count):
            description = f"Simulated {task_type} task #{i+1}"
            complexity = 1.0 + (i * 0.5)  # Increasing complexity

            try:
                # Use new ExecutionContext if available
                if "ExecutionContext" in globals():
                    from datetime import timedelta

                    context = ExecutionContext(
                        task_id=f"sim_{task_type}_{i+1}",
                        task_type=task_type,
                        description=description,
                        complexity=complexity,
                        priority=3,
                        deadline=datetime.now() + timedelta(hours=1),
                    )
                    result = await self.orchestrator.execute_with_learning(context)
                else:
                    # Fallback to old interface
                    result = await self.orchestrator.execute_with_learning(
                        description, task_type, complexity=complexity
                    )

                status = "✓" if result.get("success") else "✗"
                print(f"  {i+1}. {status} {description} (complexity: {complexity:.1f})")

            except Exception as e:
                print(f"  {i+1}. ✗ {description} - Error: {e}")

            # Small delay between simulations
            await asyncio.sleep(0.1)

        print(
            f"\nSimulation complete. Run 'learning-cli status' to see updated metrics."
        )

    async def dashboard(self):
        """Show comprehensive learning dashboard"""
        if not self.orchestrator:
            print("Orchestrator not available")
            return

        await self.orchestrator.initialize()

        # Try enhanced dashboard first, fall back to regular
        try:
            dashboard = await self.orchestrator.get_enhanced_dashboard()
        except AttributeError:
            dashboard = await self.orchestrator.get_learning_dashboard()

        print("=== Learning Dashboard ===")
        print(json.dumps(dashboard, indent=2, default=str))

    async def export(self, filepath="learning_export.json"):
        """Export learning data"""
        if not self.learning_system:
            print("Learning system not available")
            return

        export_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.learning_system.get_learning_summary(),
            "executions": [
                {
                    "task_id": e.task_id,
                    "task_type": e.task_type,
                    "agents_used": e.agents_used,
                    "duration": e.duration,
                    "success": e.success,
                    "complexity_score": e.complexity_score,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in self.learning_system.execution_history[-100:]  # Last 100
            ],
            "insights": [
                {
                    "type": i.insight_type,
                    "confidence": i.confidence,
                    "description": i.description,
                    "data": i.data,
                    "created_at": i.created_at.isoformat(),
                }
                for i in self.learning_system.insights
            ],
        }

        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"Learning data exported to {filepath}")
        print(f"  - {len(export_data['executions'])} executions")
        print(f"  - {len(export_data['insights'])} insights")

    async def clear(self, confirm=False):
        """Clear learning data"""
        if not confirm:
            print("This will clear all learning data. Use --confirm to proceed.")
            return

        if self.learning_system:
            # Clear in-memory data
            self.learning_system.execution_history.clear()
            self.learning_system.agent_performance.clear()
            self.learning_system.insights.clear()
            self.learning_system.models.clear()

            # Clear database
            import sqlite3

            conn = sqlite3.connect(self.learning_system.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM task_executions")
            cursor.execute("DELETE FROM agent_performance")
            cursor.execute("DELETE FROM learning_insights")
            conn.commit()
            conn.close()

            print("Learning data cleared")
        else:
            print("Learning system not available")


async def main():
    parser = argparse.ArgumentParser(description="Agent Learning System CLI")
    parser.add_argument(
        "command",
        choices=[
            "status",
            "insights",
            "analyze",
            "predict",
            "simulate",
            "dashboard",
            "export",
            "clear",
        ],
        help="Command to execute",
    )

    # Command-specific arguments
    parser.add_argument(
        "--task-type", default="general", help="Task type for prediction/simulation"
    )
    parser.add_argument(
        "--complexity", type=float, default=1.0, help="Task complexity (0.1-5.0)"
    )
    parser.add_argument(
        "--count", type=int, default=5, help="Number of simulations to run"
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Limit for insights display"
    )
    parser.add_argument(
        "--output", default="learning_export.json", help="Export file path"
    )
    parser.add_argument(
        "--confirm", action="store_true", help="Confirm destructive operations"
    )

    args = parser.parse_args()

    cli = LearningCLI()

    try:
        if args.command == "status":
            await cli.status()
        elif args.command == "insights":
            await cli.insights(args.limit)
        elif args.command == "analyze":
            await cli.analyze()
        elif args.command == "predict":
            await cli.predict(args.task_type, args.complexity)
        elif args.command == "simulate":
            await cli.simulate(args.task_type, args.count)
        elif args.command == "dashboard":
            await cli.dashboard()
        elif args.command == "export":
            await cli.export(args.output)
        elif args.command == "clear":
            await cli.clear(args.confirm)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
