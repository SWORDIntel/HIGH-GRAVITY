"""
MEMSHADOW Protocol - Memory Deduplication

Implements content-addressable storage and deduplication for
efficient memory transfer between nodes.
"""

import hashlib
import struct
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import IntEnum
import mmh3  # MurmurHash3 for fast hashing


class DeduplicationLevel(IntEnum):
    """Deduplication levels"""
    NONE = 0
    CHUNK_LEVEL = 1  # Deduplicate chunks
    CROSS_NODE = 2  # Cross-node deduplication
    GLOBAL = 3  # Global deduplication across all nodes


@dataclass
class ChunkReference:
    """Reference to a deduplicated chunk"""
    chunk_hash: bytes  # SHA256 hash
    size: int
    offset: int
    node_id: Optional[str] = None  # Node that has this chunk


@dataclass
class MerkleNode:
    """Merkle tree node for deduplication"""
    hash: bytes
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    chunk_ref: Optional[ChunkReference] = None
    is_leaf: bool = False


class ContentAddressableStorage:
    """
    Content-Addressable Storage (CAS)
    
    Stores data by content hash, enabling deduplication.
    """
    
    def __init__(self):
        self.storage: Dict[bytes, bytes] = {}  # hash -> data
        self.references: Dict[bytes, int] = {}  # hash -> reference count
    
    def store(self, data: bytes) -> bytes:
        """
        Store data and return content hash
        
        Returns:
            Content hash (SHA256)
        """
        content_hash = hashlib.sha256(data).digest()
        
        if content_hash not in self.storage:
            self.storage[content_hash] = data
            self.references[content_hash] = 0
        
        self.references[content_hash] += 1
        return content_hash
    
    def retrieve(self, content_hash: bytes) -> Optional[bytes]:
        """Retrieve data by content hash"""
        return self.storage.get(content_hash)
    
    def has(self, content_hash: bytes) -> bool:
        """Check if content hash exists"""
        return content_hash in self.storage
    
    def release(self, content_hash: bytes):
        """Release reference to content"""
        if content_hash in self.references:
            self.references[content_hash] -= 1
            if self.references[content_hash] <= 0:
                # Could garbage collect here
                pass
    
    def get_stats(self) -> Dict:
        """Get storage statistics"""
        total_size = sum(len(data) for data in self.storage.values())
        return {
            'chunks': len(self.storage),
            'total_size': total_size,
            'unique_size': total_size,  # All chunks are unique by definition
            'deduplication_ratio': 0.0  # Would calculate based on references
        }


class MerkleTree:
    """
    Merkle tree for efficient deduplication
    
    Allows quick comparison of data structures and
    identification of changed chunks.
    """
    
    def __init__(self, chunks: List[bytes]):
        self.chunks = chunks
        self.root = self._build_tree(chunks)
    
    def _build_tree(self, chunks: List[bytes]) -> MerkleNode:
        """Build Merkle tree from chunks"""
        if len(chunks) == 1:
            # Leaf node
            chunk_hash = hashlib.sha256(chunks[0]).digest()
            return MerkleNode(
                hash=chunk_hash,
                chunk_ref=ChunkReference(
                    chunk_hash=chunk_hash,
                    size=len(chunks[0]),
                    offset=0
                ),
                is_leaf=True
            )
        
        # Build left and right subtrees
        mid = len(chunks) // 2
        left_node = self._build_tree(chunks[:mid])
        right_node = self._build_tree(chunks[mid:])
        
        # Combine hashes
        combined_hash = hashlib.sha256(
            left_node.hash + right_node.hash
        ).digest()
        
        return MerkleNode(
            hash=combined_hash,
            left=left_node,
            right=right_node,
            is_leaf=False
        )
    
    def get_root_hash(self) -> bytes:
        """Get root hash of Merkle tree"""
        return self.root.hash
    
    def find_differences(self, other: 'MerkleTree') -> List[bytes]:
        """
        Find chunk hashes that differ between trees
        
        Returns:
            List of chunk hashes that are different
        """
        differences = []
        self._compare_nodes(self.root, other.root, differences)
        return differences
    
    def _compare_nodes(self, node1: MerkleNode, node2: MerkleNode, differences: List[bytes]):
        """Recursively compare nodes"""
        if node1.hash == node2.hash:
            # Subtrees are identical
            return
        
        if node1.is_leaf and node2.is_leaf:
            # Both are leaves - chunks differ
            differences.append(node1.chunk_ref.chunk_hash)
            differences.append(node2.chunk_ref.chunk_hash)
        elif node1.is_leaf or node2.is_leaf:
            # One is leaf, one is not - structure differs
            if node1.is_leaf:
                differences.append(node1.chunk_ref.chunk_hash)
            if node2.is_leaf:
                differences.append(node2.chunk_ref.chunk_hash)
        else:
            # Both are internal nodes - recurse
            if node1.left and node2.left:
                self._compare_nodes(node1.left, node2.left, differences)
            if node1.right and node2.right:
                self._compare_nodes(node1.right, node2.right, differences)


