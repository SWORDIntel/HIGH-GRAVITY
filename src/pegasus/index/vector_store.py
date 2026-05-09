import numpy as np
import hashlib
import time
import json
from pathlib import Path
from typing import Optional, List, Dict
from src.qihse_wrapper import QIHSE
from src.turbo_quant import TurboQuantIndex

class PegasusVectorStore:
    """Full-integrated memory-resident vector index powered by TurboQuant and QIHSE."""
    def __init__(self):
        self.qihse = QIHSE()
        self.tq_index = TurboQuantIndex()
        self.vector_data = [] # List of binary hashes (SHA-384)
        self.metadata = {}    # Map: hash -> file_info
        
    def add_artifact(self, content: str, file_path: str):
        # CNSA 2.0 Compliant SHA-384
        content_hash = hashlib.sha384(content.encode()).digest()
        if content_hash not in self.metadata:
            self.vector_data.append(content_hash)
            self.tq_index.add(content_hash)
            self.metadata[content_hash] = {
                "path": file_path,
                "timestamp": time.time(),
                "type": "code_artifact",
                "length": len(content)
            }
    
    def add_file(self, file_path: str, content: str):
        """Alias for add_artifact for compatibility"""
        self.add_artifact(content, file_path)
        
    def query_context(self, query: str, threshold: float = 0.85) -> Optional[dict]:
        """Performs semantic search for query context using TurboQuant ANN."""
        query_hash = hashlib.sha384(query.encode()).digest()
        
        # 1. Exact match attempt
        if query_hash in self.metadata:
            return self.metadata[query_hash]
            
        # 2. TurboQuant ANN — Semantic similarity lookup
        ann_hash = self.tq_index.search(query_hash, threshold=threshold)
        if ann_hash:
            return self.metadata.get(ann_hash)
            
        # 3. QIHSE binary search fallback (exact hash in pool)
        idx = self.qihse.search_binary(self.vector_data, query_hash)
        if idx != -1:
            return self.metadata.get(self.vector_data[idx])
            
        return None

    def get_stats(self) -> dict:
        return {
            "indexed_artifacts": len(self.vector_data),
            "memory_usage_bytes": self.tq_index.memory_bytes,
            "compression_ratio": f"{self.tq_index.raw_bytes / max(1, self.tq_index.memory_bytes):.2f}x"
        }
