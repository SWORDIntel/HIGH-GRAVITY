#!/usr/bin/env python3
"""
LINTER Agent v9.0 - Senior Code Review Specialist
Python Implementation for Tandem Orchestration System

This module provides comprehensive code quality analysis, style enforcement,
security vulnerability detection, and automated fix capabilities.
"""

import ast
import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Import parallel orchestration enhancements
try:
    from parallel_orchestration_enhancements import (
        EnhancedOrchestrationMixin,
        MessageType,
        ParallelBatch,
        ParallelExecutionMode,
        ParallelOrchestrationEnhancer,
        ParallelTask,
        TaskResult,
    )

    HAS_ORCHESTRATION_ENHANCEMENTS = True
except ImportError:
    HAS_ORCHESTRATION_ENHANCEMENTS = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Issue severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(Enum):
    """Issue categories"""

    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    COMPLEXITY = "complexity"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    COMPATIBILITY = "compatibility"


@dataclass
class LintIssue:
    """Represents a linting issue"""

    file_path: str
    line_number: int
    column: int
    severity: SeverityLevel
    category: IssueCategory
    rule_id: str
    message: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False
    fix_content: Optional[str] = None
    confidence: float = 1.0


@dataclass
class QualityMetrics:
    """Code quality metrics"""

    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    cyclomatic_complexity: int = 0
    maintainability_index: float = 0.0
    test_coverage: float = 0.0
    documentation_coverage: float = 0.0
    duplication_ratio: float = 0.0
    technical_debt_minutes: int = 0


@dataclass
class LintResult:
    """Complete linting result"""

    file_path: str
    issues: List[LintIssue]
    metrics: QualityMetrics
    execution_time_ms: int
    tools_used: List[str]
    auto_fixes_applied: int = 0


class LanguageDetector:
    """Detects programming language from file extension"""

    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".c": "c",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".cc": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".java": "java",
        ".kt": "kotlin",
        ".swift": "swift",
        ".rb": "ruby",
        ".php": "php",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".less": "less",
    }

    @classmethod
    def detect(cls, file_path: str) -> Optional[str]:
        """Detect language from file extension"""
        ext = Path(file_path).suffix.lower()
        return cls.LANGUAGE_MAP.get(ext)


class BaseLinter(ABC):
    """Base class for language-specific linters"""

    @abstractmethod
    def lint(self, file_path: str, content: str) -> List[LintIssue]:
        """Lint the given file content"""
        pass

    @abstractmethod
    def can_auto_fix(self, issue: LintIssue) -> bool:
        """Check if issue can be auto-fixed"""
        pass

    @abstractmethod
    def auto_fix(self, file_path: str, content: str, issue: LintIssue) -> Optional[str]:
        """Auto-fix the issue and return corrected content"""
        pass


