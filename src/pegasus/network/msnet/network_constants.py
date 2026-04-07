"""
MEMSHADOW Protocol Network Constants

All network-related constants are defined here as protocol defaults.
Applications should use these constants unless overridden via config file.

Different settings (e.g., handshake timeout) will prevent nodes from joining
the same network, so changes should be coordinated.
"""

# ============================================================================
# Discovery Constants
# ============================================================================

# Cluster name (default - can be overridden)
DEFAULT_CLUSTER_NAME = "memshadow-mesh"

# Discovery announcement interval (seconds)
DISCOVERY_ANNOUNCE_INTERVAL = 15 * 60  # 15 minutes

# Discovery query interval (seconds) - Not needed, but kept for compatibility
DISCOVERY_QUERY_INTERVAL = 0  # Disabled - new peers find network via broadcasts

# Discovery grace period for multicast (seconds)
MULTICAST_GRACE_PERIOD = 300  # 5 minutes

# Discovery rate limiting
DISCOVERY_RATE_LIMIT_PER_MINUTE = 10  # Max discovery messages per minute per peer

# ============================================================================
# Handshake Constants
# ============================================================================

# Handshake timeout (seconds)
HANDSHAKE_TIMEOUT = 60  # 60 seconds

# Handshake protocol version
HANDSHAKE_PROTOCOL_VERSION = 1

# Public key format: PQC CSNA2.0 compliant ZKP
PUBLIC_KEY_FORMAT = "PQC_CSNA2_ZKP"  # Post-Quantum Cryptography CSNA2.0 Zero-Knowledge Proof

# Public key size (bytes) - CSNA2.0 ZKP format
PUBLIC_KEY_SIZE = 64  # CSNA2.0 ZKP public key size

# Signature algorithm
SIGNATURE_ALGORITHM = "CSNA2_ZKP"  # CSNA2.0 ZKP signature

# Signature size (bytes)
SIGNATURE_SIZE = 64  # CSNA2.0 ZKP signature size

# ============================================================================
# IPv4/IPv6 Constants
# ============================================================================

# IPv4 multicast group
IPV4_MULTICAST_GROUP = "239.255.42.99"

# IPv4 multicast port
IPV4_MULTICAST_PORT = 8899

# IPv4 multicast TTL
# TTL values:
#   1 = Same host
#   2 = Same subnet (default for LAN discovery)
#   >2 = Routed (for wider area)
IPV4_MULTICAST_TTL = 2  # Local subnet only

# IPv6 multicast group (link-local all nodes)
IPV6_MULTICAST_GROUP = "FF02::1"

# IPv6 multicast port
IPV6_MULTICAST_PORT = 8899

# IPv6 multicast scope
# Scope values:
#   1 = Interface-local (same interface)
#   2 = Link-local (same link/subnet) - DEFAULT
#   5 = Site-local (same site/organization)
#   8 = Organization-local
#   E = Global
IPV6_MULTICAST_SCOPE = 2  # Link-local (same as IPv4 TTL=2)

# IPv6 multicast scope explanation:
# - Link-local (2): Packets stay on local network segment, not routed beyond router
# - Site-local (5): Packets can be routed within organization but not to internet
# - Global (E): Packets can be routed anywhere on internet
# For discovery, link-local (2) is appropriate for LAN discovery

# Dual-stack preference
PREFER_IPV6 = True  # Prefer IPv6 if both available

# ============================================================================
# Transport Constants
# ============================================================================

# TCP/UDP port base
TRANSPORT_PORT_BASE = 8890

# TCP port offset
TCP_PORT_OFFSET = 0  # TCP on base port

# UDP port offset
UDP_PORT_OFFSET = 1  # UDP on base+1 port

# Message size threshold for TCP (bytes)
# Messages larger than this use TCP, smaller use UDP
TCP_SIZE_THRESHOLD = 1024  # 1 KB

# Use both TCP and UDP in parallel
USE_PARALLEL_TRANSPORT = True

# UDP ACK timeout (seconds) - if relegated to UDP only
UDP_ACK_TIMEOUT = 5

# UDP retransmission attempts
UDP_MAX_RETRIES = 3

# ============================================================================
# NAT Traversal Constants
# ============================================================================

# NAT traversal method priority (sequential, not parallel)
# Order: Try methods in this sequence until one succeeds
NAT_TRAVERSAL_METHODS = [
    "direct",      # 1. Try direct connection first
    "mesh_relay",  # 2. Use mesh network relay (our infrastructure)
    "stun",        # 3. STUN for NAT mapping discovery
    "turn",        # 4. TURN relay (public servers)
]

# STUN servers (public, no infrastructure needed)
STUN_SERVERS = [
    ("stun.l.google.com", 19302),
    ("stun1.l.google.com", 19302),
    ("stun.stunprotocol.org", 3478),
]

# TURN servers (public relays)
TURN_SERVERS = [
    {
        "host": "stun.l.google.com",
        "port": 19302,
        "username": None,  # Public TURN servers may not require auth
        "password": None,
    },
    {
        "host": "stun.stunprotocol.org",
        "port": 3478,
        "username": None,
        "password": None,
    },
]

# UPnP discovery timeout (seconds)
UPNP_DISCOVERY_TIMEOUT = 5

# Mesh relay discovery timeout (seconds)
MESH_RELAY_DISCOVERY_TIMEOUT = 10

# ============================================================================
# Multicast Strategy Constants
# ============================================================================

# Use multicast for announcements
USE_MULTICAST_FOR_ANNOUNCEMENTS = True

# Use unicast for data
USE_UNICAST_FOR_DATA = True

# Continue multicast during grace period
MULTICAST_GRACE_PERIOD_ENABLED = True

# Continue multicast if peer not connected to broader network
MULTICAST_IF_PEER_ISOLATED = True

# ============================================================================
# Security Constants
# ============================================================================

# Verify signatures on all messages
VERIFY_ALL_SIGNATURES = True

# Rate limit discovery messages
RATE_LIMIT_DISCOVERY = True

# Maximum discovery messages per peer per minute
MAX_DISCOVERY_MESSAGES_PER_MINUTE = 10

# ============================================================================
# Error Handling Constants
# ============================================================================

# Retry discovery on failure (seconds)
DISCOVERY_RETRY_INTERVAL = 60  # Retry every minute

# Maximum retry attempts before giving up
MAX_DISCOVERY_RETRIES = 10

# Continue in standalone mode if discovery fails
CONTINUE_STANDALONE_ON_FAILURE = True

# ============================================================================
# Protocol Version
# ============================================================================

NETWORK_PROTOCOL_VERSION = 1
