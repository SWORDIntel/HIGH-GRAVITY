import ctypes
import os
import time
from src.pegasus.gsl_manager import GlobalStateLedger

class MemorySuperposition:
    """Handles agent state migration via memory-mapped buffers."""
    def __init__(self):
        self.gsl = GlobalStateLedger()
        self.shm_base = "/dev/shm/superposition_states"
        os.makedirs(self.shm_base, exist_ok=True)

    def checkpoint_agent(self, pid: int, state_data: bytes):
        """Dumps agent internal state to RAM disk."""
        checkpoint_path = os.path.join(self.shm_base, f"{pid}.bin")
        with open(checkpoint_path, "wb") as f:
            f.write(state_data)
        # Notify swarm through GSL that state is pinned
        self.gsl.post_delta(pid, "STATE_READY", 1)
        print(f"[*] Agent {pid} checkpointed to RAM disk.")

    def restore_agent(self, pid: int) -> bytes:
        """Loads agent internal state from RAM disk."""
        checkpoint_path = os.path.join(self.shm_base, f"{pid}.bin")
        if not os.path.exists(checkpoint_path):
            return b""
        with open(checkpoint_path, "rb") as f:
            return f.read()
        print(f"[*] Agent {pid} state restored.")
