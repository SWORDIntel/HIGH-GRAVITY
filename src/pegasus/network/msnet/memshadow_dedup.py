"""
MEMSHADOW Protocol - Memory Deduplication

Implements content-aware deduplication for efficient memory transfer.
Identifies and eliminates duplicate content across memory regions.
"""

import hashlib
from typing import Dict, Optional, List, Set
from dataclasses import dataclass
from enum import IntEnum


class DeduplicationAlgorithm(IntEnum):
    """Deduplication algorithms"""
    CONTENT_ADDRESSABLE = 0  # Content-addressable storage
    FIXED_BLOCK = 1  # Fixed-size block deduplication
    VARIABLE_BLOCK = 2  # Variable-size block deduplication


@dataclass
class DeduplicationBlock:
    """Deduplication block"""
    hash: bytes  # Content hash
    size: int  # Block size
    reference_count: int  # Number of references
    data: Optional[bytes] = None  # Actual data (for new blocks)


class MemoryDeduplication:
    """
    Memory Deduplication - Content-aware deduplication

    Eliminates duplicate content across memory regions.
    Stores unique content only once, with reference counting.
    """

    def __init__(self, algorithm: DeduplicationAlgorithm = DeduplicationAlgorithm.CONTENT_ADDRESSABLE):
        self.algorithm = algorithm
        self.blocks: Dict[bytes, DeduplicationBlock] = {}  # hash -> block
        self.total_saved_bytes = 0

    def store(self, data: bytes) -> bytes:
        """
        Store data with deduplication

        Args:
            data: Data to store

        Returns:
            Hash of the stored data
        """
        # Compute content hash
        content_hash = hashlib.sha256(data).digest()

        if content_hash in self.blocks:
            # Duplicate - increment reference count
            self.blocks[content_hash].reference_count += 1
            self.total_saved_bytes += len(data)
        else:
            # New unique content
            block = DeduplicationBlock(
                hash=content_hash,
                size=len(data),
                reference_count=1,
                data=data
            )
            self.blocks[content_hash] = block

        return content_hash

    def retrieve(self, hash: bytes) -> Optional[bytes]:
        """
        Retrieve data by hash

        Args:
            hash: Content hash

        Returns:
            Data if found, None otherwise
        """
        if hash in self.blocks:
            return self.blocks[hash].data
        return None

    def remove(self, hash: bytes) -> bool:
        """
        Remove reference to data

        Args:
            hash: Content hash

        Returns:
            True if block was removed, False otherwise
        """
        if hash in self.blocks:
            self.blocks[hash].reference_count -= 1
            if self.blocks[hash].reference_count <= 0:
                # No more references, remove block
                block_size = self.blocks[hash].size
                self.total_saved_bytes -= block_size * (self.blocks[hash].reference_count + 1)
                del self.blocks[hash]
                return True
        return False

    def get_statistics(self) -> Dict[str, int]:
        """
        Get deduplication statistics

        Returns:
            Dictionary with statistics
        """
        total_blocks = len(self.blocks)
        total_references = sum(block.reference_count for block in self.blocks.values())
        total_unique_bytes = sum(block.size for block in self.blocks.values())

        return {
            'total_blocks': total_blocks,
            'total_references': total_references,
            'total_unique_bytes': total_unique_bytes,
            'total_saved_bytes': self.total_saved_bytes,
            'deduplication_ratio': total_references / total_blocks if total_blocks > 0 else 1.0
        }

    def deduplicate_memory_region(self, memory_data: bytes, block_size: int = 4096) -> List[bytes]:
        """
        Deduplicate a memory region into blocks

        Args:
            memory_data: Memory region to deduplicate
            block_size: Size of fixed blocks

        Returns:
            List of block hashes
        """
        hashes = []

        if self.algorithm == DeduplicationAlgorithm.FIXED_BLOCK:
            # Fixed-size block deduplication
            for i in range(0, len(memory_data), block_size):
                block_data = memory_data[i:i + block_size]
                hash = self.store(block_data)
                hashes.append(hash)
        else:
            # Content-addressable (treat whole region as one block)
            hash = self.store(memory_data)
            hashes.append(hash)

        return hashes

    def reconstruct_memory_region(self, block_hashes: List[bytes]) -> Optional[bytes]:
        """
        Reconstruct memory region from block hashes

        Args:
            block_hashes: List of block hashes

        Returns:
            Reconstructed data or None if any block missing
        """
        reconstructed = bytearray()

        for hash in block_hashes:
            block_data = self.retrieve(hash)
            if block_data is None:
                return None  # Missing block
            reconstructed.extend(block_data)

        return bytes(reconstructed)
