#!/usr/bin/env python3
"""Tests for proxy upstream target selection."""

import importlib.util
import sys
from pathlib import Path
import unittest


def _load_proxy_module():
    repo_root = Path(__file__).resolve().parent.parent
    proxy_path = repo_root / "src" / "proxy.py"
    spec = importlib.util.spec_from_file_location("hg_proxy_for_routing_tests", proxy_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["hg_proxy_for_routing_tests"] = module
    spec.loader.exec_module(module)
    return module


class ProxyRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proxy = _load_proxy_module()

    def test_local_host_maps_to_server_self_serve(self):
        self.assertEqual(
            self.proxy._select_upstream_base_url("127.0.0.1:9998", False),
            "https://server.self-serve.windsurf.com",
        )
        self.assertEqual(
            self.proxy._select_upstream_base_url("localhost:12345", False),
            "https://server.self-serve.windsurf.com",
        )
        self.assertEqual(
            self.proxy._select_upstream_base_url("0.0.0.0", False),
            "https://server.self-serve.windsurf.com",
        )

    def test_proxy_windsurf_maps_to_server_self_serve(self):
        self.assertEqual(
            self.proxy._select_upstream_base_url("proxy.windsurf.com", False),
            "https://server.self-serve.windsurf.com",
        )
        self.assertEqual(
            self.proxy._select_upstream_base_url("proxy.windsurf.com:9998", False),
            "https://server.self-serve.windsurf.com",
        )

    def test_non_loopback_hosts_preserve_host(self):
        self.assertEqual(
            self.proxy._select_upstream_base_url("server.self-serve.windsurf.com", False),
            "https://server.self-serve.windsurf.com",
        )
        self.assertEqual(
            self.proxy._select_upstream_base_url("api.codeium.com:443", False),
            "https://api.codeium.com",
        )

    def test_inference_host_forces_inference_endpoint(self):
        self.assertEqual(
            self.proxy._select_upstream_base_url("anything", True),
            "https://inference.codeium.com",
        )

    def test_api_server_chat_stays_on_self_serve(self):
        self.assertEqual(
            self.proxy._select_upstream_base_url(
                "proxy.windsurf.com",
                True,
                "exa.api_server_pb.ApiServerService/GetChatMessage",
            ),
            "https://server.self-serve.windsurf.com",
        )
        self.assertEqual(
            self.proxy._select_upstream_base_url(
                "proxy.windsurf.com",
                True,
                "exa.api_server_pb.ApiServerService/CheckUserMessageRateLimit",
            ),
            "https://server.self-serve.windsurf.com",
        )

    def test_openai_compat_paths_do_not_route_to_windsurf_by_default(self):
        self.assertEqual(
            self.proxy._select_upstream_base_url("proxy.windsurf.com", True, "v1/chat/completions"),
            "",
        )
        self.assertEqual(
            self.proxy._select_upstream_base_url("127.0.0.1:9998", False, "v1/models"),
            "",
        )


if __name__ == "__main__":
    unittest.main()
