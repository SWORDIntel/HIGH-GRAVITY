#!/usr/bin/env python3
"""
Pegasus Orchestrator - Central Command & Control
Manages all agents with random API key assignment and E2E code auditing
"""
import random
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("Pegasus-Orchestrator")

class PegasusOrchestrator:
    """
    Central orchestrator for all Pegasus agents.
    - Assigns random API keys to agents
    - Manages agent lifecycle
    - Coordinates E2E code audits
    - Distributes tasks across swarm
    """
    
    def __init__(self, keys_file: Optional[Path] = None):
        self.repo_root = Path(__file__).resolve().parent.parent.parent
        self.keys_file = keys_file or self.repo_root / "config" / "gemini_keys.json"
        self.api_keys = self._load_api_keys()
        self.agent_registry: Dict[str, Dict] = {}
        self.task_queue: List[Dict] = []
        self.audit_results: List[Dict] = []
        
        logger.info(f"ORCHESTRATOR_INIT: Loaded {len(self.api_keys)} API keys")
    
    def _load_api_keys(self) -> List[str]:
        """Load Gemini API keys from config"""
        try:
            with open(self.keys_file, 'r') as f:
                data = json.load(f)
                keys = [k["key"] for k in data.get("keys", []) if k.get("status") == "active"]
                return keys
        except Exception as e:
            logger.warning(f"Failed to load keys: {e}")
            return []
    
    def assign_random_key(self, agent_id: str) -> str:
        """Assign a random API key to an agent"""
        if not self.api_keys:
            logger.error("No API keys available!")
            return ""
        
        key = random.choice(self.api_keys)
        logger.info(f"ORCHESTRATOR: Assigned key {key[:20]}... to {agent_id}")
        return key
    
    def register_agent(self, agent_id: str, role: str, capabilities: List[str]) -> Dict:
        """Register a new agent under orchestrator command"""
        api_key = self.assign_random_key(agent_id)
        
        agent_config = {
            "agent_id": agent_id,
            "role": role,
            "capabilities": capabilities,
            "api_key": api_key,
            "status": "active",
            "tasks_completed": 0,
            "registered_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat()
        }
        
        self.agent_registry[agent_id] = agent_config
        logger.info(f"ORCHESTRATOR: Registered {agent_id} with role {role}")
        return agent_config
    
    def get_agent_config(self, agent_id: str) -> Optional[Dict]:
        """Get agent configuration including API key"""
        return self.agent_registry.get(agent_id)
    
    def rotate_agent_key(self, agent_id: str) -> str:
        """Rotate API key for an agent"""
        if agent_id not in self.agent_registry:
            logger.error(f"Agent {agent_id} not found")
            return ""
        
        new_key = self.assign_random_key(agent_id)
        self.agent_registry[agent_id]["api_key"] = new_key
        logger.info(f"ORCHESTRATOR: Rotated key for {agent_id}")
        return new_key
    
    def dispatch_task(self, task_type: str, target: str, priority: int = 5) -> str:
        """Dispatch a task to the swarm"""
        task_id = f"TASK-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9998)}"
        
        task = {
            "task_id": task_id,
            "type": task_type,
            "target": target,
            "priority": priority,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "assigned_to": None
        }
        
        self.task_queue.append(task)
        logger.info(f"ORCHESTRATOR: Dispatched {task_type} task {task_id}")
        return task_id
    
    def assign_task_to_agent(self, task_id: str, agent_id: str) -> bool:
        """Assign a queued task to a specific agent"""
        for task in self.task_queue:
            if task["task_id"] == task_id:
                task["assigned_to"] = agent_id
                task["status"] = "assigned"
                logger.info(f"ORCHESTRATOR: Assigned {task_id} to {agent_id}")
                return True
        return False
    
    def initiate_e2e_code_audit(self, target_path: str = ".") -> str:
        """
        Initiate end-to-end code audit across entire codebase
        Distributes audit tasks to all available agents
        """
        audit_id = f"AUDIT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        audit_tasks = [
            ("SECURITY_SCAN", "Scan for security vulnerabilities"),
            ("CODE_QUALITY", "Analyze code quality and patterns"),
            ("DEPENDENCY_CHECK", "Check dependencies for CVEs"),
            ("SECRET_DETECTION", "Detect hardcoded secrets"),
            ("API_AUDIT", "Audit API key usage"),
            ("PERMISSION_CHECK", "Check file permissions"),
            ("IMPORT_ANALYSIS", "Analyze import chains"),
            ("DEAD_CODE", "Detect dead/unused code"),
        ]
        
        task_ids = []
        for task_type, description in audit_tasks:
            task_id = self.dispatch_task(task_type, target_path, priority=10)
            task_ids.append(task_id)
        
        audit_record = {
            "audit_id": audit_id,
            "target": target_path,
            "task_ids": task_ids,
            "started_at": datetime.now().isoformat(),
            "status": "in_progress",
            "results": []
        }
        
        self.audit_results.append(audit_record)
        logger.info(f"ORCHESTRATOR: Initiated E2E audit {audit_id} with {len(task_ids)} tasks")
        return audit_id
    
    def get_audit_status(self, audit_id: str) -> Optional[Dict]:
        """Get status of an ongoing audit"""
        for audit in self.audit_results:
            if audit["audit_id"] == audit_id:
                # Count completed tasks
                completed = sum(1 for task in self.task_queue 
                              if task["task_id"] in audit["task_ids"] 
                              and task["status"] == "completed")
                total = len(audit["task_ids"])
                
                audit["progress"] = f"{completed}/{total}"
                audit["completion_pct"] = (completed / total * 100) if total > 0 else 0
                return audit
        return None
    
    def get_swarm_status(self) -> Dict:
        """Get overall swarm status"""
        active_agents = sum(1 for a in self.agent_registry.values() if a["status"] == "active")
        queued_tasks = sum(1 for t in self.task_queue if t["status"] == "queued")
        assigned_tasks = sum(1 for t in self.task_queue if t["status"] == "assigned")
        completed_tasks = sum(1 for t in self.task_queue if t["status"] == "completed")
        
        return {
            "total_agents": len(self.agent_registry),
            "active_agents": active_agents,
            "available_keys": len(self.api_keys),
            "queued_tasks": queued_tasks,
            "assigned_tasks": assigned_tasks,
            "completed_tasks": completed_tasks,
            "active_audits": sum(1 for a in self.audit_results if a["status"] == "in_progress")
        }
    
    def auto_distribute_tasks(self):
        """Automatically distribute queued tasks to available agents"""
        available_agents = [aid for aid, cfg in self.agent_registry.items() 
                          if cfg["status"] == "active"]
        
        if not available_agents:
            logger.warning("No available agents for task distribution")
            return
        
        queued = [t for t in self.task_queue if t["status"] == "queued"]
        
        for task in queued:
            # Match task to agent based on role/capabilities
            agent_id = random.choice(available_agents)
            self.assign_task_to_agent(task["task_id"], agent_id)
        
        logger.info(f"ORCHESTRATOR: Auto-distributed {len(queued)} tasks")
    
    def export_agent_configs(self, output_file: Path):
        """Export all agent configurations to file"""
        export_data = {
            "orchestrator_version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "total_agents": len(self.agent_registry),
            "agents": list(self.agent_registry.values())
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"ORCHESTRATOR: Exported {len(self.agent_registry)} agent configs to {output_file}")
    
    def generate_audit_report(self, audit_id: str) -> str:
        """Generate comprehensive audit report"""
        audit = self.get_audit_status(audit_id)
        if not audit:
            return "Audit not found"
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    PEGASUS E2E CODE AUDIT REPORT                         ║
╚══════════════════════════════════════════════════════════════════════════╝

