"""
Peer Management System for Large Local Networks

Handles peer discovery, peer list distribution, and peer tracking for local networks.
Unlike internet connections which use Veilid for auto-discovery, MEMSHADOW used locally
needs to keep track and distribute the list of peers.
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from .dsmil_protocol import MessageType, MemshadowMessage


class PeerStatus(IntEnum):
    """Peer status"""
    ACTIVE = 1
    INACTIVE = 2
    UNKNOWN = 3


@dataclass
class PeerInfo:
    """
    Peer information structure.
    
    Tracks all known peers and their capabilities for local network operation.
    """
    peer_id: str  # Unique peer identifier
    address: str  # IP address
    port: int  # MEMSHADOW relay port
    platform: str  # Platform (windows/linux/macos)
    status: int = PeerStatus.ACTIVE  # PeerStatus
    last_seen: float = field(default_factory=time.time)  # Last seen timestamp
    shared_secret: Optional[str] = None  # Shared secret (local only, not distributed)
    capabilities: Dict = field(default_factory=dict)  # Peer capabilities
    has_internet: bool = False  # Internet connectivity flag
    relay_depth: int = 0  # Current relay depth
    created_at: float = field(default_factory=time.time)  # Creation timestamp
    
    def to_dict(self) -> Dict:
        """Convert to dictionary (excluding shared_secret)"""
        data = asdict(self)
        data.pop('shared_secret', None)  # Don't distribute secrets
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PeerInfo":
        """Create from dictionary"""
        return cls(**data)


class MemshadowPeerManager:
    """
    Manages peers for local network operation.
    
    Features:
    - Peer registration and tracking
    - Peer list distribution
    - Internet connectivity tracking
    - Peer discovery via peer list exchange
    - Relay path finding
    """
    
    def __init__(
        self,
        peer_id: Optional[str] = None,
        address: Optional[str] = None,
        port: int = 8901,
        platform: str = "linux",
        shared_secret: Optional[str] = None,
        storage_path: Optional[Path] = None,
    ):
        """
        Initialize peer manager.
        
        Args:
            peer_id: This peer's ID (auto-generated if None)
            address: This peer's address
            port: This peer's port
            platform: Platform identifier
            shared_secret: Shared secret for this peer
            storage_path: Path to store peer lists
        """
        self.peer_id = peer_id or self._generate_peer_id(address, port)
        self.address = address or "127.0.0.1"
        self.port = port
        self.platform = platform
        self.shared_secret = shared_secret
        
        self.peers: Dict[str, PeerInfo] = {}
        self.storage_path = storage_path or Path("peers")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Register self
        self.register_peer(
            peer_id=self.peer_id,
            address=self.address,
            port=self.port,
            platform=self.platform,
            shared_secret=self.shared_secret,
            capabilities={"self": True},
        )
    
    def _generate_peer_id(self, address: Optional[str], port: int) -> str:
        """Generate unique peer ID"""
        addr = address or "127.0.0.1"
        timestamp = int(time.time())
        return f"{addr}_{port}_{timestamp}"
    
    def register_peer(
        self,
        peer_id: str,
        address: str,
        port: int,
        platform: str,
        shared_secret: Optional[str] = None,
        capabilities: Optional[Dict] = None,
        has_internet: bool = False,
    ) -> bool:
        """
        Register a peer.
        
        Args:
            peer_id: Unique peer identifier
            address: IP address
            port: MEMSHADOW port
            platform: Platform identifier
            shared_secret: Shared secret (local only)
            capabilities: Peer capabilities
            has_internet: Internet connectivity flag
        
        Returns:
            True if registered successfully
        """
        peer = PeerInfo(
            peer_id=peer_id,
            address=address,
            port=port,
            platform=platform,
            shared_secret=shared_secret,
            capabilities=capabilities or {},
            has_internet=has_internet,
            status=PeerStatus.ACTIVE,
            last_seen=time.time(),
        )
        
        self.peers[peer_id] = peer
        self._save_peer_list()
        return True
    
    def update_peer_status(self, peer_id: str, status: int):
        """Update peer status"""
        if peer_id in self.peers:
            self.peers[peer_id].status = status
            self.peers[peer_id].last_seen = time.time()
            self._save_peer_list()
    
    def update_peer_internet_status(self, peer_id: str, has_internet: bool):
        """Update peer internet connectivity status"""
        if peer_id in self.peers:
            self.peers[peer_id].has_internet = has_internet
            self.peers[peer_id].last_seen = time.time()
            self._save_peer_list()
    
    def get_peer(self, peer_id: str) -> Optional[PeerInfo]:
        """Get peer by ID"""
        return self.peers.get(peer_id)
    
    def get_active_peers(self) -> List[PeerInfo]:
        """Get all active peers"""
        return [
            peer for peer in self.peers.values()
            if peer.status == PeerStatus.ACTIVE
        ]
    
    def get_internet_capable_peers(self) -> List[PeerInfo]:
        """Get all peers with internet connectivity"""
        return [
            peer for peer in self.peers.values()
            if peer.has_internet and peer.status == PeerStatus.ACTIVE
        ]
    
    def discover_peers(self, known_peers: List[str]) -> List[PeerInfo]:
        """
        Discover peers by querying known peers for their peer lists.
        
        Args:
            known_peers: List of peer IDs to query
        
        Returns:
            List of newly discovered peers
        """
        new_peers = []
        
        for peer_id in known_peers:
            if peer_id not in self.peers:
                continue
            
            peer = self.peers[peer_id]
            # In real implementation, would send MEMSHADOW message to request peer list
            # For now, return empty list (would be implemented with actual network calls)
            pass
        
        return new_peers
    
    def merge_peer_list(self, peer_list: List[Dict]) -> int:
        """
        Merge received peer list with local peers.
        
        Args:
            peer_list: List of peer dictionaries from another peer
        
        Returns:
            Number of new peers added
        """
        new_count = 0
        
        for peer_data in peer_list:
            peer_id = peer_data.get("peer_id")
            if not peer_id:
                continue
            
            # Don't merge self
            if peer_id == self.peer_id:
                continue
            
            # Create or update peer
            if peer_id not in self.peers:
                self.peers[peer_id] = PeerInfo.from_dict(peer_data)
                new_count += 1
            else:
                # Update existing peer
                existing = self.peers[peer_id]
                existing.address = peer_data.get("address", existing.address)
                existing.port = peer_data.get("port", existing.port)
                existing.platform = peer_data.get("platform", existing.platform)
                existing.capabilities = peer_data.get("capabilities", existing.capabilities)
                existing.has_internet = peer_data.get("has_internet", existing.has_internet)
                existing.last_seen = time.time()
        
        if new_count > 0:
            self._save_peer_list()
        
        return new_count
    
    def get_peer_list_dict(self) -> List[Dict]:
        """Get peer list as dictionary (for distribution)"""
        return [peer.to_dict() for peer in self.peers.values() if peer.peer_id != self.peer_id]
    
    def find_relay_path(
        self,
        source_peer_id: str,
        max_depth: int = 3,
    ) -> Optional[List[str]]:
        """
        Find shortest path to an internet-capable peer using BFS.
        
        Args:
            source_peer_id: Source peer ID
            max_depth: Maximum relay depth
        
        Returns:
            List of peer IDs forming the path, or None if no path found
        """
        if source_peer_id not in self.peers:
            return None
        
        # BFS to find shortest path
        queue = [(source_peer_id, [source_peer_id])]
        visited = {source_peer_id}
        
        while queue:
            current_id, path = queue.pop(0)
            
            if len(path) > max_depth + 1:
                continue
            
            current_peer = self.peers.get(current_id)
            if not current_peer:
                continue
            
            # Check if this peer has internet
            if current_peer.has_internet and current_peer.status == PeerStatus.ACTIVE:
                return path
            
            # Explore neighbors (all other active peers)
            for peer_id, peer in self.peers.items():
                if peer_id in visited:
                    continue
                if peer.status != PeerStatus.ACTIVE:
                    continue
                if peer_id == current_id:
                    continue
                
                visited.add(peer_id)
                queue.append((peer_id, path + [peer_id]))
        
        return None
    
    def check_internet_connectivity(self, peer_id: str) -> bool:
        """
        Check if a peer has internet connectivity.
        
        Args:
            peer_id: Peer to check
        
        Returns:
            True if peer has internet
        """
        if peer_id not in self.peers:
            return False
        
        return self.peers[peer_id].has_internet
    
    def _save_peer_list(self):
        """Save peer list to storage"""
        peer_file = self.storage_path / f"{self.peer_id}_peers.json"
        
        peer_data = {
            "peer_id": self.peer_id,
            "peers": [peer.to_dict() for peer in self.peers.values()],
            "updated_at": time.time(),
        }
        
        with open(peer_file, "w") as f:
            json.dump(peer_data, f, indent=2)
    
    def _load_peer_list(self):
        """Load peer list from storage"""
        peer_file = self.storage_path / f"{self.peer_id}_peers.json"
        
        if not peer_file.exists():
            return
        
        try:
            with open(peer_file, "r") as f:
                data = json.load(f)
            
            for peer_data in data.get("peers", []):
                peer = PeerInfo.from_dict(peer_data)
                self.peers[peer.peer_id] = peer
        except Exception:
            pass  # Ignore load errors
