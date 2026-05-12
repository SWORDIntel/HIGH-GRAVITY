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
        path = self.registry.get(name.upper())
        if not path:
            return None
        return {
            "name": name.upper(),
            "path": path,
            "capabilities": self._extract_capabilities(Path(path)),
        }

    def _extract_capabilities(self, path: Path):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        capabilities = []
        for field in ("tools", "proactive_triggers", "parallel_capabilities"):
            match = re.search(rf"(?ms)^  {field}:\n(?P<body>.*?)(?=^  [a-zA-Z_]+:|\n---|\Z)", text)
            if not match:
                continue
            for item in re.findall(r"(?m)^  -\s+(.+)$", match.group("body")):
                value = item.split("#", 1)[0].strip()
                if value:
                    capabilities.append(value)
        return capabilities

    def list_available(self):
        return sorted(self.registry.keys())