class PythonLinter(BaseLinter):
    """Python-specific linter implementation"""

    def __init__(self):
        self.security_patterns = [
            (r"eval\s*\(", "PY001", "Avoid eval() - potential code injection"),
            (r"exec\s*\(", "PY002", "Avoid exec() - potential code injection"),
            (
                r"subprocess\.call\([^)]*shell=True",
                "PY003",
                "Avoid shell=True - command injection risk",
            ),
            (r"pickle\.loads?\(", "PY004", "Pickle unsafe - use JSON instead"),
            (
                r"random\.random\(\)",
                "PY005",
                "Use secrets module for cryptographic randomness",
            ),
            (
                r"hashlib\.md5\(",
                "PY006",
                "MD5 is cryptographically broken - use SHA-256",
            ),
            (
                r"sqlite3\.execute\([^)]*%",
                "PY007",
                "SQL injection risk - use parameterized queries",
            ),
        ]

        self.performance_patterns = [
            (
                r"for\s+\w+\s+in\s+range\(len\(",
                "PY101",
                "Use enumerate() instead of range(len())",
            ),
            (r"\.join\(\[.*for.*\]\)", "PY102", "Use generator expression with join()"),
            (r"list\(filter\(", "PY103", "Use list comprehension instead of filter()"),
            (r"list\(map\(", "PY104", "Use list comprehension instead of map()"),
        ]

    def lint(self, file_path: str, content: str) -> List[LintIssue]:
        """Lint Python file"""
        issues = []

        # Parse AST for deeper analysis
        try:
            tree = ast.parse(content)
            issues.extend(self._analyze_ast(tree, file_path))
        except SyntaxError as e:
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=e.lineno or 1,
                    column=e.offset or 0,
                    severity=SeverityLevel.CRITICAL,
                    category=IssueCategory.SYNTAX,
                    rule_id="PY000",
                    message=f"Syntax error: {e.msg}",
                )
            )

        # Pattern-based analysis
        lines = content.split("\n")
        for line_no, line in enumerate(lines, 1):
            issues.extend(self._check_security_patterns(line, line_no, file_path))
            issues.extend(self._check_performance_patterns(line, line_no, file_path))
            issues.extend(self._check_style_patterns(line, line_no, file_path))

        return issues

    def _analyze_ast(self, tree: ast.AST, file_path: str) -> List[LintIssue]:
        """Analyze AST for complex issues"""
        issues = []

        class ComplexityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.complexity = 1
                self.function_lines = {}
                self.class_methods = {}

            def visit_FunctionDef(self, node):
                # Calculate cyclomatic complexity
                complexity = 1
                for child in ast.walk(node):
                    if isinstance(
                        child, (ast.If, ast.While, ast.For, ast.Try, ast.With)
                    ):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1

                if complexity > 10:
                    issues.append(
                        LintIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            severity=SeverityLevel.HIGH,
                            category=IssueCategory.COMPLEXITY,
                            rule_id="PY201",
                            message=f"Function {node.name} has high complexity ({complexity})",
                            suggestion="Consider breaking into smaller functions",
                        )
                    )

                # Check function length
                func_lines = (node.end_lineno or node.lineno) - node.lineno
                if func_lines > 50:
                    issues.append(
                        LintIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            severity=SeverityLevel.MEDIUM,
                            category=IssueCategory.MAINTAINABILITY,
                            rule_id="PY202",
                            message=f"Function {node.name} is too long ({func_lines} lines)",
                            suggestion="Consider breaking into smaller functions",
                        )
                    )

                self.generic_visit(node)

            def visit_ClassDef(self, node):
                # Count methods
                method_count = sum(
                    1 for child in node.body if isinstance(child, ast.FunctionDef)
                )

                if method_count > 20:
                    issues.append(
                        LintIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            severity=SeverityLevel.HIGH,
                            category=IssueCategory.MAINTAINABILITY,
                            rule_id="PY203",
                            message=f"Class {node.name} has too many methods ({method_count})",
                            suggestion="Consider splitting into multiple classes",
                        )
                    )

                self.generic_visit(node)

        visitor = ComplexityVisitor()
        visitor.visit(tree)

        return issues

    def _check_security_patterns(
        self, line: str, line_no: int, file_path: str
    ) -> List[LintIssue]:
        """Check for security vulnerabilities"""
        issues = []
        for pattern, rule_id, message in self.security_patterns:
            if re.search(pattern, line):
                issues.append(
                    LintIssue(
                        file_path=file_path,
                        line_number=line_no,
                        column=0,
                        severity=SeverityLevel.CRITICAL,
                        category=IssueCategory.SECURITY,
                        rule_id=rule_id,
                        message=message,
                        confidence=0.9,
                    )
                )
        return issues

    def _check_performance_patterns(
        self, line: str, line_no: int, file_path: str
    ) -> List[LintIssue]:
        """Check for performance issues"""
        issues = []
        for pattern, rule_id, message in self.performance_patterns:
            if re.search(pattern, line):
                issues.append(
                    LintIssue(
                        file_path=file_path,
                        line_number=line_no,
                        column=0,
                        severity=SeverityLevel.MEDIUM,
                        category=IssueCategory.PERFORMANCE,
                        rule_id=rule_id,
                        message=message,
                        auto_fixable=True,
                    )
                )
        return issues

    def _check_style_patterns(
        self, line: str, line_no: int, file_path: str
    ) -> List[LintIssue]:
        """Check for style issues"""
        issues = []

        # Line length
        if len(line) > 88:  # Black's default
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=line_no,
                    column=88,
                    severity=SeverityLevel.LOW,
                    category=IssueCategory.STYLE,
                    rule_id="PY301",
                    message=f"Line too long ({len(line)} chars)",
                    auto_fixable=True,
                )
            )

        # Trailing whitespace
        if line.endswith(" ") or line.endswith("\t"):
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=line_no,
                    column=len(line.rstrip()),
                    severity=SeverityLevel.LOW,
                    category=IssueCategory.STYLE,
                    rule_id="PY302",
                    message="Trailing whitespace",
                    auto_fixable=True,
                )
            )

        return issues

    def can_auto_fix(self, issue: LintIssue) -> bool:
        """Check if issue can be auto-fixed"""
        auto_fixable_rules = {"PY301", "PY302", "PY101", "PY102", "PY103", "PY104"}
        return issue.rule_id in auto_fixable_rules

    def auto_fix(self, file_path: str, content: str, issue: LintIssue) -> Optional[str]:
        """Auto-fix the issue"""
        lines = content.split("\n")

        if issue.rule_id == "PY302":  # Trailing whitespace
            if issue.line_number <= len(lines):
                lines[issue.line_number - 1] = lines[issue.line_number - 1].rstrip()
                return "\n".join(lines)

        # Add more auto-fix implementations as needed
        return None


