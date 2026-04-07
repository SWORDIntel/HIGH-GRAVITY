"""
MEMSHADOW Protocol Error Codes

Comprehensive error code enumeration with detailed documentation.
Allows precise error identification and debugging.
"""

from enum import IntEnum
from typing import Dict, Optional


class MemshadowErrorCode(IntEnum):
    """
    MEMSHADOW Protocol Error Codes
    
    Used in ERROR (0x0003) message payloads to indicate specific failure reasons.
    """
    
    # Protocol Errors (0x00xx)
    ERR_INVALID_MAGIC = 0x0001
    """Invalid magic number in message header. Expected 0x4D53485700000000."""
    
    ERR_INVALID_VERSION = 0x0002
    """Invalid or unsupported protocol version. Version negotiation failed."""
    
    ERR_INVALID_HEADER = 0x0003
    """Invalid message header format or corrupted header data."""
    
    ERR_INVALID_PAYLOAD = 0x0004
    """Invalid payload format or payload length mismatch."""
    
    ERR_INVALID_MESSAGE_TYPE = 0x0005
    """Unknown or unsupported message type."""
    
    ERR_INVALID_FLAGS = 0x0006
    """Invalid or conflicting message flags."""
    
    ERR_INVALID_TIMESTAMP = 0x0007
    """Invalid timestamp (future timestamp or too old)."""
    
    ERR_MESSAGE_TOO_LARGE = 0x0008
    """Message exceeds maximum allowed size (16MB normal, 24MB with file transfer)."""
    
    ERR_MESSAGE_TOO_SMALL = 0x0009
    """Message smaller than minimum required size."""
    
    ERR_UNEXPECTED_MESSAGE = 0x000A
    """Message received in unexpected context or state."""
    
    ERR_MALFORMED_MESSAGE = 0x000B
    """Message format is malformed or corrupted."""
    
    # Authentication & Security Errors (0x01xx)
    ERR_INVALID_SIGNATURE = 0x0101
    """Message signature verification failed."""
    
    ERR_AUTHENTICATION_FAILED = 0x0102
    """Peer authentication failed (challenge-response verification)."""
    
    ERR_PEER_BLACKLISTED = 0x0103
    """Peer is blacklisted due to previous authentication failures."""
    
    ERR_ENCRYPTION_FAILED = 0x0104
    """Message encryption failed."""
    
    ERR_DECRYPTION_FAILED = 0x0105
    """Message decryption failed (wrong key or corrupted data)."""
    
    ERR_KEY_EXCHANGE_FAILED = 0x0106
    """Key exchange failed during handshake."""
    
    ERR_INVALID_PUBLIC_KEY = 0x0107
    """Invalid public key format or key verification failed."""
    
    ERR_SIGNATURE_REQUIRED = 0x0108
    """Message requires signature but none provided."""
    
    ERR_ENCRYPTION_REQUIRED = 0x0109
    """Message requires encryption but received unencrypted."""
    
    ERR_REPLAY_ATTACK = 0x010A
    """Detected replay attack (duplicate nonce/timestamp)."""
    
    # Network Errors (0x02xx)
    ERR_PEER_NOT_FOUND = 0x0201
    """Requested peer not found in network."""
    
    ERR_PEER_OFFLINE = 0x0202
    """Peer is currently offline or unreachable."""
    
    ERR_CONNECTION_FAILED = 0x0203
    """Failed to establish connection to peer."""
    
    ERR_CONNECTION_TIMEOUT = 0x0204
    """Connection attempt timed out."""
    
    ERR_NAT_TRAVERSAL_FAILED = 0x0205
    """NAT traversal failed (all methods exhausted)."""
    
    ERR_RELAY_UNAVAILABLE = 0x0206
    """No relay nodes available for connection."""
    
    ERR_NETWORK_UNREACHABLE = 0x0207
    """Network unreachable or routing failed."""
    
    ERR_ADDRESS_INVALID = 0x0208
    """Invalid transport address format."""
    
    ERR_PORT_UNAVAILABLE = 0x0209
    """Requested port is unavailable or in use."""
    
    ERR_MULTICAST_FAILED = 0x020A
    """Multicast operation failed."""
    
    ERR_VLAN_RELAY_FAILED = 0x020B
    """VLAN relay connection failed."""
    
    # Handshake Errors (0x03xx)
    ERR_HANDSHAKE_TIMEOUT = 0x0301
    """Handshake did not complete within timeout period (60 seconds)."""
    
    ERR_HANDSHAKE_IN_PROGRESS = 0x0302
    """Handshake already in progress with this peer."""
    
    ERR_HANDSHAKE_FAILED = 0x0303
    """Handshake failed (general error)."""
    
    ERR_HANDSHAKE_REJECTED = 0x0304
    """Handshake was rejected by peer."""
    
    ERR_CAPABILITY_MISMATCH = 0x0305
    """Peer capabilities do not match requirements."""
    
    ERR_VERSION_INCOMPATIBLE = 0x0306
    """Protocol version incompatible (requires upgrade)."""
    
    ERR_CHALLENGE_FAILED = 0x0307
    """Authentication challenge failed."""
    
    ERR_CHALLENGE_TIMEOUT = 0x0308
    """Authentication challenge timed out."""
    
    # Rate Limiting Errors (0x04xx)
    ERR_RATE_LIMIT_EXCEEDED = 0x0401
    """Rate limit exceeded for this operation."""
    
    ERR_ANNOUNCEMENT_RATE_LIMIT = 0x0402
    """Announcement rate limit exceeded (max 4/minute)."""
    
    ERR_QUERY_RATE_LIMIT = 0x0403
    """Query rate limit exceeded (max 10/minute)."""
    
    ERR_MESSAGE_RATE_LIMIT = 0x0404
    """Message rate limit exceeded (max 60/peer/minute)."""
    
    ERR_TOO_MANY_REQUESTS = 0x0405
    """Too many requests in short time period."""
    
    # Queue & Storage Errors (0x05xx)
    ERR_QUEUE_FULL = 0x0501
    """Message queue is full (1000 messages per peer limit)."""
    
    ERR_QUEUE_EMPTY = 0x0502
    """Message queue is empty (no messages to process)."""
    
    ERR_STORAGE_FULL = 0x0503
    """Storage is full (cannot queue more messages)."""
    
    ERR_STORAGE_ERROR = 0x0504
    """Storage operation failed."""
    
    ERR_QUEUE_TIMEOUT = 0x0505
    """Message queue operation timed out."""
    
    ERR_MESSAGE_EXPIRED = 0x0506
    """Message expired (exceeded TTL)."""
    
    # File Transfer Errors (0x06xx)
    ERR_FILE_TRANSFER_FAILED = 0x0601
    """File transfer failed."""
    
    ERR_FILE_TOO_LARGE = 0x0602
    """File exceeds maximum size (24MB with file transfer extension)."""
    
    ERR_CHUNK_MISSING = 0x0603
    """Required file chunk is missing."""
    
    ERR_CHUNK_CORRUPTED = 0x0604
    """File chunk is corrupted (checksum mismatch)."""
    
    ERR_CHUNK_OUT_OF_ORDER = 0x0605
    """File chunk received out of order."""
    
    ERR_FILE_TRANSFER_TIMEOUT = 0x0606
    """File transfer timed out."""
    
    ERR_FILE_TRANSFER_ABORTED = 0x0607
    """File transfer was aborted by peer."""
    
    ERR_COMPRESSION_FAILED = 0x0608
    """File compression failed."""
    
    ERR_DECOMPRESSION_FAILED = 0x0609
    """File decompression failed."""
    
    ERR_HARDWARE_UNAVAILABLE = 0x060A
    """Required hardware (QAT/Kanzi) unavailable for compression."""
    
    # Discovery Errors (0x07xx)
    ERR_DISCOVERY_FAILED = 0x0701
    """Peer discovery failed."""
    
    ERR_VEILID_UNAVAILABLE = 0x0702
    """Veilid discovery unavailable."""
    
    ERR_DHT_UNAVAILABLE = 0x0703
    """DHT discovery unavailable."""
    
    ERR_MULTICAST_UNAVAILABLE = 0x0704
    """Multicast discovery unavailable."""
    
    ERR_DISCOVERY_TIMEOUT = 0x0705
    """Discovery operation timed out."""
    
    ERR_BOOTSTRAP_FAILED = 0x0706
    """Bootstrap into discovery network failed."""
    
    # Memory & Resource Errors (0x08xx)
    ERR_OUT_OF_MEMORY = 0x0801
    """Out of memory (cannot allocate buffer)."""
    
    ERR_RESOURCE_EXHAUSTED = 0x0802
    """System resource exhausted."""
    
    ERR_TOO_MANY_CONNECTIONS = 0x0803
    """Too many active connections."""
    
    ERR_TOO_MANY_PEERS = 0x0804
    """Too many peers in network."""
    
    ERR_BUFFER_OVERFLOW = 0x0805
    """Buffer overflow detected."""
    
    ERR_BUFFER_UNDERFLOW = 0x0806
    """Buffer underflow detected."""
    
    # Application Errors (0x09xx)
    ERR_APPLICATION_ERROR = 0x0901
    """Application-specific error."""
    
    ERR_SERVICE_UNAVAILABLE = 0x0902
    """Requested service unavailable."""
    
    ERR_OPERATION_NOT_SUPPORTED = 0x0903
    """Operation not supported by this node."""
    
    ERR_INVALID_PARAMETERS = 0x0904
    """Invalid parameters provided."""
    
    ERR_PERMISSION_DENIED = 0x0905
    """Permission denied for this operation."""
    
    ERR_QUOTA_EXCEEDED = 0x0906
    """Quota exceeded for this operation."""
    
    # Internal Errors (0x0Axx)
    ERR_INTERNAL_ERROR = 0x0A01
    """Internal error (unexpected condition)."""
    
    ERR_NOT_IMPLEMENTED = 0x0A02
    """Feature not implemented."""
    
    ERR_STATE_INVALID = 0x0A03
    """Invalid state for this operation."""
    
    ERR_OPERATION_CANCELLED = 0x0A04
    """Operation was cancelled."""
    
    ERR_DEADLINE_EXCEEDED = 0x0A05
    """Operation deadline exceeded."""
    
    # Reserved for Future Use (0x0Bxx - 0x0FFF)
    ERR_RESERVED_START = 0x0B00
    ERR_RESERVED_END = 0x0FFF


