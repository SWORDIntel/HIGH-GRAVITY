"""
MEMSHADOW Protocol - Performance Auto-Tuning

Automatically tunes protocol parameters for optimal performance
based on observed metrics and network conditions.
"""

import time
import statistics
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import IntEnum
from collections import deque


class TuningParameter(IntEnum):
    """Tunable parameters"""
    BATCH_SIZE = 1
    WINDOW_SIZE = 2
    RETRY_TIMEOUT = 3
    COMPRESSION_LEVEL = 4
    PARALLEL_STREAMS = 5
    CHUNK_SIZE = 6


@dataclass
class ParameterValue:
    """Parameter value with bounds"""
    current: float
    min_value: float
    max_value: float
    step: float = 1.0


@dataclass
class PerformanceBaseline:
    """Performance baseline for comparison"""
    latency_ms: float
    throughput_bps: float
    error_rate: float
    timestamp: float = field(default_factory=time.time)


class AdaptiveTuner:
    """
    Adaptive parameter tuning
    
    Automatically adjusts parameters based on performance metrics.
    """
    
    def __init__(self):
        self.parameters: Dict[TuningParameter, ParameterValue] = {
            TuningParameter.BATCH_SIZE: ParameterValue(64, 1, 1000, 1),
            TuningParameter.WINDOW_SIZE: ParameterValue(65536, 1024, 1048576, 1024),
            TuningParameter.RETRY_TIMEOUT: ParameterValue(5.0, 1.0, 30.0, 0.5),
            TuningParameter.COMPRESSION_LEVEL: ParameterValue(6, 1, 9, 1),
            TuningParameter.PARALLEL_STREAMS: ParameterValue(4, 1, 16, 1),
            TuningParameter.CHUNK_SIZE: ParameterValue(2048, 512, 16384, 512),
        }
        
        self.baseline: Optional[PerformanceBaseline] = None
        self.performance_history: deque = deque(maxlen=100)
        self.tuning_enabled = True
    
    def set_parameter(
        self,
        param: TuningParameter,
        value: float
    ) -> bool:
        """Set parameter value (within bounds)"""
        if param not in self.parameters:
            return False
        
        param_value = self.parameters[param]
        value = max(param_value.min_value, min(param_value.max_value, value))
        param_value.current = value
        return True
    
    def get_parameter(self, param: TuningParameter) -> Optional[float]:
        """Get current parameter value"""
        if param in self.parameters:
            return self.parameters[param].current
        return None
    
    def record_performance(
        self,
        latency_ms: float,
        throughput_bps: float,
        error_rate: float
    ):
        """Record performance metrics"""
        self.performance_history.append({
            'latency': latency_ms,
            'throughput': throughput_bps,
            'error_rate': error_rate,
            'timestamp': time.time()
        })
        
        # Update baseline if not set or periodically
        if not self.baseline or len(self.performance_history) % 10 == 0:
            self._update_baseline()
    
    def _update_baseline(self):
        """Update performance baseline"""
        if len(self.performance_history) < 5:
            return
        
        recent = list(self.performance_history)[-20:]
        self.baseline = PerformanceBaseline(
            latency_ms=statistics.median([p['latency'] for p in recent]),
            throughput_bps=statistics.mean([p['throughput'] for p in recent]),
            error_rate=statistics.mean([p['error_rate'] for p in recent])
        )
    
    def tune_parameters(self) -> Dict[TuningParameter, float]:
        """
        Automatically tune parameters based on performance
        
        Returns:
            Dict of parameter changes
        """
        if not self.tuning_enabled or not self.baseline:
            return {}
        
        if len(self.performance_history) < 10:
            return {}
        
        recent = list(self.performance_history)[-10:]
        current_latency = statistics.median([p['latency'] for p in recent])
        current_throughput = statistics.mean([p['throughput'] for p in recent])
        current_error_rate = statistics.mean([p['error_rate'] for p in recent])
        
        changes = {}
        
        # Tune batch size based on throughput
        if current_throughput < self.baseline.throughput_bps * 0.8:
            # Low throughput - try increasing batch size
            batch_size = self.parameters[TuningParameter.BATCH_SIZE]
            new_value = min(batch_size.max_value, batch_size.current * 1.5)
            if new_value != batch_size.current:
                self.set_parameter(TuningParameter.BATCH_SIZE, new_value)
                changes[TuningParameter.BATCH_SIZE] = new_value
        
        # Tune window size based on latency
        if current_latency > self.baseline.latency_ms * 1.5:
            # High latency - try reducing window size
            window_size = self.parameters[TuningParameter.WINDOW_SIZE]
            new_value = max(window_size.min_value, window_size.current * 0.8)
            if new_value != window_size.current:
                self.set_parameter(TuningParameter.WINDOW_SIZE, new_value)
                changes[TuningParameter.WINDOW_SIZE] = new_value
        
        # Tune retry timeout based on error rate
        if current_error_rate > self.baseline.error_rate * 2:
            # High error rate - increase retry timeout
            retry_timeout = self.parameters[TuningParameter.RETRY_TIMEOUT]
            new_value = min(retry_timeout.max_value, retry_timeout.current * 1.2)
            if new_value != retry_timeout.current:
                self.set_parameter(TuningParameter.RETRY_TIMEOUT, new_value)
                changes[TuningParameter.RETRY_TIMEOUT] = new_value
        
        # Tune compression level based on throughput
        if current_throughput < self.baseline.throughput_bps * 0.9:
            # Low throughput - reduce compression (faster)
            comp_level = self.parameters[TuningParameter.COMPRESSION_LEVEL]
            new_value = max(comp_level.min_value, comp_level.current - 1)
            if new_value != comp_level.current:
                self.set_parameter(TuningParameter.COMPRESSION_LEVEL, new_value)
                changes[TuningParameter.COMPRESSION_LEVEL] = new_value
        
        # Tune parallel streams based on throughput
        if current_throughput < self.baseline.throughput_bps * 0.8:
            # Low throughput - try more parallel streams
            parallel_streams = self.parameters[TuningParameter.PARALLEL_STREAMS]
            new_value = min(parallel_streams.max_value, parallel_streams.current + 1)
            if new_value != parallel_streams.current:
                self.set_parameter(TuningParameter.PARALLEL_STREAMS, new_value)
                changes[TuningParameter.PARALLEL_STREAMS] = new_value
        
        return changes
    
    def get_optimal_parameters(self) -> Dict[TuningParameter, float]:
        """Get current optimal parameter values"""
        return {
            param: value.current
            for param, value in self.parameters.items()
        }


