#!/usr/bin/env python3
"""
Intel NPU Hardware Detection and Optimization
Advanced hardware detection for Intel Meteor Lake NPU with 34 TOPS capability
Integrates with Rust NPU coordination bridge for optimal performance
"""

import json
import logging
import os
import platform
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NPUCapabilities:
    """Intel NPU hardware capabilities"""

    model_name: str
    max_tops: float
    memory_mb: int
    driver_version: str
    device_path: str
    pci_id: str
    vendor_id: str
    device_id: str
    subsystem_vendor: str
    subsystem_device: str
    supports_fp16: bool
    supports_int8: bool
    supports_int4: bool
    max_batch_size: int
    thermal_design_power: float
    base_frequency_mhz: int
    boost_frequency_mhz: int
    architecture: str
    features: List[str]


@dataclass
class SystemOptimization:
    """System optimization recommendations"""

    cpu_governor: str
    cpu_frequency_scaling: str
    turbo_boost_enabled: bool
    hyperthreading_enabled: bool
    numa_balancing: bool
    transparent_hugepages: str
    kernel_parameters: List[str]
    compiler_flags: List[str]
    rust_target_features: List[str]
    recommended_memory_allocation: int


class IntelNPUDetector:
    """
    Advanced Intel NPU hardware detection and optimization
    Focuses on Intel Meteor Lake architecture with 34 TOPS NPU
    """

    # Intel NPU PCI IDs for Meteor Lake
    INTEL_NPU_DEVICE_IDS = {
        "0x7d1d": "Intel NPU (Meteor Lake)",
        "0x643e": "Intel NPU (Lunar Lake)",
        "0x4f80": "Intel NPU (Arrow Lake)",
        "0x4f81": "Intel NPU (Arrow Lake-H)",
    }

    INTEL_VENDOR_ID = "8086"

    def __init__(self):
        self.detected_npu: Optional[NPUCapabilities] = None
        self.system_info = self._gather_system_info()

    def _gather_system_info(self) -> Dict[str, Any]:
        """Gather comprehensive system information"""
        info = {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "kernel_version": platform.release(),
        }

        # Get detailed CPU information
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read()
                info["cpuinfo"] = cpuinfo
        except FileNotFoundError:
            info["cpuinfo"] = ""

        return info

    def detect_intel_npu(self) -> Optional[NPUCapabilities]:
        """
        Comprehensive Intel NPU detection
        Returns NPU capabilities if found, None otherwise
        """
        logger.info("Starting Intel NPU detection...")

        # Method 1: PCI device detection
        npu_from_pci = self._detect_npu_via_pci()
        if npu_from_pci:
            logger.info(f"NPU detected via PCI: {npu_from_pci.model_name}")
            self.detected_npu = npu_from_pci
            return npu_from_pci

        # Method 2: Device node detection
        npu_from_device = self._detect_npu_via_device_nodes()
        if npu_from_device:
            logger.info(f"NPU detected via device nodes: {npu_from_device.model_name}")
            self.detected_npu = npu_from_device
            return npu_from_device

        # Method 3: Driver module detection
        npu_from_driver = self._detect_npu_via_driver()
        if npu_from_driver:
            logger.info(f"NPU detected via driver: {npu_from_driver.model_name}")
            self.detected_npu = npu_from_driver
            return npu_from_driver

        # Method 4: CPU model-based inference
        npu_from_cpu = self._infer_npu_from_cpu()
        if npu_from_cpu:
            logger.info(f"NPU inferred from CPU: {npu_from_cpu.model_name}")
            self.detected_npu = npu_from_cpu
            return npu_from_cpu

        logger.warning("No Intel NPU detected")
        return None

    def _detect_npu_via_pci(self) -> Optional[NPUCapabilities]:
        """
        SECURITY: Enhanced PCI detection with strict validation
        Only accept verified Intel NPU device IDs, no fuzzy matching
        """
        try:
            # Use lspci with verbose mode for detailed validation
            result = subprocess.run(
                ["lspci", "-vvnn", "-d", f"{self.INTEL_VENDOR_ID}:"],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode != 0:
                logger.warning("lspci command failed")
                return None

            pci_devices = self._parse_pci_output_securely(result.stdout)

            for device in pci_devices:
                # Strict device ID validation
                if device.get("device_id") in self.INTEL_NPU_DEVICE_IDS:
                    logger.info(
                        f"Verified Intel NPU found: {device['device_id']} at {device['pci_address']}"
                    )
                    return self._create_npu_capabilities_from_validated_pci(device)

            logger.info("No verified Intel NPU devices found via PCI")
            return None

        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ) as e:
            logger.warning(f"PCI detection failed: {e}")
            return None

    def _parse_pci_output_securely(self, pci_output: str) -> List[Dict[str, str]]:
        """Securely parse lspci output with validation"""
        devices = []
        current_device = {}

        for line in pci_output.split("\n"):
            line = line.strip()
            if not line:
                if current_device:
                    devices.append(current_device)
                    current_device = {}
                continue

            # Parse PCI address and device info
            pci_match = re.match(
                r"^([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F])\s+.*\[([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\]",
                line,
            )
            if pci_match:
                pci_address, vendor_id, device_id = pci_match.groups()

                # Validate vendor is Intel
                if vendor_id.lower() == self.INTEL_VENDOR_ID:
                    current_device = {
                        "pci_address": pci_address,
                        "vendor_id": vendor_id,
                        "device_id": f"0x{device_id}",
                        "raw_line": line,
                        "validated": True,
                    }

            # Extract additional device information
            elif current_device and line.startswith("Subsystem:"):
                subsystem_match = re.search(
                    r"\[([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\]", line
                )
                if subsystem_match:
                    current_device["subsystem_vendor"] = subsystem_match.group(1)
                    current_device["subsystem_device"] = subsystem_match.group(2)

        # Add final device
        if current_device:
            devices.append(current_device)

        return devices

    def _create_npu_capabilities_from_validated_pci(
        self, device: Dict[str, str]
    ) -> NPUCapabilities:
        """Create NPU capabilities from validated PCI device"""
        device_id = device["device_id"]
        model_name = self.INTEL_NPU_DEVICE_IDS.get(
            device_id, f"Intel NPU ({device_id})"
        )

        # Get additional device information from sysfs
        sysfs_info = self._get_sysfs_device_info(device["pci_address"])

        return NPUCapabilities(
            model_name=model_name,
            max_tops=self._get_npu_tops_for_device(device_id),
            memory_mb=self._get_npu_memory_for_device(device_id),
            driver_version=self._get_driver_version(),
            device_path=f"/sys/bus/pci/devices/0000:{device['pci_address']}",
            pci_id=device["pci_address"],
            vendor_id=device["vendor_id"],
            device_id=device_id,
            subsystem_vendor=device.get("subsystem_vendor", "unknown"),
            subsystem_device=device.get("subsystem_device", "unknown"),
            supports_fp16=True,
            supports_int8=True,
            supports_int4=device_id in ["0x7d1d"],  # Meteor Lake supports INT4
            max_batch_size=32,
            thermal_design_power=self._get_npu_tdp_for_device(device_id),
            base_frequency_mhz=1000,
            boost_frequency_mhz=1400,
            architecture=self._get_npu_architecture_for_device(device_id),
            features=["inference", "validated_pci", "hardware_verified"],
        )

    def _get_sysfs_device_info(self, pci_address: str) -> Dict[str, str]:
        """Get additional device information from sysfs"""
        sysfs_path = Path(f"/sys/bus/pci/devices/0000:{pci_address}")
        info = {}

        try:
            if (sysfs_path / "vendor").exists():
                with open(sysfs_path / "vendor", "r") as f:
                    info["vendor"] = f.read().strip()

            if (sysfs_path / "device").exists():
                with open(sysfs_path / "device", "r") as f:
                    info["device"] = f.read().strip()

            if (sysfs_path / "class").exists():
                with open(sysfs_path / "class", "r") as f:
                    info["class"] = f.read().strip()

        except (OSError, IOError):
            pass

        return info

    def _get_npu_tops_for_device(self, device_id: str) -> float:
        """Get TOPS rating for specific NPU device"""
        tops_map = {
            "0x7d1d": 11.0,  # Meteor Lake NPU (updated from Intel specs)
            "0x643e": 45.0,  # Lunar Lake NPU
            "0x4f80": 13.0,  # Arrow Lake NPU
            "0x4f81": 13.0,  # Arrow Lake-H NPU
        }
        return tops_map.get(device_id, 11.0)

    def _get_npu_memory_for_device(self, device_id: str) -> int:
        """Get memory allocation for specific NPU device"""
        memory_map = {
            "0x7d1d": 256,  # Meteor Lake
            "0x643e": 512,  # Lunar Lake
            "0x4f80": 256,  # Arrow Lake
            "0x4f81": 256,  # Arrow Lake-H
        }
        return memory_map.get(device_id, 256)

    def _get_npu_tdp_for_device(self, device_id: str) -> float:
        """Get TDP for specific NPU device"""
        tdp_map = {
            "0x7d1d": 4.5,  # Meteor Lake NPU
            "0x643e": 6.0,  # Lunar Lake NPU
            "0x4f80": 4.8,  # Arrow Lake NPU
            "0x4f81": 5.5,  # Arrow Lake-H NPU
        }
        return tdp_map.get(device_id, 4.5)

    def _get_npu_architecture_for_device(self, device_id: str) -> str:
        """Get architecture name for specific NPU device"""
        arch_map = {
            "0x7d1d": "Meteor Lake",
            "0x643e": "Lunar Lake",
            "0x4f80": "Arrow Lake",
            "0x4f81": "Arrow Lake-H",
        }
        return arch_map.get(device_id, "Intel NPU")

    def _detect_npu_via_device_nodes(self) -> Optional[NPUCapabilities]:
        """Detect NPU via device node enumeration"""
        device_paths = [
            "/dev/accel/accel0",
            "/dev/intel-npu",
            "/dev/dri/renderD128",  # Intel GPU that might include NPU
        ]

        for device_path in device_paths:
            path = Path(device_path)
            if path.exists():
                # Verify it's an Intel NPU
                if self._verify_device_is_intel_npu(path):
                    return self._create_npu_capabilities_from_device(device_path)

        return None

    def _detect_npu_via_driver(self) -> Optional[NPUCapabilities]:
        """Detect NPU via loaded kernel modules"""
        try:
            result = subprocess.run(
                ["lsmod"], capture_output=True, text=True, timeout=5
            )

            intel_npu_modules = ["intel_vpu", "intel_npu", "ivpu"]

            for module in intel_npu_modules:
                if module in result.stdout:
                    logger.info(f"Found Intel NPU module: {module}")
                    return self._create_npu_capabilities_from_driver(module)

        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
            logger.debug("Driver detection failed")

        return None

    def _infer_npu_from_cpu(self) -> Optional[NPUCapabilities]:
        """
        SECURITY: Strict PCI validation only - no CPU inference
        CPU inference is unreliable and creates false positives
        """
        logger.info("Skipping CPU inference - using strict PCI validation only")
        return None

    def _verify_device_is_intel_npu(self, device_path: Path) -> bool:
        """Verify device is actually an Intel NPU"""
        # Check sysfs for device information
        device_name = device_path.name

        sysfs_paths = [
            f"/sys/class/accel/{device_name}/device/vendor",
            f"/sys/class/drm/{device_name}/device/vendor",
        ]

        for sysfs_path in sysfs_paths:
            try:
                with open(sysfs_path, "r") as f:
                    vendor_id = f.read().strip()
                    if vendor_id == f"0x{self.INTEL_VENDOR_ID}":
                        return True
            except FileNotFoundError:
                continue

        return False

    def _create_npu_capabilities_from_pci(
        self, pci_line: str, device_id: str
    ) -> NPUCapabilities:
        """Create NPU capabilities from PCI detection"""
        model_name = self.INTEL_NPU_DEVICE_IDS.get(device_id, "Intel NPU (Unknown)")

        # Extract PCI address
        pci_match = re.match(r"^([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F])", pci_line)
        pci_id = pci_match.group(1) if pci_match else "unknown"

        return NPUCapabilities(
            model_name=model_name,
            max_tops=34.0,  # Intel Meteor Lake NPU capability
            memory_mb=256,
            driver_version=self._get_driver_version(),
            device_path=f"/sys/bus/pci/devices/0000:{pci_id}",
            pci_id=pci_id,
            vendor_id=self.INTEL_VENDOR_ID,
            device_id=device_id,
            subsystem_vendor="unknown",
            subsystem_device="unknown",
            supports_fp16=True,
            supports_int8=True,
            supports_int4=True,
            max_batch_size=32,
            thermal_design_power=8.0,  # Estimated TDP for Meteor Lake NPU
            base_frequency_mhz=1000,
            boost_frequency_mhz=1400,
            architecture="Meteor Lake",
            features=["inference", "training", "quantization", "batching"],
        )

    def _create_npu_capabilities_from_device(self, device_path: str) -> NPUCapabilities:
        """Create NPU capabilities from device node"""
        return NPUCapabilities(
            model_name="Intel NPU (Device Node)",
            max_tops=34.0,
            memory_mb=256,
            driver_version=self._get_driver_version(),
            device_path=device_path,
            pci_id="unknown",
            vendor_id=self.INTEL_VENDOR_ID,
            device_id="unknown",
            subsystem_vendor="unknown",
            subsystem_device="unknown",
            supports_fp16=True,
            supports_int8=True,
            supports_int4=True,
            max_batch_size=32,
            thermal_design_power=8.0,
            base_frequency_mhz=1000,
            boost_frequency_mhz=1400,
            architecture="Intel NPU",
            features=["inference", "batching"],
        )

    def _create_npu_capabilities_from_driver(self, module_name: str) -> NPUCapabilities:
        """Create NPU capabilities from driver module"""
        return NPUCapabilities(
            model_name=f"Intel NPU ({module_name} driver)",
            max_tops=34.0,
            memory_mb=256,
            driver_version=self._get_driver_version(),
            device_path="/dev/accel/accel0",
            pci_id="unknown",
            vendor_id=self.INTEL_VENDOR_ID,
            device_id="unknown",
            subsystem_vendor="unknown",
            subsystem_device="unknown",
            supports_fp16=True,
            supports_int8=True,
            supports_int4=True,
            max_batch_size=32,
            thermal_design_power=8.0,
            base_frequency_mhz=1000,
            boost_frequency_mhz=1400,
            architecture="Intel NPU",
            features=["inference", "driver_managed"],
        )

    def _create_inferred_npu_capabilities(self, cpu_pattern: str) -> NPUCapabilities:
        """Create NPU capabilities inferred from CPU"""
        return NPUCapabilities(
            model_name="Intel NPU (Inferred from CPU)",
            max_tops=34.0,
            memory_mb=256,
            driver_version="unknown",
            device_path="/dev/accel/accel0",
            pci_id="unknown",
            vendor_id=self.INTEL_VENDOR_ID,
            device_id="unknown",
            subsystem_vendor="unknown",
            subsystem_device="unknown",
            supports_fp16=True,
            supports_int8=True,
            supports_int4=True,
            max_batch_size=32,
            thermal_design_power=8.0,
            base_frequency_mhz=1000,
            boost_frequency_mhz=1400,
            architecture="Meteor Lake",
            features=["inference", "inferred"],
        )

    def _get_driver_version(self) -> str:
        """Get Intel NPU driver version"""
        version_paths = [
            "/sys/module/intel_vpu/version",
            "/sys/module/intel_npu/version",
            "/proc/version",
        ]

        for path in version_paths:
            try:
                with open(path, "r") as f:
                    return f.read().strip()
            except FileNotFoundError:
                continue

        return "unknown"

    def get_system_optimization_recommendations(self) -> SystemOptimization:
        """
        Generate system optimization recommendations for NPU performance
        """
        cpu_info = self.system_info.get("cpuinfo", "")

        # Detect CPU capabilities
        supports_avx512 = "avx512f" in cpu_info
        supports_avx2 = "avx2" in cpu_info
        supports_fma = "fma" in cpu_info

        # Base optimization recommendations
        compiler_flags = [
            "-O3",
            "-march=native",
            "-mtune=native",
            "-ffast-math",
        ]

        rust_target_features = ["+crt-static"]

        if supports_avx512:
            compiler_flags.extend(
                ["-mavx512f", "-mavx512dq", "-mavx512cd", "-mavx512bw", "-mavx512vl"]
            )
            rust_target_features.extend(["+avx512f", "+avx512dq"])
            cpu_optimization = "skylake-avx512"
        elif supports_avx2:
            compiler_flags.extend(["-mavx2", "-mfma"])
            rust_target_features.extend(["+avx2", "+fma"])
            cpu_optimization = "haswell"
        else:
            cpu_optimization = "x86-64"

        kernel_params = [
            "intel_iommu=on",
            "intel_pstate=performance",
            "processor.max_cstate=1",
            "intel_idle.max_cstate=0",
        ]

        # NPU-specific memory allocation
        npu_memory = 256 if self.detected_npu else 128

        return SystemOptimization(
            cpu_governor="performance",
            cpu_frequency_scaling="performance",
            turbo_boost_enabled=True,
            hyperthreading_enabled=True,
            numa_balancing=False,
            transparent_hugepages="always",
            kernel_parameters=kernel_params,
            compiler_flags=compiler_flags,
            rust_target_features=rust_target_features,
            recommended_memory_allocation=npu_memory,
        )

    def generate_rust_build_config(self) -> Dict[str, Any]:
        """Generate Rust build configuration for optimal NPU bridge compilation"""
        optimization = self.get_system_optimization_recommendations()

        cpu_info = self.system_info.get("cpuinfo", "")
        supports_avx512 = "avx512f" in cpu_info
        supports_avx2 = "avx2" in cpu_info

        if supports_avx512:
            target_cpu = "skylake-avx512"
            target_features = "+avx512f,+avx512dq,+fma"
            rustflags = (
                "-C target-cpu=skylake-avx512 -C target-feature=+avx512f,+avx512dq,+fma"
            )
        elif supports_avx2:
            target_cpu = "haswell"
            target_features = "+avx2,+fma"
            rustflags = "-C target-cpu=haswell -C target-feature=+avx2,+fma"
        else:
            target_cpu = "x86-64"
            target_features = ""
            rustflags = "-C target-cpu=x86-64"

        return {
            "target_triple": "x86_64-unknown-linux-gnu",
            "target_cpu": target_cpu,
            "target_features": target_features,
            "rustflags": f"{rustflags} -C opt-level=3 -C lto=fat -C codegen-units=1",
            "cargo_features": self._get_cargo_features(),
            "environment_vars": {
                "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUSTFLAGS": rustflags,
                "CC": "gcc",
                "CXX": "g++",
                "CFLAGS": " ".join(optimization.compiler_flags),
                "CXXFLAGS": " ".join(optimization.compiler_flags),
            },
        }

    def _get_cargo_features(self) -> List[str]:
        """Get Cargo features based on detected hardware"""
        features = ["python-bindings"]

        if self.detected_npu:
            features.append("intel-npu")

            if "Meteor Lake" in self.detected_npu.architecture:
                features.append("meteor-lake")

            if self.detected_npu.supports_fp16:
                features.append("fp16")

            if self.detected_npu.supports_int8:
                features.append("int8")

        # Check for additional hardware features
        cpu_info = self.system_info.get("cpuinfo", "")
        if "avx512f" in cpu_info:
            features.append("avx512")
        elif "avx2" in cpu_info:
            features.append("avx2")

        return features

    def export_detection_results(self, output_path: str) -> None:
        """Export detection results to JSON file"""
        results = {
            "system_info": self.system_info,
            "npu_capabilities": (
                asdict(self.detected_npu) if self.detected_npu else None
            ),
            "optimization_recommendations": asdict(
                self.get_system_optimization_recommendations()
            ),
            "rust_build_config": self.generate_rust_build_config(),
            "detection_timestamp": __import__("time").time(),
        }

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Detection results exported to: {output_path}")

    def install_optimized_binary(self, install_dir: str = "/usr/local") -> bool:
        """Install optimized binary based on detected hardware"""
        from .npu_binary_installer import NPUBinaryInstaller

        # Determine optimal target based on detection
        build_config = self.generate_rust_build_config()
        target = build_config["target_triple"]

        installer = NPUBinaryInstaller(install_dir=install_dir, force_target=target)

        return installer.install()


