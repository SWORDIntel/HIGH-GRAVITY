"""
Protocol Obscurity and Steganography

Makes MEMSHADOW protocol traffic look like normal network traffic.
Includes automatic traffic shaping, steganography, and quantum-resistant features.
"""

import random
import struct
from typing import Tuple, Optional
from enum import IntEnum

from src.pegasus.network.msnet.dsmil_protocol import MessageFlags, MessageType


class TrafficProfile(IntEnum):
    """Traffic shaping profiles"""
    HTTP = 1  # HTTP/HTTPS traffic
    DNS = 2  # DNS queries/responses
    TLS = 3  # TLS handshake/data
    WEBSOCKET = 4  # WebSocket frames
    QUIC = 5  # QUIC packets
    RANDOM = 6  # Random padding/noise


class ObscurityManager:
    """
    Manages protocol obscurity features.
    
    Automatically selects best obfuscation method based on context.
    """
    
    def __init__(self):
        """Initialize obscurity manager"""
        self.default_profile = TrafficProfile.HTTP
    
    def shape_traffic(self, data: bytes, profile: TrafficProfile = None) -> bytes:
        """
        Shape traffic to mimic specified protocol.
        
        Args:
            data: Raw protocol data
            profile: Traffic profile (default: HTTP)
        
        Returns:
            Shaped data that looks like specified protocol
        """
        if profile is None:
            profile = self.default_profile
        
        if profile == TrafficProfile.HTTP:
            return self._shape_http(data)
        elif profile == TrafficProfile.DNS:
            return self._shape_dns(data)
        elif profile == TrafficProfile.TLS:
            return self._shape_tls(data)
        elif profile == TrafficProfile.WEBSOCKET:
            return self._shape_websocket(data)
        elif profile == TrafficProfile.QUIC:
            return self._shape_quic(data)
        else:
            return self._add_random_padding(data)
    
    def _shape_http(self, data: bytes) -> bytes:
        """Shape data to look like HTTP request/response"""
        # Wrap in HTTP-like structure
        # Format: "HTTP/1.1 200 OK\r\n" + headers + "\r\n" + data
        headers = b"Content-Type: application/octet-stream\r\n"
        headers += b"Content-Length: " + str(len(data)).encode() + b"\r\n"
        headers += b"Connection: keep-alive\r\n"
        return b"HTTP/1.1 200 OK\r\n" + headers + b"\r\n" + data
    
    def _shape_dns(self, data: bytes) -> bytes:
        """Shape data to look like DNS packet"""
        # DNS header: ID (2) + Flags (2) + Questions (2) + Answers (2) + ...
        # Simple DNS-like wrapper
        dns_id = random.randint(0, 65535)
        dns_header = struct.pack(">HHHHHH", dns_id, 0x8180, 1, 1, 0, 0)
        return dns_header + data[:512]  # DNS max 512 bytes
    
    def _shape_tls(self, data: bytes) -> bytes:
        """Shape data to look like TLS record"""
        # TLS Record: Type (1) + Version (2) + Length (2) + Data
        tls_type = 0x17  # Application Data
        tls_version = 0x0303  # TLS 1.2
        tls_length = len(data)
        return struct.pack(">BHH", tls_type, tls_version, tls_length) + data
    
    def _shape_websocket(self, data: bytes) -> bytes:
        """Shape data to look like WebSocket frame"""
        # WebSocket: FIN (1) + Opcode (4) + Mask (1) + Payload Len (7) + Mask Key (4) + Data
        fin_opcode = 0x82  # FIN + Binary
        mask = 0x80  # Masked
        payload_len = len(data)
        
        if payload_len < 126:
            header = struct.pack(">BB", fin_opcode, mask | payload_len)
        elif payload_len < 65536:
            header = struct.pack(">BBH", fin_opcode, mask | 126, payload_len)
        else:
            header = struct.pack(">BBQ", fin_opcode, mask | 127, payload_len)
        
        mask_key = random.randint(0, 0xFFFFFFFF).to_bytes(4, 'big')
        return header + mask_key + data
    
    def _shape_quic(self, data: bytes) -> bytes:
        """Shape data to look like QUIC packet"""
        # QUIC header: Flags (1) + Connection ID + Packet Number + Data
        flags = 0x40  # Long header, version
        conn_id = random.randint(0, 2**64-1).to_bytes(8, 'big')
        packet_num = random.randint(0, 2**32-1).to_bytes(4, 'big')
        return struct.pack(">B", flags) + conn_id + packet_num + data
    
    def _add_random_padding(self, data: bytes) -> bytes:
        """Add random padding to obscure size"""
        padding_size = random.randint(0, 64)
        padding = random.randbytes(padding_size)
        return data + padding
    
    def steganographic_encode(self, data: bytes, carrier: bytes) -> bytes:
        """
        Encode data steganographically in carrier.
        
        Uses LSB steganography - embeds data in least significant bits.
        """
        if len(carrier) < len(data) * 8:
            # Not enough carrier data, pad carrier
            carrier = carrier + b'\x00' * (len(data) * 8 - len(carrier))
        
        result = bytearray(carrier)
        data_bits = ''.join(format(b, '08b') for b in data)
        
        for i, bit in enumerate(data_bits):
            if i < len(result):
                # Set LSB of carrier byte
                result[i] = (result[i] & 0xFE) | int(bit)
        
        return bytes(result)
    
    def steganographic_decode(self, stego_data: bytes, expected_length: int) -> bytes:
        """Decode steganographically hidden data"""
        result = bytearray()
        bits = []
        
        for byte in stego_data[:expected_length * 8]:
            bits.append(str(byte & 0x01))
        
        # Convert bits to bytes
        for i in range(0, len(bits), 8):
            if i + 8 <= len(bits):
                byte_bits = ''.join(bits[i:i+8])
                result.append(int(byte_bits, 2))
        
        return bytes(result[:expected_length])
    
    def auto_select_profile(self, payload_size: int, message_type: MessageType) -> TrafficProfile:
        """
        Automatically select best traffic profile.
        
        Args:
            payload_size: Size of payload
            message_type: Message type
        
        Returns:
            Recommended traffic profile
        """
        # Small JSON telemetry -> HTTP
        if payload_size < 1024 and message_type in (MessageType.TELEMETRY, MessageType.CONTROL):
            return TrafficProfile.HTTP
        
        # Large data -> TLS or QUIC
        elif payload_size > 64 * 1024:
            return TrafficProfile.TLS
        
        # Medium data -> WebSocket
        elif payload_size > 1024:
            return TrafficProfile.WEBSOCKET
        
        # Default -> HTTP
        else:
            return TrafficProfile.HTTP
