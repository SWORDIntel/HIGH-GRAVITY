#!/usr/bin/env python3
"""
DEVELOPMENT CLUSTER DIRECT IMPLEMENTATION
Direct implementation of Linter→Patcher→Testbed pipeline without Task tool dependency

This implements the agent functionality directly since Claude Code's Task tool
only supports built-in agents, not custom agents.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import get_project_root
except ImportError:
    # Fallback if path_utilities not available
    def get_project_root():
        return Path(__file__).parent.parent.parent


class LinterAgent:
    """Senior Code Review Specialist - Direct Implementation"""

    __slots__ = ["name", "version", "priority", "status"]

    def __init__(self):
        self.name = "Linter"
        self.version = "7.0.0"
        self.priority = "HIGH"
        self.status = "PRODUCTION"

    def analyze_code(self, file_path: str) -> Dict:
        """Perform static analysis on code file"""
        issues = []

        # Check if file exists and is readable
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        # Language detection
        lang = self._detect_language(file_path)

        # Run appropriate linters
        if lang == "python":
            issues.extend(self._lint_python(file_path))
        elif lang == "javascript":
            issues.extend(self._lint_javascript(file_path))
        elif lang == "typescript":
            issues.extend(self._lint_typescript(file_path))
        elif lang == "c" or lang == "cpp":
            issues.extend(self._lint_c_cpp(file_path))

        return {
            "file": file_path,
            "language": lang,
            "issues": issues,
            "severity_counts": self._count_severities(issues),
            "status": "completed",
        }

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".c": "c",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".h": "c",
            ".hpp": "cpp",
        }
        return lang_map.get(ext, "unknown")

    def _lint_python(self, file_path: str) -> List[Dict]:
        """Lint Python code using ruff and other tools"""
        issues = []

        # Try ruff first (fast)
        try:
            result = subprocess.run(
                ["ruff", "check", "--output-format=json", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout:
                ruff_issues = json.loads(result.stdout)
                for issue in ruff_issues:
                    issues.append(
                        {
                            "line": issue.get("location", {}).get("row", 0),
                            "column": issue.get("location", {}).get("column", 0),
                            "severity": "error" if issue.get("fix", {}) else "warning",
                            "message": issue.get("message", ""),
                            "rule": issue.get("code", ""),
                            "tool": "ruff",
                        }
                    )
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        # Fallback to basic checks
        if not issues:
            issues.extend(self._basic_python_checks(file_path))

        return issues

    def _lint_javascript(self, file_path: str) -> List[Dict]:
        """Lint JavaScript/TypeScript code"""
        issues = []

        # Try eslint
        try:
            result = subprocess.run(
                ["npx", "eslint", "--format=json", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout:
                eslint_result = json.loads(result.stdout)
                for file_result in eslint_result:
                    for message in file_result.get("messages", []):
                        issues.append(
                            {
                                "line": message.get("line", 0),
                                "column": message.get("column", 0),
                                "severity": message.get("severity", 1) == 2
                                and "error"
                                or "warning",
                                "message": message.get("message", ""),
                                "rule": message.get("ruleId", ""),
                                "tool": "eslint",
                            }
                        )
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return issues

    def _lint_typescript(self, file_path: str) -> List[Dict]:
        """Lint TypeScript code"""
        issues = self._lint_javascript(file_path)  # ESLint handles TS too

        # Try tsc for type checking
        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stderr:
                # Parse TypeScript compiler output
                for line in result.stderr.split("\n"):
                    if "(" in line and ")" in line:
                        parts = line.split("(")
                        if len(parts) >= 2:
                            coords = parts[1].split(")")[0].split(",")
                            if len(coords) >= 2:
                                issues.append(
                                    {
                                        "line": int(coords[0]),
                                        "column": int(coords[1]),
                                        "severity": "error",
                                        "message": (
                                            parts[1].split("): ")[1]
                                            if "): " in parts[1]
                                            else line
                                        ),
                                        "rule": "typescript",
                                        "tool": "tsc",
                                    }
                                )
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass

        return issues

    def _lint_c_cpp(self, file_path: str) -> List[Dict]:
        """Lint C/C++ code"""
        issues = []

        # Try clang-tidy
        try:
            result = subprocess.run(
                ["clang-tidy", file_path, "--"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout:
                for line in result.stdout.split("\n"):
                    if ":" in line and ("warning:" in line or "error:" in line):
                        parts = line.split(":")
                        if len(parts) >= 4:
                            issues.append(
                                {
                                    "line": int(parts[1]) if parts[1].isdigit() else 0,
                                    "column": (
                                        int(parts[2]) if parts[2].isdigit() else 0
                                    ),
                                    "severity": (
                                        "error" if "error:" in line else "warning"
                                    ),
                                    "message": ":".join(parts[3:]).strip(),
                                    "rule": "clang-tidy",
                                    "tool": "clang-tidy",
                                }
                            )
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass

        return issues

    def _basic_python_checks(self, file_path: str) -> List[Dict]:
        """Basic Python code quality checks"""
        issues = []

        try:
            with open(file_path, "r") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # Long lines
                if len(line.rstrip()) > 88:
                    issues.append(
                        {
                            "line": i,
                            "column": 89,
                            "severity": "warning",
                            "message": f"Line too long ({len(line.rstrip())} > 88 characters)",
                            "rule": "E501",
                            "tool": "basic_checker",
                        }
                    )

                # Missing docstrings for functions
                if line.strip().startswith("def ") and not (
                    i > 1 and '"""' in lines[i]
                ):
                    issues.append(
                        {
                            "line": i,
                            "column": 1,
                            "severity": "info",
                            "message": "Missing docstring",
                            "rule": "D100",
                            "tool": "basic_checker",
                        }
                    )

        except Exception:
            pass

        return issues

    def _count_severities(self, issues: List[Dict]) -> Dict[str, int]:
        """Count issues by severity"""
        counts = {"error": 0, "warning": 0, "info": 0}
        for issue in issues:
            severity = issue.get("severity", "info")
            counts[severity] = counts.get(severity, 0) + 1
        return counts


