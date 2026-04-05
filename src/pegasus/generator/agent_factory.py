import os
import re
from pathlib import Path

class AgentFactory:
    def __init__(self, agent_dir: Path):
        self.agent_dir = agent_dir
        self.registry = {}
        self._scan()

    def _scan(self):
        for md_file in self.agent_dir.rglob("*.md"):
            name = md_file.stem
            self.registry[name.upper()] = str(md_file)
            
    def get_agent_spec(self, name: str):
        return self.registry.get(name.upper())

    def list_available(self):
        return sorted(self.registry.keys())
