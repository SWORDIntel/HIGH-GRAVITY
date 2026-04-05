#!/usr/bin/env python3
"""
Capacity Planning and Performance Analysis for Claude Agent Communication System
Provides predictive analytics and capacity recommendations
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import aiohttp
import numpy as np
import pandas as pd
from prometheus_client import Gauge
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CapacityMetrics:
    """Container for capacity planning metrics"""

    __slots__ = []
    timestamp: datetime
    message_throughput: float
    cpu_utilization: float
    memory_utilization: float
    network_utilization: float
    agent_count: int
    queue_depth: float
    error_rate: float
    latency_p99: float


@dataclass
class CapacityForecast:
    """Capacity planning forecast"""

    __slots__ = []
    metric_name: str
    current_value: float
    predicted_value: float
    confidence_interval: Tuple[float, float]
    time_horizon: str
    recommendation: str
    risk_level: str


@dataclass
class ScalingRecommendation:
    """Scaling recommendation for the system"""

    __slots__ = []
    component: str
    action: str  # scale_up, scale_down, maintain
    target_capacity: int
    current_capacity: int
    justification: str
    priority: str  # critical, high, medium, low
    timeline: str


class CapacityPlanner:
    """Main capacity planning and analysis engine"""

    __slots__ = []

    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url
        self.historical_data = []
        self.models = {}

        # Capacity planning metrics
        self.capacity_forecast = Gauge(
            "capacity_forecast_value",
            "Forecasted capacity values",
            ["metric", "horizon"],
        )

        self.scaling_recommendation = Gauge(
            "scaling_recommendation_priority",
            "Scaling recommendation priority (0-3)",
            ["component", "action"],
        )

        self.resource_efficiency = Gauge(
            "resource_efficiency_ratio", "Resource efficiency ratio", ["resource_type"]
        )

        self.bottleneck_prediction = Gauge(
            "bottleneck_prediction_score",
            "Predicted bottleneck score (0-100)",
            ["bottleneck_type"],
        )

    async def collect_historical_data(
        self, lookback_hours: int = 168
    ) -> List[CapacityMetrics]:
        """Collect historical metrics for analysis"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=lookback_hours)

        queries = {
            "message_throughput": "transport:message_rate_5m",
            "cpu_utilization": "system:cpu_utilization_avg",
            "memory_utilization": "system:memory_utilization_avg",
            "network_utilization": "system:network_utilization_avg",
            "agent_count": "system:total_active_agents",
            "queue_depth": "avg(agent:queue_depth_avg_5m)",
            "error_rate": "transport:error_rate_5m",
            "latency_p99": "transport:latency_p99_5m",
        }

        historical_data = []

        async with aiohttp.ClientSession() as session:
            for metric_name, query in queries.items():
                url = f"{self.prometheus_url}/api/v1/query_range"
                params = {
                    "query": query,
                    "start": start_time.timestamp(),
                    "end": end_time.timestamp(),
                    "step": "300s",  # 5 minute intervals
                }

                try:
                    async with session.get(url, params=params) as response:
                        data = await response.json()

                        if data["status"] == "success" and data["data"]["result"]:
                            result = data["data"]["result"][0]
                            values = result["values"]

                            for timestamp, value in values:
                                dt = datetime.fromtimestamp(timestamp)

                                # Find or create metrics entry for this timestamp
                                existing_metric = None
                                for m in historical_data:
                                    if (
                                        abs((m.timestamp - dt).total_seconds()) < 150
                                    ):  # Within 2.5 minutes
                                        existing_metric = m
                                        break

                                if not existing_metric:
                                    existing_metric = CapacityMetrics(
                                        timestamp=dt,
                                        message_throughput=0,
                                        cpu_utilization=0,
                                        memory_utilization=0,
                                        network_utilization=0,
                                        agent_count=0,
                                        queue_depth=0,
                                        error_rate=0,
                                        latency_p99=0,
                                    )
                                    historical_data.append(existing_metric)

                                # Update the metric value
                                setattr(existing_metric, metric_name, float(value))

                except Exception as e:
                    logger.error(f"Error fetching {metric_name}: {e}")

        # Sort by timestamp and filter out incomplete records
        historical_data.sort(key=lambda x: x.timestamp)
        complete_data = [m for m in historical_data if m.message_throughput > 0]

        logger.info(f"Collected {len(complete_data)} complete historical data points")
        self.historical_data = complete_data
        return complete_data

    def train_forecasting_models(self):
        """Train machine learning models for capacity forecasting"""
        if len(self.historical_data) < 50:
            logger.warning("Insufficient historical data for model training")
            return

        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(
            [
                {
                    "timestamp": m.timestamp.timestamp(),
                    "message_throughput": m.message_throughput,
                    "cpu_utilization": m.cpu_utilization,
                    "memory_utilization": m.memory_utilization,
                    "network_utilization": m.network_utilization,
                    "agent_count": m.agent_count,
                    "queue_depth": m.queue_depth,
                    "error_rate": m.error_rate,
                    "latency_p99": m.latency_p99,
                }
                for m in self.historical_data
            ]
        )

        # Create time-based features
        df["hour"] = pd.to_datetime(df["timestamp"], unit="s").dt.hour
        df["day_of_week"] = pd.to_datetime(df["timestamp"], unit="s").dt.dayofweek
        df["time_since_start"] = (
            df["timestamp"] - df["timestamp"].min()
        ) / 3600  # Hours

        # Define target metrics for forecasting
        target_metrics = [
            "message_throughput",
            "cpu_utilization",
            "memory_utilization",
            "network_utilization",
            "agent_count",
            "queue_depth",
            "error_rate",
            "latency_p99",
        ]

        feature_columns = ["hour", "day_of_week", "time_since_start"]

        for metric in target_metrics:
            if df[metric].std() == 0:  # Skip constant metrics
                continue

            # Prepare features and target
            X = df[feature_columns].values
            y = df[metric].values

            # Split into train/test
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # Train models
            models = {
                "linear": LinearRegression(),
                "random_forest": RandomForestRegressor(
                    n_estimators=100, random_state=42
                ),
            }

            best_model = None
            best_score = float("inf")

            for name, model in models.items():
                try:
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)
                    mse = mean_squared_error(y_test, y_pred)

                    if mse < best_score:
                        best_score = mse
                        best_model = model

                except Exception as e:
                    logger.error(f"Error training {name} model for {metric}: {e}")

            if best_model:
                self.models[metric] = {
                    "model": best_model,
                    "feature_columns": feature_columns,
                    "mse": best_score,
                }
                logger.info(f"Trained model for {metric} with MSE: {best_score:.4f}")

    def generate_capacity_forecasts(
        self, horizons: List[str] = None
    ) -> List[CapacityForecast]:
        """Generate capacity forecasts for different time horizons"""
        if not horizons:
            horizons = ["1h", "6h", "1d", "1w"]

        forecasts = []
        current_time = datetime.now()

        for horizon in horizons:
            # Parse horizon
            if horizon.endswith("h"):
                hours = int(horizon[:-1])
            elif horizon.endswith("d"):
                hours = int(horizon[:-1]) * 24
            elif horizon.endswith("w"):
                hours = int(horizon[:-1]) * 24 * 7
            else:
                continue

            future_time = current_time + timedelta(hours=hours)

            # Create features for future prediction
            future_features = np.array(
                [[future_time.hour, future_time.weekday(), hours]]  # Time since current
            )

            for metric_name, model_info in self.models.items():
                try:
                    model = model_info["model"]
                    predicted_value = model.predict(future_features)[0]

                    # Get current value for comparison
                    current_value = (
                        getattr(self.historical_data[-1], metric_name)
                        if self.historical_data
                        else 0
                    )

                    # Calculate confidence interval (simplified)
                    mse = model_info["mse"]
                    confidence_range = 1.96 * np.sqrt(mse)  # 95% confidence
                    confidence_interval = (
                        max(0, predicted_value - confidence_range),
                        predicted_value + confidence_range,
                    )

                    # Generate recommendation
                    recommendation = self._generate_recommendation(
                        metric_name, current_value, predicted_value, horizon
                    )

                    # Determine risk level
                    risk_level = self._assess_risk_level(
                        metric_name, current_value, predicted_value
                    )

                    forecast = CapacityForecast(
                        metric_name=metric_name,
                        current_value=current_value,
                        predicted_value=predicted_value,
                        confidence_interval=confidence_interval,
                        time_horizon=horizon,
                        recommendation=recommendation,
                        risk_level=risk_level,
                    )

                    forecasts.append(forecast)

                    # Update metrics
                    self.capacity_forecast.labels(
                        metric=metric_name, horizon=horizon
                    ).set(predicted_value)

                except Exception as e:
                    logger.error(f"Error generating forecast for {metric_name}: {e}")

        return forecasts

    def generate_scaling_recommendations(self) -> List[ScalingRecommendation]:
        """Generate scaling recommendations based on forecasts and current state"""
        recommendations = []

        if not self.historical_data:
            return recommendations

        current_metrics = self.historical_data[-1]

        # CPU-based recommendations
        if current_metrics.cpu_utilization > 80:
            recommendations.append(
                ScalingRecommendation(
                    component="compute_nodes",
                    action="scale_up",
                    target_capacity=int(current_metrics.agent_count * 1.5),
                    current_capacity=current_metrics.agent_count,
                    justification=f"CPU utilization at {current_metrics.cpu_utilization:.1f}%",
                    priority="high",
                    timeline="immediate",
                )
            )
        elif current_metrics.cpu_utilization < 30 and current_metrics.agent_count > 10:
            recommendations.append(
                ScalingRecommendation(
                    component="compute_nodes",
                    action="scale_down",
                    target_capacity=int(current_metrics.agent_count * 0.8),
                    current_capacity=current_metrics.agent_count,
                    justification=f"CPU utilization at {current_metrics.cpu_utilization:.1f}%",
                    priority="medium",
                    timeline="1-2 hours",
                )
            )

        # Memory-based recommendations
        if current_metrics.memory_utilization > 85:
            recommendations.append(
                ScalingRecommendation(
                    component="memory_allocation",
                    action="scale_up",
                    target_capacity=int(current_metrics.agent_count * 1.3),
                    current_capacity=current_metrics.agent_count,
                    justification=f"Memory utilization at {current_metrics.memory_utilization:.1f}%",
                    priority="critical",
                    timeline="immediate",
                )
            )

        # Queue depth recommendations
        if current_metrics.queue_depth > 100:
            recommendations.append(
                ScalingRecommendation(
                    component="message_processors",
                    action="scale_up",
                    target_capacity=int(current_metrics.agent_count * 1.4),
                    current_capacity=current_metrics.agent_count,
                    justification=f"Average queue depth at {current_metrics.queue_depth:.1f} messages",
                    priority="high",
                    timeline="15-30 minutes",
                )
            )

        # Throughput-based recommendations
        if current_metrics.message_throughput < 3000000:  # Below 3M msg/s
            recommendations.append(
                ScalingRecommendation(
                    component="transport_layer",
                    action="scale_up",
                    target_capacity=int(current_metrics.agent_count * 1.2),
                    current_capacity=current_metrics.agent_count,
                    justification=f"Throughput at {current_metrics.message_throughput:.0f} msg/s, below target",
                    priority="medium",
                    timeline="30-60 minutes",
                )
            )

        # Update metrics
        for rec in recommendations:
            priority_value = {"critical": 3, "high": 2, "medium": 1, "low": 0}.get(
                rec.priority, 0
            )
            self.scaling_recommendation.labels(
                component=rec.component, action=rec.action
            ).set(priority_value)

        return recommendations

    def analyze_resource_efficiency(self) -> Dict[str, float]:
        """Analyze resource efficiency and utilization patterns"""
        if not self.historical_data:
            return {}

        recent_data = self.historical_data[-20:]  # Last 20 data points

        # Calculate efficiency metrics
        efficiency_metrics = {}

        # Throughput per CPU unit
        avg_cpu = np.mean(
            [m.cpu_utilization for m in recent_data if m.cpu_utilization > 0]
        )
        avg_throughput = np.mean([m.message_throughput for m in recent_data])

        if avg_cpu > 0:
            efficiency_metrics["throughput_per_cpu"] = avg_throughput / avg_cpu
            self.resource_efficiency.labels(resource_type="cpu").set(
                avg_throughput / avg_cpu / 1000
            )

        # Messages per agent
        avg_agents = np.mean([m.agent_count for m in recent_data if m.agent_count > 0])
        if avg_agents > 0:
            efficiency_metrics["messages_per_agent"] = avg_throughput / avg_agents
            self.resource_efficiency.labels(resource_type="agents").set(
                avg_throughput / avg_agents / 1000
            )

        # Memory efficiency
        avg_memory = np.mean(
            [m.memory_utilization for m in recent_data if m.memory_utilization > 0]
        )
        if avg_memory > 0:
            efficiency_metrics["throughput_per_memory"] = avg_throughput / avg_memory
            self.resource_efficiency.labels(resource_type="memory").set(
                avg_throughput / avg_memory / 1000
            )

        # Network efficiency
        avg_network = np.mean(
            [m.network_utilization for m in recent_data if m.network_utilization > 0]
        )
        if avg_network > 0:
            efficiency_metrics["throughput_per_network"] = avg_throughput / avg_network
            self.resource_efficiency.labels(resource_type="network").set(
                avg_throughput / avg_network / 1000
            )

        return efficiency_metrics

    def predict_bottlenecks(self) -> Dict[str, float]:
        """Predict potential system bottlenecks"""
        if len(self.historical_data) < 10:
            return {}

        recent_data = self.historical_data[-10:]
        bottleneck_scores = {}

        # CPU bottleneck prediction
        cpu_trend = np.polyfit(
            range(len(recent_data)), [m.cpu_utilization for m in recent_data], 1
        )[0]
        cpu_current = recent_data[-1].cpu_utilization
        cpu_bottleneck_score = min(100, max(0, (cpu_current + cpu_trend * 10) - 70))
        bottleneck_scores["cpu"] = cpu_bottleneck_score

        # Memory bottleneck prediction
        memory_trend = np.polyfit(
            range(len(recent_data)), [m.memory_utilization for m in recent_data], 1
        )[0]
        memory_current = recent_data[-1].memory_utilization
        memory_bottleneck_score = min(
            100, max(0, (memory_current + memory_trend * 10) - 80)
        )
        bottleneck_scores["memory"] = memory_bottleneck_score

        # Queue bottleneck prediction
        queue_trend = np.polyfit(
            range(len(recent_data)), [m.queue_depth for m in recent_data], 1
        )[0]
        queue_current = recent_data[-1].queue_depth
        queue_bottleneck_score = min(
            100, max(0, (queue_current + queue_trend * 5) - 50)
        )
        bottleneck_scores["queue"] = queue_bottleneck_score

        # Network bottleneck prediction
        network_trend = np.polyfit(
            range(len(recent_data)), [m.network_utilization for m in recent_data], 1
        )[0]
        network_current = recent_data[-1].network_utilization
        network_bottleneck_score = min(
            100, max(0, (network_current + network_trend * 10) - 70)
        )
        bottleneck_scores["network"] = network_bottleneck_score

        # Update metrics
        for bottleneck_type, score in bottleneck_scores.items():
            self.bottleneck_prediction.labels(bottleneck_type=bottleneck_type).set(
                score
            )

        return bottleneck_scores

    def _generate_recommendation(
        self, metric_name: str, current: float, predicted: float, horizon: str
    ) -> str:
        """Generate human-readable recommendation"""
        change_pct = ((predicted - current) / current * 100) if current > 0 else 0

        if metric_name == "cpu_utilization":
            if predicted > 90:
                return f"Critical: CPU will reach {predicted:.1f}% in {horizon}. Scale up immediately."
            elif predicted > 80:
                return f"Warning: CPU will reach {predicted:.1f}% in {horizon}. Prepare to scale up."
            elif change_pct > 50:
                return (
                    f"Monitor: CPU usage increasing rapidly ({change_pct:.1f}% growth)."
                )
            else:
                return f"Normal: CPU usage stable at {predicted:.1f}%."

        elif metric_name == "memory_utilization":
            if predicted > 95:
                return f"Critical: Memory will reach {predicted:.1f}% in {horizon}. Scale up immediately."
            elif predicted > 85:
                return f"Warning: Memory will reach {predicted:.1f}% in {horizon}. Prepare to scale up."
            else:
                return f"Normal: Memory usage at {predicted:.1f}%."

        elif metric_name == "message_throughput":
            if predicted < 3000000:
                return f"Warning: Throughput dropping to {predicted:.0f} msg/s. Investigate performance issues."
            elif change_pct > 100:
                return (
                    f"Monitor: Throughput increasing rapidly. Ensure adequate capacity."
                )
            else:
                return f"Normal: Throughput at {predicted:.0f} msg/s."

        else:
            if abs(change_pct) > 50:
                return f"Monitor: {metric_name} changing by {change_pct:.1f}% in {horizon}."
            else:
                return f"Normal: {metric_name} stable."

    def _assess_risk_level(
        self, metric_name: str, current: float, predicted: float
    ) -> str:
        """Assess risk level for a metric prediction"""
        change_pct = abs((predicted - current) / current * 100) if current > 0 else 0

        if metric_name in ["cpu_utilization", "memory_utilization"]:
            if predicted > 95:
                return "critical"
            elif predicted > 85:
                return "high"
            elif predicted > 70:
                return "medium"
            else:
                return "low"

        elif metric_name == "error_rate":
            if predicted > 0.01:  # > 1%
                return "critical"
            elif predicted > 0.005:  # > 0.5%
                return "high"
            elif predicted > 0.001:  # > 0.1%
                return "medium"
            else:
                return "low"

        else:
            if change_pct > 100:
                return "high"
            elif change_pct > 50:
                return "medium"
            else:
                return "low"


