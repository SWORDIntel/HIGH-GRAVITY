import subprocess
import uuid
import logging
import threading
import time
import psutil
import os
import re
from pathlib import Path
from typing import Dict
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
from src.pegasus.orchestrator import PegasusOrchestrator
from lib.protocols.ufp_bridge import UFPBridge

logger = logging.getLogger("Pegasus-Swarm")
REPO_ROOT = Path(__file__).resolve().parents[2]

class SubAgentManager:
    def __init__(self):
        self.active_agents: Dict[str, subprocess.Popen] = {}
        self.agent_started_at: Dict[str, float] = {}
        self.max_active_agents = int(os.environ.get("HG_PEGASUS_MAX_ACTIVE_AGENTS", "3"))
        self.agent_max_seconds = int(os.environ.get("HG_PEGASUS_AGENT_MAX_SECONDS", "900"))
        self.jit = JITCompiler()
        self.gsl = GlobalStateLedger()
        self.superposition = MemorySuperposition()
        self.factory = AgentFactory(Path("src/pegasus/agents"))
        self.governance = DelegationEngine()
        self.veto = VetoEngine(self.gsl)
        self.locks = ResourceLockManager(self.gsl)
        self.scheduler = HardwareScheduler()
        self.network = NetworkRotator(Path("src/pegasus/network"))
        self.orchestrator = PegasusOrchestrator()
        self.bridge = UFPBridge()
        
        # Initialize Vector Indexer (async to avoid blocking)
        self.vector_store = PegasusVectorStore()
        self.indexer = CodebaseIndexer(self.vector_store)
        threading.Thread(target=self._index_project_async, daemon=True).start()
        
        # Start Proactive Auto-Tasker
        threading.Thread(target=self._auto_tasker_loop, daemon=True).start()
        logger.info("PEGASUS: Orchestrator active. Indexing in background.")

    def _index_project_async(self):
        """Index project in background"""
        try:
            logger.info("PEGASUS_INDEXER: Starting background indexing...")
            self.indexer.index_project(".")
            logger.info("PEGASUS_INDEXER: Indexing complete.")
        except Exception as e:
            logger.warning(f"PEGASUS_INDEXER: Indexing failed: {e}")

    def _auto_tasker_loop(self):
        """Periodically scans for idle agents and assigns background maintenance tasks."""
        while True:
            time.sleep(30) # Check every 30 seconds
            for aid, proc in list(self.active_agents.items()):
                started = self.agent_started_at.get(aid, time.time())
                if proc.poll() is not None:
                    self.active_agents.pop(aid, None)
                    self.agent_started_at.pop(aid, None)
                    try:
                        proc._hg_log_fh.close()
                    except Exception:
                        pass
                    logger.info(f"AGENT_REAPED: {aid} rc={proc.returncode}")
                    continue
                if self.agent_max_seconds > 0 and time.time() - started > self.agent_max_seconds:
                    logger.warning(f"AGENT_TIMEOUT: terminating {aid} after {self.agent_max_seconds}s")
                    proc.terminate()
                    self.active_agents.pop(aid, None)
                    self.agent_started_at.pop(aid, None)
                    try:
                        proc._hg_log_fh.close()
                    except Exception:
                        pass
                    continue
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

    def _external_swarm_worker_count(self) -> int:
        try:
            proc = subprocess.run(
                ["ps", "-eo", "args"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=1.0,
            )
        except Exception:
            return 0
        if proc.returncode != 0:
            return 0
        request_ids = set()
        fallback_count = 0
        for line in proc.stdout.splitlines():
            if "gemini --prompt [HG_SWARM_TRIGGER]" not in line:
                continue
            match = re.search(r"\brequest_id=([A-Za-z0-9_-]+)", line)
            if match:
                request_ids.add(match.group(1))
            elif line.startswith("node ") or line.startswith("/usr/bin/node "):
                fallback_count += 1
        return len(request_ids) if request_ids else fallback_count

    def spawn_agent(self, role: str, prompt: str, source: str = "HUMAN") -> str:
        for aid, proc in list(self.active_agents.items()):
            if proc.poll() is not None:
                self.active_agents.pop(aid, None)
                self.agent_started_at.pop(aid, None)
                try:
                    proc._hg_log_fh.close()
                except Exception:
                    pass
        if self.max_active_agents > 0 and len(self.active_agents) >= self.max_active_agents:
            logger.warning(
                f"AGENT_SPAWN_BUSY: active={len(self.active_agents)} max={self.max_active_agents} role={role}"
            )
            return "BUSY"
        external_active = self._external_swarm_worker_count()
        if self.max_active_agents > 0 and external_active >= self.max_active_agents:
            logger.warning(
                f"AGENT_SPAWN_BUSY_GLOBAL: active={external_active} max={self.max_active_agents} role={role}"
            )
            return "BUSY"

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
        
        # Register with orchestrator and get random API key
        agent_config = self.orchestrator.register_agent(
            agent_id=agent_id,
            role=role,
            capabilities=spec.get("capabilities", [])
        )
        api_key = agent_config["api_key"]
        
        vpn_config = self.network.get_random_config()
        logger.info(f"SPAWNING_GEODISTRIBUTED_AGENT: {agent_id} via {vpn_config} with key {api_key[:20]}...")

        launcher = REPO_ROOT / "scripts" / "internal" / "launch_claude_interface.sh"
        if not launcher.exists():
            logger.error(f"AGENT_LAUNCHER_MISSING: {launcher}")
            return "ERROR"

        # Pass proxy-bound execution through the local launcher. VPN/API key details
        # are carried in env so the Claude CLI argument surface stays stable.
        env = {
            **os.environ,
            "GEMINI_API_KEY": api_key,
            "HG_PEGASUS_AGENT_ID": agent_id,
            "HG_PEGASUS_AGENT_ROLE": role,
            "HG_PEGASUS_VPN_CONFIG": vpn_config,
        }
        cmd = ["bash", str(launcher), "-p", prompt]
        log_dir = REPO_ROOT / "logs" / "pegasus_agents"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_fh = open(log_dir / f"{agent_id}.log", "ab", buffering=0)
        proc = subprocess.Popen(
            cmd, 
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        time.sleep(0.2)
        if proc.poll() is not None:
            try:
                log_fh.close()
            except Exception:
                pass
            log_path = log_dir / f"{agent_id}.log"
            try:
                stderr = log_path.read_text(encoding="utf-8", errors="replace").strip()
            except Exception:
                stderr = "unavailable"
            logger.error(f"AGENT_LAUNCH_FAILED: {agent_id} rc={proc.returncode} log={log_path} stderr={stderr[:300]}")
            return "ERROR"
        proc._hg_log_fh = log_fh
        self.active_agents[agent_id] = proc
        self.agent_started_at[agent_id] = time.time()
        self.gsl.post_delta(proc.pid, "STATUS", 1)
        logger.info(f"ORCHESTRATOR: Agent {agent_id} spawned under orchestrator command")
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

    def initiate_code_audit(self, target_path: str = ".") -> str:
        """Initiate end-to-end code audit"""
        audit_id = self.orchestrator.initiate_e2e_code_audit(target_path)
        self.orchestrator.auto_distribute_tasks()
        logger.info(f"E2E_AUDIT: Initiated {audit_id} and distributed tasks")
        return audit_id

    def get_audit_status(self, audit_id: str) -> dict:
        """Get audit status"""
        return self.orchestrator.get_audit_status(audit_id) or {}

    def get_orchestrator_status(self) -> dict:
        """Get orchestrator swarm status"""
        return self.orchestrator.get_swarm_status()
