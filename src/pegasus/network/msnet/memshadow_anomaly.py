"""
MEMSHADOW Protocol - Anomaly Detection

Detects anomalies in network behavior, performance, and security.
"""

import time
import statistics
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import IntEnum
from collections import deque
import math


class AnomalyType(IntEnum):
    """Types of anomalies"""
    TRAFFIC_PATTERN = 1  # Unusual traffic pattern
    PERFORMANCE_DEGRADATION = 2  # Performance issues
    SECURITY_THREAT = 3  # Security-related anomaly
    NETWORK_PARTITION = 4  # Network partition detected
    ATTACK_DETECTED = 5  # Attack pattern detected


class AnomalySeverity(IntEnum):
    """Anomaly severity levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Anomaly:
    """Detected anomaly"""
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    description: str
    detected_at: float = field(default_factory=time.time)
    metrics: Dict = field(default_factory=dict)
    node_id: Optional[str] = None
    resolved: bool = False


class TrafficPatternAnalyzer:
    """
    Traffic pattern analysis
    
    Detects unusual traffic patterns that might indicate issues or attacks.
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.message_times: deque = deque(maxlen=window_size)
        self.message_sizes: deque = deque(maxlen=window_size)
        self.baseline_rate: Optional[float] = None
        self.baseline_size: Optional[float] = None
    
    def record_message(self, size: int):
        """Record message for pattern analysis"""
        current_time = time.time()
        self.message_times.append(current_time)
        self.message_sizes.append(size)
        
        # Update baseline
        if len(self.message_times) >= 10:
            self._update_baseline()
    
    def _update_baseline(self):
        """Update baseline statistics"""
        if len(self.message_times) < 2:
            return
        
        # Calculate message rate
        time_span = self.message_times[-1] - self.message_times[0]
        if time_span > 0:
            self.baseline_rate = len(self.message_times) / time_span
        
        # Calculate average message size
        if self.message_sizes:
            self.baseline_size = statistics.mean(self.message_sizes)
    
    def detect_anomaly(self) -> Optional[Anomaly]:
        """Detect traffic pattern anomalies"""
        if len(self.message_times) < 10:
            return None
        
        current_time = time.time()
        recent_window = 60.0  # Last 60 seconds
        
        # Get recent messages
        recent_times = [
            t for t in self.message_times
            if current_time - t <= recent_window
        ]
        
        if len(recent_times) < 2:
            return None
        
        # Calculate current rate
        time_span = recent_times[-1] - recent_times[0]
        if time_span == 0:
            return None
        
        current_rate = len(recent_times) / time_span
        
        # Check for rate anomalies
        if self.baseline_rate:
            rate_ratio = current_rate / self.baseline_rate if self.baseline_rate > 0 else 0
            
            if rate_ratio > 5.0:  # 5x increase
                return Anomaly(
                    anomaly_type=AnomalyType.TRAFFIC_PATTERN,
                    severity=AnomalySeverity.HIGH,
                    description=f"Traffic spike detected: {current_rate:.2f} msg/s (baseline: {self.baseline_rate:.2f})",
                    metrics={
                        'current_rate': current_rate,
                        'baseline_rate': self.baseline_rate,
                        'ratio': rate_ratio
                    }
                )
            
            elif rate_ratio < 0.1:  # 90% decrease
                return Anomaly(
                    anomaly_type=AnomalyType.TRAFFIC_PATTERN,
                    severity=AnomalySeverity.MEDIUM,
                    description=f"Traffic drop detected: {current_rate:.2f} msg/s (baseline: {self.baseline_rate:.2f})",
                    metrics={
                        'current_rate': current_rate,
                        'baseline_rate': self.baseline_rate,
                        'ratio': rate_ratio
                    }
                )
        
        return None


