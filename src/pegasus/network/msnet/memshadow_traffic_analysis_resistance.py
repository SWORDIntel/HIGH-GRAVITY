"""
MEMSHADOW Protocol - Traffic Analysis Resistance

Implements techniques to resist traffic analysis, including:
- Packet size normalization
- Timing pattern masking
- Flow correlation resistance
- Protocol fingerprinting resistance
"""

import time
import random
import struct
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from enum import IntEnum
from collections import deque
import hashlib


class ResistanceLevel(IntEnum):
    """Traffic analysis resistance levels"""
    NONE = 0
    BASIC = 1  # Basic padding and delays
    INTERMEDIATE = 2  # Size normalization and timing jitter
    ADVANCED = 3  # Full pattern masking
    MAXIMUM = 4  # Maximum resistance with dummy traffic


@dataclass
class PacketSizeDistribution:
    """Packet size distribution for normalization"""
    min_size: int = 64
    max_size: int = 1500
    common_sizes: List[int] = None  # Common sizes to mimic
    
    def __post_init__(self):
        if self.common_sizes is None:
            # Common packet sizes in typical networks
            self.common_sizes = [
                64, 128, 256, 512, 576, 1024, 1280, 1500
            ]


class PacketSizeNormalizer:
    """
    Normalize packet sizes to resist analysis
    
    Prevents fingerprinting based on packet size patterns.
    """
    
    def __init__(self, distribution: Optional[PacketSizeDistribution] = None):
        self.distribution = distribution or PacketSizeDistribution()
        self.size_history: deque = deque(maxlen=1000)
    
    def normalize(self, data: bytes) -> List[bytes]:
        """
        Normalize data into packets of common sizes
        
        Args:
            data: Data to normalize
        
        Returns:
            List of normalized packets
        """
        packets = []
        remaining = data
        
        while remaining:
            # Select size from common distribution
            target_size = random.choice(self.distribution.common_sizes)
            chunk_size = min(len(remaining), target_size)
            
            chunk = remaining[:chunk_size]
            remaining = remaining[chunk_size:]
            
            # Pad to exact size if needed
            if len(chunk) < target_size:
                import os
                padding = os.urandom(target_size - len(chunk))
                chunk += padding
            
            packets.append(chunk)
            self.size_history.append(len(chunk))
        
        return packets
    
    def add_dummy_packets(self, count: int) -> List[bytes]:
        """Generate dummy packets to mask real traffic"""
        packets = []
        
        import os
        for _ in range(count):
            size = random.choice(self.distribution.common_sizes)
            packet = os.urandom(size)
            packets.append(packet)
        
        return packets


class TimingPatternMasker:
    """
    Mask timing patterns to resist analysis
    
    Prevents correlation based on inter-packet timing.
    """
    
    def __init__(self):
        self.base_delay = 0.1  # Base delay (100ms)
        self.jitter_range = 0.05  # ±50ms jitter
        self.timing_history: deque = deque(maxlen=1000)
        self.last_send_time = 0.0
    
    def get_next_delay(self) -> float:
        """
        Get next inter-packet delay
        
        Uses random jitter to prevent timing analysis.
        """
        delay = self.base_delay + random.uniform(
            -self.jitter_range,
            self.jitter_range
        )
        delay = max(0.01, delay)  # Minimum delay
        
        self.timing_history.append(delay)
        return delay
    
    def mask_timing_pattern(self, delays: List[float]) -> List[float]:
        """
        Mask timing pattern by adding noise
        
        Args:
            delays: Original delays
        
        Returns:
            Masked delays
        """
        masked = []
        
        for delay in delays:
            # Add random noise
            noise = random.uniform(-self.jitter_range, self.jitter_range)
            masked_delay = max(0.01, delay + noise)
            masked.append(masked_delay)
        
        return masked
    
    def add_dummy_timing(self, count: int) -> List[float]:
        """Generate dummy timing to mask real patterns"""
        return [self.get_next_delay() for _ in range(count)]


