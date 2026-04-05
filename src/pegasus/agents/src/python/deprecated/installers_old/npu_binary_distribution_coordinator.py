#!/usr/bin/env python3
"""
NPU Binary Distribution Coordinator
Strategic oversight and integration of all NPU bridge distribution components
Orchestrates the complete pre-compiled binary distribution system
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
import logging

# Import our specialized components
from intel_npu_hardware_detector import IntelNPUDetector, NPUCapabilities
from npu_binary_installer import NPUBinaryInstaller
from npu_release_manager import NPUReleaseManager, ReleaseInfo
from npu_fallback_compiler import NPUFallbackCompiler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_npu_bridge_source():
    """Get NPU bridge source directory dynamically"""
    from pathlib import Path
    current = Path(__file__).resolve().parent
    while current != current.parent:
        rust_path = current / "agents" / "src" / "rust" / "npu_coordination_bridge"
        if rust_path.exists():
            return str(rust_path)
        current = current.parent
    return str(Path(__file__).parent.parent / "rust" / "npu_coordination_bridge")


@dataclass
class InstallationStrategy:
    """Installation strategy decision"""
    method: str  # "binary", "fallback_compile", "abort"
    reasoning: str
    confidence: float  # 0.0 to 1.0
    estimated_time_seconds: int
    requirements: List[str]
    alternatives: List[str]

@dataclass
class InstallationResult:
    """Complete installation result"""
    success: bool
    method_used: str
    duration_seconds: float
    installed_files: List[str]
    performance_features: List[str]
    error_details: Optional[str]
    npu_capabilities: Optional[NPUCapabilities]
    system_optimization_applied: bool

class NPUBinaryDistributionCoordinator:
    """
    Strategic coordinator for NPU bridge binary distribution

    Orchestrates the complete system:
    1. Hardware detection and optimization
    2. Release management and binary discovery
    3. Fast binary installation or intelligent fallback compilation
    4. System optimization and verification
    """

    def __init__(self,
                 repo_owner: str = "SWORDIntel",
                 repo_name: str = "claude-backups",
                 github_token: Optional[str] = None,
                 install_dir: str = "/usr/local",
                 force_compilation: bool = False):

        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_token = github_token
        self.install_dir = install_dir
        self.force_compilation = force_compilation

        # Initialize components
        self.hardware_detector = IntelNPUDetector()
        self.release_manager = NPUReleaseManager(repo_owner, repo_name, github_token)
        self.start_time = time.time()

        # State tracking
        self.detected_npu: Optional[NPUCapabilities] = None
        self.selected_strategy: Optional[InstallationStrategy] = None
        self.installation_result: Optional[InstallationResult] = None

    def detect_and_analyze_system(self) -> Dict[str, Any]:
        """Comprehensive system detection and analysis"""
        logger.info("🔍 Detecting system capabilities and NPU hardware...")

        # Detect NPU hardware
        self.detected_npu = self.hardware_detector.detect_intel_npu()

        # Get system optimization recommendations
        optimization = self.hardware_detector.get_system_optimization_recommendations()

        # Generate Rust build configuration
        rust_config = self.hardware_detector.generate_rust_build_config()

        analysis = {
            "npu_detected": self.detected_npu is not None,
            "npu_capabilities": asdict(self.detected_npu) if self.detected_npu else None,
            "system_optimization": asdict(optimization),
            "rust_build_config": rust_config,
            "performance_score": self._calculate_performance_score(),
            "installation_complexity": self._assess_installation_complexity(),
        }

        if self.detected_npu:
            logger.info(f"✅ Intel NPU detected: {self.detected_npu.model_name}")
            logger.info(f"   Max TOPS: {self.detected_npu.max_tops}")
            logger.info(f"   Memory: {self.detected_npu.memory_mb} MB")
            logger.info(f"   Features: {', '.join(self.detected_npu.features)}")
        else:
            logger.warning("❌ No Intel NPU detected - basic functionality only")

        return analysis

    def _calculate_performance_score(self) -> float:
        """Calculate overall system performance score (0.0 to 1.0)"""
        score = 0.0

        # NPU contribution (40%)
        if self.detected_npu:
            score += 0.4
            if self.detected_npu.max_tops >= 30:
                score += 0.1  # Bonus for high-performance NPU

        # CPU features contribution (40%)
        rust_config = self.hardware_detector.generate_rust_build_config()
        if "avx512" in rust_config.get("target_features", ""):
            score += 0.4
        elif "avx2" in rust_config.get("target_features", ""):
            score += 0.3
        elif "avx" in rust_config.get("target_features", ""):
            score += 0.2
        else:
            score += 0.1

        # Memory contribution (20%)
        system_info = self.hardware_detector.system_info
        cpu_count = system_info.get("cpu_count", 1)
        if cpu_count >= 8:
            score += 0.2
        elif cpu_count >= 4:
            score += 0.15
        else:
            score += 0.1

        return min(score, 1.0)

    def _assess_installation_complexity(self) -> str:
        """Assess installation complexity level"""
        # Check for common issues
        detector = NPUFallbackCompiler(
            get_npu_bridge_source()
        )
        fallback_reasons = detector.detect_fallback_reason()

        if not fallback_reasons:
            return "simple"
        elif len(fallback_reasons) <= 2:
            return "moderate"
        else:
            return "complex"

    def determine_installation_strategy(self, analysis: Dict[str, Any]) -> InstallationStrategy:
        """Determine optimal installation strategy"""
        logger.info("🎯 Determining optimal installation strategy...")

        if self.force_compilation:
            return InstallationStrategy(
                method="fallback_compile",
                reasoning="Forced compilation requested by user",
                confidence=1.0,
                estimated_time_seconds=600,  # 10 minutes
                requirements=["rust", "gcc", "time"],
                alternatives=["binary"]
            )

        # Try binary installation first
        latest_release = self.release_manager.get_latest_release()
        if latest_release:
            # Check if we have a compatible binary
            rust_config = analysis["rust_build_config"]
            target_platform = rust_config["target_triple"]

            compatible_asset = self.release_manager.find_best_asset_for_platform(
                latest_release, target_platform
            )

            if compatible_asset:
                return InstallationStrategy(
                    method="binary",
                    reasoning=f"Compatible pre-built binary available: {compatible_asset.name}",
                    confidence=0.9,
                    estimated_time_seconds=30,  # 30 seconds
                    requirements=["curl", "tar"],
                    alternatives=["fallback_compile"]
                )

        # Check if fallback compilation is viable
        complexity = analysis["installation_complexity"]
        if complexity in ["simple", "moderate"]:
            return InstallationStrategy(
                method="fallback_compile",
                reasoning=f"No compatible binary found, fallback compilation viable ({complexity} complexity)",
                confidence=0.7,
                estimated_time_seconds=300 if complexity == "simple" else 600,
                requirements=["rust", "gcc", "cmake", "time"],
                alternatives=[]
            )

        # Last resort: abort with detailed explanation
        return InstallationStrategy(
            method="abort",
            reasoning="System not compatible for either binary installation or compilation",
            confidence=1.0,
            estimated_time_seconds=0,
            requirements=[],
            alternatives=["manual_installation", "docker_container"]
        )

    def execute_installation_strategy(self, strategy: InstallationStrategy) -> InstallationResult:
        """Execute the determined installation strategy"""
        logger.info(f"🚀 Executing installation strategy: {strategy.method}")
        logger.info(f"   Reasoning: {strategy.reasoning}")
        logger.info(f"   Estimated time: {strategy.estimated_time_seconds} seconds")

        start_time = time.time()

        if strategy.method == "binary":
            return self._execute_binary_installation()
        elif strategy.method == "fallback_compile":
            return self._execute_fallback_compilation()
        elif strategy.method == "abort":
            return InstallationResult(
                success=False,
                method_used="abort",
                duration_seconds=time.time() - start_time,
                installed_files=[],
                performance_features=[],
                error_details=strategy.reasoning,
                npu_capabilities=self.detected_npu,
                system_optimization_applied=False
            )
        else:
            raise ValueError(f"Unknown installation method: {strategy.method}")

    def _execute_binary_installation(self) -> InstallationResult:
        """Execute binary installation"""
        logger.info("📦 Installing pre-compiled binary...")

        start_time = time.time()
        error_details = None
        installed_files = []

        try:
            # Use the binary installer
            installer = NPUBinaryInstaller(
                install_dir=self.install_dir,
                version="latest"
            )

            success = installer.install()

            if success:
                # Find installed files
                bin_dir = Path(self.install_dir) / "bin"
                lib_dir = Path(self.install_dir) / "lib"

                for directory in [bin_dir, lib_dir]:
                    if directory.exists():
                        for file_path in directory.glob("*npu*"):
                            installed_files.append(str(file_path))

                # Extract performance features from build info
                performance_features = self._extract_performance_features_from_binary()

            else:
                error_details = "Binary installation failed"

        except Exception as e:
            success = False
            error_details = str(e)

        return InstallationResult(
            success=success,
            method_used="binary",
            duration_seconds=time.time() - start_time,
            installed_files=installed_files,
            performance_features=performance_features if success else [],
            error_details=error_details,
            npu_capabilities=self.detected_npu,
            system_optimization_applied=False
        )

    def _execute_fallback_compilation(self) -> InstallationResult:
        """Execute fallback compilation"""
        logger.info("🔨 Compiling from source (fallback)...")

        start_time = time.time()
        error_details = None
        installed_files = []
        performance_features = []

        try:
            compiler = NPUFallbackCompiler(
                source_dir=get_npu_bridge_source(),
                output_dir=None
            )

            success = compiler.run_fallback_compilation(self.install_dir)

            if success:
                # Find installed files
                bin_dir = Path(self.install_dir) / "bin"
                lib_dir = Path(self.install_dir) / "lib"

                for directory in [bin_dir, lib_dir]:
                    if directory.exists():
                        for file_path in directory.glob("*npu*"):
                            installed_files.append(str(file_path))

                # Get performance features from compilation config
                fallback_reasons = compiler.detect_fallback_reason()
                config = compiler.generate_compilation_config(fallback_reasons)
                performance_features = config.features

            else:
                error_details = "Fallback compilation failed"

        except Exception as e:
            success = False
            error_details = str(e)

        return InstallationResult(
            success=success,
            method_used="fallback_compile",
            duration_seconds=time.time() - start_time,
            installed_files=installed_files,
            performance_features=performance_features,
            error_details=error_details,
            npu_capabilities=self.detected_npu,
            system_optimization_applied=False
        )

    def _extract_performance_features_from_binary(self) -> List[str]:
        """Extract performance features from installed binary"""
        features = []

        # Check build info if available
        config_dir = Path(self.install_dir) / "etc" / "npu-bridge"
        build_info_file = config_dir / "BUILD_INFO.json"

        if build_info_file.exists():
            try:
                with open(build_info_file, 'r') as f:
                    build_info = json.load(f)
                    features = build_info.get("features", [])
            except (json.JSONDecodeError, IOError):
                pass

        # Fallback: infer from hardware detection
        if not features and self.detected_npu:
            features = ["intel-npu"]
            if "avx512" in self.hardware_detector.system_info.get("cpuinfo", ""):
                features.append("avx512")
            elif "avx2" in self.hardware_detector.system_info.get("cpuinfo", ""):
                features.append("avx2")

        return features

    def apply_system_optimizations(self) -> bool:
        """Apply system-level optimizations for NPU performance"""
        logger.info("⚡ Applying system optimizations...")

        optimization = self.hardware_detector.get_system_optimization_recommendations()

        success_count = 0
        total_optimizations = 0

        # Apply CPU governor settings
        total_optimizations += 1
        if self._apply_cpu_governor(optimization.cpu_governor):
            success_count += 1

        # Apply kernel parameters (if possible)
        total_optimizations += 1
        if self._suggest_kernel_parameters(optimization.kernel_parameters):
            success_count += 1

        # Set environment variables for optimal performance
        total_optimizations += 1
        if self._set_performance_env_vars():
            success_count += 1

        success_rate = success_count / total_optimizations if total_optimizations > 0 else 0
        logger.info(f"Applied {success_count}/{total_optimizations} optimizations ({success_rate:.0%})")

        return success_rate >= 0.5

    def _apply_cpu_governor(self, governor: str) -> bool:
        """Apply CPU governor setting"""
        try:
            # Check if we can modify CPU governor
            if os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"):
                # Try to set governor (may require sudo)
                result = subprocess.run([
                    "sudo", "cpupower", "frequency-set", "-g", governor
                ], capture_output=True, timeout=10)

                if result.returncode == 0:
                    logger.info(f"CPU governor set to: {governor}")
                    return True
                else:
                    logger.warning(f"Could not set CPU governor (may require sudo)")
                    return False
            else:
                logger.info("CPU frequency scaling not available")
                return False
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Could not modify CPU governor")
            return False

    def _suggest_kernel_parameters(self, kernel_params: List[str]) -> bool:
        """Suggest kernel parameters for optimization"""
        if kernel_params:
            logger.info("💡 Suggested kernel parameters for optimal NPU performance:")
            for param in kernel_params:
                logger.info(f"   {param}")
            logger.info("Add these to GRUB_CMDLINE_LINUX in /etc/default/grub and run 'sudo update-grub'")

        return True  # Always return true for suggestions

    def _set_performance_env_vars(self) -> bool:
        """Set environment variables for performance"""
        env_vars = {
            "OMP_NUM_THREADS": str(os.cpu_count() or 4),
            "NPU_OPTIMIZATION": "1",
            "INTEL_NPU_ENABLE": "1" if self.detected_npu else "0",
        }

        for var, value in env_vars.items():
            os.environ[var] = value

        logger.info(f"Set {len(env_vars)} performance environment variables")
        return True

    def verify_installation(self) -> bool:
        """Verify installation success and functionality"""
        logger.info("🔍 Verifying installation...")

        # Check if binary exists and is executable
        server_binary = Path(self.install_dir) / "bin" / "npu-bridge-server"
        if not server_binary.exists():
            logger.error("NPU bridge server binary not found")
            return False

        # Test binary execution
        try:
            result = subprocess.run([
                str(server_binary), "--version"
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logger.info(f"✅ Binary verification successful")
                logger.info(f"   Version output: {result.stdout.strip()}")

                # Optional: Run quick health check
                health_result = subprocess.run([
                    str(server_binary), "--health-check"
                ], capture_output=True, text=True, timeout=15)

                if health_result.returncode == 0:
                    logger.info("✅ Health check passed")
                else:
                    logger.warning("⚠️ Health check failed (NPU hardware may not be available)")

                return True
            else:
                logger.error(f"Binary execution failed: {result.stderr}")
                return False

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.error(f"Binary verification error: {e}")
            return False

    def run_complete_installation(self) -> InstallationResult:
        """Run the complete installation workflow"""
        logger.info("🚀 Starting NPU Bridge Binary Distribution System")
        logger.info(f"   Repository: {self.repo_owner}/{self.repo_name}")
        logger.info(f"   Install directory: {self.install_dir}")

        try:
            # Step 1: System detection and analysis
            analysis = self.detect_and_analyze_system()
            logger.info(f"   Performance score: {analysis['performance_score']:.2f}")
            logger.info(f"   Complexity: {analysis['installation_complexity']}")

            # Step 2: Determine strategy
            self.selected_strategy = self.determine_installation_strategy(analysis)
            logger.info(f"   Selected strategy: {self.selected_strategy.method}")

            # Step 3: Execute installation
            self.installation_result = self.execute_installation_strategy(self.selected_strategy)

            if self.installation_result.success:
                # Step 4: Apply optimizations
                opt_success = self.apply_system_optimizations()
                self.installation_result.system_optimization_applied = opt_success

                # Step 5: Verify installation
                verification_success = self.verify_installation()

                if verification_success:
                    total_time = time.time() - self.start_time
                    logger.info(f"✅ Complete installation successful in {total_time:.1f} seconds")
                    logger.info(f"   Method: {self.installation_result.method_used}")
                    logger.info(f"   Features: {', '.join(self.installation_result.performance_features)}")
                    logger.info(f"   Files installed: {len(self.installation_result.installed_files)}")

                    if self.detected_npu:
                        logger.info(f"   NPU: {self.detected_npu.model_name} ({self.detected_npu.max_tops} TOPS)")

                    logger.info("🎉 NPU Bridge is ready for use!")
                    logger.info("   Run 'npu-bridge-server --help' to get started")

                else:
                    logger.error("❌ Installation verification failed")
                    self.installation_result.success = False
                    self.installation_result.error_details = "Verification failed"

            return self.installation_result

        except Exception as e:
            logger.error(f"💥 Installation failed with error: {e}")
            return InstallationResult(
                success=False,
                method_used="error",
                duration_seconds=time.time() - self.start_time,
                installed_files=[],
                performance_features=[],
                error_details=str(e),
                npu_capabilities=self.detected_npu,
                system_optimization_applied=False
            )

    def generate_installation_report(self) -> Dict[str, Any]:
        """Generate comprehensive installation report"""
        return {
            "installation_result": asdict(self.installation_result) if self.installation_result else None,
            "selected_strategy": asdict(self.selected_strategy) if self.selected_strategy else None,
            "detected_npu": asdict(self.detected_npu) if self.detected_npu else None,
            "system_analysis": self.detect_and_analyze_system(),
            "timestamp": time.time(),
            "total_duration": time.time() - self.start_time,
        }


def main():
    """Command-line interface for NPU binary distribution coordinator"""
    import argparse

    parser = argparse.ArgumentParser(
        description="NPU Bridge Binary Distribution Coordinator"
    )
    parser.add_argument(
        "--install-dir",
        default="/usr/local",
        help="Installation directory (default: /usr/local)"
    )
    parser.add_argument(
        "--repo",
        default="SWORDIntel/claude-backups",
        help="GitHub repository (owner/name)"
    )
    parser.add_argument(
        "--force-compile",
        action="store_true",
        help="Force compilation instead of using pre-built binaries"
    )
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Only detect system capabilities"
    )
    parser.add_argument(
        "--report",
        metavar="FILE",
        help="Generate installation report to file"
    )
    parser.add_argument(
        "--github-token",
        help="GitHub token for API access"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse repository
    if '/' in args.repo:
        repo_owner, repo_name = args.repo.split('/', 1)
    else:
        repo_owner, repo_name = "SWORDIntel", args.repo

    coordinator = NPUBinaryDistributionCoordinator(
        repo_owner=repo_owner,
        repo_name=repo_name,
        github_token=args.github_token,
        install_dir=args.install_dir,
        force_compilation=args.force_compile
    )

    if args.detect_only:
        analysis = coordinator.detect_and_analyze_system()
        print("🔍 System Analysis:")
        print(f"   NPU Detected: {'✅' if analysis['npu_detected'] else '❌'}")
        print(f"   Performance Score: {analysis['performance_score']:.2f}")
        print(f"   Installation Complexity: {analysis['installation_complexity']}")

        if coordinator.detected_npu:
            npu = coordinator.detected_npu
            print(f"   NPU Model: {npu.model_name}")
            print(f"   Max TOPS: {npu.max_tops}")
            print(f"   Memory: {npu.memory_mb} MB")

        strategy = coordinator.determine_installation_strategy(analysis)
        print(f"\n🎯 Recommended Strategy: {strategy.method}")
        print(f"   Reasoning: {strategy.reasoning}")
        print(f"   Confidence: {strategy.confidence:.0%}")
        print(f"   Estimated Time: {strategy.estimated_time_seconds} seconds")

    else:
        # Run complete installation
        result = coordinator.run_complete_installation()

        if args.report:
            report = coordinator.generate_installation_report()
            with open(args.report, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"📊 Installation report saved to: {args.report}")

        sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()