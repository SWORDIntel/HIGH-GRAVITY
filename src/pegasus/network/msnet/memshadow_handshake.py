"""
MEMSHADOW Handshake Protocol Implementation

Handshake message format (0x0004) with variable payload supporting:
- PQC CSNA2.0 compliant ZKP public keys
- Full node capabilities advertisement
- Signature verification
"""

import struct
import json
import time
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set
from enum import IntFlag

logger = logging.getLogger(__name__)

from .dsmil_protocol import MemshadowHeader, MessageType, Priority, MessageFlags
from .memshadow_network_constants import (
    HANDSHAKE_VERSION,
    HANDSHAKE_TIMEOUT,
    PUBLIC_KEY_FORMAT,
    SIGNATURE_ALGORITHM,
    CAPABILITY_IPV4,
    CAPABILITY_IPV6,
    CAPABILITY_MULTICAST,
    CAPABILITY_VEILID,
    CAPABILITY_DHT,
    CAPABILITY_TOR,
    CAPABILITY_RELAY,
    CAPABILITY_PQC_ENCRYPTION,
    CAPABILITY_COMPRESSION,
    CAPABILITY_TCP,
    CAPABILITY_UDP,
    CAPABILITY_STUN,
    CAPABILITY_TURN,
    CAPABILITY_UPNP,
)


class HandshakeFlags(IntFlag):
    """Handshake-specific flags"""
    INIT = 0x01           # Initial handshake
    RESPONSE = 0x02       # Handshake response
    ACK = 0x04           # Handshake acknowledgment
    PQC_KEY_EXCHANGE = 0x08  # PQC key exchange included
    CAPABILITIES_FULL = 0x10  # Full capabilities advertised


