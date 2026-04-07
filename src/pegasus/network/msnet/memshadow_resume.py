"""
MEMSHADOW Protocol - Resume Capability

Implements resumable file transfers with state persistence.
"""

import os
import json
import hashlib
import time
import pickle
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import IntEnum


class TransferState(IntEnum):
    """Transfer state"""
    INITIALIZING = 0
    IN_PROGRESS = 1
    PAUSED = 2
    COMPLETED = 3
    FAILED = 4
    CANCELLED = 5


@dataclass
class ChunkInfo:
    """Information about a transfer chunk"""
    chunk_id: int
    offset: int
    size: int
    checksum: Optional[str] = None
    received: bool = False
    verified: bool = False
    received_at: Optional[float] = None


@dataclass
class TransferState:
    """State of a file transfer"""
    transfer_id: str
    file_path: str
    file_size: int
    total_chunks: int
    chunk_size: int
    state: TransferState
    chunks: List[ChunkInfo]
    created_at: float
    updated_at: float
    peer_id: str
    checksum_algorithm: str = "sha256"
    file_checksum: Optional[str] = None
    bytes_transferred: int = 0
    bytes_verified: int = 0


class ResumableTransfer:
    """
    Resumable file transfer manager
    
    Tracks transfer state and allows resuming interrupted transfers.
    """
    
    def __init__(self, state_dir: str = "/tmp/memshadow_transfers"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.active_transfers: Dict[str, TransferState] = {}
    
    def create_transfer(
        self,
        transfer_id: str,
        file_path: str,
        file_size: int,
        chunk_size: int,
        peer_id: str,
        file_checksum: Optional[str] = None
    ) -> TransferState:
        """
        Create new transfer state
        
        Args:
            transfer_id: Unique transfer identifier
            file_path: Destination file path
            file_size: Total file size in bytes
            chunk_size: Size of each chunk
            peer_id: Peer node ID
            file_checksum: Optional file checksum for verification
        
        Returns:
            TransferState object
        """
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        # Create chunk info for each chunk
        chunks = []
        for i in range(total_chunks):
            offset = i * chunk_size
            size = min(chunk_size, file_size - offset)
            chunks.append(ChunkInfo(
                chunk_id=i,
                offset=offset,
                size=size
            ))
        
        transfer_state = TransferState(
            transfer_id=transfer_id,
            file_path=file_path,
            file_size=file_size,
            total_chunks=total_chunks,
            chunk_size=chunk_size,
            state=TransferState.INITIALIZING,
            chunks=chunks,
            created_at=time.time(),
            updated_at=time.time(),
            peer_id=peer_id,
            file_checksum=file_checksum
        )
        
        self.active_transfers[transfer_id] = transfer_state
        self._save_state(transfer_state)
        
        return transfer_state
    
    def load_transfer(self, transfer_id: str) -> Optional[TransferState]:
        """
        Load transfer state from disk
        
        Returns:
            TransferState if found, None otherwise
        """
        if transfer_id in self.active_transfers:
            return self.active_transfers[transfer_id]
        
        state_file = self.state_dir / f"{transfer_id}.json"
        if not state_file.exists():
            return None
        
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
            
            # Reconstruct TransferState
            chunks = [ChunkInfo(**c) for c in data['chunks']]
            transfer_state = TransferState(
                transfer_id=data['transfer_id'],
                file_path=data['file_path'],
                file_size=data['file_size'],
                total_chunks=data['total_chunks'],
                chunk_size=data['chunk_size'],
                state=TransferState(data['state']),
                chunks=chunks,
                created_at=data['created_at'],
                updated_at=data['updated_at'],
                peer_id=data['peer_id'],
                checksum_algorithm=data.get('checksum_algorithm', 'sha256'),
                file_checksum=data.get('file_checksum'),
                bytes_transferred=data.get('bytes_transferred', 0),
                bytes_verified=data.get('bytes_verified', 0)
            )
            
            self.active_transfers[transfer_id] = transfer_state
            return transfer_state
        
        except Exception as e:
            print(f"Error loading transfer state: {e}")
            return None
    
    def mark_chunk_received(
        self,
        transfer_id: str,
        chunk_id: int,
        checksum: Optional[str] = None
    ) -> bool:
        """
        Mark chunk as received
        
        Args:
            transfer_id: Transfer identifier
            chunk_id: Chunk identifier
            checksum: Optional chunk checksum
        
        Returns:
            True if successful
        """
        transfer_state = self.load_transfer(transfer_id)
        if not transfer_state:
            return False
        
        if chunk_id >= len(transfer_state.chunks):
            return False
        
        chunk = transfer_state.chunks[chunk_id]
        chunk.received = True
        chunk.received_at = time.time()
        if checksum:
            chunk.checksum = checksum
        
        # Update transfer state
        transfer_state.state = TransferState.IN_PROGRESS
        transfer_state.updated_at = time.time()
        transfer_state.bytes_transferred = sum(
            c.size for c in transfer_state.chunks if c.received
        )
        
        self._save_state(transfer_state)
        return True
    
    def mark_chunk_verified(self, transfer_id: str, chunk_id: int) -> bool:
        """Mark chunk as verified"""
        transfer_state = self.load_transfer(transfer_id)
        if not transfer_state:
            return False
        
        if chunk_id >= len(transfer_state.chunks):
            return False
        
        chunk = transfer_state.chunks[chunk_id]
        chunk.verified = True
        
        transfer_state.bytes_verified = sum(
            c.size for c in transfer_state.chunks if c.verified
        )
        
        self._save_state(transfer_state)
        return True
    
    def get_missing_chunks(self, transfer_id: str) -> List[int]:
        """
        Get list of missing chunk IDs
        
        Returns:
            List of chunk IDs that need to be received
        """
        transfer_state = self.load_transfer(transfer_id)
        if not transfer_state:
            return []
        
        return [
            chunk.chunk_id
            for chunk in transfer_state.chunks
            if not chunk.received
        ]
    
    def get_unverified_chunks(self, transfer_id: str) -> List[int]:
        """Get list of unverified chunk IDs"""
        transfer_state = self.load_transfer(transfer_id)
        if not transfer_state:
            return []
        
        return [
            chunk.chunk_id
            for chunk in transfer_state.chunks
            if chunk.received and not chunk.verified
        ]
    
    def get_progress(self, transfer_id: str) -> Tuple[float, int, int]:
        """
        Get transfer progress
        
        Returns:
            (progress_percentage, bytes_transferred, bytes_total)
        """
        transfer_state = self.load_transfer(transfer_id)
        if not transfer_state:
            return (0.0, 0, 0)
        
        progress = (transfer_state.bytes_transferred / transfer_state.file_size * 100) if transfer_state.file_size > 0 else 0.0
        return (
            progress,
            transfer_state.bytes_transferred,
            transfer_state.file_size
        )
    
    def complete_transfer(self, transfer_id: str) -> bool:
        """Mark transfer as completed"""
        transfer_state = self.load_transfer(transfer_id)
        if not transfer_state:
            return False
        
        transfer_state.state = TransferState.COMPLETED
        transfer_state.updated_at = time.time()
        
        self._save_state(transfer_state)
        return True
    
    def pause_transfer(self, transfer_id: str) -> bool:
        """Pause transfer"""
        transfer_state = self.load_transfer(transfer_id)
        if not transfer_state:
            return False
        
        transfer_state.state = TransferState.PAUSED
        transfer_state.updated_at = time.time()
        
        self._save_state(transfer_state)
        return True
    
    def resume_transfer(self, transfer_id: str) -> bool:
        """Resume paused transfer"""
        transfer_state = self.load_transfer(transfer_id)
        if not transfer_state:
            return False
        
        if transfer_state.state != TransferState.PAUSED:
            return False
        
        transfer_state.state = TransferState.IN_PROGRESS
        transfer_state.updated_at = time.time()
        
        self._save_state(transfer_state)
        return True
    
    def cancel_transfer(self, transfer_id: str) -> bool:
        """Cancel transfer"""
        transfer_state = self.load_transfer(transfer_id)
        if not transfer_state:
            return False
        
        transfer_state.state = TransferState.CANCELLED
        transfer_state.updated_at = time.time()
        
        self._save_state(transfer_state)
        return True
    
    def _save_state(self, transfer_state: TransferState):
        """Save transfer state to disk"""
        state_file = self.state_dir / f"{transfer_state.transfer_id}.json"
        
        try:
            # Convert to dict
            data = {
                'transfer_id': transfer_state.transfer_id,
                'file_path': transfer_state.file_path,
                'file_size': transfer_state.file_size,
                'total_chunks': transfer_state.total_chunks,
                'chunk_size': transfer_state.chunk_size,
                'state': transfer_state.state.value,
                'chunks': [asdict(c) for c in transfer_state.chunks],
                'created_at': transfer_state.created_at,
                'updated_at': transfer_state.updated_at,
                'peer_id': transfer_state.peer_id,
                'checksum_algorithm': transfer_state.checksum_algorithm,
                'file_checksum': transfer_state.file_checksum,
                'bytes_transferred': transfer_state.bytes_transferred,
                'bytes_verified': transfer_state.bytes_verified
            }
            
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            print(f"Error saving transfer state: {e}")
    
    def cleanup_old_transfers(self, max_age_days: int = 7):
        """Clean up old completed/failed transfers"""
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600
        
        for state_file in self.state_dir.glob("*.json"):
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                
                age = current_time - data.get('updated_at', 0)
                state = data.get('state', 0)
                
                # Clean up old completed/failed/cancelled transfers
                if (age > max_age_seconds and
                    state in [TransferState.COMPLETED.value,
                             TransferState.FAILED.value,
                             TransferState.CANCELLED.value]):
                    state_file.unlink()
            
            except Exception:
                pass


class ResumeCapability:
    """
    Resume Capability - Simple checkpoint-based resumption

    Provides basic checkpoint functionality for testing.
    """

    def __init__(self, checkpoint_dir: str = "/tmp/memshadow_checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints: Dict[str, int] = {}

    def save_checkpoint(self, transfer_id: str, offset: int):
        """
        Save transfer checkpoint

        Args:
            transfer_id: Transfer identifier
            offset: Current transfer offset
        """
        self.checkpoints[transfer_id] = offset

        # Also save to file for persistence
        checkpoint_file = self.checkpoint_dir / f"{transfer_id}.checkpoint"
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump({'offset': offset, 'timestamp': time.time()}, f)
        except Exception:
            pass  # Ignore file write errors

    def get_checkpoint(self, transfer_id: str) -> Optional[int]:
        """
        Get saved checkpoint offset

        Args:
            transfer_id: Transfer identifier

        Returns:
            Saved offset or None if not found
        """
        # Check in-memory cache first
        if transfer_id in self.checkpoints:
            return self.checkpoints[transfer_id]

        # Check file system
        checkpoint_file = self.checkpoint_dir / f"{transfer_id}.checkpoint"
        try:
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                    offset = data.get('offset', 0)
                    self.checkpoints[transfer_id] = offset  # Cache it
                    return offset
        except Exception:
            pass

        return None

    def clear_checkpoint(self, transfer_id: str):
        """
        Clear saved checkpoint

        Args:
            transfer_id: Transfer identifier
        """
        if transfer_id in self.checkpoints:
            del self.checkpoints[transfer_id]

        checkpoint_file = self.checkpoint_dir / f"{transfer_id}.checkpoint"
        try:
            if checkpoint_file.exists():
                checkpoint_file.unlink()
        except Exception:
            pass
