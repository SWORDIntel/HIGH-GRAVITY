#!/usr/bin/env python3
"""
Tests for the Windsurf Cascade hook bridge.
"""

import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock


def load_hook_module():
    module_path = Path(__file__).resolve().parent.parent / ".windsurf" / "cascade_highgravity_hook.py"
    spec = importlib.util.spec_from_file_location("cascade_highgravity_hook", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


HOOK_MODULE = load_hook_module()


class WindsurfHookBridgeTests(unittest.TestCase):
    @mock.patch.dict(
        os.environ,
        {
            "HIGHGRAVITY_API_KEY": "AIzaSyBridgeKey123456",
            "HIGHGRAVITY_PROVIDER": "proxy",
            "HIGHGRAVITY_PROXY_URL": "http://localhost:9999",
            "HIGHGRAVITY_DRY_RUN": "false",
        },
        clear=False,
    )
    def test_build_payload_merges_env_defaults(self):
        payload = {
            "agent_action_name": "post_run_command",
            "trajectory_id": "traj-123",
            "tool_info": {
                "command_line": "echo hello"
            },
        }

        result = HOOK_MODULE.build_payload(payload)
        variables = result["tool_info"]["variables"]

        self.assertEqual(variables["apiKey"], "AIzaSyBridgeKey123456")
        self.assertEqual(variables["provider"], "proxy")
        self.assertEqual(variables["proxyUrl"], "http://localhost:9999")
        self.assertEqual(variables["mode"], "windsurf")
        self.assertEqual(variables["dryRun"], "false")

    def test_build_payload_preserves_explicit_variables(self):
        payload = {
            "tool_info": {
                "variables": {
                    "apiKey": "explicit-key",
                    "windowName": "explicit-window",
                    "dryRun": True,
                }
            }
        }

        result = HOOK_MODULE.build_payload(payload)
        variables = result["tool_info"]["variables"]

        self.assertEqual(variables["apiKey"], "explicit-key")
        self.assertEqual(variables["windowName"], "explicit-window")
        self.assertTrue(variables["dryRun"])


if __name__ == "__main__":
    unittest.main()
