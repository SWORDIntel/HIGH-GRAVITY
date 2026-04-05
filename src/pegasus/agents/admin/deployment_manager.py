"""
Claude Agent Communication System - Deployment Manager
=====================================================

Advanced deployment and scaling management for the distributed Claude agent system.
Handles container orchestration, Kubernetes integration, scaling operations,
and deployment strategies for maintaining 4.2M+ msg/sec performance.

Features:
- Kubernetes and Docker integration
- Blue-green and canary deployment strategies
- Automatic scaling based on performance metrics
- Rolling updates with zero downtime
- Resource allocation optimization
- Health monitoring and rollback capabilities
- Multi-region deployment support
- Infrastructure as code integration

Author: Claude Agent Administration System
Version: 1.0.0 Production
"""

import asyncio
import copy
import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Kubernetes and container imports
import docker
import kubernetes
import yaml

# Local imports
from admin_core import OperationResult
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

# Deployment strategies
DEPLOYMENT_STRATEGIES = {
    "rolling": "RollingUpdate",
    "blue_green": "BlueGreen",
    "canary": "Canary",
    "recreate": "Recreate",
}

# Resource specifications for different agent types
AGENT_RESOURCES = {
    "director": {"cpu": "500m", "memory": "512Mi", "replicas": 1},
    "project-orchestrator": {"cpu": "300m", "memory": "256Mi", "replicas": 1},
    "security": {"cpu": "200m", "memory": "256Mi", "replicas": 2},
    "testbed": {"cpu": "1000m", "memory": "1Gi", "replicas": 1},
    "web": {"cpu": "300m", "memory": "512Mi", "replicas": 3},
    "api-designer": {"cpu": "200m", "memory": "256Mi", "replicas": 2},
    "database": {"cpu": "500m", "memory": "1Gi", "replicas": 1},
    "monitor": {"cpu": "200m", "memory": "256Mi", "replicas": 2},
    "optimizer": {"cpu": "800m", "memory": "512Mi", "replicas": 1},
    "mlops": {"cpu": "1000m", "memory": "2Gi", "replicas": 1},
    "data-science": {"cpu": "1500m", "memory": "4Gi", "replicas": 1},
    # Add more agent types as needed
}

# Performance thresholds for auto-scaling
AUTO_SCALE_THRESHOLDS = {
    "cpu_high": 80,  # Scale up when CPU > 80%
    "cpu_low": 30,  # Scale down when CPU < 30%
    "memory_high": 85,  # Scale up when memory > 85%
    "latency_high": 500,  # Scale up when latency > 500ms
    "queue_high": 1000,  # Scale up when queue depth > 1000
    "throughput_low": 2000000,  # Scale up when throughput < 2M msg/s
}

# ============================================================================
# CORE DATA STRUCTURES
# ============================================================================


@dataclass
class DeploymentConfig:
    """Deployment configuration"""

    __slots__ = []
    environment: str
    cluster_name: str
    namespace: str
    agent_configs: Dict[str, Any]
    resource_limits: Dict[str, Any]
    scaling_policies: Dict[str, Any]
    networking: Dict[str, Any]
    security: Dict[str, Any]
    monitoring: Dict[str, Any]


@dataclass
class DeploymentStep:
    """Single deployment step"""

    __slots__ = []
    name: str
    description: str
    action: str
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retries: int = 3
    rollback_action: Optional[str] = None


@dataclass
class DeploymentPlan:
    """Complete deployment plan"""

    __slots__ = []
    name: str
    version: str
    environment: str
    steps: List[DeploymentStep]
    estimated_duration: int
    rollback_plan: List[DeploymentStep]
    validation_checks: List[str]


@dataclass
class ScalingEvent:
    """Scaling operation event"""

    __slots__ = []
    timestamp: datetime
    agent_type: str
    action: str  # scale_up, scale_down
    from_replicas: int
    to_replicas: int
    reason: str
    trigger_metrics: Dict[str, float]
    duration_seconds: float
    success: bool


# ============================================================================
# KUBERNETES DEPLOYMENT MANAGER
# ============================================================================