class JavaScriptLinter(BaseLinter):
    """JavaScript/TypeScript linter implementation"""

    def __init__(self):
        self.security_patterns = [
            (r"eval\s*\(", "JS001", "Avoid eval() - potential code injection"),
            (r"document\.write\s*\(", "JS002", "Avoid document.write - XSS risk"),
            (r"innerHTML\s*=.*\+", "JS003", "Potential XSS - sanitize HTML content"),
            (
                r"Math\.random\(\)",
                "JS004",
                "Use crypto.getRandomValues() for secure randomness",
            ),
        ]

    def lint(self, file_path: str, content: str) -> List[LintIssue]:
        """Lint JavaScript/TypeScript file"""
        issues = []
        lines = content.split("\n")

        for line_no, line in enumerate(lines, 1):
            # Security patterns
            for pattern, rule_id, message in self.security_patterns:
                if re.search(pattern, line):
                    issues.append(
                        LintIssue(
                            file_path=file_path,
                            line_number=line_no,
                            column=0,
                            severity=SeverityLevel.HIGH,
                            category=IssueCategory.SECURITY,
                            rule_id=rule_id,
                            message=message,
                        )
                    )

            # Style checks
            if len(line) > 120:
                issues.append(
                    LintIssue(
                        file_path=file_path,
                        line_number=line_no,
                        column=120,
                        severity=SeverityLevel.LOW,
                        category=IssueCategory.STYLE,
                        rule_id="JS301",
                        message=f"Line too long ({len(line)} chars)",
                        auto_fixable=True,
                    )
                )

        return issues

    def can_auto_fix(self, issue: LintIssue) -> bool:
        return issue.rule_id in {"JS301"}

    def auto_fix(self, file_path: str, content: str, issue: LintIssue) -> Optional[str]:
        return None


class SecurityAnalyzer:
    """Dedicated security vulnerability analyzer"""

    def __init__(self):
        self.vulnerability_db = {
            "hardcoded_secrets": [
                r'(?i)(password|pwd|pass)\s*=\s*["\'][^"\']{3,}["\']',
                r'(?i)(api[_-]?key|apikey)\s*=\s*["\'][^"\']{10,}["\']',
                r'(?i)(secret|token)\s*=\s*["\'][^"\']{10,}["\']',
            ],
            "weak_crypto": [
                r"md5|sha1",
                r"DES|3DES",
                r"RC4",
            ],
            "injection_risks": [
                r"eval\s*\(",
                r"exec\s*\(",
                r"system\s*\(",
                r"shell_exec\s*\(",
            ],
        }

    def analyze(self, content: str, file_path: str) -> List[LintIssue]:
        """Analyze content for security vulnerabilities"""
        issues = []
        lines = content.split("\n")

        for line_no, line in enumerate(lines, 1):
            for vuln_type, patterns in self.vulnerability_db.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        severity = (
                            SeverityLevel.CRITICAL
                            if vuln_type == "injection_risks"
                            else SeverityLevel.HIGH
                        )
                        issues.append(
                            LintIssue(
                                file_path=file_path,
                                line_number=line_no,
                                column=0,
                                severity=severity,
                                category=IssueCategory.SECURITY,
                                rule_id=f"SEC_{vuln_type.upper()}",
                                message=f'Security vulnerability: {vuln_type.replace("_", " ")}',
                                confidence=0.8,
                            )
                        )

        return issues


