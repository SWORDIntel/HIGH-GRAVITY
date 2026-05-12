#!/usr/bin/env python3
"""Tests for safe NCS2 recovery state classification."""

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "internal" / "khoj_ncs2_recover.py"
SPEC = importlib.util.spec_from_file_location("khoj_ncs2_recover", MODULE_PATH)
khoj_ncs2_recover = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(khoj_ncs2_recover)


class KhojNcs2RecoverTests(unittest.TestCase):
    def test_classifies_visible_boot_failure(self):
        status = {
            "runtime": {
                "openvino": {
                    "devices": ["CPU", "MYRIAD.2.1.4.1.1-ma2480"],
                    "compile": {
                        "MYRIAD.2.1.4.1.1-ma2480": {
                            "ok": False,
                            "error": "RuntimeError: Failed to allocate graph: MYRIAD device is not opened",
                        }
                    },
                }
            }
        }
        lsusb = "Bus 001 Device 004: ID 03e7:2485 Intel Movidius MyriadX\n"

        summary = khoj_ncs2_recover.build_summary(status, lsusb)

        self.assertEqual(summary["state"], "visible_boot_failed")
        self.assertTrue(summary["boot_failure"])
        self.assertFalse(summary["compile_ok"])
        self.assertEqual(summary["usb_device_count"], 1)
        self.assertEqual(summary["next_command"], "./hg.sh khoj ncs2 reset")

    def test_compile_active_needs_no_reset(self):
        status = {
            "runtime": {
                "openvino": {
                    "devices": ["CPU", "MYRIAD"],
                    "compile": {"MYRIAD": {"ok": True}},
                }
            }
        }

        summary = khoj_ncs2_recover.build_summary(status, "")

        self.assertEqual(summary["state"], "compile_active")
        self.assertTrue(summary["compile_ok"])
        self.assertEqual(summary["next_command"], "")

    def test_usb_visible_but_runtime_missing(self):
        status = {"runtime": {"openvino": {"devices": ["CPU"], "compile": {"CPU": {"ok": True}}}}}
        lsusb = "Bus 002 Device 003: ID 03e7:2485 Intel Movidius MyriadX\n"

        summary = khoj_ncs2_recover.build_summary(status, lsusb)

        self.assertEqual(summary["state"], "usb_visible_runtime_missing")
        self.assertEqual(summary["usb_devices"][0]["path"], "/dev/bus/usb/002/003")


if __name__ == "__main__":
    unittest.main()