class PerformanceAnomalyDetector:
    """
    Performance anomaly detection
    
    Detects performance degradation and bottlenecks.
    """
    
    def __init__(self):
        self.latency_samples: deque = deque(maxlen=1000)
        self.error_samples: deque = deque(maxlen=1000)
        self.baseline_latency: Optional[float] = None
        self.baseline_error_rate: Optional[float] = None
    
    def record_latency(self, latency_ms: float):
        """Record latency sample"""
        self.latency_samples.append(latency_ms)
        
        if len(self.latency_samples) >= 100:
            self.baseline_latency = statistics.median(self.latency_samples)
    
    def record_error(self, is_error: bool):
        """Record error sample"""
        self.error_samples.append(1 if is_error else 0)
        
        if len(self.error_samples) >= 100:
            self.baseline_error_rate = statistics.mean(self.error_samples)
    
    def detect_anomaly(self) -> Optional[Anomaly]:
        """Detect performance anomalies"""
        if len(self.latency_samples) < 10:
            return None
        
        # Check latency degradation
        recent_latencies = list(self.latency_samples)[-100:]
        if recent_latencies and self.baseline_latency:
            current_median = statistics.median(recent_latencies)
            
            if current_median > self.baseline_latency * 3:  # 3x increase
                return Anomaly(
                    anomaly_type=AnomalyType.PERFORMANCE_DEGRADATION,
                    severity=AnomalySeverity.HIGH,
                    description=f"Latency degradation: {current_median:.2f}ms (baseline: {self.baseline_latency:.2f}ms)",
                    metrics={
                        'current_latency': current_median,
                        'baseline_latency': self.baseline_latency,
                        'degradation_ratio': current_median / self.baseline_latency
                    }
                )
        
        # Check error rate increase
        if len(self.error_samples) >= 10 and self.baseline_error_rate is not None:
            recent_errors = list(self.error_samples)[-100:]
            current_error_rate = statistics.mean(recent_errors)
            
            if current_error_rate > self.baseline_error_rate * 2 and current_error_rate > 0.1:
                return Anomaly(
                    anomaly_type=AnomalyType.PERFORMANCE_DEGRADATION,
                    severity=AnomalySeverity.MEDIUM,
                    description=f"Error rate increase: {current_error_rate:.2%} (baseline: {self.baseline_error_rate:.2%})",
                    metrics={
                        'current_error_rate': current_error_rate,
                        'baseline_error_rate': self.baseline_error_rate
                    }
                )
        
        return None


class SecurityAnomalyDetector:
    """
    Security anomaly detection
    
    Detects security threats and attack patterns.
    """
    
    def __init__(self):
        self.failed_auth_attempts: Dict[str, int] = {}  # peer_id -> count
        self.suspicious_messages: List[Dict] = []
        self.rate_limit_violations: Dict[str, int] = {}  # peer_id -> count
    
    def record_auth_failure(self, peer_id: str):
        """Record authentication failure"""
        self.failed_auth_attempts[peer_id] = self.failed_auth_attempts.get(peer_id, 0) + 1
    
    def record_suspicious_message(self, peer_id: str, reason: str):
        """Record suspicious message"""
        self.suspicious_messages.append({
            'peer_id': peer_id,
            'reason': reason,
            'timestamp': time.time()
        })
    
    def record_rate_limit_violation(self, peer_id: str):
        """Record rate limit violation"""
        self.rate_limit_violations[peer_id] = self.rate_limit_violations.get(peer_id, 0) + 1
    
    def detect_anomaly(self) -> Optional[Anomaly]:
        """Detect security anomalies"""
        # Check for brute force attacks
        for peer_id, count in self.failed_auth_attempts.items():
            if count >= 5:  # 5 failed attempts
                return Anomaly(
                    anomaly_type=AnomalyType.SECURITY_THREAT,
                    severity=AnomalySeverity.HIGH,
                    description=f"Multiple authentication failures from {peer_id}",
                    node_id=peer_id,
                    metrics={
                        'failed_attempts': count,
                        'type': 'brute_force'
                    }
                )
        
        # Check for rate limit violations
        for peer_id, count in self.rate_limit_violations.items():
            if count >= 10:  # 10 violations
                return Anomaly(
                    anomaly_type=AnomalyType.ATTACK_DETECTED,
                    severity=AnomalySeverity.MEDIUM,
                    description=f"Rate limit violations from {peer_id}",
                    node_id=peer_id,
                    metrics={
                        'violations': count,
                        'type': 'rate_limit_abuse'
                    }
                )
        
        # Check for suspicious message patterns
        recent_suspicious = [
            m for m in self.suspicious_messages
            if time.time() - m['timestamp'] <= 300  # Last 5 minutes
        ]
        
        if len(recent_suspicious) >= 10:
            return Anomaly(
                anomaly_type=AnomalyType.SECURITY_THREAT,
                severity=AnomalySeverity.MEDIUM,
                description=f"Multiple suspicious messages detected ({len(recent_suspicious)} in last 5 minutes)",
                metrics={
                    'suspicious_count': len(recent_suspicious),
                    'type': 'suspicious_pattern'
                }
            )
        
        return None
    
    def reset_peer(self, peer_id: str):
        """Reset counters for peer"""
        self.failed_auth_attempts.pop(peer_id, None)
        self.rate_limit_violations.pop(peer_id, None)


