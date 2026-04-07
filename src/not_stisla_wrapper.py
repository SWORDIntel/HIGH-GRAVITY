import ctypes
import numpy as np
from pathlib import Path
from typing import List, Optional

class NotStisla:
    """Python wrapper for NOT_STISLA search algorithm."""
    def __init__(self):
        repo_root = Path(__file__).resolve().parent.parent
        lib_path = repo_root / "lib" / "binaries" / "libnot_stisla.so"
        
        if not lib_path.exists():
            raise FileNotFoundError(f"NOT_STISLA library not found at {lib_path}")
            
        self.lib = ctypes.CDLL(str(lib_path))
        self._setup_api()
        
    def _setup_api(self):
        # Anchor Table
        self.lib.not_stisla_anchor_table_create.restype = ctypes.c_void_p
        self.lib.not_stisla_anchor_table_destroy.argtypes = [ctypes.c_void_p]
        
        # Search
        self.lib.not_stisla_search.argtypes = [
            ctypes.POINTER(ctypes.c_int64), # data
            ctypes.c_size_t,               # n
            ctypes.c_int64,                # target
            ctypes.c_void_p,               # anchor table
            ctypes.c_double                # tolerance
        ]
        self.lib.not_stisla_search.restype = ctypes.c_int64

    def search_hashes(self, sorted_hashes: np.ndarray, target_hash: int) -> int:
        """High-speed interpolation search for hash values."""
        table = self.lib.not_stisla_anchor_table_create()
        try:
            # NOT_STISLA expects int64
            # We treat the first 8 bytes of SHA-384 as a signed int64
            idx = self.lib.not_stisla_search(
                sorted_hashes.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),
                len(sorted_hashes),
                ctypes.c_int64(target_hash),
                table,
                ctypes.c_double(0.01)
            )
            return int(idx)
        finally:
            self.lib.not_stisla_anchor_table_destroy(table)

if __name__ == "__main__":
    n = NotStisla()
    print("[*] NOT_STISLA Initialized.")
    
    # Simple benchmark
    size = 1000000
    data = np.sort(np.random.randint(-(2**63), 2**63 - 1, size, dtype=np.int64))
    target_idx = size // 2
    target = data[target_idx]
    
    import time
    start = time.perf_counter()
    res = n.search_hashes(data, target)
    end = time.perf_counter()
    
    print(f"Search for {target} in {size} elements took {(end-start)*1000:.4f}ms")
    print(f"Result: {res} (Expected: {target_idx})")