class PatcherAgent:
    """Precision Code Surgery Specialist - Direct Implementation"""

    __slots__ = ["name", "version", "priority", "status"]

    def __init__(self):
        self.name = "Patcher"
        self.version = "7.0.0"
        self.priority = "HIGH"
        self.status = "PRODUCTION"

    def apply_fixes(self, file_path: str, lint_issues: List[Dict]) -> Dict:
        """Apply automatic fixes for lint issues"""
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        fixes_applied = []
        fixes_skipped = []

        # Sort issues by line number (descending) to apply fixes safely
        issues = sorted(lint_issues, key=lambda x: x.get("line", 0), reverse=True)

        try:
            with open(file_path, "r") as f:
                content = f.read()
                lines = content.splitlines()

            original_content = content

            for issue in issues:
                fix_result = self._apply_single_fix(lines, issue)
                if fix_result["applied"]:
                    fixes_applied.append(fix_result)
                else:
                    fixes_skipped.append(fix_result)

            # Write back if changes made
            if fixes_applied:
                with open(file_path, "w") as f:
                    f.write("\n".join(lines))
                    if content.endswith("\n"):
                        f.write("\n")

            return {
                "file": file_path,
                "fixes_applied": len(fixes_applied),
                "fixes_skipped": len(fixes_skipped),
                "details": {"applied": fixes_applied, "skipped": fixes_skipped},
                "status": "completed",
            }

        except Exception as e:
            return {"error": f"Failed to apply fixes: {str(e)}"}

    def _apply_single_fix(self, lines: List[str], issue: Dict) -> Dict:
        """Apply a single fix to the code"""
        line_num = issue.get("line", 0) - 1  # Convert to 0-based indexing
        rule = issue.get("rule", "")
        message = issue.get("message", "")

        if line_num < 0 or line_num >= len(lines):
            return {"applied": False, "reason": "Invalid line number", "issue": issue}

        original_line = lines[line_num]

        # Apply specific fixes based on rule
        if rule == "E501" or "Line too long" in message:
            # Try to break long lines
            if len(original_line) > 88:
                new_line = self._break_long_line(original_line)
                if new_line != original_line:
                    lines[line_num] = new_line
                    return {"applied": True, "fix_type": "line_break", "issue": issue}

        elif rule == "W291" or "trailing whitespace" in message.lower():
            # Remove trailing whitespace
            new_line = original_line.rstrip()
            if new_line != original_line:
                lines[line_num] = new_line
                return {"applied": True, "fix_type": "whitespace", "issue": issue}

        elif rule == "E302" or "expected 2 blank lines" in message.lower():
            # Add blank lines before function/class
            lines.insert(line_num, "")
            lines.insert(line_num, "")
            return {"applied": True, "fix_type": "spacing", "issue": issue}

        return {
            "applied": False,
            "reason": "No automatic fix available",
            "issue": issue,
        }

    def _break_long_line(self, line: str) -> str:
        """Intelligently break a long line"""
        if len(line) <= 88:
            return line

        # Simple line breaking for common patterns
        if "," in line and line.count("(") == line.count(")"):
            # Break on commas
            parts = line.split(", ")
            if len(parts) > 1:
                indent = len(line) - len(line.lstrip())
                base_indent = " " * indent
                continuation_indent = " " * (indent + 4)

                result = parts[0] + ","
                for part in parts[1:]:
                    result += "\n" + continuation_indent + part.strip()
                    if part != parts[-1]:
                        result += ","

                return result

        return line  # No safe way to break, return original