class AnomalyDetector:
    """
    Main anomaly detector
    
    Coordinates all anomaly detection components.
    """
    
    def __init__(self):
        self.traffic_analyzer = TrafficPatternAnalyzer()
        self.performance_detector = PerformanceAnomalyDetector()
        self.security_detector = SecurityAnomalyDetector()
        self.detected_anomalies: List[Anomaly] = []
        self.anomaly_callbacks: List[callable] = []
    
    def register_callback(self, callback: callable):
        """Register callback for anomaly detection"""
        self.anomaly_callbacks.append(callback)
    
    def record_message(self, size: int):
        """Record message for analysis"""
        self.traffic_analyzer.record_message(size)
    
    def record_latency(self, latency_ms: float):
        """Record latency for analysis"""
        self.performance_detector.record_latency(latency_ms)
    
    def record_error(self, is_error: bool):
        """Record error for analysis"""
        self.performance_detector.record_error(is_error)
    
    def record_auth_failure(self, peer_id: str):
        """Record authentication failure"""
        self.security_detector.record_auth_failure(peer_id)
    
    def detect_all(self) -> List[Anomaly]:
        """Run all anomaly detectors"""
        anomalies = []
        
        # Traffic pattern anomalies
        traffic_anomaly = self.traffic_analyzer.detect_anomaly()
        if traffic_anomaly:
            anomalies.append(traffic_anomaly)
        
        # Performance anomalies
        perf_anomaly = self.performance_detector.detect_anomaly()
        if perf_anomaly:
            anomalies.append(perf_anomaly)
        
        # Security anomalies
        security_anomaly = self.security_detector.detect_anomaly()
        if security_anomaly:
            anomalies.append(security_anomaly)
        
        # Store detected anomalies
        for anomaly in anomalies:
            if anomaly not in self.detected_anomalies:
                self.detected_anomalies.append(anomaly)
                
                # Notify callbacks
                for callback in self.anomaly_callbacks:
                    try:
                        callback(anomaly)
                    except Exception:
                        pass
        
        return anomalies
    
    def get_recent_anomalies(self, seconds: float = 3600) -> List[Anomaly]:
        """Get anomalies detected in last N seconds"""
        cutoff = time.time() - seconds
        return [
            a for a in self.detected_anomalies
            if a.detected_at >= cutoff
        ]
    
    def get_unresolved_anomalies(self) -> List[Anomaly]:
        """Get unresolved anomalies"""
        return [a for a in self.detected_anomalies if not a.resolved]
    
    def resolve_anomaly(self, anomaly: Anomaly):
        """Mark anomaly as resolved"""
        anomaly.resolved = True
