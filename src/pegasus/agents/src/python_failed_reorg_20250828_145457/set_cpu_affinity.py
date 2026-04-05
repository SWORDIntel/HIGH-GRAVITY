#!/usr/bin/env python3
import os
from pathlib import Path

import psutil
import yaml


def set_process_affinity():
    """Set CPU affinity based on Meteor Lake configuration"""
    config_file = Path(__file__).parent / os.path.join(
        os.environ.get("CLAUDE_AGENTS_ROOT", "."), "config", "$1"
    )

    if not config_file.exists():
        print("Configuration file not found")
        return

    with open(config_file) as f:
        config = yaml.safe_load(f)

    # Get current process
    process = psutil.Process()

    # Set affinity to P-cores for main orchestrator process
    p_cores = config["hardware"]["cores"]["p_cores"]["ids"]
    try:
        process.cpu_affinity(p_cores)
        print(f"Set CPU affinity to P-cores: {p_cores}")
    except Exception as e:
        print(f"Failed to set CPU affinity: {e}")


if __name__ == "__main__":
    set_process_affinity()
