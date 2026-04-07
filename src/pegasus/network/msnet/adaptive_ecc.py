"""
Adaptive ECC Manager

Automatically adjusts ECC strength based on connection quality feedback.
Tracks quality over time and adapts ECC mode to optimize for current conditions.
"""

import time
from typing import List, Tuple, Optional, Deque
from collections import deque
from dataclasses import dataclass, field

from src.pegasus.network.msnet.dsmil_protocol import ECC_NONE, ECC_PARITY, ECC_REED_SOLOMON, MAX_CONNECTION_QUALITY


@dataclass
class QualitySample:
    """Single quality measurement"""
    quality: int  # 0-255
    timestamp: float
    errors_corrected: bool = False  # Whether ECC corrected errors
    ecc_mode_used: int = ECC_NONE


@dataclass
class ConnectionStats:
    """Connection quality statistics"""
    current_quality: int = MAX_CONNECTION_QUALITY
    average_quality: float = MAX_CONNECTION_QUALITY
    min_quality: int = MAX_CONNECTION_QUALITY
    max_quality: int = MAX_CONNECTION_QUALITY
    error_rate: float = 0.0  # Fraction of messages with errors
    samples_count: int = 0
    trend: str = "stable"  # "improving", "degrading", "stable"


class AdaptiveECCManager:
    """
    Manages adaptive ECC based on connection quality feedback.
    
    Automatically adjusts ECC strength:
    - High quality (>200): No ECC or parity only
    - Medium quality (100-200): Parity ECC
    - Low quality (<100): Reed-Solomon ECC
    - Very low quality (<50): Strong Reed-Solomon
    
    Tracks quality trends and adapts proactively.
    """
    
    # Quality thresholds
    QUALITY_EXCELLENT = 200
    QUALITY_GOOD = 150
    QUALITY_FAIR = 100
    QUALITY_POOR = 50
    
    # ECC configuration
    RS_BYTES_LIGHT = 2  # Light Reed-Solomon
    RS_BYTES_MEDIUM = 4  # Medium Reed-Solomon
    RS_BYTES_STRONG = 8  # Strong Reed-Solomon
    
    def __init__(
        self,
        window_size: int = 20,  # Number of samples to track
        adaptation_rate: float = 0.1,  # How quickly to adapt (0-1)
        min_samples: int = 5,  # Minimum samples before adapting
    ):
        """
        Initialize adaptive ECC manager.
        
        Args:
            window_size: Number of quality samples to track
            adaptation_rate: Rate of adaptation (0.1 = slow, 1.0 = fast)
            min_samples: Minimum samples before making adaptation decisions
        """
        self.window_size = window_size
        self.adaptation_rate = adaptation_rate
        self.min_samples = min_samples
        
        # Quality history (sliding window)
        self.quality_history: Deque[QualitySample] = deque(maxlen=window_size)
        
        # Current ECC mode
        self.current_ecc_mode = ECC_NONE
        self.current_ecc_bytes = 0
        
        # Statistics
        self.stats = ConnectionStats()
        
        # Adaptation state
        self.last_adaptation_time = time.time()
        self.adaptation_cooldown = 2.0  # Seconds between adaptations
    
    def record_quality(
        self,
        quality: int,
        errors_corrected: bool = False,
        ecc_mode_used: int = ECC_NONE,
    ):
        """
        Record a quality measurement.
        
        Args:
            quality: Connection quality (0-255)
            errors_corrected: Whether ECC corrected errors
            ecc_mode_used: ECC mode that was used
        """
        sample = QualitySample(
            quality=quality,
            timestamp=time.time(),
            errors_corrected=errors_corrected,
            ecc_mode_used=ecc_mode_used,
        )
        
        self.quality_history.append(sample)
        self._update_stats()
        
        # Auto-adapt if enough samples and cooldown passed
        if len(self.quality_history) >= self.min_samples:
            if time.time() - self.last_adaptation_time >= self.adaptation_cooldown:
                self._adapt_ecc()
        elif len(self.quality_history) >= 1:
            # Adapt immediately for small sample sizes (for testing/quick adaptation)
            self._adapt_ecc()
    
    def _update_stats(self):
        """Update connection statistics from history"""
        if not self.quality_history:
            return
        
        qualities = [s.quality for s in self.quality_history]
        errors = [s.errors_corrected for s in self.quality_history]
        
        self.stats.current_quality = qualities[-1]
        self.stats.average_quality = sum(qualities) / len(qualities)
        self.stats.min_quality = min(qualities)
        self.stats.max_quality = max(qualities)
        self.stats.error_rate = sum(errors) / len(errors) if errors else 0.0
        self.stats.samples_count = len(self.quality_history)
        
        # Calculate trend
        if len(qualities) >= 3:
            recent_avg = sum(qualities[-3:]) / 3
            older_avg = sum(qualities[-6:-3]) / 3 if len(qualities) >= 6 else recent_avg
            
            if recent_avg > older_avg + 10:
                self.stats.trend = "improving"
            elif recent_avg < older_avg - 10:
                self.stats.trend = "degrading"
            else:
                self.stats.trend = "stable"
    
    def _adapt_ecc(self):
        """
        Automatically adapt ECC mode based on quality statistics.
        
        Uses quality, error rate, and trend to select optimal ECC.
        """
        if not self.quality_history:
            return
        
        avg_quality = self.stats.average_quality
        error_rate = self.stats.error_rate
        trend = self.stats.trend
        
        # Determine target ECC mode based on quality and errors
        if avg_quality >= self.QUALITY_EXCELLENT and error_rate < 0.01:
            # Excellent quality, low errors: no ECC needed
            target_mode = ECC_NONE
            target_bytes = 0
        
        elif avg_quality >= self.QUALITY_GOOD and error_rate < 0.05:
            # Good quality, few errors: light parity
            target_mode = ECC_PARITY
            target_bytes = 0
        
        elif avg_quality >= self.QUALITY_FAIR:
            # Fair quality: parity or light RS
            if error_rate > 0.1 or trend == "degrading":
                target_mode = ECC_REED_SOLOMON
                target_bytes = self.RS_BYTES_LIGHT
            else:
                target_mode = ECC_PARITY
                target_bytes = 0
        
        elif avg_quality >= self.QUALITY_POOR:
            # Poor quality: medium RS
            target_mode = ECC_REED_SOLOMON
            target_bytes = self.RS_BYTES_MEDIUM
        
        else:
            # Very poor quality: strong RS
            target_mode = ECC_REED_SOLOMON
            target_bytes = self.RS_BYTES_STRONG
        
        # Apply adaptation immediately
        self.current_ecc_mode = target_mode
        self.current_ecc_bytes = target_bytes
        self.last_adaptation_time = time.time()
    
    def get_recommended_ecc(self) -> Tuple[int, int]:
        """
        Get recommended ECC mode and bytes for current conditions.
        
        Returns:
            Tuple of (ecc_mode, ecc_bytes)
        """
        # If we have enough history, use adaptive mode
        if len(self.quality_history) >= self.min_samples:
            return self.current_ecc_mode, self.current_ecc_bytes
        
        # Otherwise, use conservative default based on current quality
        if self.stats.current_quality >= self.QUALITY_GOOD:
            return ECC_PARITY, 0
        elif self.stats.current_quality >= self.QUALITY_FAIR:
            return ECC_REED_SOLOMON, self.RS_BYTES_LIGHT
        else:
            return ECC_REED_SOLOMON, self.RS_BYTES_MEDIUM
    
    def get_stats(self) -> ConnectionStats:
        """Get current connection statistics"""
        return self.stats
    
    def reset(self):
        """Reset adaptation state"""
        self.quality_history.clear()
        self.current_ecc_mode = ECC_NONE
        self.current_ecc_bytes = 0
        self.stats = ConnectionStats()
        self.last_adaptation_time = time.time()
    
    def should_increase_ecc(self) -> bool:
        """Check if ECC should be increased based on recent quality"""
        if len(self.quality_history) < 3:
            return False
        
        recent = [s.quality for s in list(self.quality_history)[-3:]]
        avg_recent = sum(recent) / len(recent)
        
        return avg_recent < self.QUALITY_FAIR or self.stats.error_rate > 0.1
    
    def should_decrease_ecc(self) -> bool:
        """Check if ECC can be decreased based on recent quality"""
        if len(self.quality_history) < 5:
            return False
        
        recent = [s.quality for s in list(self.quality_history)[-5:]]
        avg_recent = sum(recent) / len(recent)
        
        return avg_recent > self.QUALITY_GOOD and self.stats.error_rate < 0.02


