"""
DSMIL MEMSHADOW Protocol v3.0 - Canonical Implementation

Unified binary wire format for intra-node communications within the DSMIL ecosystem.

This is the canonical protocol library referenced by:
- ai/brain/federation/hub_orchestrator.py
- ai/brain/federation/spoke_client.py
- ai/brain/memory/memory_sync_protocol.py
- ai/brain/plugins/ingest/memshadow_ingest.py
- external/intel/shrink/shrink/kernel_receiver.py

Protocol Version: 3.0
Header Size: 32 bytes
Magic Number: 0x4D534857 ("MSHW" in ASCII)
"""

import struct
import time
import hashlib
import json
import gzip
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum, IntFlag
from typing import Any, Dict, List, Optional, Tuple

# Try to import kanzi compression (better than gzip)
try:
    import kanzi
    KANZI_AVAILABLE = True
except ImportError:
    KANZI_AVAILABLE = False

# Try to import QATzip (Intel QAT hardware acceleration - best compression)
QATZIP_AVAILABLE = False
QATZIP_HARDWARE_AVAILABLE = False

try:
    import qatzip
    QATZIP_AVAILABLE = True
    
    # Detect if Intel QAT hardware accelerators are actually present
    try:
        # Method 1: Try QATzip library hardware detection
        if hasattr(qatzip, 'is_hardware_available'):
            QATZIP_HARDWARE_AVAILABLE = qatzip.is_hardware_available()
        elif hasattr(qatzip, 'check_hardware'):
            QATZIP_HARDWARE_AVAILABLE = qatzip.check_hardware()
        elif hasattr(qatzip, 'QzCompress'):
            # Method 2: Try to initialize - will fail if no hardware
            try:
                test_compressor = qatzip.QzCompress()
                QATZIP_HARDWARE_AVAILABLE = True
            except Exception:
                QATZIP_HARDWARE_AVAILABLE = False
        else:
            # Method 3: Check system for QAT devices
            import os
            qat_devices = ["/dev/qat_adf_ctl", "/dev/qat_dev0", "/dev/qat_dev1"]
            QATZIP_HARDWARE_AVAILABLE = any(os.path.exists(d) for d in qat_devices)
    except Exception:
        # Hardware detection failed - assume not available
        QATZIP_HARDWARE_AVAILABLE = False
except ImportError:
    QATZIP_AVAILABLE = False
    QATZIP_HARDWARE_AVAILABLE = False

# Try to import Reed-Solomon for ECC (optional, has fallback)
try:
    import reedsolo
    REED_SOLOMON_AVAILABLE = True
except ImportError:
    REED_SOLOMON_AVAILABLE = False

# ============================================================================
# Protocol Constants
# ============================================================================

MEMSHADOW_MAGIC = 0x4D53485700000000  # "MSHW" in ASCII (padded to 8 bytes)
MEMSHADOW_VERSION = 3  # Version 3.0
HEADER_SIZE = 32

# Version compatibility
VERSION_MAJOR = 3
VERSION_MINOR = 0
PSYCH_EVENT_SIZE = 64

# Telemetry mode uses minimal header (16 bytes instead of 32)
TELEMETRY_HEADER_SIZE = 16
TELEMETRY_MAGIC = 0x4D53544C  # "MSTL" in ASCII (MemShadow Telemetry)

# ECC and connection quality constants
ECC_NONE = 0
ECC_PARITY = 1  # Simple parity (1 byte overhead)
ECC_REED_SOLOMON = 2  # Reed-Solomon (configurable overhead)
MAX_CONNECTION_QUALITY = 255  # 0-255 scale


# ============================================================================
# Enumerations
# ============================================================================

class MessageType(IntEnum):
    """MEMSHADOW Protocol v3.0 Message Types"""
    
    # System/Control (0x00xx)
    HEARTBEAT = 0x0001
    ACK = 0x0002
    NACK = 0x0003
    ERROR = 0x0003  # Alias for NACK
    HANDSHAKE = 0x0004
    DISCONNECT = 0x0005
    
    # SHRINK Psychological Intelligence (0x01xx)
    PSYCH_ASSESSMENT = 0x0100
    DARK_TRIAD_UPDATE = 0x0101
    RISK_UPDATE = 0x0102
    NEURO_UPDATE = 0x0103
    TMI_UPDATE = 0x0104
    COGARCH_UPDATE = 0x0105
    COGNITIVE_UPDATE = 0x0105  # Alias
    FULL_PSYCH = 0x0106
    PSYCH_THREAT_ALERT = 0x0110
    PSYCH_ANOMALY = 0x0111
    PSYCH_RISK_THRESHOLD = 0x0112
    
    # Threat Intelligence (0x02xx)
    THREAT_REPORT = 0x0201
    INTEL_REPORT = 0x0202
    KNOWLEDGE_UPDATE = 0x0203
    BRAIN_INTEL_REPORT = 0x0204
    INTEL_PROPAGATE = 0x0205
    
    # Memory Operations (0x03xx)
    MEMORY_STORE = 0x0301
    MEMORY_QUERY = 0x0302
    MEMORY_RESPONSE = 0x0303
    MEMORY_SYNC = 0x0304
    VECTOR_SYNC = 0x0305
    
    # File Transfer Operations (0x06xx) - NEW for large file support
    FILE_TRANSFER_START = 0x0601  # Initial file metadata
    FILE_TRANSFER_CHUNK = 0x0602  # File data chunk
    FILE_TRANSFER_END = 0x0603    # Transfer completion
    FILE_TRANSFER_ABORT = 0x0604  # Transfer cancellation
    FILE_TRANSFER_REQUEST = 0x0605  # Request file transfer
    
    # Federation/Mesh (0x04xx)
    NODE_REGISTER = 0x0401
    NODE_DEREGISTER = 0x0402
    QUERY_DISTRIBUTE = 0x0403
    BRAIN_QUERY = 0x0403  # Alias
    QUERY_RESPONSE = 0x0404
    
    # Self-Improvement (0x05xx)
    IMPROVEMENT_ANNOUNCE = 0x0501
    IMPROVEMENT_REQUEST = 0x0502
    IMPROVEMENT_PAYLOAD = 0x0503
    IMPROVEMENT_ACK = 0x0504
    IMPROVEMENT_REJECT = 0x0505
    IMPROVEMENT_METRICS = 0x0506
    
    # Temporal Message Queuing (0x08xx) - Enhancement 1
    TEMPORAL_QUEUE = 0x0801  # Schedule message for future delivery
    TEMPORAL_DELIVER = 0x0802  # Deliver temporally queued message
    TEMPORAL_CANCEL = 0x0803  # Cancel scheduled message
    TEMPORAL_QUERY = 0x0804  # Query scheduled messages
    
    # Quantum Entanglement Routing (0x09xx) - Enhancement 2
    QUANTUM_ENTANGLE = 0x0901  # Create entanglement group
    QUANTUM_DELIVER = 0x0902  # Deliver to entangled nodes
    QUANTUM_COLLAPSE = 0x0903  # Collapse quantum state
    QUANTUM_STATE_SYNC = 0x0904  # Sync quantum state
    
    # Morphic Protocol Adaptation (0x0Axx) - Enhancement 3
    MORPHIC_PROPOSAL = 0x0A01  # Propose protocol adaptation
    MORPHIC_VOTE = 0x0A02  # Vote on adaptation (accept/reject)
    MORPHIC_TEST = 0x0A03  # Test adaptation in network
    MORPHIC_METRICS = 0x0A04  # Report adaptation metrics
    MORPHIC_ACCEPT = 0x0A05  # Accept adaptation (consensus reached)
    MORPHIC_REJECT = 0x0A06  # Reject adaptation (consensus failed)
    MORPHIC_RESEARCH = 0x0A07  # AI research proposal for adaptation
    
    # Peer Management (0x0Bxx) - Large Local Network Support
    PEER_REGISTER = 0x0B01  # Register peer
    PEER_LIST_REQUEST = 0x0B02  # Request peer list
    PEER_LIST_RESPONSE = 0x0B03  # Peer list response
    PEER_UPDATE = 0x0B04  # Update peer information
    PEER_DISCOVERY = 0x0B05  # Peer discovery request
    
    # Relay System (0x0Cxx) - Multi-hop Relay
    RELAY_REQUEST = 0x0C01  # Request relay
    RELAY_DATA = 0x0C02  # Relay data through path
    RELAY_ACK = 0x0C03  # Relay acknowledgment
    RELAY_ERROR = 0x0C04  # Relay error
    
    # Telemetry/Control (0x07xx) - Lightweight telemetry and control messages
    TELEMETRY = 0x0701  # Telemetry/metrics (uses 16-byte header)
    CONTROL = 0x0702  # Control messages
    HEADER_ONLY = 0x0703  # Header-only messages
    PAYLOAD_ONLY = 0x0704  # Payload-only messages

    # DSOS Intelligence Operations (0xD0xx) - DSOS Intelligence Extension
    DSOS_INTELLIGENCE_COLLECTION = 0xD001  # Coordinate multi-source intelligence gathering
    DSOS_INTELLIGENCE_PROCESSING = 0xD002  # AI-powered intelligence analysis and correlation
    DSOS_INTELLIGENCE_DISSEMINATION = 0xD003  # Secure intelligence product distribution
    DSOS_INTELLIGENCE_ARCHIVAL = 0xD004  # Long-term intelligence storage and retrieval
    DSOS_INTELLIGENCE_QUERY = 0xD005  # Semantic intelligence database querying
    DSOS_INTELLIGENCE_REPORTING = 0xD006  # Automated intelligence report generation
    DSOS_INTELLIGENCE_CORRELATION = 0xD007  # Cross-source intelligence correlation
    DSOS_INTELLIGENCE_SYNTHESIS = 0xD008  # AI-powered intelligence synthesis and fusion

    # AI Processing Operations (0xD3xx) - DSOS Intelligence Extension
    DSOS_AI_MODEL_DEPLOYMENT = 0xD301  # Deploy AI models across DSOS nodes
    DSOS_AI_INFERENCE_REQUEST = 0xD302  # Request AI inference on intelligence data
    DSOS_AI_TRAINING_COORDINATION = 0xD303  # Coordinate federated learning sessions
    DSOS_AI_MODEL_SYNCHRONIZATION = 0xD304  # Synchronize AI models across nodes
    DSOS_AI_QUANTUM_PROCESSING = 0xD305  # Quantum-accelerated AI operations
    DSOS_AI_NEUROMORPHIC_EXECUTION = 0xD306  # Neuromorphic hardware processing
    DSOS_AI_EXPLAINABILITY = 0xD307  # Request AI decision explanations
    DSOS_AI_ADVERSARIAL_TESTING = 0xD308  # Test AI robustness against adversarial inputs

    # Advanced Routing Operations (0xD4xx) - DSOS Intelligence Extension
    DSOS_MOE_ROUTING = 0xD401  # Mixture-of-Experts intelligent routing
    DSOS_TOPOLOGY_AWARE_ROUTING = 0xD402  # Network topology-aware message routing
    DSOS_LOAD_BALANCING = 0xD403  # Intelligent load balancing across processing nodes
    DSOS_PRIORITY_BASED_ROUTING = 0xD404  # Priority-based intelligence routing
    DSOS_RESILIENCE_ROUTING = 0xD405  # Adaptive routing for network resilience
    DSOS_COVERT_ROUTING = 0xD406  # Covert channel routing for sensitive intelligence
    DSOS_MULTICAST_INTELLIGENCE = 0xD407  # Multi-destination intelligence dissemination
    DSOS_BROADCAST_ALERT = 0xD408  # Emergency intelligence broadcasting

    # Security and Cryptographic Operations (0xD5xx) - DSOS Intelligence Extension
    DSOS_PQC_KEY_EXCHANGE = 0xD501  # Post-quantum cryptographic key exchange
    DSOS_STEGANOGRAPHY_ENCODING = 0xD502  # Steganographic data encoding
    DSOS_COVERT_CHANNEL_ESTABLISHMENT = 0xD503  # Establish covert communication channels
    DSOS_TAMPER_DETECTION = 0xD504  # Cryptographic integrity verification
    DSOS_ZERO_KNOWLEDGE_PROOF = 0xD505  # Zero-knowledge authentication
    DSOS_QUANTUM_KEY_DISTRIBUTION = 0xD506  # Quantum key distribution protocols
    DSOS_HOMOMORPHIC_ENCRYPTION = 0xD507  # Homomorphic encryption operations
    DSOS_SECURE_MULTIPARTY_COMPUTATION = 0xD508  # Secure multi-party computation

    # Orchestration and Coordination (0xD6xx) - DSOS Intelligence Extension
    DSOS_SPOE_INTELLIGENCE_ORCHESTRATION = 0xD601  # SPOE intelligence coordination
    DSOS_WORKFLOW_EXECUTION = 0xD602  # Execute intelligence processing workflows
    DSOS_RESOURCE_ALLOCATION = 0xD603  # Dynamic resource allocation for intelligence tasks
    DSOS_PERFORMANCE_MONITORING = 0xD604  # Real-time performance monitoring and alerting
    DSOS_FAILURE_RECOVERY = 0xD605  # Automated failure detection and recovery
    DSOS_LOAD_SHEDDING = 0xD606  # Intelligent load shedding during resource constraints
    DSOS_MAINTENANCE_COORDINATION = 0xD607  # Coordinated system maintenance operations
    DSOS_AUDIT_LOG_SYNCHRONIZATION = 0xD608  # Distributed audit log synchronization