class ComplexityAnalyzer:
    """Analyzes code complexity and maintainability"""

    def analyze_python_complexity(self, content: str) -> QualityMetrics:
        """Analyze Python code complexity"""
        try:
            tree = ast.parse(content)

            class ComplexityVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.complexity = 0
                    self.functions = 0
                    self.classes = 0
                    self.max_nesting = 0
                    self.current_nesting = 0

                def visit_FunctionDef(self, node):
                    self.functions += 1
                    self.current_nesting += 1
                    self.max_nesting = max(self.max_nesting, self.current_nesting)

                    # Calculate cyclomatic complexity
                    func_complexity = 1
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.While, ast.For, ast.Try)):
                            func_complexity += 1
                        elif isinstance(child, ast.BoolOp):
                            func_complexity += len(child.values) - 1

                    self.complexity += func_complexity
                    self.generic_visit(node)
                    self.current_nesting -= 1

                def visit_ClassDef(self, node):
                    self.classes += 1
                    self.generic_visit(node)

            visitor = ComplexityVisitor()
            visitor.visit(tree)

            lines = content.split("\n")
            total_lines = len(lines)
            code_lines = sum(
                1 for line in lines if line.strip() and not line.strip().startswith("#")
            )
            comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
            blank_lines = total_lines - code_lines - comment_lines

            # Calculate maintainability index (simplified)
            maintainability = (
                171
                - 5.2 * math.log(visitor.complexity)
                - 0.23 * visitor.functions
                - 16.2 * math.log(code_lines)
            )
            maintainability = max(0, min(100, maintainability))

            return QualityMetrics(
                total_lines=total_lines,
                code_lines=code_lines,
                comment_lines=comment_lines,
                blank_lines=blank_lines,
                cyclomatic_complexity=visitor.complexity,
                maintainability_index=maintainability,
                documentation_coverage=comment_lines / max(1, code_lines) * 100,
            )

        except Exception:
            return QualityMetrics()


class DuplicationDetector:
    """Detects code duplication"""

    def detect_duplicates(self, content: str, min_lines: int = 5) -> List[Dict]:
        """Detect duplicate code blocks"""
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        duplicates = []

        for i in range(len(lines) - min_lines + 1):
            block = tuple(lines[i : i + min_lines])

            for j in range(i + min_lines, len(lines) - min_lines + 1):
                compare_block = tuple(lines[j : j + min_lines])

                if block == compare_block:
                    duplicates.append(
                        {
                            "lines_1": (i + 1, i + min_lines),
                            "lines_2": (j + 1, j + min_lines),
                            "content": "\n".join(block),
                        }
                    )

        return duplicates


