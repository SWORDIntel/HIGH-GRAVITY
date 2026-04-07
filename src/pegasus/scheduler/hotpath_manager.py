import mmap
import os
import struct
import tempfile
import logging
from typing import Optional

logger = logging.getLogger("HotPathManager")

class HotPathManager:
    """
    Manages a shared memory pool using mmap for zero-copy message transfer
    between the C-based binary layer and Python.
    
    Optimized for Linux using /dev/shm (POSIX shared memory) when available,
    and memoryview objects for true zero-copy reads and writes.
    """
    
    # Header: [uint32 head][uint32 tail][uint32 flags][uint32 capacity]
    HEADER_FORMAT = "<IIII"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    
    def __init__(self, filepath: Optional[str] = None, size: int = 1024 * 1024):
        if filepath is None:
            # Default to RAM disk on Linux for true shared memory performance
            shm_dir = "/dev/shm" if os.path.exists("/dev/shm") else tempfile.gettempdir()
            self.filepath = os.path.join(shm_dir, "swordswarm_hotpath.shm")
        else:
            self.filepath = filepath
            
        self.size = max(size, self.HEADER_SIZE + 1024)  # Minimum size
        self.file_obj = None
        self.mmap_obj = None
        self._initialize_pool()

    def _initialize_pool(self):
        is_new = not os.path.exists(self.filepath)
        
        if is_new:
            # Create file with zeroes
            with open(self.filepath, 'wb') as f:
                f.write(b'\x00' * self.size)
        else:
            current_size = os.path.getsize(self.filepath)
            if current_size < self.size:
                with open(self.filepath, 'ab') as f:
                    f.write(b'\x00' * (self.size - current_size))

        self.file_obj = open(self.filepath, 'r+b')
        self.mmap_obj = mmap.mmap(self.file_obj.fileno(), self.size, access=mmap.ACCESS_WRITE)
        
        if is_new:
            self.reset_header()
            
        logger.info(f"HotPathManager initialized pool at {self.filepath} (Size: {self.size} bytes)")

    def reset_header(self):
        """Resets the ring buffer pointers and flags."""
        struct.pack_into(self.HEADER_FORMAT, self.mmap_obj, 0, 0, 0, 0, self.size - self.HEADER_SIZE)

    def get_header(self):
        """Returns (head, tail, flags, capacity)."""
        return struct.unpack_from(self.HEADER_FORMAT, self.mmap_obj, 0)

    def get_view(self, offset: int, length: int) -> memoryview:
        """
        Returns a zero-copy memoryview of the requested region.
        This allows parsing/reading without allocating new bytes objects.
        """
        if offset + length > self.size:
            raise ValueError(f"Read request (offset={offset}, len={length}) exceeds allocated memory pool size ({self.size}).")
        
        return memoryview(self.mmap_obj)[offset:offset + length]

    def write_message(self, offset: int, data: bytes):
        """Writes data to the shared memory pool at the specified offset."""
        if offset + len(data) > self.size:
            raise ValueError(f"Data exceeds allocated memory pool size ({self.size}).")
        
        self.mmap_obj.seek(offset)
        self.mmap_obj.write(data)

    def read_message(self, offset: int, length: int) -> bytes:
        """Reads a message as bytes (allocates memory). Prefer get_view() for zero-copy."""
        if offset + length > self.size:
            raise ValueError(f"Read request exceeds allocated memory pool size.")
        
        self.mmap_obj.seek(offset)
        return self.mmap_obj.read(length)

    def get_segment(self, segment_index: int, segment_size: int = 512) -> memoryview:
        """
        Returns a memoryview for a specific cache segment.
        Segment 0 starts after the header (offset 1024).
        """
        offset = 1024 + (segment_index * segment_size)
        return self.get_view(offset, segment_size)

    def write_segment(self, segment_index: int, data: bytes, segment_size: int = 512):
        """Writes data to a specific cache segment."""
        offset = 1024 + (segment_index * segment_size)
        if len(data) > segment_size:
            raise ValueError(f"Data size {len(data)} exceeds segment size {segment_size}")
        self.write_message(offset, data)

    def close(self):
        """Closes the memory mapped file and file object."""
        if self.mmap_obj:
            self.mmap_obj.close()
            self.mmap_obj = None
        if self.file_obj:
            self.file_obj.close()
            self.file_obj = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
