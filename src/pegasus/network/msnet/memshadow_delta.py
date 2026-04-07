"""
MEMSHADOW Protocol - Delta Compression

Implements efficient delta compression for memory transfer,
using rsync-like algorithms and content-defined chunking.
"""

import hashlib
import struct
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass
from enum import IntEnum


class ChunkingAlgorithm(IntEnum):
    """Chunking algorithms"""
    FIXED_SIZE = 0
    CONTENT_DEFINED = 1  # Content-Defined Chunking (CDC)
    RABIN_KARP = 2  # Rabin-Karp rolling hash


@dataclass
class Chunk:
    """Data chunk"""
    chunk_id: int
    offset: int
    size: int
    hash: bytes  # Strong hash (SHA256)
    weak_hash: int  # Rolling hash for quick comparison
    data: Optional[bytes] = None  # Data (only if new/unique)


@dataclass
class Delta:
    """Delta information"""
    chunk_id: int
    offset: int
    size: int
    data: bytes  # New data for this chunk


class RollingHash:
    """
    Rolling hash for content-defined chunking
    
    Uses polynomial rolling hash (Rabin-Karp style).
    """
    
    def __init__(self, window_size: int = 48, base: int = 256, mod: int = 2**31 - 1):
        self.window_size = window_size
        self.base = base
        self.mod = mod
        self.base_power = pow(base, window_size - 1, mod)
    
    def compute(self, data: bytes) -> int:
        """Compute rolling hash for data"""
        if len(data) < self.window_size:
            # Pad with zeros
            data = data + b'\x00' * (self.window_size - len(data))
        
        hash_value = 0
        for byte in data[:self.window_size]:
            hash_value = (hash_value * self.base + byte) % self.mod
        
        return hash_value
    
    def roll(self, old_hash: int, old_byte: int, new_byte: int) -> int:
        """
        Roll hash forward
        
        Removes old_byte and adds new_byte.
        """
        hash_value = (old_hash - old_byte * self.base_power) % self.mod
        hash_value = (hash_value * self.base + new_byte) % self.mod
        return hash_value


class ContentDefinedChunker:
    """
    Content-Defined Chunking (CDC)
    
    Splits data into chunks based on content, not fixed size.
    This improves deduplication and delta compression.
    """
    
    def __init__(
        self,
        min_chunk_size: int = 512,
        avg_chunk_size: int = 2048,
        max_chunk_size: int = 8192,
        chunk_boundary_mask: int = 0x1FFF  # ~8KB average
    ):
        self.min_chunk_size = min_chunk_size
        self.avg_chunk_size = avg_chunk_size
        self.max_chunk_size = max_chunk_size
        self.chunk_boundary_mask = chunk_boundary_mask
        self.rolling_hash = RollingHash(window_size=48)
    
    def chunk(self, data: bytes) -> List[Tuple[int, int]]:
        """
        Chunk data using content-defined chunking
        
        Returns:
            List of (offset, size) tuples
        """
        chunks = []
        offset = 0
        data_len = len(data)
        
        while offset < data_len:
            chunk_start = offset
            
            # Minimum chunk size
            if offset + self.min_chunk_size > data_len:
                # Last chunk
                chunks.append((chunk_start, data_len - chunk_start))
                break
            
            # Compute initial rolling hash
            window = data[offset:offset + self.rolling_hash.window_size]
            hash_value = self.rolling_hash.compute(window)
            offset += self.rolling_hash.window_size
            
            # Look for chunk boundary
            while offset < data_len:
                # Check if this is a boundary
                if (hash_value & self.chunk_boundary_mask) == 0:
                    chunk_size = offset - chunk_start
                    if chunk_size >= self.min_chunk_size:
                        chunks.append((chunk_start, chunk_size))
                        break
                
                # Check max size
                if offset - chunk_start >= self.max_chunk_size:
                    chunks.append((chunk_start, self.max_chunk_size))
                    break
                
                # Roll hash forward
                if offset < data_len:
                    old_byte = data[offset - self.rolling_hash.window_size]
                    new_byte = data[offset]
                    hash_value = self.rolling_hash.roll(hash_value, old_byte, new_byte)
                
                offset += 1
            
            # Handle remaining data
            if offset >= data_len and offset > chunk_start:
                chunks.append((chunk_start, data_len - chunk_start))
        
        return chunks