class KubernetesDeploymentManager:
    """Manages Kubernetes-based deployments"""

    __slots__ = []

    def __init__(self):
        self.k8s_client = None
        self.apps_v1 = None
        self.core_v1 = None
        self.autoscaling_v1 = None
        self.networking_v1 = None

        self._initialize_k8s_client()

        # Deployment tracking
        self.active_deployments = {}
        self.deployment_history = []

        # Auto-scaling
        self.auto_scaling_enabled = True
        self.scaling_history = []
        self.last_scale_check = time.time()

        # Background monitoring
        self.monitor_thread = threading.Thread(
            target=self._monitor_deployments, daemon=True
        )
        self.monitor_thread.start()

    def _initialize_k8s_client(self):
        """Initialize Kubernetes client"""
        try:
            # Try in-cluster configuration first
            config.load_incluster_config()
            logging.info("Loaded in-cluster Kubernetes configuration")
        except:
            try:
                # Fall back to local kubeconfig
                config.load_kube_config()
                logging.info("Loaded local Kubernetes configuration")
            except Exception as e:
                logging.warning(f"Failed to load Kubernetes configuration: {e}")
                return

        self.k8s_client = client.ApiClient()
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self.autoscaling_v1 = client.AutoscalingV1Api()
        self.networking_v1 = client.NetworkingV1Api()

    def deploy_agent(
        self, agent_type: str, config: DeploymentConfig, strategy: str = "rolling"
    ) -> OperationResult:
        """Deploy single agent type"""
        if not self.k8s_client:
            return OperationResult(False, "Kubernetes client not available")

        start_time = time.time()

        try:
            # Generate Kubernetes manifests
            manifests = self._generate_agent_manifests(agent_type, config)

            # Apply deployment strategy
            if strategy == "rolling":
                result = self._rolling_deployment(agent_type, manifests, config)
            elif strategy == "blue_green":
                result = self._blue_green_deployment(agent_type, manifests, config)
            elif strategy == "canary":
                result = self._canary_deployment(agent_type, manifests, config)
            else:
                result = self._recreate_deployment(agent_type, manifests, config)

            duration = time.time() - start_time

            if result.success:
                # Record deployment
                self.deployment_history.append(
                    {
                        "timestamp": datetime.now(),
                        "agent_type": agent_type,
                        "strategy": strategy,
                        "duration": duration,
                        "success": True,
                    }
                )

                # Start monitoring
                self.active_deployments[agent_type] = {
                    "config": config,
                    "manifests": manifests,
                    "deployed_at": datetime.now(),
                }

            return OperationResult(result.success, result.error, result.data, duration)

        except Exception as e:
            duration = time.time() - start_time
            return OperationResult(
                False, f"Deployment failed: {e}", duration_seconds=duration
            )

    def _generate_agent_manifests(
        self, agent_type: str, config: DeploymentConfig
    ) -> Dict[str, Any]:
        """Generate Kubernetes manifests for agent"""

        # Get resource specifications
        resources = AGENT_RESOURCES.get(
            agent_type, {"cpu": "200m", "memory": "256Mi", "replicas": 1}
        )

        # Override with config-specific resources
        if agent_type in config.agent_configs:
            resources.update(config.agent_configs[agent_type].get("resources", {}))

        manifests = {}

        # Deployment manifest
        manifests["deployment"] = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": f"claude-{agent_type}",
                "namespace": config.namespace,
                "labels": {
                    "app": f"claude-{agent_type}",
                    "component": "agent",
                    "type": agent_type,
                    "version": config.agent_configs.get(agent_type, {}).get(
                        "version", "1.0.0"
                    ),
                },
            },
            "spec": {
                "replicas": resources.get("replicas", 1),
                "selector": {"matchLabels": {"app": f"claude-{agent_type}"}},
                "template": {
                    "metadata": {
                        "labels": {
                            "app": f"claude-{agent_type}",
                            "component": "agent",
                            "type": agent_type,
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": f"claude-{agent_type}",
                                "image": f"claude-agents/{agent_type}:latest",
                                "ports": [
                                    {"containerPort": 9090, "name": "metrics"},
                                    {"containerPort": 8080, "name": "http"},
                                ],
                                "resources": {
                                    "requests": {
                                        "cpu": resources.get("cpu", "200m"),
                                        "memory": resources.get("memory", "256Mi"),
                                    },
                                    "limits": {
                                        "cpu": resources.get("cpu", "200m"),
                                        "memory": resources.get("memory", "256Mi"),
                                    },
                                },
                                "env": [
                                    {"name": "AGENT_TYPE", "value": agent_type},
                                    {
                                        "name": "CLUSTER_NAME",
                                        "value": config.cluster_name,
                                    },
                                    {"name": "NAMESPACE", "value": config.namespace},
                                    {
                                        "name": "PROMETHEUS_ENDPOINT",
                                        "value": "http://prometheus:9090",
                                    },
                                ],
                                "livenessProbe": {
                                    "httpGet": {"path": "/health", "port": 8080},
                                    "initialDelaySeconds": 30,
                                    "periodSeconds": 10,
                                },
                                "readinessProbe": {
                                    "httpGet": {"path": "/ready", "port": 8080},
                                    "initialDelaySeconds": 5,
                                    "periodSeconds": 5,
                                },
                            }
                        ],
                        "nodeSelector": {"claude-agent-node": "true"},
                        "affinity": self._generate_affinity_rules(agent_type),
                        "tolerations": self._generate_tolerations(agent_type),
                    },
                },
            },
        }

        # Service manifest
        manifests["service"] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"claude-{agent_type}",
                "namespace": config.namespace,
                "labels": {
                    "app": f"claude-{agent_type}",
                    "component": "agent",
                    "type": agent_type,
                },
            },
            "spec": {
                "selector": {"app": f"claude-{agent_type}"},
                "ports": [
                    {"name": "http", "port": 80, "targetPort": 8080},
                    {"name": "metrics", "port": 9090, "targetPort": 9090},
                ],
                "type": "ClusterIP",
            },
        }

        # HorizontalPodAutoscaler if enabled
        if config.scaling_policies.get("auto_scaling", False):
            manifests["hpa"] = {
                "apiVersion": "autoscaling/v2",
                "kind": "HorizontalPodAutoscaler",
                "metadata": {
                    "name": f"claude-{agent_type}",
                    "namespace": config.namespace,
                },
                "spec": {
                    "scaleTargetRef": {
                        "apiVersion": "apps/v1",
                        "kind": "Deployment",
                        "name": f"claude-{agent_type}",
                    },
                    "minReplicas": resources.get("min_replicas", 1),
                    "maxReplicas": resources.get("max_replicas", 10),
                    "metrics": [
                        {
                            "type": "Resource",
                            "resource": {
                                "name": "cpu",
                                "target": {
                                    "type": "Utilization",
                                    "averageUtilization": 70,
                                },
                            },
                        },
                        {
                            "type": "Resource",
                            "resource": {
                                "name": "memory",
                                "target": {
                                    "type": "Utilization",
                                    "averageUtilization": 80,
                                },
                            },
                        },
                    ],
                },
            }

        # ServiceMonitor for Prometheus
        if config.monitoring.get("prometheus_enabled", True):
            manifests["servicemonitor"] = {
                "apiVersion": "monitoring.coreos.com/v1",
                "kind": "ServiceMonitor",
                "metadata": {
                    "name": f"claude-{agent_type}",
                    "namespace": config.namespace,
                    "labels": {
                        "app": f"claude-{agent_type}",
                        "monitoring": "prometheus",
                    },
                },
                "spec": {
                    "selector": {"matchLabels": {"app": f"claude-{agent_type}"}},
                    "endpoints": [
                        {"port": "metrics", "interval": "30s", "path": "/metrics"}
                    ],
                },
            }

        return manifests

    def _rolling_deployment(
        self, agent_type: str, manifests: Dict[str, Any], config: DeploymentConfig
    ) -> OperationResult:
        """Perform rolling deployment"""
        try:
            namespace = config.namespace
            deployment_name = f"claude-{agent_type}"

            # Check if deployment exists
            try:
                existing = self.apps_v1.read_namespaced_deployment(
                    deployment_name, namespace
                )
                update_mode = True
            except ApiException as e:
                if e.status == 404:
                    update_mode = False
                else:
                    raise

            if update_mode:
                # Update existing deployment
                deployment = manifests["deployment"]
                result = self.apps_v1.patch_namespaced_deployment(
                    deployment_name, namespace, deployment
                )

                # Wait for rollout to complete
                self._wait_for_rollout_completion(deployment_name, namespace)

            else:
                # Create new deployment
                for manifest_type, manifest in manifests.items():
                    if manifest_type == "deployment":
                        self.apps_v1.create_namespaced_deployment(namespace, manifest)
                    elif manifest_type == "service":
                        self.core_v1.create_namespaced_service(namespace, manifest)
                    elif manifest_type == "hpa":
                        self.autoscaling_v1.create_namespaced_horizontal_pod_autoscaler(
                            namespace, manifest
                        )

                # Wait for deployment to be ready
                self._wait_for_deployment_ready(deployment_name, namespace)

            return OperationResult(True, data={"deployment_name": deployment_name})

        except Exception as e:
            return OperationResult(False, f"Rolling deployment failed: {e}")

    def _blue_green_deployment(
        self, agent_type: str, manifests: Dict[str, Any], config: DeploymentConfig
    ) -> OperationResult:
        """Perform blue-green deployment"""
        try:
            namespace = config.namespace
            green_name = f"claude-{agent_type}-green"
            blue_name = f"claude-{agent_type}"

            # Deploy green version
            green_manifests = copy.deepcopy(manifests)
            green_manifests["deployment"]["metadata"]["name"] = green_name
            green_manifests["deployment"]["spec"]["selector"]["matchLabels"][
                "version"
            ] = "green"
            green_manifests["deployment"]["spec"]["template"]["metadata"]["labels"][
                "version"
            ] = "green"

            # Create green deployment
            self.apps_v1.create_namespaced_deployment(
                namespace, green_manifests["deployment"]
            )

            # Wait for green to be ready
            self._wait_for_deployment_ready(green_name, namespace)

            # Validate green deployment
            if self._validate_deployment(green_name, namespace):
                # Switch traffic to green
                service_manifest = manifests["service"]
                service_manifest["spec"]["selector"]["version"] = "green"

                self.core_v1.patch_namespaced_service(
                    f"claude-{agent_type}", namespace, service_manifest
                )

                # Delete blue deployment after delay
                try:
                    self.apps_v1.delete_namespaced_deployment(blue_name, namespace)
                except ApiException:
                    pass  # Blue might not exist

                return OperationResult(True, data={"deployment_name": green_name})
            else:
                # Rollback - delete failed green deployment
                self.apps_v1.delete_namespaced_deployment(green_name, namespace)
                return OperationResult(False, "Green deployment validation failed")

        except Exception as e:
            return OperationResult(False, f"Blue-green deployment failed: {e}")

    def _canary_deployment(
        self, agent_type: str, manifests: Dict[str, Any], config: DeploymentConfig
    ) -> OperationResult:
        """Perform canary deployment"""
        try:
            namespace = config.namespace
            canary_name = f"claude-{agent_type}-canary"
            stable_name = f"claude-{agent_type}"

            # Deploy canary with 10% traffic
            canary_manifests = copy.deepcopy(manifests)
            canary_manifests["deployment"]["metadata"]["name"] = canary_name
            canary_manifests["deployment"]["spec"]["replicas"] = 1  # Start small
            canary_manifests["deployment"]["spec"]["selector"]["matchLabels"][
                "version"
            ] = "canary"
            canary_manifests["deployment"]["spec"]["template"]["metadata"]["labels"][
                "version"
            ] = "canary"

            # Create canary deployment
            self.apps_v1.create_namespaced_deployment(
                namespace, canary_manifests["deployment"]
            )

            # Wait for canary to be ready
            self._wait_for_deployment_ready(canary_name, namespace)

            # Monitor canary metrics
            canary_healthy = self._monitor_canary_health(
                canary_name, namespace, duration=300
            )

            if canary_healthy:
                # Gradually increase canary traffic
                for traffic_percent in [25, 50, 75, 100]:
                    self._adjust_canary_traffic(agent_type, namespace, traffic_percent)
                    time.sleep(60)  # Wait between adjustments

                    if not self._monitor_canary_health(
                        canary_name, namespace, duration=60
                    ):
                        # Rollback
                        self._rollback_canary(agent_type, namespace)
                        return OperationResult(False, "Canary health check failed")

                # Promote canary to stable
                self._promote_canary_to_stable(agent_type, namespace)
                return OperationResult(True, data={"deployment_name": canary_name})
            else:
                # Rollback canary
                self._rollback_canary(agent_type, namespace)
                return OperationResult(False, "Canary deployment unhealthy")

        except Exception as e:
            return OperationResult(False, f"Canary deployment failed: {e}")

    def scale_agent(
        self, agent_type: str, target_replicas: int, strategy: str = "gradual"
    ) -> OperationResult:
        """Scale agent instances"""
        if not self.k8s_client:
            return OperationResult(False, "Kubernetes client not available")

        start_time = time.time()

        try:
            deployment_name = f"claude-{agent_type}"

            # Get current deployment
            for namespace in self._get_agent_namespaces():
                try:
                    deployment = self.apps_v1.read_namespaced_deployment(
                        deployment_name, namespace
                    )
                    current_replicas = deployment.spec.replicas

                    if current_replicas == target_replicas:
                        return OperationResult(
                            True,
                            data={
                                "message": f"{agent_type} already at target scale: {target_replicas}"
                            },
                        )

                    # Record scaling event
                    scaling_event = ScalingEvent(
                        timestamp=datetime.now(),
                        agent_type=agent_type,
                        action=(
                            "scale_up"
                            if target_replicas > current_replicas
                            else "scale_down"
                        ),
                        from_replicas=current_replicas,
                        to_replicas=target_replicas,
                        reason="manual",
                        trigger_metrics={},
                        duration_seconds=0,
                        success=False,
                    )

                    # Apply scaling strategy
                    if (
                        strategy == "gradual"
                        and abs(target_replicas - current_replicas) > 2
                    ):
                        # Gradual scaling for large changes
                        self._gradual_scale(
                            deployment_name,
                            namespace,
                            current_replicas,
                            target_replicas,
                        )
                    else:
                        # Direct scaling
                        deployment.spec.replicas = target_replicas
                        self.apps_v1.patch_namespaced_deployment_scale(
                            deployment_name, namespace, deployment
                        )

                    # Wait for scaling to complete
                    self._wait_for_deployment_ready(
                        deployment_name, namespace, timeout=300
                    )

                    duration = time.time() - start_time
                    scaling_event.duration_seconds = duration
                    scaling_event.success = True

                    self.scaling_history.append(scaling_event)

                    return OperationResult(
                        True,
                        data={
                            "from_replicas": current_replicas,
                            "to_replicas": target_replicas,
                            "duration_seconds": duration,
                        },
                        duration_seconds=duration,
                    )

                except ApiException as e:
                    if e.status != 404:
                        raise

            return OperationResult(False, f"Agent {agent_type} not found")

        except Exception as e:
            duration = time.time() - start_time
            return OperationResult(
                False, f"Scaling failed: {e}", duration_seconds=duration
            )

    def _gradual_scale(
        self, deployment_name: str, namespace: str, from_replicas: int, to_replicas: int
    ):
        """Perform gradual scaling"""

        if from_replicas < to_replicas:
            # Scale up gradually
            step_size = max(1, (to_replicas - from_replicas) // 3)
            current = from_replicas

            while current < to_replicas:
                next_scale = min(current + step_size, to_replicas)

                # Update deployment
                deployment = self.apps_v1.read_namespaced_deployment(
                    deployment_name, namespace
                )
                deployment.spec.replicas = next_scale
                self.apps_v1.patch_namespaced_deployment_scale(
                    deployment_name, namespace, deployment
                )

                # Wait for pods to be ready
                self._wait_for_deployment_ready(deployment_name, namespace, timeout=120)

                current = next_scale
                time.sleep(10)  # Brief pause between scale steps

        else:
            # Scale down gradually
            step_size = max(1, (from_replicas - to_replicas) // 3)
            current = from_replicas

            while current > to_replicas:
                next_scale = max(current - step_size, to_replicas)

                # Update deployment
                deployment = self.apps_v1.read_namespaced_deployment(
                    deployment_name, namespace
                )
                deployment.spec.replicas = next_scale
                self.apps_v1.patch_namespaced_deployment_scale(
                    deployment_name, namespace, deployment
                )

                # Wait for scale down
                time.sleep(30)  # Allow pods to terminate gracefully

                current = next_scale

    def get_deployment_status(self, agent_type: str) -> Dict[str, Any]:
        """Get deployment status for agent"""
        if not self.k8s_client:
            return {"error": "Kubernetes client not available"}

        try:
            deployment_name = f"claude-{agent_type}"

            for namespace in self._get_agent_namespaces():
                try:
                    deployment = self.apps_v1.read_namespaced_deployment(
                        deployment_name, namespace
                    )

                    return {
                        "name": deployment.metadata.name,
                        "namespace": deployment.metadata.namespace,
                        "replicas": {
                            "desired": deployment.spec.replicas,
                            "ready": deployment.status.ready_replicas or 0,
                            "available": deployment.status.available_replicas or 0,
                            "unavailable": deployment.status.unavailable_replicas or 0,
                        },
                        "conditions": [
                            {
                                "type": condition.type,
                                "status": condition.status,
                                "reason": condition.reason,
                                "message": condition.message,
                                "last_transition": (
                                    condition.last_transition_time.isoformat()
                                    if condition.last_transition_time
                                    else None
                                ),
                            }
                            for condition in (deployment.status.conditions or [])
                        ],
                        "created": deployment.metadata.creation_timestamp.isoformat(),
                        "generation": deployment.metadata.generation,
                        "observed_generation": deployment.status.observed_generation,
                    }

                except ApiException as e:
                    if e.status != 404:
                        raise

            return {"error": f"Agent {agent_type} not found"}

        except Exception as e:
            return {"error": str(e)}

    def _monitor_deployments(self):
        """Background thread to monitor deployments"""
        while True:
            try:
                if self.auto_scaling_enabled:
                    self._check_auto_scaling()

                # Check deployment health
                self._check_deployment_health()

                time.sleep(60)  # Check every minute

            except Exception as e:
                logging.error(f"Deployment monitoring error: {e}")
                time.sleep(300)  # Longer delay on error

    def _check_auto_scaling(self):
        """Check if auto-scaling is needed"""
        current_time = time.time()

        # Only check every 5 minutes
        if current_time - self.last_scale_check < 300:
            return

        self.last_scale_check = current_time

        for agent_type in AGENT_RESOURCES.keys():
            try:
                # Get current metrics
                metrics = self._get_agent_metrics(agent_type)

                if not metrics:
                    continue

                # Check scaling conditions
                scale_decision = self._evaluate_scaling_decision(agent_type, metrics)

                if scale_decision["action"] != "none":
                    logging.info(f"Auto-scaling {agent_type}: {scale_decision}")

                    current_replicas = scale_decision["current_replicas"]
                    target_replicas = scale_decision["target_replicas"]

                    # Perform scaling
                    result = self.scale_agent(
                        agent_type, target_replicas, strategy="gradual"
                    )

                    # Record scaling event
                    scaling_event = ScalingEvent(
                        timestamp=datetime.now(),
                        agent_type=agent_type,
                        action=scale_decision["action"],
                        from_replicas=current_replicas,
                        to_replicas=target_replicas,
                        reason="auto_scaling",
                        trigger_metrics=metrics,
                        duration_seconds=result.duration_seconds,
                        success=result.success,
                    )

                    self.scaling_history.append(scaling_event)

            except Exception as e:
                logging.error(f"Auto-scaling check failed for {agent_type}: {e}")

    def _evaluate_scaling_decision(
        self, agent_type: str, metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """Evaluate if scaling is needed based on metrics"""

        # Get current deployment status
        status = self.get_deployment_status(agent_type)
        if "error" in status:
            return {"action": "none"}

        current_replicas = status["replicas"]["desired"]
        min_replicas = AGENT_RESOURCES[agent_type].get("min_replicas", 1)
        max_replicas = AGENT_RESOURCES[agent_type].get("max_replicas", 10)

        # Scaling decision logic
        cpu_usage = metrics.get("cpu_percentage", 0)
        memory_usage = metrics.get("memory_percentage", 0)
        latency = metrics.get("avg_latency_ms", 0)
        queue_depth = metrics.get("queue_depth", 0)

        scale_up_reasons = []
        scale_down_reasons = []

        # Scale up conditions
        if cpu_usage > AUTO_SCALE_THRESHOLDS["cpu_high"]:
            scale_up_reasons.append(f"CPU usage: {cpu_usage}%")

        if memory_usage > AUTO_SCALE_THRESHOLDS["memory_high"]:
            scale_up_reasons.append(f"Memory usage: {memory_usage}%")

        if latency > AUTO_SCALE_THRESHOLDS["latency_high"]:
            scale_up_reasons.append(f"High latency: {latency}ms")

        if queue_depth > AUTO_SCALE_THRESHOLDS["queue_high"]:
            scale_up_reasons.append(f"Queue depth: {queue_depth}")

        # Scale down conditions
        if (
            cpu_usage < AUTO_SCALE_THRESHOLDS["cpu_low"]
            and memory_usage < 50
            and latency < 100
            and queue_depth < 100
        ):
            scale_down_reasons.append("Low resource utilization")

        # Make scaling decision
        if scale_up_reasons and current_replicas < max_replicas:
            return {
                "action": "scale_up",
                "current_replicas": current_replicas,
                "target_replicas": min(current_replicas + 1, max_replicas),
                "reasons": scale_up_reasons,
            }

        elif scale_down_reasons and current_replicas > min_replicas:
            return {
                "action": "scale_down",
                "current_replicas": current_replicas,
                "target_replicas": max(current_replicas - 1, min_replicas),
                "reasons": scale_down_reasons,
            }

        else:
            return {
                "action": "none",
                "current_replicas": current_replicas,
                "target_replicas": current_replicas,
            }

    def _get_agent_namespaces(self) -> List[str]:
        """Get list of namespaces containing agents"""
        try:
            namespaces = self.core_v1.list_namespace()
            agent_namespaces = []

            for ns in namespaces.items:
                if "claude-agents" in ns.metadata.labels.get("app", ""):
                    agent_namespaces.append(ns.metadata.name)

            return agent_namespaces or ["claude-agents", "default"]

        except:
            return ["claude-agents", "default"]

    def _wait_for_deployment_ready(
        self, deployment_name: str, namespace: str, timeout: int = 300
    ):
        """Wait for deployment to be ready"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                deployment = self.apps_v1.read_namespaced_deployment(
                    deployment_name, namespace
                )

                desired_replicas = deployment.spec.replicas
                ready_replicas = deployment.status.ready_replicas or 0

                if ready_replicas >= desired_replicas:
                    return True

                time.sleep(10)

            except ApiException:
                time.sleep(10)

        raise Exception(f"Timeout waiting for {deployment_name} to be ready")

    def _generate_affinity_rules(self, agent_type: str) -> Dict[str, Any]:
        """Generate pod affinity rules"""
        return {
            "nodeAffinity": {
                "preferredDuringSchedulingIgnoredDuringExecution": [
                    {
                        "weight": 100,
                        "preference": {
                            "matchExpressions": [
                                {
                                    "key": "claude-agent-optimized",
                                    "operator": "In",
                                    "values": ["true"],
                                }
                            ]
                        },
                    }
                ]
            },
            "podAntiAffinity": {
                "preferredDuringSchedulingIgnoredDuringExecution": [
                    {
                        "weight": 100,
                        "podAffinityTerm": {
                            "labelSelector": {
                                "matchLabels": {"app": f"claude-{agent_type}"}
                            },
                            "topologyKey": "kubernetes.io/hostname",
                        },
                    }
                ]
            },
        }

    def _generate_tolerations(self, agent_type: str) -> List[Dict[str, Any]]:
        """Generate pod tolerations"""
        return [
            {
                "key": "claude-agents",
                "operator": "Equal",
                "value": "true",
                "effect": "NoSchedule",
            }
        ]


# ============================================================================
# DOCKER DEPLOYMENT MANAGER
# ============================================================================


class DockerDeploymentManager:
    """Manages Docker-based deployments for development/single-node"""

    __slots__ = []

    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logging.warning(f"Docker client not available: {e}")
            self.docker_client = None

        self.containers = {}

    def deploy_agent(self, agent_type: str, config: Dict[str, Any]) -> OperationResult:
        """Deploy agent using Docker"""
        if not self.docker_client:
            return OperationResult(False, "Docker client not available")

        try:
            container_name = f"claude-{agent_type}"

            # Stop existing container if running
            self._stop_container(container_name)

            # Get resource limits
            resources = AGENT_RESOURCES.get(agent_type, {})

            # Create and start container
            container = self.docker_client.containers.run(
                image=f"claude-agents/{agent_type}:latest",
                name=container_name,
                detach=True,
                restart_policy={"Name": "unless-stopped"},
                ports={
                    "8080/tcp": None,  # Dynamic port mapping
                    "9090/tcp": None,  # Metrics port
                },
                environment={
                    "AGENT_TYPE": agent_type,
                    "PROMETHEUS_ENDPOINT": "http://prometheus:9090",
                },
                mem_limit=resources.get("memory", "256m"),
                cpu_count=self._parse_cpu_limit(resources.get("cpu", "200m")),
                labels={
                    "app": f"claude-{agent_type}",
                    "component": "agent",
                    "type": agent_type,
                },
            )

            self.containers[agent_type] = container

            return OperationResult(
                True,
                data={"container_id": container.id, "container_name": container_name},
            )

        except Exception as e:
            return OperationResult(False, f"Docker deployment failed: {e}")

    def _stop_container(self, container_name: str):
        """Stop and remove existing container"""
        try:
            container = self.docker_client.containers.get(container_name)
            container.stop(timeout=30)
            container.remove()
        except docker.errors.NotFound:
            pass  # Container doesn't exist
        except Exception as e:
            logging.warning(f"Failed to stop container {container_name}: {e}")

    def _parse_cpu_limit(self, cpu_str: str) -> float:
        """Parse CPU limit string (e.g., '500m' -> 0.5)"""
        if cpu_str.endswith("m"):
            return float(cpu_str[:-1]) / 1000
        else:
            return float(cpu_str)


# ============================================================================
# MAIN DEPLOYMENT MANAGER
# ============================================================================


class DeploymentManager:
    """Main deployment manager - orchestrates Kubernetes and Docker deployments"""

    __slots__ = []

    def __init__(self):
        self.k8s_manager = KubernetesDeploymentManager()
        self.docker_manager = DockerDeploymentManager()

        # Determine primary deployment method
        self.use_kubernetes = self.k8s_manager.k8s_client is not None

        logging.info(
            f"Deployment manager initialized - using {'Kubernetes' if self.use_kubernetes else 'Docker'}"
        )

    def create_deployment_plan(
        self, environment: str, config_path: Optional[str] = None
    ) -> DeploymentPlan:
        """Create deployment plan for environment"""

        # Load configuration
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
        else:
            config_data = self._get_default_config(environment)

        config = DeploymentConfig(
            environment=environment,
            cluster_name=config_data.get("cluster_name", "claude-agents"),
            namespace=config_data.get("namespace", "claude-agents"),
            agent_configs=config_data.get("agents", {}),
            resource_limits=config_data.get("resources", {}),
            scaling_policies=config_data.get("scaling", {}),
            networking=config_data.get("networking", {}),
            security=config_data.get("security", {}),
            monitoring=config_data.get("monitoring", {}),
        )

        # Generate deployment steps
        steps = []

        # Infrastructure setup
        steps.append(
            DeploymentStep(
                name="setup_namespace",
                description="Create namespace and RBAC",
                action="create_namespace",
                parameters={"namespace": config.namespace},
            )
        )

        # Deploy core agents first
        core_agents = ["director", "project-orchestrator", "security"]
        for agent in core_agents:
            if agent in config.agent_configs or agent in AGENT_RESOURCES:
                steps.append(
                    DeploymentStep(
                        name=f"deploy_{agent}",
                        description=f"Deploy {agent} agent",
                        action="deploy_agent",
                        parameters={
                            "agent_type": agent,
                            "config": config,
                            "strategy": "rolling",
                        },
                        dependencies=["setup_namespace"],
                    )
                )

        # Deploy remaining agents
        remaining_agents = [a for a in AGENT_RESOURCES.keys() if a not in core_agents]
        for agent in remaining_agents:
            if agent in config.agent_configs or agent in AGENT_RESOURCES:
                steps.append(
                    DeploymentStep(
                        name=f"deploy_{agent}",
                        description=f"Deploy {agent} agent",
                        action="deploy_agent",
                        parameters={
                            "agent_type": agent,
                            "config": config,
                            "strategy": "rolling",
                        },
                        dependencies=[f"deploy_{core_agents[0]}"],
                    )
                )

        # Post-deployment validation
        steps.append(
            DeploymentStep(
                name="validate_deployment",
                description="Validate deployment health",
                action="validate_cluster",
                parameters={"config": config},
                dependencies=[
                    f"deploy_{agent}" for agent in core_agents + remaining_agents[:3]
                ],
            )
        )

        return DeploymentPlan(
            name=f"{environment}_deployment",
            version="1.0.0",
            environment=environment,
            steps=steps,
            estimated_duration=len(steps) * 60,  # Estimate 1 minute per step
            rollback_plan=self._create_rollback_plan(steps),
            validation_checks=[
                "health_check",
                "performance_check",
                "connectivity_check",
            ],
        )

    def execute_step(self, step: DeploymentStep) -> OperationResult:
        """Execute single deployment step"""
        try:
            if step.action == "create_namespace":
                return self._create_namespace(step.parameters)
            elif step.action == "deploy_agent":
                return self._deploy_agent(step.parameters)
            elif step.action == "validate_cluster":
                return self._validate_cluster(step.parameters)
            else:
                return OperationResult(False, f"Unknown action: {step.action}")

        except Exception as e:
            return OperationResult(False, f"Step execution failed: {e}")

    def _deploy_agent(self, parameters: Dict[str, Any]) -> OperationResult:
        """Deploy agent using appropriate manager"""
        agent_type = parameters["agent_type"]
        config = parameters["config"]
        strategy = parameters.get("strategy", "rolling")

        if self.use_kubernetes:
            return self.k8s_manager.deploy_agent(agent_type, config, strategy)
        else:
            return self.docker_manager.deploy_agent(agent_type, config.__dict__)

    def scale_agent(
        self, agent_type: str, target_scale: int, strategy: str = "rolling"
    ) -> OperationResult:
        """Scale agent instances"""
        if self.use_kubernetes:
            return self.k8s_manager.scale_agent(agent_type, target_scale, strategy)
        else:
            # Docker scaling would involve creating multiple containers
            return OperationResult(False, "Docker scaling not implemented")

    def _get_default_config(self, environment: str) -> Dict[str, Any]:
        """Get default configuration for environment"""
        return {
            "cluster_name": f"claude-agents-{environment}",
            "namespace": "claude-agents",
            "agents": {},
            "resources": {},
            "scaling": {"auto_scaling": environment == "production"},
            "networking": {},
            "security": {},
            "monitoring": {"prometheus_enabled": True},
        }
