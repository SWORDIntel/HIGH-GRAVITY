"""
MEMSHADOW Protocol - Gossip Protocol

Implements epidemic broadcast and anti-entropy for fully decentralized
peer discovery and state synchronization without central servers.
"""

import asyncio
import hashlib
import time
import random
from typing import Dict, List, Set, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import IntEnum
from collections import deque


class GossipMessageType(IntEnum):
    """Gossip message types"""
    MEMBERSHIP = 1  # Node membership information
    STATE = 2  # State synchronization
    ANTI_ENTROPY = 3  # Anti-entropy reconciliation
    RUMOR = 4  # Rumor mongering (epidemic broadcast)


@dataclass
class GossipMessage:
    """Gossip protocol message"""
    message_type: GossipMessageType
    sender_id: str
    sequence_number: int
    payload: bytes
    timestamp: float = field(default_factory=time.time)
    ttl: int = 10  # Time-to-live (hop count)
    signature: Optional[bytes] = None


@dataclass
class NodeState:
    """Node state information"""
    node_id: str
    address: str
    port: int
    capabilities: Set[str]
    last_seen: float = field(default_factory=time.time)
    version: int = 0  # State version for anti-entropy
    metadata: Dict = field(default_factory=dict)


class EpidemicBroadcast:
    """
    Epidemic broadcast (rumor mongering)
    
    Spreads messages through the network using probabilistic flooding.
    Each node forwards messages to random neighbors.
    """
    
    def __init__(self, fanout: int = 3, probability: float = 0.5):
        """
        Args:
            fanout: Number of random neighbors to forward to
            probability: Probability of forwarding (for probabilistic flooding)
        """
        self.fanout = fanout
        self.probability = probability
        self.received_messages: Set[bytes] = set()  # Message hashes
        self.message_history: deque = deque(maxlen=10000)  # Recent messages
    
    def should_forward(self, message_hash: bytes) -> bool:
        """
        Decide if should forward message
        
        Uses probabilistic flooding to reduce network load.
        """
        if message_hash in self.received_messages:
            return False  # Already received
        
        # Probabilistic forwarding
        return random.random() < self.probability
    
    def mark_received(self, message_hash: bytes):
        """Mark message as received"""
        self.received_messages.add(message_hash)
    
    def get_random_neighbors(self, all_neighbors: List[str], count: int) -> List[str]:
        """Get random neighbors for forwarding"""
        if len(all_neighbors) <= count:
            return all_neighbors
        return random.sample(all_neighbors, count)
    
    def create_rumor(self, sender_id: str, payload: bytes, sequence: int) -> GossipMessage:
        """Create rumor message for epidemic broadcast"""
        return GossipMessage(
            message_type=GossipMessageType.RUMOR,
            sender_id=sender_id,
            sequence_number=sequence,
            payload=payload,
            ttl=10
        )
    
    def should_process(self, message: GossipMessage) -> bool:
        """Check if should process message"""
        message_hash = self._hash_message(message)
        
        if message_hash in self.received_messages:
            return False  # Already processed
        
        if message.ttl <= 0:
            return False  # TTL expired
        
        return True
    
    def _hash_message(self, message: GossipMessage) -> bytes:
        """Compute message hash"""
        data = f"{message.sender_id}:{message.sequence_number}:{message.message_type}".encode()
        return hashlib.sha256(data).digest()