class ChunkDeduplicator:
    """
    Chunk-level deduplication
    
    Identifies duplicate chunks across data transfers.
    """
    
    def __init__(self, chunk_size: int = 2048):
        self.chunk_size = chunk_size
        self.cas = ContentAddressableStorage()
        self.chunk_index: Dict[bytes, List[ChunkReference]] = {}  # hash -> references
    
    def chunk_and_deduplicate(self, data: bytes) -> Tuple[List[ChunkReference], List[bytes]]:
        """
        Chunk data and identify duplicates
        
        Returns:
            (chunk_references, unique_chunk_data)
        """
        # Chunk data
        chunks = []
        for i in range(0, len(data), self.chunk_size):
            chunk_data = data[i:i + self.chunk_size]
            chunks.append(chunk_data)
        
        # Deduplicate
        references = []
        unique_chunks = []
        seen_hashes = set()
        
        for i, chunk_data in enumerate(chunks):
            chunk_hash = hashlib.sha256(chunk_data).digest()
            
            if chunk_hash in self.cas.storage:
                # Chunk already exists - reference it
                references.append(ChunkReference(
                    chunk_hash=chunk_hash,
                    size=len(chunk_data),
                    offset=i * self.chunk_size
                ))
            else:
                # New chunk - store it
                self.cas.store(chunk_data)
                references.append(ChunkReference(
                    chunk_hash=chunk_hash,
                    size=len(chunk_data),
                    offset=i * self.chunk_size
                ))
                unique_chunks.append(chunk_data)
                seen_hashes.add(chunk_hash)
        
        return references, unique_chunks
    
    def reconstruct(self, references: List[ChunkReference]) -> bytes:
        """
        Reconstruct data from chunk references
        
        Assumes all referenced chunks are available in CAS.
        """
        result_parts = []
        for ref in sorted(references, key=lambda r: r.offset):
            chunk_data = self.cas.retrieve(ref.chunk_hash)
            if chunk_data:
                result_parts.append(chunk_data)
            else:
                # Missing chunk - would error in real implementation
                result_parts.append(b'\x00' * ref.size)
        
        return b''.join(result_parts)


class CrossNodeDeduplication:
    """
    Cross-node deduplication
    
    Shares chunk information between nodes to avoid
    transferring duplicate data.
    """
    
    def __init__(self):
        self.node_chunks: Dict[str, Set[bytes]] = {}  # node_id -> set of chunk hashes
        self.global_chunk_index: Dict[bytes, Set[str]] = {}  # chunk_hash -> set of node_ids
    
    def register_node_chunks(self, node_id: str, chunk_hashes: List[bytes]):
        """Register chunks available at a node"""
        if node_id not in self.node_chunks:
            self.node_chunks[node_id] = set()
        
        for chunk_hash in chunk_hashes:
            self.node_chunks[node_id].add(chunk_hash)
            
            if chunk_hash not in self.global_chunk_index:
                self.global_chunk_index[chunk_hash] = set()
            self.global_chunk_index[chunk_hash].add(node_id)
    
    def find_nodes_with_chunk(self, chunk_hash: bytes) -> List[str]:
        """Find nodes that have a specific chunk"""
        return list(self.global_chunk_index.get(chunk_hash, set()))
    
    def get_deduplication_hints(
        self,
        source_node: str,
        target_node: str,
        chunk_hashes: List[bytes]
    ) -> Dict[bytes, Optional[str]]:
        """
        Get deduplication hints for transfer
        
        Returns:
            Dict mapping chunk_hash -> node_id (if available elsewhere) or None
        """
        hints = {}
        target_chunks = self.node_chunks.get(target_node, set())
        
        for chunk_hash in chunk_hashes:
            if chunk_hash in target_chunks:
                # Target already has chunk - don't send
                hints[chunk_hash] = None  # None means skip
            else:
                # Check if available at other nodes
                nodes_with_chunk = self.find_nodes_with_chunk(chunk_hash)
                if nodes_with_chunk:
                    # Prefer nodes closer to target (simplified)
                    hints[chunk_hash] = nodes_with_chunk[0]
                else:
                    # Must send from source
                    hints[chunk_hash] = source_node
        
        return hints
    
    def get_deduplication_stats(self) -> Dict:
        """Get deduplication statistics"""
        total_chunks = len(self.global_chunk_index)
        total_nodes = len(self.node_chunks)
        
        # Calculate average chunks per node
        avg_chunks = sum(len(chunks) for chunks in self.node_chunks.values()) / max(total_nodes, 1)
        
        # Calculate unique chunks (chunks available at only one node)
        unique_chunks = sum(
            1 for nodes in self.global_chunk_index.values()
            if len(nodes) == 1
        )
        
        return {
            'total_chunks': total_chunks,
            'total_nodes': total_nodes,
            'avg_chunks_per_node': avg_chunks,
            'unique_chunks': unique_chunks,
            'shared_chunks': total_chunks - unique_chunks
        }


