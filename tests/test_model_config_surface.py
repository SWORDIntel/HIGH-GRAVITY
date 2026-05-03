#!/usr/bin/env python3
"""
Tests for the local Windsurf model catalog fallback.
"""

import importlib.util
import sys
import unittest
from pathlib import Path


def _load_proxy_module():
    repo_root = Path(__file__).resolve().parent.parent
    proxy_path = repo_root / "src" / "proxy.py"
    spec = importlib.util.spec_from_file_location("hg_proxy_for_model_surface", proxy_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["hg_proxy_for_model_surface"] = module
    spec.loader.exec_module(module)
    return module


class LocalModelSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proxy = _load_proxy_module()

    def test_private_models_are_surfaced_locally(self):
        payload = self.proxy.build_local_model_config_response()
        self.assertEqual(payload["status"], "ok")
        keys = {m["modelKey"] for m in payload["models"]}
        self.assertIn("MODEL_PRIVATE_11", keys)
        self.assertIn("MODEL_PRIVATE_2", keys)
        self.assertIn("MODEL_PRIVATE_3", keys)

    def test_private_model_surface_has_display_names(self):
        payload = self.proxy.build_local_model_config_response()
        by_key = {m["modelKey"]: m for m in payload["models"]}
        self.assertEqual(by_key["MODEL_PRIVATE_11"]["displayName"], "Claude Haiku 4.5")
        self.assertEqual(by_key["MODEL_PRIVATE_2"]["displayName"], "Claude Sonnet 4.5")
        self.assertEqual(by_key["MODEL_PRIVATE_3"]["displayName"], "Claude Sonnet 4.5 Thinking")


if __name__ == "__main__":
    unittest.main()
