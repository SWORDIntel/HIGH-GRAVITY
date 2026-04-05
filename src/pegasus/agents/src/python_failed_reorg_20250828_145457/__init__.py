"""
Claude Agent Framework - Python Implementation Package
Version 8.0.0

This package provides a comprehensive agent system with:
- 70+ specialized agent implementations
- Tandem orchestration system
- Learning system integration
- Binary bridge connectivity
- Voice input capabilities
"""

__version__ = "8.0.0"
__author__ = "Claude Agent Framework Team"

import importlib
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Type

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add this directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# ============================================================================
# AGENT IMPLEMENTATIONS
# ============================================================================

# Dictionary to store loaded agent modules
_agent_modules: Dict[str, Any] = {}


def _load_agent_implementation(agent_name: str) -> Optional[Any]:
    """Dynamically load an agent implementation module"""
    implementations = [
        f"{agent_name}_impl",
        f"{agent_name}_agent_impl",
        f"{agent_name}",
        f"enhanced_{agent_name}_impl",
        agent_name.replace("-", "_") + "_impl",
    ]

    for impl_name in implementations:
        try:
            module = importlib.import_module(impl_name)
            return module
        except ImportError:
            continue

    return None


def get_agent(agent_name: str) -> Optional[Any]:
    """Get an agent implementation by name"""
    agent_name = agent_name.lower().replace("-", "_")

    # Check cache first
    if agent_name in _agent_modules:
        return _agent_modules[agent_name]

    # Try to load the agent
    module = _load_agent_implementation(agent_name)
    if module:
        _agent_modules[agent_name] = module
        return module

    logger.warning(f"Agent '{agent_name}' not found")
    return None


# Core agent implementations - explicit imports for IDE support
try:
    from . import architect_impl as architect
    from . import constructor_impl as constructor
    from . import debugger_impl as debugger
    from . import deployer_impl as deployer
    from . import director_impl as director
    from . import linter_impl as linter
    from . import monitor_impl as monitor
    from . import optimizer_impl as optimizer
    from . import security_impl as security
    from . import testbed_impl as testbed
except ImportError as e:
    logger.debug(f"Some core agents not available: {e}")

# ============================================================================
# ORCHESTRATION SYSTEMS
# ============================================================================

# Orchestration modules
try:
    from . import (
        agent_registry,
        database_orchestrator,
        learning_orchestrator_bridge,
        production_orchestrator,
        tandem_orchestrator,
    )

    # Main orchestrator classes
    ProductionOrchestrator = (
        production_orchestrator.ProductionOrchestrator
        if hasattr(production_orchestrator, "ProductionOrchestrator")
        else None
    )
    TandemOrchestrator = (
        tandem_orchestrator.TandemOrchestrator
        if hasattr(tandem_orchestrator, "TandemOrchestrator")
        else None
    )
    AgentRegistry = (
        agent_registry.AgentRegistry
        if hasattr(agent_registry, "AgentRegistry")
        else None
    )

except ImportError as e:
    logger.debug(f"Orchestration modules not fully available: {e}")
    ProductionOrchestrator = None
    TandemOrchestrator = None
    AgentRegistry = None

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def list_available_agents() -> list:
    """List all available agent implementations"""
    agents = []

    # Find all *_impl.py files
    impl_files = Path(__file__).parent.glob("*_impl.py")
    for file in impl_files:
        agent_name = file.stem.replace("_impl", "").replace("enhanced_", "")
        agents.append(agent_name)

    # Find all *_agent_impl.py files
    agent_impl_files = Path(__file__).parent.glob("*_agent_impl.py")
    for file in agent_impl_files:
        agent_name = file.stem.replace("_agent_impl", "").replace("enhanced_", "")
        if agent_name not in agents:
            agents.append(agent_name)

    return sorted(agents)


def get_agent_class(agent_name: str, class_suffix: str = "Agent") -> Optional[Type]:
    """Get the main class from an agent module"""
    module = get_agent(agent_name)
    if not module:
        return None

    # Try common class name patterns
    class_names = [
        f"{agent_name.title().replace('_', '')}{class_suffix}",
        f"{agent_name.upper()}{class_suffix}",
        agent_name.title().replace("_", ""),
        "Agent",
        f"{agent_name.title()}Implementation",
    ]

    for class_name in class_names:
        if hasattr(module, class_name):
            return getattr(module, class_name)

    # Return first class found
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and attr_name[0].isupper():
            return attr

    return None


# ============================================================================
# BRIDGES AND INTEGRATIONS
# ============================================================================

try:
    from . import (
        binary_bridge_connector,
        claude_agent_bridge,
        claude_code_integration,
        learning_orchestrator_bridge,
    )

    ClaudeAgentBridge = (
        claude_agent_bridge.ClaudeAgentBridge
        if hasattr(claude_agent_bridge, "ClaudeAgentBridge")
        else None
    )
    BinaryBridge = (
        binary_bridge_connector.BinaryBridgeConnector
        if hasattr(binary_bridge_connector, "BinaryBridgeConnector")
        else None
    )

except ImportError as e:
    logger.debug(f"Bridge modules not fully available: {e}")
    ClaudeAgentBridge = None
    BinaryBridge = None

# ============================================================================
# VOICE SYSTEM
# ============================================================================

try:
    from . import VOICE_INPUT_SYSTEM, VOICE_TOGGLE, voice_system

    VoiceSystem = (
        voice_system.VoiceSystem if hasattr(voice_system, "VoiceSystem") else None
    )

except ImportError as e:
    logger.debug(f"Voice system not available: {e}")
    VoiceSystem = None

# ============================================================================
# UTILITIES
# ============================================================================

try:
    from . import (
        async_io_optimizer,
        intelligent_cache,
        meteor_lake_parallel,
        parallel_orchestration_utils,
    )

    ParallelOrchestrator = (
        parallel_orchestration_utils.ParallelOrchestrator
        if hasattr(parallel_orchestration_utils, "ParallelOrchestrator")
        else None
    )

except ImportError as e:
    logger.debug(f"Utility modules not fully available: {e}")
    ParallelOrchestrator = None

# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Core functions
    "get_agent",
    "get_agent_class",
    "list_available_agents",
    # Orchestration
    "ProductionOrchestrator",
    "TandemOrchestrator",
    "AgentRegistry",
    # Bridges
    "ClaudeAgentBridge",
    "BinaryBridge",
    # Voice
    "VoiceSystem",
    # Utilities
    "ParallelOrchestrator",
]

# ============================================================================
# MODULE INITIALIZATION
# ============================================================================


def initialize():
    """Initialize the Claude Agent Framework"""
    logger.info(f"Claude Agent Framework v{__version__} initializing...")

    # Count available agents
    agents = list_available_agents()
    logger.info(f"Found {len(agents)} agent implementations")

    # Check orchestration
    if ProductionOrchestrator:
        logger.info("Production Orchestrator available")
    if TandemOrchestrator:
        logger.info("Tandem Orchestrator available")

    # Check bridges
    if ClaudeAgentBridge:
        logger.info("Claude Agent Bridge available")
    if BinaryBridge:
        logger.info("Binary Bridge available")

    # Check voice
    if VoiceSystem:
        logger.info("Voice System available")

    logger.info("Initialization complete")

    return True


# Auto-initialize on import if running as main package
if __name__ != "__main__":
    # Don't auto-initialize to avoid side effects
    pass
else:
    initialize()
