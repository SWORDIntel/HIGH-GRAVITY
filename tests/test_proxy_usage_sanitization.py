#!/usr/bin/env python3
"""
Targeted tests for usage/rate-limit sanitization in the proxy.
"""

import importlib.util
import json
import sys
from pathlib import Path
import unittest


def _load_proxy_module():
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    proxy_path = repo_root / "src" / "proxy.py"
    spec = importlib.util.spec_from_file_location("hg_proxy_for_usage_tests", proxy_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["hg_proxy_for_usage_tests"] = module
    spec.loader.exec_module(module)
    return module


class UsageSanitizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proxy = _load_proxy_module()

    def test_sanitize_usage_payload_resets_usage_fields(self):
        payload = {
            "usagePercent": 87,
            "remainingTokens": 12,
            "isRateLimited": True,
            "context": {
                "creditsUsed": 400,
            },
            "message": "ok",
        }
        sanitized = self.proxy._sanitize_usage_payload(payload, include_unlimited=True)

        self.assertEqual(sanitized["usagePercent"], 0)
        self.assertEqual(sanitized["remainingTokens"], 999999)
        self.assertEqual(sanitized["isRateLimited"], False)
        self.assertEqual(sanitized["context"]["creditsUsed"], 0)
        self.assertNotIn("extra_usage", sanitized["context"])
        self.assertEqual(sanitized["extra_usage"], {"is_enabled": True, "monthly_limit": None, "used_credits": 0})
        self.assertEqual(sanitized["message"], "ok")

    def test_sanitize_usage_response_runs_only_on_route_or_usage_path(self):
        response = json.dumps({
            "message": "ok",
            "status": "ok",
            "rateLimited": True,
            "used_credits": 44,
        }).encode("utf-8")
        out_passthrough = self.proxy._maybe_sanitize_usage_response(
            "/api/oauth/usage",
            response,
            "application/json",
            route_mode="passthrough",
        )
        parsed_passthrough = json.loads(out_passthrough.decode("utf-8"))
        self.assertEqual(parsed_passthrough["used_credits"], 0)
        self.assertEqual(parsed_passthrough["rateLimited"], False)
        self.assertEqual(parsed_passthrough["extra_usage"]["used_credits"], 0)

        out_config = self.proxy._maybe_sanitize_usage_response(
            "/exa.api_server_pb.ApiServerService/CheckUserMessageRateLimit",
            response,
            "application/json",
            route_mode="config",
        )
        parsed = json.loads(out_config.decode("utf-8"))
        self.assertEqual(parsed["used_credits"], 0)
        self.assertEqual(parsed["rateLimited"], False)
        self.assertEqual(parsed["extra_usage"]["used_credits"], 0)

        out_non_usage_route = self.proxy._maybe_sanitize_usage_response(
            "/exa.api_server_pb.SeatManagementService/GetUserStatus",
            response,
            "application/json",
            route_mode="config",
        )
        parsed = json.loads(out_non_usage_route.decode("utf-8"))
        self.assertEqual(parsed["used_credits"], 0)
        self.assertEqual(parsed["rateLimited"], False)

    def test_payload_has_usage_key_detects_nested_fields(self):
        self.assertTrue(
            self.proxy._payload_has_usage_key({
                "outer": {
                    "inner": {
                        "used_tokens": 7,
                    }
                }
            })
        )
        self.assertFalse(self.proxy._payload_has_usage_key({"outer": {"inner": {"value": 7}}}))

    def test_usage_probe_path_normalization(self):
        self.assertTrue(self.proxy._is_usage_probe_path("api/oauth/usage"))
        self.assertTrue(self.proxy._is_usage_probe_path("/api/oauth/usage"))
        self.assertTrue(self.proxy._is_usage_probe_path("/api/oauth/usage/"))
        self.assertTrue(self.proxy._is_usage_probe_path("api//oauth//usage//"))
        self.assertFalse(self.proxy._is_usage_probe_path("api/client/features"))
        self.assertFalse(self.proxy._is_usage_probe_path("/exa.api_server_pb.ApiServerService/GetChatMessage"))

    def test_non_billing_request_paths_are_exempt_from_usage_counting(self):
        self.assertTrue(self.proxy._is_non_billing_request_path("api/client/features"))
        self.assertTrue(self.proxy._is_non_billing_request_path("/api/client/metrics"))
        self.assertTrue(self.proxy._is_non_billing_request_path("api/client//metrics"))
        self.assertTrue(self.proxy._is_non_billing_request_path("/api/frontend/client/metrics"))
        self.assertTrue(self.proxy._is_non_billing_request_path("api/frontend"))
        self.assertTrue(self.proxy._is_non_billing_request_path("/api/frontend/client/metrics"))
        self.assertTrue(self.proxy._is_non_billing_request_path("/api/client/features"))
        self.assertTrue(self.proxy._is_non_billing_request_path("hg/telemetry"))
        self.assertTrue(self.proxy._is_non_billing_request_path("/hg/microproxy/status"))
        self.assertTrue(self.proxy._is_non_billing_request_path("exa.analytics_pb.AnalyticsService/RecordCortexTrajectoryStep"))
        self.assertTrue(self.proxy._is_non_billing_request_path("exa.product_analytics_pb.ProductAnalyticsService/RecordAnalyticsEvent"))
        self.assertTrue(self.proxy._is_non_billing_request_path("exa.api_server_pb.ApiServerService/RecordAsyncTelemetry"))
        self.assertFalse(self.proxy._is_non_billing_request_path("/api/oauth/usage"))

    def test_usage_proto_non_targeted_config_path_is_left_untouched(self):
        untouched = self.proxy._maybe_sanitize_usage_response(
            "/exa.api_server_pb.ApiServerService/GetModelStatuses",
            b"\x08\x01\x18\xff\xff",
            "application/proto",
            route_mode="config",
        )
        self.assertEqual(untouched, b"\x08\x01\x18\xff\xff")

    def test_stream_sanitizer_handles_json_lines_and_partial_frames(self):
        path = "/exa.api_server_pb.ApiServerService/CheckUserMessageRateLimit"
        header = "application/json"

        first_chunk = b'data: {"used_credits":44,"remainingCredits":12}\n'
        out1, carry1 = self.proxy._sanitize_streaming_usage_lines(
            first_chunk,
            path,
            "config",
            header,
        )
        self.assertEqual(carry1, b"")
        line_payload = json.loads(out1.decode("utf-8").removeprefix("data:").lstrip())
        self.assertEqual(
            line_payload["used_credits"],
            0,
        )
        self.assertEqual(
            line_payload["remainingCredits"],
            999999,
        )

        partial1 = b'data: {"used_tokens":12,'
        partial2 = b'"remaining_tokens":3}\n'
        out2a, carry2a = self.proxy._sanitize_streaming_usage_lines(
            partial1,
            path,
            "config",
            header,
        )
        self.assertEqual(out2a, b"")
        self.assertEqual(carry2a, partial1)

        out2b, carry2b = self.proxy._sanitize_streaming_usage_lines(
            partial2,
            path,
            "config",
            header,
            carry2a,
        )
        self.assertEqual(carry2b, b"")
        parsed = json.loads(out2b.decode("utf-8").removeprefix("data:").lstrip())
        self.assertEqual(parsed["used_tokens"], 0)
        self.assertEqual(parsed["remaining_tokens"], 999999)

    def test_stream_sanitizer_runs_for_usage_passthrough(self):
        path = "/api/oauth/usage"
        header = "application/json"
        payload = b"data: {\"usagePercent\": 87, \"used_tokens\": 12, \"remainingTokens\": 4}\n"

        out, carry = self.proxy._sanitize_streaming_usage_lines(
            payload,
            path,
            "passthrough",
            header,
        )

        self.assertEqual(carry, b"")
        parsed = json.loads(out.decode("utf-8").removeprefix("data:").lstrip())
        self.assertEqual(parsed["usagePercent"], 0)
        self.assertEqual(parsed["used_tokens"], 0)
        self.assertEqual(parsed["remainingTokens"], 999999)

    def test_relay_headers_strip_rate_limits_for_usage_passthrough(self):
        headers = {
            "content-type": "application/json",
            "x-ratelimit-limit": "7",
            "retry-after": "10",
            "anthropic-ratelimit-unified-7d-utilization": "9.9",
        }
        out = self.proxy._relay_headers(
            headers,
            route_mode="passthrough",
            path_l="/api/oauth/usage",
        )
        self.assertNotIn("x-ratelimit-limit", out)
        self.assertNotIn("retry-after", out)
        self.assertEqual(out["anthropic-ratelimit-unified-7d-utilization"], "0")

    def test_relay_headers_strip_rate_limits_for_passthrough_inference_path(self):
        headers = {
            "content-type": "application/json",
            "x-ratelimit-limit": "7",
            "ratelimit-remaining": "4",
            "retry-after": "10",
        }
        out = self.proxy._relay_headers(
            headers,
            route_mode="passthrough",
            path_l="/v1/completions",
        )
        self.assertNotIn("x-ratelimit-limit", out)
        self.assertNotIn("ratelimit-remaining", out)
        self.assertNotIn("retry-after", out)
        self.assertEqual(out["anthropic-ratelimit-unified-7d-utilization"], "0")

    def test_usage_proto_fields_are_sanitized(self):
        # CheckUserMessageRateLimit currently carries varint fields for usage in
        # wire order [1, 3, 4], where 3 and 4 are the high watermark values.
        path = "/exa.api_server_pb.ApiServerService/CheckUserMessageRateLimit"
        original = b"\x08\x01\x18\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01 \xff\xff\xff\xff\xff\xff\xff\xff\xff\x01"
        sanitized = self.proxy._maybe_sanitize_usage_response(
            path,
            original,
            "application/proto",
            route_mode="config",
        )
        self.assertNotEqual(sanitized, original)
        self.assertEqual(sanitized, b"\x08\x01\x18\xbf\x84\x3d\x20\xbf\x84\x3d")


if __name__ == "__main__":
    unittest.main()
