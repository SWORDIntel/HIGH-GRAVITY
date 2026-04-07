"""
MEMSHADOW Protocol Network Constants

All network-related constants baked into the protocol specification.
These should be consistent across all implementations.

Optional override via config file is supported, but different settings
may prevent nodes from joining the network.
"""

from typing import List, Optional

# ============================================================================
# Cluster Configuration
# ============================================================================

# Protocol-defined cluster name (baked into protocol)
CLUSTER_NAME = "MSHW"

# Cluster name hash (for DHT keys)
CLUSTER_NAME_HASH = None  # Computed at runtime


# ============================================================================
# Discovery Configuration
# ============================================================================

# Announcement interval (seconds)
DISCOVERY_ANNOUNCE_INTERVAL = 15 * 60  # 15 minutes

# Query interval (seconds) - not normally needed as new peers broadcast
DISCOVERY_QUERY_INTERVAL = 30 * 60  # 30 minutes (fallback only)

# Grace period for multicast after peer discovery (seconds)
MULTICAST_GRACE_PERIOD = 300  # 5 minutes

# Discovery timeout (seconds)
DISCOVERY_TIMEOUT = 60


# ============================================================================
# Handshake Configuration
# ============================================================================

# Handshake protocol version
HANDSHAKE_VERSION = 1

# Handshake timeout (seconds)
HANDSHAKE_TIMEOUT = 60

# Public key format: PQC CSNA2.0 compliant ZKP
# CSNA2.0 = Cryptographic Suite for Network Applications 2.0
PUBLIC_KEY_FORMAT = "PQC_CSNA2.0_ZKP"

# Signature algorithm: PQC CSNA2.0 compliant
SIGNATURE_ALGORITHM = "PQC_CSNA2.0"


# ============================================================================
# Multicast Configuration
# ============================================================================

# IPv4 Multicast
MULTICAST_IPV4_GROUP = "239.255.42.99"
MULTICAST_IPV4_PORT = 8899
MULTICAST_IPV4_TTL = 2  # Local subnet only (0-255)

# IPv6 Multicast
MULTICAST_IPV6_GROUP = "FF02::42:99"  # Link-local scope
MULTICAST_IPV6_PORT = 8899
MULTICAST_IPV6_SCOPE = 2  # Link-local (see IPv6_SCOPE_* constants)

# IPv6 Multicast Scope Levels
# Scope 1: Interface-local (loopback)
# Scope 2: Link-local (same network segment) - DEFAULT
# Scope 3: Admin-local (administratively configured)
# Scope 4: Site-local (same site/organization)
# Scope 5: Organization-local (same organization)
# Scope 8: Global (entire internet)

IPv6_SCOPE_INTERFACE_LOCAL = 1
IPv6_SCOPE_LINK_LOCAL = 2  # Default for MEMSHADOW
IPv6_SCOPE_ADMIN_LOCAL = 3
IPv6_SCOPE_SITE_LOCAL = 4
IPv6_SCOPE_ORGANIZATION_LOCAL = 5
IPv6_SCOPE_GLOBAL = 8

# TTL vs IPv6 Scope Explanation:
# IPv4 TTL: Maximum number of router hops (0-255)
#   - TTL=1: Same network segment only
#   - TTL=2: Local subnet (default for MEMSHADOW)
#   - TTL>2: Can traverse routers
# IPv6 Scope: Administrative boundary (not hop count)
#   - Scope 2 (link-local): Same network segment (like TTL=1-2)
#   - Scope 4 (site-local): Same organization (like TTL>2 but bounded)
#   - Scope 8 (global): Entire internet (like TTL=255)


# ============================================================================
# Transport Configuration
# ============================================================================

# Use both TCP and UDP in parallel
USE_PARALLEL_TCP_UDP = True

# Message size limits
MAX_PAYLOAD_SIZE_NORMAL = 16 * 1024 * 1024  # 16MB normal payload
MAX_PAYLOAD_SIZE_FILE_TRANSFER = 24 * 1024 * 1024  # 24MB with file transfer extension
MAX_HEADER_SIZE = 32  # Fixed header size
MAX_MESSAGE_SIZE_NORMAL = MAX_HEADER_SIZE + MAX_PAYLOAD_SIZE_NORMAL
MAX_MESSAGE_SIZE_FILE_TRANSFER = MAX_HEADER_SIZE + MAX_PAYLOAD_SIZE_FILE_TRANSFER

# Message size threshold for TCP (bytes)
# Messages smaller than this can use UDP
TCP_SIZE_THRESHOLD = 1024  # 1 KB