class IntelligentCache:
    """
    Intelligent message caching
    
    Caches messages intelligently based on access patterns.
    """
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: Dict[str, Dict] = {}
        self.access_times: Dict[str, float] = {}
        self.access_counts: Dict[str, int] = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def get(self, key: str) -> Optional[bytes]:
        """Get cached value"""
        if key in self.cache:
            self.cache_hits += 1
            self.access_times[key] = time.time()
            self.access_counts[key] = self.access_counts.get(key, 0) + 1
            return self.cache[key].get('data')
        
        self.cache_misses += 1
        return None
    
    def set(self, key: str, value: bytes, ttl: Optional[float] = None):
        """Set cached value"""
        # Evict if cache is full
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_lru()
        
        self.cache[key] = {
            'data': value,
            'ttl': ttl,
            'created_at': time.time()
        }
        self.access_times[key] = time.time()
        self.access_counts[key] = 1
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if not self.cache:
            return
        
        # Find LRU item
        lru_key = min(self.access_times.items(), key=lambda x: x[1])[0]
        del self.cache[lru_key]
        del self.access_times[lru_key]
        self.access_counts.pop(lru_key, None)
    
    def cleanup_expired(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if entry.get('ttl') and (current_time - entry['created_at']) > entry['ttl']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            self.access_times.pop(key, None)
            self.access_counts.pop(key, None)
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_rate': hit_rate
        }


class AutoTuneManager:
    """
    Main auto-tuning manager
    
    Coordinates parameter tuning and caching.
    """
    
    def __init__(self):
        self.tuner = AdaptiveTuner()
        self.cache = IntelligentCache()
        self.tuning_interval = 60.0  # Tune every 60 seconds
        self.last_tuning = 0.0
    
    def enable_auto_tuning(self):
        """Enable automatic tuning"""
        self.tuner.tuning_enabled = True
    
    def disable_auto_tuning(self):
        """Disable automatic tuning"""
        self.tuner.tuning_enabled = False
    
    def update_performance(
        self,
        latency_ms: float,
        throughput_bps: float,
        error_rate: float
    ):
        """Update performance metrics"""
        self.tuner.record_performance(latency_ms, throughput_bps, error_rate)
        
        # Auto-tune periodically
        current_time = time.time()
        if current_time - self.last_tuning >= self.tuning_interval:
            changes = self.tuner.tune_parameters()
            self.last_tuning = current_time
            
            if changes:
                return changes
        
        return {}
    
    def get_parameters(self) -> Dict[TuningParameter, float]:
        """Get current parameter values"""
        return self.tuner.get_optimal_parameters()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return self.cache.get_stats()


class AutoTuner:
    """
    Auto-Tuning - Simple parameter optimization

    Provides basic auto-tuning functionality for testing.
    """

    def __init__(self):
        self.parameter_performance: Dict[str, List[float]] = {}
        self.optimization_results: Dict[str, float] = {}

    def record_performance(self, parameter: str, performance_value: float):
        """
        Record performance for a parameter

        Args:
            parameter: Parameter name
            performance_value: Performance metric value
        """
        if parameter not in self.parameter_performance:
            self.parameter_performance[parameter] = []
        self.parameter_performance[parameter].append(performance_value)

    def optimize_parameter(self, parameter: str) -> Optional[float]:
        """
        Optimize a parameter based on recorded performance

        Args:
            parameter: Parameter name to optimize

        Returns:
            Optimized parameter value or None if insufficient data
        """
        if parameter not in self.parameter_performance:
            return None

        performance_values = self.parameter_performance[parameter]
        if len(performance_values) < 2:
            return None

        # Simple optimization: return the value that gave the best performance
        # In a real implementation, this would use more sophisticated algorithms
        best_performance = max(performance_values)
        best_index = performance_values.index(best_performance)

        # For this simple implementation, return the index as the "optimized" value
        # In practice, this would map back to actual parameter values
        optimized_value = float(best_index + 1)  # +1 to avoid 0

        self.optimization_results[parameter] = optimized_value
        return optimized_value
