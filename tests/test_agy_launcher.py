"""Root triple-account Antigravity launcher contract tests."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "agy.sh"


class AgyLauncherTests(unittest.TestCase):
    def run_launcher(self, *args, env=None):
        return subprocess.run(
            ("bash", str(LAUNCHER), *args),
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )

    def test_shell_syntax_and_help(self):
        syntax = subprocess.run(("bash", "-n", str(LAUNCHER)), check=False)
        self.assertEqual(syntax.returncode, 0)
        result = self.run_launcher("help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("monitor-window", result.stdout)
        self.assertIn("triple-account", result.stdout)

    def test_plan_is_non_destructive_and_shows_stack_actions(self):
        env = os.environ.copy()
        env["AGY_CONFIG"] = "/definitely/missing/accounts.json"
        result = self.run_launcher("plan", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DRY_RUN", result.stdout)
        self.assertIn("microproxy build", result.stdout)
        self.assertIn("proxy start", result.stdout)
        self.assertIn("companion monitor window", result.stdout)

    def test_launch_dry_run_accepts_staged_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "accounts.json"
            config.write_text('{"accounts": []}\n', encoding="utf-8")
            env = os.environ.copy()
            env["AGY_CONFIG"] = str(config)
            env["AGY_LAUNCH_DRY_RUN"] = "1"
            result = self.run_launcher("launch", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("antigravity status", result.stdout)

    def test_run_dry_run_does_not_execute_wrapper(self):
        env = os.environ.copy()
        env["AGY_CONFIG"] = "/definitely/missing/accounts.json"
        env["AGY_LAUNCH_DRY_RUN"] = "1"
        result = self.run_launcher("run", "--", "audit prompt", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("antigravity run", result.stdout)
        self.assertIn(r"audit\ prompt", result.stdout)


if __name__ == "__main__":
    unittest.main()
