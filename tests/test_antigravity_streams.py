"""Antigravity stream-tool rotation regression tests."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_streams_module():
    path = ROOT / "tools" / "antigravity_three_account" / "ag-streams.py"
    spec = importlib.util.spec_from_file_location("ag_streams_for_tests", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AntigravityStreamsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.streams = load_streams_module()

    def test_follow_jsonl_reopens_after_rotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traffic.jsonl"
            path.write_text(json.dumps({"index": 1}) + "\n", encoding="utf-8")
            events = self.streams.follow_jsonl(path, interval=0.001, from_start=True)
            self.assertEqual(next(events)["index"], 1)
            path.replace(path.with_name("traffic.jsonl.1"))
            path.write_text(json.dumps({"index": 2}) + "\n", encoding="utf-8")
            self.assertEqual(next(events)["index"], 2)
            events.close()


if __name__ == "__main__":
    unittest.main()