class DeltaCompressor:
    """
    Delta compression for memory transfer
    
    Computes differences between old and new data,
    sending only changed chunks.
    """
    
    def __init__(self, chunking: ChunkingAlgorithm = ChunkingAlgorithm.CONTENT_DEFINED):
        self.chunking = chunking
        self.chunker = ContentDefinedChunker() if chunking == ChunkingAlgorithm.CONTENT_DEFINED else None
        self.chunk_cache: Dict[bytes, Chunk] = {}  # hash -> chunk
    
    def compute_chunks(self, data: bytes) -> List[Chunk]:
        """
        Compute chunks for data
        
        Returns:
            List of Chunk objects
        """
        if self.chunking == ChunkingAlgorithm.CONTENT_DEFINED and self.chunker:
            chunk_ranges = self.chunker.chunk(data)
        else:
            # Fixed-size chunking
            chunk_size = 2048
            chunk_ranges = [
                (i * chunk_size, min(chunk_size, len(data) - i * chunk_size))
                for i in range((len(data) + chunk_size - 1) // chunk_size)
            ]
        
        chunks = []
        for chunk_id, (offset, size) in enumerate(chunk_ranges):
            chunk_data = data[offset:offset + size]
            
            # Compute hashes
            strong_hash = hashlib.sha256(chunk_data).digest()
            weak_hash = self._compute_weak_hash(chunk_data)
            
            chunk = Chunk(
                chunk_id=chunk_id,
                offset=offset,
                size=size,
                hash=strong_hash,
                weak_hash=weak_hash,
                data=chunk_data
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def compute_delta(
        self,
        old_data: bytes,
        new_data: bytes
    ) -> Tuple[List[Delta], List[int]]:
        """
        Compute delta between old and new data
        
        Returns:
            (list of deltas, list of chunk IDs to reuse)
        """
        # Compute chunks for both
        old_chunks = self.compute_chunks(old_data)
        new_chunks = self.compute_chunks(new_data)
        
        # Build hash index for old chunks
        old_chunk_index: Dict[bytes, Chunk] = {}
        for chunk in old_chunks:
            old_chunk_index[chunk.hash] = chunk
        
        # Find matching chunks
        deltas = []
        reused_chunks = []
        
        for new_chunk in new_chunks:
            if new_chunk.hash in old_chunk_index:
                # Chunk exists in old data - reuse
                old_chunk = old_chunk_index[new_chunk.hash]
                reused_chunks.append(new_chunk.chunk_id)
            else:
                # New chunk - add to delta
                deltas.append(Delta(
                    chunk_id=new_chunk.chunk_id,
                    offset=new_chunk.offset,
                    size=new_chunk.size,
                    data=new_chunk.data
                ))
        
        return deltas, reused_chunks
    
    def apply_delta(
        self,
        old_data: bytes,
        deltas: List[Delta],
        reused_chunks: List[int],
        new_chunks: List[Chunk]
    ) -> bytes:
        """
        Apply delta to reconstruct new data
        
        Args:
            old_data: Original data
            deltas: List of new chunks
            reused_chunks: List of chunk IDs to reuse from old data
            new_chunks: Full list of new chunks (for ordering)
        
        Returns:
            Reconstructed new data
        """
        # Build old chunks
        old_chunks = self.compute_chunks(old_data)
        old_chunk_map = {c.chunk_id: c for c in old_chunks}
        
        # Build delta map
        delta_map = {d.chunk_id: d for d in deltas}
        
        # Reconstruct data
        result_parts = []
        for chunk in sorted(new_chunks, key=lambda c: c.chunk_id):
            if chunk.chunk_id in delta_map:
                # Use delta data
                delta = delta_map[chunk.chunk_id]
                result_parts.append(delta.data)
            elif chunk.chunk_id in reused_chunks and chunk.chunk_id in old_chunk_map:
                # Reuse from old data
                old_chunk = old_chunk_map[chunk.chunk_id]
                result_parts.append(old_data[old_chunk.offset:old_chunk.offset + old_chunk.size])
            else:
                # Missing chunk - use placeholder (would error in real implementation)
                result_parts.append(b'\x00' * chunk.size)
        
        return b''.join(result_parts)
    
    def _compute_weak_hash(self, data: bytes) -> int:
        """Compute weak hash for quick comparison"""
        # Simple checksum-style hash
        hash_value = 0
        for byte in data:
            hash_value = (hash_value * 31 + byte) & 0xFFFFFFFF
        return hash_value


class MemoryDeltaTransfer:
    """
    Memory delta transfer manager
    
    Handles incremental memory synchronization using delta compression.
    """
    
    def __init__(self):
        self.compressor = DeltaCompressor()
        self.memory_snapshots: Dict[str, bytes] = {}  # node_id -> snapshot
    
    def create_snapshot(self, node_id: str, memory_data: bytes):
        """Create memory snapshot for node"""
        self.memory_snapshots[node_id] = memory_data
    
    def compute_memory_delta(
        self,
        node_id: str,
        new_memory_data: bytes
    ) -> Tuple[List[Delta], List[int], int]:
        """
        Compute delta for memory update
        
        Returns:
            (deltas, reused_chunk_ids, compression_ratio)
        """
        if node_id not in self.memory_snapshots:
            # First sync - send all data
            chunks = self.compressor.compute_chunks(new_memory_data)
            deltas = [Delta(
                chunk_id=c.chunk_id,
                offset=c.offset,
                size=c.size,
                data=c.data
            ) for c in chunks]
            return deltas, [], 0
        
        old_data = self.memory_snapshots[node_id]
        deltas, reused = self.compressor.compute_delta(old_data, new_memory_data)
        
        # Calculate compression ratio
        original_size = len(new_memory_data)
        delta_size = sum(d.size for d in deltas)
        compression_ratio = (1 - delta_size / original_size) * 100 if original_size > 0 else 0
        
        return deltas, reused, compression_ratio
    
    def apply_memory_delta(
        self,
        node_id: str,
        deltas: List[Delta],
        reused_chunks: List[int]
    ) -> bytes:
        """
        Apply memory delta to reconstruct new memory state
        """
        if node_id not in self.memory_snapshots:
            # First sync - reconstruct from deltas only
            chunks = sorted(deltas, key=lambda d: d.chunk_id)
            return b''.join(d.data for d in chunks)
        
        old_data = self.memory_snapshots[node_id]
        old_chunks = self.compressor.compute_chunks(old_data)
        new_chunks = self.compressor.compute_chunks(old_data)  # Placeholder
        
        return self.compressor.apply_delta(old_data, deltas, reused_chunks, new_chunks)
    
    def update_snapshot(self, node_id: str, memory_data: bytes):
        """Update memory snapshot after successful sync"""
        self.memory_snapshots[node_id] = memory_data


class DeltaCompression:
    """
    Delta Compression - Simple diff-based compression

    Provides basic delta compression functionality for testing.
    """

    def __init__(self):
        self.compressor = DeltaCompressor()

    def compute_diff(self, old_data: bytes, new_data: bytes) -> List[Delta]:
        """
        Compute difference between old and new data

        Args:
            old_data: Original data
            new_data: Modified data

        Returns:
            List of deltas representing the differences
        """
        try:
            # Use the existing DeltaCompressor to compute chunks
            old_chunks = self.compressor.compute_chunks(old_data)
            new_chunks = self.compressor.compute_chunks(new_data)

            # Build chunk cache from old data
            chunk_cache = {chunk.hash: chunk for chunk in old_chunks}

            deltas = []
            for new_chunk in new_chunks:
                if new_chunk.hash in chunk_cache:
                    # Reuse existing chunk
                    old_chunk = chunk_cache[new_chunk.hash]
                    deltas.append(Delta(
                        chunk_id=new_chunk.chunk_id,
                        offset=new_chunk.offset,
                        size=new_chunk.size,
                        data=b""  # Empty data means reuse
                    ))
                else:
                    # New chunk, include data
                    deltas.append(Delta(
                        chunk_id=new_chunk.chunk_id,
                        offset=new_chunk.offset,
                        size=new_chunk.size,
                        data=new_chunk.data or b""
                    ))

            return deltas

        except Exception:
            # Fallback to simple byte-by-byte diff
            return [Delta(0, 0, len(new_data), new_data)]

    def apply_diff(self, old_data: bytes, deltas: List[Delta]) -> bytes:
        """
        Apply deltas to reconstruct new data

        Args:
            old_data: Original data
            deltas: List of deltas

        Returns:
            Reconstructed data
        """
        try:
            # For simplicity, reconstruct by applying deltas in order
            result = bytearray()
            old_chunks = self.compressor.compute_chunks(old_data)
            chunk_map = {chunk.chunk_id: chunk for chunk in old_chunks}

            for delta in deltas:
                if delta.data:  # New data
                    result.extend(delta.data)
                else:  # Reuse from old data
                    if delta.chunk_id in chunk_map:
                        old_chunk = chunk_map[delta.chunk_id]
                        result.extend(old_chunk.data or b"")

            return bytes(result)

        except Exception:
            # Fallback: if delta application fails, return original
            return old_data
