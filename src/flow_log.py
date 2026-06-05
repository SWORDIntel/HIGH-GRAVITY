"""Bounded asynchronous JSONL writer for decrypted-flow observations."""

from __future__ import annotations

import atexit
import json
import queue
import threading
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


class AsyncRotatingJsonlWriter:
    """Serialize and rotate JSONL records on a bounded background queue."""

    def __init__(
        self,
        path: Path,
        *,
        max_bytes: int,
        backup_count: int,
        queue_size: int,
        transform: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None,
        on_written: Optional[Callable[[Mapping[str, Any]], None]] = None,
    ) -> None:
        self.path = Path(path)
        self.max_bytes = max(1, int(max_bytes))
        self.backup_count = max(0, int(backup_count))
        self._transform = transform
        self._on_written = on_written
        self._queue: queue.Queue[Optional[Mapping[str, Any]]] = queue.Queue(
            maxsize=max(1, int(queue_size))
        )
        self._lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._written = 0
        self._dropped = 0
        self._failures = 0
        self._closed = False
        self._thread = threading.Thread(
            target=self._run,
            name="hg-decrypted-flow-writer",
            daemon=True,
        )
        self._thread.start()
        atexit.register(self.close)

    def enqueue(self, record: Mapping[str, Any]) -> bool:
        """Queue a record without blocking the caller; return False when full."""

        with self._lifecycle_lock:
            if self._closed:
                return False
            try:
                self._queue.put_nowait(record)
                return True
            except queue.Full:
                with self._lock:
                    self._dropped += 1
                return False

    def flush(self) -> None:
        """Wait until all currently queued records have been processed."""

        self._queue.join()

    def close(self) -> None:
        """Flush and stop the worker. Safe to call more than once."""

        with self._lifecycle_lock:
            if self._closed:
                return
            self._closed = True
        self._queue.put(None)
        self._queue.join()
        self._thread.join(timeout=5)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "queued": self._queue.qsize(),
                "written": self._written,
                "dropped": self._dropped,
                "failures": self._failures,
                "max_bytes": self.max_bytes,
                "backup_count": self.backup_count,
                "queue_size": self._queue.maxsize,
            }

    def _run(self) -> None:
        while True:
            record = self._queue.get()
            try:
                if record is None:
                    return
                output = self._transform(record) if self._transform else record
                line = (
                    json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n"
                ).encode("utf-8")
                self._write_line(line)
                with self._lock:
                    self._written += 1
                if self._on_written:
                    self._on_written(record)
            except Exception:
                with self._lock:
                    self._failures += 1
            finally:
                self._queue.task_done()

    def _write_line(self, line: bytes) -> None:
        if len(line) > self.max_bytes:
            raise ValueError("JSONL record exceeds configured rotation size")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size + len(line) > self.max_bytes:
            self._rotate()
        with self.path.open("ab") as handle:
            handle.write(line)

    def _rotate(self) -> None:
        if self.backup_count <= 0:
            self.path.unlink(missing_ok=True)
            return
        oldest = self.path.with_name(f"{self.path.name}.{self.backup_count}")
        oldest.unlink(missing_ok=True)
        for index in range(self.backup_count - 1, 0, -1):
            source = self.path.with_name(f"{self.path.name}.{index}")
            if source.exists():
                source.replace(self.path.with_name(f"{self.path.name}.{index + 1}"))
        if self.path.exists():
            self.path.replace(self.path.with_name(f"{self.path.name}.1"))
