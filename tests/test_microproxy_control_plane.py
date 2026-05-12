"""Shell guardrails for disabled microproxy control-plane wiring."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_command(*args, **kwargs):
    return subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    )


class MicroproxyControlPlaneTests(unittest.TestCase):
    def test_microproxy_shell_entrypoints_parse(self):
        scripts = [
            ROOT / "hg.sh",
            ROOT / "scripts" / "internal" / "hg_microproxy.sh",
        ]

        for script in scripts:
            with self.subTest(script=script):
                result = run_command("bash", "-n", str(script))
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_microproxy_status_is_disabled_when_no_prototype_is_configured(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_dir = Path(tmp_dir) / "missing-microproxy"
            env = os.environ.copy()
            env["HG_MICROPROXY_DIR"] = str(missing_dir)

            result = run_command(
                "bash",
                "scripts/internal/hg_microproxy.sh",
                "status",
                env=env,
            )

        self.assertEqual(result.returncode, 3)
        self.assertIn("Prototype path: not configured", result.stdout)
        self.assertIn("Python proxy remains default", result.stdout)

    def test_hg_help_advertises_microproxy_without_start_stop_changes(self):
        hg_sh = (ROOT / "hg.sh").read_text()

        self.assertIn("microproxy", hg_sh)
        self.assertIn('exec bash "$SCRIPTS_DIR/internal/hg_microproxy.sh"', hg_sh)
        self.assertIn('exec bash "$SCRIPTS_DIR/internal/hg_start.sh" start', hg_sh)
        self.assertIn('exec bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct', hg_sh)

    def test_hg_status_reports_enabled_front_listener_failure(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            temp_root = tmp_path / "repo"
            status_script = temp_root / "scripts" / "internal" / "hg_status.sh"
            fake_bin = tmp_path / "bin"
            logs = temp_root / "logs"

            status_script.parent.mkdir(parents=True)
            logs.mkdir(parents=True)
            (temp_root / "certs").mkdir()
            (temp_root / "certs" / "proxy.crt").write_text("test\n")
            (temp_root / "certs" / "proxy.key").write_text("test\n")
            status_script.write_text(
                (ROOT / "scripts" / "internal" / "hg_status.sh").read_text()
            )
            (logs / "microproxy_front.pid").write_text(f"{os.getpid()}\n")
            fake_bin.mkdir()
            (fake_bin / "ss").write_text(
                "#!/usr/bin/env bash\n"
                "args=\"$*\"\n"
                "if [[ \"$args\" == *':9443'* ]]; then\n"
                "  echo 'State Recv-Q Send-Q Local Address:Port Peer Address:Port Process'\n"
                "  echo 'LISTEN 0 128 127.0.0.1:9443 0.0.0.0:* users:((\"python\",pid=222,fd=3))'\n"
                "fi\n"
            )
            (fake_bin / "ss").chmod(0o755)
            (fake_bin / "curl").write_text("#!/usr/bin/env bash\nexit 7\n")
            (fake_bin / "curl").chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{fake_bin}:{env['PATH']}",
                    "HG_MICROPROXY_FRONT": "1",
                    "HG_MICROPROXY_FRONT_LISTEN": "127.0.0.1:2443",
                    "HG_MICROPROXY_FRONT_UPSTREAM": "127.0.0.1:9443",
                    "HG_PROXY_INTERNAL_HTTPS_PORT": "9443",
                }
            )
            result = subprocess.run(
                ["bash", str(status_script), "--direct"],
                cwd=temp_root,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Proxy TLS:", result.stdout)
        self.assertIn("Port: 9443, internal", result.stdout)
        self.assertIn("C Front:", result.stdout)
        self.assertIn("RELAY PROCESS UP, LISTENER DOWN", result.stdout)
        self.assertIn("127.0.0.1:2443", result.stdout)
        self.assertIn("127.0.0.1:9443", result.stdout)

    def test_hg_status_reads_front_cmdline_for_direct_fast_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            temp_root = tmp_path / "repo"
            status_script = temp_root / "scripts" / "internal" / "hg_status.sh"
            fake_bin = tmp_path / "bin"
            logs = temp_root / "logs"

            status_script.parent.mkdir(parents=True)
            logs.mkdir(parents=True)
            (temp_root / "certs").mkdir()
            (temp_root / "certs" / "proxy.crt").write_text("test\n")
            (temp_root / "certs" / "proxy.key").write_text("test\n")
            status_script.write_text(
                (ROOT / "scripts" / "internal" / "hg_status.sh").read_text()
            )
            (logs / "microproxy_front.pid").write_text("4242\n")
            fake_bin.mkdir()
            (fake_bin / "ps").write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$*\" == *'-p 4242'* ]]; then\n"
                "  echo 'src/microproxy/build/hg-edge --relay --listen 0.0.0.0:443 --upstream 127.0.0.1:9443 --direct-upstream server.self-serve.windsurf.com:443 --direct-hot-path --hot-path-observe'\n"
                "fi\n"
            )
            (fake_bin / "ps").chmod(0o755)
            (fake_bin / "ss").write_text(
                "#!/usr/bin/env bash\n"
                "args=\"$*\"\n"
                "if [[ \"$args\" == *':9998'* ]]; then\n"
                "  echo 'State Recv-Q Send-Q Local Address:Port Peer Address:Port Process'\n"
                "  echo 'LISTEN 0 128 127.0.0.1:9998 0.0.0.0:* users:((\"python\",pid=111,fd=3))'\n"
                "elif [[ \"$args\" == *':9443'* ]]; then\n"
                "  echo 'State Recv-Q Send-Q Local Address:Port Peer Address:Port Process'\n"
                "  echo 'LISTEN 0 128 127.0.0.1:9443 0.0.0.0:* users:((\"python\",pid=222,fd=3))'\n"
                "elif [[ \"$args\" == *':443'* ]]; then\n"
                "  echo 'State Recv-Q Send-Q Local Address:Port Peer Address:Port Process'\n"
                "  echo 'LISTEN 0 128 0.0.0.0:443 0.0.0.0:* users:((\"hg-edge\",pid=4242,fd=3))'\n"
                "fi\n"
            )
            (fake_bin / "ss").chmod(0o755)
            (fake_bin / "curl").write_text(
                "#!/usr/bin/env bash\n"
                "cat <<'JSON'\n"
                "{\"reader\":{\"rows\":0,\"invalid_rows\":0},\"classifier\":{\"request_seen_by_class\":{},\"route_selected_by_class\":{}},\"fast_path_candidates\":{\"total\":0,\"by_class\":{},\"by_candidate\":{}},\"upstream_errors\":{\"total\":0,\"error_types\":{},\"upstreams\":{},\"recent\":[]},\"direct_fast_path\":{\"target\":\"server.self-serve.windsurf.com:443\",\"configured\":true,\"active\":true,\"cooled_down\":false,\"state\":\"active\",\"health_state\":\"healthy\",\"usage\":{\"total\":2,\"direct_upstream\":2,\"python_fallback\":0,\"passthrough\":0,\"fallbacks\":0,\"active\":true}}}\n"
                "JSON\n"
            )
            (fake_bin / "curl").chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{fake_bin}:{env['PATH']}",
                    "HG_MICROPROXY_FRONT": "0",
                    "HG_PROXY_INTERNAL_HTTPS_PORT": "9443",
                }
            )
            result = subprocess.run(
                ["bash", str(status_script), "--direct"],
                cwd=temp_root,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("C Front:   ", result.stdout)
        self.assertIn("TLS RELAY RUNNING", result.stdout)
        self.assertIn(
            "Direct fast path: target=server.self-serve.windsurf.com:443 | configured=True active=True cooled_down=False | state=active health=healthy",
            result.stdout,
        )

    def test_hg_status_reports_disabled_front_listener(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            temp_root = tmp_path / "repo"
            status_script = temp_root / "scripts" / "internal" / "hg_status.sh"
            fake_bin = tmp_path / "bin"

            status_script.parent.mkdir(parents=True)
            (temp_root / "logs").mkdir(parents=True)
            (temp_root / "certs").mkdir()
            (temp_root / "certs" / "proxy.crt").write_text("test\n")
            (temp_root / "certs" / "proxy.key").write_text("test\n")
            status_script.write_text(
                (ROOT / "scripts" / "internal" / "hg_status.sh").read_text()
            )
            fake_bin.mkdir()
            (fake_bin / "ss").write_text(
                "#!/usr/bin/env bash\n"
                "args=\"$*\"\n"
                "if [[ \"$args\" == *':2443'* ]]; then\n"
                "  echo 'State Recv-Q Send-Q Local Address:Port Peer Address:Port Process'\n"
                "  echo 'LISTEN 0 128 127.0.0.1:2443 0.0.0.0:* users:((\"hg-edge\",pid=333,fd=3))'\n"
                "fi\n"
            )
            (fake_bin / "ss").chmod(0o755)
            (fake_bin / "curl").write_text("#!/usr/bin/env bash\nexit 7\n")
            (fake_bin / "curl").chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{fake_bin}:{env['PATH']}",
                    "HG_MICROPROXY_FRONT": "0",
                    "HG_MICROPROXY_FRONT_LISTEN": "127.0.0.1:2443",
                }
            )
            result = subprocess.run(
                ["bash", str(status_script), "--direct"],
                cwd=temp_root,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("C Front:", result.stdout)
        self.assertIn("LISTENER ACTIVE BUT DISABLED BY ENV", result.stdout)
        self.assertIn("Port: 2443", result.stdout)

    def test_microproxy_run_and_stop_use_pid_and_log_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            proto_dir = tmp_path / "prototype"
            proto_dir.mkdir()
            (proto_dir / "Makefile").write_text("all:\n\t@true\n")
            fake_bin = proto_dir / "hg-edge"
            fake_bin.write_text(
                "#!/usr/bin/env bash\n"
                "echo fake microproxy \"$@\"\n"
                "trap 'kill \"$child\" 2>/dev/null; exit 0' TERM INT\n"
                "sleep 30 &\n"
                "child=$!\n"
                "wait \"$child\"\n"
            )
            fake_bin.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "HG_MICROPROXY_DIR": str(proto_dir),
                    "HG_MICROPROXY_BIN": str(fake_bin),
                    "HG_MICROPROXY_PID_FILE": str(tmp_path / "microproxy.pid"),
                    "HG_MICROPROXY_LOG_FILE": str(tmp_path / "microproxy.log"),
                    "HG_MICROPROXY_LISTEN": "127.0.0.1:18443",
                    "HG_MICROPROXY_UPSTREAM": "127.0.0.1:443",
                }
            )

            run_result = run_command(
                "bash",
                "scripts/internal/hg_microproxy.sh",
                "run",
                env=env,
            )
            self.assertEqual(run_result.returncode, 0, run_result.stderr)
            self.assertIn("Started microproxy prototype", run_result.stdout)
            self.assertTrue((tmp_path / "microproxy.pid").exists())
            self.assertIn(
                "Python proxy remains the default live proxy",
                run_result.stdout,
            )

            try:
                status_result = run_command(
                    "bash",
                    "scripts/internal/hg_microproxy.sh",
                    "status",
                    env=env,
                )
                self.assertEqual(status_result.returncode, 0)
                self.assertIn("Prototype process: running", status_result.stdout)
                self.assertIn("Runtime listen: 127.0.0.1:18443", status_result.stdout)
            finally:
                stop_result = run_command(
                    "bash",
                    "scripts/internal/hg_microproxy.sh",
                    "stop",
                    env=env,
                )

            self.assertEqual(stop_result.returncode, 0, stop_result.stderr)
            self.assertIn("Stopped microproxy prototype", stop_result.stdout)
            self.assertFalse((tmp_path / "microproxy.pid").exists())
            log_text = (tmp_path / "microproxy.log").read_text()
            self.assertIn("--relay", log_text)
            self.assertIn("--listen 127.0.0.1:18443", log_text)

    def test_hg_start_direct_banner_reports_configuration_state(self):
        env = os.environ.copy()
        env.update(
            {
                "HG_START_SOURCE_ONLY": "1",
                "HG_MICROPROXY_DIRECT_UPSTREAM": "127.0.0.1:10443",
                "HG_MICROPROXY_DIRECT_HOT_PATH": "1",
            }
        )

        result = run_command(
            "bash",
            "-c",
            "source scripts/internal/hg_start.sh; _microproxy_direct_banner",
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "Direct fast-path configured: 127.0.0.1:10443 (hot-path enabled)",
            result.stdout,
        )

    def test_microproxy_run_can_enable_advisory_hot_path_observe(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            proto_dir = tmp_path / "prototype"
            proto_dir.mkdir()
            fake_bin = proto_dir / "hg-edge"
            fake_bin.write_text(
                "#!/usr/bin/env bash\n"
                "echo fake microproxy \"$@\"\n"
                "trap 'kill \"$child\" 2>/dev/null; exit 0' TERM INT\n"
                "sleep 30 &\n"
                "child=$!\n"
                "wait \"$child\"\n"
            )
            fake_bin.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "HG_MICROPROXY_DIR": str(proto_dir),
                    "HG_MICROPROXY_BIN": str(fake_bin),
                    "HG_MICROPROXY_PID_FILE": str(tmp_path / "microproxy.pid"),
                    "HG_MICROPROXY_LOG_FILE": str(tmp_path / "microproxy.log"),
                    "HG_MICROPROXY_LISTEN": "127.0.0.1:18443",
                    "HG_MICROPROXY_UPSTREAM": "127.0.0.1:9443",
                    "HG_MICROPROXY_HOT_PATH_OBSERVE": "1",
                }
            )

            run_result = run_command(
                "bash",
                "scripts/internal/hg_microproxy.sh",
                "run",
                env=env,
            )
            try:
                self.assertEqual(run_result.returncode, 0, run_result.stderr)
                log_text = (tmp_path / "microproxy.log").read_text()
                self.assertIn("--hot-path-observe", log_text)
            finally:
                run_command(
                    "bash",
                    "scripts/internal/hg_microproxy.sh",
                    "stop",
                    env=env,
                )

    def test_microproxy_run_refuses_live_listen_port_without_force(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            proto_dir = tmp_path / "prototype"
            proto_dir.mkdir()
            fake_bin = proto_dir / "hg-edge"
            fake_bin.write_text("#!/usr/bin/env bash\nsleep 30\n")
            fake_bin.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "HG_MICROPROXY_DIR": str(proto_dir),
                    "HG_MICROPROXY_BIN": str(fake_bin),
                    "HG_MICROPROXY_PID_FILE": str(tmp_path / "microproxy.pid"),
                    "HG_MICROPROXY_LOG_FILE": str(tmp_path / "microproxy.log"),
                    "HG_MICROPROXY_LISTEN": "127.0.0.1:9998",
                }
            )

            result = run_command(
                "bash",
                "scripts/internal/hg_microproxy.sh",
                "run",
                env=env,
            )

        self.assertEqual(result.returncode, 5)
        self.assertIn("Refusing live HIGH-GRAVITY listen port 9998", result.stderr)

    def test_microproxy_smoke_refuses_live_upstream_port_without_force(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            proto_dir = tmp_path / "prototype"
            proto_dir.mkdir()
            (proto_dir / "Makefile").write_text("all:\n\t@true\n")

            env = os.environ.copy()
            env.update(
                {
                    "HG_MICROPROXY_DIR": str(proto_dir),
                    "HG_MICROPROXY_SMOKE_DIR": str(tmp_path / "smoke"),
                    "HG_MICROPROXY_SMOKE_LISTEN": "127.0.0.1:18443",
                    "HG_MICROPROXY_SMOKE_UPSTREAM": "127.0.0.1:443",
                }
            )

            result = run_command(
                "bash",
                "scripts/internal/hg_microproxy.sh",
                "smoke",
                env=env,
            )

            self.assertEqual(result.returncode, 5)
        self.assertIn(
            "Refusing privileged microproxy smoke upstream port 443",
            result.stderr,
        )

    @unittest.skipUnless(shutil.which("cc"), "C compiler is required")
    def test_microproxy_smoke_builds_runs_fixture_and_summarizes_events(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            env = os.environ.copy()
            env.update(
                {
                    "HG_MICROPROXY_DIR": str(ROOT / "src" / "microproxy"),
                    "HG_MICROPROXY_SMOKE_DIR": str(tmp_path / "smoke"),
                    "HG_MICROPROXY_HOT_PATH_OBSERVE": "1",
                }
            )

            result = run_command(
                "bash",
                "scripts/internal/hg_microproxy.sh",
                "smoke",
                env=env,
                timeout=15,
            )

            event_log = tmp_path / "smoke" / "events.jsonl"
            event_log_exists = event_log.exists()
            run_log_text = (tmp_path / "smoke" / "hg-edge.log").read_text()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Running microproxy smoke check.", result.stdout)
        self.assertIn("HTTP/1.", result.stdout)
        self.assertIn("Microproxy smoke event summary:", result.stdout)
        self.assertIn("request_seen: 1", result.stdout)
        self.assertIn("route_selected: 1", result.stdout)
        self.assertIn("stream_finished: 1", result.stdout)
        self.assertIn("Python proxy remains the default live proxy", result.stdout)
        self.assertIn("--hot-path-observe", run_log_text)
        self.assertTrue(event_log_exists)

    @unittest.skipUnless(shutil.which("cc"), "C compiler is required")
    def test_microproxy_smoke_direct_exercises_local_direct_upstream_fixture(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            env = os.environ.copy()
            env.update(
                {
                    "HG_MICROPROXY_DIR": str(ROOT / "src" / "microproxy"),
                    "HG_MICROPROXY_SMOKE_DIR": str(tmp_path / "smoke-direct"),
                    "HG_MICROPROXY_HOT_PATH_OBSERVE": "1",
                }
            )

            result = run_command(
                "bash",
                "scripts/internal/hg_microproxy.sh",
                "smoke-direct",
                env=env,
                timeout=20,
            )

            smoke_dir = tmp_path / "smoke-direct"
            event_log = smoke_dir / "events.jsonl"
            event_log_exists = event_log.exists()
            run_log_text = (smoke_dir / "hg-edge.log").read_text()
            direct_log_text = (smoke_dir / "direct-fixture.log").read_text()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Running direct-path microproxy smoke check.", result.stdout)
        self.assertIn("Direct fast-path: enabled", result.stdout)
        self.assertIn("Microproxy direct smoke event summary:", result.stdout)
        self.assertIn("route_selected: 1", result.stdout)
        self.assertIn("hot_path_candidate: 1", result.stdout)
        self.assertIn("direct_upstream: 1", result.stdout)
        self.assertIn("Python proxy remains the default live proxy", result.stdout)
        self.assertIn("--direct-upstream", run_log_text)
        self.assertIn("--direct-hot-path", run_log_text)
        self.assertIn("POST /exa.api_server_pb.ApiServerService/GetChatMessage", direct_log_text)
        self.assertTrue(event_log_exists)


if __name__ == "__main__":
    unittest.main()
