"""Development Module - AI-powered development agents"""

# Import Codex agent if available
try:
    from .codex_agent_impl import CodexAgent, get_codex_agent, generate, review, refactor
    CODEX_AVAILABLE = True
except ImportError:
    CODEX_AVAILABLE = False
    CodexAgent = None

__all__ = []

if CODEX_AVAILABLE:
    __all__.extend(["CodexAgent", "get_codex_agent", "generate", "review", "refactor"])
