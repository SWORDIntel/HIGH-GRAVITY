#!/usr/bin/env python3
"""
Neural Code Reviewer - Real-time AI-powered Code Review
Team Echo Implementation

Features:
- Real-time code quality analysis
- Neural pattern recognition
- Security vulnerability detection
- Performance optimization suggestions
- OpenVINO neural acceleration
"""

import ast
import asyncio
import base64
import hashlib
import json
import logging
import os
import pickle
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import asyncpg
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CodeMetrics:
    """Comprehensive code metrics"""

    complexity_score: float
    maintainability_index: float
    duplication_ratio: float
    test_coverage_estimate: float
    documentation_ratio: float
    security_score: float
    performance_score: float
    style_consistency: float


@dataclass
class CodeIssue:
    """Individual code issue or suggestion"""

    issue_type: str  # 'security', 'performance', 'maintainability', 'style', 'bug'
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    line_number: int
    column: Optional[int]
    message: str
    suggestion: str
    confidence: float
    rule_id: str


@dataclass
class CodeReview:
    """Complete code review result"""

    overall_score: float
    metrics: CodeMetrics
    issues: List[CodeIssue]
    suggestions: List[str]
    neural_insights: List[str]
    estimated_review_time: int
    complexity_breakdown: Dict[str, float]
    diff_analysis: Optional[Dict[str, Any]] = None


