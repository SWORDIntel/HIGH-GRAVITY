#!/usr/bin/env python3
"""
Unified Hardware Detection System v1.0
Integration with PICMCS v3.0 for seamless orchestrator fallback

Provides comprehensive hardware detection and capability assessment:
- NPU/GNA/GPU detection with OpenVINO integration
- CPU feature detection (AVX2, AVX-512, SSE)
- Memory and thermal monitoring
- Automatic orchestrator selection (NPU vs CPU fallback)
- Performance tier classification

Compatible with PICMCS v3.0 8-level hardware fallback system
"""

import json
import logging
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cpuinfo
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class HardwareCapabilities:
    """Comprehensive hardware capability assessment"""

    # System identification
    system_id: str
    hostname: str
    platform: str
    architecture: str

    # CPU capabilities
    cpu_brand: str
    cpu_cores: int
    cpu_threads: int
    cpu_base_freq: float
    cpu_max_freq: float
    has_avx: bool
    has_avx2: bool
    has_avx512: bool
    has_sse4_2: bool

    # Memory capabilities
    total_memory_gb: float
    available_memory_gb: float
    memory_speed_mhz: Optional[int]

    # AI acceleration
    has_npu: bool
    npu_tops: Optional[float]
    has_gna: bool
    has_gpu_compute: bool
    gpu_memory_gb: Optional[float]

    # OpenVINO support
    openvino_available: bool
    openvino_devices: List[str]
    openvino_version: Optional[str]

    # Thermal and power
    thermal_design_power: Optional[int]
    current_temp_celsius: Optional[float]
    thermal_throttling: bool

    # Performance classification
    performance_tier: str  # 'ultra', 'high', 'medium', 'low', 'constrained'
    orchestrator_mode: str  # 'npu', 'cpu_optimized', 'cpu_basic', 'memory_constrained'
    fallback_level: int  # 1-8 (PICMCS v3.0 compatibility)


@dataclass
class OrchestrationConfig:
    """Orchestrator configuration based on hardware capabilities"""

    mode: str
    max_concurrent_tasks: int
    memory_limit_mb: int
    cpu_threshold: float
    use_npu: bool
    use_gpu: bool
    optimization_level: str
    fallback_enabled: bool


