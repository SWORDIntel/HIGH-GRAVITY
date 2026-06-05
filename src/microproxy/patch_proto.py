"""Observe-only protobuf compatibility helper."""

from typing import Any


def patch_proto(payload: bytes, *args: Any, **kwargs: Any) -> bytes:
    """Return payload unchanged; Antigravity observe-only mode never patches proto."""
    return bytes(payload)
