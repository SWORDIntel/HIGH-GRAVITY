"""Regression tests for bounded asynchronous decrypted-flow JSONL logging."""

import json
import tempfile
import threading
import unittest
from pathlib import Path

from src.flow_log import AsyncRotatingJsonlWriter


class FlowLogWriterTests(unittest.TestCase):
    def test_rotates_and_bounds_jsonl_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traffic.jsonl"
            writer = AsyncRotatingJsonlWriter(
                path,
                max_bytes=90,
                backup_count=2,
                queue_size=16,
            )
            for index in range(8):
                self.assertTrue(writer.enqueue({"index": index, "payload": "x" * 30}))
            writer.close()

            files = sorted(path.parent.glob("traffic.jsonl*"))
            self.assertLessEqual(len(files), 3)
            self.assertTrue(path.exists())
            for candidate in files:
                self.assertLessEqual(candidate.stat().st_size, 90)
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    json.loads(line)

    def test_oversized_record_is_rejected_without_growing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traffic.jsonl"
            writer = AsyncRotatingJsonlWriter(
                path,
                max_bytes=32,
                backup_count=1,
                queue_size=2,
            )
            self.assertTrue(writer.enqueue({"payload": "x" * 100}))
            writer.close()
            self.assertFalse(path.exists())
            self.assertEqual(writer.stats()["failures"], 1)

    def test_enqueue_after_close_is_rejected_without_deadlock(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = AsyncRotatingJsonlWriter(
                Path(tmp) / "traffic.jsonl",
                max_bytes=1024,
                backup_count=1,
                queue_size=2,
            )
            writer.close()
            self.assertFalse(writer.enqueue({"index": 1}))
            writer.close()

    def test_full_queue_drops_without_blocking(self):
        release = threading.Event()
        started = threading.Event()

        def blocked_transform(record):
            started.set()
            release.wait(timeout=5)
            return record

        with tempfile.TemporaryDirectory() as tmp:
            writer = AsyncRotatingJsonlWriter(
                Path(tmp) / "traffic.jsonl",
                max_bytes=1024,
                backup_count=1,
                queue_size=1,
                transform=blocked_transform,
            )
            self.assertTrue(writer.enqueue({"index": 1}))
            self.assertTrue(started.wait(timeout=2))
            self.assertTrue(writer.enqueue({"index": 2}))
            self.assertFalse(writer.enqueue({"index": 3}))
            self.assertEqual(writer.stats()["dropped"], 1)
            release.set()
            writer.close()


if __name__ == "__main__":
    unittest.main()
