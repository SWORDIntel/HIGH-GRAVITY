"""Antigravity bridge path-default regression tests."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AntigravityPathTests(unittest.TestCase):
    def test_bridge_env_uses_xdg_config_and_state_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            env["XDG_STATE_HOME"] = str(Path(tmp) / "state")
            env.pop("AGY_CONFIG", None)
            env.pop("AGY_STATE_DIR", None)
            result = subprocess.run(
                ("bash", "scripts/internal/hg_antigravity.sh", "env"),
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'export AGY_CONFIG="{tmp}/config/high-gravity/antigravity/accounts.json"', result.stdout)
        self.assertIn(f'export AGY_STATE_DIR="{tmp}/state/high-gravity/antigravity"', result.stdout)

    def test_bootstrap_to_status_uses_the_same_xdg_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["HOME"] = str(Path(tmp) / "home")
            env["XDG_CONFIG_HOME"] = str(Path(tmp) / "config")
            env["XDG_STATE_HOME"] = str(Path(tmp) / "state")
            env["XDG_DATA_HOME"] = str(Path(tmp) / "data")
            env["DRY_RUN"] = "1"
            env["SKIP_VENV"] = "1"
            setup = subprocess.run(
                ("bash", "tools/antigravity_three_account/setup.sh"),
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            self.assertEqual(setup.returncode, 0, setup.stderr)
            status = subprocess.run(
                ("bash", "scripts/internal/hg_antigravity.sh", "status"),
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn(f"config={tmp}/config/high-gravity/antigravity/accounts.json", status.stdout)
        self.assertIn("account_1", status.stdout)


if __name__ == "__main__":
    unittest.main()
