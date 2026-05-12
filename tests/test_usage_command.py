"""Usage command shell entrypoint and runtime contract tests."""

import json
import os
import subprocess
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


class UsageCommandTests(unittest.TestCase):
    def test_usage_scripts_are_parseable(self):
        result = run_command("bash", "-n", str(ROOT / "scripts" / "internal" / "hg_usage.sh"))

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_usage_help_is_user_visible(self):
        result = run_command("bash", "hg.sh", "--help", timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage", result.stdout)
        self.assertIn("cache savings ratio", result.stdout)

    def test_usage_help_shows_options(self):
        result = run_command("bash", "scripts/internal/hg_usage.sh", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage: ./hg.sh usage [options]", result.stdout)
        self.assertIn("-w, --watch", result.stdout)
        self.assertIn("-i, --interval", result.stdout)
        self.assertIn("-j, --json", result.stdout)

    def test_usage_json_emits_snapshot_when_proxy_unreachable(self):
        env = os.environ.copy()
        env["HG_PROXY_URL"] = "http://127.0.0.1:1"
        env["HG_USAGE_PATH"] = "/api/oauth/usage"

        result = run_command(
            "bash",
            "hg.sh",
            "usage",
            "--json",
            env=env,
            timeout=20,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.strip())
        self.assertIn("usage_route", payload)
        self.assertIn("proxy_url", payload)
        self.assertEqual(payload.get("usage_route", {}).get("reachable"), False)
        self.assertIn("telemetry_error", payload)


if __name__ == "__main__":
    unittest.main()
