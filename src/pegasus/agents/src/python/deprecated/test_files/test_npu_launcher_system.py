#!/usr/bin/env python3
"""
NPU Launcher System Comprehensive Test Suite
Validates all components of the CONSTRUCTOR-grade NPU launcher system
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple


# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import (
        get_project_root, get_agents_dir, get_database_dir,
        get_python_src_dir, get_shadowgit_paths, get_database_config
    )
except ImportError:
    # Fallback if path_utilities not available
    def get_project_root():
        return Path(__file__).parent.parent.parent
    def get_agents_dir():
        return get_project_root() / 'agents'
    def get_database_dir():
        return get_project_root() / 'database'
    def get_python_src_dir():
        return get_agents_dir() / 'src' / 'python'
    def get_shadowgit_paths():
        home_dir = Path.home()
        return {'root': home_dir / 'shadowgit'}
    def get_database_config():
        return {
            'host': 'localhost', 'port': 5433,
            'database': 'claude_agents_auth',
            'user': 'claude_agent', 'password': 'claude_auth_pass'
        }
class NPULauncherSystemTester:
    """Comprehensive test suite for NPU launcher system"""

    def __init__(self):
        self.project_root = Path(str(get_project_root()))
        self.install_dir = Path.home() / ".local" / "bin"
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log test result"""
        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
            print(f"✅ {test_name}: {status}")
        else:
            self.failed_tests += 1
            print(f"❌ {test_name}: {status}")

        if details:
            print(f"   {details}")

        self.test_results[test_name] = {
            "status": status,
            "details": details,
            "timestamp": time.time()
        }

    def run_command(self, command: List[str], timeout: int = 30) -> Tuple[int, str, str]:
        """Run command and return (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return 1, "", str(e)

    def test_file_existence(self):
        """Test that all NPU launcher files exist"""
        files_to_check = [
            (self.install_dir / "claude-npu", "Main NPU launcher"),
            (self.install_dir / "claude-with-npu", "Integration wrapper"),
            (self.install_dir / "claude-npu-health", "Health checker"),
            (self.project_root / "config" / "npu_launcher.json", "Configuration file"),
            (self.project_root / "docs" / "npu_launcher_system.md", "Documentation"),
            (self.project_root / "agents/src/python/npu_constructor_integration.py", "Constructor integration"),
            (self.project_root / "agents/src/python/npu_optimized_final.py", "NPU orchestrator")
        ]

        for file_path, description in files_to_check:
            if file_path.exists():
                self.log_test(f"File Existence: {description}", "PASS", str(file_path))
            else:
                self.log_test(f"File Existence: {description}", "FAIL", f"Missing: {file_path}")

    def test_file_permissions(self):
        """Test that executable files have correct permissions"""
        executable_files = [
            self.install_dir / "claude-npu",
            self.install_dir / "claude-with-npu",
            self.install_dir / "claude-npu-health"
        ]

        for file_path in executable_files:
            if file_path.exists():
                mode = file_path.stat().st_mode
                if mode & 0o111:  # Check if executable
                    self.log_test(f"Permissions: {file_path.name}", "PASS", f"Mode: {oct(mode)}")
                else:
                    self.log_test(f"Permissions: {file_path.name}", "FAIL", f"Not executable: {oct(mode)}")
            else:
                self.log_test(f"Permissions: {file_path.name}", "FAIL", "File does not exist")

    def test_configuration_file(self):
        """Test configuration file format and content"""
        config_path = self.project_root / "config" / "npu_launcher.json"

        if not config_path.exists():
            self.log_test("Configuration File", "FAIL", "File does not exist")
            return

        try:
            config_data = json.loads(config_path.read_text())

            required_fields = [
                "project_root", "venv_path", "install_dir",
                "openvino_version", "npu_available", "performance_target",
                "build_timestamp", "builder_version"
            ]

            missing_fields = [field for field in required_fields if field not in config_data]

            if not missing_fields:
                self.log_test("Configuration File", "PASS", f"All {len(required_fields)} fields present")
            else:
                self.log_test("Configuration File", "FAIL", f"Missing fields: {missing_fields}")

        except json.JSONDecodeError as e:
            self.log_test("Configuration File", "FAIL", f"Invalid JSON: {e}")
        except Exception as e:
            self.log_test("Configuration File", "FAIL", f"Error reading: {e}")

    def test_claude_wrapper_integration(self):
        """Test integration with Claude wrapper"""
        wrapper_path = self.project_root / "claude-wrapper-ultimate.sh"

        if not wrapper_path.exists():
            self.log_test("Claude Wrapper Integration", "FAIL", "Wrapper file does not exist")
            return

        content = wrapper_path.read_text()

        # Check for NPU integration markers
        integration_markers = [
            "NPU Acceleration Integration",
            "CONSTRUCTOR v8.0",
            "--npu",
            "claude-npu"
        ]

        found_markers = [marker for marker in integration_markers if marker in content]

        if len(found_markers) >= 3:
            self.log_test("Claude Wrapper Integration", "PASS", f"Found {len(found_markers)}/4 integration markers")
        else:
            self.log_test("Claude Wrapper Integration", "FAIL", f"Only found {len(found_markers)}/4 integration markers")

    def test_npu_launcher_help(self):
        """Test NPU launcher help command"""
        returncode, stdout, stderr = self.run_command(["claude-npu", "--help"])

        if returncode == 0:
            expected_help_content = [
                "Professional NPU-Accelerated Claude Orchestrator",
                "--help", "--version", "--validate", "--performance-test",
                "Performance Target", "NPU Available"
            ]

            found_content = [content for content in expected_help_content if content in stdout]

            if len(found_content) >= 5:
                self.log_test("NPU Launcher Help", "PASS", f"Found {len(found_content)}/6 expected elements")
            else:
                self.log_test("NPU Launcher Help", "FAIL", f"Only found {len(found_content)}/6 expected elements")
        else:
            self.log_test("NPU Launcher Help", "FAIL", f"Command failed: {stderr}")

    def test_npu_launcher_version(self):
        """Test NPU launcher version command"""
        returncode, stdout, stderr = self.run_command(["claude-npu", "--version"])

        if returncode == 0:
            if "NPU Orchestrator v8.0" in stdout and "CONSTRUCTOR Grade" in stdout:
                self.log_test("NPU Launcher Version", "PASS", "Version info correct")
            else:
                self.log_test("NPU Launcher Version", "FAIL", f"Unexpected version output: {stdout}")
        else:
            self.log_test("NPU Launcher Version", "FAIL", f"Command failed: {stderr}")

    def test_npu_launcher_config(self):
        """Test NPU launcher config command"""
        returncode, stdout, stderr = self.run_command(["claude-npu", "--config"])

        if returncode == 0:
            expected_config_items = [
                "Project Root", "Virtual Environment", "NPU Orchestrator",
                "Performance Target", "Health Check Interval"
            ]

            found_items = [item for item in expected_config_items if item in stdout]

            if len(found_items) >= 4:
                self.log_test("NPU Launcher Config", "PASS", f"Found {len(found_items)}/5 config items")
            else:
                self.log_test("NPU Launcher Config", "FAIL", f"Only found {len(found_items)}/5 config items")
        else:
            self.log_test("NPU Launcher Config", "FAIL", f"Command failed: {stderr}")

    def test_npu_health_checker(self):
        """Test NPU health checker"""
        returncode, stdout, stderr = self.run_command(["claude-npu-health"], timeout=60)

        if returncode == 0:
            expected_health_content = [
                "NPU System Health Check", "Health Score", "Hardware:",
                "OpenVINO:", "NPU Orchestrator:"
            ]

            combined_output = stdout + stderr
            found_content = [content for content in expected_health_content if content in combined_output]

            if len(found_content) >= 4:
                self.log_test("NPU Health Checker", "PASS", f"Found {len(found_content)}/5 health elements")
            else:
                self.log_test("NPU Health Checker", "FAIL", f"Only found {len(found_content)}/5 health elements")
        else:
            # Health checker might exit with 1 if system needs attention
            if "Health Score" in stderr:
                self.log_test("NPU Health Checker", "PASS", "Health check ran (system needs attention)")
            else:
                self.log_test("NPU Health Checker", "FAIL", f"Command failed: {stderr}")

    def test_claude_wrapper_npu_integration(self):
        """Test NPU integration via Claude wrapper"""
        returncode, stdout, stderr = self.run_command(["claude", "--npu", "--help"], timeout=30)

        if returncode == 0:
            if "🚀 Launching with NPU acceleration" in stdout or "Professional NPU-Accelerated" in stdout:
                self.log_test("Claude Wrapper NPU Integration", "PASS", "NPU integration working")
            else:
                self.log_test("Claude Wrapper NPU Integration", "FAIL", "NPU integration not triggered")
        else:
            self.log_test("Claude Wrapper NPU Integration", "FAIL", f"Command failed: {stderr}")

    def test_integration_wrapper(self):
        """Test integration wrapper functionality"""
        returncode, stdout, stderr = self.run_command(["claude-with-npu", "--help"], timeout=30)

        if returncode == 0:
            if "Claude Master System" in stdout:
                self.log_test("Integration Wrapper", "PASS", "Wrapper functionality working")
            else:
                self.log_test("Integration Wrapper", "FAIL", "Unexpected wrapper output")
        else:
            self.log_test("Integration Wrapper", "FAIL", f"Command failed: {stderr}")

    def test_documentation_quality(self):
        """Test documentation completeness"""
        doc_path = self.project_root / "docs" / "npu_launcher_system.md"

        if not doc_path.exists():
            self.log_test("Documentation Quality", "FAIL", "Documentation file missing")
            return

        content = doc_path.read_text()

        expected_sections = [
            "# NPU Launcher System Documentation",
            "## Overview", "## Configuration", "## Components",
            "## Usage", "## Performance", "## Troubleshooting"
        ]

        found_sections = [section for section in expected_sections if section in content]

        if len(found_sections) >= 6:
            self.log_test("Documentation Quality", "PASS", f"Found {len(found_sections)}/7 expected sections")
        else:
            self.log_test("Documentation Quality", "FAIL", f"Only found {len(found_sections)}/7 expected sections")

    def run_all_tests(self):
        """Run all tests in the test suite"""
        print("🚀 NPU Launcher System Comprehensive Test Suite")
        print("=" * 60)
        print()

        test_methods = [
            self.test_file_existence,
            self.test_file_permissions,
            self.test_configuration_file,
            self.test_claude_wrapper_integration,
            self.test_npu_launcher_help,
            self.test_npu_launcher_version,
            self.test_npu_launcher_config,
            self.test_npu_health_checker,
            self.test_claude_wrapper_npu_integration,
            self.test_integration_wrapper,
            self.test_documentation_quality
        ]

        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                test_name = test_method.__name__.replace('test_', '').replace('_', ' ').title()
                self.log_test(test_name, "FAIL", f"Test exception: {e}")
            print()

        # Generate summary
        print("=" * 60)
        print("🎯 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")

        pass_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        print(f"📊 Pass Rate: {pass_rate:.1f}%")

        if pass_rate >= 90:
            print("🎉 EXCELLENT: NPU Launcher System is production ready!")
        elif pass_rate >= 80:
            print("✅ GOOD: NPU Launcher System is mostly functional")
        elif pass_rate >= 70:
            print("⚠️  FAIR: NPU Launcher System needs some attention")
        else:
            print("❌ POOR: NPU Launcher System needs significant work")

        print()
        print("📄 Detailed results saved to test_results.json")

        # Save detailed results
        results_file = Path("npu_launcher_test_results.json")
        results_file.write_text(json.dumps({
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "pass_rate": pass_rate,
                "timestamp": time.time()
            },
            "detailed_results": self.test_results
        }, indent=2))

        return pass_rate >= 80

def main():
    """Main function"""
    tester = NPULauncherSystemTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()