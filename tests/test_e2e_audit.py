"""E2E audit strictness and diagnostic regression tests."""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_audit_module():
    path = ROOT / "tools" / "audit" / "hg_e2e_audit.py"
    spec = importlib.util.spec_from_file_location("hg_e2e_audit_for_tests", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class E2EAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit_module()

    def test_full_unittest_discovery_is_required(self):
        self.assertTrue(self.audit.FULL_COMMANDS)
        self.assertTrue(all(item[3] for item in self.audit.FULL_COMMANDS))

    def test_command_diagnostics_extracts_failure_names(self):
        diagnostics = self.audit.command_diagnostics(
            "FAIL: test_one (suite.Case)\n",
            "ERROR: test_two (suite.Case)\nFAIL: test_one (suite.Case)\n",
        )
        self.assertEqual(
            diagnostics,
            ["test_one (suite.Case)", "test_two (suite.Case)"],
        )


if __name__ == "__main__":
    unittest.main()
