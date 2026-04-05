import subprocess
import uuid
import logging
from typing import Dict, List
from pathlib import Path
from tools.integration.pegasus.jit_engine.compiler import JITCompiler
from tools.integration.pegasus.gsl_manager import GlobalStateLedger
from tools.integration.pegasus.memory_sync.superposition import MemorySuperposition
from tools.integration.pegasus.generator.agent_factory import AgentFactory
from tools.integration.pegasus.governance.delegation import DelegationEngine
from tools.integration.pegasus.governance.veto_engine import VetoEngine
from tools.integration.pegasus.governance.locks.lock_manager import ResourceLockManager
from tools.integration.pegasus.scheduler.hw_aware import HardwareScheduler
from tools.integration.pegasus.network.rotator import NetworkRotator
from tools.integration.pegasus.index.vector_store import PegasusVectorStore
from tools.integration.pegasus.index.indexer import CodebaseIndexer

logger = logging.getLogger("Pegasus-Swarm")

class SubAgentManager:
    def __init__(self):
        self.active_agents: Dict[str, subprocess.Popen] = {}
        self.jit = JITCompiler()
        self.gsl = GlobalStateLedger()
        self.superposition = MemorySuperposition()
        self.factory = AgentFactory(Path("tools/integration/pegasus/agents"))
        self.governance = DelegationEngine()
        self.veto = VetoEngine(self.gsl)
        self.locks = ResourceLockManager(self.gsl)
        self.scheduler = HardwareScheduler()
        self.network = NetworkRotator(Path("tools/integration/pegasus/network"))
        # Initialize Vector Indexer
        self.vector_store = PegasusVectorStore()
        self.indexer = CodebaseIndexer(self.vector_store)
        self.indexer.index_project(".")
        logger.info("PEGASUS_INDEXER: Codebase indexed into Hilbert Space.")

    def spawn_agent(self, role: str, prompt: str, source: str = "HUMAN") -> str:
        # Check Hardware capability
        backend = self.scheduler.get_optimal_backend()
        logger.info(f"HARDWARE_SCHEDULER: Routing {role} to {backend}")

        # Validate delegation
        if not self.governance.validate_delegation(source, role):
            logger.error(f"DELEGATION_DENIED: {source} cannot spawn {role}")
            return "ACCESS_DENIED"
        
        # Validate agent exists in SWORDSwarm registry
        spec = self.factory.get_agent_spec(role)
        if not spec:
            logger.error(f"AGENT_NOT_FOUND: {role}")
            return "ERROR"
            
        agent_id = f"{role}-{uuid.uuid4().hex[:6]}"
        vpn_config = self.network.get_random_config()
        logger.info(f"SPAWNING_GEODISTRIBUTED_AGENT: {agent_id} via {vpn_config} (Spec: {spec})")

        # Pass VPN config to the launch script
        cmd = ["bash", "tools/integration/launch_claude_interface.sh", "-p", prompt, "--vpn", vpn_config]
        proc = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        self.active_agents[agent_id] = proc
        self.gsl.post_delta(proc.pid, "STATUS", 1)
        return agent_id

    def checkpoint_swarm(self):
        """Perform global state superposition check."""
        for aid, proc in self.active_agents.items():
            # Dummy state for demo integration
            self.superposition.checkpoint_agent(proc.pid, b"PEGASUS_STATE_DATA")
            logger.info(f"SWARM_SYNC: {aid} checkpointed to RAM Superposition.")

    def terminate_all(self):
        for aid, proc in self.active_agents.items():
            proc.terminate()
        self.active_agents.clear()
        logger.info("SWARM_TERMINATED.")
