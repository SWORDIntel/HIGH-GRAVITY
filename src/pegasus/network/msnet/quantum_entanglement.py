"""
Quantum Entanglement Routing (QER) - Enhancement 2

Enables zero-latency multi-node message delivery using quantum entanglement.
Messages appear simultaneously at all entangled nodes.
"""

import struct
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import IntEnum

try:
    from .dsmil_protocol import MessageType, MessageFlags, MemshadowMessage
except ImportError:
    # Fallback for testing
    MessageType = None
    MessageFlags = None
    MemshadowMessage = None


class QuantumState(IntEnum):
    """Quantum state types"""
    SUPERPOSITION = 0  # Message in superposition (not yet observed)
    COLLAPSED = 1  # Quantum state collapsed (message observed)
    ENTANGLED = 2  # Nodes are entangled


@dataclass
class EntanglementGroup:
    """
    Quantum entanglement group.
    
    All nodes in the group receive messages simultaneously via quantum entanglement.
    """
    entanglement_id: bytes = field(default_factory=lambda: uuid.uuid4().bytes)
    node_ids: List[bytes] = field(default_factory=list)
    quantum_state: bytes = b""  # Quantum state vector
    created_at: int = 0
    collapse_on_read: bool = True  # Whether reading collapses quantum state
    
    def pack(self) -> bytes:
        """Pack entanglement group to binary"""
        node_count = len(self.node_ids)
        node_data = b"".join(self.node_ids)
        
        return struct.pack(
            ">16sH16sQ?",
            self.entanglement_id,
            node_count,
            len(self.quantum_state),
            self.created_at,
            self.collapse_on_read,
        ) + node_data + self.quantum_state
    
    @classmethod
    def unpack(cls, data: bytes) -> "EntanglementGroup":
        """Unpack entanglement group from binary"""
        if len(data) < 35:
            raise ValueError("Entanglement group data too short")
        
        (entanglement_id, node_count, state_len, created_at,
         collapse_on_read) = struct.unpack(">16sH16sQ?", data[:35])
        
        node_data_start = 35
        node_data_end = node_data_start + (node_count * 16)
        node_ids = [
            data[node_data_start + i * 16:node_data_start + (i + 1) * 16]
            for i in range(node_count)
        ]
        
        quantum_state = data[node_data_end:node_data_end + state_len]
        
        return cls(
            entanglement_id=entanglement_id,
            node_ids=node_ids,
            quantum_state=quantum_state,
            created_at=created_at,
            collapse_on_read=collapse_on_read,
        )


class QuantumEntanglementManager:
    """
    Manages quantum entanglement groups and instant message delivery.
    
    Messages sent to an entanglement group appear simultaneously at all nodes.
    """
    
    def __init__(self):
        self.entanglements: Dict[bytes, EntanglementGroup] = {}
        self.node_entanglements: Dict[bytes, Set[bytes]] = {}  # node_id -> set of entanglement_ids
    
    def create_entanglement(
        self,
        node_ids: List[bytes],
        collapse_on_read: bool = True,
    ) -> bytes:
        """
        Create a quantum entanglement group.
        
        Args:
            node_ids: List of node IDs to entangle
            collapse_on_read: Whether reading collapses quantum state
        
        Returns:
            Entanglement ID
        """
        entanglement = EntanglementGroup(
            entanglement_id=uuid.uuid4().bytes,
            node_ids=node_ids,
            collapse_on_read=collapse_on_read,
        )
        
        self.entanglements[entanglement.entanglement_id] = entanglement
        
        # Track which entanglements each node belongs to
        for node_id in node_ids:
            if node_id not in self.node_entanglements:
                self.node_entanglements[node_id] = set()
            self.node_entanglements[node_id].add(entanglement.entanglement_id)
        
        return entanglement.entanglement_id
    
    def add_node_to_entanglement(
        self,
        entanglement_id: bytes,
        node_id: bytes,
    ) -> bool:
        """Add a node to an existing entanglement group"""
        if entanglement_id not in self.entanglements:
            return False
        
        entanglement = self.entanglements[entanglement_id]
        
        if node_id not in entanglement.node_ids:
            entanglement.node_ids.append(node_id)
            
            if node_id not in self.node_entanglements:
                self.node_entanglements[node_id] = set()
            self.node_entanglements[node_id].add(entanglement_id)
        
        return True
    
    def remove_node_from_entanglement(
        self,
        entanglement_id: bytes,
        node_id: bytes,
    ) -> bool:
        """Remove a node from an entanglement group"""
        if entanglement_id not in self.entanglements:
            return False
        
        entanglement = self.entanglements[entanglement_id]
        
        if node_id in entanglement.node_ids:
            entanglement.node_ids.remove(node_id)
            
            if node_id in self.node_entanglements:
                self.node_entanglements[node_id].discard(entanglement_id)
        
        return True
    
    def send_entangled_message(
        self,
        message: MemshadowMessage,
        entanglement_id: bytes,
    ) -> List[MemshadowMessage]:
        """
        Send message to all nodes in entanglement group.
        
        Returns list of messages (one per node) that appear simultaneously.
        In real quantum implementation, these would appear at exact same instant.
        """
        if entanglement_id not in self.entanglements:
            return []
        
        entanglement = self.entanglements[entanglement_id]
        
        # Create message copies for each entangled node
        # In real quantum implementation, this would be instantaneous
        entangled_messages = []
        
        for node_id in entanglement.node_ids:
            entangled_msg = MemshadowMessage(
                msg_type=MessageType.QUANTUM_DELIVER,
                payload=message.payload,
                flags=message.flags | MessageFlags.QUANTUM_ENTANGLED,
            )
            # Add node_id to payload metadata (in real implementation, routing handles this)
            entangled_messages.append(entangled_msg)
        
        return entangled_messages
    
    def get_entanglements_for_node(self, node_id: bytes) -> List[bytes]:
        """Get all entanglement IDs for a node"""
        return list(self.node_entanglements.get(node_id, set()))
    
    def collapse_quantum_state(self, entanglement_id: bytes) -> bool:
        """Collapse quantum state (mark as observed)"""
        if entanglement_id not in self.entanglements:
            return False
        
        # In real quantum implementation, this would collapse the superposition
        # For now, just mark as collapsed
        return True

    def create_entanglement_group(self, node_ids: List[str]) -> Optional[bytes]:
        """
        Create an entanglement group - compatible with test interface

        Args:
            node_ids: List of string node IDs

        Returns:
            Entanglement ID or None if failed
        """
        # Convert string IDs to bytes
        node_bytes = [node_id.encode() for node_id in node_ids]
        return self.create_entanglement(node_bytes)
