#!/usr/bin/env python3
"""
C-INTERNAL Agent Implementation
==============================

Elite C/C++ Systems Engineering Agent with Hardware Optimization
Leverages PYTHON-INTERNAL environment management and CONSTRUCTOR patterns

Author: Claude Agent Framework
Version: 1.0.0
Classification: UNCLASSIFIED//FOR_OFFICIAL_USE_ONLY
Agent: C-INTERNAL
"""

import asyncio
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import psutil

# Advanced system monitoring
try:
    import gputil

    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False


class OptimizationLevel(Enum):
    """Compilation optimization levels"""

    DEBUG = "debug"
    RELEASE = "release"
    PERFORMANCE = "performance"
    SIZE = "size"
    SECURITY = "security"


class ToolchainType(Enum):
    """Supported C/C++ toolchains"""

    GCC = "gcc"
    CLANG = "clang"
    MSVC = "msvc"
    ICC = "icc"
    MINGW = "mingw"


class ThermalState(Enum):
    """CPU thermal states for optimization"""

    NORMAL = "normal"  # <75°C
    WARM = "warm"  # 75-85°C
    HOT = "hot"  # 85-95°C
    CRITICAL = "critical"  # >95°C


@dataclass
class CompilerInfo:
    """Comprehensive compiler information"""

    name: str
    version: str
    path: str
    type: ToolchainType
    target_arch: str
    capabilities: List[str]
    optimization_flags: Dict[str, List[str]]
    is_cross_compiler: bool = False


@dataclass
class ProjectSpec:
    """C/C++ project specification"""

    name: str
    language: str  # 'c' or 'cpp'
    type: str  # 'executable', 'static_lib', 'shared_lib'
    sources: List[str]
    headers: List[str]
    dependencies: List[str]
    optimization_level: OptimizationLevel
    target_arch: str
    custom_flags: List[str]


@dataclass
class BuildResult:
    """Build operation result"""

    success: bool
    build_time: float
    binary_path: Optional[str]
    binary_size: int
    warnings: List[str]
    errors: List[str]
    performance_metrics: Dict[str, Any]


@dataclass
class ThermalProfile:
    """System thermal profile"""

    cpu_temp: float
    thermal_state: ThermalState
    throttle_level: float
    recommended_cores: int
    max_optimization: OptimizationLevel


