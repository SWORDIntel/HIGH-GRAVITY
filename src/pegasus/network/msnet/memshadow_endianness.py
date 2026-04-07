"""
MEMSHADOW Protocol Endianness Helpers

Provides conversion helpers for big-endian (network byte order) operations.
All protocol messages use big-endian encoding.
"""

import struct
from typing import Union


# Protocol uses big-endian (network byte order)
BYTE_ORDER = ">"  # Big-endian


def pack_uint8(value: int) -> bytes:
    """Pack unsigned 8-bit integer (big-endian)"""
    return struct.pack(">B", value)


def pack_uint16(value: int) -> bytes:
    """Pack unsigned 16-bit integer (big-endian)"""
    return struct.pack(">H", value)


def pack_uint32(value: int) -> bytes:
    """Pack unsigned 32-bit integer (big-endian)"""
    return struct.pack(">I", value)


def pack_uint64(value: int) -> bytes:
    """Pack unsigned 64-bit integer (big-endian)"""
    return struct.pack(">Q", value)


def pack_int8(value: int) -> bytes:
    """Pack signed 8-bit integer (big-endian)"""
    return struct.pack(">b", value)


def pack_int16(value: int) -> bytes:
    """Pack signed 16-bit integer (big-endian)"""
    return struct.pack(">h", value)


def pack_int32(value: int) -> bytes:
    """Pack signed 32-bit integer (big-endian)"""
    return struct.pack(">i", value)


def pack_int64(value: int) -> bytes:
    """Pack signed 64-bit integer (big-endian)"""
    return struct.pack(">q", value)


def pack_float32(value: float) -> bytes:
    """Pack 32-bit float (big-endian)"""
    return struct.pack(">f", value)


def pack_float64(value: float) -> bytes:
    """Pack 64-bit float (big-endian)"""
    return struct.pack(">d", value)


def unpack_uint8(data: bytes, offset: int = 0) -> int:
    """Unpack unsigned 8-bit integer (big-endian)"""
    return struct.unpack_from(">B", data, offset)[0]


def unpack_uint16(data: bytes, offset: int = 0) -> int:
    """Unpack unsigned 16-bit integer (big-endian)"""
    return struct.unpack_from(">H", data, offset)[0]


def unpack_uint32(data: bytes, offset: int = 0) -> int:
    """Unpack unsigned 32-bit integer (big-endian)"""
    return struct.unpack_from(">I", data, offset)[0]


def unpack_uint64(data: bytes, offset: int = 0) -> int:
    """Unpack unsigned 64-bit integer (big-endian)"""
    return struct.unpack_from(">Q", data, offset)[0]


def unpack_int8(data: bytes, offset: int = 0) -> int:
    """Unpack signed 8-bit integer (big-endian)"""
    return struct.unpack_from(">b", data, offset)[0]


def unpack_int16(data: bytes, offset: int = 0) -> int:
    """Unpack signed 16-bit integer (big-endian)"""
    return struct.unpack_from(">h", data, offset)[0]


def unpack_int32(data: bytes, offset: int = 0) -> int:
    """Unpack signed 32-bit integer (big-endian)"""
    return struct.unpack_from(">i", data, offset)[0]


def unpack_int64(data: bytes, offset: int = 0) -> int:
    """Unpack signed 64-bit integer (big-endian)"""
    return struct.unpack_from(">q", data, offset)[0]


def unpack_float32(data: bytes, offset: int = 0) -> float:
    """Unpack 32-bit float (big-endian)"""
    return struct.unpack_from(">f", data, offset)[0]


def unpack_float64(data: bytes, offset: int = 0) -> float:
    """Unpack 64-bit float (big-endian)"""
    return struct.unpack_from(">d", data, offset)[0]


def pack_string(value: str, encoding: str = "utf-8") -> bytes:
    """
    Pack string with length prefix (big-endian uint32)
    
    Format: [length:4][string_data:variable]
    """
    encoded = value.encode(encoding)
    return pack_uint32(len(encoded)) + encoded


def unpack_string(data: bytes, offset: int = 0, encoding: str = "utf-8") -> tuple[str, int]:
    """
    Unpack string with length prefix (big-endian uint32)
    
    Returns:
        Tuple of (string_value, new_offset)
    """
    length = unpack_uint32(data, offset)
    offset += 4
    if offset + length > len(data):
        raise ValueError(f"String data truncated: need {length} bytes, have {len(data) - offset}")
    string_data = data[offset:offset + length]
    return string_data.decode(encoding), offset + length


def pack_bytes(value: bytes) -> bytes:
    """
    Pack bytes with length prefix (big-endian uint32)
    
    Format: [length:4][bytes_data:variable]
    """
    return pack_uint32(len(value)) + value


def unpack_bytes(data: bytes, offset: int = 0) -> tuple[bytes, int]:
    """
    Unpack bytes with length prefix (big-endian uint32)
    
    Returns:
        Tuple of (bytes_value, new_offset)
    """
    length = unpack_uint32(data, offset)
    offset += 4
    if offset + length > len(data):
        raise ValueError(f"Bytes data truncated: need {length} bytes, have {len(data) - offset}")
    return data[offset:offset + length], offset + length


def swap_endianness_uint16(value: int) -> int:
    """Swap endianness of 16-bit integer"""
    return struct.unpack("<H", struct.pack(">H", value))[0]


def swap_endianness_uint32(value: int) -> int:
    """Swap endianness of 32-bit integer"""
    return struct.unpack("<I", struct.pack(">I", value))[0]


def swap_endianness_uint64(value: int) -> int:
    """Swap endianness of 64-bit integer"""
    return struct.unpack("<Q", struct.pack(">Q", value))[0]


def is_big_endian() -> bool:
    """Check if system is big-endian"""
    return struct.pack(">H", 1) == struct.pack("H", 1)


def is_little_endian() -> bool:
    """Check if system is little-endian"""
    return struct.pack("<H", 1) == struct.pack("H", 1)


# Convenience aliases
pack_u8 = pack_uint8
pack_u16 = pack_uint16
pack_u32 = pack_uint32
pack_u64 = pack_uint64
pack_i8 = pack_int8
pack_i16 = pack_int16
pack_i32 = pack_int32
pack_i64 = pack_int64
pack_f32 = pack_float32
pack_f64 = pack_float64

unpack_u8 = unpack_uint8
unpack_u16 = unpack_uint16
unpack_u32 = unpack_uint32
unpack_u64 = unpack_uint64
unpack_i8 = unpack_int8
unpack_i16 = unpack_int16
unpack_i32 = unpack_int32
unpack_i64 = unpack_int64
unpack_f32 = unpack_float32
unpack_f64 = unpack_float64
