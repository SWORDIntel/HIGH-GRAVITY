#!/usr/bin/env python3
"""
Advanced Learning Analytics for Claude Agent Framework
Implements sophisticated ML/AI analytics based on RESEARCHER agent recommendations
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import get_database_config
except ImportError:
    # Fallback if path_utilities not available
    def get_database_config():
        return {
            "host": "localhost",
            "port": 5433,
            "database": "claude_agents_auth",
            "user": "claude_agent",
            "password": "claude_auth_pass",
        }


# ML imports
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from sklearn.cluster import DBSCAN
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import StandardScaler
except ImportError:
    print("Installing required packages...")
    import subprocess

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "scikit-learn",
            "pandas",
            "psycopg2-binary",
        ]
    )
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from sklearn.cluster import DBSCAN
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceTrend(Enum):
    """Performance trend classification"""

    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    ANOMALOUS = "anomalous"


@dataclass
class AgentPerformanceProfile:
    """Profile of agent performance characteristics"""

    agent_name: str
    avg_execution_time: float
    success_rate: float
    resource_efficiency: float
    collaboration_score: float
    learning_rate: float
    specialization_areas: List[str]


class AdvancedLearningAnalytics:
    """Advanced analytics engine for the learning system"""

    def __init__(self, db_config: Optional[Dict] = None):
        """Initialize analytics engine"""
        self.db_config = db_config or self._get_default_config()
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.performance_classifier = RandomForestClassifier(
            n_estimators=100, random_state=42
        )
        self.scaler = StandardScaler()
        self.agent_profiles: Dict[str, AgentPerformanceProfile] = {}

    def _get_default_config(self) -> Dict[str, str]:
        """Get default database configuration using path utilities"""
        config = get_database_config()
        # Convert port to string for compatibility
        config["port"] = str(config["port"])
        return config

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    async def analyze_performance_trajectories(self) -> Dict[str, Any]:
        """
        Analyze agent performance trajectories to detect learning vs degradation
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Get performance trajectory data
            cursor.execute(
                """
                WITH performance_trends AS (
                    SELECT 
                        agent_name,
                        execution_start,
                        duration_ms,
                        success_score,
                        cpu_usage_percent,
                        memory_usage_mb,
                        AVG(duration_ms) OVER (
                            PARTITION BY agent_name 
                            ORDER BY execution_start 
                            ROWS BETWEEN 10 PRECEDING AND CURRENT ROW
                        ) as rolling_avg,
                        STDDEV(duration_ms) OVER (
                            PARTITION BY agent_name 
                            ORDER BY execution_start 
                            ROWS BETWEEN 10 PRECEDING AND CURRENT ROW
                        ) as rolling_stddev
                    FROM learning.agent_metrics
                    WHERE execution_start >= NOW() - INTERVAL '7 days'
                )
                SELECT 
                    agent_name,
                    execution_start,
                    duration_ms,
                    success_score,
                    rolling_avg,
                    rolling_stddev,
                    CASE 
                        WHEN duration_ms < rolling_avg - 2 * rolling_stddev THEN 'improving'
                        WHEN duration_ms > rolling_avg + 2 * rolling_stddev THEN 'degrading'
                        ELSE 'stable'
                    END as performance_trend
                FROM performance_trends
                ORDER BY agent_name, execution_start DESC
            """
            )

            results = cursor.fetchall()

            # Analyze trends by agent
            agent_trends = {}
            for row in results:
                agent = row["agent_name"]
                if agent not in agent_trends:
                    agent_trends[agent] = {
                        "total_executions": 0,
                        "improving": 0,
                        "stable": 0,
                        "degrading": 0,
                        "avg_duration": 0,
                        "trend_direction": None,
                        "learning_coefficient": 0,
                    }

                agent_trends[agent]["total_executions"] += 1
                agent_trends[agent][row["performance_trend"]] += 1
                agent_trends[agent]["avg_duration"] += row["duration_ms"]

            # Calculate learning coefficients
            for agent, trends in agent_trends.items():
                if trends["total_executions"] > 0:
                    trends["avg_duration"] /= trends["total_executions"]

                    # Learning coefficient: ratio of improvements to degradations
                    if trends["degrading"] > 0:
                        trends["learning_coefficient"] = (
                            trends["improving"] / trends["degrading"]
                        )
                    elif trends["improving"] > 0:
                        trends["learning_coefficient"] = trends["improving"]
                    else:
                        trends["learning_coefficient"] = 0

                    # Determine overall trend
                    if trends["improving"] > trends["degrading"] * 1.5:
                        trends["trend_direction"] = PerformanceTrend.IMPROVING
                    elif trends["degrading"] > trends["improving"] * 1.5:
                        trends["trend_direction"] = PerformanceTrend.DEGRADING
                    else:
                        trends["trend_direction"] = PerformanceTrend.STABLE

            return {
                "agent_trends": agent_trends,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "recommendation": self._generate_trend_recommendations(agent_trends),
            }

        finally:
            cursor.close()
            conn.close()

    def _generate_trend_recommendations(self, agent_trends: Dict) -> List[str]:
        """Generate recommendations based on performance trends"""
        recommendations = []

        for agent, trends in agent_trends.items():
            if trends["trend_direction"] == PerformanceTrend.DEGRADING:
                recommendations.append(
                    f"⚠️ {agent}: Performance degrading - consider retraining or resource reallocation"
                )
            elif trends["trend_direction"] == PerformanceTrend.IMPROVING:
                recommendations.append(
                    f"✅ {agent}: Performance improving - learning coefficient {trends['learning_coefficient']:.2f}"
                )

            if trends["avg_duration"] > 5000:  # 5 seconds
                recommendations.append(
                    f"🐌 {agent}: High average duration ({trends['avg_duration']:.0f}ms) - optimize or parallelize"
                )

        return recommendations

    async def detect_agent_synergies(self) -> Dict[str, Any]:
        """
        Detect synergistic agent combinations using collaboration history
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Get agent collaboration data
            cursor.execute(
                """
                WITH collaboration_pairs AS (
                    SELECT 
                        source_agent,
                        target_agent,
                        COUNT(*) as interaction_count,
                        AVG(latency_ms) as avg_latency,
                        SUM(CASE WHEN success THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as success_rate
                    FROM learning.interaction_logs
                    WHERE request_timestamp >= NOW() - INTERVAL '30 days'
                    GROUP BY source_agent, target_agent
                    HAVING COUNT(*) >= 5
                )
                SELECT 
                    source_agent,
                    target_agent,
                    interaction_count,
                    avg_latency,
                    success_rate,
                    interaction_count * success_rate / NULLIF(avg_latency, 0) as synergy_score
                FROM collaboration_pairs
                ORDER BY synergy_score DESC
                LIMIT 20
            """
            )

            synergy_pairs = cursor.fetchall()

            # Build synergy graph
            synergy_graph = {}
            high_synergy_pairs = []

            for pair in synergy_pairs:
                source = pair["source_agent"]
                target = pair["target_agent"]
                score = pair["synergy_score"] or 0

                if source not in synergy_graph:
                    synergy_graph[source] = {}
                synergy_graph[source][target] = {
                    "synergy_score": score,
                    "success_rate": pair["success_rate"],
                    "avg_latency": pair["avg_latency"],
                    "interactions": pair["interaction_count"],
                }

                if score > 0.8:  # High synergy threshold
                    high_synergy_pairs.append(
                        {
                            "pair": f"{source} → {target}",
                            "score": score,
                            "success_rate": pair["success_rate"],
                        }
                    )

            # Detect collaboration triangles (3-agent synergies)
            triangles = self._detect_collaboration_triangles(synergy_graph)

            return {
                "high_synergy_pairs": high_synergy_pairs,
                "collaboration_triangles": triangles,
                "synergy_graph": synergy_graph,
                "optimal_workflows": self._suggest_optimal_workflows(synergy_graph),
            }

        finally:
            cursor.close()
            conn.close()

    def _detect_collaboration_triangles(self, synergy_graph: Dict) -> List[Dict]:
        """Detect 3-agent collaboration patterns"""
        triangles = []
        agents = list(synergy_graph.keys())

        for i, agent1 in enumerate(agents):
            for j, agent2 in enumerate(agents[i + 1 :], i + 1):
                for k, agent3 in enumerate(agents[j + 1 :], j + 1):
                    # Check if all three pairs have interactions
                    if (
                        agent2 in synergy_graph.get(agent1, {})
                        and agent3 in synergy_graph.get(agent2, {})
                        and (
                            agent3 in synergy_graph.get(agent1, {})
                            or agent1 in synergy_graph.get(agent3, {})
                        )
                    ):

                        # Calculate triangle synergy score
                        score = 0
                        pairs = [(agent1, agent2), (agent2, agent3), (agent1, agent3)]

                        for a, b in pairs:
                            if b in synergy_graph.get(a, {}):
                                score += synergy_graph[a][b]["synergy_score"]
                            elif a in synergy_graph.get(b, {}):
                                score += synergy_graph[b][a]["synergy_score"]

                        if score > 0:
                            triangles.append(
                                {
                                    "agents": [agent1, agent2, agent3],
                                    "triangle_score": score / 3,
                                    "pattern": f"{agent1} ↔ {agent2} ↔ {agent3}",
                                }
                            )

        return sorted(triangles, key=lambda x: x["triangle_score"], reverse=True)[:5]

    def _suggest_optimal_workflows(self, synergy_graph: Dict) -> List[Dict]:
        """Suggest optimal agent workflows based on synergy analysis"""
        workflows = []

        # Find chains of high-synergy interactions
        for source_agent in synergy_graph:
            chain = [source_agent]
            current = source_agent
            visited = {source_agent}

            for _ in range(5):  # Max chain length
                best_next = None
                best_score = 0

                for target, metrics in synergy_graph.get(current, {}).items():
                    if target not in visited and metrics["synergy_score"] > best_score:
                        best_next = target
                        best_score = metrics["synergy_score"]

                if best_next and best_score > 0.5:
                    chain.append(best_next)
                    visited.add(best_next)
                    current = best_next
                else:
                    break

            if len(chain) >= 3:
                workflows.append(
                    {
                        "workflow": " → ".join(chain),
                        "agents": chain,
                        "estimated_efficiency": self._calculate_workflow_efficiency(
                            chain, synergy_graph
                        ),
                    }
                )

        return sorted(workflows, key=lambda x: x["estimated_efficiency"], reverse=True)[
            :10
        ]

    def _calculate_workflow_efficiency(
        self, chain: List[str], synergy_graph: Dict
    ) -> float:
        """Calculate estimated efficiency of a workflow chain"""
        if len(chain) < 2:
            return 0

        total_score = 0
        for i in range(len(chain) - 1):
            source = chain[i]
            target = chain[i + 1]
            if target in synergy_graph.get(source, {}):
                total_score += synergy_graph[source][target]["synergy_score"]

        return total_score / (len(chain) - 1)

    async def predict_system_anomalies(self) -> Dict[str, Any]:
        """
        Predict system anomalies using multi-dimensional analysis
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Get recent system metrics for anomaly detection
            cursor.execute(
                """
                SELECT 
                    timestamp,
                    db_cpu_usage,
                    db_memory_usage_mb,
                    active_agents,
                    average_response_time_ms,
                    error_rate,
                    system_cpu_usage,
                    system_memory_usage_gb,
                    throughput_tasks_per_second
                FROM learning.system_health_metrics
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                ORDER BY timestamp DESC
            """
            )

            metrics = cursor.fetchall()

            if len(metrics) < 10:
                return {
                    "status": "insufficient_data",
                    "message": "Need at least 10 data points for anomaly detection",
                }

            # Prepare data for anomaly detection
            feature_columns = [
                "db_cpu_usage",
                "db_memory_usage_mb",
                "active_agents",
                "average_response_time_ms",
                "error_rate",
                "system_cpu_usage",
            ]

            X = np.array(
                [[row[col] or 0 for col in feature_columns] for row in metrics]
            )

            # Handle missing values
            X = np.nan_to_num(X, nan=0.0)

            # Standardize features
            X_scaled = self.scaler.fit_transform(X)

            # Detect anomalies
            self.anomaly_detector.fit(X_scaled[:-5])  # Train on all but last 5
            anomaly_scores = self.anomaly_detector.decision_function(
                X_scaled[-5:]
            )  # Test on last 5
            anomaly_predictions = self.anomaly_detector.predict(X_scaled[-5:])

            # Analyze anomalies
            anomalies = []
            for i, (score, pred) in enumerate(zip(anomaly_scores, anomaly_predictions)):
                if pred == -1:  # Anomaly detected
                    metric_idx = len(metrics) - 5 + i
                    anomalies.append(
                        {
                            "timestamp": metrics[metric_idx]["timestamp"].isoformat(),
                            "anomaly_score": float(score),
                            "severity": "high" if score < -0.5 else "medium",
                            "metrics": {
                                col: metrics[metric_idx][col] for col in feature_columns
                            },
                        }
                    )

            return {
                "anomalies_detected": len(anomalies),
                "anomalies": anomalies,
                "system_health_score": self._calculate_health_score(anomaly_scores),
                "recommendations": self._generate_anomaly_recommendations(anomalies),
            }

        finally:
            cursor.close()
            conn.close()

    def _calculate_health_score(self, anomaly_scores: np.ndarray) -> float:
        """Calculate overall system health score"""
        if len(anomaly_scores) == 0:
            return 100.0

        # Normalize scores to 0-100 scale
        min_score = -1.0  # Typical minimum for IsolationForest
        max_score = 0.5  # Typical maximum for normal points

        normalized = (anomaly_scores - min_score) / (max_score - min_score)
        health_score = np.mean(np.clip(normalized, 0, 1)) * 100

        return float(health_score)

    def _generate_anomaly_recommendations(self, anomalies: List[Dict]) -> List[str]:
        """Generate recommendations based on detected anomalies"""
        recommendations = []

        for anomaly in anomalies:
            metrics = anomaly["metrics"]

            if metrics.get("system_cpu_usage", 0) > 80:
                recommendations.append(
                    "🔥 High CPU usage detected - consider load balancing or scaling"
                )

            if metrics.get("error_rate", 0) > 0.05:
                recommendations.append(
                    "⚠️ Elevated error rate - investigate recent changes or system issues"
                )

            if metrics.get("average_response_time_ms", 0) > 5000:
                recommendations.append(
                    "🐌 High response times - optimize slow queries or increase resources"
                )

        return list(set(recommendations))  # Remove duplicates

    async def analyze_resource_optimization_opportunities(self) -> Dict[str, Any]:
        """
        Analyze resource usage patterns to identify optimization opportunities
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Analyze resource usage patterns
            cursor.execute(
                """
                WITH resource_analysis AS (
                    SELECT 
                        agent_name,
                        AVG(cpu_usage_percent) as avg_cpu,
                        AVG(memory_usage_mb) as avg_memory,
                        AVG(duration_ms) as avg_duration,
                        COUNT(*) as execution_count,
                        AVG(success_score) as avg_success,
                        STDDEV(cpu_usage_percent) as cpu_variance,
                        STDDEV(memory_usage_mb) as memory_variance
                    FROM learning.agent_metrics
                    WHERE execution_start >= NOW() - INTERVAL '7 days'
                    GROUP BY agent_name
                ),
                efficiency_scores AS (
                    SELECT 
                        *,
                        avg_success / NULLIF(avg_cpu * avg_memory / 1000, 0) as efficiency_score,
                        avg_duration / NULLIF(avg_cpu, 0) as cpu_efficiency,
                        avg_duration / NULLIF(avg_memory, 0) as memory_efficiency
                    FROM resource_analysis
                )
                SELECT * FROM efficiency_scores
                ORDER BY efficiency_score DESC
            """
            )

            resource_metrics = cursor.fetchall()

            # Identify optimization opportunities
            optimization_opportunities = []

            for agent_metrics in resource_metrics:
                agent = agent_metrics["agent_name"]

                # High CPU usage with low efficiency
                if (
                    agent_metrics["avg_cpu"] > 50
                    and agent_metrics["cpu_efficiency"] < 100
                ):
                    optimization_opportunities.append(
                        {
                            "agent": agent,
                            "type": "cpu_optimization",
                            "current_cpu": agent_metrics["avg_cpu"],
                            "potential_savings": "20-30%",
                            "recommendation": "Consider algorithm optimization or caching",
                        }
                    )

                # High memory usage with variance
                if (
                    agent_metrics["avg_memory"] > 1000
                    and agent_metrics["memory_variance"] > 500
                ):
                    optimization_opportunities.append(
                        {
                            "agent": agent,
                            "type": "memory_optimization",
                            "current_memory_mb": agent_metrics["avg_memory"],
                            "variance": agent_metrics["memory_variance"],
                            "recommendation": "Implement memory pooling or garbage collection tuning",
                        }
                    )

                # Low efficiency score
                if (
                    agent_metrics["efficiency_score"]
                    and agent_metrics["efficiency_score"] < 0.5
                ):
                    optimization_opportunities.append(
                        {
                            "agent": agent,
                            "type": "overall_efficiency",
                            "efficiency_score": agent_metrics["efficiency_score"],
                            "recommendation": "Complete refactoring recommended for better resource utilization",
                        }
                    )

            # P-core vs E-core recommendations for Intel Meteor Lake
            p_core_candidates = [
                m["agent_name"]
                for m in resource_metrics
                if m["avg_cpu"] > 70 and m["avg_duration"] < 1000
            ]

            e_core_candidates = [
                m["agent_name"]
                for m in resource_metrics
                if m["avg_cpu"] < 30 and m["avg_duration"] > 5000
            ]

            return {
                "optimization_opportunities": optimization_opportunities,
                "p_core_recommendations": p_core_candidates,
                "e_core_recommendations": e_core_candidates,
                "overall_efficiency": self._calculate_overall_efficiency(
                    resource_metrics
                ),
                "resource_allocation_strategy": self._generate_allocation_strategy(
                    resource_metrics
                ),
            }

        finally:
            cursor.close()
            conn.close()

    def _calculate_overall_efficiency(self, metrics: List[Dict]) -> float:
        """Calculate overall system efficiency"""
        if not metrics:
            return 0.0

        total_efficiency = sum(
            m["efficiency_score"] for m in metrics if m["efficiency_score"] is not None
        )

        count = sum(1 for m in metrics if m["efficiency_score"] is not None)

        return total_efficiency / count if count > 0 else 0.0

    def _generate_allocation_strategy(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Generate resource allocation strategy"""
        strategy = {
            "high_priority_agents": [],
            "parallel_execution_groups": [],
            "resource_pools": {},
        }

        # Identify high-priority agents
        for m in metrics:
            if (
                m["avg_success"]
                and m["avg_success"] > 0.9
                and m["execution_count"] > 100
            ):
                strategy["high_priority_agents"].append(
                    {
                        "agent": m["agent_name"],
                        "priority_score": m["avg_success"] * m["execution_count"] / 100,
                    }
                )

        # Group agents that can run in parallel (low resource usage)
        low_resource_agents = [
            m["agent_name"]
            for m in metrics
            if m["avg_cpu"]
            and m["avg_cpu"] < 20
            and m["avg_memory"]
            and m["avg_memory"] < 500
        ]

        if len(low_resource_agents) >= 3:
            strategy["parallel_execution_groups"].append(
                {
                    "group_name": "low_resource_parallel",
                    "agents": low_resource_agents[:5],
                    "max_parallel": 3,
                }
            )

        return strategy

    async def generate_comprehensive_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive learning analytics report
        """
        logger.info("Generating comprehensive learning analytics report...")

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "analysis_period": "7 days",
            "sections": {},
        }

        try:
            # Performance Trajectories
            report["sections"][
                "performance_trajectories"
            ] = await self.analyze_performance_trajectories()

            # Agent Synergies
            report["sections"]["agent_synergies"] = await self.detect_agent_synergies()

            # Anomaly Detection
            report["sections"][
                "anomaly_detection"
            ] = await self.predict_system_anomalies()

            # Resource Optimization
            report["sections"][
                "resource_optimization"
            ] = await self.analyze_resource_optimization_opportunities()

            # Executive Summary
            report["executive_summary"] = self._generate_executive_summary(
                report["sections"]
            )

            logger.info("Comprehensive report generated successfully")

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            report["error"] = str(e)

        return report

    def _generate_executive_summary(self, sections: Dict) -> Dict[str, Any]:
        """Generate executive summary of the analytics report"""
        summary = {"key_findings": [], "critical_actions": [], "opportunities": []}

        # Extract key findings
        if "performance_trajectories" in sections:
            trends = sections["performance_trajectories"].get("agent_trends", {})
            improving = sum(
                1
                for t in trends.values()
                if t.get("trend_direction") == PerformanceTrend.IMPROVING
            )
            degrading = sum(
                1
                for t in trends.values()
                if t.get("trend_direction") == PerformanceTrend.DEGRADING
            )

            if improving > 0:
                summary["key_findings"].append(
                    f"✅ {improving} agents showing performance improvements"
                )
            if degrading > 0:
                summary["critical_actions"].append(
                    f"⚠️ {degrading} agents need attention - performance degrading"
                )

        # Extract synergy opportunities
        if "agent_synergies" in sections:
            high_synergy = sections["agent_synergies"].get("high_synergy_pairs", [])
            if high_synergy:
                summary["opportunities"].append(
                    f"🤝 {len(high_synergy)} high-synergy agent pairs identified for workflow optimization"
                )

        # Extract anomalies
        if "anomaly_detection" in sections:
            anomalies = sections["anomaly_detection"].get("anomalies_detected", 0)
            if anomalies > 0:
                summary["critical_actions"].append(
                    f"🔍 {anomalies} system anomalies detected requiring investigation"
                )

        # Extract optimization opportunities
        if "resource_optimization" in sections:
            opportunities = sections["resource_optimization"].get(
                "optimization_opportunities", []
            )
            if opportunities:
                summary["opportunities"].append(
                    f"💡 {len(opportunities)} resource optimization opportunities identified"
                )

        return summary


async def main():
    """Test the advanced analytics engine"""
    analytics = AdvancedLearningAnalytics()

    print("🔬 Advanced Learning Analytics Test")
    print("=" * 50)

    # Generate comprehensive report
    report = await analytics.generate_comprehensive_report()

    # Print executive summary
    if "executive_summary" in report:
        print("\n📊 EXECUTIVE SUMMARY")
        print("-" * 30)
        summary = report["executive_summary"]

        print("\n🔍 Key Findings:")
        for finding in summary.get("key_findings", []):
            print(f"  {finding}")

        print("\n⚠️ Critical Actions:")
        for action in summary.get("critical_actions", []):
            print(f"  {action}")

        print("\n💡 Opportunities:")
        for opportunity in summary.get("opportunities", []):
            print(f"  {opportunity}")

    # Save full report
    with open(
        '${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}learning_analytics_report.json',
        "w",
    ) as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n✅ Full report saved to learning_analytics_report.json")
    print(f"📅 Generated at: {report['generated_at']}")


if __name__ == "__main__":
    asyncio.run(main())