# Main capacity planning loop
async def main():
    """Main capacity planning application"""
    logger.info("Starting Claude Agent Capacity Planning System")

    planner = CapacityPlanner()

    while True:
        try:
            # Collect historical data
            logger.info("Collecting historical data...")
            await planner.collect_historical_data()

            # Train forecasting models
            logger.info("Training forecasting models...")
            planner.train_forecasting_models()

            # Generate forecasts
            logger.info("Generating capacity forecasts...")
            forecasts = planner.generate_capacity_forecasts()

            # Generate scaling recommendations
            logger.info("Generating scaling recommendations...")
            recommendations = planner.generate_scaling_recommendations()

            # Analyze efficiency
            logger.info("Analyzing resource efficiency...")
            efficiency = planner.analyze_resource_efficiency()

            # Predict bottlenecks
            logger.info("Predicting bottlenecks...")
            bottlenecks = planner.predict_bottlenecks()

            # Print summary
            print("\n" + "=" * 80)
            print("CLAUDE AGENT SYSTEM CAPACITY PLANNING REPORT")
            print("=" * 80)

            if recommendations:
                print(f"\nSCALING RECOMMENDATIONS ({len(recommendations)}):")
                for rec in recommendations:
                    print(f"  [{rec.priority.upper()}] {rec.component}: {rec.action}")
                    print(
                        f"    Current: {rec.current_capacity}, Target: {rec.target_capacity}"
                    )
                    print(f"    Reason: {rec.justification}")
                    print(f"    Timeline: {rec.timeline}")
                    print()

            if bottlenecks:
                print("BOTTLENECK PREDICTIONS:")
                for bottleneck, score in bottlenecks.items():
                    risk = "HIGH" if score > 70 else "MEDIUM" if score > 40 else "LOW"
                    print(f"  {bottleneck.upper()}: {score:.1f}% risk [{risk}]")

            if efficiency:
                print("\nRESOURCE EFFICIENCY:")
                for metric, value in efficiency.items():
                    print(f"  {metric}: {value:.2f}")

            print("\n" + "=" * 80)

            # Wait before next analysis
            await asyncio.sleep(300)  # 5 minutes

        except Exception as e:
            logger.error(f"Error in capacity planning loop: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
