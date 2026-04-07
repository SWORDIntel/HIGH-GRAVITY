"""
MEMSHADOW Protocol C Binary Wrapper

This module provides Python bindings to the C binary implementation.
Falls back to pure Python if C extension is not available.
"""

import ctypes
import os
from pathlib import Path

# Try to load C extension
try:
    import memshadow_c
    _C_EXTENSION_AVAILABLE = True
except ImportError:
    _C_EXTENSION_AVAILABLE = False
    
    # Try to load shared library directly
    _lib_path = Path(__file__).parent.parent / "c" / "libmemshadow.so"
    if _lib_path.exists():
        try:
            _lib = ctypes.CDLL(str(_lib_path))
            _C_EXTENSION_AVAILABLE = True
        except OSError:
            pass

# Fallback to pure Python implementation
if not _C_EXTENSION_AVAILABLE:
    from src.pegasus.network.msnet.dsmil_protocol import MemshadowHeader
    _USE_C_BINARY = False
else:
    _USE_C_BINARY = True


def pack_header_c(header):
    """
    Pack header using C binary implementation
    
    Falls back to Python if C extension unavailable.
    """
    if _USE_C_BINARY:
        try:
            return memshadow_c.pack_header(
                header.magic,
                header.version,
                header.priority,
                header.msg_type,
                header.flags_batch,
                header.payload_len,
                header.timestamp_ns,
                header.sequence_num
            )
        except Exception:
            # Fallback to Python
            pass
    
    # Python fallback
    return header.pack()


def unpack_header_c(data):
    """
    Unpack header using C binary implementation
    
    Falls back to Python if C extension unavailable.
    """
    if _USE_C_BINARY:
        try:
            result = memshadow_c.unpack_header(data)
            from src.pegasus.network.msnet.dsmil_protocol import MemshadowHeader
            return MemshadowHeader(
                magic=result[0],
                version=result[1],
                priority=result[2],
                msg_type=result[3],
                flags_batch=result[4],
                payload_len=result[5],
                timestamp_ns=result[6],
                sequence_num=result[7],
            )
        except Exception:
            # Fallback to Python
            pass
    
    # Python fallback
    from src.pegasus.network.msnet.dsmil_protocol import MemshadowHeader
    return MemshadowHeader.unpack(data)


# Export functions
__all__ = ['pack_header_c', 'unpack_header_c', '_USE_C_BINARY']
