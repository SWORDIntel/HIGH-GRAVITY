"""
Internal Language Specialist Agent Implementations
=================================================

This module contains implementations for internal language and data processing
specialists including JSON-INTERNAL, XML-INTERNAL, and other data format handlers.

All agents in this module provide:
- Hardware-accelerated processing (NPU when available)
- Comprehensive error handling and recovery
- High-performance parsing and validation
- Intelligent caching and optimization
- Full Claude Code Task tool integration
"""

from .json_internal_impl import JSONInternalPythonExecutor

__all__ = [
    "JSONInternalPythonExecutor",
]
