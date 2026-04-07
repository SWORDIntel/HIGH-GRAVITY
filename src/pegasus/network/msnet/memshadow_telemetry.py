"""
MEMSHADOW Protocol - Advanced Telemetry

Comprehensive telemetry and metrics collection for monitoring,
performance analysis, and anomaly detection.
"""

import time
import statistics
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import IntEnum
from collections import deque, defaultdict
import json


class MetricType(IntEnum):
    """Telemetry metric types"""
    COUNTER = 1  # Incrementing counter
    GAUGE = 2  # Current value
    HISTOGRAM = 3  # Value distribution
    SUMMARY = 4  # Summary statistics


@dataclass
class Metric:
    """Telemetry metric"""
    name: str
    metric_type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    unit: str = ""


@dataclass
class MessageMetrics:
    """Per-message metrics"""
    message_id: str
    message_type: int
    size: int
    sent_at: float
    received_at: Optional[float] = None
    latency_ms: Optional[float] = None
    retry_count: int = 0
    success: bool = False


@dataclass
class NetworkMetrics:
    """Network-level metrics"""
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0
    retries: int = 0
    connections_active: int = 0
    connections_total: int = 0
    bandwidth_sent_bps: float = 0.0
    bandwidth_received_bps: float = 0.0


@dataclass
class PeerMetrics:
    """Per-peer metrics"""
    peer_id: str
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=100))
    error_count: int = 0
    last_seen: float = field(default_factory=time.time)
    connection_quality: float = 1.0  # 0.0 to 1.0
    rtt_ms: Optional[float] = None


class TelemetryCollector:
    """
    Telemetry data collector
    
    Collects metrics from various protocol components.
    """
    
    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self.message_metrics: Dict[str, MessageMetrics] = {}
        self.network_metrics = NetworkMetrics()
        self.peer_metrics: Dict[str, PeerMetrics] = {}
        self.custom_metrics: Dict[str, List[Metric]] = defaultdict(list)
    
    def record_metric(self, metric: Metric):
        """Record a metric"""
        key = f"{metric.name}:{json.dumps(metric.labels, sort_keys=True)}"
        self.metrics[key].append(metric)
        
        # Also store in custom metrics
        self.custom_metrics[metric.name].append(metric)
        if len(self.custom_metrics[metric.name]) > self.max_samples:
            self.custom_metrics[metric.name].pop(0)
    
    def record_message_sent(
        self,
        message_id: str,
        message_type: int,
        size: int,
        peer_id: str
    ):
        """Record message sent"""
        metrics = MessageMetrics(
            message_id=message_id,
            message_type=message_type,
            size=size,
            sent_at=time.time()
        )
        self.message_metrics[message_id] = metrics
        
        # Update network metrics
        self.network_metrics.messages_sent += 1
        self.network_metrics.bytes_sent += size
        
        # Update peer metrics
        if peer_id not in self.peer_metrics:
            self.peer_metrics[peer_id] = PeerMetrics(peer_id=peer_id)
        peer = self.peer_metrics[peer_id]
        peer.messages_sent += 1
        peer.bytes_sent += size
        peer.last_seen = time.time()
    
    def record_message_received(
        self,
        message_id: str,
        message_type: int,
        size: int,
        peer_id: str
    ):
        """Record message received"""
        if message_id in self.message_metrics:
            metrics = self.message_metrics[message_id]
            metrics.received_at = time.time()
            if metrics.sent_at:
                metrics.latency_ms = (metrics.received_at - metrics.sent_at) * 1000
            metrics.success = True
        
        # Update network metrics
        self.network_metrics.messages_received += 1
        self.network_metrics.bytes_received += size
        
        # Update peer metrics
        if peer_id not in self.peer_metrics:
            self.peer_metrics[peer_id] = PeerMetrics(peer_id=peer_id)
        peer = self.peer_metrics[peer_id]
        peer.messages_received += 1
        peer.bytes_received += size
        peer.last_seen = time.time()
        
        # Record latency if available
        if message_id in self.message_metrics:
            latency = self.message_metrics[message_id].latency_ms
            if latency:
                peer.latency_samples.append(latency)
                peer.rtt_ms = statistics.mean(peer.latency_samples) if peer.latency_samples else None
    
    def record_error(self, error_type: str, peer_id: Optional[str] = None):
        """Record error"""
        self.network_metrics.errors += 1
        
        if peer_id and peer_id in self.peer_metrics:
            self.peer_metrics[peer_id].error_count += 1
    
    def record_retry(self, message_id: str):
        """Record message retry"""
        if message_id in self.message_metrics:
            self.message_metrics[message_id].retry_count += 1
        self.network_metrics.retries += 1
    
    def update_connection_count(self, active: int, total: int):
        """Update connection counts"""
        self.network_metrics.connections_active = active
        self.network_metrics.connections_total = total
    
    def update_bandwidth(self, sent_bps: float, received_bps: float):
        """Update bandwidth metrics"""
        self.network_metrics.bandwidth_sent_bps = sent_bps
        self.network_metrics.bandwidth_received_bps = received_bps
    
    def get_network_metrics(self) -> NetworkMetrics:
        """Get network-level metrics"""
        return self.network_metrics
    
    def get_peer_metrics(self, peer_id: str) -> Optional[PeerMetrics]:
        """Get metrics for specific peer"""
        return self.peer_metrics.get(peer_id)
    
    def get_all_peer_metrics(self) -> Dict[str, PeerMetrics]:
        """Get all peer metrics"""
        return self.peer_metrics.copy()
    
    def get_message_metrics(self, message_id: str) -> Optional[MessageMetrics]:
        """Get metrics for specific message"""
        return self.message_metrics.get(message_id)
    
    def get_metric_statistics(self, metric_name: str) -> Dict:
        """Get statistics for a metric"""
        if metric_name not in self.custom_metrics:
            return {}
        
        values = [m.value for m in self.custom_metrics[metric_name]]
        if not values:
            return {}
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0.0
        }


