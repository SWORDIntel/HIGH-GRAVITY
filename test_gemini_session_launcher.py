#!/usr/bin/env python3
"""
Basic tests for Windsurf profile generation in gemini_session_launcher.py
"""

import tempfile
import unittest
from pathlib import Path

from gemini_session_launcher import GeminiSessionLauncher


class GeminiSessionLauncherTests(unittest.TestCase):
    def setUp(self):
        self.launcher = GeminiSessionLauncher()
        self.api_key = "AIzaSyExampleKey1234567890"

    def test_build_windsurf_profile_proxy_sets_expected_env(self):
        profile = self.launcher.build_windsurf_profile(
            api_key=self.api_key,
            window_name="Main Window",
            provider="proxy",
            proxy_url="http://localhost:9999",
        )

        self.assertEqual(profile["profile_id"], "main-window")
        self.assertEqual(profile["provider"], "proxy")
        self.assertEqual(profile["env"]["GOOGLE_API_KEY"], self.api_key)
        self.assertEqual(profile["env"]["OPENAI_BASE_URL"], "http://localhost:9999")
        self.assertEqual(profile["env"]["HIGHGRAVITY_WINDOW_ID"], "main-window")

    def test_build_windsurf_profile_direct_omits_proxy_env(self):
        profile = self.launcher.build_windsurf_profile(
            api_key=self.api_key,
            window_name="Direct",
            provider="direct",
        )

        self.assertEqual(profile["provider"], "direct")
        self.assertNotIn("OPENAI_BASE_URL", profile["env"])
        self.assertIsNone(profile["proxy_url"])

    def test_write_windsurf_profile_creates_expected_files(self):
        profile = self.launcher.build_windsurf_profile(
            api_key=self.api_key,
            window_name="QC Window",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            files = self.launcher.write_windsurf_profile(
                profile,
                output_dir=Path(tmpdir) / "windsurf-profile",
            )

            self.assertTrue(files["env_file"].exists())
            self.assertTrue(files["metadata_file"].exists())
            self.assertTrue(files["launch_script"].exists())

            env_text = files["env_file"].read_text()
            launch_text = files["launch_script"].read_text()

            self.assertIn("HIGHGRAVITY_WINDOW_ID=qc-window", env_text)
            self.assertIn('exec "${WINDSURF_BIN:-windsurf}" --new-window "$@"', launch_text)

    def test_normalize_hook_style_json_payload(self):
        payload = {
            "agent_action_name": "post_run_command",
            "trajectory_id": "traj-123",
            "execution_id": "exec-456",
            "tool_info": {
                "variables": {
                    "apiKey": self.api_key,
                    "mode": "windsurf",
                    "proxyUrl": "http://localhost:9999",
                    "windowName": "Cascade Window",
                    "dryRun": True,
                }
            },
        }

        normalized = self.launcher._normalize_integration_overrides(payload)

        self.assertEqual(normalized["api_key"], self.api_key)
        self.assertEqual(normalized["mode"], "windsurf")
        self.assertEqual(normalized["proxy_url"], "http://localhost:9999")
        self.assertEqual(normalized["window_name"], "Cascade Window")
        self.assertTrue(normalized["dry_run"])

    def test_normalize_windsurf_hook_payload(self):
        overrides = self.launcher._normalize_integration_overrides({
            "agent_action_name": "pre_run_command",
            "trajectory_id": "traj-123",
            "execution_id": "exec-456",
            "tool_info": {
                "apiKey": self.api_key,
                "mode": "windsurf",
                "provider": "proxy",
                "proxyUrl": "http://localhost:9999",
                "dryRun": True,
            },
        })

        self.assertEqual(overrides["api_key"], self.api_key)
        self.assertEqual(overrides["mode"], "windsurf")
        self.assertEqual(overrides["provider"], "proxy")
        self.assertEqual(overrides["proxy_url"], "http://localhost:9999")
        self.assertTrue(overrides["dry_run"])
        self.assertEqual(overrides["window_name"], "traj-123-exec-456")


if __name__ == "__main__":
    unittest.main()
