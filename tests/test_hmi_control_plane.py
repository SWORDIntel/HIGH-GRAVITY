"""Shell guardrails for procedural HMI control-plane wiring."""

import os
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


class HmiControlPlaneTests(unittest.TestCase):
    def test_hmi_shell_entrypoints_parse(self):
        scripts = [
            ROOT / "hg.sh",
            ROOT / "scripts" / "internal" / "hg_hmi.sh",
        ]

        for script in scripts:
            with self.subTest(script=script):
                result = run_command("bash", "-n", str(script))
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_hg_help_advertises_hmi_dispatch(self):
        result = run_command("bash", "hg.sh", "--help", timeout=15)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("hmi", result.stdout)
        self.assertIn("Manage procedural C++ HMI build/check/run/tui/status", result.stdout)
        self.assertIn("hmi-dashboard", result.stdout)

        hg_sh = (ROOT / "hg.sh").read_text(encoding="utf-8")
        self.assertIn('exec bash "$SCRIPTS_DIR/internal/hg_hmi.sh"', hg_sh)
        self.assertIn('exec bash "$SCRIPTS_DIR/internal/hg_start.sh" start', hg_sh)
        self.assertIn('exec bash "$SCRIPTS_DIR/internal/hg_stop.sh" --direct', hg_sh)
        self.assertIn("hmi-dashboard|hmi_dash|hmidashboard", hg_sh)

    def test_readme_documents_hmi_dashboard_control(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("hmi-dashboard", readme)
        self.assertIn("Launch Procedural HMI Dashboard", readme)
        self.assertIn("**`H`**: Launch Procedural HMI Dashboard", readme)

    def test_hg_aliases_expose_hmi_dashboard_shortcut(self):
        aliases = (ROOT / "scripts" / "hg_aliases.sh").read_text(encoding="utf-8")
        self.assertIn('alias hg-hmi-dashboard="$HG_ROOT/hg.sh hmi-dashboard"', aliases)

    def test_hmi_dashboard_alias_routes_to_noninteractive_tui_hint(self):
        result = run_command("bash", "hg.sh", "hmi-dashboard", timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HMI TUI mode requires an interactive terminal.", result.stdout + result.stderr)

    def test_menu_includes_hmi_dashboard_option(self):
        menu_script = (ROOT / "scripts" / "internal" / "hgmenu.sh").read_text(encoding="utf-8")
        self.assertIn("HMI Dashboard", menu_script)
        self.assertIn('"HMI Dashboard") bash ./hg.sh hmi-dashboard', menu_script)

    def test_hmi_help_lists_required_commands(self):
        result = run_command("bash", "scripts/internal/hg_hmi.sh", "help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage: ./hg.sh hmi <command>", result.stdout)
        for command in ("status", "build", "check", "run", "dash", "dashboard", "tui"):
            self.assertIn(command, result.stdout)

    def test_dashboard_includes_hmi_dashboard_control(self):
        dashboard = (ROOT / "src" / "hg_dashboard.py").read_text(encoding="utf-8")
        self.assertIn('tbl.add_row("H", "HMI Dashboard")', dashboard)
        self.assertIn('elif c == "h":', dashboard)

    def test_hmi_status_reports_isolated_proxy_routing(self):
        result = run_command("bash", "scripts/internal/hg_hmi.sh", "status")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("HIGH-GRAVITY procedural HMI status", result.stdout)
        self.assertIn("Proxy routing: unchanged", result.stdout)
        self.assertIn("Telemetry source: http://127.0.0.1:9998/hg/telemetry", result.stdout)
        self.assertIn("Proxy telemetry:", result.stdout)

    def test_hmi_check_is_headless_safe_without_glslc(self):
        env = os.environ.copy()
        env.update(
            {
                "GLSLC": "/definitely/missing/glslc",
                "DISPLAY": "",
                "WAYLAND_DISPLAY": "",
            }
        )

        result = run_command(
            "bash",
            "scripts/internal/hg_hmi.sh",
            "check",
            env=env,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("headless validation only", result.stdout)
        self.assertIn("skipping shader compilation", result.stdout)
        self.assertIn("hmi_push_size=96", result.stdout)

    def test_hmi_run_skips_safely_without_display_or_vulkan(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_bin = Path(tmp_dir) / "hmi"
            fake_bin.write_text("#!/usr/bin/env bash\necho should-not-run\n", encoding="utf-8")
            fake_bin.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "HG_HMI_BIN": str(fake_bin),
                    "DISPLAY": "",
                    "WAYLAND_DISPLAY": "",
                }
            )

            result = run_command(
                "bash",
                "scripts/internal/hg_hmi.sh",
                "run",
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("runtime was not started", result.stdout)
        self.assertIn("Proxy routing remains unchanged", result.stdout)
        self.assertNotIn("should-not-run", result.stdout)

    def test_hmi_runner_uses_native_proxy_telemetry_not_synthetic_counters(self):
        runner = (ROOT / "src" / "hmi" / "hmi_runner.cpp").read_text(encoding="utf-8")

        self.assertIn("HmiTelemetryPoller telemetry", runner)
        self.assertIn("telemetry_source_from_env", runner)
        self.assertNotIn("640.0F + now", runner)
        self.assertNotIn("39000.0F + now", runner)


if __name__ == "__main__":
    unittest.main()