class NetworkTopologyTracker:
    """
    Network topology tracking
    
    Tracks network structure and relationships.
    """
    
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}  # node_id -> node info
        self.edges: List[Tuple[str, str]] = []  # (node1, node2) connections
        self.clusters: Dict[str, Set[str]] = {}  # cluster_id -> set of nodes
    
    def add_node(self, node_id: str, info: Dict):
        """Add node to topology"""
        self.nodes[node_id] = info
    
    def add_edge(self, node1: str, node2: str):
        """Add connection edge"""
        edge = (min(node1, node2), max(node1, node2))
        if edge not in self.edges:
            self.edges.append(edge)
    
    def remove_edge(self, node1: str, node2: str):
        """Remove connection edge"""
        edge = (min(node1, node2), max(node1, node2))
        if edge in self.edges:
            self.edges.remove(edge)
    
    def get_neighbors(self, node_id: str) -> List[str]:
        """Get neighbors of a node"""
        neighbors = []
        for node1, node2 in self.edges:
            if node1 == node_id:
                neighbors.append(node2)
            elif node2 == node_id:
                neighbors.append(node1)
        return neighbors
    
    def get_topology_graph(self) -> Dict:
        """Get topology as graph structure"""
        return {
            'nodes': list(self.nodes.keys()),
            'edges': self.edges,
            'node_count': len(self.nodes),
            'edge_count': len(self.edges)
        }


