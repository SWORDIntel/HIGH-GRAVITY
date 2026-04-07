import subprocess
import uuid
import logging
import threading
import time
import psutil
from pathlib import Path
from src.pegasus.jit_engine.compiler import JITCompiler
from src.pegasus.gsl_manager import GlobalStateLedger
from src.pegasus.memory_sync.superposition import MemorySuperposition
from src.pegasus.generator.agent_factory import AgentFactory
from src.pegasus.governance.delegation import DelegationEngine
from src.pegasus.governance.veto_engine import VetoEngine
from src.pegasus.governance.locks.lock_manager import ResourceLockManager
from src.pegasus.scheduler.hw_aware import HardwareScheduler
from src.pegasus.network.rotator import NetworkRotator
from src.pegasus.index.vector_store import PegasusVectorStore
from src.pegasus.index.indexer import CodebaseIndexer
from lib.protocols.ufp_bridge import UFPBridge

logger = logging.getLogger("Pegasus-Swarm")

class SubAgentManager:
    def __init__(self):
        self.active_agents: Dict[str, subprocess.Popen] = {}
        self.jit = JITCompiler()
        self.gsl = GlobalStateLedger()
        self.superposition = MemorySuperposition()
        self.factory = AgentFactory(Path("src/pegasus/agents"))
        self.governance = DelegationEngine()
        self.veto = VetoEngine(self.gsl)
        self.locks = ResourceLockManager(self.gsl)
        self.scheduler = HardwareScheduler()
        self.network = NetworkRotator(Path("src/pegasus/network"))
        self.bridge = UFPBridge()
        
        # Initialize Vector Indexer
        self.vector_store = PegasusVectorStore()
        self.indexer = CodebaseIndexer(self.vector_store)
        self.indexer.index_project(".")
        
        # Start Proactive Auto-Tasker
        threading.Thread(target=self._auto_tasker_loop, daemon=True).start()
        logger.info("PEGASUS_INDEXER: Codebase indexed. Auto-Tasker Active.")

    def _auto_tasker_loop(self):
        """Periodically scans for idle agents and assigns background maintenance tasks."""
        while True:
            time.sleep(30) # Check every 30 seconds
            for aid, proc in list(self.active_agents.items()):
                if proc.poll() is None: # Still running
                    try:
                        p = psutil.Process(proc.pid)
                        if p.cpu_percent(interval=1.0) < 1.0: # Agent is idle
                            logger.info(f"PROACTIVE_SCHEDULER: Agent {aid} is idle. Assigning maintenance task.")
                            # Assign a maintenance task based on role
                            role = aid.split("-")[0]
                            task = "AUDIT_LOCAL_RECON" if "SECURITY" in role else "MAP_INTERNAL_FLOW"
                            self.bridge.send_task(role, task)
                    except: continue

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
        cmd = ["bash", "bin/launch_claude_interface.sh", "-p", prompt, "--vpn", vpn_config]
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
