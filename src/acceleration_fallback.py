"""Stdlib fallbacks for optional NumPy-backed proxy acceleration.

These preserve correctness when NumPy is unavailable. They intentionally disable
approximate-nearest-neighbour matching and use bisect for exact sorted-prefix
lookups; installing NumPy restores the accelerated implementations.
"""

from __future__ import annotations

import bisect
import zlib
from typing import Iterable, Optional


class TurboQuantIndex:
    """No-ANN fallback retaining the TurboQuantIndex surface."""

    def __init__(self) -> None:
        self._hashes: list[bytes] = []

    def add(self, value: bytes) -> None:
        if value not in self._hashes:
            self._hashes.append(value)

    def search(self, value: bytes) -> Optional[bytes]:
        return value if value in self._hashes else None

    def __len__(self) -> int:
        return len(self._hashes)

    @property
    def memory_bytes(self) -> int:
        return sum(len(item) for item in self._hashes)

    @property
    def raw_bytes(self) -> int:
        return self.memory_bytes


def compress_payload(data: bytes) -> bytes:
    return zlib.compress(bytes(data), level=1)


def decompress_payload(data: bytes) -> bytes:
    return zlib.decompress(bytes(data))


class QIHSE:
    """Exact sorted-int lookup fallback."""

    def search_sorted_int64(self, values: Iterable[int], target: int) -> int:
        sequence = list(values)
        index = bisect.bisect_left(sequence, target)
        return index if index < len(sequence) and sequence[index] == target else -1


class NotStisla:
    """Exact interpolation-search-compatible fallback."""

    def search_hashes(self, values: Iterable[int], target: int) -> int:
        sequence = list(values)
        index = bisect.bisect_left(sequence, target)
        return index if index < len(sequence) and sequence[index] == target else -1
