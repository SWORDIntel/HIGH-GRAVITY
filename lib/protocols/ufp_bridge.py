import ctypes
import numpy as np
from pathlib import Path
from typing import Optional

UFP_MAX_TARGETS = 256
UFP_AGENT_NAME_SIZE = 64

class UfpMessage(ctypes.Structure):
    _fields_ = [
        ("msg_id", ctypes.c_uint32),
        ("msg_type", ctypes.c_int),
        ("priority", ctypes.c_int),
        ("source", ctypes.c_char * UFP_AGENT_NAME_SIZE),
        ("targets", (ctypes.c_char * UFP_AGENT_NAME_SIZE) * UFP_MAX_TARGETS),
        ("target_count", ctypes.c_uint8),
        ("payload", ctypes.c_void_p),
        ("payload_size", ctypes.c_size_t),
        ("timestamp", ctypes.c_uint32),
        ("correlation_id", ctypes.c_uint32),
        ("flags", ctypes.c_uint8),
    ]

class UFPBridge:
    def __init__(self, lib_path: Optional[str] = None):
        if not lib_path:
            repo_root = Path(__file__).resolve().parent.parent.parent
            lib_path = repo_root / "src" / "pegasus" / "agents" / "binary-communications-system" / "agent_bridge.so"
        
        if not lib_path.exists():
            raise FileNotFoundError(f"UFP binary bridge not found at {lib_path}")
            
        self.lib = ctypes.CDLL(str(lib_path))
        self._setup_api()
        
    def _setup_api(self):
        self.lib.ufp_init.restype = ctypes.c_int
        self.lib.ufp_pack_message.argtypes = [ctypes.POINTER(UfpMessage), ctypes.c_char_p, ctypes.c_size_t]
        self.lib.ufp_pack_message.restype = ctypes.c_ssize_t
        
        # Gold Standard MEMSHADOW Extensions
        if hasattr(self.lib, "memshadow_covert_vlan_init"):
            self.lib.memshadow_covert_vlan_init.restype = ctypes.c_void_p
            self.lib.memshadow_dpi_evasion_wrap.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
            self.lib.memshadow_dpi_evasion_wrap.restype = ctypes.c_ssize_t

    def enable_stealth_mode(self):
        """Activates Gold Standard DPI Evasion and Traffic Analysis Resistance."""
        if hasattr(self.lib, "memshadow_covert_vlan_init"):
            self.stealth_ctx = self.lib.memshadow_covert_vlan_init()
            print("[*] MEMSHADOW Stealth Mode Activated (Gold Standard).")
        else:
            print("[!] Stealth primitives not found in binary bridge.")

    def set_node_identity(self, node_type="HG-NODE"):
        """Broadcasts identity as a Pegasus HG-Node."""
        if hasattr(self.lib, "ufp_set_identity"):
            self.lib.ufp_set_identity(node_type.encode())
            print(f"[*] Node designated as {node_type} via MSHW.")
        else:
            print(f"[*] Node designated as {node_type} (mocked).")

    def send_task(self, target: str, task: str):
        msg = UfpMessage()
        msg.msg_type = 0x08 # UFP_MSG_TASK
        msg.source = b"PEGASUS_PROXY"
        
        # Correctly assign the target bytes to the C-array
        msg.targets[0].value = target.encode()
        
        msg.target_count = 1
        
        payload = task.encode()
        payload_buf = ctypes.create_string_buffer(payload)
        msg.payload = ctypes.cast(payload_buf, ctypes.c_void_p)
        msg.payload_size = len(payload)
        
        # Packing would follow here using ufp_pack_message
        buffer = ctypes.create_string_buffer(4096)
        res = self.lib.ufp_pack_message(ctypes.byref(msg), buffer, ctypes.sizeof(buffer))
        
        print(f"[*] Dispatched UFP Task: {task} -> {target}, Pack Result: {res}")

