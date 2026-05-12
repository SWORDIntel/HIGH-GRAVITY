#!/usr/bin/env python3
"""
Tests for PegasusKhojBridge state tracking and injection flow.
"""

import gzip
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

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
        self.assertTrue(result["stored"])
        self.assertEqual(self.bridge.last_injection_status, "ok")
        self.assertEqual(self.bridge.last_snippet_count, 2)
        self.assertEqual(self.bridge.last_search_status, "ok")
        self.assertEqual(self.bridge.stored_observation_count, 1)
        self.assertIn("alpha.md", self.bridge.last_snippet_sources)
        self.assertIn("beta.md", self.bridge.last_snippet_sources)
        self.assertTrue(messages[0]["content"].startswith("KHOJ_CONTEXT"))
        stored = (self.repo_root / "logs" / "khoj_intelligence.jsonl").read_text()
        self.assertIn('"mode": "json_injection"', stored)
        self.assertIn('"injected": true', stored)

    async def test_observe_binary_request_records_passive_lookup(self):
        self.bridge.search = AsyncMock(
            return_value={
                "status": "ok",
                "results": [
                    {
                        "entry": "provider unreachable root cause notes",
                        "file": "docs/provider.md",
                    }
                ],
            }
        )

        body = (
            b"\x00\x00random framing"
            b"please fix provider unreachable after wait in proxy stream relay"
            b"\x00more framing"
        )
        result = await self.bridge.observe_binary_request(
            "exa.api_server_pb.ApiServerService/GetChatMessage",
            body,
            request_id="abcd1234",
            content_type="application/connect+proto",
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["snippets"], 1)
        self.assertTrue(result["stored"])
        self.assertEqual(self.bridge.passive_lookup_count, 1)
        self.assertEqual(self.bridge.passive_hit_count, 1)
        self.assertEqual(self.bridge.stored_observation_count, 1)
        self.assertEqual(self.bridge.last_passive_status, "ok")
        self.assertIn("docs/provider.md", self.bridge.last_passive_sources)
        self.assertIn("provider unreachable", self.bridge.last_passive_query)
        stored = (self.repo_root / "logs" / "khoj_intelligence.jsonl").read_text()
        self.assertIn('"mode": "binary_passive"', stored)
        self.assertIn('"injected": false', stored)

    async def test_observe_binary_request_ignores_noise_only_body(self):
        self.bridge.search = AsyncMock()

        result = await self.bridge.observe_binary_request(
            "exa.api_server_pb.ApiServerService/GetChatMessage",
            b"connect-go/1.18.1 codeium windsurf api_server_pb",
            request_id="abcd1234",
            content_type="application/connect+proto",
        )

        self.assertEqual(result["status"], "no_query")
        self.assertFalse((self.repo_root / "logs" / "khoj_intelligence.jsonl").exists())
        self.bridge.search.assert_not_called()

    async def test_observe_binary_request_extracts_gzip_connect_frame(self):
        self.bridge.search = AsyncMock(
            return_value={
                "status": "ok",
                "results": [
                    {
                        "entry": "connect gzip extraction notes",
                        "file": "docs/connect.md",
                    }
                ],
            }
        )

        message = b"please improve binary protobuf extraction for gzip connect frames"
        compressed = gzip.compress(message)
        body = b"\x01" + len(compressed).to_bytes(4, "big") + compressed

        result = await self.bridge.observe_binary_request(
            "exa.api_server_pb.ApiServerService/GetChatMessage",
            body,
            request_id="gzip1234",
            content_type="application/connect+proto",
        )

        self.assertEqual(result["status"], "ok")
        self.assertIn("gzip connect frames", self.bridge.last_passive_query)
        self.bridge.search.assert_awaited_once()

    async def test_extract_binary_query_reads_protobuf_length_delimited_text(self):
        text = b"surface useful query text for live Windsurf chat without prompt growth"
        body = b"\x12" + bytes([len(text)]) + text + b"\x1a\x03\x00\x01\x02"

        query = self.bridge._extract_binary_query(
            body,
            "exa.api_server_pb.ApiServerService/GetChatMessage",
        )

        self.assertIn("useful query text", query)
        self.assertIn("live Windsurf chat", query)

    async def test_extract_binary_query_filters_noisy_opaque_bytes(self):
        body = (
            b"\x00\x0cconnect-go/1.18.1\x00"
            b"api_server_pb codeium request_id product_analytics "
            b"3f8b2d9b4e6a488f9b483a611949c17e "
            b"QWxhZGRpbjpvcGVuIHNlc2FtZQ=="
        )

        query = self.bridge._extract_binary_query(
            body,
            "exa.api_server_pb.ApiServerService/GetChatMessage",
        )

        self.assertEqual(query, "")

    async def test_binary_context_injection_dedupes_same_query(self):
        first = self.bridge.should_inject_binary_context({"query_hash": "abc123"})
        second = self.bridge.should_inject_binary_context({"query_hash": "abc123"})

        self.assertEqual(first, (True, "ok"))
        self.assertEqual(second, (False, "duplicate_query"))
        self.assertEqual(self.bridge.binary_inject_dedupe_skips, 1)


if __name__ == "__main__":
    unittest.main()
