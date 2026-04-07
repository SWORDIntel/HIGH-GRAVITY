import os
from src.pegasus.index.vector_store import PegasusVectorStore

class CodebaseIndexer:
    """Recursively indexes the project into the Vector Store."""
    def __init__(self, vector_store: PegasusVectorStore):
        self.vector_store = vector_store

    def index_project(self, root_dir: str):
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(('.py', '.c', '.h', '.md', '.sh')):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                            self.vector_store.add_file(path, content)
                    except: continue
