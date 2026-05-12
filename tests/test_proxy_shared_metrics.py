#!/usr/bin/env python3
"""Tests for restart-stable proxy telemetry counters."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def _load_proxy_module():
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    proxy_path = repo_root / "src" / "proxy.py"
    spec = importlib.util.spec_from_file_location("hg_proxy_for_shared_metrics_tests", proxy_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["hg_proxy_for_shared_metrics_tests"] = module
    spec.loader.exec_module(module)
    return module


class _FakeKhojBridge:
    def get_stats(self):
        return {
            "enabled": True,
            "search_cache_hits": 1,
            "binary_injection_count": 0,
            "binary_inject_dedupe_skips": 2,
            "binary_tokens_injected": 0,
            "binary_tokens_avoided": 0,
            "injection_count": 0,
        }


class ProxySharedMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proxy = _load_proxy_module()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_metrics_file = self.proxy.SHARED_METRICS_FILE
        self.original_khoj_bridge = self.proxy.khoj_bridge
        self.proxy.SHARED_METRICS_FILE = Path(self.tmp.name) / "proxy_metrics.jsonl"
        self.proxy.app.state.thinking_by_level = {"low": 0, "medium": 0, "high": 0, "xhigh": 0}

    def tearDown(self):
        self.proxy.SHARED_METRICS_FILE = self.original_metrics_file
        self.proxy.khoj_bridge = self.original_khoj_bridge
        self.tmp.cleanup()

    def test_record_thinking_persists_by_level_for_restart_display(self):
        self.proxy._record_thinking("high")
        self.proxy.app.state.thinking_by_level = {"low": 0, "medium": 0, "high": 0, "xhigh": 0}

        shared = self.proxy._shared_metric_totals()
        self.assertEqual(shared["mitm_thinking_high"], 1)
        self.assertEqual(
            self.proxy._shared_thinking_by_level(shared),
            {"low": 0, "medium": 0, "high": 1, "xhigh": 0},
        )

    def test_binary_fail_open_metric_is_restart_stable(self):
        self.proxy._append_shared_metric("binary_fail_open", binary_fail_open=2)

        shared = self.proxy._shared_metric_totals()

        self.assertEqual(shared["binary_fail_open"], 2)

    def test_swarm_quality_uses_latest_persisted_outcome(self):
        self.proxy._append_shared_metric(
            "swarm_trigger",
            status="failed",
            latency_ms=12.5,
            agent_id="ERROR",
            failure_reason="old",
            pegasus_swarm_triggers=1,
            pegasus_swarm_attempts=1,
            pegasus_swarm_fail=1,
            pegasus_swarm_latency_ms_total=12,
        )
        self.proxy._append_shared_metric(
            "swarm_trigger",
            status="success",
            latency_ms=33.25,
            agent_id="RESEARCHER-test",
            failure_reason="",
            pegasus_swarm_triggers=1,
            pegasus_swarm_attempts=1,
            pegasus_swarm_success=1,
            pegasus_swarm_latency_ms_total=33,
        )

        summary = self.proxy._swarm_quality_summary(self.proxy._shared_metric_totals())

        self.assertEqual(summary["attempts"], 2)
        self.assertEqual(summary["success"], 1)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["last"]["status"], "success")
        self.assertEqual(summary["last"]["agent_id"], "RESEARCHER-test")

    def test_khoj_shared_metrics_are_restart_stable_without_double_counting(self):
        self.proxy.khoj_bridge = _FakeKhojBridge()
        self.proxy._append_shared_metric(
            "khoj_binary_inject",
            khoj_search_cache_hits=4,
            khoj_binary_injections=3,
            khoj_binary_dedupe_skips=5,
            khoj_tokens_injected=120,
            khoj_tokens_avoided=240,
        )

        stats = self.proxy._khoj_stats_with_shared_metrics(self.proxy._shared_metric_totals())
        self.assertEqual(stats["search_cache_hits"], 4)
        self.assertEqual(stats["binary_injection_count"], 3)
        self.assertEqual(stats["binary_inject_dedupe_skips"], 5)
        self.assertEqual(stats["binary_tokens_injected"], 120)
        self.assertEqual(stats["binary_tokens_avoided"], 240)
        self.assertEqual(stats["injection_count"], 3)

    def test_large_binary_fail_open_only_for_enabled_opaque_real_work(self):
        original_enabled = self.proxy.HG_BINARY_FAIL_OPEN
        original_threshold = self.proxy.HG_BINARY_FAIL_OPEN_BYTES
        try:
            self.proxy.HG_BINARY_FAIL_OPEN = True
            self.proxy.HG_BINARY_FAIL_OPEN_BYTES = 128

            self.assertTrue(self.proxy._is_large_binary_fail_open(128, False, True))
            self.assertFalse(self.proxy._is_large_binary_fail_open(127, False, True))
            self.assertFalse(self.proxy._is_large_binary_fail_open(128, True, True))
            self.assertFalse(self.proxy._is_large_binary_fail_open(128, False, False))

            self.proxy.HG_BINARY_FAIL_OPEN = False
            self.assertFalse(self.proxy._is_large_binary_fail_open(128, False, True))
        finally:
            self.proxy.HG_BINARY_FAIL_OPEN = original_enabled
            self.proxy.HG_BINARY_FAIL_OPEN_BYTES = original_threshold

    def test_large_json_intelligence_fail_open_only_for_real_work(self):
        original_threshold = self.proxy.HG_JSON_INTELLIGENCE_MAX_BYTES
        try:
            self.proxy.HG_JSON_INTELLIGENCE_MAX_BYTES = 256

            self.assertTrue(self.proxy._skip_expensive_json_intelligence(256, True, True))
            self.assertFalse(self.proxy._skip_expensive_json_intelligence(255, True, True))
            self.assertFalse(self.proxy._skip_expensive_json_intelligence(256, False, True))
            self.assertFalse(self.proxy._skip_expensive_json_intelligence(256, True, False))

            self.proxy.HG_JSON_INTELLIGENCE_MAX_BYTES = 0
            self.assertFalse(self.proxy._skip_expensive_json_intelligence(256, True, True))
        finally:
            self.proxy.HG_JSON_INTELLIGENCE_MAX_BYTES = original_threshold

    def test_stream_cache_capture_stops_before_unbounded_growth(self):
        original_limit = self.proxy.HG_STREAM_CACHE_MAX_BYTES
        try:
            self.proxy.HG_STREAM_CACHE_MAX_BYTES = 5
            chunks = []

            current_len, truncated = self.proxy._capture_stream_cache_chunk(chunks, 0, b"abc")
            self.assertEqual(current_len, 3)
            self.assertFalse(truncated)
            self.assertEqual(chunks, [b"abc"])

            current_len, truncated = self.proxy._capture_stream_cache_chunk(chunks, current_len, b"def")
            self.assertEqual(current_len, 3)
            self.assertTrue(truncated)
            self.assertEqual(chunks, [b"abc"])
        finally:
            self.proxy.HG_STREAM_CACHE_MAX_BYTES = original_limit

    def test_exact_response_cache_replays_only_matching_request_hash(self):
        self.proxy._exact_response_cache.clear()
        self.proxy._exact_response_cache_order.clear()

        key = self.proxy._exact_response_cache_key(
            "POST",
            "exa.api_server_pb.ApiServerService/GetChatMessage",
            "application/connect+proto",
            b"same request",
        )
        other_key = self.proxy._exact_response_cache_key(
            "POST",
            "exa.api_server_pb.ApiServerService/GetChatMessage",
            "application/connect+proto",
            b"different request",
        )

        stored = self.proxy._store_exact_response_cache(
            key,
            200,
            b"\x00\x00\x00\x00\x05hello",
            {"content-type": "application/connect+proto", "content-length": "10"},
        )

        self.assertTrue(stored)
        cached = self.proxy._lookup_exact_response_cache(key)
        self.assertIsNotNone(cached)
        status, body, headers = cached
        self.assertEqual(status, 200)
        self.assertEqual(body, b"\x00\x00\x00\x00\x05hello")
        self.assertEqual(headers["content-type"], "application/connect+proto")
        self.assertNotIn("content-length", {k.lower(): v for k, v in headers.items()})
        self.assertIsNone(self.proxy._lookup_exact_response_cache(other_key))

    def test_exact_response_cache_does_not_store_quota_or_oversized_body(self):
        self.proxy._exact_response_cache.clear()
        self.proxy._exact_response_cache_order.clear()
        original_limit = self.proxy.HG_EXACT_RESPONSE_CACHE_MAX_BODY_BYTES
        try:
            self.proxy.HG_EXACT_RESPONSE_CACHE_MAX_BODY_BYTES = 4
            key = self.proxy._exact_response_cache_key(
                "POST",
                "getchatmessage",
                "application/connect+proto",
                b"request",
            )
            self.assertFalse(
                self.proxy._store_exact_response_cache(key, 200, b"12345", {})
            )
            self.assertTrue(self.proxy._response_body_has_quota_signal(b"daily usage quota exhausted"))
        finally:
            self.proxy.HG_EXACT_RESPONSE_CACHE_MAX_BODY_BYTES = original_limit

    def test_canonical_response_cache_ignores_common_volatiles(self):
        original_enabled = self.proxy.HG_CANONICAL_RESPONSE_CACHE
        original_min_chars = self.proxy.HG_CANONICAL_RESPONSE_CACHE_MIN_TEXT_CHARS
        try:
            self.proxy.HG_CANONICAL_RESPONSE_CACHE = True
            self.proxy.HG_CANONICAL_RESPONSE_CACHE_MIN_TEXT_CHARS = 20
            key_a = self.proxy._canonical_response_cache_key(
                "POST",
                "exa.api_server_pb.ApiServerService/GetChatMessage",
                "application/connect+proto",
                b"a" * 9000,
                "Fix provider unreachable request 1234567890 id abcdef1234567890",
            )
            key_b = self.proxy._canonical_response_cache_key(
                "POST",
                "exa.api_server_pb.ApiServerService/GetChatMessage",
                "application/connect+proto",
                b"b" * 9000,
                "Fix provider unreachable request 9999999999 id ffffffffffffffff",
            )

            self.assertEqual(key_a, key_b)
            self.assertTrue(key_a)
        finally:
            self.proxy.HG_CANONICAL_RESPONSE_CACHE = original_enabled
            self.proxy.HG_CANONICAL_RESPONSE_CACHE_MIN_TEXT_CHARS = original_min_chars

    def test_local_ack_detects_high_volume_reporting_paths(self):
        self.assertTrue(
            self.proxy._is_local_ack_telemetry_path(
                "exa.analytics_pb.AnalyticsService/RecordCortexTrajectoryStep",
                "proxy.windsurf.com",
            )
        )
        self.assertTrue(
            self.proxy._is_local_ack_telemetry_path(
                "telemetry",
                "windsurf-telemetry.codeium.com",
            )
        )
        self.assertTrue(
            self.proxy._is_local_ack_telemetry_path(
                "api/frontend//client/metrics",
                "unleash.codeium.com",
            )
        )
        self.assertFalse(
            self.proxy._is_local_ack_telemetry_path(
                "exa.api_server_pb.ApiServerService/GetChatMessage",
                "proxy.windsurf.com",
            )
        )

    def test_inference_gate_block_returns_connect_error_for_chat(self):
        response = self.proxy._inference_gate_block_response(
            "req-gate",
            "exa.api_server_pb.ApiServerService/GetChatMessage",
            "application/connect+proto",
            "cache-only",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "application/connect+proto")
        self.assertEqual(response.body[0], 0x02)

    def test_billing_guard_uses_connect_error_envelope_for_proto_streams(self):
        response = self.proxy._billing_guard_block_response(
            "req-guard",
            "/exa.api_server_pb.ApiServerService/GetChatMessage",
            4,
            "application/connect+proto",
        )

        body = response.body
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "application/connect+proto")
        self.assertEqual(body[0], 0x02)
        payload_len = int.from_bytes(body[1:5], "big")
        payload = json.loads(body[5:5 + payload_len].decode("utf-8"))
        self.assertEqual(payload["error"]["code"], "resource_exhausted")


if __name__ == "__main__":
    unittest.main()
