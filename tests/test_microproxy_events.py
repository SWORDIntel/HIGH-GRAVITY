#!/usr/bin/env python3
"""Tests for passive microproxy event schema helpers."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


def _load_events_module():
    repo_root = Path(__file__).resolve().parent.parent
    events_path = repo_root / "src" / "microproxy" / "events.py"
    spec = importlib.util.spec_from_file_location(
        "microproxy_events_for_tests",
        events_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MicroproxyEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = _load_events_module()

    def test_make_event_builds_valid_envelope(self):
        event = self.events.make_event(
            "request_seen",
            "req-1",
            {"method": "POST", "path": "/v1/chat/completions"},
            connection_id="conn-1",
            sequence=1,
            ts="2026-05-11T10:00:00.000Z",
        )

        self.assertEqual(event["schema_version"], 1)
        self.assertEqual(event["event"], "request_seen")
        self.assertEqual(event["request_id"], "req-1")
        self.assertEqual(event["details"]["method"], "POST")
        self.assertEqual(event["connection_id"], "conn-1")

    def test_validate_event_rejects_unknown_event(self):
        with self.assertRaisesRegex(
            self.events.EventValidationError,
            "unsupported event",
        ):
            self.events.validate_event({
                "schema_version": 1,
                "event": "request_complete",
                "ts": "2026-05-11T10:00:00.000Z",
                "request_id": "req-1",
                "details": {},
            })

    def test_validate_event_rejects_unsupported_schema_version(self):
        with self.assertRaisesRegex(
            self.events.EventValidationError,
            "unsupported schema_version",
        ):
            self.events.validate_event({
                "schema_version": 2,
                "event": "request_seen",
                "ts": "2026-05-11T10:00:00.000Z",
                "request_id": "req-1",
                "details": {
                    "method": "POST",
                    "path": "/v1/chat/completions",
                },
            })

    def test_validate_event_rejects_missing_event_specific_detail(self):
        with self.assertRaisesRegex(
            self.events.EventValidationError,
            "status_code",
        ):
            self.events.make_event(
                "stream_finished",
                "req-1",
                {"stream_id": "stream-1"},
                ts="2026-05-11T10:00:00.000Z",
            )

    def test_append_and_iter_events_round_trip_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            first = self.events.make_event(
                "route_selected",
                "req-1",
                {"route": "passthrough"},
                ts="2026-05-11T10:00:00.000Z",
            )
            second = self.events.make_event(
                "upstream_error",
                "req-1",
                {
                    "upstream": "openai",
                    "error_type": "timeout",
                    "message": "timed out",
                },
                ts="2026-05-11T10:00:01.000Z",
            )

            self.events.append_event(path, first)
            self.events.append_event(path, second)

            self.assertEqual(
                list(self.events.iter_events(path)),
                [first, second],
            )
            self.assertEqual(
                self.events.summarize_events(
                    self.events.iter_events(path)
                )["upstream_error"],
                1,
            )

    def test_iter_events_can_skip_invalid_rows_for_tailers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                '{"not":"valid"}\n'
                + self.events.event_to_jsonl(
                    self.events.make_event(
                        "proto_observed",
                        "req-1",
                        {"proto": "grpc"},
                        ts="2026-05-11T10:00:00.000Z",
                    )
                ),
                encoding="utf-8",
            )

            rows = list(self.events.iter_events(path, skip_invalid=True))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event"], "proto_observed")

    def test_summarize_routes_counts_routes_and_classifications(self):
        rows = [
            self.events.make_event(
                "route_selected",
                "req-1",
                {"route": "passthrough", "classification": "direct"},
                ts="2026-05-11T10:00:00.000Z",
            ),
            self.events.make_event(
                "route_selected",
                "req-2",
                {"route": "mutating", "route_class": "augmented"},
                ts="2026-05-11T10:00:01.000Z",
            ),
            self.events.make_event(
                "route_selected",
                "req-3",
                {"route": "passthrough"},
                ts="2026-05-11T10:00:02.000Z",
            ),
        ]

        summary = self.events.summarize_routes(rows)

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["routes"], {
            "mutating": 1,
            "passthrough": 2,
        })
        self.assertEqual(summary["classifications"], {
            "augmented": 1,
            "direct": 1,
            "passthrough": 1,
        })
        self.assertEqual(summary["requests"]["req-2"], {
            "route": "mutating",
            "classification": "augmented",
        })

    def test_summarize_stream_lifecycle_tracks_open_and_finished_streams(self):
        rows = [
            self.events.make_event(
                "stream_started",
                "req-1",
                {"stream_id": "stream-1"},
                ts="2026-05-11T10:00:00.000Z",
            ),
            self.events.make_event(
                "stream_finished",
                "req-1",
                {"stream_id": "stream-1", "status_code": 200},
                ts="2026-05-11T10:00:01.250Z",
            ),
            self.events.make_event(
                "stream_started",
                "req-2",
                {"stream_id": "stream-2"},
                ts="2026-05-11T10:00:02.000Z",
            ),
            self.events.make_event(
                "stream_finished",
                "req-3",
                {"stream_id": "stream-3", "status_code": 502},
                ts="2026-05-11T10:00:03.000Z",
            ),
        ]

        summary = self.events.summarize_stream_lifecycle(rows)

        self.assertEqual(summary["streams_started"], 2)
        self.assertEqual(summary["streams_finished"], 2)
        self.assertEqual(summary["streams_open"], 1)
        self.assertEqual(summary["streams_finished_without_start"], 1)
        self.assertEqual(summary["open_stream_ids"], ["stream-2"])
        self.assertEqual(
            summary["finished_without_start_ids"],
            ["stream-3"],
        )
        self.assertEqual(summary["status_codes"], {"200": 1, "502": 1})
        self.assertEqual(
            summary["streams"]["stream-1"]["duration_ms"],
            1250,
        )

    def test_summarize_observer_events_combines_passive_summaries(self):
        rows = [
            self.events.make_event(
                "request_seen",
                "req-1",
                {"method": "POST", "path": "/v1/messages"},
                ts="2026-05-11T10:00:00.000Z",
            ),
            self.events.make_event(
                "route_selected",
                "req-1",
                {"route": "passthrough"},
                ts="2026-05-11T10:00:00.010Z",
            ),
            self.events.make_event(
                "stream_started",
                "req-1",
                {"stream_id": "stream-1"},
                ts="2026-05-11T10:00:00.020Z",
            ),
            self.events.make_event(
                "stream_finished",
                "req-1",
                {"stream_id": "stream-1", "status_code": 200},
                ts="2026-05-11T10:00:00.030Z",
            ),
            self.events.make_event(
                "upstream_error",
                "req-2",
                {
                    "upstream": "openai",
                    "error_type": "timeout",
                    "message": "timed out",
                },
                ts="2026-05-11T10:00:01.000Z",
            ),
            self.events.make_event(
                "backpressure",
                "req-3",
                {
                    "active_streams": 48,
                    "max_active_streams": 48,
                    "wait_ms": 1000,
                },
                ts="2026-05-11T10:00:02.000Z",
            ),
        ]

        summary = self.events.summarize_observer_events(rows)

        self.assertEqual(summary["events"]["request_seen"], 1)
        self.assertEqual(summary["events"]["upstream_error"], 1)
        self.assertEqual(summary["requests"]["total"], 3)
        self.assertEqual(summary["requests"]["stream_finished"], 1)
        self.assertEqual(summary["requests"]["upstream_errors"], 1)
        self.assertEqual(summary["routes"]["routes"], {"passthrough": 1})
        self.assertEqual(summary["streams"]["streams_finished"], 1)
        self.assertEqual(
            summary["upstream_errors"]["upstreams"],
            {"openai": 1},
        )
        self.assertEqual(
            summary["upstream_errors"]["error_types"],
            {"timeout": 1},
        )
        self.assertEqual(summary["backpressure"]["total"], 1)
        self.assertEqual(summary["backpressure"]["max_active_seen"], 48)
        self.assertEqual(summary["backpressure"]["wait_ms_total"], 1000)

    def test_read_events_reports_skipped_invalid_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                self.events.event_to_jsonl(
                    self.events.make_event(
                        "request_seen",
                        "req-1",
                        {"method": "GET", "path": "/health"},
                        ts="2026-05-11T10:00:00.000Z",
                    )
                )
                + '{"bad": "row"}\n'
                + self.events.event_to_jsonl(
                    self.events.make_event(
                        "stream_finished",
                        "req-1",
                        {"stream_id": "stream-1", "status_code": 204},
                        ts="2026-05-11T10:00:01.000Z",
                    )
                ),
                encoding="utf-8",
            )

            result = self.events.read_events(path, skip_invalid=True)

        self.assertEqual(result["invalid_rows"], 1)
        self.assertEqual(len(result["events"]), 2)

    def test_reader_cli_json_includes_control_plane_summary(self):
        repo_root = Path(__file__).resolve().parent.parent
        tool = repo_root / "tools" / "read_microproxy_events.py"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                self.events.event_to_jsonl(
                    self.events.make_event(
                        "route_selected",
                        "req-1",
                        {
                            "route": "passthrough",
                            "classification": "direct",
                        },
                        ts="2026-05-11T10:00:00.000Z",
                    )
                )
                + '{"bad": "row"}\n'
                + self.events.event_to_jsonl(
                    self.events.make_event(
                        "upstream_error",
                        "req-2",
                        {
                            "upstream": "openai",
                            "error_type": "timeout",
                            "message": "timed out",
                        },
                        ts="2026-05-11T10:00:01.000Z",
                    )
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(tool),
                    "--skip-invalid",
                    "--json",
                    str(path),
                ],
                cwd=repo_root,
                check=True,
                text=True,
                capture_output=True,
            )

        summary = json.loads(result.stdout)
        self.assertEqual(summary["reader"]["invalid_rows"], 1)
        self.assertEqual(summary["reader"]["rows"], 2)
        self.assertEqual(summary["requests"]["total"], 2)
        self.assertEqual(summary["routes"]["classifications"], {"direct": 1})
        self.assertEqual(summary["upstream_errors"]["total"], 1)

    def test_reader_cli_missing_ok_outputs_empty_summary(self):
        repo_root = Path(__file__).resolve().parent.parent
        tool = repo_root / "tools" / "read_microproxy_events.py"
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    str(tool),
                    "--missing-ok",
                    "--json",
                    str(missing),
                ],
                cwd=repo_root,
                check=True,
                text=True,
                capture_output=True,
            )

        summary = json.loads(result.stdout)
        self.assertFalse(summary["reader"]["source_exists"])
        self.assertEqual(summary["reader"]["rows"], 0)
        self.assertEqual(summary["requests"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
