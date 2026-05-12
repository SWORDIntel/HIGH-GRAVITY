"""Passive Connect/protobuf observer helpers for future sidecar use.

These helpers inspect byte copies only. They do not mutate payloads, open
sockets, append event logs, or integrate with the live proxy.
"""

from dataclasses import dataclass
import zlib
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple

try:
    from .events import make_event
except ImportError:  # pragma: no cover - supports direct file loading.
    from events import make_event  # type: ignore


CONNECT_HEADER_BYTES = 5
CONNECT_FLAG_COMPRESSED = 0x01
DEFAULT_MAX_FRAME_BYTES = 1024 * 1024
DEFAULT_MAX_DECOMPRESSED_BYTES = 1024 * 1024
DEFAULT_MAX_STRING_BYTES = 4096
DEFAULT_MAX_STRINGS = 24
DEFAULT_MIN_STRING_CHARS = 3


class ProtoObserverError(ValueError):
    """Raised when a passive protobuf observation exceeds configured bounds."""


@dataclass(frozen=True)
class ConnectFrame:
    """One complete Connect protocol envelope frame."""

    offset: int
    flags: int
    length: int
    payload: bytes

    @property
    def compressed(self) -> bool:
        return bool(self.flags & CONNECT_FLAG_COMPRESSED)

    @property
    def compression(self) -> Optional[str]:
        return "gzip" if self.compressed else None


def parse_connect_frames(
    body: bytes,
    *,
    max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
) -> List[ConnectFrame]:
    """Parse complete Connect envelope frames from ``body``.

    Incomplete trailing data is ignored because the future sidecar may observe
    bounded snapshots rather than full streams. Oversized complete frame lengths
    raise instead of allocating.
    """

    view = bytes(body)
    frames: List[ConnectFrame] = []
    offset = 0
    while offset + CONNECT_HEADER_BYTES <= len(view):
        flags = view[offset]
        length = int.from_bytes(
            view[offset + 1:offset + CONNECT_HEADER_BYTES],
            "big",
        )
        if length > max_frame_bytes:
            raise ProtoObserverError(
                f"Connect frame length {length} exceeds limit {max_frame_bytes}"
            )
        payload_start = offset + CONNECT_HEADER_BYTES
        payload_end = payload_start + length
        if payload_end > len(view):
            break
        frames.append(
            ConnectFrame(
                offset=offset,
                flags=flags,
                length=length,
                payload=view[payload_start:payload_end],
            )
        )
        offset = payload_end
    return frames


def gzip_decompress_copy(
    payload: bytes,
    *,
    max_output_bytes: int = DEFAULT_MAX_DECOMPRESSED_BYTES,
) -> bytes:
    """Return a bounded gzip-decompressed copy of ``payload``."""

    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    output = bytearray()
    chunk_size = 64 * 1024
    for offset in range(0, len(payload), chunk_size):
        chunk = payload[offset:offset + chunk_size]
        remaining = max_output_bytes - len(output)
        if remaining < 0:
            raise ProtoObserverError(
                f"gzip output exceeds limit {max_output_bytes}"
            )
        output.extend(decompressor.decompress(chunk, remaining + 1))
        if len(output) > max_output_bytes:
            raise ProtoObserverError(
                f"gzip output exceeds limit {max_output_bytes}"
            )

    remaining = max_output_bytes - len(output)
    output.extend(decompressor.flush(remaining + 1))
    if len(output) > max_output_bytes:
        raise ProtoObserverError(f"gzip output exceeds limit {max_output_bytes}")
    return bytes(output)


def extract_length_delimited_utf8_strings(
    protobuf_bytes: bytes,
    *,
    min_chars: int = DEFAULT_MIN_STRING_CHARS,
    max_string_bytes: int = DEFAULT_MAX_STRING_BYTES,
    max_strings: int = DEFAULT_MAX_STRINGS,
) -> List[str]:
    """Extract protobuf wire type 2 fields that decode as useful UTF-8 text."""

    data = bytes(protobuf_bytes)
    strings: List[str] = []
    seen = set()
    offset = 0
    while offset < len(data) and len(strings) < max_strings:
        key, next_offset = _read_varint(data, offset)
        if key is None:
            break
        offset = next_offset
        field_number = key >> 3
        wire_type = key & 0x07
        if field_number <= 0:
            break
        if wire_type == 2:
            length, next_offset = _read_varint(data, offset)
            if length is None:
                break
            offset = next_offset
            if length < 0 or offset + length > len(data):
                break
            raw = data[offset:offset + length]
            offset += length
            text = _decode_useful_utf8(raw, min_chars, max_string_bytes)
            if text and text not in seen:
                strings.append(text)
                seen.add(text)
            continue
        skip_to = _skip_wire_value(data, offset, wire_type)
        if skip_to is None:
            break
        offset = skip_to
    return strings