def main():
    """Command-line interface for Intel NPU detection"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Intel NPU Hardware Detection and Optimization"
    )
    parser.add_argument(
        "--detect", action="store_true", help="Detect Intel NPU hardware"
    )
    parser.add_argument(
        "--optimize", action="store_true", help="Generate optimization recommendations"
    )
    parser.add_argument(
        "--rust-config", action="store_true", help="Generate Rust build configuration"
    )
    parser.add_argument("--export", metavar="FILE", help="Export results to JSON file")
    parser.add_argument(
        "--install-binary", metavar="DIR", help="Install optimized binary to directory"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    detector = IntelNPUDetector()

    if args.detect or not any(
        [args.optimize, args.rust_config, args.export, args.install_binary]
    ):
        npu = detector.detect_intel_npu()
        if npu:
            print(f"✅ Intel NPU detected: {npu.model_name}")
            print(f"   Max TOPS: {npu.max_tops}")
            print(f"   Memory: {npu.memory_mb} MB")
            print(f"   Device: {npu.device_path}")
            print(f"   Features: {', '.join(npu.features)}")
        else:
            print("❌ No Intel NPU detected")

    if args.optimize:
        optimization = detector.get_system_optimization_recommendations()
        print("\n📊 System Optimization Recommendations:")
        print(f"   CPU Governor: {optimization.cpu_governor}")
        print(f"   Compiler Flags: {' '.join(optimization.compiler_flags)}")
        print(f"   Rust Features: {' '.join(optimization.rust_target_features)}")

    if args.rust_config:
        config = detector.generate_rust_build_config()
        print("\n🔧 Rust Build Configuration:")
        print(f"   Target: {config['target_triple']}")
        print(f"   CPU: {config['target_cpu']}")
        print(f"   Features: {config['target_features']}")
        print(f"   RUSTFLAGS: {config['rustflags']}")

    if args.export:
        detector.export_detection_results(args.export)

    if args.install_binary:
        success = detector.install_optimized_binary(args.install_binary)
        if success:
            print(f"✅ Optimized binary installed to {args.install_binary}")
        else:
            print("❌ Binary installation failed")


if __name__ == "__main__":
    main()