# UDP ACK timeout (seconds) - when relegated to UDP only
UDP_ACK_TIMEOUT = 5

# UDP retransmission attempts
UDP_MAX_RETRIES = 3


# ============================================================================
# NAT Traversal Configuration
# ============================================================================

# NAT traversal method priority (try sequentially)
# 1 = highest priority, 5 = lowest priority
NAT_METHOD_PRIORITY = {
    "direct": 1,           # Direct connection (always try first)
    "mesh_relay": 2,       # Mesh network relay (our infrastructure)
    "stun": 3,             # STUN (public servers)
    "turn": 4,             # TURN relay (public servers)
    "upnp": 5,             # UPnP port forwarding (last resort - security risk)
}

# STUN servers (public, no infrastructure needed)
STUN_SERVERS = [
    ("stun.l.google.com", 19302),
    ("stun1.l.google.com", 19302),
    ("stun2.l.google.com", 19302),
    ("stun.stunprotocol.org", 3478),
]

# TURN servers (public, last resort)
TURN_SERVERS = [
    ("turn.anyfirewall.com", 3478),
    ("turn.bistri.com", 80),
    ("turn.voiparound.com", 3478),
]

# TURN credentials (if required - many public servers don't require)
TURN_USERNAME = None
TURN_PASSWORD = None

# NAT traversal timeout (seconds)
NAT_TRAVERSAL_TIMEOUT = 30


# ============================================================================
# Security Configuration
# ============================================================================

# Verify signatures on all messages
VERIFY_ALL_SIGNATURES = True

# Rate limiting for discovery messages
DISCOVERY_RATE_LIMIT = {
    "announcements_per_minute": 4,  # Max 4 announcements per minute
    "queries_per_minute": 10,       # Max 10 queries per minute
    "messages_per_peer_per_minute": 60,  # Max 60 messages per peer per minute
}

# Blacklist duration (seconds)
BLACKLIST_DURATION = 3600  # 1 hour


# ============================================================================
# Error Handling Configuration
# ============================================================================

# Retry intervals (seconds)
RETRY_INTERVALS = {
    "discovery": 60,        # Retry discovery every 60s
    "handshake": 30,        # Retry handshake every 30s
    "connection": 10,       # Retry connection every 10s
}

# Max retry attempts
MAX_RETRIES = {
    "discovery": None,      # Infinite retries (continue working alone)
    "handshake": 3,        # 3 attempts
    "connection": 5,       # 5 attempts
}


# ============================================================================
# IPv4/IPv6 Dual-Stack Configuration
# ============================================================================

# Prefer IPv6 when both available
PREFER_IPV6 = True

# Use both IPv4 and IPv6 simultaneously if possible
USE_DUAL_STACK_PARALLEL = True

# Fallback to IPv4 if IPv6 fails
FALLBACK_TO_IPV4 = True


# ============================================================================
# Capabilities Flags
# ============================================================================

# Capability bit flags (for handshake)
CAPABILITY_IPV4 = 0x0001
CAPABILITY_IPV6 = 0x0002
CAPABILITY_MULTICAST = 0x0004
CAPABILITY_VEILID = 0x0008
CAPABILITY_DHT = 0x0010
CAPABILITY_TOR = 0x0020
CAPABILITY_RELAY = 0x0040
CAPABILITY_PQC_ENCRYPTION = 0x0080
CAPABILITY_COMPRESSION = 0x0100
CAPABILITY_TCP = 0x0200
CAPABILITY_UDP = 0x0400
CAPABILITY_STUN = 0x0800
CAPABILITY_TURN = 0x1000
CAPABILITY_UPNP = 0x2000


# ============================================================================
# Helper Functions
# ============================================================================

def get_cluster_name_hash() -> bytes:
    """Get hash of cluster name for DHT keys"""
    import hashlib
    global CLUSTER_NAME_HASH
    if CLUSTER_NAME_HASH is None:
        CLUSTER_NAME_HASH = hashlib.sha256(CLUSTER_NAME.encode()).digest()
    return CLUSTER_NAME_HASH


from typing import List

def get_nat_methods_ordered() -> List[str]:
    """Get NAT traversal methods in priority order"""
    return sorted(
        NAT_METHOD_PRIORITY.keys(),
        key=lambda x: NAT_METHOD_PRIORITY[x]
    )


def is_capability_supported(capabilities: int, flag: int) -> bool:
    """Check if a capability flag is set"""
    return (capabilities & flag) != 0