class CInternalAgent:
    """
    Elite C/C++ Systems Engineering Agent

    Advanced C/C++ development environment with:
    - Adaptive toolchain detection and management
    - Hardware-aware compilation optimization
    - Thermal-aware performance tuning
    - Multi-agent orchestration capabilities
    - Real-time performance monitoring
    """

    def __init__(self):
        self.agent_id = str(uuid.uuid4())
        self.name = "C-INTERNAL"
        self.version = "1.0.0"
        self.classification = "UNCLASSIFIED//FOR_OFFICIAL_USE_ONLY"

        # Core capabilities
        self.capabilities = {
            "c_compilation": True,
            "cpp_compilation": True,
            "cross_compilation": True,
            "optimization": True,
            "profiling": True,
            "debugging": True,
            "static_analysis": True,
            "binary_analysis": True,
            "hardware_optimization": True,
            "thermal_management": True,
        }

        # Performance tracking
        self.metrics = {
            "compilations_completed": 0,
            "successful_builds": 0,
            "optimization_saves": 0,
            "thermal_throttles": 0,
            "binary_optimizations": 0,
            "average_build_time": 0.0,
            "total_code_generated": 0,
            "cross_platform_builds": 0,
        }

        # System resources
        self.cpu_count = psutil.cpu_count()
        self.memory_gb = psutil.virtual_memory().total // (1024**3)
        self.platform_info = self._detect_platform()

        # Toolchain management
        self.detected_compilers = {}
        self.active_toolchain = None
        self.toolchain_cache = {}

        # Thermal management
        self.thermal_monitor = ThermalMonitor()
        self.thermal_profile = None

        # Build cache and optimization
        self.build_cache = {}
        self.optimization_profiles = self._load_optimization_profiles()

        # Agent coordination
        self.coordinated_agents = set()
        self.orchestration_tasks = []

        # Initialize logging
        self._setup_logging()

        # Initialize components
        self._initialize_sync()

    def _setup_logging(self):
        """Configure comprehensive logging"""
        log_dir = Path.home() / ".c_internal_logs"
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - C-INTERNAL - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(
                    log_dir / f'c_internal_{datetime.now().strftime("%Y%m%d")}.log'
                ),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def _initialize_sync(self):
        """Synchronous initialization of agent components"""
        self.logger.info("Initializing C-INTERNAL Agent...")

        # Basic initialization - async methods will be called when needed
        self.logger.info(
            "C-INTERNAL Agent initialized - async components will load on demand"
        )

    async def _initialize_async(self):
        """Async initialization of agent components"""
        if len(self.detected_compilers) == 0:  # Only initialize once
            self.logger.info("Loading async components...")

            # Detect available toolchains
            await self._detect_toolchains()

            # Initialize thermal monitoring
            await self.thermal_monitor.initialize()

            # Setup hardware optimization
            await self._setup_hardware_optimization()

            self.logger.info(
                f"C-INTERNAL Agent fully initialized with {len(self.detected_compilers)} compilers"
            )

    def _detect_platform(self) -> Dict[str, Any]:
        """Detect comprehensive platform information"""
        info = {
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "architecture": platform.architecture(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_gb": psutil.virtual_memory().total // (1024**3),
        }

        # Detect Intel Meteor Lake specific features
        if "Intel" in info.get("processor", ""):
            info["intel_features"] = self._detect_intel_features()

        return info

    def _detect_intel_features(self) -> Dict[str, bool]:
        """Detect Intel-specific CPU features"""
        features = {
            "avx512": False,
            "avx2": True,  # Assume available on modern Intel
            "sse4_2": True,
            "aes_ni": True,
            "meteor_lake": False,
        }

        try:
            # Check CPU info for specific features
            with open("/proc/cpuinfo", "r") as f:
                cpu_info = f.read()
                if "avx512" in cpu_info:
                    features["avx512"] = True
                if "meteor" in cpu_info.lower():
                    features["meteor_lake"] = True
        except:
            pass

        return features

    async def _detect_toolchains(self):
        """Detect available C/C++ toolchains"""
        self.logger.info("Detecting available toolchains...")

        toolchain_candidates = [
            ("gcc", ToolchainType.GCC),
            ("g++", ToolchainType.GCC),
            ("clang", ToolchainType.CLANG),
            ("clang++", ToolchainType.CLANG),
            ("icc", ToolchainType.ICC),
            ("icpc", ToolchainType.ICC),
        ]

        for binary, toolchain_type in toolchain_candidates:
            compiler_info = await self._analyze_compiler(binary, toolchain_type)
            if compiler_info:
                self.detected_compilers[binary] = compiler_info

        # Set default active toolchain
        if "gcc" in self.detected_compilers:
            self.active_toolchain = self.detected_compilers["gcc"]
        elif "clang" in self.detected_compilers:
            self.active_toolchain = self.detected_compilers["clang"]

        self.logger.info(f"Detected {len(self.detected_compilers)} compilers")

    async def _analyze_compiler(
        self, binary: str, toolchain_type: ToolchainType
    ) -> Optional[CompilerInfo]:
        """Analyze a specific compiler"""
        compiler_path = shutil.which(binary)
        if not compiler_path:
            return None

        try:
            # Get version
            result = subprocess.run(
                [binary, "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return None

            version_output = result.stdout
            version = self._extract_version(version_output)

            # Get target architecture
            result = subprocess.run(
                [binary, "-dumpmachine"], capture_output=True, text=True, timeout=10
            )
            target_arch = result.stdout.strip() if result.returncode == 0 else "unknown"

            # Detect capabilities
            capabilities = await self._detect_compiler_capabilities(binary)

            # Generate optimization flags
            opt_flags = self._generate_optimization_flags(toolchain_type, capabilities)

            return CompilerInfo(
                name=binary,
                version=version,
                path=compiler_path,
                type=toolchain_type,
                target_arch=target_arch,
                capabilities=capabilities,
                optimization_flags=opt_flags,
            )

        except Exception as e:
            self.logger.warning(f"Failed to analyze compiler {binary}: {e}")
            return None

    def _extract_version(self, version_output: str) -> str:
        """Extract version number from compiler output"""
        patterns = [
            r"gcc.*?(\d+\.\d+\.\d+)",
            r"clang.*?(\d+\.\d+\.\d+)",
            r"icc.*?(\d+\.\d+\.\d+)",
            r"version\s+(\d+\.\d+\.\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, version_output, re.IGNORECASE)
            if match:
                return match.group(1)

        return "unknown"

    async def _detect_compiler_capabilities(self, binary: str) -> List[str]:
        """Detect compiler-specific capabilities"""
        capabilities = []

        # Test various compiler flags
        test_flags = [
            ("-fopenmp", "openmp"),
            ("-mavx2", "avx2"),
            ("-mavx512f", "avx512"),
            ("-flto", "lto"),
            ("-fprofile-generate", "pgo"),
            ("-fsanitize=address", "asan"),
            ("-fsanitize=thread", "tsan"),
            ("-march=native", "native_arch"),
        ]

        for flag, capability in test_flags:
            if await self._test_compiler_flag(binary, flag):
                capabilities.append(capability)

        return capabilities

    async def _test_compiler_flag(self, binary: str, flag: str) -> bool:
        """Test if compiler supports a specific flag"""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
                f.write("int main(){return 0;}")
                test_file = f.name

            cmd = [binary, flag, "-c", test_file, "-o", "/dev/null"]
            result = subprocess.run(cmd, capture_output=True, timeout=5)

            os.unlink(test_file)
            return result.returncode == 0

        except:
            return False

    def _generate_optimization_flags(
        self, toolchain_type: ToolchainType, capabilities: List[str]
    ) -> Dict[str, List[str]]:
        """Generate optimization flags for different levels"""
        base_flags = {
            OptimizationLevel.DEBUG: ["-g", "-O0", "-DDEBUG"],
            OptimizationLevel.RELEASE: ["-O2", "-DNDEBUG"],
            OptimizationLevel.PERFORMANCE: ["-O3", "-DNDEBUG"],
            OptimizationLevel.SIZE: ["-Os", "-DNDEBUG"],
            OptimizationLevel.SECURITY: ["-O2", "-DNDEBUG", "-fstack-protector-strong"],
        }

        # Add capability-specific flags
        if "lto" in capabilities:
            base_flags[OptimizationLevel.PERFORMANCE].append("-flto")
            base_flags[OptimizationLevel.SIZE].append("-flto")

        if "native_arch" in capabilities:
            base_flags[OptimizationLevel.PERFORMANCE].append("-march=native")

        if "avx512" in capabilities and self.platform_info.get(
            "intel_features", {}
        ).get("avx512"):
            base_flags[OptimizationLevel.PERFORMANCE].extend(
                ["-mavx512f", "-mavx512cd"]
            )

        return {level.value: flags for level, flags in base_flags.items()}

    def _load_optimization_profiles(self) -> Dict[str, Any]:
        """Load platform-specific optimization profiles"""
        profiles = {
            "intel_meteor_lake": {
                "p_cores": [0, 2, 4, 6, 8, 10],  # Performance cores
                "e_cores": list(range(12, 20)),  # Efficiency cores
                "preferred_flags": ["-march=native", "-mtune=native"],
                "thermal_threshold": 85.0,
                "max_parallel_jobs": 6,
            },
            "generic_x86_64": {
                "preferred_flags": ["-march=x86-64", "-mtune=generic"],
                "thermal_threshold": 80.0,
                "max_parallel_jobs": min(8, self.cpu_count),
            },
        }

        # Select appropriate profile
        if self.platform_info.get("intel_features", {}).get("meteor_lake"):
            return profiles["intel_meteor_lake"]
        else:
            return profiles["generic_x86_64"]

    async def _setup_hardware_optimization(self):
        """Setup hardware-specific optimizations"""
        self.logger.info("Setting up hardware optimizations...")

        # CPU affinity optimization for Intel Meteor Lake
        if self.platform_info.get("intel_features", {}).get("meteor_lake"):
            await self._setup_meteor_lake_optimization()

        # Memory optimization
        await self._setup_memory_optimization()

    async def _setup_meteor_lake_optimization(self):
        """Setup Intel Meteor Lake specific optimizations"""
        self.logger.info("Configuring Intel Meteor Lake optimizations...")

        # Set process affinity to performance cores for compilation
        try:
            import psutil

            current_process = psutil.Process()
            p_cores = self.optimization_profiles.get("p_cores", [0, 2, 4, 6])
            current_process.cpu_affinity(p_cores)
            self.logger.info(f"Set CPU affinity to P-cores: {p_cores}")
        except Exception as e:
            self.logger.warning(f"Failed to set CPU affinity: {e}")

    async def _setup_memory_optimization(self):
        """Setup memory optimizations for large builds"""
        # Calculate optimal parallel job count based on available memory
        available_memory_gb = psutil.virtual_memory().available // (1024**3)

        # Estimate ~2GB per parallel compilation job
        safe_parallel_jobs = min(
            available_memory_gb // 2,
            self.cpu_count,
            self.optimization_profiles.get("max_parallel_jobs", 8),
        )

        self.optimization_profiles["calculated_max_jobs"] = safe_parallel_jobs
        self.logger.info(f"Set maximum parallel jobs to {safe_parallel_jobs}")

    async def create_project(self, project_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new C/C++ project"""
        self.logger.info(f"Creating project: {project_spec.get('name', 'unnamed')}")

        try:
            # Parse project specification
            spec = ProjectSpec(
                name=project_spec["name"],
                language=project_spec.get("language", "c"),
                type=project_spec.get("type", "executable"),
                sources=project_spec.get("sources", []),
                headers=project_spec.get("headers", []),
                dependencies=project_spec.get("dependencies", []),
                optimization_level=OptimizationLevel(
                    project_spec.get("optimization", "release")
                ),
                target_arch=project_spec.get("target_arch", "native"),
                custom_flags=project_spec.get("custom_flags", []),
            )

            # Create project directory structure
            project_path = Path.cwd() / spec.name
            project_path.mkdir(exist_ok=True)

            (project_path / "src").mkdir(exist_ok=True)
            (project_path / "include").mkdir(exist_ok=True)
            (project_path / "build").mkdir(exist_ok=True)

            # Generate CMakeLists.txt
            cmake_content = await self._generate_cmake(spec)
            (project_path / "CMakeLists.txt").write_text(cmake_content)

            # Generate main source file if none provided
            if not spec.sources:
                main_content = self._generate_main_source(spec.language)
                main_file = f"main.{('c' if spec.language == 'c' else 'cpp')}"
                (project_path / "src" / main_file).write_text(main_content)
                spec.sources = [f"src/{main_file}"]

            # Generate Makefile as fallback
            makefile_content = await self._generate_makefile(spec)
            (project_path / "Makefile").write_text(makefile_content)

            self.metrics["total_code_generated"] += len(cmake_content) + len(
                makefile_content
            )

            return {
                "success": True,
                "project_path": str(project_path),
                "build_system": "cmake",
                "fallback_build": "makefile",
                "spec": asdict(spec),
            }

        except Exception as e:
            self.logger.error(f"Failed to create project: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_cmake(self, spec: ProjectSpec) -> str:
        """Generate CMakeLists.txt for project"""
        cmake_lines = [
            f"cmake_minimum_required(VERSION 3.10)",
            f"project({spec.name} {'CXX' if spec.language == 'cpp' else 'C'})",
            "",
            f"set(CMAKE_{'CXX' if spec.language == 'cpp' else 'C'}_STANDARD {'17' if spec.language == 'cpp' else '11'})",
            "",
        ]

        # Add optimization flags
        opt_flags = self.active_toolchain.optimization_flags.get(
            spec.optimization_level.value, []
        )
        if opt_flags:
            cmake_lines.extend(
                [
                    f"set(CMAKE_{'CXX' if spec.language == 'cpp' else 'C'}_FLAGS \"${{{' '.join(opt_flags)}}}\")",
                    "",
                ]
            )

        # Add sources
        if spec.sources:
            cmake_lines.extend(
                [f"set(SOURCES", *[f"    {src}" for src in spec.sources], ")", ""]
            )

        # Add target
        if spec.type == "executable":
            cmake_lines.append(f"add_executable({spec.name} ${{SOURCES}})")
        elif spec.type == "static_lib":
            cmake_lines.append(f"add_library({spec.name} STATIC ${{SOURCES}})")
        elif spec.type == "shared_lib":
            cmake_lines.append(f"add_library({spec.name} SHARED ${{SOURCES}})")

        # Add dependencies
        if spec.dependencies:
            cmake_lines.extend(
                [
                    "",
                    f"target_link_libraries({spec.name}",
                    *[f"    {dep}" for dep in spec.dependencies],
                    ")",
                ]
            )

        return "\n".join(cmake_lines)

    async def _generate_makefile(self, spec: ProjectSpec) -> str:
        """Generate Makefile as fallback build system"""
        compiler = "g++" if spec.language == "cpp" else "gcc"
        if self.active_toolchain and self.active_toolchain.name in ["clang", "clang++"]:
            compiler = "clang++" if spec.language == "cpp" else "clang"

        opt_flags = self.active_toolchain.optimization_flags.get(
            spec.optimization_level.value, []
        )

        makefile_lines = [
            f"CC = {compiler}",
            f"CFLAGS = {' '.join(opt_flags)}",
            f"TARGET = {spec.name}",
            f"SOURCES = {' '.join(spec.sources)}",
            f"OBJECTS = $(SOURCES:.{('cpp' if spec.language == 'cpp' else 'c')}=.o)",
            "",
            "all: $(TARGET)",
            "",
            "$(TARGET): $(OBJECTS)",
            f"\t$(CC) $(OBJECTS) -o $(TARGET) {' '.join(spec.dependencies)}",
            "",
            f".{('cpp' if spec.language == 'cpp' else 'c')}.o:",
            "\t$(CC) $(CFLAGS) -c $< -o $@",
            "",
            "clean:",
            "\trm -f $(OBJECTS) $(TARGET)",
            "",
            ".PHONY: all clean",
        ]

        return "\n".join(makefile_lines)

    def _generate_main_source(self, language: str) -> str:
        """Generate a basic main source file"""
        if language == "c":
            return """#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    printf("Hello, C World!\\n");
    return EXIT_SUCCESS;
}
"""
        else:  # C++
            return """#include <iostream>
#include <string>

int main(int argc, char *argv[]) {
    std::cout << "Hello, C++ World!" << std::endl;
    return 0;
}
"""

    async def compile_project(
        self, project_path: str, build_config: Dict[str, Any] = None
    ) -> BuildResult:
        """Compile a C/C++ project with optimization"""
        self.logger.info(f"Compiling project at {project_path}")
        start_time = time.time()

        try:
            # Update thermal profile before compilation
            self.thermal_profile = await self.thermal_monitor.get_thermal_profile()

            # Adjust compilation strategy based on thermal state
            build_strategy = await self._select_build_strategy(self.thermal_profile)

            project_dir = Path(project_path)
            build_dir = project_dir / "build"
            build_dir.mkdir(exist_ok=True)

            # Try CMake build first
            cmake_result = await self._try_cmake_build(
                project_dir, build_dir, build_strategy
            )
            if cmake_result.success:
                compile_time = time.time() - start_time
                self._update_build_metrics(compile_time, True)
                return cmake_result

            # Fallback to Makefile
            make_result = await self._try_make_build(project_dir, build_strategy)
            compile_time = time.time() - start_time
            self._update_build_metrics(compile_time, make_result.success)

            return make_result

        except Exception as e:
            self.logger.error(f"Compilation failed: {e}")
            compile_time = time.time() - start_time
            self._update_build_metrics(compile_time, False)

            return BuildResult(
                success=False,
                build_time=compile_time,
                binary_path=None,
                binary_size=0,
                warnings=[],
                errors=[str(e)],
                performance_metrics={},
            )

    async def _select_build_strategy(
        self, thermal_profile: ThermalProfile
    ) -> Dict[str, Any]:
        """Select optimal build strategy based on thermal conditions"""
        strategy = {
            "parallel_jobs": self.optimization_profiles.get("calculated_max_jobs", 4),
            "optimization_level": OptimizationLevel.RELEASE,
            "use_lto": True,
            "use_native_arch": True,
        }

        # Thermal throttling adjustments
        if thermal_profile.thermal_state == ThermalState.CRITICAL:
            strategy["parallel_jobs"] = 1
            strategy["optimization_level"] = OptimizationLevel.SIZE
            strategy["use_lto"] = False
            self.metrics["thermal_throttles"] += 1

        elif thermal_profile.thermal_state == ThermalState.HOT:
            strategy["parallel_jobs"] = max(1, strategy["parallel_jobs"] // 2)
            strategy["optimization_level"] = OptimizationLevel.RELEASE

        elif thermal_profile.thermal_state == ThermalState.WARM:
            strategy["parallel_jobs"] = max(2, strategy["parallel_jobs"] * 3 // 4)

        return strategy

    async def _try_cmake_build(
        self, project_dir: Path, build_dir: Path, strategy: Dict[str, Any]
    ) -> BuildResult:
        """Try building with CMake"""
        if not (project_dir / "CMakeLists.txt").exists():
            return BuildResult(False, 0, None, 0, [], ["No CMakeLists.txt found"], {})

        try:
            # Configure
            configure_cmd = [
                "cmake",
                "-S",
                str(project_dir),
                "-B",
                str(build_dir),
                f'-DCMAKE_BUILD_TYPE={strategy["optimization_level"].value.title()}',
            ]

            configure_result = subprocess.run(
                configure_cmd, capture_output=True, text=True, timeout=60
            )

            if configure_result.returncode != 0:
                return BuildResult(False, 0, None, 0, [], [configure_result.stderr], {})

            # Build
            build_cmd = [
                "cmake",
                "--build",
                str(build_dir),
                "--parallel",
                str(strategy["parallel_jobs"]),
            ]

            build_result = subprocess.run(
                build_cmd, capture_output=True, text=True, timeout=300
            )

            if build_result.returncode != 0:
                return BuildResult(False, 0, None, 0, [], [build_result.stderr], {})

            # Find built binary
            binary_path = self._find_binary(build_dir)
            binary_size = binary_path.stat().st_size if binary_path else 0

            return BuildResult(
                success=True,
                build_time=0,  # Will be set by caller
                binary_path=str(binary_path) if binary_path else None,
                binary_size=binary_size,
                warnings=self._extract_warnings(build_result.stderr),
                errors=[],
                performance_metrics={"build_system": "cmake"},
            )

        except Exception as e:
            return BuildResult(False, 0, None, 0, [], [str(e)], {})

    async def _try_make_build(
        self, project_dir: Path, strategy: Dict[str, Any]
    ) -> BuildResult:
        """Try building with Make"""
        if not (project_dir / "Makefile").exists():
            return BuildResult(False, 0, None, 0, [], ["No Makefile found"], {})

        try:
            build_cmd = ["make", f'-j{strategy["parallel_jobs"]}']

            build_result = subprocess.run(
                build_cmd, cwd=project_dir, capture_output=True, text=True, timeout=300
            )

            success = build_result.returncode == 0

            # Find built binary
            binary_path = self._find_binary(project_dir)
            binary_size = binary_path.stat().st_size if binary_path else 0

            return BuildResult(
                success=success,
                build_time=0,  # Will be set by caller
                binary_path=str(binary_path) if binary_path else None,
                binary_size=binary_size,
                warnings=self._extract_warnings(build_result.stderr),
                errors=[build_result.stderr] if not success else [],
                performance_metrics={"build_system": "make"},
            )

        except Exception as e:
            return BuildResult(False, 0, None, 0, [], [str(e)], {})

    def _find_binary(self, search_dir: Path) -> Optional[Path]:
        """Find the compiled binary in build directory"""
        # Common binary locations and patterns
        search_patterns = ["**/*", "*.exe", "*.out", "**/*.exe", "**/*.out"]

        for pattern in search_patterns:
            for path in search_dir.glob(pattern):
                if path.is_file() and os.access(path, os.X_OK):
                    return path

        return None

    def _extract_warnings(self, compiler_output: str) -> List[str]:
        """Extract warnings from compiler output"""
        warnings = []
        lines = compiler_output.split("\n")

        for line in lines:
            if "warning:" in line.lower():
                warnings.append(line.strip())

        return warnings

    def _update_build_metrics(self, build_time: float, success: bool):
        """Update build performance metrics"""
        self.metrics["compilations_completed"] += 1
        if success:
            self.metrics["successful_builds"] += 1

        # Update average build time
        total_builds = self.metrics["compilations_completed"]
        current_avg = self.metrics["average_build_time"]
        self.metrics["average_build_time"] = (
            current_avg * (total_builds - 1) + build_time
        ) / total_builds

    async def optimize_binary(
        self, binary_path: str, optimization_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Post-compilation binary optimization"""
        self.logger.info(f"Optimizing binary: {binary_path}")

        try:
            binary = Path(binary_path)
            if not binary.exists():
                return {"success": False, "error": "Binary not found"}

            original_size = binary.stat().st_size
            optimizations_applied = []

            # Strip debug symbols if requested
            config = optimization_config or {}
            if config.get("strip_symbols", True):
                await self._strip_binary(binary)
                optimizations_applied.append("symbol_stripping")

            # UPX compression if available
            if config.get("compress", False) and shutil.which("upx"):
                await self._compress_binary(binary)
                optimizations_applied.append("upx_compression")

            optimized_size = binary.stat().st_size
            size_reduction = original_size - optimized_size

            self.metrics["binary_optimizations"] += 1

            return {
                "success": True,
                "original_size": original_size,
                "optimized_size": optimized_size,
                "size_reduction": size_reduction,
                "optimizations": optimizations_applied,
            }

        except Exception as e:
            self.logger.error(f"Binary optimization failed: {e}")
            return {"success": False, "error": str(e)}

    async def _strip_binary(self, binary_path: Path):
        """Strip debug symbols from binary"""
        if shutil.which("strip"):
            subprocess.run(["strip", str(binary_path)], check=True)

    async def _compress_binary(self, binary_path: Path):
        """Compress binary with UPX"""
        if shutil.which("upx"):
            subprocess.run(["upx", "--best", str(binary_path)], check=True)

    async def analyze_performance(
        self, binary_path: str, test_args: List[str] = None
    ) -> Dict[str, Any]:
        """Analyze binary performance characteristics"""
        self.logger.info(f"Analyzing performance: {binary_path}")

        try:
            binary = Path(binary_path)
            if not binary.exists():
                return {"success": False, "error": "Binary not found"}

            analysis_results = {}

            # File analysis
            analysis_results["file_info"] = {
                "size": binary.stat().st_size,
                "permissions": oct(binary.stat().st_mode)[-3:],
                "executable": os.access(binary, os.X_OK),
            }

            # Binary analysis with objdump if available
            if shutil.which("objdump"):
                analysis_results["symbols"] = await self._analyze_symbols(binary)

            # Performance testing if test arguments provided
            if test_args:
                analysis_results["runtime"] = await self._performance_test(
                    binary, test_args
                )

            # Memory analysis with valgrind if available
            if shutil.which("valgrind"):
                analysis_results["memory"] = await self._memory_analysis(
                    binary, test_args or []
                )

            return {"success": True, "analysis": analysis_results}

        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}")
            return {"success": False, "error": str(e)}

    async def _analyze_symbols(self, binary_path: Path) -> Dict[str, Any]:
        """Analyze binary symbols"""
        try:
            result = subprocess.run(
                ["objdump", "-t", str(binary_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                symbol_count = len(
                    [
                        line
                        for line in result.stdout.split("\n")
                        if line.strip() and not line.startswith("SYMBOL")
                    ]
                )
                return {"symbol_count": symbol_count, "has_symbols": symbol_count > 0}
            else:
                return {"error": "Failed to analyze symbols"}

        except Exception:
            return {"error": "Symbol analysis unavailable"}

    async def _performance_test(
        self, binary_path: Path, test_args: List[str]
    ) -> Dict[str, Any]:
        """Run performance test on binary"""
        try:
            start_time = time.time()
            result = subprocess.run(
                [str(binary_path)] + test_args,
                capture_output=True,
                text=True,
                timeout=60,
            )
            execution_time = time.time() - start_time

            return {
                "execution_time": execution_time,
                "exit_code": result.returncode,
                "stdout_lines": len(result.stdout.split("\n")),
                "stderr_lines": len(result.stderr.split("\n")),
            }

        except Exception as e:
            return {"error": f"Performance test failed: {e}"}

    async def _memory_analysis(
        self, binary_path: Path, test_args: List[str]
    ) -> Dict[str, Any]:
        """Analyze memory usage with valgrind"""
        try:
            cmd = [
                "valgrind",
                "--tool=memcheck",
                "--leak-check=summary",
                str(binary_path),
            ] + test_args

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            # Parse valgrind output for memory statistics
            stderr_lines = result.stderr.split("\n")
            memory_stats = {}

            for line in stderr_lines:
                if "bytes in" in line and "blocks" in line:
                    # Parse memory leak information
                    if "definitely lost" in line:
                        memory_stats["definitely_lost"] = self._extract_bytes(line)
                    elif "indirectly lost" in line:
                        memory_stats["indirectly_lost"] = self._extract_bytes(line)

            return memory_stats

        except Exception:
            return {"error": "Memory analysis unavailable"}

    def _extract_bytes(self, line: str) -> int:
        """Extract byte count from valgrind output line"""
        import re

        match = re.search(r"([\d,]+)\s+bytes", line)
        if match:
            return int(match.group(1).replace(",", ""))
        return 0

    async def cross_compile(
        self, project_path: str, target_arch: str, toolchain_path: str = None
    ) -> BuildResult:
        """Cross-compile project for different architecture"""
        self.logger.info(f"Cross-compiling for {target_arch}")

        try:
            # Detect cross-compilation toolchain
            cross_compiler = await self._detect_cross_compiler(
                target_arch, toolchain_path
            )
            if not cross_compiler:
                return BuildResult(
                    success=False,
                    build_time=0,
                    binary_path=None,
                    binary_size=0,
                    warnings=[],
                    errors=[f"No cross-compiler found for {target_arch}"],
                    performance_metrics={},
                )

            # Temporarily switch active toolchain
            original_toolchain = self.active_toolchain
            self.active_toolchain = cross_compiler

            try:
                # Perform cross-compilation
                result = await self.compile_project(
                    project_path, {"target_arch": target_arch, "cross_compile": True}
                )

                if result.success:
                    self.metrics["cross_platform_builds"] += 1

                return result

            finally:
                # Restore original toolchain
                self.active_toolchain = original_toolchain

        except Exception as e:
            self.logger.error(f"Cross-compilation failed: {e}")
            return BuildResult(
                success=False,
                build_time=0,
                binary_path=None,
                binary_size=0,
                warnings=[],
                errors=[str(e)],
                performance_metrics={},
            )

    async def _detect_cross_compiler(
        self, target_arch: str, toolchain_path: str = None
    ) -> Optional[CompilerInfo]:
        """Detect cross-compiler for target architecture"""
        # Common cross-compiler naming patterns
        cross_patterns = {
            "arm": ["arm-linux-gnueabihf-gcc", "arm-none-eabi-gcc"],
            "arm64": ["aarch64-linux-gnu-gcc", "aarch64-none-elf-gcc"],
            "mips": ["mips-linux-gnu-gcc", "mipsel-linux-gnu-gcc"],
            "riscv": ["riscv64-linux-gnu-gcc", "riscv32-unknown-elf-gcc"],
        }

        candidates = cross_patterns.get(target_arch, [])

        # Add custom toolchain path if provided
        if toolchain_path:
            candidates.insert(0, toolchain_path)

        for candidate in candidates:
            compiler_info = await self._analyze_compiler(candidate, ToolchainType.GCC)
            if compiler_info:
                compiler_info.is_cross_compiler = True
                return compiler_info

        return None

    async def profile_guided_optimization(
        self, project_path: str, training_data: List[str]
    ) -> BuildResult:
        """Perform Profile-Guided Optimization (PGO)"""
        self.logger.info(f"Starting PGO for project: {project_path}")

        try:
            if "pgo" not in self.active_toolchain.capabilities:
                return BuildResult(
                    success=False,
                    build_time=0,
                    binary_path=None,
                    binary_size=0,
                    warnings=[],
                    errors=["PGO not supported by active toolchain"],
                    performance_metrics={},
                )

            project_dir = Path(project_path)
            pgo_dir = project_dir / "pgo"
            pgo_dir.mkdir(exist_ok=True)

            # Phase 1: Instrumented build
            instrumented_result = await self._pgo_instrumented_build(
                project_dir, pgo_dir
            )
            if not instrumented_result.success:
                return instrumented_result

            # Phase 2: Training run
            training_result = await self._pgo_training_run(
                instrumented_result.binary_path, training_data, pgo_dir
            )
            if not training_result:
                return BuildResult(
                    success=False,
                    build_time=0,
                    binary_path=None,
                    binary_size=0,
                    warnings=[],
                    errors=["PGO training failed"],
                    performance_metrics={},
                )

            # Phase 3: Optimized build
            optimized_result = await self._pgo_optimized_build(project_dir, pgo_dir)

            if optimized_result.success:
                self.metrics["optimization_saves"] += 1

            return optimized_result

        except Exception as e:
            self.logger.error(f"PGO failed: {e}")
            return BuildResult(
                success=False,
                build_time=0,
                binary_path=None,
                binary_size=0,
                warnings=[],
                errors=[str(e)],
                performance_metrics={},
            )

    async def _pgo_instrumented_build(
        self, project_dir: Path, pgo_dir: Path
    ) -> BuildResult:
        """Build with profiling instrumentation"""
        # Add PGO instrumentation flags
        original_flags = self.active_toolchain.optimization_flags.copy()

        for level in original_flags:
            original_flags[level].extend(
                ["-fprofile-generate", f"-fprofile-dir={pgo_dir}"]
            )

        try:
            self.active_toolchain.optimization_flags = original_flags
            return await self.compile_project(str(project_dir))
        finally:
            # Restore original flags
            self.active_toolchain.optimization_flags = original_flags

    async def _pgo_training_run(
        self, binary_path: str, training_data: List[str], pgo_dir: Path
    ) -> bool:
        """Run training workload to generate profile data"""
        try:
            for training_args in training_data:
                result = subprocess.run(
                    [binary_path] + training_args.split(),
                    timeout=60,
                    capture_output=True,
                )
                if result.returncode != 0:
                    self.logger.warning(f"Training run failed: {result.stderr}")

            # Check if profile data was generated
            profile_files = list(pgo_dir.glob("*.gcda"))
            return len(profile_files) > 0

        except Exception as e:
            self.logger.error(f"PGO training failed: {e}")
            return False

    async def _pgo_optimized_build(
        self, project_dir: Path, pgo_dir: Path
    ) -> BuildResult:
        """Build optimized binary using profile data"""
        # Add PGO optimization flags
        original_flags = self.active_toolchain.optimization_flags.copy()

        for level in original_flags:
            original_flags[level].extend(["-fprofile-use", f"-fprofile-dir={pgo_dir}"])

        try:
            self.active_toolchain.optimization_flags = original_flags
            return await self.compile_project(str(project_dir))
        finally:
            # Restore original flags
            self.active_toolchain.optimization_flags = original_flags

    async def coordinate_with_agents(
        self, agents: List[str], task: str, **kwargs
    ) -> Dict[str, Any]:
        """Coordinate with other agents for comprehensive C/C++ workflows"""
        self.logger.info(f"Coordinating with agents: {agents} for task: {task}")

        coordination_results = {}

        try:
            for agent in agents:
                self.coordinated_agents.add(agent)

                if agent == "PYTHON-INTERNAL":
                    # Coordinate for Python binding generation
                    result = await self._coordinate_python_bindings(task, **kwargs)
                elif agent == "CONSTRUCTOR":
                    # Coordinate for project setup
                    result = await self._coordinate_project_construction(task, **kwargs)
                elif agent == "OPTIMIZER":
                    # Coordinate for performance optimization
                    result = await self._coordinate_optimization(task, **kwargs)
                elif agent == "TESTBED":
                    # Coordinate for testing
                    result = await self._coordinate_testing(task, **kwargs)
                else:
                    result = {"status": "unsupported_agent", "agent": agent}

                coordination_results[agent] = result

            return {
                "success": True,
                "coordinated_agents": len(self.coordinated_agents),
                "results": coordination_results,
            }

        except Exception as e:
            self.logger.error(f"Agent coordination failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "partial_results": coordination_results,
            }

    async def _coordinate_python_bindings(self, task: str, **kwargs) -> Dict[str, Any]:
        """Coordinate Python binding generation"""
        if task == "generate_bindings":
            headers = kwargs.get("headers", [])
            if not headers:
                return {
                    "status": "error",
                    "message": "No headers specified for binding generation",
                }

            # Generate Python bindings using ctypes or pybind11
            binding_results = []
            for header in headers:
                binding_code = await self._generate_python_binding(header)
                binding_results.append(
                    {
                        "header": header,
                        "binding_code": binding_code,
                        "generated": bool(binding_code),
                    }
                )

            return {
                "status": "completed",
                "bindings_generated": len(
                    [r for r in binding_results if r["generated"]]
                ),
                "results": binding_results,
            }

        return {"status": "unsupported_task", "task": task}

    async def _generate_python_binding(self, header_path: str) -> Optional[str]:
        """Generate Python binding for C header"""
        try:
            # Basic ctypes binding generation
            header = Path(header_path)
            if not header.exists():
                return None

            # Parse header for function declarations
            with open(header) as f:
                content = f.read()

            # Simple regex-based parsing (could be enhanced with proper C parser)
            import re

            functions = re.findall(r"(\w+)\s+(\w+)\s*\([^)]*\)\s*;", content)

            if not functions:
                return None

            binding_lines = [
                "import ctypes",
                f"# Generated binding for {header.name}",
                "",
                f'lib = ctypes.CDLL("./{header.stem}.so")',
                "",
            ]

            for return_type, func_name in functions:
                binding_lines.extend(
                    [
                        f"# {func_name}",
                        f"lib.{func_name}.restype = ctypes.{self._map_c_type(return_type)}",
                        # f'lib.{func_name}.argtypes = [...]',  # Would need argument parsing
                        "",
                    ]
                )

            return "\n".join(binding_lines)

        except Exception as e:
            self.logger.error(f"Failed to generate binding for {header_path}: {e}")
            return None

    def _map_c_type(self, c_type: str) -> str:
        """Map C type to ctypes equivalent"""
        type_map = {
            "int": "c_int",
            "float": "c_float",
            "double": "c_double",
            "char": "c_char",
            "void": "c_void_p",
        }
        return type_map.get(c_type, "c_void_p")

    async def _coordinate_project_construction(
        self, task: str, **kwargs
    ) -> Dict[str, Any]:
        """Coordinate with CONSTRUCTOR for project setup"""
        if task == "setup_project":
            project_spec = kwargs.get("project_spec", {})
            return await self.create_project(project_spec)

        return {"status": "unsupported_task", "task": task}

    async def _coordinate_optimization(self, task: str, **kwargs) -> Dict[str, Any]:
        """Coordinate with OPTIMIZER for performance tuning"""
        if task == "optimize_binary":
            binary_path = kwargs.get("binary_path")
            if not binary_path:
                return {"status": "error", "message": "No binary path specified"}

            return await self.optimize_binary(binary_path, kwargs.get("config", {}))

        return {"status": "unsupported_task", "task": task}

    async def _coordinate_testing(self, task: str, **kwargs) -> Dict[str, Any]:
        """Coordinate with TESTBED for testing"""
        if task == "performance_test":
            binary_path = kwargs.get("binary_path")
            test_args = kwargs.get("test_args", [])

            if not binary_path:
                return {"status": "error", "message": "No binary path specified"}

            return await self.analyze_performance(binary_path, test_args)

        return {"status": "unsupported_task", "task": task}

    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status"""
        thermal_profile = await self.thermal_monitor.get_thermal_profile()

        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "version": self.version,
            "status": "operational",
            "capabilities": self.capabilities,
            "metrics": self.metrics,
            "platform_info": self.platform_info,
            "detected_compilers": {
                name: {
                    "version": compiler.version,
                    "path": compiler.path,
                    "type": compiler.type.value,
                    "capabilities": compiler.capabilities,
                }
                for name, compiler in self.detected_compilers.items()
            },
            "active_toolchain": (
                {
                    "name": self.active_toolchain.name,
                    "version": self.active_toolchain.version,
                    "type": self.active_toolchain.type.value,
                }
                if self.active_toolchain
                else None
            ),
            "thermal_profile": {
                "cpu_temp": thermal_profile.cpu_temp,
                "thermal_state": thermal_profile.thermal_state.value,
                "throttle_level": thermal_profile.throttle_level,
            },
            "coordinated_agents": list(self.coordinated_agents),
            "optimization_profiles": self.optimization_profiles,
        }


class ThermalMonitor:
    """Advanced thermal monitoring for C/C++ compilation optimization"""

    def __init__(self):
        self.thermal_sensors = []
        self.baseline_temp = 0.0
        self.monitoring_active = False

    async def initialize(self):
        """Initialize thermal monitoring"""
        try:
            # Detect available thermal sensors
            await self._detect_thermal_sensors()
            self.monitoring_active = len(self.thermal_sensors) > 0
        except Exception as e:
            logging.warning(f"Thermal monitoring initialization failed: {e}")

    async def _detect_thermal_sensors(self):
        """Detect available thermal sensors"""
        sensor_paths = [
            "/sys/class/thermal/thermal_zone*/temp",
            "/sys/devices/virtual/thermal/thermal_zone*/temp",
        ]

        import glob

        for pattern in sensor_paths:
            for sensor_path in glob.glob(pattern):
                try:
                    with open(sensor_path, "r") as f:
                        temp = int(f.read().strip()) / 1000.0  # Convert millicelsius
                        self.thermal_sensors.append(sensor_path)
                        if not self.baseline_temp:
                            self.baseline_temp = temp
                except:
                    continue

    async def get_thermal_profile(self) -> ThermalProfile:
        """Get current thermal profile"""
        if not self.monitoring_active:
            return ThermalProfile(
                cpu_temp=50.0,
                thermal_state=ThermalState.NORMAL,
                throttle_level=0.0,
                recommended_cores=psutil.cpu_count(),
                max_optimization=OptimizationLevel.PERFORMANCE,
            )

        try:
            # Read current temperatures
            temps = []
            for sensor_path in self.thermal_sensors:
                try:
                    with open(sensor_path, "r") as f:
                        temp = int(f.read().strip()) / 1000.0
                        temps.append(temp)
                except:
                    continue

            if not temps:
                cpu_temp = 50.0
            else:
                cpu_temp = max(temps)  # Use highest temperature

            # Determine thermal state
            if cpu_temp >= 95.0:
                thermal_state = ThermalState.CRITICAL
                throttle_level = 0.8
                recommended_cores = 1
                max_optimization = OptimizationLevel.SIZE
            elif cpu_temp >= 85.0:
                thermal_state = ThermalState.HOT
                throttle_level = 0.5
                recommended_cores = max(1, psutil.cpu_count() // 2)
                max_optimization = OptimizationLevel.RELEASE
            elif cpu_temp >= 75.0:
                thermal_state = ThermalState.WARM
                throttle_level = 0.25
                recommended_cores = max(2, psutil.cpu_count() * 3 // 4)
                max_optimization = OptimizationLevel.PERFORMANCE
            else:
                thermal_state = ThermalState.NORMAL
                throttle_level = 0.0
                recommended_cores = psutil.cpu_count()
                max_optimization = OptimizationLevel.PERFORMANCE

            return ThermalProfile(
                cpu_temp=cpu_temp,
                thermal_state=thermal_state,
                throttle_level=throttle_level,
                recommended_cores=recommended_cores,
                max_optimization=max_optimization,
            )

        except Exception:
            # Fallback to safe defaults
            return ThermalProfile(
                cpu_temp=60.0,
                thermal_state=ThermalState.NORMAL,
                throttle_level=0.0,
                recommended_cores=psutil.cpu_count(),
                max_optimization=OptimizationLevel.PERFORMANCE,
            )


# Main execution and testing
async def main():
    """Main function for testing C-INTERNAL agent"""
    print("=== C-INTERNAL Agent Test Suite ===")

    # Initialize agent
    agent = CInternalAgent()

    # Initialize async components
    await agent._initialize_async()

    # Display status
    status = await agent.get_status()
    print(f"\nAgent Status: {status['name']} v{status['version']}")
    print(f"Detected Compilers: {len(status['detected_compilers'])}")
    for name, info in status["detected_compilers"].items():
        print(f"  - {name}: {info['type']} {info['version']}")

    # Test project creation
    print("\n=== Testing Project Creation ===")
    project_spec = {
        "name": "test_project",
        "language": "c",
        "type": "executable",
        "optimization": "performance",
    }

    create_result = await agent.create_project(project_spec)
    print(f"Project creation: {'SUCCESS' if create_result['success'] else 'FAILED'}")
    if create_result["success"]:
        print(f"Project path: {create_result['project_path']}")

        # Test compilation
        print("\n=== Testing Compilation ===")
        build_result = await agent.compile_project(create_result["project_path"])
        print(f"Compilation: {'SUCCESS' if build_result.success else 'FAILED'}")
        print(f"Build time: {build_result.build_time:.2f}s")

        if build_result.success and build_result.binary_path:
            # Test binary optimization
            print("\n=== Testing Binary Optimization ===")
            opt_result = await agent.optimize_binary(build_result.binary_path)
            if opt_result["success"]:
                print(f"Size reduction: {opt_result['size_reduction']} bytes")
                print(f"Optimizations: {opt_result['optimizations']}")

            # Test performance analysis
            print("\n=== Testing Performance Analysis ===")
            perf_result = await agent.analyze_performance(build_result.binary_path)
            if perf_result["success"]:
                print("Performance analysis completed")
                print(
                    f"Binary size: {perf_result['analysis']['file_info']['size']} bytes"
                )

    # Test agent coordination
    print("\n=== Testing Agent Coordination ===")
    coord_result = await agent.coordinate_with_agents(
        ["PYTHON-INTERNAL", "CONSTRUCTOR"], "setup_project", project_spec=project_spec
    )
    print(f"Coordination: {'SUCCESS' if coord_result['success'] else 'FAILED'}")

    # Display final metrics
    print(f"\n=== Final Metrics ===")
    final_status = await agent.get_status()
    metrics = final_status["metrics"]
    print(f"Compilations completed: {metrics['compilations_completed']}")
    print(f"Successful builds: {metrics['successful_builds']}")
    print(f"Average build time: {metrics['average_build_time']:.2f}s")
    print(f"Binary optimizations: {metrics['binary_optimizations']}")

    print("\n=== C-INTERNAL Agent Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
