"""
MEMSHADOW TLS Extension Handler
================================

Implements APT41-style TLS extensions for carrying extended flags.
Extended flags are negotiated once per TLS session, eliminating the need
for payload extension headers.

Based on ARTICBASTION TLS obfuscator implementation.
"""

import struct
import time
import hmac
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from enum import IntEnum

logger = logging.getLogger(__name__)

# MEMSHADOW Custom TLS Extension ID
# Using unassigned range: 0xFC00-0xFFFF (private use)
MEMSHADOW_TLS_EXTENSION_ID = 0xFC01  # Custom extension for MEMSHADOW flags

class TLSExtensionHandler:
    """
    Handler for MEMSHADOW TLS extensions carrying extended flags.
    
    Extension Format:
    - Extension Type: 2 bytes (0xFC01)
    - Extension Length: 2 bytes
    - Extension Data:
      - Protocol Version: 2 bytes (0x0300 = v3.0)
      - Extended Flags: 4 bytes (32-bit flags)
      - Timestamp: 4 bytes
      - HMAC: 48 bytes (SHA384)
    """
    
    def __init__(self, extension_key: Optional[bytes] = None):
        """
        Initialize TLS extension handler.
        
        Args:
            extension_key: HMAC key for extension validation (32 bytes)
        """
        self.extension_id = MEMSHADOW_TLS_EXTENSION_ID
        self.extension_key = extension_key or self._generate_key()
        self.extension_data_len = 42  # 2 + 4 + 4 + 32 = 42 bytes
        
    def _generate_key(self) -> bytes:
        """Generate random extension key"""
        return hashlib.sha384(f"memshadow-{time.time()}".encode()).digest()
    
    def create_client_extension(self, extended_flags: int, protocol_version: int = 0x0300) -> bytes:
        """
        Create TLS extension for ClientHello.
        
        Args:
            extended_flags: Extended flags to send (32-bit)
            protocol_version: Protocol version (default 0x0300 = v3.0)
            
        Returns:
            Complete TLS extension bytes
        """
        timestamp = int(time.time())
        
        # Extension data: version(2) + flags(4) + timestamp(4) + hmac(32)
        extension_data = struct.pack(">H", protocol_version)  # 2 bytes
        extension_data += struct.pack(">I", extended_flags)   # 4 bytes
        extension_data += struct.pack(">I", timestamp)        # 4 bytes
        
        # Calculate HMAC over version + flags + timestamp
        hmac_obj = hmac.new(self.extension_key, extension_data, hashlib.sha384)
        extension_data += hmac_obj.digest()  # 32 bytes
        
        # TLS Extension format: type(2) + length(2) + data
        extension = struct.pack(">HH", self.extension_id, len(extension_data))
        extension += extension_data
        
        logger.debug(f"Created ClientHello extension: flags=0x{extended_flags:08X}, len={len(extension)}")
        return extension
    
    def create_server_extension(self, negotiated_flags: int, protocol_version: int = 0x0300) -> bytes:
        """
        Create TLS extension for ServerHello.
        
        Args:
            negotiated_flags: Negotiated extended flags (32-bit)
            protocol_version: Protocol version (default 0x0300 = v3.0)
            
        Returns:
            Complete TLS extension bytes
        """
        timestamp = int(time.time())
        
        # Extension data: version(2) + flags(4) + timestamp(4) + hmac(32)
        extension_data = struct.pack(">H", protocol_version)  # 2 bytes
        extension_data += struct.pack(">I", negotiated_flags)  # 4 bytes
        extension_data += struct.pack(">I", timestamp)        # 4 bytes
        
        # Calculate HMAC over version + flags + timestamp
        hmac_obj = hmac.new(self.extension_key, extension_data, hashlib.sha384)
        extension_data += hmac_obj.digest()  # 32 bytes
        
        # TLS Extension format: type(2) + length(2) + data
        extension = struct.pack(">HH", self.extension_id, len(extension_data))
        extension += extension_data
        
        logger.debug(f"Created ServerHello extension: flags=0x{negotiated_flags:08X}, len={len(extension)}")
        return extension
    
    def parse_extension(self, extension_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse TLS extension data.
        
        Args:
            extension_data: Extension data (without type/length header)
            
        Returns:
            Dict with parsed extension data or None if invalid
        """
        if len(extension_data) < 42:
            logger.error(f"Extension data too short: {len(extension_data)} bytes")
            return None
        
        try:
            # Parse extension data
            offset = 0
            protocol_version = struct.unpack(">H", extension_data[offset:offset+2])[0]
            offset += 2
            
            extended_flags = struct.unpack(">I", extension_data[offset:offset+4])[0]
            offset += 4
            
            timestamp = struct.unpack(">I", extension_data[offset:offset+4])[0]
            offset += 4
            
            received_hmac = extension_data[offset:offset+32]
            
            # Verify HMAC
            data_to_verify = extension_data[:10]  # version + flags + timestamp
            expected_hmac = hmac.new(self.extension_key, data_to_verify, hashlib.sha384).digest()
            
            if not hmac.compare_digest(received_hmac, expected_hmac):
                logger.error("Extension HMAC validation failed")
                return None
            
            return {
                'protocol_version': protocol_version,
                'extended_flags': extended_flags,
                'timestamp': timestamp,
                'valid': True
            }
            
        except Exception as e:
            logger.error(f"Error parsing extension: {e}")
            return None
    
    def negotiate_flags(self, client_flags: int, server_flags: int) -> int:
        """
        Negotiate extended flags between client and server.
        
        Args:
            client_flags: Flags requested by client
            server_flags: Flags supported by server
            
        Returns:
            Negotiated flags (intersection of client and server)
        """
        # Return intersection (flags supported by both)
        negotiated = client_flags & server_flags
        logger.info(f"Flag negotiation: client=0x{client_flags:08X}, server=0x{server_flags:08X}, negotiated=0x{negotiated:08X}")
        return negotiated


class TLSConnectionContext:
    """
    Context for TLS connection with negotiated flags.
    Stores extended flags negotiated during TLS handshake.
    """
    
    def __init__(self):
        """Initialize connection context"""
        self.extended_flags = 0
        self.protocol_version = 0x0300
        self.negotiated = False
        self.timestamp = 0
    
    def set_negotiated_flags(self, flags: int, protocol_version: int = 0x0300):
        """Set negotiated extended flags"""
        self.extended_flags = flags
        self.protocol_version = protocol_version
        self.negotiated = True
        self.timestamp = int(time.time())
        logger.debug(f"Connection context: flags=0x{flags:08X}, version=0x{protocol_version:04X}")
    
    def get_all_flags(self, base_flags: int) -> int:
        """
        Get combined flags (base + extended).
        
        Args:
            base_flags: Base flags from header (8 bits)
            
        Returns:
            Combined flags (base flags in low 8 bits, extended in high bits)
        """
        return base_flags | (self.extended_flags << 8)
    
    def has_flag(self, flag: int) -> bool:
        """Check if extended flag is set"""
        return bool(self.extended_flags & flag)


# Global extension handler instance
_extension_handler: Optional[TLSExtensionHandler] = None

def get_extension_handler() -> TLSExtensionHandler:
    """Get or create global TLS extension handler"""
    global _extension_handler
    if _extension_handler is None:
        _extension_handler = TLSExtensionHandler()
    return _extension_handler


# Convenience functions
def create_client_hello_extension(extended_flags: int, protocol_version: int = 0x0300) -> bytes:
    """Create TLS ClientHello extension for MEMSHADOW flags"""
    handler = get_extension_handler()
    return handler.create_client_extension(extended_flags, protocol_version)


def create_server_hello_extension(negotiated_flags: int, protocol_version: int = 0x0300) -> bytes:
    """Create TLS ServerHello extension for MEMSHADOW flags"""
    handler = get_extension_handler()
    return handler.create_server_extension(negotiated_flags, protocol_version)


def parse_tls_extension(extension_data: bytes) -> Optional[Dict[str, Any]]:
    """Parse TLS extension data"""
    handler = get_extension_handler()
    return handler.parse_extension(extension_data)
