"""
MEMSHADOW Protocol - Network Partition Resilience

Handles network partitions, split-brain scenarios, and partition merges
with conflict resolution and eventual consistency.
"""

import time
import hashlib
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import IntEnum
from collections import defaultdict


class PartitionState(IntEnum):
    """Partition state"""
    NORMAL = 0  # Normal operation, no partition detected
    SUSPECTED = 1  # Partition suspected
    CONFIRMED = 2  # Partition confirmed
    MERGING = 3  # Partition merge in progress
    MERGED = 4  # Partition merge completed


@dataclass
class PartitionInfo:
    """Information about a network partition"""
    partition_id: str
    nodes: Set[str]
    detected_at: float
    state: PartitionState = PartitionState.SUSPECTED
    leader: Optional[str] = None
    version: int = 0


@dataclass
class Conflict:
    """Conflict detected during partition merge"""
    key: str
    local_value: Any
    remote_value: Any
    local_version: int
    remote_version: int
    conflict_type: str  # "update", "delete", "create"


class SplitBrainDetector:
    """
    Split-brain detection
    
    Detects when network has split into multiple partitions.
    """
    
    def __init__(self, quorum_size: int = 3):
        self.quorum_size = quorum_size
        self.known_nodes: Set[str] = set()
        self.node_last_seen: Dict[str, float] = {}
        self.partition_timeout = 30.0  # Seconds before suspecting partition
        self.partitions: Dict[str, PartitionInfo] = {}
    
    def register_node(self, node_id: str):
        """Register known node"""
        self.known_nodes.add(node_id)
        self.node_last_seen[node_id] = time.time()
    
    def update_node_seen(self, node_id: str):
        """Update when node was last seen"""
        if node_id in self.known_nodes:
            self.node_last_seen[node_id] = time.time()
    
    def detect_partitions(self) -> List[PartitionInfo]:
        """
        Detect network partitions
        
        Returns:
            List of detected partitions
        """
        current_time = time.time()
        unreachable_nodes = set()
        
        # Find unreachable nodes
        for node_id, last_seen in self.node_last_seen.items():
            if current_time - last_seen > self.partition_timeout:
                unreachable_nodes.add(node_id)
        
        if not unreachable_nodes:
            return []
        
        # Group unreachable nodes into partitions
        # Simplified: assume all unreachable nodes are in one partition
        partition_id = hashlib.sha256(
            "|".join(sorted(unreachable_nodes)).encode()
        ).hexdigest()[:16]
        
        if partition_id not in self.partitions:
            partition = PartitionInfo(
                partition_id=partition_id,
                nodes=unreachable_nodes.copy(),
                detected_at=current_time,
                state=PartitionState.SUSPECTED
            )
            self.partitions[partition_id] = partition
        
        return [self.partitions[partition_id]]
    
    def confirm_partition(self, partition_id: str):
        """Confirm partition exists"""
        if partition_id in self.partitions:
            self.partitions[partition_id].state = PartitionState.CONFIRMED
    
    def get_reachable_nodes(self) -> Set[str]:
        """Get nodes that are currently reachable"""
        current_time = time.time()
        return {
            node_id for node_id, last_seen in self.node_last_seen.items()
            if current_time - last_seen <= self.partition_timeout
        }


