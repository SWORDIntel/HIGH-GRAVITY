"""Claude Agent Framework - Organized Package Structure"""

__version__ = "8.0.0"

from .core import *

# Import organization modules
from .orchestration import *
from .utils import *

# Make implementations accessible (import LAST to override any conflicts)
from .implementations import get_agent, list_agents, get_agent_registry, register_agent

__all__ = ["get_agent", "list_agents", "get_agent_registry", "register_agent"]
