import json
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "microproxy" / "hg_edge.c"


@unittest.skipUnless(shutil.which("cc"), "C compiler is required")
class MicroproxyEdgeBuildTests(unittest.TestCase):
    def build_edge(self, tmp_path):
        binary = tmp_path / "hg-edge"
        subprocess.run(
            [
                "cc",
                "-D_POSIX_C_SOURCE=200809L",
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-o",
                str(binary),
                str(SOURCE),
            ],
            check=True,
            cwd=ROOT,
        )
        return binary

    def read_events(self, event_log):
        if not event_log.exists():
            return []
        return [
            json.loads(line)
            for line in event_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def wait_for_events(self, event_log, expected_count, timeout=3):
        deadline = time.monotonic() + timeout
        events = []
        while time.monotonic() < deadline:
            events = self.read_events(event_log)
            if len(events) >= expected_count:
                return events
            time.sleep(0.05)
        return events

    def run_single_http_exchange(
        self,
        binary,
        tmp_path,
        request,
        extra_args=None,
        expected_events=4,
    ):
        event_log = tmp_path / "events.jsonl"
        upstream_ready = threading.Event()
        upstream_port_holder = []
        upstream_request_holder = []

        def run_http_server():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("127.0.0.1", 0))
                server.listen(1)
                upstream_port_holder.append(server.getsockname()[1])
                upstream_ready.set()
                conn, _ = server.accept()
                with conn:
                    data = conn.recv(4096)
                    upstream_request_holder.append(data)
                    conn.sendall(
                        b"HTTP/1.1 200 OK\r\n"
                        b"Content-Length: 0\r\n"
                        b"Connection: close\r\n"
                        b"\r\n"
                    )

        upstream_thread = threading.Thread(target=run_http_server)
        upstream_thread.start()
        self.assertTrue(upstream_ready.wait(timeout=2))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            relay_port = probe.getsockname()[1]

        args = [
            str(binary),
            "--relay",
            "--listen",
            f"127.0.0.1:{relay_port}",
            "--upstream",
            f"127.0.0.1:{upstream_port_holder[0]}",
            "--event-log",
            str(event_log),
            "--idle-timeout",
            "2",
        ]
        args.extend(extra_args or [])
        proc = subprocess.Popen(
            args,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            self.assertIn("relay listening", proc.stdout.readline())
            with socket.create_connection(("127.0.0.1", relay_port), timeout=2) as client:
                client.sendall(request)
                self.assertIn(b"200 OK", client.recv(4096))
            events = self.wait_for_events(event_log, expected_events)
        finally:
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate(timeout=3)

        self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
        upstream_thread.join(timeout=2)
        self.assertEqual(upstream_request_holder, [request])
        return events

    def test_edge_builds_and_prints_passive_flow(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            result = subprocess.run(
                [
                    str(binary),
                    "--check-config",
                    "--listen",
                    "127.0.0.1:18080",
                    "--upstream",
                    "127.0.0.1:8000",
                    "--max-active-streams",
                    "12",
                ],
                check=True,
                text=True,
                capture_output=True,
            )

        self.assertIn("Windsurf -> hg-edge", result.stdout)
        self.assertIn("Python proxy", result.stdout)
        self.assertIn("passive skeleton", result.stdout)
        self.assertIn("max-active-streams: 12", result.stdout)

    def test_relay_requires_explicit_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            result = subprocess.run(
                [str(binary), "--relay"],
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--relay requires explicit --listen and --upstream", result.stderr)

    def test_edge_rejects_invalid_ports(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            result = subprocess.run(
                [
                    str(binary),
                    "--check-config",
                    "--listen",
                    "127.0.0.1:0",
                    "--upstream",
                    "127.0.0.1:8000",
                ],
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid --listen", result.stderr)

    def test_relay_forwards_raw_tcp_bytes_on_localhost_high_ports(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            event_log = Path(tmp_dir) / "events.jsonl"
            upstream_ready = threading.Event()
            upstream_port_holder = []

            def run_echo_server():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(("127.0.0.1", 0))
                    server.listen(1)
                    upstream_port_holder.append(server.getsockname()[1])
                    upstream_ready.set()
                    conn, _addr = server.accept()
                    with conn:
                        while True:
                            data = conn.recv(4096)
                            if not data:
                                break
                            conn.sendall(data)

            upstream_thread = threading.Thread(target=run_echo_server, daemon=True)
            upstream_thread.start()
            self.assertTrue(upstream_ready.wait(2), "upstream echo server did not start")
            upstream_port = upstream_port_holder[0]

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                relay_port = probe.getsockname()[1]

            proc = subprocess.Popen(
                [
                    str(binary),
                    "--relay",
                    "--listen",
                    f"127.0.0.1:{relay_port}",
                    "--upstream",
                    f"127.0.0.1:{upstream_port}",
                    "--idle-timeout",
                    "2",
                    "--event-log",
                    str(event_log),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                ready_line = proc.stdout.readline()
                self.assertIn("relay listening", ready_line)

                with socket.create_connection(("127.0.0.1", relay_port), timeout=2) as client:
                    client.sendall(b"high-gravity-relay")
                    self.assertEqual(client.recv(4096), b"high-gravity-relay")

                events = self.wait_for_events(event_log, 2)
            finally:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate(timeout=3)

            self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
            upstream_thread.join(timeout=2)
            self.assertEqual(
                [event["event"] for event in events],
                ["stream_started", "stream_finished"],
            )
            self.assertEqual(events[0]["schema_version"], 1)
            self.assertEqual(events[0]["stream_id"], events[1]["stream_id"])
            self.assertEqual(events[1]["listen"], f"127.0.0.1:{relay_port}")
            self.assertEqual(events[1]["upstream"], f"127.0.0.1:{upstream_port}")
            self.assertEqual(events[1]["details"]["bytes_in"], len(b"high-gravity-relay"))
            self.assertEqual(events[1]["details"]["bytes_out"], len(b"high-gravity-relay"))
            self.assertEqual(events[1]["details"]["status_code"], 0)
            self.assertIsInstance(events[1]["details"]["duration_ms"], int)

    def test_relay_sniffs_plaintext_http_request_events_without_mutating_bytes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            event_log = Path(tmp_dir) / "events.jsonl"
            upstream_ready = threading.Event()
            upstream_port_holder = []
            upstream_request_holder = []

            def run_http_server():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(("127.0.0.1", 0))
                    server.listen(1)
                    upstream_port_holder.append(server.getsockname()[1])
                    upstream_ready.set()
                    conn, _addr = server.accept()
                    with conn:
                        data = conn.recv(4096)
                        upstream_request_holder.append(data)
                        conn.sendall(
                            b"HTTP/1.1 200 OK\r\n"
                            b"Content-Length: 2\r\n"
                            b"Connection: close\r\n"
                            b"\r\n"
                            b"ok"
                        )

            upstream_thread = threading.Thread(target=run_http_server, daemon=True)
            upstream_thread.start()
            self.assertTrue(upstream_ready.wait(2), "upstream HTTP server did not start")
            upstream_port = upstream_port_holder[0]

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                relay_port = probe.getsockname()[1]

            proc = subprocess.Popen(
                [
                    str(binary),
                    "--relay",
                    "--listen",
                    f"127.0.0.1:{relay_port}",
                    "--upstream",
                    f"127.0.0.1:{upstream_port}",
                    "--idle-timeout",
                    "2",
                    "--event-log",
                    str(event_log),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                ready_line = proc.stdout.readline()
                self.assertIn("relay listening", ready_line)

                request = (
                    b"POST /v1/messages HTTP/1.1\r\n"
                    b"Host: api.anthropic.test\r\n"
                    b"Content-Length: 0\r\n"
                    b"\r\n"
                )
                with socket.create_connection(("127.0.0.1", relay_port), timeout=2) as client:
                    client.sendall(request)
                    self.assertIn(b"200 OK", client.recv(4096))

                events = self.wait_for_events(event_log, 4)
            finally:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate(timeout=3)

            self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
            upstream_thread.join(timeout=2)
            self.assertEqual(upstream_request_holder, [request])
            self.assertEqual(
                [event["event"] for event in events],
                ["stream_started", "request_seen", "route_selected", "stream_finished"],
            )
            self.assertEqual(events[1]["details"]["method"], "POST")
            self.assertEqual(events[1]["details"]["path"], "/v1/messages")
            self.assertEqual(events[1]["details"]["host"], "api.anthropic.test")
            self.assertEqual(events[1]["details"]["classification"], "chat_completion")
            self.assertEqual(events[2]["details"]["route"], "passthrough")
            self.assertEqual(events[2]["details"]["classification"], "chat_completion")

    def test_relay_classifies_openai_compatible_plaintext_routes_as_chat_completion(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            event_log = Path(tmp_dir) / "events.jsonl"
            upstream_ready = threading.Event()
            upstream_port_holder = []

            def run_http_server():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(("127.0.0.1", 0))
                    server.listen(1)
                    upstream_port_holder.append(server.getsockname()[1])
                    upstream_ready.set()
                    conn, _addr = server.accept()
                    with conn:
                        conn.recv(4096)
                        conn.sendall(b"HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n")

            upstream_thread = threading.Thread(target=run_http_server, daemon=True)
            upstream_thread.start()
            self.assertTrue(upstream_ready.wait(2), "upstream HTTP server did not start")
            upstream_port = upstream_port_holder[0]

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                relay_port = probe.getsockname()[1]

            proc = subprocess.Popen(
                [
                    str(binary),
                    "--relay",
                    "--listen",
                    f"127.0.0.1:{relay_port}",
                    "--upstream",
                    f"127.0.0.1:{upstream_port}",
                    "--idle-timeout",
                    "2",
                    "--event-log",
                    str(event_log),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                ready_line = proc.stdout.readline()
                self.assertIn("relay listening", ready_line)

                with socket.create_connection(("127.0.0.1", relay_port), timeout=2) as client:
                    client.sendall(
                        b"POST /v1/chat/completions HTTP/1.1\r\n"
                        b"Host: local-compatible.test\r\n"
                        b"Content-Length: 0\r\n"
                        b"\r\n"
                    )
                    self.assertIn(b"204 No Content", client.recv(4096))

                events = self.wait_for_events(event_log, 4)
            finally:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate(timeout=3)

            self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
            upstream_thread.join(timeout=2)
            self.assertEqual(events[1]["details"]["classification"], "chat_completion")
            self.assertEqual(events[2]["details"]["route"], "passthrough")

    def test_relay_classifies_windsurf_get_chat_message_as_chat_completion(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            event_log = Path(tmp_dir) / "events.jsonl"
            upstream_ready = threading.Event()
            upstream_port_holder = []

            def run_http_server():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(("127.0.0.1", 0))
                    server.listen(1)
                    upstream_port_holder.append(server.getsockname()[1])
                    upstream_ready.set()
                    conn, _ = server.accept()
                    with conn:
                        conn.recv(4096)
                        conn.sendall(
                            b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
                        )

            upstream_thread = threading.Thread(target=run_http_server)
            upstream_thread.start()
            self.assertTrue(upstream_ready.wait(timeout=2))
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                relay_port = probe.getsockname()[1]
            proc = subprocess.Popen(
                [
                    str(binary),
                    "--relay",
                    "--listen",
                    f"127.0.0.1:{relay_port}",
                    "--upstream",
                    f"127.0.0.1:{upstream_port_holder[0]}",
                    "--event-log",
                    str(event_log),
                    "--idle-timeout",
                    "2",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                self.assertIn("relay listening", proc.stdout.readline())
                request = (
                    b"POST /exa.api_server_pb.ApiServerService/GetChatMessage HTTP/1.1\r\n"
                    b"Host: proxy.windsurf.com\r\n"
                    b"Content-Length: 0\r\n"
                    b"\r\n"
                )
                with socket.create_connection(("127.0.0.1", relay_port), timeout=2) as client:
                    client.sendall(request)
                    self.assertIn(b"200 OK", client.recv(4096))
                events = self.wait_for_events(event_log, 4)
            finally:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate(timeout=3)

            self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
            upstream_thread.join(timeout=2)
            self.assertEqual(events[1]["details"]["classification"], "chat_completion")
            self.assertEqual(events[2]["details"]["route"], "passthrough")

    def test_relay_classifies_model_control_and_unknown_without_mutation(self):
        cases = [
            (
                "model_list",
                b"GET /v1/models HTTP/1.1\r\n"
                b"Host: api.openai.com\r\n"
                b"Content-Length: 0\r\n"
                b"\r\n",
            ),
            (
                "control",
                b"POST /telemetry/events HTTP/1.1\r\n"
                b"Host: telemetry.local\r\n"
                b"Content-Length: 0\r\n"
                b"\r\n",
            ),
            (
                "unknown",
                b"GET /static/logo.png HTTP/1.1\r\n"
                b"Host: local.test\r\n"
                b"Content-Length: 0\r\n"
                b"\r\n",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            for index, (expected_classification, request) in enumerate(cases):
                with self.subTest(classification=expected_classification):
                    case_dir = Path(tmp_dir) / f"{index}-{expected_classification}"
                    case_dir.mkdir()
                    events = self.run_single_http_exchange(
                        binary,
                        case_dir,
                        request,
                    )

                self.assertEqual(
                    [event["event"] for event in events],
                    [
                        "stream_started",
                        "request_seen",
                        "route_selected",
                        "stream_finished",
                    ],
                )
                self.assertEqual(
                    events[1]["details"]["classification"],
                    expected_classification,
                )
                self.assertEqual(
                    events[2]["details"]["route"],
                    "passthrough",
                )
                self.assertEqual(
                    events[2]["details"]["classification"],
                    expected_classification,
                )
                self.assertIn("reason", events[2]["details"])

    def test_hot_path_observe_marks_windsurf_connect_proto_candidate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            event_log = Path(tmp_dir) / "events.jsonl"
            upstream_ready = threading.Event()
            upstream_port_holder = []

            def run_http_server():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(("127.0.0.1", 0))
                    server.listen(1)
                    upstream_port_holder.append(server.getsockname()[1])
                    upstream_ready.set()
                    conn, _ = server.accept()
                    with conn:
                        conn.recv(4096)
                        conn.sendall(
                            b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
                        )

            upstream_thread = threading.Thread(target=run_http_server)
            upstream_thread.start()
            self.assertTrue(upstream_ready.wait(timeout=2))
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                relay_port = probe.getsockname()[1]
            proc = subprocess.Popen(
                [
                    str(binary),
                    "--relay",
                    "--listen",
                    f"127.0.0.1:{relay_port}",
                    "--upstream",
                    f"127.0.0.1:{upstream_port_holder[0]}",
                    "--event-log",
                    str(event_log),
                    "--idle-timeout",
                    "2",
                    "--hot-path-observe",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                self.assertIn("relay listening", proc.stdout.readline())
                request = (
                    b"POST /exa.api_server_pb.ApiServerService/GetChatMessage HTTP/1.1\r\n"
                    b"Host: proxy.windsurf.com\r\n"
                    b"Content-Type: application/connect+proto\r\n"
                    b"Content-Length: 5\r\n"
                    b"\r\n"
                    b"\x00\x00\x00\x00\x00"
                )
                with socket.create_connection(("127.0.0.1", relay_port), timeout=2) as client:
                    client.sendall(request)
                    self.assertIn(b"200 OK", client.recv(4096))
                events = self.wait_for_events(event_log, 5)
            finally:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate(timeout=3)

            self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
            upstream_thread.join(timeout=2)
            self.assertEqual(
                [event["event"] for event in events],
                [
                    "stream_started",
                    "request_seen",
                    "route_selected",
                    "hot_path_candidate",
                    "stream_finished",
                ],
            )
            self.assertEqual(events[3]["details"]["candidate"], "windsurf_get_chat_message")
            self.assertEqual(events[3]["details"]["route"], "passthrough")
            self.assertEqual(events[3]["details"]["method"], "POST")
            self.assertEqual(
                events[3]["details"]["path"],
                "/exa.api_server_pb.ApiServerService/GetChatMessage",
            )
            self.assertEqual(events[3]["details"]["host"], "proxy.windsurf.com")
            self.assertEqual(
                events[3]["details"]["content_type"],
                "application/connect+proto",
            )

    def test_hot_path_candidate_is_disabled_without_explicit_flag(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            event_log = Path(tmp_dir) / "events.jsonl"
            upstream_ready = threading.Event()
            upstream_port_holder = []

            def run_http_server():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(("127.0.0.1", 0))
                    server.listen(1)
                    upstream_port_holder.append(server.getsockname()[1])
                    upstream_ready.set()
                    conn, _ = server.accept()
                    with conn:
                        conn.recv(4096)
                        conn.sendall(
                            b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
                        )

            upstream_thread = threading.Thread(target=run_http_server)
            upstream_thread.start()
            self.assertTrue(upstream_ready.wait(timeout=2))
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                relay_port = probe.getsockname()[1]
            proc = subprocess.Popen(
                [
                    str(binary),
                    "--relay",
                    "--listen",
                    f"127.0.0.1:{relay_port}",
                    "--upstream",
                    f"127.0.0.1:{upstream_port_holder[0]}",
                    "--event-log",
                    str(event_log),
                    "--idle-timeout",
                    "2",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                self.assertIn("relay listening", proc.stdout.readline())
                request = (
                    b"POST /exa.api_server_pb.ApiServerService/GetChatMessage HTTP/1.1\r\n"
                    b"Host: proxy.windsurf.com\r\n"
                    b"Content-Type: application/connect+proto\r\n"
                    b"Content-Length: 0\r\n"
                    b"\r\n"
                )
                with socket.create_connection(("127.0.0.1", relay_port), timeout=2) as client:
                    client.sendall(request)
                    self.assertIn(b"200 OK", client.recv(4096))
                events = self.wait_for_events(event_log, 4)
            finally:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate(timeout=3)

            self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
            upstream_thread.join(timeout=2)
            self.assertNotIn("hot_path_candidate", [event["event"] for event in events])

    def test_direct_hot_path_routes_candidate_to_direct_upstream(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            event_log = Path(tmp_dir) / "events.jsonl"
            primary_ready = threading.Event()
            direct_ready = threading.Event()
            primary_port_holder = []
            direct_port_holder = []
            primary_requests = []
            direct_requests = []

            def run_one_server(ready, port_holder, requests, response):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(("127.0.0.1", 0))
                    server.listen(1)
                    server.settimeout(3)
                    port_holder.append(server.getsockname()[1])
                    ready.set()
                    try:
                        conn, _ = server.accept()
                    except socket.timeout:
                        return
                    with conn:
                        data = conn.recv(4096)
                        requests.append(data)
                        conn.sendall(response)

            primary_thread = threading.Thread(
                target=run_one_server,
                args=(
                    primary_ready,
                    primary_port_holder,
                    primary_requests,
                    b"HTTP/1.1 599 Primary\r\nContent-Length: 0\r\n\r\n",
                ),
            )
            direct_thread = threading.Thread(
                target=run_one_server,
                args=(
                    direct_ready,
                    direct_port_holder,
                    direct_requests,
                    b"HTTP/1.1 200 Direct\r\nContent-Length: 0\r\n\r\n",
                ),
            )
            primary_thread.start()
            direct_thread.start()
            self.assertTrue(primary_ready.wait(timeout=2))
            self.assertTrue(direct_ready.wait(timeout=2))

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                relay_port = probe.getsockname()[1]

            proc = subprocess.Popen(
                [
                    str(binary),
                    "--relay",
                    "--listen",
                    f"127.0.0.1:{relay_port}",
                    "--upstream",
                    f"127.0.0.1:{primary_port_holder[0]}",
                    "--direct-upstream",
                    f"127.0.0.1:{direct_port_holder[0]}",
                    "--direct-hot-path",
                    "--hot-path-observe",
                    "--event-log",
                    str(event_log),
                    "--idle-timeout",
                    "2",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                self.assertIn("relay listening", proc.stdout.readline())
                request = (
                    b"POST /exa.api_server_pb.ApiServerService/GetChatMessage HTTP/1.1\r\n"
                    b"Host: proxy.windsurf.com\r\n"
                    b"Content-Type: application/connect+proto\r\n"
                    b"Content-Length: 5\r\n"
                    b"\r\n"
                    b"\x00\x00\x00\x00\x00"
                )
                with socket.create_connection(("127.0.0.1", relay_port), timeout=2) as client:
                    client.sendall(request)
                    self.assertIn(b"200 Direct", client.recv(4096))
                events = self.wait_for_events(event_log, 5)
            finally:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate(timeout=3)

            self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
            primary_thread.join(timeout=4)
            direct_thread.join(timeout=2)
            self.assertEqual(primary_requests, [])
            self.assertEqual(direct_requests, [request])
            self.assertIn("hot_path_candidate", [event["event"] for event in events])
            route_event = next(event for event in events if event["event"] == "route_selected")
            self.assertEqual(route_event["details"]["route"], "direct_upstream")
            self.assertEqual(route_event["details"]["classification"], "chat_completion")

    def test_direct_hot_path_falls_back_to_python_upstream_when_direct_connect_fails(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            event_log = Path(tmp_dir) / "events.jsonl"
            primary_ready = threading.Event()
            primary_port_holder = []
            primary_requests = []

            def run_primary_server():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(("127.0.0.1", 0))
                    server.listen(1)
                    primary_port_holder.append(server.getsockname()[1])
                    primary_ready.set()
                    conn, _ = server.accept()
                    with conn:
                        data = conn.recv(4096)
                        primary_requests.append(data)
                        conn.sendall(b"HTTP/1.1 200 Fallback\r\nContent-Length: 0\r\n\r\n")

            primary_thread = threading.Thread(target=run_primary_server)
            primary_thread.start()
            self.assertTrue(primary_ready.wait(timeout=2))

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                relay_port = probe.getsockname()[1]
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                direct_dead_port = probe.getsockname()[1]

            proc = subprocess.Popen(
                [
                    str(binary),
                    "--relay",
                    "--listen",
                    f"127.0.0.1:{relay_port}",
                    "--upstream",
                    f"127.0.0.1:{primary_port_holder[0]}",
                    "--direct-upstream",
                    f"127.0.0.1:{direct_dead_port}",
                    "--direct-hot-path",
                    "--hot-path-observe",
                    "--event-log",
                    str(event_log),
                    "--idle-timeout",
                    "2",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                self.assertIn("relay listening", proc.stdout.readline())
                request = (
                    b"POST /exa.api_server_pb.ApiServerService/GetChatMessage HTTP/1.1\r\n"
                    b"Host: proxy.windsurf.com\r\n"
                    b"Content-Type: application/connect+proto\r\n"
                    b"Content-Length: 5\r\n"
                    b"\r\n"
                    b"\x00\x00\x00\x00\x00"
                )
                with socket.create_connection(("127.0.0.1", relay_port), timeout=2) as client:
                    client.sendall(request)
                    self.assertIn(b"200 Fallback", client.recv(4096))
                events = self.wait_for_events(event_log, 7)
            finally:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate(timeout=3)

            self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
            primary_thread.join(timeout=2)
            self.assertEqual(primary_requests, [request])
            routes = [
                event["details"]["route"]
                for event in events
                if event["event"] == "route_selected"
            ]
            self.assertIn("direct_upstream", routes)
            self.assertIn("python_fallback", routes)
            errors = [event for event in events if event["event"] == "upstream_error"]
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]["details"]["upstream"], f"127.0.0.1:{direct_dead_port}")

    def test_direct_hot_path_trips_cooldown_after_repeated_connect_failures(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            event_log = Path(tmp_dir) / "events.jsonl"
            primary_ready = threading.Event()
            primary_port_holder = []
            primary_requests = []

            def run_primary_server():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(("127.0.0.1", 0))
                    server.listen(3)
                    server.settimeout(3)
                    primary_port_holder.append(server.getsockname()[1])
                    primary_ready.set()
                    for _ in range(3):
                        try:
                            conn, _ = server.accept()
                        except socket.timeout:
                            return
                        with conn:
                            data = conn.recv(4096)
                            primary_requests.append(data)
                            conn.sendall(b"HTTP/1.1 200 Fallback\r\nContent-Length: 0\r\n\r\n")

            primary_thread = threading.Thread(target=run_primary_server)
            primary_thread.start()
            self.assertTrue(primary_ready.wait(timeout=2))

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                relay_port = probe.getsockname()[1]
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                direct_dead_port = probe.getsockname()[1]

            proc = subprocess.Popen(
                [
                    str(binary),
                    "--relay",
                    "--listen",
                    f"127.0.0.1:{relay_port}",
                    "--upstream",
                    f"127.0.0.1:{primary_port_holder[0]}",
                    "--direct-upstream",
                    f"127.0.0.1:{direct_dead_port}",
                    "--direct-hot-path",
                    "--hot-path-observe",
                    "--event-log",
                    str(event_log),
                    "--idle-timeout",
                    "2",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                self.assertIn("relay listening", proc.stdout.readline())
                request = (
                    b"POST /exa.api_server_pb.ApiServerService/GetChatMessage HTTP/1.1\r\n"
                    b"Host: proxy.windsurf.com\r\n"
                    b"Content-Type: application/connect+proto\r\n"
                    b"Content-Length: 5\r\n"
                    b"\r\n"
                    b"\x00\x00\x00\x00\x00"
                )
                for _ in range(3):
                    with socket.create_connection(("127.0.0.1", relay_port), timeout=2) as client:
                        client.sendall(request)
                        self.assertIn(b"200 Fallback", client.recv(4096))
                events = self.wait_for_events(event_log, 19)
            finally:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate(timeout=3)

            self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
            primary_thread.join(timeout=4)
            self.assertEqual(primary_requests, [request, request, request])

            error_events = [event for event in events if event["event"] == "upstream_error"]
            self.assertEqual(len(error_events), 2)
            self.assertEqual(error_events[0]["details"]["direct_failure_count"], 1)
            self.assertFalse(error_events[0]["details"]["direct_cooldown_active"])
            self.assertEqual(error_events[1]["details"]["direct_failure_count"], 2)
            self.assertTrue(error_events[1]["details"]["direct_cooldown_active"])
            self.assertGreater(error_events[1]["details"]["direct_cooldown_remaining_ms"], 0)

            route_events = [event for event in events if event["event"] == "route_selected"]
            stream_ids = sorted({event["stream_id"] for event in route_events})
            first_stream_routes = [event for event in route_events if event["stream_id"] == stream_ids[0]]
            second_stream_routes = [event for event in route_events if event["stream_id"] == stream_ids[1]]
            third_stream_routes = [event for event in route_events if event["stream_id"] == stream_ids[2]]

            self.assertEqual([event["details"]["route"] for event in first_stream_routes], ["direct_upstream", "python_fallback"])
            self.assertEqual(first_stream_routes[1]["details"]["fallback_state"], "direct_connect_failed")
            self.assertEqual([event["details"]["route"] for event in second_stream_routes], ["direct_upstream", "python_fallback"])
            self.assertEqual(second_stream_routes[1]["details"]["direct_failure_count"], 2)
            self.assertEqual([event["details"]["route"] for event in third_stream_routes], ["python_fallback"])
            self.assertEqual(third_stream_routes[0]["details"]["fallback_state"], "direct_upstream_cooldown")
            self.assertTrue(third_stream_routes[0]["details"]["direct_cooldown_active"])
            self.assertGreater(third_stream_routes[0]["details"]["direct_cooldown_remaining_ms"], 0)

    def test_hot_path_observe_does_not_mark_control_proto_requests(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            events = self.run_single_http_exchange(
                binary,
                Path(tmp_dir),
                (
                    b"POST /auth/token HTTP/1.1\r\n"
                    b"Host: proxy.windsurf.com\r\n"
                    b"Content-Type: application/connect+proto\r\n"
                    b"Content-Length: 0\r\n"
                    b"\r\n"
                ),
                extra_args=["--hot-path-observe"],
            )

        self.assertNotIn("hot_path_candidate", [event["event"] for event in events])
        self.assertEqual(events[1]["details"]["classification"], "auth")
        self.assertEqual(events[2]["details"]["route"], "passthrough")

    def test_relay_emits_upstream_error_when_connect_fails(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            event_log = Path(tmp_dir) / "events.jsonl"

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                relay_port = probe.getsockname()[1]

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                upstream_port = probe.getsockname()[1]

            proc = subprocess.Popen(
                [
                    str(binary),
                    "--relay",
                    "--listen",
                    f"127.0.0.1:{relay_port}",
                    "--upstream",
                    f"127.0.0.1:{upstream_port}",
                    "--idle-timeout",
                    "2",
                    "--event-log",
                    str(event_log),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                ready_line = proc.stdout.readline()
                self.assertIn("relay listening", ready_line)

                with socket.create_connection(("127.0.0.1", relay_port), timeout=2):
                    pass

                events = self.wait_for_events(event_log, 1)
            finally:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate(timeout=3)

            self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["event"], "upstream_error")
            self.assertEqual(events[0]["schema_version"], 1)
            self.assertEqual(events[0]["listen"], f"127.0.0.1:{relay_port}")
            self.assertEqual(events[0]["upstream"], f"127.0.0.1:{upstream_port}")
            self.assertEqual(events[0]["details"]["upstream"], f"127.0.0.1:{upstream_port}")
            self.assertEqual(events[0]["details"]["error_type"], "connect_failed")

    def test_relay_reaps_finished_children_before_enforcing_active_stream_cap(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary = self.build_edge(Path(tmp_dir))
            event_log = Path(tmp_dir) / "events.jsonl"
            upstream_ready = threading.Event()
            upstream_port_holder = []

            def run_http_server():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind(("127.0.0.1", 0))
                    server.listen(2)
                    upstream_port_holder.append(server.getsockname()[1])
                    upstream_ready.set()
                    for _ in range(2):
                        conn, _ = server.accept()
                        with conn:
                            conn.recv(4096)
                            conn.sendall(
                                b"HTTP/1.1 200 OK\r\n"
                                b"Content-Length: 0\r\n"
                                b"Connection: close\r\n"
                                b"\r\n"
                            )

            upstream_thread = threading.Thread(target=run_http_server)
            upstream_thread.start()
            self.assertTrue(upstream_ready.wait(timeout=2))
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", 0))
                relay_port = probe.getsockname()[1]

            proc = subprocess.Popen(
                [
                    str(binary),
                    "--relay",
                    "--listen",
                    f"127.0.0.1:{relay_port}",
                    "--upstream",
                    f"127.0.0.1:{upstream_port_holder[0]}",
                    "--max-active-streams",
                    "1",
                    "--idle-timeout",
                    "2",
                    "--event-log",
                    str(event_log),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                self.assertIn("relay listening", proc.stdout.readline())
                request = (
                    b"GET / HTTP/1.1\r\n"
                    b"Host: proxy.windsurf.com\r\n"
                    b"Content-Length: 0\r\n"
                    b"\r\n"
                )
                for _ in range(2):
                    with socket.create_connection(("127.0.0.1", relay_port), timeout=2) as client:
                        client.settimeout(2)
                        client.sendall(request)
                        self.assertIn(b"200 OK", client.recv(4096))
                    self.wait_for_events(event_log, 4, timeout=3)
                events = self.wait_for_events(event_log, 8, timeout=3)
            finally:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate(timeout=3)

            upstream_thread.join(timeout=2)
            self.assertIn(proc.returncode, (0, -15), msg=f"stdout={stdout!r} stderr={stderr!r}")
            self.assertEqual(
                sum(1 for event in events if event["event"] == "stream_finished"),
                2,
            )
            self.assertLessEqual(
                sum(1 for event in events if event["event"] == "backpressure"),
                2,
            )


if __name__ == "__main__":
    unittest.main()
