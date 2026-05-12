#!/usr/bin/env python3
"""Targeted tests for control-plane response caching."""

import importlib.util
import sys
import tempfile
import time
from pathlib import Path
import unittest


def _load_proxy_module():
    repo_root = Path(__file__).resolve().parent.parent
    proxy_path = repo_root / "src" / "proxy.py"
    spec = importlib.util.spec_from_file_location("hg_proxy_for_control_plane_cache_tests", proxy_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["hg_proxy_for_control_plane_cache_tests"] = module
    spec.loader.exec_module(module)
    return module


class ControlPlaneCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proxy = _load_proxy_module()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_metrics_file = self.proxy.SHARED_METRICS_FILE
        self.proxy.SHARED_METRICS_FILE = Path(self.tmp.name) / "proxy_metrics.jsonl"

        self.original_cache_ttl = self.proxy.HG_CONTROL_PLANE_CACHE_TTL_SECONDS
        self.original_cache_max = self.proxy.HG_CONTROL_PLANE_CACHE_MAX_ENTRIES
        self.original_bypass = self.proxy.HG_BYPASS_CONTROL_PLANE

        self.proxy.HG_CONTROL_PLANE_CACHE_TTL_SECONDS = 30
        self.proxy.HG_CONTROL_PLANE_CACHE_MAX_ENTRIES = 2
        self.proxy.HG_BYPASS_CONTROL_PLANE = True
        self.proxy._control_plane_cache = {}

    def tearDown(self):
        self.proxy.SHARED_METRICS_FILE = self.original_metrics_file
        self.proxy.HG_CONTROL_PLANE_CACHE_TTL_SECONDS = self.original_cache_ttl
        self.proxy.HG_CONTROL_PLANE_CACHE_MAX_ENTRIES = self.original_cache_max
        self.proxy.HG_BYPASS_CONTROL_PLANE = self.original_bypass
        self.proxy._control_plane_cache = {}
        self.tmp.cleanup()

    def test_cache_candidate_only_for_config_and_proto(self):
        path = "/exa.api_server_pb.ApiServerService/GetUserStatus"
        self.assertTrue(self.proxy._is_control_plane_cache_candidate(path.lower(), "config", "application/grpc"))
        self.assertTrue(self.proxy._is_control_plane_cache_candidate(path.lower(), "config", "application/proto"))
        self.assertFalse(self.proxy._is_control_plane_cache_candidate(path.lower(), "inference", "application/grpc"))
        self.assertFalse(self.proxy._is_control_plane_cache_candidate("/v1/chat/completions", "config", "application/json"))
        self.assertFalse(self.proxy._is_control_plane_cache_candidate("/unknown/control/path", "config", "application/connect+proto"))

    def test_cache_key_includes_auth_and_body(self):
        key_a = self.proxy._control_plane_cache_key(
            "POST",
            "/exa.api_server_pb.ApiServerService/GetUserStatus",
            b"body-a",
            "Bearer A",
        )
        key_b = self.proxy._control_plane_cache_key(
            "POST",
            "/exa.api_server_pb.ApiServerService/GetUserStatus",
            b"body-a",
            "Bearer B",
        )
        key_c = self.proxy._control_plane_cache_key(
            "POST",
            "/exa.api_server_pb.ApiServerService/GetUserStatus",
            b"body-c",
            "Bearer A",
        )
        self.assertNotEqual(key_a, key_b)
        self.assertNotEqual(key_a, key_c)

    def test_cache_round_trip_stores_and_honors_ttl(self):
        cache_key = self.proxy._control_plane_cache_key(
            "POST",
            "/exa.api_server_pb.ApiServerService/GetUserStatus",
            b"body",
            "Bearer token",
        )
        headers = {"content-type": "application/grpc"}
        self.proxy._store_control_plane_cache(cache_key, 200, b"cached-body", headers)

        cached = self.proxy._lookup_control_plane_cache(cache_key)
        self.assertIsNotNone(cached)
        status, body, out_headers = cached
        self.assertEqual(status, 200)
        self.assertEqual(body, b"cached-body")
        self.assertEqual(out_headers, headers)

        shared = self.proxy._shared_metric_totals()
        self.assertEqual(shared["control_plane_cache_stores"], 1)

        cached_expired = self.proxy._lookup_control_plane_cache(cache_key)
        self.assertIsNotNone(cached_expired)

        with self.proxy._control_plane_cache_lock:
            self.proxy._control_plane_cache[cache_key] = (time.time() - 1, 200, b"cached-body", headers)
        self.assertIsNone(self.proxy._lookup_control_plane_cache(cache_key))

    def test_cache_only_stores_successful_responses(self):
        cache_key_500 = self.proxy._control_plane_cache_key(
            "POST",
            "/exa.api_server_pb.ApiServerService/GetUserStatus",
            b"body",
            "Bearer token",
        )
        self.proxy._store_control_plane_cache(cache_key_500, 500, b"server-error", {"content-type": "application/grpc"})
        self.assertIsNone(self.proxy._lookup_control_plane_cache(cache_key_500))

    def test_cache_is_fifo_evicted_when_full(self):
        self.proxy.HG_CONTROL_PLANE_CACHE_MAX_ENTRIES = 1

        first_key = self.proxy._control_plane_cache_key(
            "POST",
            "/exa.api_server_pb.ApiServerService/GetUserStatus",
            b"body-1",
            "Bearer token",
        )
        second_key = self.proxy._control_plane_cache_key(
            "POST",
            "/exa.api_server_pb.ApiServerService/GetUserStatus",
            b"body-2",
            "Bearer token",
        )
        self.proxy._store_control_plane_cache(first_key, 200, b"v1", {"content-type": "application/grpc"})
        self.proxy._store_control_plane_cache(second_key, 200, b"v2", {"content-type": "application/grpc"})

        self.assertIsNone(self.proxy._lookup_control_plane_cache(first_key))
        cached = self.proxy._lookup_control_plane_cache(second_key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached[1], b"v2")


if __name__ == "__main__":
    unittest.main()