# Error code to human-readable message mapping
ERROR_MESSAGES: Dict[int, str] = {
    # Protocol Errors
    0x0001: "Invalid magic number in message header",
    0x0002: "Invalid or unsupported protocol version",
    0x0003: "Invalid message header format",
    0x0004: "Invalid payload format or length mismatch",
    0x0005: "Unknown or unsupported message type",
    0x0006: "Invalid or conflicting message flags",
    0x0007: "Invalid timestamp (future or too old)",
    0x0008: "Message exceeds maximum size",
    0x0009: "Message smaller than minimum size",
    0x000A: "Message received in unexpected context",
    0x000B: "Message format is malformed",
    
    # Authentication & Security
    0x0101: "Message signature verification failed",
    0x0102: "Peer authentication failed",
    0x0103: "Peer is blacklisted",
    0x0104: "Message encryption failed",
    0x0105: "Message decryption failed",
    0x0106: "Key exchange failed",
    0x0107: "Invalid public key format",
    0x0108: "Message requires signature",
    0x0109: "Message requires encryption",
    0x010A: "Replay attack detected",
    
    # Network
    0x0201: "Peer not found in network",
    0x0202: "Peer is offline or unreachable",
    0x0203: "Connection establishment failed",
    0x0204: "Connection attempt timed out",
    0x0205: "NAT traversal failed",
    0x0206: "No relay nodes available",
    0x0207: "Network unreachable",
    0x0208: "Invalid transport address",
    0x0209: "Port unavailable",
    0x020A: "Multicast operation failed",
    0x020B: "VLAN relay connection failed",
    
    # Handshake
    0x0301: "Handshake timeout (60 seconds)",
    0x0302: "Handshake already in progress",
    0x0303: "Handshake failed",
    0x0304: "Handshake rejected by peer",
    0x0305: "Capability mismatch",
    0x0306: "Protocol version incompatible",
    0x0307: "Authentication challenge failed",
    0x0308: "Authentication challenge timeout",
    
    # Rate Limiting
    0x0401: "Rate limit exceeded",
    0x0402: "Announcement rate limit (max 4/minute)",
    0x0403: "Query rate limit (max 10/minute)",
    0x0404: "Message rate limit (max 60/peer/minute)",
    0x0405: "Too many requests",
    
    # Queue & Storage
    0x0501: "Message queue full (1000 per peer)",
    0x0502: "Message queue empty",
    0x0503: "Storage full",
    0x0504: "Storage operation failed",
    0x0505: "Queue operation timeout",
    0x0506: "Message expired (TTL exceeded)",
    
    # File Transfer
    0x0601: "File transfer failed",
    0x0602: "File too large (max 24MB)",
    0x0603: "Required chunk missing",
    0x0604: "Chunk corrupted (checksum mismatch)",
    0x0605: "Chunk out of order",
    0x0606: "File transfer timeout",
    0x0607: "File transfer aborted",
    0x0608: "Compression failed",
    0x0609: "Decompression failed",
    0x060A: "Hardware unavailable (QAT/Kanzi)",
    
    # Discovery
    0x0701: "Peer discovery failed",
    0x0702: "Veilid unavailable",
    0x0703: "DHT unavailable",
    0x0704: "Multicast unavailable",
    0x0705: "Discovery timeout",
    0x0706: "Bootstrap failed",
    
    # Memory & Resources
    0x0801: "Out of memory",
    0x0802: "Resource exhausted",
    0x0803: "Too many connections",
    0x0804: "Too many peers",
    0x0805: "Buffer overflow",
    0x0806: "Buffer underflow",
    
    # Application
    0x0901: "Application error",
    0x0902: "Service unavailable",
    0x0903: "Operation not supported",
    0x0904: "Invalid parameters",
    0x0905: "Permission denied",
    0x0906: "Quota exceeded",
    
    # Internal
    0x0A01: "Internal error",
    0x0A02: "Not implemented",
    0x0A03: "Invalid state",
    0x0A04: "Operation cancelled",
    0x0A05: "Deadline exceeded",
}


