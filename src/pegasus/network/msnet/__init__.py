"""
MEMSHADOW Protocol v3.0 - Complete Python Implementation
Natively Integrated into HIGH-GRAVITY Pegasus Swarm
"""

import sys
from typing import Optional, Tuple, Union

# Version information
from ._version import __version__, get_version, get_version_tuple, is_compatible

# Core protocol implementation
from .dsmil_protocol import (
    MEMSHADOW_MAGIC, MEMSHADOW_VERSION, HEADER_SIZE, ECC_NONE, MessageType,
    MemshadowHeader, MemshadowMessage, FileMetadata
)

# Exotic enhancement modules
from .temporal_queue import TemporalQueue, TemporalMessage, TemporalMode
from .quantum_entanglement import QuantumEntanglementManager, EntanglementGroup
from .morphic_adaptation import MorphicAdaptationManager

# Large local network support
from .peer_manager import MemshadowPeerManager, PeerInfo, PeerStatus
from .relay_system import MemshadowRelay, RelayResult

__all__ = [
    "__version__", "get_version", "MEMSHADOW_MAGIC", "MEMSHADOW_VERSION",
    "TemporalQueue", "QuantumEntanglementManager", "MorphicAdaptationManager",
    "MemshadowPeerManager", "MemshadowRelay"
]
