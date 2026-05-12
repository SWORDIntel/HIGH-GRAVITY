#!/usr/bin/env python3
"""Tests for Khoj acceleration status normalization."""

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "internal" / "khoj_accel_status.py"
SPEC = importlib.util.spec_from_file_location("khoj_accel_status", MODULE_PATH)
khoj_accel_status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(khoj_accel_status)


class KhojAccelStatusTests(unittest.TestCase):
    def test_distinguishes_host_exposed_and_runtime_active(self):
        runtime = {
            "torch": {
                "cuda_available": True,
                "cuda_count": 1,
                "cuda_runtime_ok": True,
                "proof": "torch tensor op on cuda:0",
            },
            "openvino": {
                "devices": ["CPU", "MYRIAD"],
                "compile": {
                    "CPU": {"ok": True},
                    "MYRIAD": {"ok": False, "error": "device busy"},
                },
            },
            "usb": {
                "dev_bus_usb_present": True,
                "device_count": 2,
            },
        }
        env = {
            "ACCEL_MODE": "all",
            "CUDA_HOST_DETECTED": "1",
            "CUDA_ENABLED": "1",
            "OPENVINO_HOST_DETECTED": "1",
            "OPENVINO_ENABLED": "1",
            "MYRIAD_HOST_DETECTED": "1",
            "MYRIAD_ENABLED": "1",
            "MYRIAD_COUNT": "2",
            "NVIDIA_NAME": "Test GPU",
            "OPENVINO_HOST_DEVICES": "CPU,MYRIAD",
        }

        status = khoj_accel_status.build_status(env, runtime=runtime, phase="runtime_probed")

        self.assertTrue(status["host"]["cuda"])
        self.assertTrue(status["container"]["cuda_exposed"])
        self.assertTrue(status["runtime_active"]["cuda"])
        self.assertTrue(status["runtime_active"]["openvino"])
        self.assertTrue(status["runtime_active"]["openvino_runtime_visible"])
        self.assertTrue(status["runtime_active"]["openvino_compile_ok"])
        self.assertFalse(status["runtime_active"]["openvino_accelerated"])
        self.assertTrue(status["host"]["myriad"])
        self.assertTrue(status["container"]["myriad_exposed"])
        self.assertFalse(status["runtime_active"]["myriad"])
        self.assertTrue(status["runtime_active"]["myriad_visible"])
        self.assertFalse(status["runtime_active"]["myriad_compile_ok"])
        self.assertTrue(status["runtime_active"]["myriad_compile_failed"])
        self.assertEqual(status["host"]["ncs2_count"], 2)
        self.assertTrue(status["runtime_active"]["usb_passthrough"])
        self.assertEqual(status["runtime_active"]["usb_device_count"], 2)
        self.assertEqual(status["proof"]["cuda"]["method"], "torch tensor op on cuda:0")

    def test_marks_myriad_boot_failure_from_compile_error(self):
        runtime = {
            "openvino": {
                "devices": ["CPU", "MYRIAD.2.1.4.1.1-ma2480"],
                "compile": {
                    "CPU": {"ok": True},
                    "MYRIAD.2.1.4.1.1-ma2480": {
                        "ok": False,
                        "error": "RuntimeError: Failed to allocate graph: MYRIAD device is not opened.",
                    },
                },
            }
        }

        active = khoj_accel_status.runtime_activity(runtime)

        self.assertTrue(active["openvino_runtime_visible"])
        self.assertTrue(active["openvino_compile_ok"])
        self.assertTrue(active["myriad_visible"])
        self.assertTrue(active["myriad_compile_failed"])
        self.assertTrue(active["myriad_boot_failed"])
        self.assertIn("MYRIAD device is not opened", active["myriad_compile_errors"][0])

    def test_manual_probe_preserves_previous_host_and_container(self):
        previous = {
            "host": {"cuda": True, "myriad": True, "myriad_count": 1, "ncs2": True, "ncs2_count": 1},
            "container": {"cuda_exposed": True, "myriad_exposed": True, "ncs2_exposed": True},
        }
        runtime = {"error": "khoj_container_not_running"}

        status = khoj_accel_status.build_status({}, runtime=runtime, previous=previous)

        self.assertTrue(status["host"]["cuda"])
        self.assertTrue(status["container"]["cuda_exposed"])
        self.assertFalse(status["runtime_active"]["cuda"])
        self.assertEqual(status["myriad_count"], 1)


if __name__ == "__main__":
    unittest.main()
