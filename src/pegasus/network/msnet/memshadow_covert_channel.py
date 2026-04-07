"""
MEMSHADOW Protocol - Covert Channel Implementation

Implements advanced covert channels for stealth communication in
restricted networks, including timing channels and protocol steganography.
"""

import time
import random
import struct
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import IntEnum
from collections import deque


class CovertChannelType(IntEnum):
    """Types of covert channels"""
    TIMING = 1  # Timing-based channel
    SIZE = 2  # Packet size-based channel
    PROTOCOL = 3  # Protocol field-based channel
    STEGANOGRAPHY = 4  # Data hiding in legitimate traffic
    HYBRID = 5  # Multiple channels combined


@dataclass
class TimingChannelConfig:
    """Configuration for timing-based covert channel"""
    bit_duration: float = 0.1  # Duration for one bit (seconds)
    zero_delay: float = 0.05  # Delay for '0' bit
    one_delay: float = 0.15  # Delay for '1' bit
    jitter: float = 0.02  # Random jitter to avoid detection


class TimingCovertChannel:
    """
    Timing-based covert channel
    
    Encodes data in inter-packet timing delays.
    """
    
    def __init__(self, config: Optional[TimingChannelConfig] = None):
        self.config = config or TimingChannelConfig()
        self.last_send_time = 0.0
    
    def encode_timing(self, data: bytes) -> List[float]:
        """
        Encode data as timing delays
        
        Returns:
            List of delays between packets
        """
        delays = []
        bits = []
        
        # Convert data to bits
        for byte in data:
            for i in range(8):
                bits.append((byte >> (7 - i)) & 1)
        
        # Encode bits as delays
        for bit in bits:
            if bit == 0:
                delay = self.config.zero_delay
            else:
                delay = self.config.one_delay
            
            # Add jitter
            delay += random.uniform(-self.config.jitter, self.config.jitter)
            delay = max(0.01, delay)  # Minimum delay
            
            delays.append(delay)
        
        return delays
    
    def decode_timing(self, delays: List[float]) -> bytes:
        """
        Decode timing delays back to data
        
        Args:
            delays: List of inter-packet delays
        
        Returns:
            Decoded bytes
        """
        bits = []
        
        # Decode delays to bits
        threshold = (self.config.zero_delay + self.config.one_delay) / 2
        
        for delay in delays:
            if delay < threshold:
                bits.append(0)
            else:
                bits.append(1)
        
        # Convert bits to bytes
        data = bytearray()
        for i in range(0, len(bits), 8):
            if i + 8 <= len(bits):
                byte = 0
                for j in range(8):
                    byte |= (bits[i + j] << (7 - j))
                data.append(byte)
        
        return bytes(data)
    
    def get_next_delay(self, bit: int) -> float:
        """Get delay for next bit"""
        if bit == 0:
            delay = self.config.zero_delay
        else:
            delay = self.config.one_delay
        
        delay += random.uniform(-self.config.jitter, self.config.jitter)
        return max(0.01, delay)


