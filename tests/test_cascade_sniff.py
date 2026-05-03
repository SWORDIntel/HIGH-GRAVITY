#!/usr/bin/env python3
"""
Tests for Cascade RPC classification in tools/sniff_cascade.py.
"""

import ast
import os
import unittest
from pathlib import Path
from unittest import mock


def load_helper_namespace():
    source_path = Path(__file__).resolve().parent.parent / "tools" / "sniff_cascade.py"
    source = source_path.read_text()
    tree = ast.parse(source, filename=str(source_path))
    wanted = {"is_truthy", "cascade_only_enabled", "classify_rpc"}
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    module = ast.Module(body=selected, type_ignores=[])
    code = compile(module, str(source_path), "exec")
    ns = {"os": os, "__builtins__": __builtins__}
    exec(code, ns, ns)
    return ns


SNIFFER = load_helper_namespace()


class CascadeSniffTests(unittest.TestCase):
    def test_classify_rpc_prioritizes_cascade_methods(self):
        self.assertEqual(
            SNIFFER["classify_rpc"]("exa.language_server_pb.LanguageServerService/AcknowledgeCascadeCodeEdit"),
            "cascade/edit-ack",
        )
        self.assertEqual(
            SNIFFER["classify_rpc"]("exa.language_server_pb.LanguageServerService/GetCodeMapSuggestions"),
            "cascade/code-map",
        )
        self.assertEqual(
            SNIFFER["classify_rpc"]("exa.language_server_pb.LanguageServerService/SomeOtherCascadeRPC"),
            "cascade/rpc",
        )
        self.assertEqual(
            SNIFFER["classify_rpc"]("exa.api_server_pb.ApiServerService/GetStreamingCompletions"),
            "completion",
        )

    def test_cascade_only_flag_uses_environment(self):
        self.assertFalse(SNIFFER["cascade_only_enabled"]())
        with mock.patch.dict(os.environ, {"HIGHGRAVITY_CASCADE_ONLY": "1"}, clear=False):
            self.assertTrue(SNIFFER["cascade_only_enabled"]())


if __name__ == "__main__":
    unittest.main()