def get_error_message(error_code: int) -> str:
    """Get human-readable error message for error code"""
    return ERROR_MESSAGES.get(error_code, f"Unknown error code: 0x{error_code:04X}")


def create_error_message(error_code: MemshadowErrorCode, details: Optional[str] = None) -> bytes:
    """
    Create ERROR message payload
    
    Format:
    [error_code:2][details_len:2][details:variable]
    
    Args:
        error_code: Error code enum value
        details: Optional error details string
        
    Returns:
        Error message payload bytes
    """
    import struct
    
    error_code_bytes = struct.pack(">H", error_code.value)
    
    if details:
        details_bytes = details.encode('utf-8')
        details_len = len(details_bytes)
        details_len_bytes = struct.pack(">H", details_len)
        return error_code_bytes + details_len_bytes + details_bytes
    else:
        return error_code_bytes + struct.pack(">H", 0)  # No details


def parse_error_message(payload: bytes) -> tuple[int, Optional[str]]:
    """
    Parse ERROR message payload
    
    Returns:
        Tuple of (error_code, details_string or None)
    """
    import struct
    
    if len(payload) < 4:
        raise ValueError("Error message payload too short")
    
    error_code, details_len = struct.unpack(">HH", payload[:4])
    
    if details_len > 0:
        if len(payload) < 4 + details_len:
            raise ValueError("Error message payload truncated")
        details = payload[4:4+details_len].decode('utf-8')
    else:
        details = None
    
    return error_code, details