class TestbedAgent:
    """Elite Test Engineering Specialist - Direct Implementation"""

    __slots__ = ["name", "version", "priority", "status"]

    def __init__(self):
        self.name = "Testbed"
        self.version = "7.0.0"
        self.priority = "HIGH"
        self.status = "PRODUCTION"

    def run_tests(self, project_path: str = ".") -> Dict:
        """Run project tests and return results"""
        results = {
            "test_framework": None,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "coverage": 0.0,
            "details": [],
            "status": "completed",
        }

        # Detect test framework and run tests
        if os.path.exists(os.path.join(project_path, "package.json")):
            results.update(self._run_npm_tests(project_path))
        elif os.path.exists(os.path.join(project_path, "pytest.ini")) or any(
            f.startswith("test_") and f.endswith(".py")
            for f in os.listdir(project_path)
        ):
            results.update(self._run_pytest(project_path))
        elif os.path.exists(os.path.join(project_path, "Makefile")):
            results.update(self._run_make_tests(project_path))
        else:
            results["error"] = "No test framework detected"

        return results

    def _run_npm_tests(self, project_path: str) -> Dict:
        """Run npm/yarn tests"""
        try:
            # Try npm test
            result = subprocess.run(
                ["npm", "test"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            return {
                "test_framework": "npm",
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {"error": f"Failed to run npm tests: {str(e)}"}

    def _run_pytest(self, project_path: str) -> Dict:
        """Run pytest"""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-v", "--tb=short"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Parse pytest output
            output_lines = result.stdout.split("\n")
            tests_run = 0
            tests_passed = 0
            tests_failed = 0

            for line in output_lines:
                if "passed" in line and "failed" in line:
                    # Parse summary line
                    import re

                    passed_match = re.search(r"(\d+) passed", line)
                    failed_match = re.search(r"(\d+) failed", line)

                    if passed_match:
                        tests_passed = int(passed_match.group(1))
                    if failed_match:
                        tests_failed = int(failed_match.group(1))

                    tests_run = tests_passed + tests_failed

            return {
                "test_framework": "pytest",
                "tests_run": tests_run,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {"error": f"Failed to run pytest: {str(e)}"}

    def _run_make_tests(self, project_path: str) -> Dict:
        """Run make test target"""
        try:
            result = subprocess.run(
                ["make", "test"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            return {
                "test_framework": "make",
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {"error": f"Failed to run make tests: {str(e)}"}


class DevelopmentCluster:
    """Direct implementation of Linter→Patcher→Testbed pipeline"""

    __slots__ = ["linter", "patcher", "testbed"]

    def __init__(self):
        self.linter = LinterAgent()
        self.patcher = PatcherAgent()
        self.testbed = TestbedAgent()

    def process_file(self, file_path: str) -> Dict:
        """Run complete development pipeline on a file"""
        print(f"🔍 [LINTER] Analyzing {file_path}...")
        lint_result = self.linter.analyze_code(file_path)

        if "error" in lint_result:
            return lint_result

        print(f"📊 Found {len(lint_result.get('issues', []))} issues")

        # Apply fixes if issues found
        patch_result = {}
        if lint_result.get("issues"):
            print(f"🔧 [PATCHER] Applying fixes...")
            patch_result = self.patcher.apply_fixes(file_path, lint_result["issues"])
            print(f"✅ Applied {patch_result.get('fixes_applied', 0)} fixes")

        # Run tests
        print(f"🧪 [TESTBED] Running tests...")
        test_result = self.testbed.run_tests()
        print(
            f"🎯 Tests: {test_result.get('tests_passed', 0)} passed, {test_result.get('tests_failed', 0)} failed"
        )

        return {
            "file": file_path,
            "pipeline": "Linter→Patcher→Testbed",
            "linter_result": lint_result,
            "patcher_result": patch_result,
            "testbed_result": test_result,
            "status": "completed",
        }

    def process_project(self, project_path: str = ".") -> Dict:
        """Run development pipeline on entire project"""
        print("🚀 Starting Development Cluster Pipeline...")

        # Find all source files
        source_files = []
        for root, dirs, files in os.walk(project_path):
            # Skip common directories
            dirs[:] = [
                d
                for d in dirs
                if d not in [".git", "node_modules", "__pycache__", ".pytest_cache"]
            ]

            for file in files:
                if file.endswith(
                    (".py", ".js", ".ts", ".tsx", ".jsx", ".c", ".cpp", ".h", ".hpp")
                ):
                    source_files.append(os.path.join(root, file))

        print(f"📁 Found {len(source_files)} source files")

        results = []
        for file_path in source_files[:10]:  # Limit to first 10 files for demo
            result = self.process_file(file_path)
            results.append(result)

        # Final test run
        print("🏁 Final test validation...")
        final_test_result = self.testbed.run_tests(project_path)

        return {
            "project_path": project_path,
            "files_processed": len(results),
            "file_results": results,
            "final_tests": final_test_result,
            "pipeline": "Development Cluster v7.0",
            "status": "completed",
        }


if __name__ == "__main__":
    # Demo usage
    cluster = DevelopmentCluster()

    # Process current project
    # Use dynamic project root detection
    project_path = get_project_root()
    result = cluster.process_project(str(project_path))

    print("\n" + "=" * 60)
    print("🎉 DEVELOPMENT CLUSTER PIPELINE COMPLETE!")
    print("=" * 60)
    print(f"Files processed: {result['files_processed']}")
    print(
        f"Final test status: {'✅ PASSED' if result['final_tests'].get('success') else '❌ FAILED'}"
    )