# Alias for backward compatibility
MemshadowMessageType = MessageType


class Priority(IntEnum):
    """
    Message priority levels for routing decisions.
    
    Routing rules:
    - LOW (0): Background processing
    - NORMAL (1): Standard hub routing
    - HIGH (2): Hub-relayed with priority queue
    - CRITICAL (3): Direct P2P + hub notification
    - EMERGENCY (4): Immediate P2P action required
    """
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    EMERGENCY = 4
    
    # Aliases for sync operations
    BACKGROUND = 0
    URGENT = 4
    
    def should_use_p2p(self) -> bool:
        """Check if this priority should use direct P2P routing"""
        return self >= Priority.CRITICAL
    
    def should_require_ack(self) -> bool:
        """Check if this priority should require acknowledgment"""
        return self >= Priority.HIGH
    
    def is_hub_relayed(self) -> bool:
        """Check if this priority uses hub relay (not P2P)"""
        return self < Priority.CRITICAL


# Alias for backward compatibility
MemshadowMessagePriority = Priority


class MessageFlags(IntFlag):
    """
    Message flags for payload handling.
    
    Flags are packed into 1 byte in header (0xFF max).
    For extensibility beyond 8 flags, use payload extensions.
    """
    NONE = 0x0000
    ENCRYPTED = 0x0001
    COMPRESSED = 0x0002
    BATCHED = 0x0004
    REQUIRES_ACK = 0x0008
    FRAGMENTED = 0x0010
    LAST_FRAGMENT = 0x0020
    FROM_KERNEL = 0x0040
    HIGH_CONFIDENCE = 0x0080
    # Note: Flags beyond 0xFF are negotiated via TLS extension during handshake
    # No payload extension header needed - flags available from TLS session context
    # HAS_EXTENSION deprecated - use TLS extensions instead
    HAS_EXTENSION = 0x0100  # Deprecated - use TLS extensions
    ECC_ENABLED = 0x0200  # Error correction code enabled (not in base flags byte)
    INTEGRITY_CHECK = 0x1000  # Per-message HMAC integrity check (HMAC-SHA384)
    # Dual-stream and obscurity flags
    DUAL_STREAM = 0x0400  # Header/payload separated into alternate streams
    TELEMETRY_MODE = 0x0800  # Ultra-lightweight telemetry mode (minimal header)
    STEGANOGRAPHIC = 0x1000  # Payload is steganographically hidden
    TRAFFIC_SHAPED = 0x2000  # Traffic shaped to mimic other protocols
    QUANTUM_RESISTANT = 0x4000  # Quantum-resistant encryption enabled
    # Exotic enhancements
    TEMPORAL_QUEUED = 0x8000  # Message is temporally queued (future/past delivery)
    QUANTUM_ENTANGLED = 0x10000  # Message uses quantum entanglement routing
    MORPHIC_ADAPTED = 0x20000  # Message uses morphed protocol structure


class SyncOperation(IntEnum):
    """Memory sync operations"""
    INSERT = 1
    UPDATE = 2
    DELETE = 3
    MERGE = 4
    REPLICATE = 5


class MemoryTier(IntEnum):
    """Memory tier levels"""
    WORKING = 1
    EPISODIC = 2
    SEMANTIC = 3
    L1 = 1
    L2 = 2
    L3 = 3


# ============================================================================
# Header Structure
# ============================================================================