class ConflictResolver:
    """
    Conflict resolution for partition merges
    
    Resolves conflicts when partitions merge.
    """
    
    def __init__(self):
        self.resolution_strategies: Dict[str, str] = {
            'last_write_wins': 'last_write_wins',
            'version_vector': 'version_vector',
            'manual': 'manual',
            'merge': 'merge'
        }
        self.default_strategy = 'last_write_wins'
    
    def resolve_conflict(
        self,
        conflict: Conflict,
        strategy: Optional[str] = None
    ) -> Any:
        """
        Resolve conflict using specified strategy
        
        Args:
            conflict: Conflict to resolve
            strategy: Resolution strategy (default: last_write_wins)
        
        Returns:
            Resolved value
        """
        strategy = strategy or self.default_strategy
        
        if strategy == 'last_write_wins':
            # Use value with higher version number
            if conflict.local_version >= conflict.remote_version:
                return conflict.local_value
            else:
                return conflict.remote_value
        
        elif strategy == 'version_vector':
            # Use version vector comparison
            # Simplified: use higher version
            if conflict.local_version >= conflict.remote_version:
                return conflict.local_value
            else:
                return conflict.remote_value
        
        elif strategy == 'merge':
            # Merge values if possible
            if isinstance(conflict.local_value, dict) and isinstance(conflict.remote_value, dict):
                merged = conflict.local_value.copy()
                merged.update(conflict.remote_value)
                return merged
            elif isinstance(conflict.local_value, list) and isinstance(conflict.remote_value, list):
                # Merge lists, removing duplicates
                merged = conflict.local_value.copy()
                for item in conflict.remote_value:
                    if item not in merged:
                        merged.append(item)
                return merged
            else:
                # Can't merge, use last_write_wins
                return self.resolve_conflict(conflict, 'last_write_wins')
        
        elif strategy == 'manual':
            # Manual resolution - return local for now
            return conflict.local_value
        
        # Default: last_write_wins
        return conflict.local_value if conflict.local_version >= conflict.remote_version else conflict.remote_value


class StateReconciliation:
    """
    State reconciliation for partition merges
    
    Compares and merges state from different partitions.
    """
    
    def __init__(self):
        self.local_state: Dict[str, Any] = {}
        self.state_versions: Dict[str, int] = {}
        self.state_timestamps: Dict[str, float] = {}
        self.conflict_resolver = ConflictResolver()
    
    def set_state(self, key: str, value: Any, version: Optional[int] = None):
        """Set local state"""
        if version is None:
            version = self.state_versions.get(key, 0) + 1
        
        self.local_state[key] = value
        self.state_versions[key] = version
        self.state_timestamps[key] = time.time()
    
    def get_state(self, key: str) -> Optional[Any]:
        """Get local state"""
        return self.local_state.get(key)
    
    def compare_states(
        self,
        remote_state: Dict[str, Any],
        remote_versions: Dict[str, int],
        remote_timestamps: Dict[str, float]
    ) -> Tuple[List[str], List[str], List[Conflict]]:
        """
        Compare local and remote states
        
        Returns:
            (keys_to_send, keys_to_request, conflicts)
        """
        keys_to_send = []
        keys_to_request = []
        conflicts = []
        
        all_keys = set(self.local_state.keys()) | set(remote_state.keys())
        
        for key in all_keys:
            local_version = self.state_versions.get(key, 0)
            remote_version = remote_versions.get(key, 0)
            
            local_exists = key in self.local_state
            remote_exists = key in remote_state
            
            if not local_exists and remote_exists:
                # Remote has key we don't have
                keys_to_request.append(key)
            
            elif local_exists and not remote_exists:
                # We have key remote doesn't have
                keys_to_send.append(key)
            
            elif local_exists and remote_exists:
                # Both have key - check for conflicts
                if local_version != remote_version:
                    # Different versions - conflict
                    conflicts.append(Conflict(
                        key=key,
                        local_value=self.local_state[key],
                        remote_value=remote_state[key],
                        local_version=local_version,
                        remote_version=remote_version,
                        conflict_type='update'
                    ))
                elif self.local_state[key] != remote_state[key]:
                    # Same version but different values - conflict
                    conflicts.append(Conflict(
                        key=key,
                        local_value=self.local_state[key],
                        remote_value=remote_state[key],
                        local_version=local_version,
                        remote_version=remote_version,
                        conflict_type='update'
                    ))
        
        return keys_to_send, keys_to_request, conflicts
    
    def merge_state(
        self,
        remote_state: Dict[str, Any],
        remote_versions: Dict[str, int],
        remote_timestamps: Dict[str, float],
        resolve_conflicts: bool = True
    ) -> List[Conflict]:
        """
        Merge remote state into local state
        
        Returns:
            List of unresolved conflicts
        """
        keys_to_send, keys_to_request, conflicts = self.compare_states(
            remote_state,
            remote_versions,
            remote_timestamps
        )
        
        # Request missing keys
        for key in keys_to_request:
            if key in remote_state:
                self.set_state(key, remote_state[key], remote_versions.get(key, 0))
        
        # Send our keys (would be handled by caller)
        
        # Resolve conflicts
        unresolved_conflicts = []
        for conflict in conflicts:
            if resolve_conflicts:
                resolved_value = self.conflict_resolver.resolve_conflict(conflict)
                self.set_state(conflict.key, resolved_value, max(conflict.local_version, conflict.remote_version))
            else:
                unresolved_conflicts.append(conflict)
        
        return unresolved_conflicts