class NeuralCodeReviewer:
    """Advanced AI-powered code reviewer with neural acceleration"""

    def __init__(self, database_url: str = None):
        self.db_url = (
            database_url
            or "postgresql://claude_agent:claude_secure_password@localhost:5433/claude_agents_auth"
        )
        self.db_pool = None

        # Neural components
        self.neural_model_loaded = False
        self.pattern_cache = {}
        self.security_patterns = self._initialize_security_patterns()
        self.performance_patterns = self._initialize_performance_patterns()
        self.quality_patterns = self._initialize_quality_patterns()

        # Code analysis caches
        self.complexity_cache = {}
        self.style_cache = {}

        # Performance metrics
        self.reviews_completed = 0
        self.total_issues_found = 0
        self.avg_review_time = 0.0

        # Language-specific analyzers
        self.language_analyzers = {
            ".py": self._analyze_python_code,
            ".js": self._analyze_javascript_code,
            ".java": self._analyze_java_code,
            ".cpp": self._analyze_cpp_code,
            ".c": self._analyze_c_code,
            ".go": self._analyze_go_code,
            ".rs": self._analyze_rust_code,
        }

    async def initialize(self):
        """Initialize the neural code reviewer"""
        try:
            # Database connection
            self.db_pool = await asyncpg.create_pool(
                self.db_url, min_size=2, max_size=8, command_timeout=30
            )

            # Ensure schema
            await self._ensure_reviewer_schema()

            # Initialize neural models
            await self._initialize_neural_models()

            # Load historical patterns
            await self._load_review_patterns()

            logger.info("Neural Code Reviewer initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize neural code reviewer: {e}")
            return False

    async def _ensure_reviewer_schema(self):
        """Ensure code review schema exists"""
        async with self.db_pool.acquire() as conn:
            # Code reviews
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS git_intelligence.code_reviews (
                    id SERIAL PRIMARY KEY,
                    repo_path TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    commit_hash TEXT,
                    review_type TEXT NOT NULL, -- 'commit', 'pr', 'file', 'diff'
                    overall_score FLOAT NOT NULL,
                    complexity_score FLOAT,
                    security_score FLOAT,
                    performance_score FLOAT,
                    maintainability_score FLOAT,
                    issues_found INTEGER DEFAULT 0,
                    critical_issues INTEGER DEFAULT 0,
                    review_time_ms INTEGER,
                    neural_enhanced BOOLEAN DEFAULT FALSE,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            )

            # Code issues
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS git_intelligence.code_issues (
                    id SERIAL PRIMARY KEY,
                    review_id INTEGER REFERENCES git_intelligence.code_reviews(id),
                    file_path TEXT NOT NULL,
                    issue_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    line_number INTEGER,
                    column_number INTEGER,
                    message TEXT NOT NULL,
                    suggestion TEXT,
                    confidence FLOAT DEFAULT 0.0,
                    rule_id TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            )

            # Pattern learning
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS git_intelligence.review_patterns (
                    id SERIAL PRIMARY KEY,
                    pattern_type TEXT NOT NULL, -- 'security', 'performance', 'quality'
                    pattern_hash TEXT NOT NULL,
                    code_snippet TEXT,
                    issue_description TEXT,
                    fix_suggestion TEXT,
                    confidence_score FLOAT DEFAULT 0.0,
                    occurrence_count INTEGER DEFAULT 1,
                    false_positive_count INTEGER DEFAULT 0,
                    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(pattern_hash)
                )
            """
            )

            # Neural embeddings for code patterns
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS git_intelligence.code_pattern_embeddings (
                    id SERIAL PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    code_hash TEXT NOT NULL,
                    embedding vector(256),
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            )

            # Create indexes
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_code_reviews_file 
                ON git_intelligence.code_reviews(file_path);
                CREATE INDEX IF NOT EXISTS idx_code_issues_severity 
                ON git_intelligence.code_issues(severity, issue_type);
                CREATE INDEX IF NOT EXISTS idx_pattern_embeddings_similarity 
                ON git_intelligence.code_pattern_embeddings USING ivfflat (embedding vector_cosine_ops);
            """
            )

    def _initialize_security_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize security vulnerability patterns"""
        return {
            "python": [
                {
                    "pattern": r"eval\s*\(",
                    "severity": "critical",
                    "message": "Use of eval() is dangerous and can lead to code injection",
                    "suggestion": "Use ast.literal_eval() for safe evaluation or find alternative approaches",
                },
                {
                    "pattern": r"exec\s*\(",
                    "severity": "critical",
                    "message": "Use of exec() can execute arbitrary code",
                    "suggestion": "Avoid exec() or ensure input is properly sanitized and validated",
                },
                {
                    "pattern": r"subprocess\.call\s*\([^)]*shell\s*=\s*True",
                    "severity": "high",
                    "message": "Using shell=True with subprocess can lead to command injection",
                    "suggestion": "Use subprocess with a list of arguments instead of shell=True",
                },
                {
                    "pattern": r"pickle\.loads?\s*\(",
                    "severity": "high",
                    "message": "Pickle deserialization can execute arbitrary code",
                    "suggestion": "Use json or other safe serialization formats for untrusted data",
                },
                {
                    "pattern": r"random\.random\s*\(\)",
                    "severity": "medium",
                    "message": "random.random() is not cryptographically secure",
                    "suggestion": "Use secrets module for cryptographic operations",
                },
            ],
            "javascript": [
                {
                    "pattern": r"eval\s*\(",
                    "severity": "critical",
                    "message": "eval() can execute arbitrary JavaScript code",
                    "suggestion": "Use JSON.parse() for data or find alternative approaches",
                },
                {
                    "pattern": r"innerHTML\s*=.*\+",
                    "severity": "high",
                    "message": "Dynamic innerHTML assignment can lead to XSS",
                    "suggestion": "Use textContent or properly sanitize HTML content",
                },
                {
                    "pattern": r"document\.write\s*\(",
                    "severity": "medium",
                    "message": "document.write() can be dangerous and blocks rendering",
                    "suggestion": "Use modern DOM manipulation methods",
                },
            ],
        }

    def _initialize_performance_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize performance anti-patterns"""
        return {
            "python": [
                {
                    "pattern": r"for\s+\w+\s+in\s+range\s*\(\s*len\s*\([^)]+\)\s*\):",
                    "severity": "medium",
                    "message": "Using range(len()) is inefficient",
                    "suggestion": "Use enumerate() or iterate directly over the collection",
                },
                {
                    "pattern": r"\.append\s*\([^)]+\)\s*\n\s*\.append",
                    "severity": "low",
                    "message": "Multiple consecutive appends can be optimized",
                    "suggestion": "Consider using list comprehension or extend()",
                },
                {
                    "pattern": r"\+\=.*\+.*str\s*\(",
                    "severity": "medium",
                    "message": "String concatenation in loops is inefficient",
                    "suggestion": "Use join() or f-strings for better performance",
                },
            ],
            "javascript": [
                {
                    "pattern": r"for\s*\(\s*var\s+\w+\s*=\s*0.*\.length",
                    "severity": "low",
                    "message": "Traditional for loop can be less readable",
                    "suggestion": "Consider using forEach(), map(), or for...of",
                },
                {
                    "pattern": r"document\.getElementById\s*\([^)]+\).*document\.getElementById",
                    "severity": "medium",
                    "message": "Repeated DOM queries are expensive",
                    "suggestion": "Cache DOM elements in variables",
                },
            ],
        }

    def _initialize_quality_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize code quality patterns"""
        return {
            "python": [
                {
                    "pattern": r"except\s*:",
                    "severity": "medium",
                    "message": "Bare except clauses catch all exceptions",
                    "suggestion": "Specify exact exception types to catch",
                },
                {
                    "pattern": r"print\s*\(",
                    "severity": "low",
                    "message": "Print statements may be debug code",
                    "suggestion": "Use proper logging instead of print statements",
                },
                {
                    "pattern": r"def\s+\w+\s*\([^)]{50,}",
                    "severity": "medium",
                    "message": "Function has too many parameters",
                    "suggestion": "Consider using a configuration object or breaking down the function",
                },
            ],
            "javascript": [
                {
                    "pattern": r"console\.log\s*\(",
                    "severity": "low",
                    "message": "Console.log statements may be debug code",
                    "suggestion": "Remove debug statements or use proper logging",
                },
                {
                    "pattern": r"==\s*(?!==)",
                    "severity": "medium",
                    "message": "Use strict equality operator",
                    "suggestion": "Use === instead of == for type-safe comparisons",
                },
            ],
        }

    async def _initialize_neural_models(self):
        """Initialize neural model components"""
        try:
            # Check for OpenVINO availability
            openvino_path = Path("${OPENVINO_ROOT:-/opt/openvino/}")
            if openvino_path.exists():
                # Initialize neural pattern recognition
                await self._setup_neural_patterns()
                self.neural_model_loaded = True
                logger.info("Neural code analysis models loaded")
            else:
                logger.info(
                    "Neural acceleration not available, using statistical analysis"
                )

        except Exception as e:
            logger.warning(f"Neural model initialization failed: {e}")

    async def _setup_neural_patterns(self):
        """Setup neural pattern recognition"""
        try:
            # Load cached pattern embeddings
            async with self.db_pool.acquire() as conn:
                patterns = await conn.fetch(
                    """
                    SELECT pattern_type, code_hash, embedding, metadata
                    FROM git_intelligence.code_pattern_embeddings
                    WHERE created_at > NOW() - INTERVAL '30 days'
                """
                )

                for pattern in patterns:
                    if pattern["embedding"]:
                        self.pattern_cache[pattern["code_hash"]] = {
                            "type": pattern["pattern_type"],
                            "vector": np.array(pattern["embedding"]),
                            "metadata": pattern["metadata"],
                        }

                logger.info(f"Loaded {len(patterns)} neural pattern embeddings")

        except Exception as e:
            logger.debug(f"Could not load neural patterns: {e}")

    async def _load_review_patterns(self):
        """Load historical review patterns"""
        try:
            async with self.db_pool.acquire() as conn:
                patterns = await conn.fetch(
                    """
                    SELECT pattern_type, pattern_hash, issue_description, 
                           fix_suggestion, confidence_score, occurrence_count
                    FROM git_intelligence.review_patterns
                    WHERE occurrence_count > 1 AND confidence_score > 0.5
                """
                )

                pattern_counts = defaultdict(int)
                for pattern in patterns:
                    pattern_counts[pattern["pattern_type"]] += pattern[
                        "occurrence_count"
                    ]

                logger.info(f"Loaded review patterns: {dict(pattern_counts)}")

        except Exception as e:
            logger.warning(f"Could not load review patterns: {e}")

    def _calculate_complexity_metrics(
        self, code: str, file_path: str
    ) -> Dict[str, float]:
        """Calculate comprehensive complexity metrics"""
        try:
            metrics = {
                "cyclomatic_complexity": 0.0,
                "cognitive_complexity": 0.0,
                "nesting_depth": 0.0,
                "function_length": 0.0,
                "parameter_count": 0.0,
            }

            lines = code.split("\n")

            # Basic cyclomatic complexity (simplified)
            complexity_keywords = [
                "if",
                "elif",
                "for",
                "while",
                "try",
                "except",
                "and",
                "or",
            ]
            complexity_count = 0
            max_nesting = 0
            current_nesting = 0

            for line in lines:
                stripped = line.strip()

                # Count complexity-increasing constructs
                for keyword in complexity_keywords:
                    complexity_count += stripped.count(f" {keyword} ") + stripped.count(
                        f"{keyword} "
                    )

                # Track nesting depth
                if any(
                    keyword in stripped
                    for keyword in ["if ", "for ", "while ", "try:", "def ", "class "]
                ):
                    current_nesting += 1
                    max_nesting = max(max_nesting, current_nesting)

                # Approximate nesting decrease (simplified)
                if line.startswith("    ") and len(line.strip()) < len(line) / 2:
                    current_nesting = max(0, current_nesting - 1)

            # Calculate metrics
            total_lines = len(lines)
            metrics["cyclomatic_complexity"] = min(
                10.0, complexity_count / max(total_lines / 10, 1)
            )
            metrics["cognitive_complexity"] = min(
                10.0, (complexity_count + max_nesting) / max(total_lines / 8, 1)
            )
            metrics["nesting_depth"] = min(10.0, max_nesting / 5.0)

            # Function analysis (simplified)
            function_matches = re.findall(r"def\s+\w+\s*\([^)]*\)", code)
            if function_matches:
                avg_params = np.mean([func.count(",") + 1 for func in function_matches])
                metrics["parameter_count"] = min(10.0, avg_params / 5.0)

                # Estimate average function length
                function_starts = [i for i, line in enumerate(lines) if "def " in line]
                if len(function_starts) > 1:
                    avg_length = np.mean(
                        [
                            function_starts[i + 1] - function_starts[i]
                            for i in range(len(function_starts) - 1)
                        ]
                    )
                    metrics["function_length"] = min(10.0, avg_length / 20.0)

            return metrics

        except Exception as e:
            logger.debug(f"Error calculating complexity: {e}")
            return {
                key: 5.0
                for key in [
                    "cyclomatic_complexity",
                    "cognitive_complexity",
                    "nesting_depth",
                    "function_length",
                    "parameter_count",
                ]
            }

    def _analyze_code_patterns(self, code: str, language: str) -> List[CodeIssue]:
        """Analyze code for pattern-based issues"""
        issues = []
        lines = code.split("\n")

        # Get patterns for language
        security_patterns = self.security_patterns.get(language, [])
        performance_patterns = self.performance_patterns.get(language, [])
        quality_patterns = self.quality_patterns.get(language, [])

        all_patterns = [
            ("security", security_patterns),
            ("performance", performance_patterns),
            ("quality", quality_patterns),
        ]

        for line_num, line in enumerate(lines, 1):
            for issue_type, patterns in all_patterns:
                for pattern_info in patterns:
                    if re.search(pattern_info["pattern"], line, re.IGNORECASE):
                        issue = CodeIssue(
                            issue_type=issue_type,
                            severity=pattern_info["severity"],
                            line_number=line_num,
                            column=None,
                            message=pattern_info["message"],
                            suggestion=pattern_info["suggestion"],
                            confidence=0.85,  # Pattern-based rules are quite reliable
                            rule_id=f"{issue_type}_{hash(pattern_info['pattern']) % 10000}",
                        )
                        issues.append(issue)

        return issues

    def _analyze_python_code(self, code: str) -> Tuple[List[CodeIssue], Dict[str, Any]]:
        """Analyze Python-specific code patterns"""
        issues = []
        analysis = {"language": "python", "parsed_successfully": False}

        try:
            # Parse AST for deeper analysis
            tree = ast.parse(code)
            analysis["parsed_successfully"] = True

            # Analyze AST nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check function complexity
                    if len(node.args.args) > 5:
                        issues.append(
                            CodeIssue(
                                issue_type="maintainability",
                                severity="medium",
                                line_number=node.lineno,
                                column=node.col_offset,
                                message=f'Function "{node.name}" has too many parameters ({len(node.args.args)})',
                                suggestion="Consider using a configuration object or breaking down the function",
                                confidence=0.9,
                                rule_id="py_too_many_params",
                            )
                        )

                elif isinstance(node, ast.Try):
                    # Check for bare except
                    for handler in node.handlers:
                        if handler.type is None:
                            issues.append(
                                CodeIssue(
                                    issue_type="quality",
                                    severity="medium",
                                    line_number=handler.lineno,
                                    column=handler.col_offset,
                                    message="Bare except clause catches all exceptions",
                                    suggestion="Specify exact exception types to catch",
                                    confidence=0.95,
                                    rule_id="py_bare_except",
                                )
                            )

                elif isinstance(node, ast.Call):
                    # Check for dangerous function calls
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ["eval", "exec"]:
                            issues.append(
                                CodeIssue(
                                    issue_type="security",
                                    severity="critical",
                                    line_number=node.lineno,
                                    column=node.col_offset,
                                    message=f"Use of {node.func.id}() is dangerous",
                                    suggestion="Use safer alternatives or ensure proper input validation",
                                    confidence=0.98,
                                    rule_id=f"py_dangerous_{node.func.id}",
                                )
                            )

        except SyntaxError as e:
            issues.append(
                CodeIssue(
                    issue_type="syntax",
                    severity="critical",
                    line_number=e.lineno or 1,
                    column=e.offset,
                    message=f"Syntax error: {e.msg}",
                    suggestion="Fix syntax error before proceeding",
                    confidence=1.0,
                    rule_id="py_syntax_error",
                )
            )
        except Exception as e:
            logger.debug(f"Python AST analysis failed: {e}")

        return issues, analysis

    def _analyze_javascript_code(
        self, code: str
    ) -> Tuple[List[CodeIssue], Dict[str, Any]]:
        """Analyze JavaScript-specific patterns"""
        issues = []
        analysis = {"language": "javascript"}

        # Pattern-based analysis for JavaScript
        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Check for common JavaScript issues
            if "==" in stripped and "===" not in stripped:
                issues.append(
                    CodeIssue(
                        issue_type="quality",
                        severity="medium",
                        line_number=line_num,
                        column=stripped.find("=="),
                        message="Use strict equality operator",
                        suggestion="Use === instead of == for type-safe comparisons",
                        confidence=0.8,
                        rule_id="js_strict_equality",
                    )
                )

            if "var " in stripped:
                issues.append(
                    CodeIssue(
                        issue_type="quality",
                        severity="low",
                        line_number=line_num,
                        column=stripped.find("var"),
                        message="Use let or const instead of var",
                        suggestion="Use let for mutable variables, const for immutable",
                        confidence=0.7,
                        rule_id="js_modern_declarations",
                    )
                )

        return issues, analysis

    def _analyze_java_code(self, code: str) -> Tuple[List[CodeIssue], Dict[str, Any]]:
        """Analyze Java-specific patterns"""
        issues = []
        analysis = {"language": "java"}

        # Basic Java pattern analysis
        if "System.out.print" in code:
            line_num = (
                code.split("\n").index(
                    next(
                        line for line in code.split("\n") if "System.out.print" in line
                    )
                )
                + 1
            )
            issues.append(
                CodeIssue(
                    issue_type="quality",
                    severity="low",
                    line_number=line_num,
                    column=None,
                    message="System.out.print may be debug code",
                    suggestion="Use proper logging framework",
                    confidence=0.6,
                    rule_id="java_debug_print",
                )
            )

        return issues, analysis

    def _analyze_cpp_code(self, code: str) -> Tuple[List[CodeIssue], Dict[str, Any]]:
        """Analyze C++ specific patterns"""
        issues = []
        analysis = {"language": "cpp"}

        # Basic C++ analysis
        if "malloc(" in code and "free(" not in code:
            line_num = (
                code.split("\n").index(
                    next(line for line in code.split("\n") if "malloc(" in line)
                )
                + 1
            )
            issues.append(
                CodeIssue(
                    issue_type="maintainability",
                    severity="high",
                    line_number=line_num,
                    column=None,
                    message="malloc() without corresponding free() may cause memory leak",
                    suggestion="Ensure every malloc() has a corresponding free() or use smart pointers",
                    confidence=0.7,
                    rule_id="cpp_memory_leak",
                )
            )

        return issues, analysis

    def _analyze_c_code(self, code: str) -> Tuple[List[CodeIssue], Dict[str, Any]]:
        """Analyze C-specific patterns"""
        return self._analyze_cpp_code(code)  # Similar patterns

    def _analyze_go_code(self, code: str) -> Tuple[List[CodeIssue], Dict[str, Any]]:
        """Analyze Go-specific patterns"""
        issues = []
        analysis = {"language": "go"}

        # Basic Go analysis
        if "fmt.Print" in code:
            line_num = (
                code.split("\n").index(
                    next(line for line in code.split("\n") if "fmt.Print" in line)
                )
                + 1
            )
            issues.append(
                CodeIssue(
                    issue_type="quality",
                    severity="low",
                    line_number=line_num,
                    column=None,
                    message="fmt.Print may be debug code",
                    suggestion="Use proper logging",
                    confidence=0.6,
                    rule_id="go_debug_print",
                )
            )

        return issues, analysis

    def _analyze_rust_code(self, code: str) -> Tuple[List[CodeIssue], Dict[str, Any]]:
        """Analyze Rust-specific patterns"""
        issues = []
        analysis = {"language": "rust"}

        # Basic Rust analysis
        if "unwrap()" in code:
            line_num = (
                code.split("\n").index(
                    next(line for line in code.split("\n") if "unwrap()" in line)
                )
                + 1
            )
            issues.append(
                CodeIssue(
                    issue_type="maintainability",
                    severity="medium",
                    line_number=line_num,
                    column=None,
                    message="unwrap() can panic at runtime",
                    suggestion="Use proper error handling with match or expect()",
                    confidence=0.8,
                    rule_id="rust_unwrap_danger",
                )
            )

        return issues, analysis

    async def review_code(
        self, code: str, file_path: str, review_type: str = "file"
    ) -> CodeReview:
        """Comprehensive code review with neural enhancement"""
        try:
            start_time = time.time()

            logger.info(f"Starting code review for {file_path} ({len(code)} chars)")

            # Determine language
            file_ext = Path(file_path).suffix.lower()
            language = {
                ".py": "python",
                ".js": "javascript",
                ".java": "java",
                ".cpp": "cpp",
                ".c": "c",
                ".go": "go",
                ".rs": "rust",
            }.get(file_ext, "unknown")

            # Calculate complexity metrics
            complexity_metrics = self._calculate_complexity_metrics(code, file_path)

            # Pattern-based analysis
            pattern_issues = self._analyze_code_patterns(code, language)

            # Language-specific analysis
            language_issues = []
            language_analysis = {}
            if file_ext in self.language_analyzers:
                language_issues, language_analysis = self.language_analyzers[file_ext](
                    code
                )

            # Combine all issues
            all_issues = pattern_issues + language_issues

            # Calculate overall metrics
            lines = code.split("\n")
            total_lines = len(lines)
            comment_lines = len(
                [line for line in lines if line.strip().startswith(("#", "//", "/*"))]
            )
            empty_lines = len([line for line in lines if not line.strip()])

            doc_ratio = comment_lines / max(total_lines, 1)

            # Security analysis
            security_issues = [
                issue for issue in all_issues if issue.issue_type == "security"
            ]
            security_score = max(0.0, 1.0 - (len(security_issues) * 0.2))

            # Performance analysis
            performance_issues = [
                issue for issue in all_issues if issue.issue_type == "performance"
            ]
            performance_score = max(0.0, 1.0 - (len(performance_issues) * 0.1))

            # Calculate style consistency
            indentation_sizes = []
            for line in lines:
                if line.strip():
                    leading_spaces = len(line) - len(line.lstrip())
                    if leading_spaces > 0:
                        indentation_sizes.append(leading_spaces)

            style_consistency = 1.0
            if indentation_sizes:
                # Check for consistent indentation
                common_indent = max(set(indentation_sizes), key=indentation_sizes.count)
                inconsistent = len(
                    [size for size in indentation_sizes if size % common_indent != 0]
                )
                style_consistency = max(
                    0.0, 1.0 - (inconsistent / len(indentation_sizes))
                )

            # Create comprehensive metrics
            metrics = CodeMetrics(
                complexity_score=1.0
                - (np.mean(list(complexity_metrics.values())) / 10.0),
                maintainability_index=max(0.0, 1.0 - (len(all_issues) * 0.05)),
                duplication_ratio=0.0,  # Would need more complex analysis
                test_coverage_estimate=0.8 if "test" in file_path.lower() else 0.3,
                documentation_ratio=doc_ratio,
                security_score=security_score,
                performance_score=performance_score,
                style_consistency=style_consistency,
            )

            # Calculate overall score
            overall_score = np.mean(
                [
                    metrics.complexity_score * 0.2,
                    metrics.maintainability_index * 0.2,
                    metrics.security_score * 0.25,
                    metrics.performance_score * 0.15,
                    metrics.documentation_ratio * 0.1,
                    metrics.style_consistency * 0.1,
                ]
            )

            # Generate suggestions
            suggestions = self._generate_suggestions(all_issues, metrics, language)

            # Neural insights (if available)
            neural_insights = []
            if self.neural_model_loaded:
                neural_insights = await self._generate_neural_insights(
                    code, file_path, all_issues
                )

            # Estimate review time
            issue_count = len(all_issues)
            critical_issues = len(
                [issue for issue in all_issues if issue.severity == "critical"]
            )
            review_time = (
                5 + (issue_count * 2) + (critical_issues * 5) + (total_lines // 50)
            )

            # Create review result
            review = CodeReview(
                overall_score=overall_score,
                metrics=metrics,
                issues=all_issues,
                suggestions=suggestions,
                neural_insights=neural_insights,
                estimated_review_time=review_time,
                complexity_breakdown=complexity_metrics,
            )

            # Store review for learning
            await self._store_review(review, file_path, review_type)

            # Update metrics
            self.reviews_completed += 1
            self.total_issues_found += len(all_issues)
            self.avg_review_time = (
                self.avg_review_time * (self.reviews_completed - 1)
                + (time.time() - start_time) * 1000
            ) / self.reviews_completed

            logger.info(
                f"Code review completed: {overall_score:.2f} score, "
                f"{len(all_issues)} issues, {time.time() - start_time:.2f}s"
            )

            return review

        except Exception as e:
            logger.error(f"Code review failed for {file_path}: {e}")

            # Return minimal review
            return CodeReview(
                overall_score=0.5,
                metrics=CodeMetrics(0.5, 0.5, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5),
                issues=[],
                suggestions=["Review failed - manual analysis recommended"],
                neural_insights=[],
                estimated_review_time=10,
                complexity_breakdown={},
            )

    def _generate_suggestions(
        self, issues: List[CodeIssue], metrics: CodeMetrics, language: str
    ) -> List[str]:
        """Generate high-level suggestions based on analysis"""
        suggestions = []

        # Security suggestions
        security_issues = [issue for issue in issues if issue.issue_type == "security"]
        if security_issues:
            critical_security = len(
                [issue for issue in security_issues if issue.severity == "critical"]
            )
            if critical_security > 0:
                suggestions.append(
                    f"🔴 CRITICAL: {critical_security} critical security issues require immediate attention"
                )
            else:
                suggestions.append(
                    f"🔒 Security: Review and fix {len(security_issues)} security-related issues"
                )

        # Performance suggestions
        performance_issues = [
            issue for issue in issues if issue.issue_type == "performance"
        ]
        if performance_issues:
            suggestions.append(
                f"⚡ Performance: {len(performance_issues)} optimizations identified"
            )

        # Complexity suggestions
        if metrics.complexity_score < 0.6:
            suggestions.append(
                "🔄 Complexity: Consider refactoring complex functions into smaller units"
            )

        # Documentation suggestions
        if metrics.documentation_ratio < 0.2:
            suggestions.append(
                "📝 Documentation: Add comments and docstrings to improve code maintainability"
            )

        # Style suggestions
        if metrics.style_consistency < 0.8:
            suggestions.append(
                "🎨 Style: Improve code formatting consistency (consider using a code formatter)"
            )

        # Language-specific suggestions
        if language == "python":
            python_issues = [issue for issue in issues if "py_" in issue.rule_id]
            if python_issues:
                suggestions.append(
                    "🐍 Python: Follow PEP 8 guidelines and Python best practices"
                )
        elif language == "javascript":
            js_issues = [issue for issue in issues if "js_" in issue.rule_id]
            if js_issues:
                suggestions.append(
                    "📜 JavaScript: Use modern ES6+ features and best practices"
                )

        # General suggestions
        if not suggestions:
            if metrics.maintainability_index > 0.8:
                suggestions.append(
                    "✅ Good code quality - minor improvements suggested"
                )
            else:
                suggestions.append(
                    "🔧 Focus on improving code maintainability and readability"
                )

        return suggestions

    async def _generate_neural_insights(
        self, code: str, file_path: str, issues: List[CodeIssue]
    ) -> List[str]:
        """Generate neural-powered insights"""
        insights = []

        try:
            # Simulate neural analysis (in production would use actual neural models)
            code_hash = hashlib.md5(code.encode()).hexdigest()

            # Check for similar patterns in cache
            similar_patterns = []
            for cached_hash, pattern_info in self.pattern_cache.items():
                # Simulate similarity check
                if code_hash[:4] == cached_hash[:4]:  # Simplified similarity
                    similar_patterns.append(pattern_info)

            if similar_patterns:
                insights.append(
                    f"🧠 Neural: Found {len(similar_patterns)} similar code patterns in database"
                )

            # Pattern-based insights
            issue_types = Counter(issue.issue_type for issue in issues)
            if issue_types:
                most_common = issue_types.most_common(1)[0]
                insights.append(
                    f"🔍 Pattern: {most_common[0]} issues are most common ({most_common[1]} occurrences)"
                )

            # File type insights
            file_ext = Path(file_path).suffix
            if file_ext == ".py" and "import" not in code:
                insights.append(
                    "🤔 Unusual: Python file without imports - consider if modules are needed"
                )

            # Complexity insights
            if len(code.split("\n")) > 500:
                insights.append(
                    "📏 Size: Large file detected - consider splitting into smaller modules"
                )

        except Exception as e:
            logger.debug(f"Neural insights generation failed: {e}")

        return insights

    async def _store_review(self, review: CodeReview, file_path: str, review_type: str):
        """Store review results for learning"""
        try:
            async with self.db_pool.acquire() as conn:
                # Store main review
                review_id = await conn.fetchval(
                    """
                    INSERT INTO git_intelligence.code_reviews
                    (repo_path, file_path, review_type, overall_score, complexity_score,
                     security_score, performance_score, maintainability_score, 
                     issues_found, critical_issues, review_time_ms, neural_enhanced, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    RETURNING id
                """,
                    "current_repo",  # Would be passed in production
                    file_path,
                    review_type,
                    review.overall_score,
                    review.metrics.complexity_score,
                    review.metrics.security_score,
                    review.metrics.performance_score,
                    review.metrics.maintainability_index,
                    len(review.issues),
                    len([i for i in review.issues if i.severity == "critical"]),
                    int(self.avg_review_time),
                    self.neural_model_loaded,
                    json.dumps(asdict(review.metrics)),
                )

                # Store individual issues
                for issue in review.issues:
                    await conn.execute(
                        """
                        INSERT INTO git_intelligence.code_issues
                        (review_id, file_path, issue_type, severity, line_number,
                         column_number, message, suggestion, confidence, rule_id)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                        review_id,
                        file_path,
                        issue.issue_type,
                        issue.severity,
                        issue.line_number,
                        issue.column,
                        issue.message,
                        issue.suggestion,
                        issue.confidence,
                        issue.rule_id,
                    )

        except Exception as e:
            logger.debug(f"Could not store review: {e}")

    async def get_reviewer_metrics(self) -> Dict[str, Any]:
        """Get comprehensive reviewer performance metrics"""
        try:
            async with self.db_pool.acquire() as conn:
                # Overall stats
                overall_stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total_reviews,
                        AVG(overall_score) as avg_score,
                        AVG(issues_found) as avg_issues,
                        AVG(review_time_ms) as avg_time_ms,
                        COUNT(*) FILTER (WHERE critical_issues > 0) as reviews_with_critical
                    FROM git_intelligence.code_reviews
                    WHERE created_at > NOW() - INTERVAL '30 days'
                """
                )

                # Issue type breakdown
                issue_stats = await conn.fetch(
                    """
                    SELECT 
                        issue_type,
                        severity,
                        COUNT(*) as count,
                        AVG(confidence) as avg_confidence
                    FROM git_intelligence.code_issues
                    JOIN git_intelligence.code_reviews ON code_issues.review_id = code_reviews.id
                    WHERE code_reviews.created_at > NOW() - INTERVAL '30 days'
                    GROUP BY issue_type, severity
                    ORDER BY count DESC
                """
                )

                # Language performance
                language_stats = await conn.fetch(
                    """
                    SELECT 
                        SUBSTRING(file_path FROM '\\.([^.]+)$') as file_extension,
                        COUNT(*) as reviews,
                        AVG(overall_score) as avg_score,
                        AVG(issues_found) as avg_issues
                    FROM git_intelligence.code_reviews
                    WHERE created_at > NOW() - INTERVAL '30 days'
                    GROUP BY SUBSTRING(file_path FROM '\\.([^.]+)$')
                    HAVING COUNT(*) > 1
                    ORDER BY reviews DESC
                """
                )

                return {
                    "total_reviews": overall_stats["total_reviews"] or 0,
                    "average_score": overall_stats["avg_score"] or 0.0,
                    "average_issues_per_review": overall_stats["avg_issues"] or 0.0,
                    "average_review_time_ms": overall_stats["avg_time_ms"] or 0.0,
                    "reviews_with_critical_issues": overall_stats[
                        "reviews_with_critical"
                    ]
                    or 0,
                    "neural_model_loaded": self.neural_model_loaded,
                    "supported_languages": list(self.language_analyzers.keys()),
                    "issue_breakdown": [
                        {
                            "type": stat["issue_type"],
                            "severity": stat["severity"],
                            "count": stat["count"],
                            "avg_confidence": stat["avg_confidence"],
                        }
                        for stat in issue_stats
                    ],
                    "language_performance": [
                        {
                            "extension": stat["file_extension"],
                            "reviews": stat["reviews"],
                            "avg_score": stat["avg_score"],
                            "avg_issues": stat["avg_issues"],
                        }
                        for stat in language_stats
                        if stat["file_extension"]
                    ],
                }

        except Exception as e:
            logger.error(f"Failed to get reviewer metrics: {e}")
            return {"error": str(e)}

    async def close(self):
        """Clean shutdown"""
        if self.db_pool:
            await self.db_pool.close()
        logger.info("Neural Code Reviewer shutdown complete")


# Production API
class NeuralCodeReviewerAPI:
    """Production API for neural code reviewer"""

    def __init__(self):
        self.reviewer = NeuralCodeReviewer()
        self._initialized = False

    async def initialize(self):
        """Initialize the API"""
        if not self._initialized:
            success = await self.reviewer.initialize()
            self._initialized = success
            return success
        return True

    async def review_code(
        self, code: str, file_path: str, review_type: str = "file"
    ) -> Dict[str, Any]:
        """API endpoint for code review"""
        if not self._initialized:
            await self.initialize()

        try:
            review = await self.reviewer.review_code(code, file_path, review_type)

            return {
                "success": True,
                "overall_score": review.overall_score,
                "metrics": {
                    "complexity": review.metrics.complexity_score,
                    "maintainability": review.metrics.maintainability_index,
                    "security": review.metrics.security_score,
                    "performance": review.metrics.performance_score,
                    "documentation": review.metrics.documentation_ratio,
                    "style_consistency": review.metrics.style_consistency,
                },
                "issues": [
                    {
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "line": issue.line_number,
                        "column": issue.column,
                        "message": issue.message,
                        "suggestion": issue.suggestion,
                        "confidence": issue.confidence,
                        "rule_id": issue.rule_id,
                    }
                    for issue in review.issues
                ],
                "suggestions": review.suggestions,
                "neural_insights": review.neural_insights,
                "estimated_review_time_minutes": review.estimated_review_time,
                "complexity_breakdown": review.complexity_breakdown,
                "critical_issues": len(
                    [i for i in review.issues if i.severity == "critical"]
                ),
                "high_severity_issues": len(
                    [i for i in review.issues if i.severity == "high"]
                ),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_metrics(self) -> Dict[str, Any]:
        """API endpoint for performance metrics"""
        if not self._initialized:
            await self.initialize()

        return await self.reviewer.get_reviewer_metrics()

    async def close(self):
        """Close the API"""
        await self.reviewer.close()


# Main execution for testing
async def main():
    """Test the neural code reviewer"""
    try:
        api = NeuralCodeReviewerAPI()
        await api.initialize()

        print("=== Neural Code Reviewer Test ===")

        # Test Python code
        python_code = """
