import mmap
import os
import struct

class GlobalStateLedger:
    """Memory-mapped ledger for O(n) swarm coordination."""
    def __init__(self, size=1024*1024): # 1MB shared state
        self.size = size
        self.shm_path = "/dev/shm/swordswarm_gsl"
        if not os.path.exists(self.shm_path):
            with open(self.shm_path, "wb") as f:
                f.write(b"\x00" * size)
        
        self.fd = os.open(self.shm_path, os.O_RDWR)
        self.map = mmap.mmap(self.fd, size)

    def post_delta(self, agent_id: int, key: str, value: int):
        # Extremely simple delta post: [AgentID:4][KeyHash:4][Value:8]
        offset = (agent_id % 1024) * 16
        self.map.seek(offset)
        self.map.write(struct.pack('IIQ', agent_id, hash(key) & 0xFFFFFFFF, value))

    def read_state(self, agent_id: int):
        offset = (agent_id % 1024) * 16
        self.map.seek(offset)
        return struct.unpack('IIQ', self.map.read(16))