class HardwareDetector:
    """
    Unified hardware detection system with PICMCS v3.0 integration

    Provides comprehensive hardware assessment and automatic
    orchestrator configuration selection
    """

    def __init__(self):
        self.system_info = None
        self.openvino_info = None
        self._detect_all_capabilities()

    def _detect_all_capabilities(self) -> HardwareCapabilities:
        """Perform comprehensive hardware detection"""
        logger.info("🔍 Starting comprehensive hardware detection...")

        try:
            # System identification
            system_id = self._generate_system_id()
            hostname = platform.node()
            platform_name = platform.system()
            architecture = platform.machine()

            # CPU detection
            cpu_info = self._detect_cpu_capabilities()

            # Memory detection
            memory_info = self._detect_memory_capabilities()

            # AI acceleration detection
            ai_info = self._detect_ai_capabilities()

            # OpenVINO detection
            openvino_info = self._detect_openvino_capabilities()

            # Thermal detection
            thermal_info = self._detect_thermal_capabilities()

            # Performance classification
            perf_tier, orchestrator_mode, fallback_level = self._classify_performance(
                cpu_info, memory_info, ai_info, openvino_info
            )

            capabilities = HardwareCapabilities(
                # System
                system_id=system_id,
                hostname=hostname,
                platform=platform_name,
                architecture=architecture,
                # CPU
                cpu_brand=cpu_info["brand"],
                cpu_cores=cpu_info["cores"],
                cpu_threads=cpu_info["threads"],
                cpu_base_freq=cpu_info["base_freq"],
                cpu_max_freq=cpu_info["max_freq"],
                has_avx=cpu_info["has_avx"],
                has_avx2=cpu_info["has_avx2"],
                has_avx512=cpu_info["has_avx512"],
                has_sse4_2=cpu_info["has_sse4_2"],
                # Memory
                total_memory_gb=memory_info["total_gb"],
                available_memory_gb=memory_info["available_gb"],
                memory_speed_mhz=memory_info["speed_mhz"],
                # AI acceleration
                has_npu=ai_info["has_npu"],
                npu_tops=ai_info["npu_tops"],
                has_gna=ai_info["has_gna"],
                has_gpu_compute=ai_info["has_gpu_compute"],
                gpu_memory_gb=ai_info["gpu_memory_gb"],
                # OpenVINO
                openvino_available=openvino_info["available"],
                openvino_devices=openvino_info["devices"],
                openvino_version=openvino_info["version"],
                # Thermal
                thermal_design_power=thermal_info["tdp"],
                current_temp_celsius=thermal_info["current_temp"],
                thermal_throttling=thermal_info["throttling"],
                # Performance
                performance_tier=perf_tier,
                orchestrator_mode=orchestrator_mode,
                fallback_level=fallback_level,
            )

            self.system_info = capabilities
            logger.info(
                f"✅ Hardware detection complete: {perf_tier} tier, {orchestrator_mode} mode"
            )
            return capabilities

        except Exception as e:
            logger.error(f"❌ Hardware detection failed: {e}")
            # Return minimal safe configuration
            return self._get_fallback_capabilities()

    def _generate_system_id(self) -> str:
        """Generate unique system identifier"""
        try:
            # Use MAC address for unique ID
            import uuid

            mac = uuid.getnode()
            return f"sys_{mac:012x}"
        except:
            return f"sys_unknown_{hash(platform.node()) % 10000:04d}"

    def _detect_cpu_capabilities(self) -> Dict[str, Any]:
        """Detect CPU capabilities and features"""
        try:
            # Get CPU info
            info = cpuinfo.get_cpu_info()

            # Basic info
            brand = info.get("brand_raw", "Unknown CPU")
            cores = psutil.cpu_count(logical=False) or 4
            threads = psutil.cpu_count(logical=True) or cores

            # Frequency info
            freq_info = psutil.cpu_freq()
            base_freq = freq_info.current / 1000.0 if freq_info else 2.5
            max_freq = (
                freq_info.max / 1000.0
                if freq_info and freq_info.max
                else base_freq * 1.2
            )

            # Feature detection
            flags = info.get("flags", [])
            has_avx = "avx" in flags
            has_avx2 = "avx2" in flags
            has_avx512 = any("avx512" in flag for flag in flags)
            has_sse4_2 = "sse4_2" in flags

            return {
                "brand": brand,
                "cores": cores,
                "threads": threads,
                "base_freq": base_freq,
                "max_freq": max_freq,
                "has_avx": has_avx,
                "has_avx2": has_avx2,
                "has_avx512": has_avx512,
                "has_sse4_2": has_sse4_2,
            }

        except Exception as e:
            logger.warning(f"CPU detection failed: {e}")
            return {
                "brand": "Unknown CPU",
                "cores": 4,
                "threads": 4,
                "base_freq": 2.5,
                "max_freq": 3.0,
                "has_avx": True,
                "has_avx2": False,
                "has_avx512": False,
                "has_sse4_2": True,
            }

    def _detect_memory_capabilities(self) -> Dict[str, Any]:
        """Detect memory capabilities"""
        try:
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024**3)
            available_gb = memory.available / (1024**3)

            # Try to detect memory speed (Linux-specific)
            speed_mhz = None
            try:
                if platform.system() == "Linux":
                    dmidecode_output = subprocess.run(
                        ["dmidecode", "--type", "memory"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if dmidecode_output.returncode == 0:
                        for line in dmidecode_output.stdout.split("\n"):
                            if "Speed:" in line and "MHz" in line:
                                speed_str = line.split(":")[1].strip()
                                if speed_str != "Unknown":
                                    speed_mhz = int(speed_str.split()[0])
                                    break
            except:
                pass

            return {
                "total_gb": total_gb,
                "available_gb": available_gb,
                "speed_mhz": speed_mhz,
            }

        except Exception as e:
            logger.warning(f"Memory detection failed: {e}")
            return {"total_gb": 8.0, "available_gb": 6.0, "speed_mhz": None}

    def _detect_ai_capabilities(self) -> Dict[str, Any]:
        """Detect AI acceleration hardware"""
        has_npu = False
        npu_tops = None
        has_gna = False
        has_gpu_compute = False
        gpu_memory_gb = None

        try:
            # Check for NPU (Intel AI Boost)
            if platform.system() == "Linux":
                # Check for NPU device files
                npu_devices = [
                    "/dev/accel/accel0",
                    "/dev/dri/renderD128",
                    "/sys/bus/pci/devices/*/class",
                ]

                for device_path in npu_devices:
                    if os.path.exists(device_path):
                        if "accel" in device_path:
                            has_npu = True
                            npu_tops = 11.0  # Intel AI Boost typical
                            break

                # Check for GNA
                if os.path.exists("/dev/gna0") or os.path.exists("/sys/class/gna"):
                    has_gna = True

            # Check for GPU compute (basic detection)
            try:
                # Try to detect GPU via lspci
                lspci_output = subprocess.run(
                    ["lspci"], capture_output=True, text=True, timeout=3
                )
                if lspci_output.returncode == 0:
                    gpu_lines = [
                        line
                        for line in lspci_output.stdout.split("\n")
                        if "VGA" in line or "Display" in line
                    ]
                    if gpu_lines:
                        has_gpu_compute = True
                        # Basic GPU memory estimation
                        if "Intel" in str(gpu_lines):
                            gpu_memory_gb = 1.0  # Integrated graphics
                        else:
                            gpu_memory_gb = 4.0  # Assume discrete GPU
            except:
                pass

        except Exception as e:
            logger.warning(f"AI capability detection failed: {e}")

        return {
            "has_npu": has_npu,
            "npu_tops": npu_tops,
            "has_gna": has_gna,
            "has_gpu_compute": has_gpu_compute,
            "gpu_memory_gb": gpu_memory_gb,
        }

    def _detect_openvino_capabilities(self) -> Dict[str, Any]:
        """Detect OpenVINO availability and supported devices"""
        available = False
        devices = []
        version = None

        try:
            # Try to import OpenVINO
            import openvino as ov

            available = True
            version = ov.__version__

            # Get available devices
            core = ov.Core()
            devices = core.available_devices

            logger.info(f"OpenVINO {version} detected with devices: {devices}")

        except ImportError:
            logger.debug("OpenVINO not available")
        except Exception as e:
            logger.warning(f"OpenVINO detection failed: {e}")

        return {"available": available, "devices": devices, "version": version}

    def _detect_thermal_capabilities(self) -> Dict[str, Any]:
        """Detect thermal and power characteristics"""
        tdp = None
        current_temp = None
        throttling = False

        try:
            # Try to get CPU temperature
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Get first available temperature sensor
                    for sensor_name, sensor_list in temps.items():
                        if sensor_list:
                            current_temp = sensor_list[0].current
                            # Check for throttling (basic heuristic)
                            if current_temp > 85:
                                throttling = True
                            break

            # Try to estimate TDP (very basic)
            cpu_info = cpuinfo.get_cpu_info()
            brand = cpu_info.get("brand_raw", "").lower()
            if "i3" in brand:
                tdp = 65
            elif "i5" in brand:
                tdp = 65
            elif "i7" in brand:
                tdp = 125
            elif "i9" in brand:
                tdp = 125
            elif "ultra" in brand:
                tdp = 28  # Intel Core Ultra (mobile)

        except Exception as e:
            logger.warning(f"Thermal detection failed: {e}")

        return {"tdp": tdp, "current_temp": current_temp, "throttling": throttling}

    def _classify_performance(
        self, cpu_info: Dict, memory_info: Dict, ai_info: Dict, openvino_info: Dict
    ) -> Tuple[str, str, int]:
        """Classify system performance and determine orchestrator mode"""

        # Calculate performance score
        score = 0

        # CPU contribution (0-40 points)
        score += min(cpu_info["cores"] * 2, 20)  # Up to 10 cores = 20 points
        score += min(cpu_info["max_freq"] * 4, 20)  # Up to 5GHz = 20 points

        # Memory contribution (0-30 points)
        score += min(memory_info["total_gb"] * 2, 30)  # Up to 15GB = 30 points

        # AI acceleration (0-30 points)
        if ai_info["has_npu"]:
            score += 30
        elif ai_info["has_gpu_compute"]:
            score += 20
        elif ai_info["has_gna"]:
            score += 15

        # Determine performance tier
        if score >= 80:
            performance_tier = "ultra"
            fallback_level = 1
        elif score >= 60:
            performance_tier = "high"
            fallback_level = 2
        elif score >= 40:
            performance_tier = "medium"
            fallback_level = 3
        elif score >= 25:
            performance_tier = "low"
            fallback_level = 4
        else:
            performance_tier = "constrained"
            fallback_level = 5

        # Determine orchestrator mode
        if ai_info["has_npu"] and openvino_info["available"]:
            orchestrator_mode = "npu"
        elif cpu_info["has_avx2"] and memory_info["total_gb"] >= 8:
            orchestrator_mode = "cpu_optimized"
        elif memory_info["total_gb"] >= 4:
            orchestrator_mode = "cpu_basic"
        else:
            orchestrator_mode = "memory_constrained"
            fallback_level = max(fallback_level, 6)

        return performance_tier, orchestrator_mode, fallback_level

    def _get_fallback_capabilities(self) -> HardwareCapabilities:
        """Return safe fallback capabilities for failed detection"""
        return HardwareCapabilities(
            system_id="sys_fallback",
            hostname="unknown",
            platform="Unknown",
            architecture="x86_64",
            cpu_brand="Generic CPU",
            cpu_cores=4,
            cpu_threads=4,
            cpu_base_freq=2.5,
            cpu_max_freq=3.0,
            has_avx=True,
            has_avx2=False,
            has_avx512=False,
            has_sse4_2=True,
            total_memory_gb=8.0,
            available_memory_gb=6.0,
            memory_speed_mhz=None,
            has_npu=False,
            npu_tops=None,
            has_gna=False,
            has_gpu_compute=False,
            gpu_memory_gb=None,
            openvino_available=False,
            openvino_devices=[],
            openvino_version=None,
            thermal_design_power=65,
            current_temp_celsius=None,
            thermal_throttling=False,
            performance_tier="medium",
            orchestrator_mode="cpu_basic",
            fallback_level=4,
        )

    def get_orchestration_config(self) -> OrchestrationConfig:
        """Generate orchestrator configuration based on detected hardware"""
        if not self.system_info:
            self.system_info = self._detect_all_capabilities()

        caps = self.system_info

        # Configure based on orchestrator mode
        if caps.orchestrator_mode == "npu":
            config = OrchestrationConfig(
                mode="npu",
                max_concurrent_tasks=16,
                memory_limit_mb=4096,
                cpu_threshold=0.8,
                use_npu=True,
                use_gpu=caps.has_gpu_compute,
                optimization_level="maximum",
                fallback_enabled=True,
            )
        elif caps.orchestrator_mode == "cpu_optimized":
            config = OrchestrationConfig(
                mode="cpu_optimized",
                max_concurrent_tasks=min(caps.cpu_cores * 2, 12),
                memory_limit_mb=min(int(caps.total_memory_gb * 512), 8192),
                cpu_threshold=0.75,
                use_npu=False,
                use_gpu=False,
                optimization_level="high",
                fallback_enabled=True,
            )
        elif caps.orchestrator_mode == "cpu_basic":
            config = OrchestrationConfig(
                mode="cpu_basic",
                max_concurrent_tasks=min(caps.cpu_cores, 8),
                memory_limit_mb=min(int(caps.total_memory_gb * 256), 2048),
                cpu_threshold=0.7,
                use_npu=False,
                use_gpu=False,
                optimization_level="moderate",
                fallback_enabled=True,
            )
        else:  # memory_constrained
            config = OrchestrationConfig(
                mode="memory_constrained",
                max_concurrent_tasks=2,
                memory_limit_mb=512,
                cpu_threshold=0.8,
                use_npu=False,
                use_gpu=False,
                optimization_level="minimal",
                fallback_enabled=True,
            )

        return config

    def get_capabilities(self) -> HardwareCapabilities:
        """Get detected hardware capabilities"""
        if not self.system_info:
            self.system_info = self._detect_all_capabilities()
        return self.system_info

    def save_detection_report(self, filepath: str):
        """Save comprehensive detection report to file"""
        if not self.system_info:
            self.system_info = self._detect_all_capabilities()

        config = self.get_orchestration_config()

        report = {
            "hardware_capabilities": asdict(self.system_info),
            "orchestration_config": asdict(config),
            "detection_timestamp": time.time(),
            "picmcs_fallback_level": self.system_info.fallback_level,
            "recommended_mode": self.system_info.orchestrator_mode,
        }

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Hardware detection report saved to {filepath}")


def main():
    """Demo and testing function"""
    print("🔍 Unified Hardware Detection System v1.0")
    print("=" * 50)

    # Initialize detector
    detector = HardwareDetector()

    # Get capabilities
    caps = detector.get_capabilities()
    config = detector.get_orchestration_config()

    # Display results
    print(f"\n🖥️  System Information:")
    print(f"Platform: {caps.platform} ({caps.architecture})")
    print(f"CPU: {caps.cpu_brand}")
    print(f"Cores: {caps.cpu_cores} physical, {caps.cpu_threads} logical")
    print(f"Frequency: {caps.cpu_base_freq:.1f} - {caps.cpu_max_freq:.1f} GHz")
    print(
        f"Memory: {caps.total_memory_gb:.1f} GB total, {caps.available_memory_gb:.1f} GB available"
    )

    print(f"\n🚀 AI Acceleration:")
    print(
        f"NPU: {'✅' if caps.has_npu else '❌'} {f'({caps.npu_tops} TOPS)' if caps.npu_tops else ''}"
    )
    print(f"GNA: {'✅' if caps.has_gna else '❌'}")
    print(
        f"GPU Compute: {'✅' if caps.has_gpu_compute else '❌'} {f'({caps.gpu_memory_gb} GB)' if caps.gpu_memory_gb else ''}"
    )
    print(
        f"OpenVINO: {'✅' if caps.openvino_available else '❌'} {f'v{caps.openvino_version}' if caps.openvino_version else ''}"
    )

    print(f"\n🏃 CPU Features:")
    print(f"AVX: {'✅' if caps.has_avx else '❌'}")
    print(f"AVX2: {'✅' if caps.has_avx2 else '❌'}")
    print(f"AVX-512: {'✅' if caps.has_avx512 else '❌'}")
    print(f"SSE 4.2: {'✅' if caps.has_sse4_2 else '❌'}")

    print(f"\n📊 Performance Classification:")
    print(f"Performance Tier: {caps.performance_tier.upper()}")
    print(f"Orchestrator Mode: {caps.orchestrator_mode}")
    print(f"PICMCS Fallback Level: {caps.fallback_level}/8")

    print(f"\n⚙️  Recommended Configuration:")
    print(f"Mode: {config.mode}")
    print(f"Max Concurrent Tasks: {config.max_concurrent_tasks}")
    print(f"Memory Limit: {config.memory_limit_mb} MB")
    print(f"CPU Threshold: {config.cpu_threshold*100:.0f}%")
    print(f"NPU Enabled: {'✅' if config.use_npu else '❌'}")
    print(f"GPU Enabled: {'✅' if config.use_gpu else '❌'}")
    print(f"Optimization Level: {config.optimization_level}")

    # Save report
    report_path = "hardware_detection_report.json"
    detector.save_detection_report(report_path)
    print(f"\n💾 Report saved to: {report_path}")


if __name__ == "__main__":
    import time

    main()