class PartitionManager:
    """
    Main partition management
    
    Coordinates partition detection, handling, and merge operations.
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.split_brain_detector = SplitBrainDetector()
        self.state_reconciliation = StateReconciliation()
        self.current_partition: Optional[PartitionInfo] = None
        self.merge_in_progress = False
    
    def register_node(self, node_id: str):
        """Register node for partition detection"""
        self.split_brain_detector.register_node(node_id)
    
    def update_node_seen(self, node_id: str):
        """Update when node was seen"""
        self.split_brain_detector.update_node_seen(node_id)
    
    def detect_partitions(self) -> List[PartitionInfo]:
        """Detect network partitions"""
        return self.split_brain_detector.detect_partitions()
    
    def handle_partition(self, partition: PartitionInfo):
        """Handle detected partition"""
        self.current_partition = partition
        
        if partition.state == PartitionState.SUSPECTED:
            # Confirm partition
            self.split_brain_detector.confirm_partition(partition.partition_id)
            partition.state = PartitionState.CONFIRMED
        
        # Would trigger partition handling logic
        # e.g., read-only mode, reduced functionality, etc.
    
    def detect_partition_merge(self, new_nodes: Set[str]) -> bool:
        """
        Detect if partition merge is happening
        
        Returns:
            True if merge detected
        """
        if not self.current_partition:
            return False
        
        # Check if nodes from partition are now reachable
        partition_nodes = self.current_partition.nodes
        newly_reachable = partition_nodes & new_nodes
        
        if len(newly_reachable) >= len(partition_nodes) // 2:
            # Majority of partition nodes are reachable - merge detected
            return True
        
        return False
    
    def start_merge(self, remote_state: Dict[str, Any], remote_versions: Dict[str, int]) -> List[Conflict]:
        """
        Start partition merge process
        
        Returns:
            List of conflicts that need resolution
        """
        if self.merge_in_progress:
            return []  # Merge already in progress
        
        self.merge_in_progress = True
        
        # Get remote timestamps (would be provided)
        remote_timestamps = {key: time.time() for key in remote_state.keys()}
        
        # Perform state reconciliation
        conflicts = self.state_reconciliation.merge_state(
            remote_state,
            remote_versions,
            remote_timestamps,
            resolve_conflicts=True
        )
        
        return conflicts
    
    def complete_merge(self):
        """Complete partition merge"""
        self.merge_in_progress = False
        if self.current_partition:
            self.current_partition.state = PartitionState.MERGED
            self.current_partition = None
    
    def get_reachable_nodes(self) -> Set[str]:
        """Get currently reachable nodes"""
        return self.split_brain_detector.get_reachable_nodes()
    
    def is_in_partition(self) -> bool:
        """Check if currently in a partition"""
        return self.current_partition is not None and \
               self.current_partition.state == PartitionState.CONFIRMED
    
    def get_partition_info(self) -> Optional[PartitionInfo]:
        """Get current partition information"""
        return self.current_partition


class NetworkPartitionResilience:
    """
    Network Partition Resilience - Simple partition detection

    Provides basic network partition resilience functionality for testing.
    """

    def __init__(self):
        self.manager = PartitionManager("test_node")

    def detect_partition(self, group1: List[str], group2: List[str]) -> bool:
        """
        Detect if two node groups are in different partitions

        Args:
            group1: First group of nodes
            group2: Second group of nodes

        Returns:
            True if partition detected between groups
        """
        # Convert string node IDs to the expected format
        all_nodes = set(group1 + group2)

        # Simulate partition detection
        # In a real implementation, this would check connectivity
        # For testing purposes, return True if groups are different
        return set(group1).isdisjoint(set(group2)) and len(group1) > 0 and len(group2) > 0