Audit ID:       {audit['audit_id']}
Target:         {audit['target']}
Started:        {audit['started_at']}
Status:         {audit['status']}
Progress:       {audit.get('progress', 'N/A')} ({audit.get('completion_pct', 0):.1f}%)

Task Breakdown:
"""
        for task_id in audit["task_ids"]:
            task = next((t for t in self.task_queue if t["task_id"] == task_id), None)
            if task:
                report += f"  [{task['status'].upper():10}] {task['type']:20} - {task_id}\n"
        
        report += f"\nTotal Tasks: {len(audit['task_ids'])}\n"
        report += "=" * 78 + "\n"
        
        return report


if __name__ == "__main__":
    # Test orchestrator
    logging.basicConfig(level=logging.INFO)
    
    orch = PegasusOrchestrator()
    
    # Register test agents
    orch.register_agent("SECURITY-001", "SECURITY", ["scan", "audit"])
    orch.register_agent("ANALYST-001", "ANALYST", ["analyze", "report"])
    
    # Initiate audit
    audit_id = orch.initiate_e2e_code_audit(".")
    
    # Auto-distribute tasks
    orch.auto_distribute_tasks()
    
    # Show status
    print(orch.generate_audit_report(audit_id))
    print("\nSwarm Status:", json.dumps(orch.get_swarm_status(), indent=2))
