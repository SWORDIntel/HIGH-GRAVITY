#!/usr/bin/env python3
"""
Tests for PegasusKhojBridge state tracking and injection flow.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.pegasus.khoj_integration import PegasusKhojBridge


class PegasusKhojBridgeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        (self.repo_root / "khoj").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "logs").mkdir(parents=True, exist_ok=True)
        self.bridge = PegasusKhojBridge(self.repo_root)

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_inject_context_records_search_and_snippets(self):
        self.bridge.search = AsyncMock(
            return_value={
                "status": "ok",
                "results": [
                    {"entry": "alpha body", "file": "alpha.md"},
                    {"entry": "beta body", "file": "beta.md"},
                ],
            }
        )

        messages = [{"role": "user", "content": "please search this"}]
        result = await self.bridge.inject_context(messages)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["injected"], 2)
        self.assertEqual(self.bridge.last_injection_status, "ok")
        self.assertEqual(self.bridge.last_snippet_count, 2)
        self.assertEqual(self.bridge.last_search_status, "ok")
        self.assertIn("alpha.md", self.bridge.last_snippet_sources)
        self.assertIn("beta.md", self.bridge.last_snippet_sources)
        self.assertTrue(messages[0]["content"].startswith("# KHOJ SEMANTIC SEARCH CONTEXT"))


if __name__ == "__main__":
    unittest.main()
