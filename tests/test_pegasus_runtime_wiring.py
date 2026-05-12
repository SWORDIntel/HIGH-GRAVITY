#!/usr/bin/env python3
"""Tests for Pegasus default-on runtime wiring."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.pegasus.generator.agent_factory import AgentFactory


ROOT = Path(__file__).resolve().parent.parent


class PegasusRuntimeWiringTests(unittest.TestCase):
    def test_agent_factory_returns_structured_spec(self):
        factory = AgentFactory(ROOT / "src" / "pegasus" / "agents")

        spec = factory.get_agent_spec("RESEARCHER")

        self.assertIsInstance(spec, dict)
        self.assertEqual(spec["name"], "RESEARCHER")
        self.assertTrue(Path(spec["path"]).name, "RESEARCHER.md")
        self.assertIsInstance(spec["capabilities"], list)
        self.assertIn("Read", spec["capabilities"])

    def test_launcher_uses_sudo_user_home_and_agent_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "hgtestuser"
            fake_bin = fake_home / ".local" / "bin"
            fake_bin.mkdir(parents=True)
            fake_agent = fake_bin / "fake-agent"
            fake_agent.write_text("#!/bin/sh\necho HOME=$HOME\necho PATH=$PATH\necho ARGS=\"$*\"\n", encoding="utf-8")
            fake_agent.chmod(0o755)

            env = {
                "HOME": "/root",
                "SUDO_USER": fake_home.name,
                "SUDO_HOME": str(fake_home),
                "HG_AGENT_CLI": str(fake_agent),
                "PATH": "/usr/bin:/bin",
            }

            result = subprocess.run(
                ["bash", str(ROOT / "scripts" / "internal" / "launch_claude_interface.sh"), "-p", "smoke"],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

        self.assertIn(f"HOME={fake_home}", result.stdout)
        self.assertIn(f"{fake_home}/.local/bin", result.stdout)
        self.assertIn("ARGS=-p smoke", result.stdout)


if __name__ == "__main__":
    unittest.main()
