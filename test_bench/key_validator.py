import json
import time
import requests
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KeyValidator")

class KeyValidator:
    def __init__(self, key_file: Path):
        self.key_file = key_file
        
    def validate_all(self):
        with open(self.key_file) as f:
            data = json.load(f)
        
        valid_keys = []
        for entry in data.get("keys", []):
            key = entry["key"]
            logger.info(f"Probing: {key[:15]}...")
            try:
                # Minimal probe via proxy
                resp = requests.post("http://127.0.0.1:9999/v1/chat/completions", 
                                     json={"model": "claude-3-5-sonnet", "messages": [{"role": "user", "content": "hi"}]},
                                     headers={"Authorization": f"Bearer {key}"}, timeout=5)
                if resp.status_code == 200:
                    entry["status"] = "active"
                    valid_keys.append(entry)
                else:
                    entry["status"] = "exhausted"
            except:
                entry["status"] = "exhausted"
        
        with open(self.key_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Validation complete. {len(valid_keys)} active.")

if __name__ == "__main__":
    validator = KeyValidator(Path("config/claude_keys.json"))
    validator.validate_all()