class AntiEntropy:
    """
    Anti-entropy for state reconciliation
    
    Ensures eventual consistency by comparing and merging states.
    """
    
    def __init__(self):
        self.local_state: Dict[str, NodeState] = {}
        self.state_versions: Dict[str, int] = {}  # node_id -> version
    
    def get_state_digest(self) -> bytes:
        """Get digest of local state for comparison"""
        # Create Merkle-like digest of all states
        state_strings = []
        for node_id, state in sorted(self.local_state.items()):
            state_str = f"{node_id}:{state.version}:{state.last_seen}"
            state_strings.append(state_str)
        
        combined = "\n".join(state_strings).encode()
        return hashlib.sha256(combined).digest()
    
    def compare_states(
        self,
        peer_digest: bytes,
        peer_states: Dict[str, NodeState]
    ) -> Tuple[List[str], List[str]]:
        """
        Compare states with peer
        
        Returns:
            (nodes_to_send, nodes_to_request)
        """
        local_digest = self.get_state_digest()
        
        if local_digest == peer_digest:
            return [], []  # States are identical
        
        # Find differences
        nodes_to_send = []
        nodes_to_request = []
        
        # Check nodes we have that peer might not have
        for node_id, state in self.local_state.items():
            if node_id not in peer_states:
                nodes_to_send.append(node_id)
            elif state.version > peer_states[node_id].version:
                nodes_to_send.append(node_id)
        
        # Check nodes peer has that we might not have
        for node_id, state in peer_states.items():
            if node_id not in self.local_state:
                nodes_to_request.append(node_id)
            elif state.version > self.local_state[node_id].version:
                nodes_to_request.append(node_id)
        
        return nodes_to_send, nodes_to_request
    
    def merge_state(self, node_state: NodeState):
        """Merge node state into local state"""
        if node_state.node_id not in self.local_state:
            self.local_state[node_state.node_id] = node_state
            self.state_versions[node_state.node_id] = node_state.version
        elif node_state.version > self.local_state[node_state.node_id].version:
            # Update with newer version
            self.local_state[node_state.node_id] = node_state
            self.state_versions[node_state.node_id] = node_state.version
    
    def get_states_to_send(self, node_ids: List[str]) -> List[NodeState]:
        """Get states for specific nodes"""
        return [self.local_state[nid] for nid in node_ids if nid in self.local_state]


