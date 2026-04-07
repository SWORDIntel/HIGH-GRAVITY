import os
import ctypes
import numpy as np
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

# --- QIHSE Types ---
class QihseAnchorConfig(ctypes.Structure):
    _fields_ = [
        ("max_anchors", ctypes.c_size_t),
        ("min_anchors", ctypes.c_size_t),
        ("anchor_prune_threshold", ctypes.c_double),
        ("memory_budget_mb", ctypes.c_size_t),
        ("enable_anchor_learning", ctypes.c_bool),
        ("chunk_size", ctypes.c_size_t),
        ("enable_anchor_simd", ctypes.c_bool),
        ("workload_type", ctypes.c_int)
    ]

class QihseAmplificationConfig(ctypes.Structure):
    _fields_ = [
        ("min_rounds", ctypes.c_int),
        ("max_rounds", ctypes.c_int),
        ("convergence_threshold", ctypes.c_double),
        ("oracle_selectivity", ctypes.c_double),
        ("adaptive_rounds", ctypes.c_bool),
        ("fixed_rounds", ctypes.c_int)
    ]

class QihseVerifyConfig(ctypes.Structure):
    _fields_ = [
        ("mode", ctypes.c_int),
        ("window_size", ctypes.c_size_t),
        ("min_confidence", ctypes.c_double),
        ("fallback_to_classical", ctypes.c_bool),
        ("max_verification_time_us", ctypes.c_size_t)
    ]

class QihseBackendPriority(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("priority_weight", ctypes.c_float),
        ("enabled", ctypes.c_bool),
        ("memory_limit", ctypes.c_size_t)
    ]

class QihseTypeDescriptor(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("element_size", ctypes.c_size_t),
        ("hash_fn", ctypes.c_void_p),
        ("compare_fn", ctypes.c_void_p),
        ("embed_fn", ctypes.c_void_p),
        ("type_name", ctypes.c_char_p)
    ]

class QihseConfig(ctypes.Structure):
    _fields_ = [
        ("anchor_config", QihseAnchorConfig),
        ("auto_dimensions", ctypes.c_bool),
        ("fixed_dimensions", ctypes.c_size_t),
        ("max_dimensions", ctypes.c_size_t),
        ("min_dimensions", ctypes.c_size_t),
        ("data_type", ctypes.c_int),
        ("type_descriptor", QihseTypeDescriptor),
        ("rff_gamma", ctypes.c_double),
        ("random_seed", ctypes.c_uint64),
        ("amplification", QihseAmplificationConfig),
        ("verification", QihseVerifyConfig),
        ("use_heterogeneous", ctypes.c_bool),
        ("enable_acceleration", ctypes.c_bool),
        ("max_batch_size", ctypes.c_size_t),
        ("enable_profiling", ctypes.c_bool),
        ("use_parallel_pipelines", ctypes.c_bool),
        ("max_parallel_pipelines", ctypes.c_size_t),
        ("timeout_ms", ctypes.c_uint32),
        ("fail_fast", ctypes.c_bool),
        ("backend_priority", QihseBackendPriority * 8),
        ("num_backends", ctypes.c_size_t),
        ("adaptive_backend", ctypes.c_bool),
        ("memory_pooling", ctypes.c_bool),
        ("memory_pool_size", ctypes.c_size_t)
    ]

class QIHSE:
    def __init__(self):
        # Locate library
        repo_root = Path(__file__).resolve().parent.parent
        lib_path = repo_root / "lib" / "binaries" / "libqihse.so"
        
        if not lib_path.exists():
            raise FileNotFoundError(f"QIHSE library not found at {lib_path}")
            
        self.lib = ctypes.CDLL(str(lib_path))
        self._setup_api()

    def _setup_api(self):
        # Versioning
        self.lib.qihse_version.restype = ctypes.c_char_p
        self.lib.qihse_build_info.restype = ctypes.c_char_p
        self.lib.qihse_available.restype = ctypes.c_bool
        
        # Config
        self.lib.qihse_config_init.argtypes = [ctypes.POINTER(QihseConfig), ctypes.c_int, ctypes.c_size_t]
        self.lib.qihse_config_init.restype = ctypes.c_int
        
        # Search
        self.lib.qihse_search.argtypes = [
            ctypes.c_void_p, # data
            ctypes.c_size_t, # n
            ctypes.c_void_p, # query
            ctypes.c_void_p, # anchor table (NULL ok)
            ctypes.POINTER(QihseConfig)
        ]
        self.lib.qihse_search.restype = ctypes.c_size_t

    def get_version(self) -> str:
        return self.lib.qihse_version().decode()

    def get_build_info(self) -> str:
        return self.lib.qihse_build_info().decode()

    def is_available(self) -> bool:
        return self.lib.qihse_available()

    def search_int64(self, data: np.ndarray, query: int) -> int:
        """High-performance search on sorted int64 array."""
        if not isinstance(data, np.ndarray):
            data = np.array(data, dtype=np.int64)
        
        if data.dtype != np.int64:
            data = data.astype(np.int64)
            
        # Ensure contiguous
        data = np.ascontiguousarray(data)
        
        config = QihseConfig()
        self.lib.qihse_config_init(ctypes.byref(config), 0, len(data)) # 0 = QIHSE_TYPE_INT64
        
        q_val = ctypes.c_int64(query)
        
        result = self.lib.qihse_search(
            data.ctypes.data_as(ctypes.c_void_p),
            len(data),
            ctypes.byref(q_val),
            None,
            ctypes.byref(config)
        )
        
        return int(result)

    def search_binary(self, data: List[bytes], query: bytes) -> int:
        """
        Quantum-Inspired search on binary blobs (hashes).
        Note: Current QIHSE C implementation expects fixed-size keys for fast SIMD.
        We convert hashes to int64 prefixes for the fast path.
        """
        # For GhostCache, we can convert the first 8 bytes of the SHA-384 hash to int64
        # to use the ultra-fast QIHSE_TYPE_INT64 path. (CNSA 2.0 Compliant)
        
        data_prefixes = np.array([int.from_bytes(b[:8], 'big') for b in data], dtype=np.int64)
        query_prefix = int.from_bytes(query[:8], 'big')
        
        # QIHSE requires sorted data for maximum speedup (interpolation search component)
        indices = np.argsort(data_prefixes)
        sorted_prefixes = data_prefixes[indices]
        
        idx = self.search_int64(sorted_prefixes, query_prefix)
        
        if idx < len(indices):
            actual_idx = indices[idx]
            # Verify full hash to prevent collisions
            if data[actual_idx] == query:
                return actual_idx
                
        return -1 # NOT_FOUND

if __name__ == "__main__":
    q = QIHSE()
    print(f"QIHSE Initialized: {q.get_version()}")
    print(f"Available: {q.is_available()}")
    
    # Simple Benchmark
    size = 1000000
    test_data = np.sort(np.random.randint(0, 10**12, size, dtype=np.int64))
    target_idx = size // 2
    target = test_data[target_idx]
    
    import time
    start = time.perf_counter()
    res = q.search_int64(test_data, target)
    end = time.perf_counter()
    
    print(f"Search for {target} in {size} elements took {(end-start)*1000:.4f}ms")
    print(f"Result: {res} (Expected: {target_idx})")
