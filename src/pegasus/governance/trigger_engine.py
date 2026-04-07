import re
import os
from pathlib import Path
from typing import Dict, List

class ProactiveTriggerEngine:
    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir
        self.triggers: Dict[str, List[str]] = {}
        self._load_triggers()

    def _load_triggers(self):
        """Scans agent .md files for proactive_triggers patterns."""
        for md_file in self.agents_dir.rglob("*.md"):
            agent_name = md_file.stem.upper()
            try:
                with open(md_file, "r") as f:
                    content = f.read()
                    # Find the patterns block
                    match = re.search(r"proactive_triggers:.*?patterns:(.*?)(?:context_triggers|---|\n\n)", content, re.DOTALL)
                    if match:
                        patterns_block = match.group(1)
                        patterns = re.findall(r'- "(.*?)"', patterns_block)
                        if patterns:
                            self.triggers[agent_name] = patterns
            except: continue

    def analyze_intent(self, text: str) -> List[str]:
        """Matches text against agent patterns to recommend proactive agents."""
        matches = []
        for agent, patterns in self.triggers.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    matches.append(agent)
                    break
        return matches