class ConnectionQualityTracker:
    """
    Tracks connection quality for a specific peer/connection.
    
    Maintains separate quality history per connection and provides
    adaptive ECC recommendations.
    """
    
    def __init__(self):
        """Initialize connection quality tracker"""
        self._connections: dict[str, AdaptiveECCManager] = {}
    
    def get_manager(self, connection_id: str) -> AdaptiveECCManager:
        """Get or create adaptive ECC manager for a connection"""
        if connection_id not in self._connections:
            self._connections[connection_id] = AdaptiveECCManager()
        return self._connections[connection_id]
    
    def record_quality(
        self,
        connection_id: str,
        quality: int,
        errors_corrected: bool = False,
        ecc_mode_used: int = ECC_NONE,
    ):
        """Record quality for a connection"""
        manager = self.get_manager(connection_id)
        manager.record_quality(quality, errors_corrected, ecc_mode_used)
    
    def get_recommended_ecc(self, connection_id: str) -> Tuple[int, int]:
        """Get recommended ECC for a connection"""
        manager = self.get_manager(connection_id)
        return manager.get_recommended_ecc()
    
    def get_stats(self, connection_id: str) -> Optional[ConnectionStats]:
        """Get connection statistics"""
        if connection_id not in self._connections:
            return None
        return self._connections[connection_id].get_stats()
    
    def remove_connection(self, connection_id: str):
        """Remove connection tracking"""
        self._connections.pop(connection_id, None)


# Global connection quality tracker
_global_tracker: Optional[ConnectionQualityTracker] = None


def get_connection_tracker() -> ConnectionQualityTracker:
    """Get global connection quality tracker"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ConnectionQualityTracker()
    return _global_tracker