def observe_connect_proto(
    body: bytes,
    *,
    request_id: str,
    content_type: Optional[str] = None,
    direction: str = "request",
    ts: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
    max_decompressed_bytes: int = DEFAULT_MAX_DECOMPRESSED_BYTES,
    max_strings: int = DEFAULT_MAX_STRINGS,
) -> Dict[str, Any]:
    """Build a passive ``proto_observed`` event for Connect/protobuf bytes."""

    body_copy = bytes(body)
    details: Dict[str, Any] = {
        "proto": "connect+proto",
        "direction": direction,
        "payload_bytes": len(body_copy),
    }
    if content_type:
        details["content_type"] = content_type

    frames = (
        parse_connect_frames(body_copy, max_frame_bytes=max_frame_bytes)
        if _looks_like_connect_frames(body_copy, max_frame_bytes)
        else []
    )
    messages: List[bytes]
    compressed_frames = 0
    gzip_errors: List[str] = []
    if frames:
        messages = []
        for frame in frames:
            payload = frame.payload
            if frame.compressed:
                compressed_frames += 1
                try:
                    payload = gzip_decompress_copy(
                        payload,
                        max_output_bytes=max_decompressed_bytes,
                    )
                except (ProtoObserverError, zlib.error) as exc:
                    gzip_errors.append(str(exc))
                    continue
            messages.append(payload)
        details.update({
            "connect_frame_count": len(frames),
            "gzip_frame_count": compressed_frames,
            "connect_flags": [frame.flags for frame in frames],
            "connect_frame_lengths": [frame.length for frame in frames],
        })
    else:
        messages = [body_copy]
        details["connect_frame_count"] = 0
        details["gzip_frame_count"] = 0

    strings = _collect_strings(messages, max_strings=max_strings)
    if strings:
        details["strings"] = strings
        details["string_count"] = len(strings)
    else:
        details["string_count"] = 0
    if gzip_errors:
        details["gzip_errors"] = gzip_errors[:3]

    event_metadata = dict(metadata or {})
    return make_event(
        "proto_observed",
        request_id,
        details,
        ts=ts,
        **event_metadata,
    )


def _collect_strings(
    messages: Iterable[bytes],
    *,
    max_strings: int,
) -> List[str]:
    strings: List[str] = []
    seen = set()
    for message in messages:
        for text in extract_length_delimited_utf8_strings(
            message,
            max_strings=max_strings - len(strings),
        ):
            if text not in seen:
                strings.append(text)
                seen.add(text)
            if len(strings) >= max_strings:
                return strings
    return strings


def _looks_like_connect_frames(data: bytes, max_frame_bytes: int) -> bool:
    if len(data) < CONNECT_HEADER_BYTES:
        return False
    flags = data[0]
    if flags & ~CONNECT_FLAG_COMPRESSED:
        return False
    length = int.from_bytes(data[1:CONNECT_HEADER_BYTES], "big")
    if length > max_frame_bytes:
        return False
    return CONNECT_HEADER_BYTES + length <= len(data)


def _read_varint(data: bytes, offset: int) -> Tuple[Optional[int], int]:
    value = 0
    shift = 0
    cursor = offset
    while cursor < len(data) and shift <= 63:
        byte = data[cursor]
        cursor += 1
        value |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            return value, cursor
        shift += 7
    return None, offset


def _skip_wire_value(data: bytes, offset: int, wire_type: int) -> Optional[int]:
    if wire_type == 0:
        _, next_offset = _read_varint(data, offset)
        return next_offset if next_offset != offset else None
    if wire_type == 1:
        return offset + 8 if offset + 8 <= len(data) else None
    if wire_type == 5:
        return offset + 4 if offset + 4 <= len(data) else None
    return None


def _decode_useful_utf8(
    raw: bytes,
    min_chars: int,
    max_string_bytes: int,
) -> str:
    if not raw or len(raw) > max_string_bytes:
        return ""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ""
    text = " ".join(text.split())
    if len(text) < min_chars:
        return ""
    if not any(char.isalpha() for char in text):
        return ""
    for char in text:
        if char in "\t\n\r":
            continue
        if ord(char) < 32:
            return ""
    return text
