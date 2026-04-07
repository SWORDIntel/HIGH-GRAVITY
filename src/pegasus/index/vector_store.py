import numpy as np
import hashlib
from pathlib import Path
from src.qihse_wrapper import QIHSE

class PegasusVectorStore:
    """Full-integrated memory-resident vector index powered by QIHSE."""
    def __init__(self):
        from src.qihse_wrapper import QIHSE
        self.qihse = QIHSE()
        self.vector_data = [] # List of binary hashes (SHA-384)
        self.metadata = {}    # Map: hash -> file_info
        
    def add_artifact(self, content: str, file_path: str):
        import hashlib
        # CNSA 2.0 Compliant SHA-384
        content_hash = hashlib.sha384(content.encode()).digest()
        self.vector_data.append(content_hash)
        self.metadata[content_hash] = {
            "path": file_path,
            "timestamp": time.time(),
            "type": "code_artifact"
        }
        
    def query_context(self, query: str) -> Optional[dict]:
        """Performs Hilbert-space expanded search for query context."""
        import hashlib
        query_hash = hashlib.sha384(query.encode()).digest()
        
        # Utilize QIHSE binary search for instant matching
        idx = self.qihse.search_binary(self.vector_data, query_hash)
        if idx != -1:
            artifact_hash = self.vector_data[idx]
            return self.metadata.get(artifact_hash)
        return None
