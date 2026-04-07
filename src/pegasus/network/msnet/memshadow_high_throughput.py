"""
MEMSHADOW Protocol - High-Throughput Optimizations

Optimizations for high-throughput local AI node communication:
- Zero-copy operations
- Parallel streams
- Batch processing
- Flow control
"""

import mmap
import os
import threading
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass
from enum import IntEnum
from queue import Queue
import struct


class StreamPriority(IntEnum):
    """Stream priority levels"""
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Stream:
    """Data stream"""
    stream_id: int
    priority: StreamPriority
    bandwidth_limit: Optional[int]  # bytes per second
    buffer: Queue


class SharedMemorySegment:
    """
    Shared memory segment for zero-copy operations
    
    Allows multiple processes to share memory without copying.
    """
    
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size
        self.fd = None
        self.mmap_obj = None
    
    def create(self) -> mmap.mmap:
        """Create shared memory segment"""
        # Create shared memory
        self.fd = os.memfd_create(self.name, 0)
        os.ftruncate(self.fd, self.size)
        
        # Map to memory
        self.mmap_obj = mmap.mmap(self.fd, self.size)
        return self.mmap_obj
    
    def open(self) -> mmap.mmap:
        """Open existing shared memory segment"""
        # Would open by name/file descriptor
        # Simplified for now
        return self.mmap_obj
    
    def close(self):
        """Close shared memory segment"""
        if self.mmap_obj:
            self.mmap_obj.close()
        if self.fd:
            os.close(self.fd)


class ZeroCopyTransport:
    """
    Zero-copy transport for local communication
    
    Uses shared memory to avoid copying data.
    """
    
    def __init__(self):
        self.segments: Dict[str, SharedMemorySegment] = {}
    
    def send_zero_copy(
        self,
        data: bytes,
        segment_name: str,
        offset: int = 0
    ) -> bool:
        """
        Send data using zero-copy
        
        Writes directly to shared memory segment.
        """
        if segment_name not in self.segments:
            segment = SharedMemorySegment(segment_name, len(data) + offset)
            mmap_obj = segment.create()
            self.segments[segment_name] = segment
        else:
            mmap_obj = self.segments[segment_name].open()
        
        # Write directly to shared memory (zero-copy)
        mmap_obj[offset:offset+len(data)] = data
        mmap_obj.flush()
        
        return True
    
    def receive_zero_copy(
        self,
        segment_name: str,
        size: int,
        offset: int = 0
    ) -> Optional[bytes]:
        """
        Receive data using zero-copy
        
        Reads directly from shared memory segment.
        """
        if segment_name not in self.segments:
            return None
        
        mmap_obj = self.segments[segment_name].open()
        return mmap_obj[offset:offset+size]


class ParallelStreamManager:
    """
    Manage multiple parallel data streams
    
    Allows concurrent data transfer over multiple streams.
    """
    
    def __init__(self, max_streams: int = 16):
        self.max_streams = max_streams
        self.streams: Dict[int, Stream] = {}
        self.stream_lock = threading.Lock()
        self.next_stream_id = 1
    
    def create_stream(
        self,
        priority: StreamPriority = StreamPriority.NORMAL,
        bandwidth_limit: Optional[int] = None
    ) -> int:
        """Create new stream"""
        with self.stream_lock:
            if len(self.streams) >= self.max_streams:
                raise ValueError("Maximum streams reached")
            
            stream_id = self.next_stream_id
            self.next_stream_id += 1
            
            self.streams[stream_id] = Stream(
                stream_id=stream_id,
                priority=priority,
                bandwidth_limit=bandwidth_limit,
                buffer=Queue()
            )
            
            return stream_id
    
    def send_on_stream(
        self,
        stream_id: int,
        data: bytes
    ) -> bool:
        """Send data on specific stream"""
        if stream_id not in self.streams:
            return False
        
        stream = self.streams[stream_id]
        stream.buffer.put(data)
        return True
    
    def receive_from_stream(
        self,
        stream_id: int,
        timeout: Optional[float] = None
    ) -> Optional[bytes]:
        """Receive data from specific stream"""
        if stream_id not in self.streams:
            return None
        
        stream = self.streams[stream_id]
        try:
            return stream.buffer.get(timeout=timeout)
        except:
            return None
    
    def get_streams_by_priority(self) -> List[int]:
        """Get stream IDs sorted by priority"""
        with self.stream_lock:
            sorted_streams = sorted(
                self.streams.items(),
                key=lambda x: x[1].priority.value,
                reverse=True
            )
            return [s[0] for s in sorted_streams]


