"""
Dual-Stream Transmission

Separates headers from payload into alternate streams for enhanced obscurity.
Headers transmitted separately allow payload to be completely opaque.
"""

import struct
import hashlib
from typing import Tuple, Optional, Dict
from dataclasses import dataclass

from src.pegasus.network.msnet.dsmil_protocol import (
    MemshadowHeader,
    MemshadowMessage,
    MessageFlags,
    MessageType,
    HEADER_SIZE,
)


@dataclass
class StreamPair:
    """Pair of header and payload streams"""
    header_stream: bytes  # Headers only (telemetry stream)
    payload_stream: bytes  # Payloads only (data stream)
    stream_id: bytes  # 16-byte stream identifier for reconstruction


class DualStreamManager:
    """
    Manages dual-stream transmission.
    
    Separates headers from payloads:
    - Header stream: Contains all headers (looks like telemetry/control)
    - Payload stream: Contains all payloads (completely opaque)
    
    Headers and payloads linked by stream_id for reconstruction.
    """
    
    def __init__(self):
        """Initialize dual-stream manager"""
        self._streams: Dict[bytes, Dict] = {}  # stream_id -> stream state
        self._pending_headers: Dict[bytes, MemshadowHeader] = {}  # stream_id -> header
        self._pending_payloads: Dict[bytes, bytes] = {}  # stream_id -> payload
    
    def separate_message(self, message: MemshadowMessage) -> Tuple[bytes, bytes, bytes]:
        """
        Separate message into header and payload streams.
        
        Args:
            message: Message to separate
        
        Returns:
            Tuple of (stream_id, header_data, payload_data)
        """
        # Generate stream ID from message hash
        msg_hash = hashlib.sha256(message.pack()).digest()
        stream_id = msg_hash[:16]
        
        # Pack header (without payload_len to avoid revealing size)
        header_data = message.header.pack()
        
        # Payload data (completely opaque)
        payload_data = message.payload
        
        # Store for reconstruction
        self._pending_headers[stream_id] = message.header
        self._pending_payloads[stream_id] = payload_data
        
        return stream_id, header_data, payload_data
    
    def reconstruct_message(self, stream_id: bytes, header_data: Optional[bytes] = None, payload_data: Optional[bytes] = None) -> Optional[MemshadowMessage]:
        """
        Reconstruct message from separated streams.
        
        Args:
            stream_id: Stream identifier
            header_data: Header data (if received)
            payload_data: Payload data (if received)
        
        Returns:
            Reconstructed message if both parts available, None otherwise
        """
        # Store received parts
        if header_data:
            try:
                header = MemshadowHeader.unpack(header_data)
                self._pending_headers[stream_id] = header
            except Exception:
                pass
        
        if payload_data:
            self._pending_payloads[stream_id] = payload_data
        
        # Check if both parts available
        if stream_id in self._pending_headers and stream_id in self._pending_payloads:
            header = self._pending_headers[stream_id]
            payload = self._pending_payloads[stream_id]
            
            # Reconstruct message
            message = MemshadowMessage(header=header, payload=payload)
            
            # Clean up
            del self._pending_headers[stream_id]
            del self._pending_payloads[stream_id]
            
            return message
        
        return None
    
    def create_header_only_message(self, header: MemshadowHeader) -> bytes:
        """
        Create header-only message for telemetry stream.
        
        Header is packed with DUAL_STREAM flag set.
        """
        header.flags |= MessageFlags.DUAL_STREAM
        header.flags |= MessageFlags.TELEMETRY_MODE  # Headers look like telemetry
        return header.pack()
    
    def create_payload_only_chunk(self, stream_id: bytes, payload: bytes, chunk_index: int = 0) -> bytes:
        """
        Create payload-only chunk for data stream.
        
        Payload is completely opaque - no headers visible.
        """
        # Prepend stream_id and chunk_index for reconstruction
        # Format: stream_id (16) + chunk_index (4) + payload
        return stream_id + struct.pack(">I", chunk_index) + payload
