import logging
import random
import time
from src.pegasus.subagent_manager import SubAgentManager

class SwarmLoadTester:
    def __init__(self, manager: SubAgentManager):
        self.manager = manager
        self.logger = logging.getLogger("LoadTester")

    def run_stress_test(self, agent_count=10):
        self.logger.info(f"Initiating multi-key superposition test with {agent_count} agents.")
        for i in range(agent_count):
            self.manager.spawn_agent("RESEARCHER", f"Stress test chunk {i}")
            time.sleep(0.1)
