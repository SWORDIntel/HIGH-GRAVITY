#!/usr/bin/env python3
"""
NPU ORCHESTRATOR LAUNCHER
Launches NPU-accelerated orchestrator with proper configuration
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from agents.src.python.npu_accelerated_orchestrator import NPUMode
    from agents.src.python.npu_orchestrator_bridge import NPUOrchestratorBridge
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure NPU orchestrator files are properly installed")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main launcher function"""
    logger.info("Starting NPU Accelerated Orchestrator...")

    # Initialize bridge with adaptive mode
    bridge = NPUOrchestratorBridge(NPUMode.ADAPTIVE)

    if await bridge.initialize():
        logger.info("NPU Orchestrator initialized successfully!")

        # Print status
        status = bridge.get_status()
        print(f"NPU Available: {status.get('npu_available', False)}")
        print(f"Agents Available: {len(bridge.get_agent_list())}")

        # Keep running (in production, this would be a service)
        try:
            while True:
                await asyncio.sleep(60)
                metrics = bridge.get_metrics()
                logger.info(f"Status: {metrics}")
        except KeyboardInterrupt:
            logger.info("Shutting down...")
    else:
        logger.error("Failed to initialize NPU Orchestrator")
        return False

    return True


if __name__ == "__main__":
    asyncio.run(main())
