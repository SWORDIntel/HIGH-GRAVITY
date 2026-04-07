"""
MEMSHADOW TLS Integration
=========================

Integrates MEMSHADOW protocol with TLS extensions for extended flags.
Extended flags are negotiated once per TLS session via custom TLS extension.

Based on ARTICBASTION TLS obfuscator implementation.
"""

import ssl
import socket
import struct
import logging
from typing import Optional, Dict, Any
from .tls_extension import (
    TLSExtensionHandler,
    TLSConnectionContext,
    MEMSHADOW_TLS_EXTENSION_ID,
    get_extension_handler
)
from .dsmil_protocol import MessageFlags

logger = logging.getLogger(__name__)


class MemshadowTLSContext:
    """
    TLS context for MEMSHADOW protocol with extended flags support.
    Manages TLS connections with custom extensions for flag negotiation.
    """
    
    def __init__(self, extension_key: Optional[bytes] = None):
        """
        Initialize MEMSHADOW TLS context.
        
        Args:
            extension_key: HMAC key for extension validation
        """
        self.extension_handler = TLSExtensionHandler(extension_key)
        self.connection_contexts: Dict[str, TLSConnectionContext] = {}
    
    def create_client_context(self, hostname: str, port: int = 443) -> TLSConnectionContext:
        """
        Create TLS connection context for client.
        
        Args:
            hostname: Server hostname
            port: Server port
            
        Returns:
            TLSConnectionContext with negotiated flags
        """
        context = TLSConnectionContext()
        
        # Create SSL context with custom extension support
        ssl_context = ssl.create_default_context()
        
        # Note: Actual TLS extension injection happens at packet level
        # (requires netfilter/scapy for full implementation)
        # This is a simplified version for application-level integration
        
        # Store context
        conn_id = f"{hostname}:{port}"
        self.connection_contexts[conn_id] = context
        
        logger.info(f"Created TLS context for {conn_id}")
        return context
    
    def get_connection_flags(self, connection_id: str) -> int:
        """
        Get extended flags for a connection.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Extended flags (32-bit)
        """
        context = self.connection_contexts.get(connection_id)
        if context and context.negotiated:
            return context.extended_flags
        return 0
    
    def set_connection_flags(self, connection_id: str, flags: int):
        """
        Set extended flags for a connection (from TLS extension negotiation).
        
        Args:
            connection_id: Connection identifier
            flags: Extended flags (32-bit)
        """
        if connection_id not in self.connection_contexts:
            self.connection_contexts[connection_id] = TLSConnectionContext()
        
        self.connection_contexts[connection_id].set_negotiated_flags(flags)
        logger.debug(f"Set flags for {connection_id}: 0x{flags:08X}")


def get_tls_context() -> MemshadowTLSContext:
    """Get or create global TLS context"""
    global _tls_context
    if '_tls_context' not in globals():
        _tls_context = MemshadowTLSContext()
    return _tls_context


def create_client_hello_extension(extended_flags: int) -> bytes:
    """
    Create TLS ClientHello extension for MEMSHADOW flags.
    
    Args:
        extended_flags: Extended flags to send (32-bit)
        
    Returns:
        TLS extension bytes ready for ClientHello
    """
    handler = get_extension_handler()
    return handler.create_client_extension(extended_flags)


def create_server_hello_extension(negotiated_flags: int) -> bytes:
    """
    Create TLS ServerHello extension for MEMSHADOW flags.
    
    Args:
        negotiated_flags: Negotiated flags (32-bit)
        
    Returns:
        TLS extension bytes ready for ServerHello
    """
    handler = get_extension_handler()
    return handler.create_server_extension(negotiated_flags)


def parse_tls_extension(extension_data: bytes) -> Optional[Dict[str, Any]]:
    """
    Parse TLS extension data.
    
    Args:
        extension_data: Extension data (without type/length header)
        
    Returns:
        Parsed extension data or None
    """
    handler = get_extension_handler()
    return handler.parse_extension(extension_data)
