import json
import requests
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("KeyTester")

def test_keys():
    # Use the full unique list
    key_file = Path("unique_claude_keys.txt")
    if not key_file.exists():
        logger.error("Claude keys file not found.")
        return

    # Extract keys
    keys = []
    with open(key_file, "r") as f:
        for line in f:
            if "sk-ant-api03-" in line:
                key = line.split("sk-ant-api03-")[1].strip()
                keys.append("sk-ant-api03-" + key)
    
    total = len(keys)
    active = 0
    valid_keys = []
    
    logger.info(f"Testing {total} Claude keys (Deep Audit)...")
    
    for i, key in enumerate(keys):
        try:
            resp = requests.get(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                timeout=5
            )
            if resp.status_code == 200:
                active += 1
                valid_keys.append({"key": key, "status": "active", "has_veo_files": False})
                logger.info(f"[{i+1}/{total}] Key OK: {key[:12]}...")
            else:
                logger.warning(f"[{i+1}/{total}] Key FAILED ({resp.status_code}): {key[:12]}...")
        except Exception as e:
            logger.error(f"[{i+1}/{total}] Key ERROR: {e}")

    # Save to config
    with open("config/claude_keys.json", "w") as f:
        json.dump({"keys": valid_keys}, f, indent=2)
    
    logger.info(f"--- Deep Audit Finished: {active}/{total} keys are valid. ---")

if __name__ == "__main__":
    test_keys()
