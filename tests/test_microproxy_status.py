#!/usr/bin/env python3
"""Tests for read-only microproxy status exposure in the Python proxy."""

import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from src.microproxy import events


def _load_proxy_module():
    if "aiohttp" not in sys.modules:
        aiohttp_stub = types.ModuleType("aiohttp")
        aiohttp_stub.ClientSession = object
        aiohttp_stub.ClientConnectionError = RuntimeError
        aiohttp_stub.ClientPayloadError = RuntimeError

        class _DefaultResolver:
            async def resolve(self, host, port=0, family=0):
                return []

        aiohttp_stub.DefaultResolver = _DefaultResolver
        sys.modules["aiohttp"] = aiohttp_stub

    repo_root = Path(__file__).resolve().parent.parent
    proxy_path = repo_root / "src" / "proxy.py"
    spec = importlib.util.spec_from_file_location(
        "hg_proxy_for_microproxy_status_tests",
        proxy_path,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["hg_proxy_for_microproxy_status_tests"] = module
    spec.loader.exec_module(module)
    return module


class MicroproxyStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proxy = _load_proxy_module()

    def test_missing_event_file_reports_empty_read_only_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_events = Path(tmp) / "missing-events.jsonl"
            missing_pid = Path(tmp) / "missing.pid"

            with mock.patch.dict(os.environ, {"HG_MICROPROXY_FRONT": "0"}):
                status = self.proxy._microproxy_status_summary(
                    missing_events,
                    missing_pid,
                    Path(tmp) / "missing-front.pid",
                )

        self.assertFalse(status["reader"]["source_exists"])
        self.assertEqual(status["reader"]["rows"], 0)
        self.assertEqual(status["events"]["request_seen"], 0)
        self.assertEqual(status["routes"]["total"], 0)
        self.assertEqual(status["streams"]["streams_started"], 0)
        self.assertEqual(status["upstream_errors"]["total"], 0)
        self.assertFalse(status["prototype"]["pid"]["running"])
        self.assertFalse(status["prototype"]["front_pid"]["running"])
        self.assertEqual(status["front"]["mode"], "python_tls_direct")
        self.assertFalse(status["front"]["enabled"])
        self.assertTrue(status["live_traffic"]["python_proxy_default"])
        self.assertFalse(status["live_traffic"]["microproxy_routing_enabled"])
        self.assertIsNone(status["front"].get("upstream"))

    def test_event_file_summary_reports_routes_streams_errors_and_pid(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            event_file = tmp_path / "microproxy_events.jsonl"
            pid_file = tmp_path / "microproxy.pid"
            front_pid_file = tmp_path / "microproxy_front.pid"
            event_file.write_text(
                events.event_to_jsonl(
                    events.make_event(
                        "request_seen",
                        "req-1",
                        {"method": "POST", "path": "/v1/messages"},
                        ts="2026-05-11T10:00:00.000Z",
                    )
                )
                + events.event_to_jsonl(
                    events.make_event(
                        "route_selected",
                        "req-1",
                        {"route": "passthrough", "classification": "direct"},
                        ts="2026-05-11T10:00:00.010Z",
                    )
                )
                + events.event_to_jsonl(
                    events.make_event(
                        "stream_started",
                        "req-1",
                        {"stream_id": "stream-1"},
                        ts="2026-05-11T10:00:00.020Z",
                    )
                )
                + events.event_to_jsonl(
                    events.make_event(
                        "upstream_error",
                        "req-2",
                        {
                            "upstream": "openai",
                            "error_type": "timeout",
                            "message": "timed out",
                        },
                        ts="2026-05-11T10:00:01.000Z",
                    )
                )
                + '{"bad": "row"}\n',
                encoding="utf-8",
            )
            pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {"HG_MICROPROXY_FRONT": "0"}):
                status = self.proxy._microproxy_status_summary(
                    event_file,
                    pid_file,
                    front_pid_file,
                )

        self.assertTrue(status["reader"]["source_exists"])
        self.assertEqual(status["reader"]["rows"], 4)
        self.assertEqual(status["reader"]["invalid_rows"], 1)
        self.assertEqual(status["events"]["request_seen"], 1)
        self.assertEqual(status["events"]["upstream_error"], 1)
        self.assertEqual(status["routes"]["routes"], {"passthrough": 1})
        self.assertEqual(status["routes"]["classifications"], {"direct": 1})
        self.assertEqual(status["streams"]["streams_started"], 1)
        self.assertEqual(status["streams"]["streams_open"], 1)
        self.assertEqual(status["upstream_errors"]["upstreams"], {"openai": 1})
        self.assertEqual(status["upstream_errors"]["error_types"], {"timeout": 1})
        self.assertTrue(status["prototype"]["pid"]["running"])
        self.assertEqual(status["prototype"]["pid"]["pid"], os.getpid())
        self.assertFalse(status["prototype"]["front_pid"]["running"])

    def test_front_pid_reports_live_routing_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            event_file = tmp_path / "microproxy_events.jsonl"
            pid_file = tmp_path / "microproxy.pid"
            front_pid_file = tmp_path / "microproxy_front.pid"
            event_file.write_text("", encoding="utf-8")
            front_pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {"HG_MICROPROXY_FRONT": "1"}):
                status = self.proxy._microproxy_status_summary(
                    event_file,
                    pid_file,
                    front_pid_file,
                )

        self.assertFalse(status["prototype"]["pid"]["running"])
        self.assertTrue(status["prototype"]["front_pid"]["running"])
        self.assertEqual(status["front"]["mode"], "c_front_active")
        self.assertTrue(status["front"]["healthy"])
        self.assertFalse(status["live_traffic"]["python_proxy_default"])
        self.assertTrue(status["live_traffic"]["microproxy_routing_enabled"])
        self.assertTrue(status["live_traffic"]["front_relay_enabled"])

    def test_front_status_reports_enabled_failed_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pid_file = tmp_path / "prototype.pid"
            front_pid_file = tmp_path / "front.pid"
            front_pid_file.write_text("999999999\n", encoding="utf-8")

            with mock.patch.dict(
                os.environ,
                {
                    "HG_MICROPROXY_FRONT": "1",
                    "HG_MICROPROXY_FRONT_LISTEN": "127.0.0.1:2443",
                    "HG_MICROPROXY_FRONT_UPSTREAM": "127.0.0.1:9443",
                },
            ):
                status = self.proxy._microproxy_status_summary(
                    tmp_path / "missing-events.jsonl",
                    pid_file,
                    front_pid_file,
                )

        self.assertEqual(status["front"]["mode"], "c_front_failed")
        self.assertTrue(status["front"]["enabled"])
        self.assertFalse(status["front"]["running"])
        self.assertEqual(status["front"]["failure"], "stale_pid_file")
        self.assertFalse(status["live_traffic"]["python_proxy_default"])
        self.assertTrue(status["live_traffic"]["front_relay_enabled"])
        self.assertFalse(status["live_traffic"]["microproxy_routing_enabled"])
        self.assertEqual(status["live_traffic"]["front_listen"], "127.0.0.1:2443")

    def test_front_status_reports_disabled_but_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            front_pid_file = tmp_path / "front.pid"
            front_pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {"HG_MICROPROXY_FRONT": "0"}):
                status = self.proxy._microproxy_status_summary(
                    tmp_path / "missing-events.jsonl",
                    tmp_path / "prototype.pid",
                    front_pid_file,
                )

        self.assertEqual(status["front"]["mode"], "c_front_disabled_but_running")
        self.assertFalse(status["front"]["enabled"])
        self.assertTrue(status["front"]["running"])
        self.assertEqual(
            status["front"]["failure"],
            "front_process_running_while_disabled",
        )
        self.assertIsNone(status["front"].get("upstream"))
        self.assertTrue(status["live_traffic"]["python_proxy_default"])
        self.assertFalse(status["live_traffic"]["microproxy_routing_enabled"])

    def test_status_reports_direct_fast_path_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            front_pid_file = tmp_path / "front.pid"
            front_pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")

            with mock.patch.dict(
                os.environ,
                {
                    "HG_MICROPROXY_FRONT": "1",
                    "HG_MICROPROXY_DIRECT_UPSTREAM": "127.0.0.1:10443",
                    "HG_MICROPROXY_DIRECT_HOT_PATH": "1",
                },
            ):
                status = self.proxy._microproxy_status_summary(
                    tmp_path / "missing-events.jsonl",
                    tmp_path / "prototype.pid",
                    front_pid_file,
                )

        self.assertTrue(status["direct_fast_path"]["enabled"])
        self.assertTrue(status["direct_fast_path"]["configured"])
        self.assertTrue(status["direct_fast_path"]["active"])
        self.assertFalse(status["direct_fast_path"]["cooled_down"])
        self.assertEqual(status["direct_fast_path"]["state"], "active")
        self.assertEqual(status["direct_fast_path"]["health_state"], "healthy")
        self.assertEqual(status["direct_fast_path"]["target"], "127.0.0.1:10443")
        self.assertEqual(status["direct_fast_path"]["upstream"], "127.0.0.1:10443")
        self.assertTrue(status["live_traffic"]["direct_fast_path_enabled"])
        self.assertTrue(status["live_traffic"]["direct_fast_path_configured"])
        self.assertTrue(status["live_traffic"]["direct_fast_path_active"])
        self.assertEqual(status["live_traffic"]["direct_fast_path_state"], "active")
        self.assertEqual(
            status["live_traffic"]["direct_fast_path_health_state"],
            "healthy",
        )
        self.assertEqual(
            status["live_traffic"]["direct_fast_path_target"],
            "127.0.0.1:10443",
        )
        self.assertEqual(
            status["live_traffic"]["direct_fast_path_upstream"],
            "127.0.0.1:10443",
        )
        self.assertEqual(status["direct_fast_path"]["usage"]["total"], 0)
        self.assertEqual(status["direct_fast_path"]["usage"]["direct_upstream"], 0)
        self.assertEqual(status["direct_fast_path"]["usage"]["python_fallback"], 0)
        self.assertEqual(status["live_traffic"]["direct_fast_path_fallbacks"], 0)

    def test_status_reads_direct_fast_path_from_front_cmdline_when_env_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            front_pid_file = tmp_path / "front.pid"
            front_pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")

            cmdline = [
                "src/microproxy/build/hg-edge",
                "--relay",
                "--listen",
                "0.0.0.0:443",
                "--upstream",
                "127.0.0.1:9443",
                "--direct-upstream",
                "server.self-serve.windsurf.com:443",
                "--direct-hot-path",
                "--hot-path-observe",
            ]

            with mock.patch.object(
                self.proxy,
                "_microproxy_process_cmdline",
                return_value=cmdline,
            ), mock.patch.dict(
                os.environ,
                {
                    "HG_MICROPROXY_FRONT": "0",
                },
                clear=False,
            ):
                status = self.proxy._microproxy_status_summary(
                    tmp_path / "missing-events.jsonl",
                    tmp_path / "prototype.pid",
                    front_pid_file,
                )

        self.assertEqual(status["front"]["mode"], "c_front_active")
        self.assertTrue(status["front"]["enabled"])
        self.assertEqual(status["front"]["listen"], "0.0.0.0:443")
        self.assertEqual(status["front"]["upstream"], "127.0.0.1:9443")
        self.assertTrue(status["direct_fast_path"]["configured"])
        self.assertTrue(status["direct_fast_path"]["active"])
        self.assertEqual(status["direct_fast_path"]["target"], "server.self-serve.windsurf.com:443")
        self.assertTrue(status["live_traffic"]["direct_fast_path_hot_path"])
        self.assertTrue(status["live_traffic"]["direct_fast_path_hot_path_observe"])

    def test_status_reports_c_edge_direct_fast_path_state_and_canary(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            event_file = tmp_path / "microproxy_events.jsonl"
            event_file.write_text("", encoding="utf-8")
            front_pid_file = tmp_path / "front.pid"
            front_pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")

            mocked_summary = {
                "events": {name: 0 for name in events.EVENT_NAMES},
                "requests": {
                    "total": 0,
                    "request_seen": 0,
                    "routed": 0,
                    "stream_started": 0,
                    "stream_finished": 0,
                    "upstream_errors": 0,
                },
                "routes": {
                    "total": 0,
                    "routes": {},
                    "classifications": {},
                    "requests": {},
                },
                "streams": {
                    "streams_started": 0,
                    "streams_finished": 0,
                    "streams_open": 0,
                    "streams_finished_without_start": 0,
                    "open_stream_ids": [],
                    "finished_without_start_ids": [],
                    "status_codes": {},
                    "streams": {},
                },
                "upstream_errors": {
                    "total": 0,
                    "upstreams": {},
                    "error_types": {},
                    "requests": {},
                },
                "direct_fast_path": {
                    "state": "cooled_down",
                    "health_state": "degraded",
                    "target": "127.0.0.1:10443",
                    "usage": {
                        "total": 7,
                        "direct_upstream": 3,
                        "python_fallback": 2,
                        "passthrough": 2,
                        "fallbacks": 2,
                        "active": False,
                    },
                    "canary": {
                        "eligible": 4,
                        "selected": 1,
                    },
                },
            }

            with mock.patch.object(
                self.proxy,
                "summarize_observer_events",
                return_value=mocked_summary,
            ), mock.patch.object(
                self.proxy,
                "read_microproxy_events",
                return_value={"events": [], "invalid_rows": 0},
            ), mock.patch.dict(
                os.environ,
                {
                    "HG_MICROPROXY_FRONT": "1",
                    "HG_MICROPROXY_DIRECT_UPSTREAM": "127.0.0.1:10443",
                    "HG_MICROPROXY_DIRECT_HOT_PATH": "1",
                },
            ):
                status = self.proxy._microproxy_status_summary(
                    event_file,
                    tmp_path / "prototype.pid",
                    front_pid_file,
                )

        self.assertTrue(status["direct_fast_path"]["configured"])
        self.assertFalse(status["direct_fast_path"]["active"])
        self.assertTrue(status["direct_fast_path"]["cooled_down"])
        self.assertEqual(status["direct_fast_path"]["state"], "cooled_down")
        self.assertEqual(status["direct_fast_path"]["health_state"], "degraded")
        self.assertEqual(status["direct_fast_path"]["target"], "127.0.0.1:10443")
        self.assertEqual(status["direct_fast_path"]["usage"]["total"], 7)
        self.assertEqual(status["direct_fast_path"]["usage"]["direct_upstream"], 3)
        self.assertEqual(status["direct_fast_path"]["usage"]["python_fallback"], 2)
        self.assertEqual(status["direct_fast_path"]["usage"]["passthrough"], 2)
        self.assertEqual(status["direct_fast_path"]["canary"], {
            "eligible": 4,
            "selected": 1,
        })
        self.assertEqual(status["live_traffic"]["direct_fast_path_state"], "cooled_down")
        self.assertEqual(
            status["live_traffic"]["direct_fast_path_health_state"],
            "degraded",
        )
        self.assertEqual(status["live_traffic"]["direct_fast_path_fallbacks"], 2)
        self.assertEqual(
            status["live_traffic"]["direct_fast_path_canary"],
            {
                "eligible": 4,
                "selected": 1,
            },
        )

    def test_status_reports_direct_fast_path_usage_from_route_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            event_file = tmp_path / "microproxy_events.jsonl"
            front_pid_file = tmp_path / "front.pid"
            front_pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")
            event_file.write_text(
                events.event_to_jsonl(
                    events.make_event(
                        "route_selected",
                        "req-1",
                        {"route": "direct_upstream", "classification": "chat_completion"},
                        ts="2026-05-11T10:00:00.000Z",
                    )
                )
                + events.event_to_jsonl(
                    events.make_event(
                        "route_selected",
                        "req-2",
                        {"route": "python_fallback", "classification": "chat_completion"},
                        ts="2026-05-11T10:00:01.000Z",
                    )
                )
                + events.event_to_jsonl(
                    events.make_event(
                        "route_selected",
                        "req-3",
                        {"route": "passthrough", "classification": "unknown"},
                        ts="2026-05-11T10:00:02.000Z",
                    )
                ),
                encoding="utf-8",
            )

            with mock.patch.dict(
                os.environ,
                {
                    "HG_MICROPROXY_FRONT": "1",
                    "HG_MICROPROXY_DIRECT_UPSTREAM": "127.0.0.1:10443",
                    "HG_MICROPROXY_DIRECT_HOT_PATH": "1",
                },
            ):
                status = self.proxy._microproxy_status_summary(
                    event_file,
                    tmp_path / "prototype.pid",
                    front_pid_file,
                )

        self.assertEqual(status["direct_fast_path"]["usage"]["total"], 3)
        self.assertEqual(status["direct_fast_path"]["usage"]["direct_upstream"], 1)
        self.assertEqual(status["direct_fast_path"]["usage"]["python_fallback"], 1)
        self.assertEqual(status["direct_fast_path"]["usage"]["passthrough"], 1)
        self.assertTrue(status["direct_fast_path"]["usage"]["active"])

    def test_stale_pid_file_does_not_report_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "microproxy.pid"
            pid_file.write_text("not-a-pid\n", encoding="utf-8")

            pid_status = self.proxy._microproxy_pid_status(pid_file)

        self.assertTrue(pid_status["pid_file_exists"])
        self.assertFalse(pid_status["running"])
        self.assertTrue(pid_status["stale"])

    def test_status_endpoint_is_registered_read_only_get(self):
        routes = {
            route.path: route
            for route in self.proxy.app.routes
            if hasattr(route, "methods")
        }

        self.assertIn("/hg/microproxy/status", routes)
        self.assertEqual(routes["/hg/microproxy/status"].methods, {"GET"})


if __name__ == "__main__":
    unittest.main()
