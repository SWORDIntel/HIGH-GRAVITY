"""Orchestration Module - Multi-agent coordination and registry"""

from .agent_registry import EnhancedAgentRegistry

# Optional import - TandemOrchestrator has additional dependencies
try:
    from .tandem_orchestration_base import TandemOrchestrator
    _tandem_available = True
except ImportError:
    TandemOrchestrator = None
    _tandem_available = False

# Singleton instance
_registry_instance = None


def get_agent_registry() -> EnhancedAgentRegistry:
    """Get or create the global agent registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = EnhancedAgentRegistry()
    return _registry_instance


__all__ = [
    "EnhancedAgentRegistry",
    "get_agent_registry",
]

if _tandem_available:
    __all__.append("TandemOrchestrator")