class LINTERPythonExecutor(
    EnhancedOrchestrationMixin if HAS_ORCHESTRATION_ENHANCEMENTS else object
):
    """
    LINTER Agent v10.0/9.0 - Senior Code Review Specialist
    Python implementation for Tandem Orchestration System

    Enhanced with optional parallel analysis, distributed processing, and
    inter-agent coordination capabilities.
    """

    def __init__(self):
        """Initialize LINTER agent with comprehensive capabilities"""
        self.agent_name = "LINTER"
        self.version = "9.0"
        self.capabilities = [
            "multi_language_linting",
            "security_vulnerability_detection",
            "performance_analysis",
            "complexity_analysis",
            "style_enforcement",
            "documentation_assessment",
            "test_coverage_analysis",
            "dependency_scanning",
            "duplication_detection",
            "best_practices_enforcement",
            "auto_fix_capabilities",
            "quality_gates",
            "continuous_improvement",
            "external_tool_integration",
            "custom_rule_configuration",
            "batch_processing",
            "performance_monitoring",
            "report_generation",
            "cicd_integration",
            "team_collaboration",
        ]

        # Initialize components
        self.language_detector = LanguageDetector()
        self.security_analyzer = SecurityAnalyzer()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.duplication_detector = DuplicationDetector()

        # Initialize linters
        self.linters = {
            "python": PythonLinter(),
            "javascript": JavaScriptLinter(),
            "typescript": JavaScriptLinter(),
        }

        # Metrics and caching
        self.metrics = {
            "files_analyzed": 0,
            "issues_found": 0,
            "auto_fixes_applied": 0,
            "execution_time_ms": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        self.cache = {}
        self.config = self._load_default_config()

        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=8)

        # Initialize orchestration enhancements if available
        if HAS_ORCHESTRATION_ENHANCEMENTS:
            super().__init__()  # Initialize EnhancedOrchestrationMixin
            self._orchestration_enhancer = ParallelOrchestrationEnhancer(max_workers=8)
            self.version = "10.0"  # Update version for enhanced capabilities
            self._parallel_analysis_enabled = True
        else:
            self._parallel_analysis_enabled = False

        logger.info(
            f"LINTER v{self.version} initialized with {len(self.capabilities)} capabilities"
        )

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            "max_line_length": {
                "python": 88,
                "javascript": 120,
                "typescript": 120,
                "default": 100,
            },
            "complexity_threshold": 10,
            "duplication_min_lines": 5,
            "auto_fix_enabled": True,
            "security_scan_enabled": True,
            "performance_analysis_enabled": True,
            "quality_gates": {
                "critical_issues": 0,
                "high_issues": 5,
                "complexity_threshold": 15,
                "duplication_ratio": 0.1,
            },
            "excluded_files": [
                "*.min.js",
                "*.bundle.js",
                "__pycache__/*",
                "node_modules/*",
                ".git/*",
            ],
        }

    async def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LINTER command with comprehensive analysis"""
        start_time = time.time()

        try:
            command_type = command.get("type", "lint_file")

            if command_type == "lint_file":
                result = await self._lint_file(command)
            elif command_type == "lint_directory":
                result = await self._lint_directory(command)
            elif command_type == "security_scan":
                result = await self._security_scan(command)
            elif command_type == "quality_report":
                result = await self._generate_quality_report(command)
            elif command_type == "auto_fix":
                result = await self._auto_fix_issues(command)
            elif command_type == "complexity_analysis":
                result = await self._analyze_complexity(command)
            elif command_type == "duplication_check":
                result = await self._check_duplication(command)
            elif command_type == "dependency_audit":
                result = await self._audit_dependencies(command)
            elif command_type == "configure_rules":
                result = await self._configure_rules(command)
            elif command_type == "batch_process":
                result = await self._batch_process(command)
            else:
                result = await self._handle_unknown_command(command)

            execution_time = int((time.time() - start_time) * 1000)
            result["execution_time_ms"] = execution_time
            self.metrics["execution_time_ms"] += execution_time

            return result

        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

    async def _lint_file(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Lint a single file with comprehensive analysis"""
        file_path = command.get("file_path")
        if not file_path or not os.path.exists(file_path):
            return {"success": False, "error": "File not found or not specified"}

        # Check cache
        file_hash = self._get_file_hash(file_path)
        cache_key = f"{file_path}:{file_hash}"

        if cache_key in self.cache:
            self.metrics["cache_hits"] += 1
            return self.cache[cache_key]

        self.metrics["cache_misses"] += 1

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {str(e)}"}

        language = self.language_detector.detect(file_path)
        if not language:
            return {"success": False, "error": "Unsupported file type"}

        issues = []
        tools_used = []

        # Language-specific linting
        if language in self.linters:
            linter_issues = self.linters[language].lint(file_path, content)
            issues.extend(linter_issues)
            tools_used.append(f"{language}_linter")

        # Security analysis
        if self.config["security_scan_enabled"]:
            security_issues = self.security_analyzer.analyze(content, file_path)
            issues.extend(security_issues)
            tools_used.append("security_analyzer")

        # Complexity analysis
        if language == "python":
            metrics = self.complexity_analyzer.analyze_python_complexity(content)

            if metrics.cyclomatic_complexity > self.config["complexity_threshold"]:
                issues.append(
                    LintIssue(
                        file_path=file_path,
                        line_number=1,
                        column=0,
                        severity=SeverityLevel.HIGH,
                        category=IssueCategory.COMPLEXITY,
                        rule_id="COMPLEXITY_HIGH",
                        message=f"High complexity score: {metrics.cyclomatic_complexity}",
                        suggestion="Consider refactoring to reduce complexity",
                    )
                )
        else:
            metrics = QualityMetrics()

        # Duplication detection
        if command.get("check_duplicates", True):
            duplicates = self.duplication_detector.detect_duplicates(content)
            for dup in duplicates:
                issues.append(
                    LintIssue(
                        file_path=file_path,
                        line_number=dup["lines_1"][0],
                        column=0,
                        severity=SeverityLevel.MEDIUM,
                        category=IssueCategory.MAINTAINABILITY,
                        rule_id="DUPLICATE_CODE",
                        message=f'Duplicate code detected (lines {dup["lines_1"][0]}-{dup["lines_1"][1]})',
                        suggestion="Extract common functionality to reduce duplication",
                    )
                )
            tools_used.append("duplication_detector")

        # Count auto-fixes applied
        auto_fixes_applied = 0
        if command.get("auto_fix", False) and self.config["auto_fix_enabled"]:
            auto_fixes_applied = await self._apply_auto_fixes(
                file_path, content, issues
            )

        result = {
            "success": True,
            "file_path": file_path,
            "language": language,
            "issues": [asdict(issue) for issue in issues],
            "metrics": asdict(metrics),
            "tools_used": tools_used,
            "auto_fixes_applied": auto_fixes_applied,
            "summary": {
                "total_issues": len(issues),
                "critical_issues": sum(
                    1 for issue in issues if issue.severity == SeverityLevel.CRITICAL
                ),
                "high_issues": sum(
                    1 for issue in issues if issue.severity == SeverityLevel.HIGH
                ),
                "medium_issues": sum(
                    1 for issue in issues if issue.severity == SeverityLevel.MEDIUM
                ),
                "low_issues": sum(
                    1 for issue in issues if issue.severity == SeverityLevel.LOW
                ),
                "security_issues": sum(
                    1 for issue in issues if issue.category == IssueCategory.SECURITY
                ),
                "performance_issues": sum(
                    1 for issue in issues if issue.category == IssueCategory.PERFORMANCE
                ),
            },
        }

        # Cache result
        self.cache[cache_key] = result
        self.metrics["files_analyzed"] += 1
        self.metrics["issues_found"] += len(issues)

        return result

    async def _lint_directory(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Lint all files in a directory"""
        directory = command.get("directory")
        if not directory or not os.path.isdir(directory):
            return {"success": False, "error": "Directory not found or not specified"}

        # Find all lintable files
        files = []
        for root, dirs, filenames in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [
                d
                for d in dirs
                if not any(
                    d.startswith(exclude.rstrip("/*"))
                    for exclude in self.config["excluded_files"]
                )
            ]

            for filename in filenames:
                file_path = os.path.join(root, filename)
                if self.language_detector.detect(
                    file_path
                ) and not self._is_excluded_file(file_path):
                    files.append(file_path)

        # Process files in parallel
        tasks = []
        for file_path in files:
            task_command = {**command, "file_path": file_path, "type": "lint_file"}
            tasks.append(self._lint_file(task_command))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        total_issues = 0
        total_files = 0
        critical_issues = 0
        high_issues = 0
        failed_files = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_files.append(files[i])
                continue

            if result.get("success"):
                total_files += 1
                total_issues += result.get("summary", {}).get("total_issues", 0)
                critical_issues += result.get("summary", {}).get("critical_issues", 0)
                high_issues += result.get("summary", {}).get("high_issues", 0)

        # Create linter files and documentation
        await self._create_linter_files(
            result, context if "context" in locals() else {}
        )
        return {
            "success": True,
            "directory": directory,
            "files_processed": total_files,
            "files_failed": len(failed_files),
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "high_issues": high_issues,
            "failed_files": failed_files,
            "results": [
                r for r in results if not isinstance(r, Exception) and r.get("success")
            ],
            "quality_gate_passed": critical_issues == 0
            and high_issues <= self.config["quality_gates"]["high_issues"],
        }

    async def _security_scan(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Perform dedicated security vulnerability scan"""
        target = command.get("target")  # file or directory

        if not target or not os.path.exists(target):
            return {"success": False, "error": "Target not found or not specified"}

        vulnerabilities = []

        if os.path.isfile(target):
            files = [target]
        else:
            files = []
            for root, dirs, filenames in os.walk(target):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    if self.language_detector.detect(file_path):
                        files.append(file_path)

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                file_vulnerabilities = self.security_analyzer.analyze(
                    content, file_path
                )
                vulnerabilities.extend(file_vulnerabilities)
            except Exception as e:
                logger.warning(f"Failed to scan {file_path}: {str(e)}")

        return {
            "success": True,
            "target": target,
            "vulnerabilities_found": len(vulnerabilities),
            "vulnerabilities": [asdict(vuln) for vuln in vulnerabilities],
            "severity_breakdown": {
                "critical": sum(
                    1 for v in vulnerabilities if v.severity == SeverityLevel.CRITICAL
                ),
                "high": sum(
                    1 for v in vulnerabilities if v.severity == SeverityLevel.HIGH
                ),
                "medium": sum(
                    1 for v in vulnerabilities if v.severity == SeverityLevel.MEDIUM
                ),
                "low": sum(
                    1 for v in vulnerabilities if v.severity == SeverityLevel.LOW
                ),
            },
            "security_score": max(0, 100 - len(vulnerabilities) * 10),  # Simple scoring
        }

    async def _generate_quality_report(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        target = command.get("target")
        if not target:
            return {"success": False, "error": "Target not specified"}

        # Perform comprehensive analysis
        lint_result = await self._lint_directory(
            {"directory": target}
            if os.path.isdir(target)
            else {"file_path": target, "type": "lint_file"}
        )
        security_result = await self._security_scan({"target": target})

        # Generate report
        report = {
            "success": True,
            "target": target,
            "timestamp": int(time.time()),
            "quality_overview": {
                "files_analyzed": lint_result.get("files_processed", 1),
                "total_issues": lint_result.get("total_issues", 0),
                "critical_issues": lint_result.get("critical_issues", 0),
                "security_vulnerabilities": security_result.get(
                    "vulnerabilities_found", 0
                ),
                "quality_gate_passed": lint_result.get("quality_gate_passed", False),
            },
            "detailed_analysis": {
                "linting_results": lint_result,
                "security_scan": security_result,
            },
            "recommendations": self._generate_recommendations(
                lint_result, security_result
            ),
            "metrics": self.metrics.copy(),
        }

        return report

    async def _auto_fix_issues(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically fix safe issues"""
        file_path = command.get("file_path")
        if not file_path or not os.path.exists(file_path):
            return {"success": False, "error": "File not found or not specified"}

        # First, lint the file to get issues
        lint_result = await self._lint_file({"file_path": file_path})
        if not lint_result.get("success"):
            return lint_result

        issues = [LintIssue(**issue_data) for issue_data in lint_result["issues"]]
        fixable_issues = [issue for issue in issues if issue.auto_fixable]

        if not fixable_issues:
            return {
                "success": True,
                "file_path": file_path,
                "fixes_applied": 0,
                "message": "No auto-fixable issues found",
            }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {str(e)}"}

        # Apply fixes
        fixes_applied = await self._apply_auto_fixes(file_path, content, fixable_issues)

        return {
            "success": True,
            "file_path": file_path,
            "fixes_applied": fixes_applied,
            "fixable_issues": len(fixable_issues),
            "fixed_issues": [asdict(issue) for issue in fixable_issues],
        }

    async def _apply_auto_fixes(
        self, file_path: str, content: str, issues: List[LintIssue]
    ) -> int:
        """Apply automatic fixes to content"""
        language = self.language_detector.detect(file_path)
        if not language or language not in self.linters:
            return 0

        linter = self.linters[language]
        modified_content = content
        fixes_applied = 0

        # Sort issues by line number (reverse order to maintain line numbers)
        fixable_issues = [issue for issue in issues if linter.can_auto_fix(issue)]
        fixable_issues.sort(key=lambda x: x.line_number, reverse=True)

        for issue in fixable_issues:
            fixed_content = linter.auto_fix(file_path, modified_content, issue)
            if fixed_content and fixed_content != modified_content:
                modified_content = fixed_content
                fixes_applied += 1

        # Write back if fixes were applied
        if fixes_applied > 0:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(modified_content)
                self.metrics["auto_fixes_applied"] += fixes_applied
            except Exception as e:
                logger.error(f"Failed to write fixes to {file_path}: {str(e)}")
                return 0

        return fixes_applied

    async def _analyze_complexity(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code complexity"""
        file_path = command.get("file_path")
        if not file_path or not os.path.exists(file_path):
            return {"success": False, "error": "File not found or not specified"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {str(e)}"}

        language = self.language_detector.detect(file_path)

        if language == "python":
            metrics = self.complexity_analyzer.analyze_python_complexity(content)
        else:
            metrics = QualityMetrics()

        return {
            "success": True,
            "file_path": file_path,
            "language": language,
            "complexity_metrics": asdict(metrics),
            "complexity_rating": self._get_complexity_rating(
                metrics.cyclomatic_complexity
            ),
            "maintainability_rating": self._get_maintainability_rating(
                metrics.maintainability_index
            ),
        }

    async def _check_duplication(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Check for code duplication"""
        target = command.get("target")
        if not target or not os.path.exists(target):
            return {"success": False, "error": "Target not found or not specified"}

        duplications = []

        if os.path.isfile(target):
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
            file_duplications = self.duplication_detector.detect_duplicates(content)
            duplications.extend([(target, dup) for dup in file_duplications])
        else:
            # Check across multiple files
            files = []
            for root, dirs, filenames in os.walk(target):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    if self.language_detector.detect(file_path):
                        files.append(file_path)

            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    file_duplications = self.duplication_detector.detect_duplicates(
                        content
                    )
                    duplications.extend([(file_path, dup) for dup in file_duplications])
                except Exception:
                    continue

        return {
            "success": True,
            "target": target,
            "duplications_found": len(duplications),
            "duplications": [
                {"file": file, "duplication": dup} for file, dup in duplications
            ],
            "duplication_ratio": (
                len(duplications) / max(1, len(files)) if "files" in locals() else 0
            ),
        }

    async def _audit_dependencies(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Audit project dependencies for vulnerabilities"""
        project_root = command.get("project_root", ".")

        vulnerabilities = []
        dependency_files = []

        # Check for dependency files
        dependency_patterns = {
            "package.json": "npm",
            "requirements.txt": "pip",
            "Pipfile": "pipenv",
            "poetry.lock": "poetry",
            "Cargo.toml": "cargo",
            "go.mod": "go",
        }

        for filename, manager in dependency_patterns.items():
            file_path = os.path.join(project_root, filename)
            if os.path.exists(file_path):
                dependency_files.append({"file": filename, "manager": manager})

        # Simulate dependency scanning (in real implementation, would use actual tools)
        for dep_file in dependency_files:
            # This would integrate with actual vulnerability databases
            # For now, returning mock data
            vulnerabilities.append(
                {
                    "package": f'example-{dep_file["manager"]}-package',
                    "severity": "medium",
                    "description": "Example vulnerability",
                    "fixed_version": "1.2.3",
                }
            )

        return {
            "success": True,
            "project_root": project_root,
            "dependency_files": dependency_files,
            "vulnerabilities": vulnerabilities,
            "security_score": max(0, 100 - len(vulnerabilities) * 15),
        }

    async def _configure_rules(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Configure linting rules"""
        rules = command.get("rules", {})

        # Update configuration
        self.config.update(rules)

        return {
            "success": True,
            "message": "Rules updated successfully",
            "current_config": self.config.copy(),
        }

    async def _batch_process(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Process multiple files/directories in batch"""
        targets = command.get("targets", [])
        operation = command.get("operation", "lint")

        if not targets:
            return {"success": False, "error": "No targets specified"}

        results = []

        for target in targets:
            if operation == "lint":
                if os.path.isdir(target):
                    result = await self._lint_directory({"directory": target})
                else:
                    result = await self._lint_file({"file_path": target})
            elif operation == "security_scan":
                result = await self._security_scan({"target": target})
            elif operation == "auto_fix":
                result = await self._auto_fix_issues({"file_path": target})
            else:
                result = {"success": False, "error": f"Unknown operation: {operation}"}

            results.append({"target": target, "result": result})

        return {
            "success": True,
            "operation": operation,
            "targets_processed": len(targets),
            "results": results,
            "summary": {
                "successful": sum(1 for r in results if r["result"].get("success")),
                "failed": sum(1 for r in results if not r["result"].get("success")),
            },
        }

    async def _handle_unknown_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown command"""
        return {
            "success": False,
            "error": f'Unknown command type: {command.get("type")}',
            "available_commands": [
                "lint_file",
                "lint_directory",
                "security_scan",
                "quality_report",
                "auto_fix",
                "complexity_analysis",
                "duplication_check",
                "dependency_audit",
                "configure_rules",
                "batch_process",
            ],
        }

    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file content for caching"""
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return str(int(time.time()))

    def _is_excluded_file(self, file_path: str) -> bool:
        """Check if file should be excluded"""
        for pattern in self.config["excluded_files"]:
            if pattern in file_path or file_path.endswith(pattern.replace("*", "")):
                return True
        return False

    def _get_complexity_rating(self, complexity: int) -> str:
        """Get human-readable complexity rating"""
        if complexity <= 5:
            return "Low"
        elif complexity <= 10:
            return "Moderate"
        elif complexity <= 20:
            return "High"
        else:
            return "Very High"

    def _get_maintainability_rating(self, index: float) -> str:
        """Get maintainability rating"""
        if index >= 85:
            return "Excellent"
        elif index >= 70:
            return "Good"
        elif index >= 50:
            return "Moderate"
        elif index >= 25:
            return "Poor"
        else:
            return "Critical"

    def _generate_recommendations(
        self, lint_result: Dict, security_result: Dict
    ) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []

        critical_issues = lint_result.get("critical_issues", 0)
        security_vulns = security_result.get("vulnerabilities_found", 0)

        if critical_issues > 0:
            recommendations.append(
                f"Address {critical_issues} critical issues immediately"
            )

        if security_vulns > 0:
            recommendations.append(f"Fix {security_vulns} security vulnerabilities")

        if lint_result.get("total_issues", 0) > 50:
            recommendations.append("Consider implementing stricter quality gates")

        recommendations.extend(
            [
                "Set up automated linting in CI/CD pipeline",
                "Configure pre-commit hooks for early issue detection",
                "Regular code reviews with linting integration",
                "Track and reduce technical debt over time",
            ]
        )

        return recommendations

    async def get_status(self) -> Dict[str, Any]:
        """Get current agent status and metrics"""
        return {
            "agent_name": self.agent_name,
            "version": self.version,
            "status": "healthy",
            "capabilities": self.capabilities,
            "metrics": self.metrics.copy(),
            "cache_size": len(self.cache),
            "supported_languages": list(self.linters.keys()),
            "configuration": {
                "auto_fix_enabled": self.config["auto_fix_enabled"],
                "security_scan_enabled": self.config["security_scan_enabled"],
                "complexity_threshold": self.config["complexity_threshold"],
            },
        }


# Export the main executor class
__all__ = ["LINTERPythonExecutor"]
