"""Proxy integration tests for non-blocking bounded flow observations."""

import importlib.util
import sys
import unittest
from pathlib import Path


def load_proxy_module():
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("hg_proxy_for_flow_tests", root / "src" / "proxy.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CaptureWriter:
    def __init__(self):
        self.record = None

    def enqueue(self, record):
        self.record = record
        return True


class DecryptedFlowProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proxy = load_proxy_module()

    def test_queue_record_caps_body_before_background_serialization(self):
        writer = CaptureWriter()
        previous_writer = self.proxy._DECRYPTED_FLOW_WRITER
        previous_limit = self.proxy.HG_DECRYPTED_TRAFFIC_MAX_BODY_BYTES
        try:
            self.proxy._DECRYPTED_FLOW_WRITER = writer
            self.proxy.HG_DECRYPTED_TRAFFIC_MAX_BODY_BYTES = 8
            self.proxy._append_decrypted_flow_event(
                request_id="req-1",
                direction="upstream_to_client",
                method="POST",
                path="/stream",
                host="localhost",
                route_mode="passthrough",
                content_type="application/octet-stream",
                body=b"x" * 100,
            )
            self.assertEqual(writer.record["body"], b"x" * 8)
            self.assertEqual(writer.record["body_total_bytes"], 100)
            event = self.proxy._decrypted_flow_event(writer.record)
            self.assertEqual(event["body"]["bytes"], 100)
            self.assertEqual(event["body"]["sample_bytes"], 8)
            self.assertTrue(event["body"]["truncated"])
            self.assertIsNone(event["body"]["sha256"])
            self.assertNotIn("body_total_bytes", event)
        finally:
            self.proxy._DECRYPTED_FLOW_WRITER = previous_writer
            self.proxy.HG_DECRYPTED_TRAFFIC_MAX_BODY_BYTES = previous_limit


if __name__ == "__main__":
    unittest.main()