class MembershipManager:
    """
    Membership management using gossip
    
    Tracks which nodes are in the network using gossip protocol.
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.members: Dict[str, NodeState] = {}
        self.suspected: Set[str] = set()  # Nodes suspected of being dead
        self.failed: Set[str] = set()  # Nodes confirmed failed
        self.failure_detector_timeout = 30.0  # Seconds before suspecting failure
    
    def add_member(self, node_state: NodeState):
        """Add or update member"""
        self.members[node_state.node_id] = node_state
        node_state.last_seen = time.time()
        
        # Remove from suspected/failed if rejoined
        self.suspected.discard(node_state.node_id)
        self.failed.discard(node_state.node_id)
    
    def remove_member(self, node_id: str):
        """Remove member"""
        if node_id in self.members:
            del self.members[node_id]
        self.failed.add(node_id)
        self.suspected.discard(node_id)
    
    def suspect_failure(self, node_id: str):
        """Mark node as suspected of failure"""
        if node_id in self.members:
            self.suspected.add(node_id)
    
    def check_failures(self):
        """Check for failed nodes based on timeout"""
        current_time = time.time()
        failed_nodes = []
        
        for node_id, state in list(self.members.items()):
            if node_id == self.node_id:
                continue
            
            age = current_time - state.last_seen
            if age > self.failure_detector_timeout:
                if node_id in self.suspected:
                    # Confirmed failure
                    failed_nodes.append(node_id)
                    self.remove_member(node_id)
                else:
                    # Suspect failure
                    self.suspect_failure(node_id)
        
        return failed_nodes
    
    def get_live_members(self) -> List[NodeState]:
        """Get list of live members (not suspected or failed)"""
        return [
            state for node_id, state in self.members.items()
            if node_id not in self.suspected and node_id not in self.failed
        ]
    
    def get_random_members(self, count: int, exclude: Optional[Set[str]] = None) -> List[NodeState]:
        """Get random members for gossip"""
        live = self.get_live_members()
        
        if exclude:
            live = [m for m in live if m.node_id not in exclude]
        
        if len(live) <= count:
            return live
        
        return random.sample(live, count)


class GossipProtocol:
    """
    Main gossip protocol implementation
    
    Coordinates epidemic broadcast, anti-entropy, and membership management.
    """
    
    def __init__(self, node_id: str, address: str, port: int):
        self.node_id = node_id
        self.address = address
        self.port = port
        
        self.epidemic = EpidemicBroadcast()
        self.anti_entropy = AntiEntropy()
        self.membership = MembershipManager(node_id)
        
        self.sequence_counter = 0
        self.running = False
        self.gossip_interval = 5.0  # Seconds between gossip rounds
        
        # Callbacks
        self.on_message_received: Optional[Callable[[GossipMessage], None]] = None
        self.on_member_added: Optional[Callable[[NodeState], None]] = None
        self.on_member_removed: Optional[Callable[[str], None]] = None
    
    def start(self):
        """Start gossip protocol"""
        self.running = True
        
        # Add self to membership
        self_state = NodeState(
            node_id=self.node_id,
            address=self.address,
            port=self.port,
            capabilities=set(),
            version=1
        )
        self.membership.add_member(self_state)
        self.anti_entropy.local_state[self.node_id] = self_state
        
        # Start gossip loop
        asyncio.create_task(self._gossip_loop())
        asyncio.create_task(self._anti_entropy_loop())
        asyncio.create_task(self._failure_detection_loop())
    
    def stop(self):
        """Stop gossip protocol"""
        self.running = False
    
    async def _gossip_loop(self):
        """Main gossip loop - epidemic broadcast"""
        while self.running:
            try:
                # Get random neighbors
                neighbors = self.membership.get_random_members(
                    self.epidemic.fanout,
                    exclude={self.node_id}
                )
                
                if neighbors:
                    # Create membership update message
                    message = self._create_membership_message()
                    
                    # Forward to neighbors
                    for neighbor in neighbors:
                        await self._send_gossip_message(neighbor, message)
                
                await asyncio.sleep(self.gossip_interval)
            
            except Exception as e:
                print(f"Gossip loop error: {e}")
                await asyncio.sleep(self.gossip_interval)
    
    async def _anti_entropy_loop(self):
        """Anti-entropy reconciliation loop"""
        while self.running:
            try:
                # Get random neighbor for anti-entropy
                neighbors = self.membership.get_random_members(1, exclude={self.node_id})
                
                if neighbors:
                    neighbor = neighbors[0]
                    await self._perform_anti_entropy(neighbor)
                
                await asyncio.sleep(self.gossip_interval * 2)  # Less frequent
            
            except Exception as e:
                print(f"Anti-entropy loop error: {e}")
                await asyncio.sleep(self.gossip_interval * 2)
    
    async def _failure_detection_loop(self):
        """Failure detection loop"""
        while self.running:
            try:
                failed = self.membership.check_failures()
                
                for node_id in failed:
                    if self.on_member_removed:
                        self.on_member_removed(node_id)
                
                await asyncio.sleep(self.gossip_interval)
            
            except Exception as e:
                print(f"Failure detection error: {e}")
                await asyncio.sleep(self.gossip_interval)
    
    def _create_membership_message(self) -> GossipMessage:
        """Create membership update message"""
        self.sequence_counter += 1
        
        # Serialize membership state
        members_data = {
            node_id: {
                'address': state.address,
                'port': state.port,
                'capabilities': list(state.capabilities),
                'version': state.version,
                'last_seen': state.last_seen
            }
            for node_id, state in self.membership.members.items()
        }
        
        import json
        payload = json.dumps(members_data).encode()
        
        return GossipMessage(
            message_type=GossipMessageType.MEMBERSHIP,
            sender_id=self.node_id,
            sequence_number=self.sequence_counter,
            payload=payload
        )
    
    async def _send_gossip_message(self, neighbor: NodeState, message: GossipMessage):
        """Send gossip message to neighbor (placeholder)"""
        # Would integrate with transport layer
        message_hash = self.epidemic._hash_message(message)
        self.epidemic.mark_received(message_hash)
        pass
    
    async def _perform_anti_entropy(self, neighbor: NodeState):
        """Perform anti-entropy with neighbor"""
        # Get peer's state digest
        # In real implementation, would request from peer
        peer_states = {}  # Would receive from peer
        
        # Compare states
        nodes_to_send, nodes_to_request = self.anti_entropy.compare_states(
            b'',  # Would be peer's digest
            peer_states
        )
        
        # Send states peer needs
        if nodes_to_send:
            states_to_send = self.anti_entropy.get_states_to_send(nodes_to_send)
            # Would send to peer
        
        # Request states we need
        if nodes_to_request:
            # Would request from peer
            pass
    
    def handle_gossip_message(self, message: GossipMessage):
        """Handle incoming gossip message"""
        message_hash = self.epidemic._hash_message(message)
        
        if not self.epidemic.should_process(message):
            return  # Already processed or expired
        
        self.epidemic.mark_received(message_hash)
        
        if message.message_type == GossipMessageType.MEMBERSHIP:
            self._handle_membership_message(message)
        elif message.message_type == GossipMessageType.STATE:
            self._handle_state_message(message)
        elif message.message_type == GossipMessageType.ANTI_ENTROPY:
            self._handle_anti_entropy_message(message)
        
        # Forward if needed
        if message.ttl > 0 and self.epidemic.should_forward(message_hash):
            message.ttl -= 1
            # Forward to random neighbors
            neighbors = self.membership.get_random_members(
                self.epidemic.fanout,
                exclude={self.node_id, message.sender_id}
            )
            for neighbor in neighbors:
                asyncio.create_task(self._send_gossip_message(neighbor, message))
        
        if self.on_message_received:
            self.on_message_received(message)
    
    def _handle_membership_message(self, message: GossipMessage):
        """Handle membership update message"""
        import json
        try:
            members_data = json.loads(message.payload.decode())
            
            for node_id, data in members_data.items():
                if node_id == self.node_id:
                    continue
                
                node_state = NodeState(
                    node_id=node_id,
                    address=data['address'],
                    port=data['port'],
                    capabilities=set(data.get('capabilities', [])),
                    version=data.get('version', 0),
                    last_seen=data.get('last_seen', time.time())
                )
                
                # Merge into membership
                if node_id not in self.membership.members:
                    self.membership.add_member(node_state)
                    if self.on_member_added:
                        self.on_member_added(node_state)
                else:
                    # Update if newer version
                    existing = self.membership.members[node_id]
                    if node_state.version > existing.version:
                        self.membership.add_member(node_state)
                
                # Update anti-entropy state
                self.anti_entropy.merge_state(node_state)
        
        except Exception as e:
            print(f"Error handling membership message: {e}")
    
    def _handle_state_message(self, message: GossipMessage):
        """Handle state synchronization message"""
        # Would deserialize and merge state
        pass
    
    def _handle_anti_entropy_message(self, message: GossipMessage):
        """Handle anti-entropy message"""
        # Would process anti-entropy reconciliation
        pass
    
    def broadcast_rumor(self, payload: bytes) -> GossipMessage:
        """Broadcast rumor message using epidemic broadcast"""
        self.sequence_counter += 1
        
        message = self.epidemic.create_rumor(
            self.node_id,
            payload,
            self.sequence_counter
        )
        
        # Forward to random neighbors
        neighbors = self.membership.get_random_members(self.epidemic.fanout)
        for neighbor in neighbors:
            asyncio.create_task(self._send_gossip_message(neighbor, message))
        
        return message
    
    def get_membership(self) -> Dict[str, NodeState]:
        """Get current membership"""
        return self.membership.members.copy()
    
    def get_member_count(self) -> int:
        """Get number of members"""
        return len(self.membership.get_live_members())