class PerformanceAnalyzer:
    """
    Performance analysis
    
    Analyzes performance metrics and identifies bottlenecks.
    """
    
    def __init__(self, collector: TelemetryCollector):
        self.collector = collector
    
    def analyze_latency(self) -> Dict:
        """Analyze message latency"""
        latencies = []
        for metrics in self.collector.message_metrics.values():
            if metrics.latency_ms:
                latencies.append(metrics.latency_ms)
        
        if not latencies:
            return {}
        
        return {
            'count': len(latencies),
            'min_ms': min(latencies),
            'max_ms': max(latencies),
            'mean_ms': statistics.mean(latencies),
            'median_ms': statistics.median(latencies),
            'p95_ms': self._percentile(latencies, 95),
            'p99_ms': self._percentile(latencies, 99)
        }
    
    def analyze_throughput(self, window_seconds: float = 60.0) -> Dict:
        """Analyze throughput"""
        current_time = time.time()
        recent_messages = [
            m for m in self.collector.message_metrics.values()
            if m.sent_at and (current_time - m.sent_at) <= window_seconds
        ]
        
        if not recent_messages:
            return {}
        
        total_bytes = sum(m.size for m in recent_messages)
        time_span = max(
            (current_time - m.sent_at for m in recent_messages),
            default=1.0
        )
        
        return {
            'messages_per_second': len(recent_messages) / time_span,
            'bytes_per_second': total_bytes / time_span,
            'bits_per_second': (total_bytes * 8) / time_span
        }
    
    def analyze_error_rate(self) -> Dict:
        """Analyze error rate"""
        total_messages = self.collector.network_metrics.messages_sent
        errors = self.collector.network_metrics.errors
        
        if total_messages == 0:
            return {'error_rate': 0.0, 'errors': 0, 'total': 0}
        
        return {
            'error_rate': errors / total_messages,
            'errors': errors,
            'total': total_messages,
            'success_rate': 1.0 - (errors / total_messages)
        }
    
    def identify_bottlenecks(self) -> List[Dict]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Check latency
        latency_analysis = self.analyze_latency()
        if latency_analysis.get('p95_ms', 0) > 1000:  # > 1 second
            bottlenecks.append({
                'type': 'high_latency',
                'severity': 'high',
                'p95_latency_ms': latency_analysis.get('p95_ms'),
                'description': 'High message latency detected'
            })
        
        # Check error rate
        error_analysis = self.analyze_error_rate()
        if error_analysis.get('error_rate', 0) > 0.1:  # > 10%
            bottlenecks.append({
                'type': 'high_error_rate',
                'severity': 'high',
                'error_rate': error_analysis.get('error_rate'),
                'description': 'High error rate detected'
            })
        
        # Check peer connection quality
        for peer_id, peer_metrics in self.collector.peer_metrics.items():
            if peer_metrics.connection_quality < 0.5:
                bottlenecks.append({
                    'type': 'poor_peer_quality',
                    'severity': 'medium',
                    'peer_id': peer_id,
                    'quality': peer_metrics.connection_quality,
                    'description': f'Poor connection quality with peer {peer_id}'
                })
        
        return bottlenecks
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class TelemetryManager:
    """
    Main telemetry manager
    
    Coordinates all telemetry collection and analysis.
    """
    
    def __init__(self):
        self.collector = TelemetryCollector()
        self.topology = NetworkTopologyTracker()
        self.analyzer = PerformanceAnalyzer(self.collector)
        self.enabled = True
    
    def enable(self):
        """Enable telemetry collection"""
        self.enabled = True
    
    def disable(self):
        """Disable telemetry collection"""
        self.enabled = False
    
    def get_comprehensive_report(self) -> Dict:
        """Get comprehensive telemetry report"""
        return {
            'network': {
                'metrics': {
                    'bytes_sent': self.collector.network_metrics.bytes_sent,
                    'bytes_received': self.collector.network_metrics.bytes_received,
                    'messages_sent': self.collector.network_metrics.messages_sent,
                    'messages_received': self.collector.network_metrics.messages_received,
                    'errors': self.collector.network_metrics.errors,
                    'retries': self.collector.network_metrics.retries,
                    'connections_active': self.collector.network_metrics.connections_active,
                    'bandwidth_sent_bps': self.collector.network_metrics.bandwidth_sent_bps,
                    'bandwidth_received_bps': self.collector.network_metrics.bandwidth_received_bps,
                },
                'latency': self.analyzer.analyze_latency(),
                'throughput': self.analyzer.analyze_throughput(),
                'error_rate': self.analyzer.analyze_error_rate(),
                'bottlenecks': self.analyzer.identify_bottlenecks()
            },
            'peers': {
                peer_id: {
                    'messages_sent': peer.messages_sent,
                    'messages_received': peer.messages_received,
                    'bytes_sent': peer.bytes_sent,
                    'bytes_received': peer.bytes_received,
                    'error_count': peer.error_count,
                    'connection_quality': peer.connection_quality,
                    'rtt_ms': peer.rtt_ms,
                    'last_seen': peer.last_seen
                }
                for peer_id, peer in self.collector.peer_metrics.items()
            },
            'topology': self.topology.get_topology_graph(),
            'timestamp': time.time()
        }