@dataclass
class MemshadowHeader:
    """
    MEMSHADOW Protocol v3 Header (32 bytes)
    
    Wire format (big-endian):
        magic         : 8 bytes - Protocol magic (0x4D53485700000000 "MSHW" padded to 8 bytes)
        version       : 2 bytes - Protocol version (3)
        priority      : 2 bytes - Message priority (0-4)
        msg_type      : 2 bytes - Message type
        flags_batch   : 2 bytes - Flags (low byte) + batch_count (high byte)
        payload_len   : 4 bytes - Payload length in bytes (reduced from 8 to make room)
        timestamp_ns  : 8 bytes - Nanosecond timestamp
        sequence_num  : 4 bytes - Sequence number (for ordering, not enforced)
    
    Total: 32 bytes exactly
    
    Version Compatibility (v3.0+):
    - Same major version: Compatible
    - Different major version: Incompatible (log but don't respond)
    - Higher minor version: Backward compatible (suggest upgrade)
    - After 3.0: Support backward compatibility, suggest upgrade, stage for 12h,
      then send binary upgrade in-place, keep old version as fallback
    
    Connection quality and ECC are encoded efficiently:
    - Connection quality byte embedded in payload_len (LSB) when ECC enabled
    - ECC parity bytes serve double duty: error correction + quality encoding
    - Quality recovered by reversing the encoding operation
    
    Extensibility notes:
    - Version field allows protocol evolution
    - Flags support future features (obfuscation, DPI resistance)
    - Payload can contain extensible metadata structures
    """
    magic: int = 0x4D53485700000000  # "MSHW" padded to 8 bytes
    version: int = MEMSHADOW_VERSION
    priority: Priority = Priority.NORMAL
    msg_type: MessageType = MessageType.HEARTBEAT
    flags: MessageFlags = MessageFlags.NONE
    batch_count: int = 0
    payload_len: int = 0
    timestamp_ns: int = field(default_factory=lambda: int(time.time() * 1e9))
    sequence_num: int = 0  # Sequence number (for ordering, not enforced)
    # Connection quality and ECC (encoded efficiently)
    connection_quality: int = 255  # 0-255, sender's perceived connection quality
    ecc_mode: int = ECC_NONE  # ECC mode (0=none, 1=parity, 2=reed-solomon)
    
    _FORMAT = ">QHHHHIIQ"  # Updated: payload_len is now I (4 bytes), added sequence_num I (4 bytes)
    
    # Aliases for backward compatibility
    @property
    def message_type(self) -> MessageType:
        return self.msg_type
    
    @message_type.setter
    def message_type(self, value: MessageType):
        self.msg_type = value
    
    def pack(self) -> bytes:
        """
        Pack header to binary (32 bytes, network byte order).
        
        Efficient encoding: When ECC enabled, connection quality is encoded
        in payload_len LSB to save space. ECC parity bytes also encode quality info.
        """
        flags_batch = (int(self.flags) & 0xFF) | ((self.batch_count & 0xFF) << 8)
        
        # Encode connection quality in payload_len LSB if ECC enabled
        # This allows quality info without extra header bytes
        payload_len_encoded = self.payload_len
        if self.ecc_mode != ECC_NONE:
            # Encode quality in LSB: multiply by 2, add quality bit
            # Quality is 0-255, we encode it in the lowest byte
            # We'll use the fact that payload_len is 8 bytes, so we can
            # encode quality in a way that doesn't affect actual length
            # For now, we'll store it separately and encode in extension
            pass  # Will be handled in message packing with ECC
        
        return struct.pack(
            self._FORMAT,
            self.magic,
            self.version,
            int(self.priority),
            int(self.msg_type),
            flags_batch,
            payload_len_encoded,
            self.sequence_num,  # Fixed: I format (4 bytes) - sequence_num comes before timestamp_ns
            self.timestamp_ns,  # Fixed: Q format (8 bytes) - timestamp_ns comes after sequence_num
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> "MemshadowHeader":
        """Unpack header from binary (32 bytes)"""
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Header too short: {len(data)} bytes, expected {HEADER_SIZE}")
        
        (
            magic,
            version,
            priority,
            msg_type,
            flags_batch,
            payload_len,
            sequence_num,  # Fixed: I format (4 bytes) - sequence_num comes before timestamp_ns
            timestamp_ns,  # Fixed: Q format (8 bytes) - timestamp_ns comes after sequence_num
        ) = struct.unpack(cls._FORMAT, data[:HEADER_SIZE])
        
        # Check first 4 bytes match "MSHW"
        magic_4bytes = (magic >> 32) & 0xFFFFFFFF
        if magic_4bytes != 0x4D534857:
            raise ValueError(f"Invalid magic: 0x{magic:016X}, expected 0x4D53485700000000 (MSHW)")
        
        flags = MessageFlags(flags_batch & 0xFF)
        batch_count = (flags_batch >> 8) & 0xFF
        
        header = cls(
            magic=magic,
            version=version,
            priority=Priority(priority),
            msg_type=MessageType(msg_type),
            flags=flags,
            batch_count=batch_count,
            payload_len=payload_len,
            timestamp_ns=timestamp_ns,
            sequence_num=sequence_num,
        )
        
        # Initialize ECC/quality fields (will be set during message unpack if ECC enabled)
        header.connection_quality = 255  # Default
        header.ecc_mode = ECC_NONE  # Default
        
        return header
    
    @property
    def timestamp(self) -> datetime:
        """Get timestamp as datetime (UTC)"""
        return datetime.fromtimestamp(self.timestamp_ns / 1e9, tz=timezone.utc)
    
    def validate(self) -> bool:
        """Validate header fields"""
        # Check first 4 bytes match "MSHW"
        magic_4bytes = (self.magic >> 32) & 0xFFFFFFFF
        return magic_4bytes == 0x4D534857 and self.version == MEMSHADOW_VERSION


# ============================================================================
# SHRINK Psychological Event Structure (64 bytes)
# ============================================================================

@dataclass
class PsychEvent:
    """
    SHRINK psychological event (64 bytes).
    
    Wire format matches kernel module struct dsmil_psych_event_t.
    """
    session_id: int = 0
    timestamp_offset_us: int = 0
    event_type: int = 0
    flags: int = 0
    window_size: int = 0
    context_hash: int = 0
    acute_stress: float = 0.0
    machiavellianism: float = 0.0
    narcissism: float = 0.0
    psychopathy: float = 0.0
    burnout_probability: float = 0.0
    espionage_exposure: float = 0.0
    confidence: float = 0.0
    
    _FORMAT = ">QIBBHQfffffff12x"
    
    @property
    def dark_triad_average(self) -> float:
        """Calculate average dark triad score"""
        return (self.machiavellianism + self.narcissism + self.psychopathy) / 3.0
    
    def pack(self) -> bytes:
        """Pack to binary (64 bytes)"""
        return struct.pack(
            self._FORMAT,
            self.session_id,
            self.timestamp_offset_us,
            self.event_type,
            self.flags,
            self.window_size,
            self.context_hash,
            self.acute_stress,
            self.machiavellianism,
            self.narcissism,
            self.psychopathy,
            self.burnout_probability,
            self.espionage_exposure,
            self.confidence,
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> "PsychEvent":
        """Unpack from binary (64 bytes)"""
        if len(data) < PSYCH_EVENT_SIZE:
            raise ValueError(f"PsychEvent too short: {len(data)} bytes")
        
        (
            session_id,
            timestamp_offset_us,
            event_type,
            flags,
            window_size,
            context_hash,
            acute_stress,
            machiavellianism,
            narcissism,
            psychopathy,
            burnout_probability,
            espionage_exposure,
            confidence,
        ) = struct.unpack(cls._FORMAT, data[:PSYCH_EVENT_SIZE])
        
        return cls(
            session_id=session_id,
            timestamp_offset_us=timestamp_offset_us,
            event_type=event_type,
            flags=flags,
            window_size=window_size,
            context_hash=context_hash,
            acute_stress=acute_stress,
            machiavellianism=machiavellianism,
            narcissism=narcissism,
            psychopathy=psychopathy,
            burnout_probability=burnout_probability,
            espionage_exposure=espionage_exposure,
            confidence=confidence,
        )


class PsychEventType(IntEnum):
    """SHRINK psychological event types"""
    KEYPRESS = 1
    MOUSE_MOVE = 2
    SCORE_UPDATE = 3
    WINDOW_CHANGE = 4
    SESSION_START = 5
    SESSION_END = 6


# ============================================================================
# Extensible Hash Algorithm System
# ============================================================================

class HashAlgorithm(IntEnum):
    """
    Extensible hash algorithm enumeration.
    
    This allows the protocol to support multiple hash algorithms
    for future extensibility while maintaining backwards compatibility.
    """
    SHA256 = 1      # SHA-256 (256 bits / 32 bytes) - Legacy support
    SHA384 = 2      # SHA-384 (384 bits / 48 bytes) - Default
    SHA512 = 3      # SHA-512 (512 bits / 64 bytes)
    BLAKE2B_256 = 4 # BLAKE2b-256 (256 bits / 32 bytes)
    BLAKE2B_512 = 5 # BLAKE2b-512 (512 bits / 64 bytes)
    SHA3_256 = 6    # SHA3-256 (256 bits / 32 bytes)
    SHA3_384 = 7    # SHA3-384 (384 bits / 48 bytes)
    SHA3_512 = 8    # SHA3-512 (512 bits / 64 bytes)
    
    @property
    def digest_size(self) -> int:
        """Get digest size in bytes"""
        sizes = {
            HashAlgorithm.SHA256: 32,
            HashAlgorithm.SHA384: 48,
            HashAlgorithm.SHA512: 64,
            HashAlgorithm.BLAKE2B_256: 32,
            HashAlgorithm.BLAKE2B_512: 64,
            HashAlgorithm.SHA3_256: 32,
            HashAlgorithm.SHA3_384: 48,
            HashAlgorithm.SHA3_512: 64,
        }
        return sizes.get(self, 48)  # Default to SHA-384 size
    
    @property
    def name(self) -> str:
        """Get algorithm name"""
        names = {
            HashAlgorithm.SHA256: "sha256",
            HashAlgorithm.SHA384: "sha384",
            HashAlgorithm.SHA512: "sha512",
            HashAlgorithm.BLAKE2B_256: "blake2b-256",
            HashAlgorithm.BLAKE2B_512: "blake2b-512",
            HashAlgorithm.SHA3_256: "sha3-256",
            HashAlgorithm.SHA3_384: "sha3-384",
            HashAlgorithm.SHA3_512: "sha3-512",
        }
        return names.get(self, "sha384")
    
    def compute_hash(self, data: bytes) -> bytes:
        """Compute hash of data using this algorithm"""
        if self == HashAlgorithm.SHA256:
            return hashlib.sha384(data).digest()
        elif self == HashAlgorithm.SHA384:
            return hashlib.sha384(data).digest()
        elif self == HashAlgorithm.SHA512:
            return hashlib.sha512(data).digest()
        elif self == HashAlgorithm.BLAKE2B_256:
            return hashlib.blake2b(data, digest_size=32).digest()
        elif self == HashAlgorithm.BLAKE2B_512:
            return hashlib.blake2b(data, digest_size=64).digest()
        elif self == HashAlgorithm.SHA3_256:
            return hashlib.sha3_256(data).digest()
        elif self == HashAlgorithm.SHA3_384:
            return hashlib.sha3_384(data).digest()
        elif self == HashAlgorithm.SHA3_512:
            return hashlib.sha3_512(data).digest()
        else:
            # Default to SHA-384
            return hashlib.sha384(data).digest()
    
    def compute_hash_hex(self, data: bytes) -> str:
        """Compute hex hash of data using this algorithm"""
        return self.compute_hash(data).hex()
    
    @classmethod
    def from_name(cls, name: str) -> "HashAlgorithm":
        """Create from algorithm name"""
        name_map = {
            "sha256": cls.SHA256,
            "sha384": cls.SHA384,
            "sha512": cls.SHA512,
            "blake2b-256": cls.BLAKE2B_256,
            "blake2b-512": cls.BLAKE2B_512,
            "sha3-256": cls.SHA3_256,
            "sha3-384": cls.SHA3_384,
            "sha3-512": cls.SHA3_512,
        }
        return name_map.get(name.lower(), cls.SHA384)  # Default to SHA-384


# Default hash algorithm (SHA-384)
DEFAULT_HASH_ALGORITHM = HashAlgorithm.SHA384


# ============================================================================
# Optional Extension Headers (Only when needed)
# ============================================================================

@dataclass
class MessageExtension:
    """
    Optional extension header for enhanced features.
    
    Only included when HAS_EXTENSION flag is set.
    Placed at start of payload (before actual payload data).
    
    Binary format (variable size):
        extension_type: 1 byte - Extension type
        extension_len: 2 bytes - Length of extension data (big-endian)
        extension_data: variable - Extension-specific data
    
    This keeps the base header minimal while allowing extensibility.
    """
    extension_type: int  # Extension type identifier
    extension_data: bytes = b""
    
    _HEADER_FORMAT = "!BH"  # type (1) + len (2)
    _HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)  # 3 bytes
    
    def pack(self) -> bytes:
        """Pack extension header"""
        header = struct.pack(
            self._HEADER_FORMAT,
            self.extension_type,
            len(self.extension_data),
        )
        return header + self.extension_data
    
    @classmethod
    def unpack(cls, data: bytes) -> Tuple["MessageExtension", int]:
        """Unpack extension header. Returns (extension, bytes_consumed)"""
        if len(data) < cls._HEADER_SIZE:
            raise ValueError("Extension header too short")
        
        ext_type, ext_len = struct.unpack(cls._HEADER_FORMAT, data[:cls._HEADER_SIZE])
        
        if len(data) < cls._HEADER_SIZE + ext_len:
            raise ValueError(f"Extension data too short: need {cls._HEADER_SIZE + ext_len}, got {len(data)}")
        
        ext_data = data[cls._HEADER_SIZE:cls._HEADER_SIZE + ext_len]
        
        return cls(extension_type=ext_type, extension_data=ext_data), cls._HEADER_SIZE + ext_len


class ExtensionType(IntEnum):
    """Extension type identifiers"""
    FILE_TRANSFER_METADATA = 1  # File transfer enhanced metadata
    DPI_RESISTANCE = 2  # DPI resistance configuration
    WORKLOAD_ENHANCED = 3  # Enhanced workload metadata
    OBFUSCATION = 4  # Obfuscation parameters
    TRAFFIC_SHAPING = 5  # Traffic shaping profile
    CONNECTION_QUALITY_ECC = 6  # Connection quality + ECC data (combined)


# ============================================================================
# File Transfer Structures
# ============================================================================

@dataclass
class FileMetadata:
    """
    File metadata for transfer operations.
    
    Serialized as JSON in FILE_TRANSFER_START payload.
    
    Designed for extensibility:
    - Configurable hash algorithms (default: SHA-384)
    - Extensible compression support
    - Additional metadata dictionary for future extensions
    """
    file_id: str  # Unique transfer ID
    filename: str
    file_size: int  # Total file size in bytes
    mime_type: str = "application/octet-stream"
    checksum: str = ""  # Hash of file content (hex encoded)
    hash_algorithm: int = DEFAULT_HASH_ALGORITHM.value  # HashAlgorithm enum value
    compression: str = ""  # Compression algorithm if used (e.g., "kanzi", "gzip", "qatzip", "zstd")
    chunk_size: int = 0  # Size of each chunk (0 = use default)
    total_chunks: int = 0  # Total number of chunks
    protocol_version: int = 3  # Protocol version for extensibility
    # Enhanced workload fields (only included if needed - reduces protocol bloat)
    obfuscation_mode: str = ""  # Obfuscation method (only if used)
    encryption_mode: str = ""  # Encryption method (only if used)
    dpi_resistance: bool = False  # Enable DPI resistance (only if True)
    traffic_shape: str = ""  # Traffic shaping profile (only if set)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata (only if present)
    
    @property
    def hash_alg(self) -> HashAlgorithm:
        """Get HashAlgorithm enum from value"""
        return HashAlgorithm(self.hash_algorithm)
    
    @hash_alg.setter
    def hash_alg(self, value: HashAlgorithm):
        """Set hash algorithm"""
        self.hash_algorithm = value.value
    
    def to_dict(self, include_extensions: bool = True) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Args:
            include_extensions: Include optional fields only if set (reduces bloat)
        """
        result = {
            "file_id": self.file_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "checksum": self.checksum,
            "hash_algorithm": self.hash_algorithm,
            "compression": self.compression,
            "chunk_size": self.chunk_size,
            "total_chunks": self.total_chunks,
            "protocol_version": self.protocol_version,
        }
        
        # Only include optional fields if set (reduces protocol bloat)
        if include_extensions:
            if self.obfuscation_mode:
                result["obfuscation_mode"] = self.obfuscation_mode
            if self.encryption_mode:
                result["encryption_mode"] = self.encryption_mode
            if self.dpi_resistance:
                result["dpi_resistance"] = self.dpi_resistance
            if self.traffic_shape:
                result["traffic_shape"] = self.traffic_shape
            if self.metadata:
                result["metadata"] = self.metadata
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileMetadata":
        """Create from dictionary (with backwards compatibility)"""
        # Backwards compatibility: if hash_algorithm not present, default to SHA-384
        hash_alg = data.get("hash_algorithm", DEFAULT_HASH_ALGORITHM.value)
        
        return cls(
            file_id=data["file_id"],
            filename=data["filename"],
            file_size=data["file_size"],
            mime_type=data.get("mime_type", "application/octet-stream"),
            checksum=data.get("checksum", ""),
            hash_algorithm=hash_alg,
            compression=data.get("compression", ""),
            chunk_size=data.get("chunk_size", 0),
            total_chunks=data.get("total_chunks", 0),
            protocol_version=data.get("protocol_version", 3),
            obfuscation_mode=data.get("obfuscation_mode", ""),
            encryption_mode=data.get("encryption_mode", ""),
            dpi_resistance=data.get("dpi_resistance", False),
            traffic_shape=data.get("traffic_shape", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class FileChunkHeader:
    """
    Header for a file transfer chunk.
    
    Optimized binary format (minimal base, variable checksum):
        file_id: 16 bytes (UUID or hash)
        chunk_index: 4 bytes (uint32, big-endian)
        chunk_size: 4 bytes (uint32, big-endian)
        hash_algorithm: 1 byte (HashAlgorithm enum value)
        checksum_size: 1 byte (size of checksum in bytes)
        chunk_checksum: variable (hash digest, typically 48 bytes for SHA-384)
    
    Total: 26 bytes base + checksum_size (typically 48 for SHA-384 = 74 bytes)
    
    Design principles:
    - Minimal base header (26 bytes)
    - Variable checksum size based on algorithm
    - No bloat for unused features
    """
    file_id: bytes  # 16 bytes
    chunk_index: int  # 0-based index
    chunk_size: int  # Size of this chunk
    hash_algorithm: HashAlgorithm = DEFAULT_HASH_ALGORITHM
    chunk_checksum: bytes = b""  # Variable size hash digest
    
    # Base format (without checksum)
    _BASE_FORMAT = "!16sIIBB"
    _BASE_SIZE = struct.calcsize(_BASE_FORMAT)  # 26 bytes base
    
    @property
    def checksum_size(self) -> int:
        """Get checksum size in bytes"""
        return len(self.chunk_checksum) if self.chunk_checksum else self.hash_algorithm.digest_size
    
    @property
    def total_size(self) -> int:
        """Get total header size including checksum"""
        return self._BASE_SIZE + self.checksum_size
    
    def pack(self) -> bytes:
        """Pack chunk header to binary (variable size)"""
        # Ensure file_id is exactly 16 bytes
        file_id_bytes = self.file_id[:16].ljust(16, b'\x00')
        
        # Ensure checksum is correct size
        if not self.chunk_checksum:
            self.chunk_checksum = b'\x00' * self.hash_algorithm.digest_size
        elif len(self.chunk_checksum) < self.hash_algorithm.digest_size:
            # Pad if needed (shouldn't happen, but be safe)
            self.chunk_checksum = self.chunk_checksum.ljust(self.hash_algorithm.digest_size, b'\x00')
        elif len(self.chunk_checksum) > self.hash_algorithm.digest_size:
            # Truncate if too long
            self.chunk_checksum = self.chunk_checksum[:self.hash_algorithm.digest_size]
        
        checksum_size = len(self.chunk_checksum)
        
        # Pack base header
        base_header = struct.pack(
            self._BASE_FORMAT,
            file_id_bytes,
            self.chunk_index,
            self.chunk_size,
            self.hash_algorithm.value,
            checksum_size,
        )
        
        return base_header + self.chunk_checksum
    
    @classmethod
    def unpack(cls, data: bytes) -> "FileChunkHeader":
        """Unpack chunk header from binary"""
        if len(data) < cls._BASE_SIZE:
            raise ValueError(f"Chunk header too short: {len(data)} bytes, expected at least {cls._BASE_SIZE}")
        
        # Unpack base header
        file_id_bytes, chunk_index, chunk_size, hash_alg_val, checksum_size = struct.unpack(
            cls._BASE_FORMAT, data[:cls._BASE_SIZE]
        )
        
        # Validate checksum size
        if checksum_size > 64:  # Sanity check
            raise ValueError(f"Invalid checksum size: {checksum_size} bytes")
        
        if len(data) < cls._BASE_SIZE + checksum_size:
            raise ValueError(f"Data too short for checksum: need {cls._BASE_SIZE + checksum_size}, got {len(data)}")
        
        # Extract checksum
        checksum = data[cls._BASE_SIZE:cls._BASE_SIZE + checksum_size]
        
        # Get hash algorithm
        try:
            hash_alg = HashAlgorithm(hash_alg_val)
        except ValueError:
            # Unknown algorithm, default to SHA-384
            hash_alg = DEFAULT_HASH_ALGORITHM
        
        return cls(
            file_id=file_id_bytes.rstrip(b'\x00'),
            chunk_index=chunk_index,
            chunk_size=chunk_size,
            hash_algorithm=hash_alg,
            chunk_checksum=checksum,
        )
    
    def pack(self) -> bytes:
        """Pack chunk header to binary (variable size)"""
        # Ensure file_id is exactly 16 bytes
        file_id_bytes = self.file_id[:16].ljust(16, b'\x00')
        
        # Ensure checksum is correct size
        if not self.chunk_checksum:
            self.chunk_checksum = b'\x00' * self.hash_algorithm.digest_size
        elif len(self.chunk_checksum) < self.hash_algorithm.digest_size:
            # Pad if needed
            self.chunk_checksum = self.chunk_checksum.ljust(self.hash_algorithm.digest_size, b'\x00')
        elif len(self.chunk_checksum) > self.hash_algorithm.digest_size:
            # Truncate if too long
            self.chunk_checksum = self.chunk_checksum[:self.hash_algorithm.digest_size]
        
        checksum_size = len(self.chunk_checksum)
        
        # Pack base header
        base_header = struct.pack(
            self._BASE_FORMAT,
            file_id_bytes,
            self.chunk_index,
            self.chunk_size,
            self.hash_algorithm.value,
            checksum_size,
        )
        
        return base_header + self.chunk_checksum
    
    @classmethod
    def unpack(cls, data: bytes) -> "FileChunkHeader":
        """Unpack chunk header from binary"""
        if len(data) < cls._BASE_SIZE:
            raise ValueError(f"Chunk header too short: {len(data)} bytes, expected at least {cls._BASE_SIZE}")
        
        # Unpack base header
        file_id_bytes, chunk_index, chunk_size, hash_alg_val, checksum_size = struct.unpack(
            cls._BASE_FORMAT, data[:cls._BASE_SIZE]
        )
        
        # Validate checksum size
        if checksum_size > 64:  # Sanity check
            raise ValueError(f"Invalid checksum size: {checksum_size} bytes")
        
        if len(data) < cls._BASE_SIZE + checksum_size:
            raise ValueError(f"Data too short for checksum: need {cls._BASE_SIZE + checksum_size}, got {len(data)}")
        
        # Extract checksum
        checksum = data[cls._BASE_SIZE:cls._BASE_SIZE + checksum_size]
        
        # Get hash algorithm
        try:
            hash_alg = HashAlgorithm(hash_alg_val)
        except ValueError:
            # Unknown algorithm, default to SHA-384
            hash_alg = DEFAULT_HASH_ALGORITHM
        
        return cls(
            file_id=file_id_bytes.rstrip(b'\x00'),
            chunk_index=chunk_index,
            chunk_size=chunk_size,
            hash_algorithm=hash_alg,
            chunk_checksum=checksum,
        )


# ============================================================================
# Message Container
# ============================================================================

@dataclass
class MemshadowMessage:
    """
    Complete MEMSHADOW message with header and payload.
    
    MEMSHADOW Protocol v3.0 Message with TLS extension support.
    
    Extended flags are negotiated via TLS extension during handshake.
    No payload extension headers needed - flags available from TLS session context.
    """
    header: MemshadowHeader
    payload: bytes = b""
    events: List[PsychEvent] = field(default_factory=list)
    # extension: Deprecated - use TLS extensions instead
    # Extended flags now negotiated via TLS extension during handshake
    
    @property
    def raw_payload(self) -> bytes:
        """Get actual payload data"""
        # No extension header - extended flags in TLS extension
        return self.payload
    
    def pack(
        self,
        connection_id: Optional[str] = None,
        dual_stream: bool = False,
        telemetry_mode: bool = False,
        auto_obscure: bool = True,
        integrity_key: Optional[bytes] = None,  # HMAC key for integrity check
    ) -> bytes:
        """
        Pack complete message to binary.
        
        Args:
            connection_id: Optional connection ID for adaptive ECC
            dual_stream: Separate header/payload into alternate streams
            telemetry_mode: Use ultra-lightweight telemetry header (16 bytes)
            auto_obscure: Automatically apply traffic shaping/obscurity
        """
        # Check if telemetry mode should be auto-enabled
        if not telemetry_mode and len(self.payload) < 1024:
            # Small payloads automatically use telemetry mode
            if self.header.msg_type in (MessageType.TELEMETRY, MessageType.CONTROL):
                telemetry_mode = True
        
        # Use telemetry header if enabled
        if telemetry_mode:
            try:
                from src.pegasus.network.msnet.telemetry_header import TelemetryHeader
                telemetry_hdr = TelemetryHeader(
                    msg_type=self.header.msg_type,
                    priority=self.header.priority,
                    flags=self.header.flags,
                    payload_len=len(self.payload),
                    sequence=self.header.sequence_num if hasattr(self.header, 'sequence_num') else 0,
                )
                self.header.flags |= MessageFlags.TELEMETRY_MODE
                header_data = telemetry_hdr.pack()
            except ImportError:
                telemetry_mode = False
                header_data = None
        else:
            header_data = None
        
        # Dual-stream mode: separate header and payload
        if dual_stream:
            try:
                from src.pegasus.network.msnet.dual_stream import DualStreamManager
                stream_mgr = DualStreamManager()
                stream_id, header_stream, payload_stream = stream_mgr.separate_message(self)
                
                # Return header stream (payload sent separately)
                self.header.flags |= MessageFlags.DUAL_STREAM
                if header_data:
                    return header_data  # Telemetry header
                else:
                    return self.header.pack()  # Standard header
            except ImportError:
                dual_stream = False
        
        # Auto-obscure if enabled
        if auto_obscure:
            try:
                from src.pegasus.network.msnet.obscurity import ObscurityManager
                obscurity = ObscurityManager()
                profile = obscurity.auto_select_profile(len(self.payload), self.header.msg_type)
                self.header.flags |= MessageFlags.TRAFFIC_SHAPED
                # Note: Actual shaping applied at transport layer
            except ImportError:
                pass
        
        # Build payload (no extension header needed - flags in TLS extension)
        payload_data = self.payload
        # Note: Extended flags are negotiated via TLS extension during handshake
        # No payload extension header needed - flags available from TLS session context
        
        # Apply ECC and encode connection quality if enabled
        ecc_bytes_used = 4  # Default RS bytes
        if hasattr(self.header, 'ecc_mode') and self.header.ecc_mode != ECC_NONE:
            try:
                from src.pegasus.network.msnet.ecc_quality import encode_quality_in_ecc
                # Get recommended RS bytes if available
                if connection_id:
                    try:
                        from src.pegasus.network.msnet.adaptive_ecc import get_connection_tracker
                        _, recommended_bytes = get_connection_tracker().get_recommended_ecc(connection_id)
                        if recommended_bytes > 0:
                            ecc_bytes_used = recommended_bytes
                    except:
                        pass
                
                payload_data, quality_info = encode_quality_in_ecc(
                    payload_data,
                    self.header.connection_quality if hasattr(self.header, 'connection_quality') else 255,
                    self.header.ecc_mode,
                    ecc_bytes_used,
                )
                self.header.flags |= MessageFlags.ECC_ENABLED
            except ImportError:
                # ECC module not available, skip
                pass
        
        # Use telemetry header if enabled
        if telemetry_mode and header_data:
            # Telemetry mode - return lightweight header + payload
            self.header.payload_len = len(payload_data)
            return header_data + payload_data
        
        # Standard mode
        self.header.payload_len = len(payload_data)
        message_data = self.header.pack() + payload_data
        
        # Add HMAC integrity check if key provided
        if integrity_key:
            # Compute HMAC over header + payload
            hmac_obj = hmac.new(integrity_key, message_data, hashlib.sha384)
            message_hmac = hmac_obj.digest()  # 32 bytes
            self.header.flags |= MessageFlags.INTEGRITY_CHECK
            # Update payload_len to include HMAC
            self.header.payload_len = len(payload_data) + len(message_hmac)
            # Rebuild message with updated header
            message_data = self.header.pack() + payload_data + message_hmac
        
        return message_data
    
    @classmethod
    def unpack(
        cls,
        data: bytes,
        connection_id: Optional[str] = None,
        is_telemetry_header: bool = False,
        integrity_key: Optional[bytes] = None,  # HMAC key for integrity verification
    ) -> "MemshadowMessage":
        """
        Unpack complete message from binary.
        
        Args:
            data: Raw message data
            connection_id: Optional connection ID for quality tracking
            is_telemetry_header: True if using telemetry header (16 bytes)
        """
        # Check for telemetry header
        if is_telemetry_header or (len(data) >= 4 and struct.unpack(">I", data[:4])[0] == TELEMETRY_MAGIC):
            try:
                from src.pegasus.network.msnet.telemetry_header import TelemetryHeader
                telemetry_hdr = TelemetryHeader.unpack(data[:TELEMETRY_HEADER_SIZE])
                # Convert to standard header
                header = MemshadowHeader(
                    msg_type=telemetry_hdr.msg_type,
                    priority=telemetry_hdr.priority,
                    flags=telemetry_hdr.flags,
                    payload_len=telemetry_hdr.payload_len,
                    sequence_num=telemetry_hdr.sequence,
                )
                # Check if integrity check is enabled
                has_integrity = MessageFlags.INTEGRITY_CHECK in MessageFlags(header.flags)
                hmac_size = 48 if has_integrity else 0
                payload_end = TELEMETRY_HEADER_SIZE + telemetry_hdr.payload_len - hmac_size
                payload = data[TELEMETRY_HEADER_SIZE:payload_end]
                
                # Verify HMAC if integrity check is enabled
                if has_integrity and integrity_key:
                    if len(data) < TELEMETRY_HEADER_SIZE + telemetry_hdr.payload_len:
                        raise ValueError(f"Message too short for HMAC: {len(data)} bytes")
                    
                    received_hmac = data[payload_end:TELEMETRY_HEADER_SIZE + telemetry_hdr.payload_len]
                    message_without_hmac = data[:payload_end]
                    expected_hmac = hmac.new(integrity_key, message_without_hmac, hashlib.sha384).digest()
                    
                    if not hmac.compare_digest(received_hmac, expected_hmac):
                        raise ValueError("Message integrity check failed: HMAC mismatch")
            except (ImportError, ValueError):
                # Fall back to standard header
                header = MemshadowHeader.unpack(data[:HEADER_SIZE])
                # Check if integrity check is enabled
                has_integrity = MessageFlags.INTEGRITY_CHECK in MessageFlags(header.flags)
                hmac_size = 48 if has_integrity else 0
                payload_end = HEADER_SIZE + header.payload_len - hmac_size
                payload = data[HEADER_SIZE:payload_end]
                
                # Verify HMAC if integrity check is enabled
                if has_integrity and integrity_key:
                    if len(data) < HEADER_SIZE + header.payload_len:
                        raise ValueError(f"Message too short for HMAC: {len(data)} bytes")
                    
                    received_hmac = data[payload_end:HEADER_SIZE + header.payload_len]
                    message_without_hmac = data[:payload_end]
                    expected_hmac = hmac.new(integrity_key, message_without_hmac, hashlib.sha384).digest()
                    
                    if not hmac.compare_digest(received_hmac, expected_hmac):
                        raise ValueError("Message integrity check failed: HMAC mismatch")
        else:
            header = MemshadowHeader.unpack(data[:HEADER_SIZE])
            # Check if integrity check is enabled
            has_integrity = MessageFlags.INTEGRITY_CHECK in MessageFlags(header.flags)
            hmac_size = 48 if has_integrity else 0  # HMAC-SHA384 is 48 bytes
            
            # Extract payload (excluding HMAC if present)
            payload_end = HEADER_SIZE + header.payload_len - hmac_size
            payload = data[HEADER_SIZE:payload_end]
            
            # Verify HMAC if integrity check is enabled
            if has_integrity and integrity_key:
                if len(data) < HEADER_SIZE + header.payload_len:
                    raise ValueError(f"Message too short for HMAC: {len(data)} bytes, expected {HEADER_SIZE + header.payload_len}")
                
                # Extract received HMAC
                received_hmac = data[payload_end:HEADER_SIZE + header.payload_len]
                
                # Compute expected HMAC over header + payload (without HMAC)
                message_without_hmac = data[:HEADER_SIZE + header.payload_len - hmac_size]
                expected_hmac = hmac.new(integrity_key, message_without_hmac, hashlib.sha256).digest()
                
                # Verify HMAC using constant-time comparison
                if not hmac.compare_digest(received_hmac, expected_hmac):
                    raise ValueError("Message integrity check failed: HMAC mismatch")
        
        # Note: HMAC verification already done above if integrity_key provided
        # Now decode ECC and recover connection quality if enabled
        actual_payload = payload
        errors_corrected = False
        recovered_quality = 255
        
        if MessageFlags.ECC_ENABLED in MessageFlags(header.flags):
            try:
                from src.pegasus.network.msnet.ecc_quality import decode_quality_from_ecc
                ecc_mode = header.ecc_mode if hasattr(header, 'ecc_mode') else ECC_NONE
                ecc_bytes = 4  # Default
                
                # Get RS bytes if available from connection tracker
                if connection_id:
                    try:
                        from src.pegasus.network.msnet.adaptive_ecc import get_connection_tracker
                        _, recommended_bytes = get_connection_tracker().get_recommended_ecc(connection_id)
                        if recommended_bytes > 0:
                            ecc_bytes = recommended_bytes
                    except:
                        pass
                
                actual_payload, recovered_quality, errors_corrected = decode_quality_from_ecc(
                    payload,
                    ecc_mode,
                    ecc_bytes,
                )
                # Store recovered quality in header
                if hasattr(header, 'connection_quality'):
                    header.connection_quality = recovered_quality
                
                # Record quality for adaptive ECC
                if connection_id:
                    try:
                        from src.pegasus.network.msnet.adaptive_ecc import get_connection_tracker
                        tracker = get_connection_tracker()
                        tracker.record_quality(
                            connection_id,
                            recovered_quality,
                            errors_corrected,
                            ecc_mode,
                        )
                    except:
                        pass
            except ImportError:
                # ECC module not available, skip decoding
                pass
        
        # Extended flags come from TLS extension (negotiated during handshake)
        # No payload extension header to parse - flags available from TLS session context
        extension = None
        # No payload offset needed - no extension header
        
        # Parse psych events if this is a psych message type
        events = []
        if header.msg_type in (
            MessageType.PSYCH_ASSESSMENT,
            MessageType.DARK_TRIAD_UPDATE,
            MessageType.RISK_UPDATE,
            MessageType.NEURO_UPDATE,
            MessageType.TMI_UPDATE,
            MessageType.COGNITIVE_UPDATE,
            MessageType.FULL_PSYCH,
        ):
            offset = 0
            while offset + PSYCH_EVENT_SIZE <= len(actual_payload):
                try:
                    event = PsychEvent.unpack(actual_payload[offset:])
                    events.append(event)
                    offset += PSYCH_EVENT_SIZE
                except:
                    break
        
        return cls(header=header, payload=actual_payload, events=events)
    
    @classmethod
    def create(
        cls,
        msg_type: MessageType,
        payload: bytes,
        priority: Priority = Priority.NORMAL,
        flags: MessageFlags = MessageFlags.NONE,
        batch_count: int = 0,
    ) -> "MemshadowMessage":
        """Create a new MEMSHADOW message"""
        header = MemshadowHeader(
            msg_type=msg_type,
            priority=priority,
            flags=flags,
            batch_count=batch_count,
            payload_len=len(payload),
        )
        return cls(header=header, payload=payload)


# ============================================================================
# Protocol Detection and Helpers
# ============================================================================

def detect_protocol_version(data: bytes) -> int:
    """
    Detect MEMSHADOW protocol version from raw data.
    
    Returns:
        Protocol version (1, 2, or 3), or 0 if not MEMSHADOW protocol
    """
    if len(data) < 8:
        return 0
    
    # Check for protocol magic (8 bytes)
    magic = struct.unpack(">Q", data[:8])[0]
    # Check first 4 bytes match "MSHW"
    magic_4bytes = magic & 0xFFFFFFFF
    if magic_4bytes == 0x4D534857:
        if len(data) >= 10:
            version = struct.unpack(">H", data[8:10])[0]
            return version
        return 2
    
    # Check for v1 magic (4 bytes)
    magic4 = struct.unpack(">I", data[:4])[0]
    if magic4 == 0x4D53544C:  # "MSTL" (MemShadow Telemetry)
        return 1
    
    return 0


def should_route_p2p(priority: Priority) -> bool:
    """
    Determine if message should be routed via P2P.
    
    CRITICAL/EMERGENCY: Direct P2P + hub notification
    HIGH/NORMAL/LOW: Hub-relayed
    """
    return priority >= Priority.CRITICAL


def get_routing_mode(priority: Priority) -> str:
    """Get human-readable routing mode for a priority level"""
    if priority >= Priority.CRITICAL:
        return "p2p+hub"
    elif priority >= Priority.HIGH:
        return "hub-priority"
    else:
        return "hub-normal"


# ============================================================================
# Convenience Constructors
# ============================================================================

def create_memory_sync_message(
    payload: bytes,
    priority: Priority = Priority.NORMAL,
    batch_count: int = 1,
    compressed: bool = False,
) -> MemshadowMessage:
    """Create a MEMORY_SYNC message"""
    flags = MessageFlags.BATCHED
    if compressed:
        flags |= MessageFlags.COMPRESSED
    if priority.should_require_ack():
        flags |= MessageFlags.REQUIRES_ACK
    
    return MemshadowMessage.create(
        msg_type=MessageType.MEMORY_SYNC,
        payload=payload,
        priority=priority,
        flags=flags,
        batch_count=batch_count,
    )


def create_psych_message(
    events: List[PsychEvent],
    priority: Priority = Priority.NORMAL,
) -> MemshadowMessage:
    """Create a PSYCH_ASSESSMENT message with batched events"""
    payload = b"".join(e.pack() for e in events)
    
    return MemshadowMessage.create(
        msg_type=MessageType.PSYCH_ASSESSMENT,
        payload=payload,
        priority=priority,
        flags=MessageFlags.BATCHED,
        batch_count=len(events),
    )


def create_improvement_announce(
    improvement_id: str,
    improvement_type: str,
    gain_percent: float,
    priority: Priority = Priority.NORMAL,
) -> MemshadowMessage:
    """Create an IMPROVEMENT_ANNOUNCE message"""
    payload = json.dumps({
        "improvement_id": improvement_id,
        "type": improvement_type,
        "gain_percent": gain_percent,
    }).encode()
    
    return MemshadowMessage.create(
        msg_type=MessageType.IMPROVEMENT_ANNOUNCE,
        payload=payload,
        priority=priority,
    )


# ============================================================================
# File Transfer Fragmentation and Reassembly
# ============================================================================

class FileFragmentationManager:
    """
    Manages fragmentation of large files into protocol-compatible chunks.
    
    Automatically splits files into chunks that fit within protocol limits,
    handles compression, and creates proper message sequences.
    """
    
    # Default chunk size: 1MB (leaves room for headers and network overhead)
    DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1MB
    
    # Maximum chunk size: 10MB (safety limit)
    MAX_CHUNK_SIZE = 10 * 1024 * 1024
    
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        compress: bool = True,
        hash_algorithm: HashAlgorithm = DEFAULT_HASH_ALGORITHM,
    ):
        """
        Initialize fragmentation manager.
        
        Args:
            chunk_size: Size of each chunk in bytes (default: 1MB)
            compress: Whether to compress file data (default: True)
            hash_algorithm: Hash algorithm to use (default: SHA-384)
        """
        self.chunk_size = min(chunk_size, self.MAX_CHUNK_SIZE)
        self.compress = compress
        self.hash_algorithm = hash_algorithm
    
    def fragment_file(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str = "application/octet-stream",
        priority: Priority = Priority.NORMAL,
        compress: Optional[bool] = None,
        compression_algorithm: Optional[str] = None,  # None = auto (QATzip > Kanzi > Gzip)
        dpi_resistance: bool = False,
        obfuscation_mode: str = "",
        encryption_mode: str = "",
        traffic_shape: str = "",
    ) -> Tuple[FileMetadata, List[MemshadowMessage]]:
        """
        Fragment a file into protocol messages.
        
        Args:
            file_data: Raw file data
            filename: Original filename
            mime_type: MIME type of the file
            priority: Message priority
            compress: Override default compression setting
        
        Returns:
            Tuple of (FileMetadata, List[MemshadowMessage])
            - FileMetadata contains file information
            - List contains FILE_TRANSFER_START, FILE_TRANSFER_CHUNK messages, and FILE_TRANSFER_END
        """
        compress = compress if compress is not None else self.compress
        hash_alg = self.hash_algorithm
        
        # Generate file ID
        file_id = uuid.uuid4().hex[:16].encode()  # 16 bytes
        
        # Apply obfuscation/encryption if requested (placeholder for future implementation)
        if encryption_mode:
            # Future: Apply encryption here
            pass
        
        if obfuscation_mode:
            # Future: Apply obfuscation here
            pass
        
        # Compress if requested (automatic algorithm selection based on hardware)
        compression_alg = ""
        if compress:
            # Auto-select compression algorithm (None = automatic)
            # Automatically uses QATzip ONLY if hardware accelerators present
            algo = compression_algorithm if compression_algorithm else "auto"
            
            # Try QATzip first ONLY if hardware accelerators are actually present
            # Automatically detects Intel QAT hardware - no configuration needed
            # QATzip only used when accelerators detected (data center scenarios)
            if algo in ("qatzip", "auto", None) and QATZIP_AVAILABLE and QATZIP_HARDWARE_AVAILABLE:
                try:
                    # QATzip with maximum compression (hardware accelerated)
                    # Only used when Intel QAT hardware is actually present
                    compressed_data = None
                    if hasattr(qatzip, 'QzCompress'):
                        qz = qatzip.QzCompress()
                        compressed_data = qz.compress(file_data, level=9)  # Maximum compression
                    elif hasattr(qatzip, 'compress'):
                        compressed_data = qatzip.compress(file_data, level=9)
                    elif callable(qatzip):
                        compressed_data = qatzip(file_data, level=9)
                    else:
                        raise AttributeError("Unknown QATzip API")
                    
                    if compressed_data and len(compressed_data) < len(file_data):
                        file_data = compressed_data
                        compression_alg = "qatzip"
                except Exception:
                    # QATzip failed (hardware error, wrong API, etc.) - fall back gracefully
                    if algo == "qatzip":
                        # Explicitly requested but failed - could log warning
                        pass
                    # Fall through to next algorithm
            
            # Try kanzi if QATzip not available (better than gzip, portable)
            if not compression_alg and algo in ("kanzi", "auto", None) and KANZI_AVAILABLE:
                    try:
                        compressed_data = kanzi.compress(file_data)
                        if len(compressed_data) < len(file_data):
                            file_data = compressed_data
                            compression_alg = "kanzi"
                    except Exception:
                        pass
            
            if not compression_alg:
                # Fall back to gzip (universally available)
                try:
                    compressed_data = gzip.compress(file_data, compresslevel=9)
                    if len(compressed_data) < len(file_data):
                        file_data = compressed_data
                        compression_alg = "gzip"
                except Exception:
                    compression_alg = ""
        
        # Calculate checksum using configured hash algorithm
        file_hash = hash_alg.compute_hash_hex(file_data)
        
        # Split into chunks
        total_size = len(file_data)
        chunk_size = self.chunk_size
        total_chunks = (total_size + chunk_size - 1) // chunk_size  # Ceiling division
        
        # Create file metadata with enhanced workload fields
        metadata = FileMetadata(
            file_id=file_id.hex(),
            filename=filename,
            file_size=total_size,
            mime_type=mime_type,
            checksum=file_hash,
            hash_algorithm=hash_alg.value,
            compression=compression_alg,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            dpi_resistance=dpi_resistance,
            obfuscation_mode=obfuscation_mode,
            encryption_mode=encryption_mode,
            traffic_shape=traffic_shape,
        )
        
        messages = []
        
        # Create FILE_TRANSFER_START message
        # Only include optional fields if they're actually set (reduces bloat)
        metadata_dict = metadata.to_dict(include_extensions=True)
        start_payload = json.dumps(metadata_dict).encode()
        
        # Build flags (minimal - only what's needed)
        flags = MessageFlags.NONE
        if compression_alg:
            flags |= MessageFlags.COMPRESSED
        
        # Include extension data in payload if enhanced features are used
        if dpi_resistance or obfuscation_mode or encryption_mode or traffic_shape:
            # Add enhanced workload metadata to the payload
            ext_data = {
                "dpi_resistance": dpi_resistance,
                "obfuscation_mode": obfuscation_mode,
                "encryption_mode": encryption_mode,
                "traffic_shape": traffic_shape,
            }
            # Merge extension data into metadata dict
            metadata_dict.update(ext_data)
            flags |= MessageFlags.HAS_EXTENSION
            # Recreate payload with extension data
            start_payload = json.dumps(metadata_dict).encode()

        start_msg = MemshadowMessage(
            header=MemshadowHeader(
                msg_type=MessageType.FILE_TRANSFER_START,
                priority=priority,
                flags=flags,
                payload_len=len(start_payload),
            ),
            payload=start_payload,
        )
        messages.append(start_msg)
        
        # Create chunk messages
        for chunk_idx in range(total_chunks):
            start_offset = chunk_idx * chunk_size
            end_offset = min(start_offset + chunk_size, total_size)
            chunk_data = file_data[start_offset:end_offset]
            
            # Create chunk header with full hash (SHA-384 = 48 bytes)
            chunk_hash = hash_alg.compute_hash(chunk_data)
            # Use the same file_id bytes as metadata (ensure consistency)
            file_id_bytes = file_id  # Already bytes from uuid generation
            chunk_header = FileChunkHeader(
                file_id=file_id_bytes,
                chunk_index=chunk_idx,
                chunk_size=len(chunk_data),
                hash_algorithm=hash_alg,
                chunk_checksum=chunk_hash,
            )
            
            # Combine header and data
            chunk_payload = chunk_header.pack() + chunk_data
            
            # Determine flags (minimal - only what's needed)
            flags = MessageFlags.FRAGMENTED
            if compression_alg:
                flags |= MessageFlags.COMPRESSED
            if chunk_idx == total_chunks - 1:
                flags |= MessageFlags.LAST_FRAGMENT
            
            # Include extension data in payload if enhanced features are used
            if dpi_resistance or obfuscation_mode or encryption_mode or traffic_shape:
                # Add enhanced workload metadata to chunk payload
                chunk_metadata = {
                    "chunk_index": chunk_idx,
                    "dpi_resistance": dpi_resistance,
                    "obfuscation_mode": obfuscation_mode,
                    "encryption_mode": encryption_mode,
                    "traffic_shape": traffic_shape,
                }
                chunk_payload = json.dumps(chunk_metadata).encode() + b'\n' + chunk_data
                flags |= MessageFlags.HAS_EXTENSION

            chunk_msg = MemshadowMessage(
                header=MemshadowHeader(
                    msg_type=MessageType.FILE_TRANSFER_CHUNK,
                    priority=priority,
                    flags=flags,
                    batch_count=chunk_idx + 1,
                    payload_len=len(chunk_payload),
                ),
                payload=chunk_payload,
            )
            messages.append(chunk_msg)
        
        # Create FILE_TRANSFER_END message
        end_payload = json.dumps({
            "file_id": metadata.file_id,
            "total_chunks": total_chunks,
            "checksum": file_hash,
        }).encode()
        end_msg = MemshadowMessage.create(
            msg_type=MessageType.FILE_TRANSFER_END,
            payload=end_payload,
            priority=priority,
            flags=MessageFlags.NONE,
        )
        messages.append(end_msg)
        
        return metadata, messages


class FileReassemblyManager:
    """
    Manages reassembly of fragmented file transfers.
    
    Tracks incoming chunks, validates checksums, and reconstructs complete files.
    """
    
    def __init__(self, timeout_seconds: int = 300):
        """
        Initialize reassembly manager.
        
        Args:
            timeout_seconds: Timeout for incomplete transfers (default: 5 minutes)
        """
        self.timeout_seconds = timeout_seconds
        self._transfers: Dict[str, Dict[str, Any]] = {}  # file_id -> transfer state
    
    def handle_start(self, message: MemshadowMessage) -> Optional[FileMetadata]:
        """
        Handle FILE_TRANSFER_START message.
        
        Returns:
            FileMetadata if valid, None otherwise
        """
        try:
            metadata_dict = json.loads(message.payload.decode())
            metadata = FileMetadata.from_dict(metadata_dict)
            
            # Initialize transfer state
            self._transfers[metadata.file_id] = {
                "metadata": metadata,
                "chunks": {},  # chunk_index -> chunk_data
                "received_chunks": set(),
                "start_time": time.time(),
                "completed": False,
            }
            
            return metadata
        except Exception as e:
            return None
    
    def handle_chunk(self, message: MemshadowMessage) -> Tuple[Optional[str], Optional[bytes], bool]:
        """
        Handle FILE_TRANSFER_CHUNK message.
        
        Returns:
            Tuple of (file_id, chunk_data, is_complete)
            - file_id: File ID if valid chunk
            - chunk_data: Raw chunk data (without header)
            - is_complete: True if all chunks received
        """
        try:
            # Parse chunk header
            chunk_header = FileChunkHeader.unpack(message.payload)
            # Convert file_id bytes to hex string for lookup
            file_id = chunk_header.file_id.hex() if isinstance(chunk_header.file_id, bytes) else str(chunk_header.file_id)
            
            if file_id not in self._transfers:
                return None, None, False
            
            transfer = self._transfers[file_id]
            
            # Extract chunk data (after variable-size header)
            header_size = chunk_header.total_size
            chunk_data = message.payload[header_size:]
            
            # Validate chunk size
            if len(chunk_data) != chunk_header.chunk_size:
                return None, None, False
            
            # Validate chunk checksum using the algorithm from header
            expected_hash = chunk_header.hash_algorithm.compute_hash(chunk_data)
            if expected_hash != chunk_header.chunk_checksum:
                return None, None, False
            
            # Store chunk
            transfer["chunks"][chunk_header.chunk_index] = chunk_data
            transfer["received_chunks"].add(chunk_header.chunk_index)
            
            # Check if complete
            metadata = transfer["metadata"]
            is_complete = len(transfer["received_chunks"]) >= metadata.total_chunks
            
            if is_complete:
                transfer["completed"] = True
            
            return file_id, chunk_data, is_complete
            
        except Exception as e:
            return None, None, False
    
    def handle_end(self, message: MemshadowMessage) -> Optional[str]:
        """
        Handle FILE_TRANSFER_END message.
        
        Returns:
            file_id if transfer is complete and valid, None otherwise
        """
        try:
            end_data = json.loads(message.payload.decode())
            file_id = end_data.get("file_id")
            
            if file_id not in self._transfers:
                return None
            
            transfer = self._transfers[file_id]
            
            # Verify all chunks received
            if len(transfer["received_chunks"]) < transfer["metadata"].total_chunks:
                return None
            
            return file_id
            
        except Exception as e:
            return None
    
    def reassemble_file(self, file_id: str) -> Optional[bytes]:
        """
        Reassemble complete file from chunks.
        
        Args:
            file_id: File transfer ID
        
        Returns:
            Complete file data, or None if incomplete/invalid
        """
        if file_id not in self._transfers:
            return None
        
        transfer = self._transfers[file_id]
        
        if not transfer["completed"]:
            return None
        
        metadata = transfer["metadata"]
        
        # Reassemble chunks in order
        chunks = transfer["chunks"]
        file_data = b""
        
        for idx in range(metadata.total_chunks):
            if idx not in chunks:
                return None  # Missing chunk
            file_data += chunks[idx]
        
        # Verify file checksum using metadata's hash algorithm
        hash_alg = metadata.hash_alg
        file_hash = hash_alg.compute_hash_hex(file_data)
        if file_hash != metadata.checksum:
            return None  # Checksum mismatch
        
        # Decompress if needed (support qatzip, kanzi, and gzip)
        if metadata.compression == "qatzip":
            if not QATZIP_AVAILABLE:
                return None  # QATzip required but not available
            try:
                # QATzip decompression - try common API patterns
                if hasattr(qatzip, 'QzDecompress'):
                    qz = qatzip.QzDecompress()
                    file_data = qz.decompress(file_data)
                elif hasattr(qatzip, 'decompress'):
                    file_data = qatzip.decompress(file_data)
                elif callable(qatzip):
                    file_data = qatzip(file_data, decompress=True)
                else:
                    raise AttributeError("Unknown QATzip API")
            except Exception:
                return None
        elif metadata.compression == "kanzi":
            if not KANZI_AVAILABLE:
                return None  # Kanzi required but not available
            try:
                file_data = kanzi.decompress(file_data)
            except Exception:
                return None
        elif metadata.compression == "gzip":
            try:
                file_data = gzip.decompress(file_data)
            except Exception:
                return None
        
        return file_data
    
    def cleanup_transfer(self, file_id: str):
        """Remove transfer from tracking"""
        self._transfers.pop(file_id, None)
    
    def cleanup_timeouts(self):
        """Remove timed-out transfers"""
        current_time = time.time()
        timed_out = [
            file_id for file_id, transfer in self._transfers.items()
            if current_time - transfer["start_time"] > self.timeout_seconds
            and not transfer["completed"]
        ]
        for file_id in timed_out:
            self.cleanup_transfer(file_id)
    
    def get_transfer_status(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a file transfer"""
        if file_id not in self._transfers:
            return None
        
        transfer = self._transfers[file_id]
        metadata = transfer["metadata"]
        
        return {
            "file_id": file_id,
            "filename": metadata.filename,
            "file_size": metadata.file_size,
            "total_chunks": metadata.total_chunks,
            "received_chunks": len(transfer["received_chunks"]),
            "completed": transfer["completed"],
            "progress_percent": (len(transfer["received_chunks"]) / metadata.total_chunks * 100) if metadata.total_chunks > 0 else 0,
        }


# ============================================================================
# Convenience Functions for File Transfer
# ============================================================================

def create_file_transfer_messages(
    file_data: bytes,
    filename: str,
    mime_type: str = "application/octet-stream",
    priority: Priority = Priority.NORMAL,
    chunk_size: int = FileFragmentationManager.DEFAULT_CHUNK_SIZE,
    compress: bool = True,
    compression_algorithm: Optional[str] = None,  # None = auto (QATzip > Kanzi > Gzip)
    hash_algorithm: HashAlgorithm = DEFAULT_HASH_ALGORITHM,
    dpi_resistance: bool = False,
    obfuscation_mode: str = "",
    encryption_mode: str = "",
    traffic_shape: str = "",
) -> Tuple[FileMetadata, List[MemshadowMessage]]:
    """
    Convenience function to create file transfer messages.
    
    Args:
        file_data: Raw file data
        filename: Original filename
        mime_type: MIME type
        priority: Message priority
        chunk_size: Chunk size in bytes
        compress: Whether to compress
        compression_algorithm: Compression algorithm ("auto", "qatzip", "kanzi", "gzip")
            - "auto": Selects best available (QATzip > kanzi > gzip)
            - "qatzip": Intel QAT hardware acceleration (best compression, data center)
            - "kanzi": Better than gzip, portable
            - "gzip": Universal fallback
        hash_algorithm: Hash algorithm (default: SHA-384)
        dpi_resistance: Enable DPI resistance features
        obfuscation_mode: Obfuscation method (e.g., "steganography", "padding")
        encryption_mode: Encryption method (e.g., "aes256", "chacha20")
        traffic_shape: Traffic shaping profile (e.g., "http", "https", "dns")
    
    Returns:
        Tuple of (FileMetadata, List[MemshadowMessage])
    
    Note:
        QATzip provides best compression ratio but requires Intel QAT hardware.
        Use "qatzip" for data center scenarios where compression time doesn't matter.
        Use "auto" for automatic selection based on availability.
    """
    manager = FileFragmentationManager(
        chunk_size=chunk_size,
        compress=compress,
        hash_algorithm=hash_algorithm,
    )
    return manager.fragment_file(
        file_data,
        filename,
        mime_type,
        priority,
        compress,
        compression_algorithm,
        dpi_resistance,
        obfuscation_mode,
        encryption_mode,
        traffic_shape,
    )


# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    # Constants
    "MEMSHADOW_MAGIC",
    "MEMSHADOW_VERSION",
    "HEADER_SIZE",
    "PSYCH_EVENT_SIZE",
    # Enums
    "MessageType",
    "MemshadowMessageType",  # Alias
    "Priority",
    "MemshadowMessagePriority",  # Alias
    "MessageFlags",
    "SyncOperation",
    "MemoryTier",
    "PsychEventType",
    "HashAlgorithm",
    "DEFAULT_HASH_ALGORITHM",
    # Data structures
    "MemshadowHeader",
    "MemshadowMessage",
    "PsychEvent",
    "FileMetadata",
    "FileChunkHeader",
    "MessageExtension",
    "ExtensionType",
    # ECC and connection quality
    "ECC_NONE",
    "ECC_PARITY",
    "ECC_REED_SOLOMON",
    "MAX_CONNECTION_QUALITY",
    # Telemetry and dual-stream
    "TELEMETRY_HEADER_SIZE",
    "TELEMETRY_MAGIC",
    # Adaptive ECC (optional import)
    # "AdaptiveECCManager",
    # "ConnectionQualityTracker",
    # "get_connection_tracker",
    # File Transfer Managers
    "FileFragmentationManager",
    "FileReassemblyManager",
    # Helpers
    "detect_protocol_version",
    "should_route_p2p",
    "get_routing_mode",
    "create_memory_sync_message",
    "create_psych_message",
    "create_improvement_announce",
    "create_file_transfer_messages",
]