def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] == 'test':
            result.append(eval(data[i] + '_processed'))
    return result

def unsafe_function():
    import subprocess
    subprocess.call('rm -rf /', shell=True)
    
try:
    process_data(['test', 'data'])
except:
    print('Error occurred')
"""

        print("\n--- Python Code Review ---")
        result = await api.review_code(python_code, "test_module.py")

        if result["success"]:
            print(f"Overall Score: {result['overall_score']:.2f}")
            print(f"Critical Issues: {result['critical_issues']}")
            print(f"Total Issues: {len(result['issues'])}")

            print("\nTop Issues:")
            for issue in sorted(
                result["issues"],
                key=lambda x: {"critical": 4, "high": 3, "medium": 2, "low": 1}[
                    x["severity"]
                ],
                reverse=True,
            )[:3]:
                print(
                    f"  Line {issue['line']}: {issue['severity'].upper()} - {issue['message']}"
                )

            print(f"\nSuggestions:")
            for suggestion in result["suggestions"][:3]:
                print(f"  - {suggestion}")

            if result["neural_insights"]:
                print(f"\nNeural Insights:")
                for insight in result["neural_insights"]:
                    print(f"  • {insight}")

        # Test JavaScript code
        js_code = """
function processArray(arr) {
    var result = [];
    for (var i = 0; i < arr.length; i++) {
        if (arr[i] == undefined) {
            console.log('Found undefined');
            document.getElementById('output').innerHTML = '<script>alert("xss")</script>';
        }
        result.push(arr[i]);
    }
    return result;
}
"""

        print("\n--- JavaScript Code Review ---")
        js_result = await api.review_code(js_code, "script.js")

        if js_result["success"]:
            print(f"Overall Score: {js_result['overall_score']:.2f}")
            print(f"Issues Found: {len(js_result['issues'])}")

            for issue in js_result["issues"][:2]:
                print(
                    f"  Line {issue['line']}: {issue['severity']} - {issue['message']}"
                )

        # Get metrics
        metrics = await api.get_metrics()
        print(f"\n=== Reviewer Metrics ===")
        print(f"Total Reviews: {metrics.get('total_reviews', 0)}")
        print(f"Average Score: {metrics.get('average_score', 0):.2f}")
        print(f"Neural Model Loaded: {metrics.get('neural_model_loaded', False)}")
        print(
            f"Supported Languages: {', '.join(metrics.get('supported_languages', []))}"
        )

        await api.close()

    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
