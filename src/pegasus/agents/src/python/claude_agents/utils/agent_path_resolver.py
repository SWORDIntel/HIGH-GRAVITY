"""
Dynamic Path Discovery Helper for Claude Agents (Python)
========================================================

This module provides consistent path resolution across the entire agent ecosystem
for Python scripts and modules.
"""

import os
import sys
from pathlib import Path


class AgentPathResolver:
    """Provides dynamic path resolution for agent system"""

    def __init__(self):
        self._project_root = None
        self._agents_root = None
        self._detect_paths()

    def _detect_paths(self):
        """Detect project and agent root paths dynamically"""
        # Check environment variables first
        if os.environ.get("CLAUDE_PROJECT_ROOT"):
            self._project_root = Path(os.environ["CLAUDE_PROJECT_ROOT"])
            self._agents_root = Path(
                os.environ.get("CLAUDE_AGENTS_ROOT", self._project_root / "agents")
            )
            return

        # Try to detect based on current file location
        current_file = Path(__file__).resolve()
        current_dir = current_file.parent

        # Look for characteristic files to identify structure
        for parent in [current_dir] + list(current_dir.parents):
            # Check if this is agents directory
            if (parent / "TEMPLATE.md").exists() and (parent / "src").exists():
                self._agents_root = parent
                self._project_root = parent.parent
                break
            # Check if this is project root
            elif (parent / "CLAUDE.md").exists() and (parent / "agents").exists():
                self._project_root = parent
                self._agents_root = parent / "agents"
                break

        # Fallback
        if not self._project_root:
            self._project_root = current_dir.parent
            self._agents_root = current_dir

        # Set environment variables for other processes
        os.environ["CLAUDE_PROJECT_ROOT"] = str(self._project_root)
        os.environ["CLAUDE_AGENTS_ROOT"] = str(self._agents_root)

    @property
    def project_root(self):
        """Get project root path"""
        return self._project_root

    @property
    def agents_root(self):
        """Get agents root path"""
        return self._agents_root

    def resolve_agent_path(self, relative_path):
        """Resolve path relative to agents directory"""
        return self._agents_root / relative_path

    def resolve_project_path(self, relative_path):
        """Resolve path relative to project root"""
        return self._project_root / relative_path

    def add_to_python_path(self):
        """Add project root to Python path if not already present"""
        project_str = str(self._project_root)
        if project_str not in sys.path:
            sys.path.insert(0, project_str)

    def get_config_path(self, config_name):
        """Get path to configuration file"""
        return self.resolve_agent_path(f"config/{config_name}")

    def get_binary_path(self, binary_name):
        """Get path to binary file"""
        return self.resolve_agent_path(f"binary-communications-system/{binary_name}")

    def get_src_path(self, lang, filename):
        """Get path to source file"""
        return self.resolve_agent_path(f"src/{lang}/{filename}")


# Global instance for easy importing
path_resolver = AgentPathResolver()


# Convenience functions
def get_project_root():
    return path_resolver.project_root


def get_agents_root():
    return path_resolver.agents_root


def resolve_agent_path(relative_path):
    return path_resolver.resolve_agent_path(relative_path)


def resolve_project_path(relative_path):
    return path_resolver.resolve_project_path(relative_path)


def add_to_python_path():
    path_resolver.add_to_python_path()


# New helpers for reorganized modules
def get_shadowgit_root() -> Path:
    """
    Get shadowgit module root directory.
    After reorganization, shadowgit is at: hooks/shadowgit/
    """
    project_root = get_project_root()
    shadowgit_root = project_root / "hooks" / "shadowgit"

    # Fallback to old location if new doesn't exist yet
    if not shadowgit_root.exists():
        shadowgit_root = project_root / "shadowgit"

    # Add Python module to sys.path
    shadowgit_python = shadowgit_root / "python"
    if shadowgit_python.exists():
        if str(shadowgit_python) not in sys.path:
            sys.path.insert(0, str(shadowgit_python))

    return shadowgit_root


def get_crypto_pow_root() -> Path:
    """
    Get crypto POW module root directory.
    After reorganization, crypto POW is at: hooks/crypto-pow/
    """
    project_root = get_project_root()
    crypto_pow_root = project_root / "hooks" / "crypto-pow"

    # Fallback to old location if new doesn't exist yet
    if not crypto_pow_root.exists():
        crypto_pow_root = project_root / "crypto"

    # Add to sys.path if exists
    if crypto_pow_root.exists():
        if str(crypto_pow_root) not in sys.path:
            sys.path.insert(0, str(crypto_pow_root))

    return crypto_pow_root


def get_shadowgit_paths() -> dict:
    """
    DEPRECATED: Legacy function for compatibility.
    Use get_shadowgit_root() instead.

    Returns dict with shadowgit path components.
    """
    import warnings

    warnings.warn(
        "get_shadowgit_paths() is deprecated. Use get_shadowgit_root() instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    shadowgit_root = get_shadowgit_root()
    return {
        "root": shadowgit_root,
        "python": shadowgit_root / "python",
        "src": shadowgit_root / "src",
        "bin": shadowgit_root / "bin",
        "analysis": shadowgit_root / "analysis",
        "deployment": shadowgit_root / "deployment",
    }


# Auto-add to Python path when imported
add_to_python_path()