class SizeCovertChannel:
    """
    Packet size-based covert channel
    
    Encodes data in packet sizes.
    """
    
    def __init__(self, min_size: int = 64, max_size: int = 1500):
        self.min_size = min_size
        self.max_size = max_size
        self.size_range = max_size - min_size
    
    def encode_size(self, data: bytes) -> List[int]:
        """
        Encode data as packet sizes
        
        Returns:
            List of packet sizes
        """
        sizes = []
        
        for byte in data:
            # Encode byte as two packet sizes (4 bits each)
            sizes.append(self.min_size + ((byte >> 4) & 0x0F) * (self.size_range // 16))
            sizes.append(self.min_size + (byte & 0x0F) * (self.size_range // 16))
        
        return sizes
    
    def decode_size(self, sizes: List[int]) -> bytes:
        """
        Decode packet sizes back to data
        
        Args:
            sizes: List of packet sizes
        
        Returns:
            Decoded bytes
        """
        data = bytearray()
        
        for i in range(0, len(sizes), 2):
            if i + 1 < len(sizes):
                # Decode two sizes to one byte
                size1 = sizes[i]
                size2 = sizes[i + 1]
                
                byte1 = ((size1 - self.min_size) * 16) // self.size_range
                byte2 = ((size2 - self.min_size) * 16) // self.size_range
                
                byte = (byte1 << 4) | byte2
                data.append(byte)
        
        return bytes(data)
    
    def pad_to_size(self, data: bytes, target_size: int) -> bytes:
        """Pad data to target size"""
        if len(data) >= target_size:
            return data[:target_size]
        
        import secrets
        padding = secrets.token_bytes(target_size - len(data))
        return data + padding


class ProtocolFieldChannel:
    """
    Protocol field-based covert channel
    
    Encodes data in protocol header fields (TTL, flags, etc.).
    """
    
    def encode_in_ttl(self, data: bytes) -> List[int]:
        """
        Encode data in TTL values
        
        Returns:
            List of TTL values
        """
        ttls = []
        
        for byte in data:
            # Encode byte in TTL (use range 32-255)
            ttl = 32 + (byte % 224)
            ttls.append(ttl)
        
        return ttls
    
    def decode_from_ttl(self, ttls: List[int]) -> bytes:
        """
        Decode data from TTL values
        
        Args:
            ttls: List of TTL values
        
        Returns:
            Decoded bytes
        """
        data = bytearray()
        
        for ttl in ttls:
            if ttl >= 32:
                byte = (ttl - 32) % 256
                data.append(byte)
        
        return bytes(data)
    
    def encode_in_flags(self, data: bytes) -> List[int]:
        """
        Encode data in TCP/IP flags
        
        Returns:
            List of flag values
        """
        flags = []
        
        for byte in data:
            # Encode byte in 8 flag combinations
            flags.append(byte & 0xFF)
        
        return flags
    
    def decode_from_flags(self, flags: List[int]) -> bytes:
        """
        Decode data from flag values
        
        Args:
            flags: List of flag values
        
        Returns:
            Decoded bytes
        """
        return bytes(flags)


class HybridCovertChannel:
    """
    Hybrid covert channel
    
    Combines multiple covert channel techniques for maximum stealth.
    """
    
    def __init__(self):
        self.timing_channel = TimingCovertChannel()
        self.size_channel = SizeCovertChannel()
        self.protocol_channel = ProtocolFieldChannel()
    
    def encode(
        self,
        data: bytes,
        use_timing: bool = True,
        use_size: bool = True,
        use_protocol: bool = False
    ) -> Dict[str, List]:
        """
        Encode data using multiple channels
        
        Returns:
            Dictionary with encoded data for each channel
        """
        encoded = {}
        
        if use_timing:
            encoded['timing'] = self.timing_channel.encode_timing(data)
        
        if use_size:
            encoded['sizes'] = self.size_channel.encode_size(data)
        
        if use_protocol:
            encoded['ttls'] = self.protocol_channel.encode_in_ttl(data)
            encoded['flags'] = self.protocol_channel.encode_in_flags(data)
        
        return encoded
    
    def decode(
        self,
        encoded: Dict[str, List],
        primary_channel: str = 'timing'
    ) -> bytes:
        """
        Decode data from multiple channels
        
        Args:
            encoded: Dictionary with encoded data
            primary_channel: Primary channel to use for decoding
        
        Returns:
            Decoded bytes
        """
        if primary_channel == 'timing' and 'timing' in encoded:
            return self.timing_channel.decode_timing(encoded['timing'])
        elif primary_channel == 'sizes' and 'sizes' in encoded:
            return self.size_channel.decode_size(encoded['sizes'])
        elif primary_channel == 'ttls' and 'ttls' in encoded:
            return self.protocol_channel.decode_from_ttl(encoded['ttls'])
        elif primary_channel == 'flags' and 'flags' in encoded:
            return self.protocol_channel.decode_from_flags(encoded['flags'])
        
        # Try any available channel
        for channel_type in ['timing', 'sizes', 'ttls', 'flags']:
            if channel_type in encoded:
                return self.decode(encoded, channel_type)
        
        return b""


class CovertChannelManager:
    """
    Main covert channel manager
    
    Coordinates all covert channel techniques.
    """
    
    def __init__(self, channel_type: CovertChannelType = CovertChannelType.HYBRID):
        self.channel_type = channel_type
        self.timing_channel = TimingCovertChannel()
        self.size_channel = SizeCovertChannel()
        self.protocol_channel = ProtocolFieldChannel()
        self.hybrid_channel = HybridCovertChannel()
    
    def encode(
        self,
        data: bytes,
        channel_type: Optional[CovertChannelType] = None
    ) -> Dict[str, List]:
        """
        Encode data using covert channel
        
        Args:
            data: Data to encode
            channel_type: Channel type to use (None = use default)
        
        Returns:
            Encoded data dictionary
        """
        channel_type = channel_type or self.channel_type
        
        if channel_type == CovertChannelType.TIMING:
            return {'timing': self.timing_channel.encode_timing(data)}
        elif channel_type == CovertChannelType.SIZE:
            return {'sizes': self.size_channel.encode_size(data)}
        elif channel_type == CovertChannelType.PROTOCOL:
            return {
                'ttls': self.protocol_channel.encode_in_ttl(data),
                'flags': self.protocol_channel.encode_in_flags(data)
            }
        elif channel_type == CovertChannelType.HYBRID:
            return self.hybrid_channel.encode(data, use_timing=True, use_size=True)
        else:
            return {'timing': self.timing_channel.encode_timing(data)}
    
    def decode(
        self,
        encoded: Dict[str, List],
        channel_type: Optional[CovertChannelType] = None
    ) -> bytes:
        """
        Decode data from covert channel
        
        Args:
            encoded: Encoded data dictionary
            channel_type: Channel type used (None = auto-detect)
        
        Returns:
            Decoded bytes
        """
        channel_type = channel_type or self.channel_type
        
        if channel_type == CovertChannelType.TIMING:
            return self.timing_channel.decode_timing(encoded.get('timing', []))
        elif channel_type == CovertChannelType.SIZE:
            return self.size_channel.decode_size(encoded.get('sizes', []))
        elif channel_type == CovertChannelType.PROTOCOL:
            if 'ttls' in encoded:
                return self.protocol_channel.decode_from_ttl(encoded['ttls'])
            elif 'flags' in encoded:
                return self.protocol_channel.decode_from_flags(encoded['flags'])
        elif channel_type == CovertChannelType.HYBRID:
            return self.hybrid_channel.decode(encoded)
        
        return b""
