"""
Telemetry Header - Ultra-lightweight header for JSON telemetry

16-byte header optimized for small JSON payloads.
Used when TELEMETRY_MODE flag is set.
"""

import struct
from dataclasses import dataclass
from enum import IntEnum

from src.pegasus.network.msnet.dsmil_protocol import MessageType, Priority, MessageFlags, TELEMETRY_MAGIC, TELEMETRY_HEADER_SIZE


@dataclass
class TelemetryHeader:
    """
    Minimal telemetry header (16 bytes).
    
    Wire format (big-endian):
        magic         : 4 bytes - Telemetry magic (0x53484144 "SHAD")
        msg_type      : 2 bytes - Message type
        priority      : 1 byte  - Priority (0-4)
        flags         : 1 byte  - Flags (low byte only)
        payload_len   : 4 bytes - Payload length (uint32, max 4GB)
        sequence      : 4 bytes - Sequence number (for ordering)
    
    Total: 16 bytes (50% smaller than standard header)
    """
    msg_type: MessageType
    priority: Priority = Priority.NORMAL
    flags: MessageFlags = MessageFlags.NONE
    payload_len: int = 0
    sequence: int = 0
    
    _FORMAT = ">IHBBII"
    _SIZE = struct.calcsize(_FORMAT)  # 16 bytes
    
    def pack(self) -> bytes:
        """Pack telemetry header to binary (16 bytes)"""
        return struct.pack(
            self._FORMAT,
            TELEMETRY_MAGIC,
            int(self.msg_type),
            int(self.priority),
            int(self.flags) & 0xFF,  # Only low byte
            self.payload_len,
            self.sequence,
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> "TelemetryHeader":
        """Unpack telemetry header from binary"""
        if len(data) < cls._SIZE:
            raise ValueError(f"Telemetry header too short: {len(data)} bytes, expected {cls._SIZE}")
        
        magic, msg_type, priority, flags, payload_len, sequence = struct.unpack(
            cls._FORMAT, data[:cls._SIZE]
        )
        
        if magic != TELEMETRY_MAGIC:
            raise ValueError(f"Invalid telemetry magic: 0x{magic:08X}")
        
        return cls(
            msg_type=MessageType(msg_type),
            priority=Priority(priority),
            flags=MessageFlags(flags),
            payload_len=payload_len,
            sequence=sequence,
        )