@dataclass
class HandshakePayload:
    """
    Handshake payload structure (variable size)
    
    Format:
    - uint8_t  handshake_version
    - uint8_t  handshake_flags
    - uint16_t capabilities_flags
    - uint16_t supported_protocols
    - uint8_t  node_id_len
    - char     node_id[node_id_len]
    - uint8_t  public_key_format_len
    - char     public_key_format[public_key_format_len]
    - uint16_t public_key_len
    - uint8_t  public_key[public_key_len]  # PQC CSNA2.0 ZKP format
    - uint16_t transport_address_len
    - char     transport_address[transport_address_len]
    - uint8_t  mesh_address_len
    - char     mesh_address[mesh_address_len]
    - uint32_t nonce
    - uint16_t signature_len
    - uint8_t  signature[signature_len]
    """
    handshake_version: int = HANDSHAKE_VERSION
    handshake_flags: int = 0
    capabilities_flags: int = 0
    supported_protocols: int = 0x0003  # Protocol version 3
    node_id: str = ""
    public_key_format: str = PUBLIC_KEY_FORMAT
    public_key: bytes = b""
    transport_address: str = ""  # "ip:port" or "ipv6:port"
    mesh_address: str = ""
    nonce: int = 0
    signature: bytes = b""
    
    # Additional capabilities (full advertisement)
    capabilities_detail: Dict[str, any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize nonce if not set"""
        if self.nonce == 0:
            self.nonce = int(time.time() * 1e6) & 0xFFFFFFFF  # 32-bit nonce
    
    def pack(self) -> bytes:
        """Pack handshake payload to binary"""
        # Encode strings
        node_id_bytes = self.node_id.encode('utf-8')
        public_key_format_bytes = self.public_key_format.encode('utf-8')
        transport_address_bytes = self.transport_address.encode('utf-8')
        mesh_address_bytes = self.mesh_address.encode('utf-8')
        
        # Pack capabilities detail as JSON
        capabilities_detail_json = json.dumps(self.capabilities_detail).encode('utf-8')
        
        # Calculate sizes
        node_id_len = len(node_id_bytes)
        public_key_format_len = len(public_key_format_bytes)
        public_key_len = len(self.public_key)
        transport_address_len = len(transport_address_bytes)
        mesh_address_len = len(mesh_address_bytes)
        signature_len = len(self.signature)
        capabilities_detail_len = len(capabilities_detail_json)
        
        # Pack header
        header = struct.pack(
            ">BBHHH",  # version, flags, capabilities, protocols, node_id_len
            self.handshake_version,
            self.handshake_flags,
            self.capabilities_flags,
            self.supported_protocols,
            node_id_len,
        )
        
        # Pack variable fields
        payload = (
            header +
            node_id_bytes +
            struct.pack(">H", public_key_format_len) +
            public_key_format_bytes +
            struct.pack(">H", public_key_len) +
            self.public_key +
            struct.pack(">H", transport_address_len) +
            transport_address_bytes +
            struct.pack(">B", mesh_address_len) +
            mesh_address_bytes +
            struct.pack(">I", self.nonce) +
            struct.pack(">H", capabilities_detail_len) +
            capabilities_detail_json +
            struct.pack(">H", signature_len) +
            self.signature
        )
        
        return payload
    
    @classmethod
    def unpack(cls, data: bytes) -> "HandshakePayload":
        """Unpack handshake payload from binary"""
        offset = 0
        
        # Unpack header
        if len(data) < 7:
            raise ValueError("Handshake payload too short")
        
        (
            handshake_version,
            handshake_flags,
            capabilities_flags,
            supported_protocols,
            node_id_len,
        ) = struct.unpack(">BBHHH", data[offset:offset+7])
        offset += 7
        
        # Unpack node_id
        if len(data) < offset + node_id_len:
            raise ValueError("Handshake payload truncated at node_id")
        node_id = data[offset:offset+node_id_len].decode('utf-8')
        offset += node_id_len
        
        # Unpack public_key_format
        if len(data) < offset + 2:
            raise ValueError("Handshake payload truncated at public_key_format_len")
        public_key_format_len, = struct.unpack(">H", data[offset:offset+2])
        offset += 2
        
        if len(data) < offset + public_key_format_len:
            raise ValueError("Handshake payload truncated at public_key_format")
        public_key_format = data[offset:offset+public_key_format_len].decode('utf-8')
        offset += public_key_format_len
        
        # Unpack public_key
        if len(data) < offset + 2:
            raise ValueError("Handshake payload truncated at public_key_len")
        public_key_len, = struct.unpack(">H", data[offset:offset+2])
        offset += 2
        
        if len(data) < offset + public_key_len:
            raise ValueError("Handshake payload truncated at public_key")
        public_key = data[offset:offset+public_key_len]
        offset += public_key_len
        
        # Unpack transport_address
        if len(data) < offset + 2:
            raise ValueError("Handshake payload truncated at transport_address_len")
        transport_address_len, = struct.unpack(">H", data[offset:offset+2])
        offset += 2
        
        if len(data) < offset + transport_address_len:
            raise ValueError("Handshake payload truncated at transport_address")
        transport_address = data[offset:offset+transport_address_len].decode('utf-8')
        offset += transport_address_len
        
        # Unpack mesh_address
        if len(data) < offset + 1:
            raise ValueError("Handshake payload truncated at mesh_address_len")
        mesh_address_len, = struct.unpack(">B", data[offset:offset+1])
        offset += 1
        
        if len(data) < offset + mesh_address_len:
            raise ValueError("Handshake payload truncated at mesh_address")
        mesh_address = data[offset:offset+mesh_address_len].decode('utf-8')
        offset += mesh_address_len
        
        # Unpack nonce
        if len(data) < offset + 4:
            raise ValueError("Handshake payload truncated at nonce")
        nonce, = struct.unpack(">I", data[offset:offset+4])
        offset += 4
        
        # Unpack capabilities_detail
        if len(data) < offset + 2:
            raise ValueError("Handshake payload truncated at capabilities_detail_len")
        capabilities_detail_len, = struct.unpack(">H", data[offset:offset+2])
        offset += 2
        
        if len(data) < offset + capabilities_detail_len:
            raise ValueError("Handshake payload truncated at capabilities_detail")
        capabilities_detail_json = data[offset:offset+capabilities_detail_len].decode('utf-8')
        capabilities_detail = json.loads(capabilities_detail_json)
        offset += capabilities_detail_len
        
        # Unpack signature
        if len(data) < offset + 2:
            raise ValueError("Handshake payload truncated at signature_len")
        signature_len, = struct.unpack(">H", data[offset:offset+2])
        offset += 2
        
        if len(data) < offset + signature_len:
            raise ValueError("Handshake payload truncated at signature")
        signature = data[offset:offset+signature_len]
        offset += signature_len
        
        return cls(
            handshake_version=handshake_version,
            handshake_flags=handshake_flags,
            capabilities_flags=capabilities_flags,
            supported_protocols=supported_protocols,
            node_id=node_id,
            public_key_format=public_key_format,
            public_key=public_key,
            transport_address=transport_address,
            mesh_address=mesh_address,
            nonce=nonce,
            signature=signature,
            capabilities_detail=capabilities_detail,
        )
    
    def set_capabilities(
        self,
        ipv4: bool = True,
        ipv6: bool = True,
        multicast: bool = True,
        veilid: bool = False,
        dht: bool = True,
        tor: bool = False,
        relay: bool = True,
        pqc_encryption: bool = True,
        compression: bool = True,
        tcp: bool = True,
        udp: bool = True,
        stun: bool = True,
        turn: bool = True,
        upnp: bool = False,
        **additional_capabilities
    ):
        """Set capability flags"""
        self.capabilities_flags = 0
        
        if ipv4:
            self.capabilities_flags |= CAPABILITY_IPV4
        if ipv6:
            self.capabilities_flags |= CAPABILITY_IPV6
        if multicast:
            self.capabilities_flags |= CAPABILITY_MULTICAST
        if veilid:
            self.capabilities_flags |= CAPABILITY_VEILID
        if dht:
            self.capabilities_flags |= CAPABILITY_DHT
        if tor:
            self.capabilities_flags |= CAPABILITY_TOR
        if relay:
            self.capabilities_flags |= CAPABILITY_RELAY
        if pqc_encryption:
            self.capabilities_flags |= CAPABILITY_PQC_ENCRYPTION
        if compression:
            self.capabilities_flags |= CAPABILITY_COMPRESSION
        if tcp:
            self.capabilities_flags |= CAPABILITY_TCP
        if udp:
            self.capabilities_flags |= CAPABILITY_UDP
        if stun:
            self.capabilities_flags |= CAPABILITY_STUN
        if turn:
            self.capabilities_flags |= CAPABILITY_TURN
        if upnp:
            self.capabilities_flags |= CAPABILITY_UPNP
        
        # Store full capabilities in detail dict
        self.capabilities_detail = {
            "ipv4": ipv4,
            "ipv6": ipv6,
            "multicast": multicast,
            "veilid": veilid,
            "dht": dht,
            "tor": tor,
            "relay": relay,
            "pqc_encryption": pqc_encryption,
            "compression": compression,
            "tcp": tcp,
            "udp": udp,
            "stun": stun,
            "turn": turn,
            "upnp": upnp,
            **additional_capabilities,
        }
        self.handshake_flags |= HandshakeFlags.CAPABILITIES_FULL
    
    def sign(self, crypto: 'CNSACrypto', keypair: 'KeyPair') -> bool:
        """
        Sign handshake payload using CNSACrypto
        
        Args:
            crypto: CNSACrypto instance
            keypair: KeyPair for signing
        
        Returns:
            True if signed successfully
        """
        # Create message to sign (everything except signature)
        payload_without_sig = self.pack()[:-2]  # Remove signature_len and signature
        
        try:
            # Use CNSACrypto to sign
            signed_msg = crypto.sign(payload_without_sig, keypair)
            self.signature = signed_msg.signature
            return True
        except Exception as e:
            logger.error(f"Failed to sign handshake: {e}")
            return False
    
    def verify(self, crypto: 'CNSACrypto', public_key: bytes) -> bool:
        """
        Verify handshake signature using CNSACrypto
        
        Args:
            crypto: CNSACrypto instance
            public_key: Public key for verification
        
        Returns:
            True if signature is valid
        """
        if not self.signature:
            return False
        
        # Create message to verify (everything except signature)
        payload_without_sig = self.pack()[:-2]  # Remove signature_len and signature
        
        try:
            # Create SignedMessage for verification
            from ai.brain.security.cnsa_crypto import SignedMessage
            signed_msg = SignedMessage(
                message=payload_without_sig,
                signature=self.signature,
            )
            
            # Verify using CNSACrypto
            return crypto.verify(signed_msg, public_key)
        except Exception as e:
            logger.error(f"Failed to verify handshake: {e}")
            return False


def create_handshake_message(
    node_id: str,
    public_key: bytes,
    transport_address: str,
    mesh_address: str,
    is_init: bool = True,
    echo_nonce: Optional[int] = None,
    **capabilities
) -> bytes:
    """
    Create a MEMSHADOW handshake message
    
    Args:
        node_id: Node identifier
        public_key: PQC CSNA2.0 ZKP public key
        transport_address: Transport address (ip:port)
        mesh_address: Mesh overlay address
        is_init: True for init, False for response
        echo_nonce: Nonce to echo (for response)
        **capabilities: Capability flags
    
    Returns:
        Complete handshake message (header + payload)
    """
    payload = HandshakePayload(
        node_id=node_id,
        public_key=public_key,
        transport_address=transport_address,
        mesh_address=mesh_address,
    )
    
    if is_init:
        payload.handshake_flags = HandshakeFlags.INIT
    else:
        payload.handshake_flags = HandshakeFlags.RESPONSE
        if echo_nonce:
            payload.nonce = echo_nonce
    
    payload.set_capabilities(**capabilities)
    
    # Pack payload
    payload_bytes = payload.pack()
    
    # Create header
    header = MemshadowHeader(
        magic=0x4D53485700000000,
        version=3,
        priority=Priority.NORMAL,
        msg_type=MessageType.HANDSHAKE,
        flags=MessageFlags.ENCRYPTED | MessageFlags.REQUIRES_ACK,
        batch_count=0,
        payload_len=len(payload_bytes),
        timestamp_ns=int(time.time() * 1e9),
    )
    
    return header.pack() + payload_bytes
