import logging
from typing import Dict, Set
from src.pegasus.gsl_manager import GlobalStateLedger

class ResourceLockManager:
    """Arbitrates file access between agents using the GSL."""
    def __init__(self, gsl: GlobalStateLedger):
        self.gsl = gsl
        self.locks: Set[str] = set()
        self.logger = logging.getLogger("LockManager")

    def acquire_lock(self, agent_id: str, resource: str) -> bool:
        if resource in self.locks:
            return False
        self.locks.add(resource)
        self.logger.info(f"LOCK_ACQUIRED: {agent_id} -> {resource}")
        return True

    def release_lock(self, agent_id: str, resource: str):
        if resource in self.locks:
            self.locks.remove(resource)
            self.logger.info(f"LOCK_RELEASED: {agent_id} -> {resource}")