class MemoryDeduplicationManager:
    """
    Main memory deduplication manager
    
    Coordinates chunk-level and cross-node deduplication.
    """
    
    def __init__(self, dedup_level: DeduplicationLevel = DeduplicationLevel.CROSS_NODE):
        self.dedup_level = dedup_level
        self.chunk_deduplicator = ChunkDeduplicator()
        self.cross_node_dedup = CrossNodeDeduplication() if dedup_level >= DeduplicationLevel.CROSS_NODE else None
        self.merkle_trees: Dict[str, MerkleTree] = {}  # node_id -> MerkleTree
    
    def prepare_transfer(
        self,
        source_node: str,
        target_node: str,
        data: bytes
    ) -> Tuple[List[ChunkReference], List[bytes], Dict]:
        """
        Prepare data for transfer with deduplication
        
        Returns:
            (chunk_references, unique_chunk_data, deduplication_info)
        """
        # Chunk and deduplicate
        references, unique_chunks = self.chunk_deduplicator.chunk_and_deduplicate(data)
        
        # Get chunk hashes
        chunk_hashes = [ref.chunk_hash for ref in references]
        
        # Register chunks at source node
        if self.cross_node_dedup:
            self.cross_node_dedup.register_node_chunks(source_node, chunk_hashes)
        
        # Get deduplication hints
        dedup_hints = {}
        if self.cross_node_dedup:
            dedup_hints = self.cross_node_dedup.get_deduplication_hints(
                source_node,
                target_node,
                chunk_hashes
            )
        
        # Filter chunks based on hints
        chunks_to_send = []
        for ref in references:
            hint = dedup_hints.get(ref.chunk_hash, source_node)
            if hint is not None:  # None means skip (target has it)
                # Find chunk data
                chunk_data = self.chunk_deduplicator.cas.retrieve(ref.chunk_hash)
                if chunk_data:
                    chunks_to_send.append(chunk_data)
        
        dedup_info = {
            'total_chunks': len(references),
            'chunks_to_send': len(chunks_to_send),
            'chunks_skipped': len(references) - len(chunks_to_send),
            'deduplication_ratio': (1 - len(chunks_to_send) / len(references)) * 100 if references else 0
        }
        
        return references, chunks_to_send, dedup_info
    
    def receive_transfer(
        self,
        target_node: str,
        references: List[ChunkReference],
        chunk_data: List[bytes]
    ) -> bytes:
        """
        Receive and reconstruct data from deduplicated transfer
        """
        # Store received chunks
        for chunk_data_item in chunk_data:
            self.chunk_deduplicator.cas.store(chunk_data_item)
        
        # Register chunks at target node
        if self.cross_node_dedup:
            chunk_hashes = [ref.chunk_hash for ref in references]
            self.cross_node_dedup.register_node_chunks(target_node, chunk_hashes)
        
        # Reconstruct data
        return self.chunk_deduplicator.reconstruct(references)