class FlowCorrelationResistance:
    """
    Resist flow correlation analysis
    
    Prevents linking packets from the same flow.
    """
    
    def __init__(self):
        self.flow_ids: Dict[str, int] = {}
        self.rotation_interval = 60.0  # Rotate flow IDs every 60 seconds
        self.last_rotation = time.time()
    
    def get_flow_id(self, source: str, destination: str) -> int:
        """
        Get flow ID for source-destination pair
        
        Rotates periodically to prevent correlation.
        """
        flow_key = f"{source}:{destination}"
        
        # Rotate flow IDs periodically
        if time.time() - self.last_rotation > self.rotation_interval:
            self.flow_ids.clear()
            self.last_rotation = time.time()
        
        if flow_key not in self.flow_ids:
            # Generate random flow ID
            self.flow_ids[flow_key] = random.randint(1, 0xFFFFFFFF)
        
        return self.flow_ids[flow_key]
    
    def randomize_flow_id(self) -> int:
        """Generate random flow ID"""
        return random.randint(1, 0xFFFFFFFF)
    
    def should_rotate(self) -> bool:
        """Check if flow IDs should be rotated"""
        return time.time() - self.last_rotation > self.rotation_interval


class ProtocolFingerprintResistance:
    """
    Resist protocol fingerprinting
    
    Prevents identification based on protocol characteristics.
    """
    
    def __init__(self):
        self.fingerprint_variations = [
            'mozilla_firefox',
            'chrome',
            'safari',
            'edge',
            'curl',
            'wget',
        ]
    
    def randomize_header_fields(self) -> Dict[str, bytes]:
        """Randomize protocol header fields"""
        return {
            'user_agent': random.choice(self.fingerprint_variations).encode(),
            'ttl': struct.pack('B', random.randint(32, 255)),
            'window_size': struct.pack('>H', random.randint(1024, 65535)),
        }
    
    def add_fingerprint_noise(self, packet: bytes) -> bytes:
        """Add noise to prevent fingerprinting"""
        # Add random padding
        padding_size = random.randint(0, 16)
        import os
        padding = os.urandom(padding_size)
        return packet + padding


class TrafficAnalysisResistance:
    """
    Main traffic analysis resistance manager
    
    Coordinates all resistance techniques.
    """
    
    def __init__(self, level: ResistanceLevel = ResistanceLevel.INTERMEDIATE):
        self.level = level
        self.size_normalizer = PacketSizeNormalizer()
        self.timing_masker = TimingPatternMasker()
        self.flow_resistance = FlowCorrelationResistance()
        self.fingerprint_resistance = ProtocolFingerprintResistance()
        self.dummy_traffic_rate = 0.1 if level >= ResistanceLevel.ADVANCED else 0.0
    
    def process_packets(
        self,
        packets: List[bytes],
        add_dummy: bool = True
    ) -> Tuple[List[bytes], List[float]]:
        """
        Process packets for analysis resistance
        
        Args:
            packets: Original packets
            add_dummy: Whether to add dummy traffic
        
        Returns:
            (processed_packets, delays)
        """
        processed = []
        delays = []
        
        # Normalize packet sizes
        for packet in packets:
            normalized = self.size_normalizer.normalize(packet)
            processed.extend(normalized)
        
        # Generate delays
        for _ in processed:
            delays.append(self.timing_masker.get_next_delay())
        
        # Add dummy traffic
        if add_dummy and self.dummy_traffic_rate > 0:
            dummy_count = int(len(processed) * self.dummy_traffic_rate)
            dummy_packets = self.size_normalizer.add_dummy_packets(dummy_count)
            dummy_delays = self.timing_masker.add_dummy_timing(len(dummy_packets))
            
            # Interleave dummy packets
            for i, (dummy_pkt, dummy_delay) in enumerate(zip(dummy_packets, dummy_delays)):
                insert_pos = random.randint(0, len(processed))
                processed.insert(insert_pos, dummy_pkt)
                delays.insert(insert_pos, dummy_delay)
        
        # Mask timing patterns
        if self.level >= ResistanceLevel.ADVANCED:
            delays = self.timing_masker.mask_timing_pattern(delays)
        
        return processed, delays
    
    def get_flow_id(self, source: str, destination: str) -> int:
        """Get flow ID with correlation resistance"""
        return self.flow_resistance.get_flow_id(source, destination)
    
    def randomize_headers(self) -> Dict[str, bytes]:
        """Randomize protocol headers"""
        return self.fingerprint_resistance.randomize_header_fields()
    
    def add_fingerprint_noise(self, packet: bytes) -> bytes:
        """Add noise to prevent fingerprinting"""
        return self.fingerprint_resistance.add_fingerprint_noise(packet)
