"""
Data Relay System for Large Local Networks

When there are more than 2 locations capable of internet connection within a local network,
data is relayed to a random internet node for upload, up to a depth of 3 computers/beacons deep.
"""

import time
import random
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass

from .peer_manager import MemshadowPeerManager, PeerInfo
from .dsmil_protocol import MemshadowMessage, MessageType


@dataclass
class RelayResult:
    """Relay operation result"""
    success: bool
    error: Optional[str] = None
    path: Optional[List[str]] = None
    hops: int = 0


class MemshadowRelay:
    """
    Manages data relay through peer network.
    
    Relay flow:
    Source Peer (no internet)
        ↓ (hop 1)
    Relay Peer 1 (no internet)
        ↓ (hop 2)
    Relay Peer 2 (no internet)
        ↓ (hop 3)
    Internet-Capable Peer → Internet Node
    """
    
    def __init__(self, peer_manager: MemshadowPeerManager):
        """
        Initialize relay handler.
        
        Args:
            peer_manager: Peer manager instance
        """
        self.peer_manager = peer_manager
        self.max_depth = 3  # Maximum relay depth
    
    def should_use_relay(self) -> bool:
        """
        Check if relay should be used.
        
        Relay is used when there are more than 2 internet-capable peers.
        
        Returns:
            True if relay should be used
        """
        internet_peers = self.peer_manager.get_internet_capable_peers()
        return len(internet_peers) > 2
    
    def relay_data_to_internet(
        self,
        source_peer_id: str,
        data: bytes,
        target_internet_node: Optional[str] = None,
    ) -> RelayResult:
        """
        Relay data to internet through peer network.
        
        Args:
            source_peer_id: Source peer ID
            data: Data to relay
            target_internet_node: Target internet node (random if None)
        
        Returns:
            RelayResult with success status and path
        """
        # Find relay path
        relay_path = self.peer_manager.find_relay_path(
            source_peer_id,
            max_depth=self.max_depth,
        )
        
        if not relay_path:
            return RelayResult(
                success=False,
                error="No relay path found to internet-capable peer",
            )
        
        # Select target internet node
        if target_internet_node is None:
            internet_peers = self.peer_manager.get_internet_capable_peers()
            if not internet_peers:
                return RelayResult(
                    success=False,
                    error="No internet-capable peers available",
                )
            target_internet_node = random.choice(internet_peers).peer_id
        
        # Ensure target is in path
        if target_internet_node not in relay_path:
            # Extend path to target
            target_peer = self.peer_manager.get_peer(target_internet_node)
            if target_peer and target_peer.has_internet:
                relay_path.append(target_internet_node)
            else:
                return RelayResult(
                    success=False,
                    error="Target internet node not reachable",
                )
        
        # Relay through path
        try:
            success = self._relay_through_path(relay_path, data)
            
            if success:
                return RelayResult(
                    success=True,
                    path=relay_path,
                    hops=len(relay_path) - 1,
                )
            else:
                return RelayResult(
                    success=False,
                    error="Relay failed during transmission",
                    path=relay_path,
                )
        except Exception as e:
            return RelayResult(
                success=False,
                error=str(e),
                path=relay_path,
            )
    
    def _relay_through_path(self, path: List[str], data: bytes) -> bool:
        """
        Relay data through the specified path.
        
        Args:
            path: List of peer IDs forming the relay path
            data: Data to relay
        
        Returns:
            True if relay successful
        """
        # In real implementation, would send MEMSHADOW messages to each peer
        # For now, simulate relay
        
        for i, peer_id in enumerate(path):
            peer = self.peer_manager.get_peer(peer_id)
            if not peer:
                return False
            
            # Check if this is the last hop (internet-capable peer)
            if i == len(path) - 1:
                if not peer.has_internet:
                    return False
                # Upload to internet (would be actual network call)
                return self._upload_to_internet(peer, data)
            
            # Relay to next peer (would be actual MEMSHADOW message)
            # For simulation, just continue
            continue
        
        return False
    
    def _upload_to_internet(self, peer: PeerInfo, data: bytes) -> bool:
        """
        Upload data to internet via peer.
        
        Args:
            peer: Internet-capable peer
            data: Data to upload
        
        Returns:
            True if upload successful
        """
        # In real implementation, would send MEMSHADOW message to peer
        # requesting internet upload
        # For now, simulate success
        return True
    
    def get_relay_statistics(self) -> Dict:
        """
        Get relay statistics.
        
        Returns:
            Dictionary with relay statistics
        """
        internet_peers = self.peer_manager.get_internet_capable_peers()
        active_peers = self.peer_manager.get_active_peers()
        
        return {
            "total_peers": len(active_peers),
            "internet_capable_peers": len(internet_peers),
            "should_use_relay": self.should_use_relay(),
            "max_depth": self.max_depth,
        }
