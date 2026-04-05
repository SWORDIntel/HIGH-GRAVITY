import json
import requests
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("KeyTester")

def test_keys():
    key_file = Path("config/claude_keys.json")
    if not key_file.exists():
        logger.error("Claude keys file not found.")
        return

    with open(key_file, "r") as f:
        data = json.load(f)
    
    total = len(data["keys"])
    active = 0
    
    logger.info(f"Testing {total} Claude keys...")
    
    for i, entry in enumerate(data["keys"]):
        key = entry["key"]
        try:
            # Probe via Anthropic API directly to verify key integrity
            resp = requests.get(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                timeout=5
            )
            if resp.status_code == 200:
                entry["status"] = "active"
                active += 1
                logger.info(f"[{i+1}/{total}] Key OK: {key[:12]}...")
            else:
                entry["status"] = "exhausted"
                logger.warning(f"[{i+1}/{total}] Key FAILED ({resp.status_code}): {key[:12]}...")
        except Exception as e:
            entry["status"] = "exhausted"
            logger.error(f"[{i+1}/{total}] Key ERROR: {e}")

    with open(key_file, "w") as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"--- Test Finished: {active}/{total} keys are valid. ---")

if __name__ == "__main__":
    test_keys()