class BatchProcessor:
    """
    Batch message processing for efficiency
    
    Combines multiple messages into batches for better throughput.
    """
    
    def __init__(self, max_batch_size: int = 64 * 1024, max_batch_count: int = 100):
        self.max_batch_size = max_batch_size
        self.max_batch_count = max_batch_count
        self.pending_messages: List[bytes] = []
        self.batch_lock = threading.Lock()
    
    def add_message(self, message: bytes) -> Optional[bytes]:
        """
        Add message to batch
        
        Returns:
            Batch if ready to send, None otherwise
        """
        with self.batch_lock:
            self.pending_messages.append(message)
            
            # Check if batch is ready
            total_size = sum(len(m) for m in self.pending_messages)
            
            if (len(self.pending_messages) >= self.max_batch_count or
                total_size >= self.max_batch_size):
                return self._create_batch()
            
            return None
    
    def _create_batch(self) -> bytes:
        """Create batch from pending messages"""
        batch_header = struct.pack('>I', len(self.pending_messages))
        batch_data = b''.join(self.pending_messages)
        
        self.pending_messages.clear()
        
        return batch_header + batch_data
    
    def unpack_batch(self, batch: bytes) -> List[bytes]:
        """Unpack batch into individual messages"""
        if len(batch) < 4:
            return []
        
        count = struct.unpack('>I', batch[:4])[0]
        offset = 4
        
        messages = []
        for _ in range(count):
            if offset >= len(batch):
                break
            # Simplified - would need message length prefix
            # For now, assume equal-sized messages
            msg_size = (len(batch) - offset) // (count - len(messages))
            messages.append(batch[offset:offset+msg_size])
            offset += msg_size
        
        return messages


class FlowController:
    """
    Advanced flow control for high-throughput
    
    Implements BBR-like congestion control and per-stream flow control.
    """
    
    def __init__(self):
        self.window_size: Dict[int, int] = {}  # stream_id -> window size
        self.bytes_in_flight: Dict[int, int] = {}  # stream_id -> bytes in flight
        self.rtt_estimates: Dict[int, float] = {}  # stream_id -> RTT estimate
    
    def update_window(
        self,
        stream_id: int,
        bytes_acked: int,
        rtt: float
    ):
        """Update flow control window"""
        if stream_id not in self.window_size:
            self.window_size[stream_id] = 65536  # Initial window
            self.rtt_estimates[stream_id] = rtt
        
        # BBR-like algorithm (simplified)
        self.rtt_estimates[stream_id] = (
            0.875 * self.rtt_estimates[stream_id] + 0.125 * rtt
        )
        
        # Increase window if no congestion
        if bytes_acked > 0:
            self.window_size[stream_id] = min(
                self.window_size[stream_id] + bytes_acked,
                16 * 1024 * 1024  # Max window
            )
    
    def can_send(
        self,
        stream_id: int,
        bytes_to_send: int
    ) -> bool:
        """Check if can send data on stream"""
        if stream_id not in self.window_size:
            return True
        
        current_in_flight = self.bytes_in_flight.get(stream_id, 0)
        return (current_in_flight + bytes_to_send) <= self.window_size[stream_id]
    
    def record_sent(self, stream_id: int, bytes_sent: int):
        """Record bytes sent"""
        self.bytes_in_flight[stream_id] = (
            self.bytes_in_flight.get(stream_id, 0) + bytes_sent
        )
    
    def record_acked(self, stream_id: int, bytes_acked: int):
        """Record bytes acknowledged"""
        self.bytes_in_flight[stream_id] = max(
            0,
            self.bytes_in_flight.get(stream_id, 0) - bytes_acked
        )


class HighThroughputManager:
    """
    Main high-throughput manager
    
    Coordinates all optimizations for maximum throughput.
    """
    
    def __init__(self, enable_zero_copy: bool = True):
        self.zero_copy = ZeroCopyTransport() if enable_zero_copy else None
        self.stream_manager = ParallelStreamManager()
        self.batch_processor = BatchProcessor()
        self.flow_controller = FlowController()
    
    def send_optimized(
        self,
        data: bytes,
        use_zero_copy: bool = True,
        stream_id: Optional[int] = None
    ) -> bool:
        """
        Send data with optimizations
        
        Uses zero-copy and batching if enabled.
        """
        # Add to batch
        batch = self.batch_processor.add_message(data)
        
        if batch:
            # Send batch
            if use_zero_copy and self.zero_copy:
                segment_name = f"memshadow_{stream_id or 0}"
                return self.zero_copy.send_zero_copy(batch, segment_name)
            else:
                # Regular send (would use transport layer)
                return True
        
        return True
    
    def create_high_priority_stream(self) -> int:
        """Create high-priority stream"""
        return self.stream_manager.create_stream(
            priority=StreamPriority.HIGH,
            bandwidth_limit=None
        )
