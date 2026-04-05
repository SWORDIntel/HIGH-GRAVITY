#!/usr/bin/env python3
"""
Conflict Predictor - Advanced ML-powered Git Conflict Prediction
Team Echo Implementation

95% accuracy target for merge conflict prediction using:
- Historical pattern analysis
- Neural embeddings with pgvector
- AVX2-accelerated diff analysis via Shadowgit
- OpenVINO neural inference
"""

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

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import Shadowgit AVX2 for high-speed diff analysis with updated path
try:
    from agent_path_resolver import get_shadowgit_root

    shadowgit_root = get_shadowgit_root()
    shadowgit_python = shadowgit_root / "python"
    if shadowgit_python.exists():
        sys.path.insert(0, str(shadowgit_python))
except ImportError:
    # Fallback to new location
    shadowgit_root = project_root.parent / "hooks" / "shadowgit"
    shadowgit_python = shadowgit_root / "python"
    if shadowgit_python.exists():
        sys.path.insert(0, str(shadowgit_python))

try:
    # shadowgit_avx2 module not found in current repo - may need to be created or imported differently
    # Commenting out for now to prevent import errors
    # from shadowgit_avx2 import ShadowgitAVX2
    SHADOWGIT_AVAILABLE = False
    logging.info("Shadowgit AVX2 module not yet available in new structure")
except ImportError:
    logging.warning("Shadowgit AVX2 not available, using fallback diff analysis")
    SHADOWGIT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConflictFeatures:
    """Features extracted for conflict prediction ML model"""

    file_path: str
    file_extension: str
    file_size: int
    lines_changed_target: int
    lines_changed_source: int
    overlap_ratio: float
    author_conflict_history: float
    file_conflict_history: float
    change_complexity: float
    temporal_distance: float
    semantic_similarity: float


@dataclass
class ConflictPredictionResult:
    """Comprehensive conflict prediction result"""

    file_path: str
    conflict_probability: float
    confidence_score: float
    prediction_method: str
    features_used: List[str]
    historical_accuracy: float
    neural_enhanced: bool
    resolution_suggestion: str
    affected_line_ranges: List[Tuple[int, int]]
    estimated_resolution_time: int  # seconds


class AdvancedConflictPredictor:
    """Advanced ML-powered conflict predictor with 95% accuracy target"""

    def __init__(self, database_url: str = None):
        self.db_url = (
            database_url
            or "postgresql://claude_agent:claude_secure_password@localhost:5433/claude_agents_auth"
        )
        self.db_pool = None

        # ML model components
        self.feature_weights = {
            "overlap_ratio": 0.25,
            "author_history": 0.20,
            "file_history": 0.20,
            "complexity": 0.15,
            "temporal": 0.10,
            "semantic": 0.10,
        }

        # Historical data caches
        self.author_conflict_rates = {}
        self.file_conflict_patterns = defaultdict(list)
        self.resolution_patterns = {}

        # Neural components
        self.neural_embeddings_cache = {}
        self.neural_model_loaded = False

        # Performance metrics
        self.prediction_accuracy = 0.0
        self.total_predictions = 0
        self.correct_predictions = 0

        # Shadowgit integration
        self.shadowgit = None
        if SHADOWGIT_AVAILABLE:
            try:
                self.shadowgit = ShadowgitAVX2()
                logger.info("Shadowgit AVX2 integration enabled")
            except Exception as e:
                logger.warning(f"Shadowgit AVX2 initialization failed: {e}")

    async def initialize(self):
        """Initialize the conflict predictor"""
        try:
            # Database connection
            self.db_pool = await asyncpg.create_pool(
                self.db_url, min_size=2, max_size=8, command_timeout=30
            )

            # Ensure schema
            await self._ensure_conflict_schema()

            # Load historical data
            await self._load_historical_patterns()

            # Initialize neural components
            await self._initialize_neural_model()

            logger.info("Advanced Conflict Predictor initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize conflict predictor: {e}")
            return False

    async def _ensure_conflict_schema(self):
        """Ensure conflict prediction schema exists"""
        async with self.db_pool.acquire() as conn:
            # Conflict prediction results
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS git_intelligence.conflict_predictions (
                    id SERIAL PRIMARY KEY,
                    repo_path TEXT NOT NULL,
                    target_branch TEXT NOT NULL,
                    source_branch TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    predicted_probability FLOAT NOT NULL,
                    confidence_score FLOAT NOT NULL,
                    prediction_method TEXT NOT NULL,
                    features_json JSONB,
                    actual_conflict BOOLEAN,
                    prediction_accuracy FLOAT,
                    resolution_time_seconds INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    validated_at TIMESTAMP WITH TIME ZONE
                )
            """
            )

            # Conflict features for ML training
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS git_intelligence.conflict_features (
                    id SERIAL PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    feature_vector vector(128),
                    conflict_occurred BOOLEAN NOT NULL,
                    resolution_strategy TEXT,
                    metadata JSONB,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            )

            # Author conflict patterns
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS git_intelligence.author_patterns (
                    author_email TEXT PRIMARY KEY,
                    total_merges INTEGER DEFAULT 0,
                    conflicts_caused INTEGER DEFAULT 0,
                    conflict_rate FLOAT DEFAULT 0.0,
                    files_frequently_modified TEXT[],
                    avg_resolution_time INTEGER DEFAULT 0,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            )

            # Create indexes for performance
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conflict_predictions_branches 
                ON git_intelligence.conflict_predictions(target_branch, source_branch);
                CREATE INDEX IF NOT EXISTS idx_conflict_features_vector 
                ON git_intelligence.conflict_features USING ivfflat (feature_vector vector_cosine_ops);
            """
            )

    async def _load_historical_patterns(self):
        """Load historical conflict patterns for ML model"""
        try:
            async with self.db_pool.acquire() as conn:
                # Load author conflict rates
                authors = await conn.fetch(
                    """
                    SELECT author_email, conflict_rate, files_frequently_modified
                    FROM git_intelligence.author_patterns
                """
                )

                for author in authors:
                    self.author_conflict_rates[author["author_email"]] = {
                        "rate": author["conflict_rate"] or 0.0,
                        "files": author["files_frequently_modified"] or [],
                    }

                # Load file conflict patterns
                patterns = await conn.fetch(
                    """
                    SELECT file_path, frequency, resolution_strategy, success_rate
                    FROM git_intelligence.conflict_patterns
                    WHERE frequency > 1
                """
                )

                for pattern in patterns:
                    self.file_conflict_patterns[pattern["file_path"]].append(
                        {
                            "frequency": pattern["frequency"],
                            "strategy": pattern["resolution_strategy"],
                            "success_rate": pattern["success_rate"] or 0.0,
                        }
                    )

                # Load resolution patterns
                resolutions = await conn.fetch(
                    """
                    SELECT DISTINCT resolution_strategy, AVG(prediction_accuracy) as accuracy
                    FROM git_intelligence.conflict_predictions
                    WHERE actual_conflict IS NOT NULL
                    GROUP BY resolution_strategy
                """
                )

                for res in resolutions:
                    self.resolution_patterns[res["resolution_strategy"]] = (
                        res["accuracy"] or 0.0
                    )

                logger.info(
                    f"Loaded patterns: {len(self.author_conflict_rates)} authors, "
                    f"{len(self.file_conflict_patterns)} files, "
                    f"{len(self.resolution_patterns)} resolution strategies"
                )

        except Exception as e:
            logger.warning(f"Could not load historical patterns: {e}")

    async def _initialize_neural_model(self):
        """Initialize neural components for enhanced prediction"""
        try:
            # Check for OpenVINO availability
            openvino_path = Path("${OPENVINO_ROOT:-/opt/openvino/}")
            if openvino_path.exists():
                # Initialize neural embedding model
                await self._setup_neural_embeddings()
                self.neural_model_loaded = True
                logger.info("Neural model components loaded")
            else:
                logger.info(
                    "Neural acceleration not available, using statistical model"
                )

        except Exception as e:
            logger.warning(f"Neural model initialization failed: {e}")

    async def _setup_neural_embeddings(self):
        """Setup neural embeddings for semantic similarity analysis"""
        try:
            # Load cached embeddings
            async with self.db_pool.acquire() as conn:
                embeddings = await conn.fetch(
                    """
                    SELECT file_path, embedding, content_hash
                    FROM git_intelligence.code_embeddings
                    WHERE timestamp > NOW() - INTERVAL '7 days'
                """
                )

                for emb in embeddings:
                    if emb["embedding"]:
                        self.neural_embeddings_cache[emb["file_path"]] = {
                            "vector": np.array(emb["embedding"]),
                            "hash": emb["content_hash"],
                        }

                logger.info(f"Loaded {len(embeddings)} neural embeddings from cache")

        except Exception as e:
            logger.debug(f"Could not load neural embeddings: {e}")

    def _extract_conflict_features(
        self,
        file_path: str,
        target_changes: Dict,
        source_changes: Dict,
        authors: List[str],
        repo_context: Dict,
    ) -> ConflictFeatures:
        """Extract comprehensive features for ML prediction"""
        try:
            # Basic file information
            file_size = repo_context.get("file_size", 0)
            file_ext = Path(file_path).suffix.lower()

            # Change analysis
            target_lines = target_changes.get("lines_changed", 0)
            source_lines = source_changes.get("lines_changed", 0)

            # Calculate overlap ratio
            target_ranges = target_changes.get("line_ranges", [])
            source_ranges = source_changes.get("line_ranges", [])
            overlap_ratio = self._calculate_line_overlap(target_ranges, source_ranges)

            # Author conflict history
            author_history = 0.0
            if authors:
                author_rates = [
                    self.author_conflict_rates.get(author, {}).get("rate", 0.0)
                    for author in authors
                ]
                author_history = np.mean(author_rates) if author_rates else 0.0

            # File conflict history
            file_history = 0.0
            if file_path in self.file_conflict_patterns:
                patterns = self.file_conflict_patterns[file_path]
                frequencies = [p["frequency"] for p in patterns]
                file_history = (
                    min(1.0, np.mean(frequencies) / 10.0) if frequencies else 0.0
                )

            # Change complexity
            complexity = self._calculate_change_complexity(
                target_changes, source_changes
            )

            # Temporal distance (how recent are the changes)
            temporal = self._calculate_temporal_distance(
                target_changes.get("timestamp"), source_changes.get("timestamp")
            )

            # Semantic similarity (if neural model available)
            semantic = 0.5  # Default neutral
            if self.neural_model_loaded and file_path in self.neural_embeddings_cache:
                semantic = self._calculate_semantic_similarity(
                    file_path, target_changes, source_changes
                )

            return ConflictFeatures(
                file_path=file_path,
                file_extension=file_ext,
                file_size=file_size,
                lines_changed_target=target_lines,
                lines_changed_source=source_lines,
                overlap_ratio=overlap_ratio,
                author_conflict_history=author_history,
                file_conflict_history=file_history,
                change_complexity=complexity,
                temporal_distance=temporal,
                semantic_similarity=semantic,
            )

        except Exception as e:
            logger.debug(f"Error extracting features for {file_path}: {e}")
            # Return default features
            return ConflictFeatures(
                file_path=file_path,
                file_extension=Path(file_path).suffix.lower(),
                file_size=0,
                lines_changed_target=0,
                lines_changed_source=0,
                overlap_ratio=0.0,
                author_conflict_history=0.0,
                file_conflict_history=0.0,
                change_complexity=0.0,
                temporal_distance=0.0,
                semantic_similarity=0.5,
            )

    def _calculate_line_overlap(
        self, target_ranges: List[Tuple[int, int]], source_ranges: List[Tuple[int, int]]
    ) -> float:
        """Calculate the overlap ratio between changed line ranges"""
        if not target_ranges or not source_ranges:
            return 0.0

        try:
            target_lines = set()
            source_lines = set()

            for start, end in target_ranges:
                target_lines.update(range(start, end + 1))

            for start, end in source_ranges:
                source_lines.update(range(start, end + 1))

            if not target_lines or not source_lines:
                return 0.0

            overlap = len(target_lines & source_lines)
            total = len(target_lines | source_lines)

            return overlap / total if total > 0 else 0.0

        except Exception:
            return 0.0

    def _calculate_change_complexity(
        self, target_changes: Dict, source_changes: Dict
    ) -> float:
        """Calculate the complexity of changes"""
        try:
            # Factors contributing to complexity
            factors = []

            # Number of lines changed
            target_lines = target_changes.get("lines_changed", 0)
            source_lines = source_changes.get("lines_changed", 0)
            total_lines = target_lines + source_lines
            factors.append(min(1.0, total_lines / 100.0))

            # Type of changes
            target_type = target_changes.get("change_type", "M")
            source_type = source_changes.get("change_type", "M")

            # Deletions and additions are more complex than modifications
            type_complexity = 0.0
            if target_type in ["D", "A"] or source_type in ["D", "A"]:
                type_complexity = 0.3
            factors.append(type_complexity)

            # Number of functions/classes affected (heuristic)
            target_functions = target_changes.get("functions_affected", 0)
            source_functions = source_changes.get("functions_affected", 0)
            function_complexity = min(0.4, (target_functions + source_functions) / 10.0)
            factors.append(function_complexity)

            return min(1.0, np.mean(factors))

        except Exception:
            return 0.5  # Default medium complexity

    def _calculate_temporal_distance(
        self, target_time: Optional[datetime], source_time: Optional[datetime]
    ) -> float:
        """Calculate temporal distance factor (recent changes more likely to conflict)"""
        try:
            if not target_time or not source_time:
                return 0.5

            # Time difference in hours
            time_diff = abs((target_time - source_time).total_seconds()) / 3600.0

            # Inverse relationship: closer in time = higher conflict probability
            if time_diff < 1:  # Within 1 hour
                return 0.9
            elif time_diff < 24:  # Within 1 day
                return 0.7
            elif time_diff < 168:  # Within 1 week
                return 0.5
            else:
                return 0.2

        except Exception:
            return 0.5

    def _calculate_semantic_similarity(
        self, file_path: str, target_changes: Dict, source_changes: Dict
    ) -> float:
        """Calculate semantic similarity using neural embeddings"""
        try:
            if file_path not in self.neural_embeddings_cache:
                return 0.5

            # Get cached embedding
            cached = self.neural_embeddings_cache[file_path]
            base_vector = cached["vector"]

            # For now, use simplified similarity based on change patterns
            # In production, this would analyze actual code content
            target_patterns = target_changes.get("code_patterns", [])
            source_patterns = source_changes.get("code_patterns", [])

            if not target_patterns or not source_patterns:
                return 0.5

            # Calculate pattern overlap
            common_patterns = set(target_patterns) & set(source_patterns)
            total_patterns = set(target_patterns) | set(source_patterns)

            similarity = (
                len(common_patterns) / len(total_patterns) if total_patterns else 0.0
            )
            return similarity

        except Exception:
            return 0.5

    async def predict_conflict_advanced(
        self,
        file_path: str,
        target_changes: Dict,
        source_changes: Dict,
        authors: List[str],
        repo_context: Dict,
    ) -> ConflictPredictionResult:
        """Advanced conflict prediction with comprehensive feature analysis"""
        try:
            start_time = time.time()

            # Extract features
            features = self._extract_conflict_features(
                file_path, target_changes, source_changes, authors, repo_context
            )

            # Calculate base probability using weighted features
            probability_components = {
                "overlap": features.overlap_ratio
                * self.feature_weights["overlap_ratio"],
                "author_history": features.author_conflict_history
                * self.feature_weights["author_history"],
                "file_history": features.file_conflict_history
                * self.feature_weights["file_history"],
                "complexity": features.change_complexity
                * self.feature_weights["complexity"],
                "temporal": features.temporal_distance
                * self.feature_weights["temporal"],
                "semantic": features.semantic_similarity
                * self.feature_weights["semantic"],
            }

            base_probability = sum(probability_components.values())

            # File type adjustments
            file_type_multipliers = {
                ".py": 1.1,
                ".js": 1.1,
                ".java": 1.0,
                ".cpp": 1.2,
                ".c": 1.2,
                ".h": 1.2,
                ".json": 0.8,
                ".md": 0.6,
                ".txt": 0.5,
                ".yml": 0.7,
                ".yaml": 0.7,
            }

            multiplier = file_type_multipliers.get(features.file_extension, 1.0)
            adjusted_probability = min(0.98, base_probability * multiplier)

            # Confidence calculation
            confidence_factors = []

            # Historical accuracy for similar patterns
            if file_path in self.file_conflict_patterns:
                patterns = self.file_conflict_patterns[file_path]
                if patterns:
                    avg_accuracy = np.mean(
                        [p.get("success_rate", 0.5) for p in patterns]
                    )
                    confidence_factors.append(avg_accuracy)

            # Feature reliability
            feature_reliability = 1.0 - abs(
                0.5 - features.overlap_ratio
            )  # Extreme values more reliable
            confidence_factors.append(feature_reliability)

            # Neural enhancement confidence
            if self.neural_model_loaded:
                neural_confidence = 0.9
                confidence_factors.append(neural_confidence)

            confidence = np.mean(confidence_factors) if confidence_factors else 0.7
            confidence = max(0.5, min(0.98, confidence))

            # Determine prediction method
            methods_used = ["statistical_features"]
            if features.overlap_ratio > 0:
                methods_used.append("line_overlap_analysis")
            if features.author_conflict_history > 0:
                methods_used.append("author_pattern_matching")
            if self.neural_model_loaded:
                methods_used.append("neural_enhancement")
            if self.shadowgit:
                methods_used.append("avx2_diff_acceleration")

            prediction_method = " + ".join(methods_used)

            # Generate resolution suggestion
            resolution_suggestion = self._generate_resolution_suggestion(
                features, adjusted_probability, repo_context
            )

            # Estimate affected line ranges (simplified)
            affected_ranges = self._estimate_affected_ranges(
                target_changes, source_changes
            )

            # Estimate resolution time
            resolution_time = self._estimate_resolution_time(
                features, adjusted_probability
            )

            # Create result
            result = ConflictPredictionResult(
                file_path=file_path,
                conflict_probability=adjusted_probability,
                confidence_score=confidence,
                prediction_method=prediction_method,
                features_used=list(probability_components.keys()),
                historical_accuracy=self.prediction_accuracy,
                neural_enhanced=self.neural_model_loaded,
                resolution_suggestion=resolution_suggestion,
                affected_line_ranges=affected_ranges,
                estimated_resolution_time=resolution_time,
            )

            # Store prediction for learning
            await self._store_prediction(result, features)

            inference_time = (time.time() - start_time) * 1000
            logger.debug(
                f"Advanced prediction for {file_path}: {adjusted_probability:.1%} "
                f"confidence {confidence:.1%} in {inference_time:.1f}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Advanced prediction failed for {file_path}: {e}")
            # Return fallback prediction
            return ConflictPredictionResult(
                file_path=file_path,
                conflict_probability=0.5,
                confidence_score=0.5,
                prediction_method="fallback",
                features_used=["default"],
                historical_accuracy=0.0,
                neural_enhanced=False,
                resolution_suggestion="Manual review recommended due to prediction failure",
                affected_line_ranges=[(1, 10)],
                estimated_resolution_time=300,
            )

    def _generate_resolution_suggestion(
        self, features: ConflictFeatures, probability: float, repo_context: Dict
    ) -> str:
        """Generate intelligent resolution suggestions"""
        try:
            suggestions = []

            # High probability conflicts
            if probability > 0.8:
                suggestions.append("High conflict probability detected.")
                if features.overlap_ratio > 0.6:
                    suggestions.append(
                        "Significant line overlap - consider manual merge with careful review."
                    )
                if features.author_conflict_history > 0.5:
                    suggestions.append(
                        "Author has history of conflicts - coordinate directly."
                    )

            # File-specific suggestions
            if features.file_extension in [".py", ".js", ".java"]:
                suggestions.append("Code file - run tests after resolution.")
            elif features.file_extension in [".json", ".yml", ".yaml"]:
                suggestions.append("Configuration file - validate syntax after merge.")

            # Complexity-based suggestions
            if features.change_complexity > 0.7:
                suggestions.append(
                    "Complex changes detected - consider splitting into smaller commits."
                )

            # Resolution strategy from patterns
            if features.file_path in self.file_conflict_patterns:
                patterns = self.file_conflict_patterns[features.file_path]
                successful_strategies = [
                    p["strategy"] for p in patterns if p.get("success_rate", 0) > 0.8
                ]
                if successful_strategies:
                    most_successful = Counter(successful_strategies).most_common(1)[0][
                        0
                    ]
                    suggestions.append(
                        f"Previously successful strategy: {most_successful}"
                    )

            # Default suggestion if no specific advice
            if not suggestions:
                if probability > 0.5:
                    suggestions.append(
                        "Review changes carefully and test thoroughly after merge."
                    )
                else:
                    suggestions.append(
                        "Low conflict probability - standard merge process recommended."
                    )

            return " ".join(suggestions)

        except Exception:
            return "Standard conflict resolution process recommended."

    def _estimate_affected_ranges(
        self, target_changes: Dict, source_changes: Dict
    ) -> List[Tuple[int, int]]:
        """Estimate line ranges that might be affected by conflicts"""
        try:
            ranges = []

            target_ranges = target_changes.get("line_ranges", [])
            source_ranges = source_changes.get("line_ranges", [])

            # Combine and merge overlapping ranges
            all_ranges = target_ranges + source_ranges
            if not all_ranges:
                return [(1, 10)]  # Default range

            # Sort ranges and merge overlapping ones
            all_ranges.sort()
            merged = [all_ranges[0]]

            for start, end in all_ranges[1:]:
                last_start, last_end = merged[-1]
                if start <= last_end + 1:  # Overlapping or adjacent
                    merged[-1] = (last_start, max(last_end, end))
                else:
                    merged.append((start, end))

            return merged[:5]  # Return up to 5 ranges

        except Exception:
            return [(1, 10)]

    def _estimate_resolution_time(
        self, features: ConflictFeatures, probability: float
    ) -> int:
        """Estimate time needed to resolve conflict in seconds"""
        try:
            # Base time estimation
            base_time = 180  # 3 minutes

            # Adjust based on probability
            if probability > 0.8:
                base_time *= 2.5
            elif probability > 0.6:
                base_time *= 2.0
            elif probability > 0.4:
                base_time *= 1.5

            # Complexity adjustments
            if features.change_complexity > 0.7:
                base_time *= 1.8
            elif features.change_complexity > 0.4:
                base_time *= 1.3

            # File size adjustment
            if features.file_size > 10000:  # Large files
                base_time *= 1.5
            elif features.file_size > 50000:  # Very large files
                base_time *= 2.0

            # File type adjustment
            complex_files = [".cpp", ".c", ".h", ".java"]
            if features.file_extension in complex_files:
                base_time *= 1.4

            return int(min(3600, max(60, base_time)))  # Between 1 minute and 1 hour

        except Exception:
            return 300  # Default 5 minutes

    async def _store_prediction(
        self, result: ConflictPredictionResult, features: ConflictFeatures
    ):
        """Store prediction for future learning and validation"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO git_intelligence.conflict_predictions
                    (repo_path, target_branch, source_branch, file_path, 
                     predicted_probability, confidence_score, prediction_method, features_json)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                    "current_repo",  # Would be passed in production
                    "target",
                    "source",
                    result.file_path,
                    result.conflict_probability,
                    result.confidence_score,
                    result.prediction_method,
                    json.dumps(asdict(features)),
                )

            self.total_predictions += 1

        except Exception as e:
            logger.debug(f"Could not store prediction: {e}")

    async def validate_prediction(
        self, file_path: str, actual_conflict: bool, resolution_time: int = None
    ):
        """Validate a previous prediction and update accuracy metrics"""
        try:
            async with self.db_pool.acquire() as conn:
                # Find the most recent prediction for this file
                prediction = await conn.fetchrow(
                    """
                    SELECT id, predicted_probability, confidence_score
                    FROM git_intelligence.conflict_predictions
                    WHERE file_path = $1 AND actual_conflict IS NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                """,
                    file_path,
                )

                if not prediction:
                    logger.debug(f"No prediction found for validation: {file_path}")
                    return

                # Calculate accuracy
                predicted_prob = prediction["predicted_probability"]

                # Binary accuracy (>0.5 predicted conflict)
                predicted_conflict = predicted_prob > 0.5
                correct_prediction = predicted_conflict == actual_conflict

                # Probabilistic accuracy (how close was the probability)
                if actual_conflict:
                    prob_accuracy = (
                        predicted_prob  # Higher is better for actual conflicts
                    )
                else:
                    prob_accuracy = (
                        1.0 - predicted_prob
                    )  # Lower is better for no conflicts

                # Update the prediction record
                await conn.execute(
                    """
                    UPDATE git_intelligence.conflict_predictions
                    SET actual_conflict = $2,
                        prediction_accuracy = $3,
                        resolution_time_seconds = $4,
                        validated_at = NOW()
                    WHERE id = $1
                """,
                    prediction["id"],
                    actual_conflict,
                    prob_accuracy,
                    resolution_time,
                )

                # Update global accuracy metrics
                if correct_prediction:
                    self.correct_predictions += 1

                if self.total_predictions > 0:
                    self.prediction_accuracy = (
                        self.correct_predictions / self.total_predictions
                    )

                logger.info(
                    f"Validated prediction for {file_path}: "
                    f"predicted={predicted_prob:.1%}, actual={actual_conflict}, "
                    f"accuracy={prob_accuracy:.1%}"
                )

        except Exception as e:
            logger.error(f"Failed to validate prediction: {e}")

    async def batch_predict_conflicts(
        self, file_changes: Dict[str, Dict], repo_context: Dict
    ) -> List[ConflictPredictionResult]:
        """Batch predict conflicts for multiple files efficiently"""
        try:
            if not file_changes:
                return []

            logger.info(
                f"Running batch conflict prediction for {len(file_changes)} files"
            )
            start_time = time.time()

            # Prepare batch processing
            tasks = []
            for file_path, changes in file_changes.items():
                target_changes = changes.get("target", {})
                source_changes = changes.get("source", {})
                authors = changes.get("authors", [])

                task = self.predict_conflict_advanced(
                    file_path, target_changes, source_changes, authors, repo_context
                )
                tasks.append(task)

            # Run predictions concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and log them
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    file_path = list(file_changes.keys())[i]
                    logger.warning(f"Prediction failed for {file_path}: {result}")
                else:
                    valid_results.append(result)

            # Sort by conflict probability
            valid_results.sort(key=lambda x: x.conflict_probability, reverse=True)

            total_time = time.time() - start_time
            logger.info(
                f"Batch prediction completed: {len(valid_results)} predictions "
                f"in {total_time:.2f}s ({total_time/len(file_changes):.3f}s per file)"
            )

            return valid_results

        except Exception as e:
            logger.error(f"Batch prediction failed: {e}")
            return []

    async def get_prediction_metrics(self) -> Dict[str, Any]:
        """Get comprehensive prediction performance metrics"""
        try:
            async with self.db_pool.acquire() as conn:
                # Overall accuracy metrics
                overall_stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total_predictions,
                        COUNT(*) FILTER (WHERE actual_conflict IS NOT NULL) as validated_predictions,
                        AVG(prediction_accuracy) as avg_accuracy,
                        AVG(confidence_score) as avg_confidence,
                        COUNT(*) FILTER (WHERE predicted_probability > 0.5 AND actual_conflict = true) as true_positives,
                        COUNT(*) FILTER (WHERE predicted_probability > 0.5 AND actual_conflict = false) as false_positives,
                        COUNT(*) FILTER (WHERE predicted_probability <= 0.5 AND actual_conflict = true) as false_negatives,
                        COUNT(*) FILTER (WHERE predicted_probability <= 0.5 AND actual_conflict = false) as true_negatives
                    FROM git_intelligence.conflict_predictions
                    WHERE created_at > NOW() - INTERVAL '30 days'
                """
                )

                # Method performance
                method_stats = await conn.fetch(
                    """
                    SELECT 
                        prediction_method,
                        COUNT(*) as predictions,
                        AVG(prediction_accuracy) as accuracy,
                        AVG(confidence_score) as confidence
                    FROM git_intelligence.conflict_predictions
                    WHERE actual_conflict IS NOT NULL
                    GROUP BY prediction_method
                    ORDER BY accuracy DESC
                """
                )

                # Calculate precision, recall, F1
                tp = overall_stats["true_positives"] or 0
                fp = overall_stats["false_positives"] or 0
                fn = overall_stats["false_negatives"] or 0
                tn = overall_stats["true_negatives"] or 0

                precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                f1_score = (
                    2 * (precision * recall) / (precision + recall)
                    if (precision + recall) > 0
                    else 0.0
                )

                return {
                    "total_predictions": overall_stats["total_predictions"] or 0,
                    "validated_predictions": overall_stats["validated_predictions"]
                    or 0,
                    "overall_accuracy": overall_stats["avg_accuracy"] or 0.0,
                    "average_confidence": overall_stats["avg_confidence"] or 0.0,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1_score,
                    "neural_enhanced": self.neural_model_loaded,
                    "avx2_acceleration": self.shadowgit is not None,
                    "method_performance": [
                        {
                            "method": method["prediction_method"],
                            "predictions": method["predictions"],
                            "accuracy": method["accuracy"],
                            "confidence": method["confidence"],
                        }
                        for method in method_stats
                    ],
                    "feature_weights": self.feature_weights,
                }

        except Exception as e:
            logger.error(f"Failed to get prediction metrics: {e}")
            return {"error": str(e)}

    async def close(self):
        """Clean shutdown of conflict predictor"""
        if self.db_pool:
            await self.db_pool.close()
        logger.info("Advanced Conflict Predictor shutdown complete")


# Production API
class ConflictPredictorAPI:
    """Production API for conflict prediction"""

    def __init__(self):
        self.predictor = AdvancedConflictPredictor()
        self._initialized = False

    async def initialize(self):
        """Initialize the API"""
        if not self._initialized:
            success = await self.predictor.initialize()
            self._initialized = success
            return success
        return True

    async def predict_conflicts(
        self, file_changes: Dict[str, Dict], repo_context: Dict = None
    ) -> Dict[str, Any]:
        """API endpoint for conflict prediction"""
        if not self._initialized:
            await self.initialize()

        try:
            repo_context = repo_context or {}
            results = await self.predictor.batch_predict_conflicts(
                file_changes, repo_context
            )

            return {
                "success": True,
                "total_files": len(file_changes),
                "predictions": [
                    {
                        "file_path": r.file_path,
                        "conflict_probability": r.conflict_probability,
                        "confidence_score": r.confidence_score,
                        "prediction_method": r.prediction_method,
                        "neural_enhanced": r.neural_enhanced,
                        "resolution_suggestion": r.resolution_suggestion,
                        "estimated_resolution_time": r.estimated_resolution_time,
                        "affected_ranges": r.affected_line_ranges,
                    }
                    for r in results
                ],
                "high_risk_count": len(
                    [r for r in results if r.conflict_probability > 0.7]
                ),
                "average_confidence": (
                    np.mean([r.confidence_score for r in results]) if results else 0.0
                ),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def validate_prediction(
        self, file_path: str, actual_conflict: bool, resolution_time: int = None
    ) -> Dict[str, Any]:
        """API endpoint for prediction validation"""
        if not self._initialized:
            await self.initialize()

        try:
            await self.predictor.validate_prediction(
                file_path, actual_conflict, resolution_time
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_metrics(self) -> Dict[str, Any]:
        """API endpoint for performance metrics"""
        if not self._initialized:
            await self.initialize()

        return await self.predictor.get_prediction_metrics()

    async def close(self):
        """Close the API"""
        await self.predictor.close()


# Main execution for testing
async def main():
    """Test the conflict predictor"""
    try:
        api = ConflictPredictorAPI()
        await api.initialize()

        print("=== Advanced Conflict Predictor Test ===")

        # Test data
        test_changes = {
            "src/main.py": {
                "target": {
                    "lines_changed": 25,
                    "change_type": "M",
                    "line_ranges": [(10, 20), (50, 60)],
                },
                "source": {
                    "lines_changed": 30,
                    "change_type": "M",
                    "line_ranges": [(15, 25), (55, 65)],
                },
                "authors": ["developer1@example.com", "developer2@example.com"],
            },
            os.path.join(os.environ.get("CLAUDE_AGENTS_ROOT", "."), "config", "$1"): {
                "target": {
                    "lines_changed": 5,
                    "change_type": "M",
                    "line_ranges": [(1, 5)],
                },
                "source": {
                    "lines_changed": 3,
                    "change_type": "M",
                    "line_ranges": [(2, 4)],
                },
                "authors": ["admin@example.com"],
            },
        }

        repo_context = {"file_size": 1000, "total_commits": 150}

        # Test prediction
        result = await api.predict_conflicts(test_changes, repo_context)

        if result["success"]:
            print(f"Analyzed {result['total_files']} files")
            print(f"High-risk conflicts: {result['high_risk_count']}")
            print(f"Average confidence: {result['average_confidence']:.1%}")

            for pred in result["predictions"]:
                print(f"\n{pred['file_path']}:")
                print(f"  Conflict probability: {pred['conflict_probability']:.1%}")
                print(f"  Confidence: {pred['confidence_score']:.1%}")
                print(f"  Method: {pred['prediction_method']}")
                print(f"  Resolution time: {pred['estimated_resolution_time']}s")
                print(f"  Suggestion: {pred['resolution_suggestion'][:100]}...")

        # Test validation
        validation = await api.validate_prediction("src/main.py", True, 450)
        print(f"\nValidation result: {validation}")

        # Get metrics
        metrics = await api.get_metrics()
        print(f"\n=== Performance Metrics ===")
        print(f"Total predictions: {metrics.get('total_predictions', 0)}")
        print(f"Overall accuracy: {metrics.get('overall_accuracy', 0):.1%}")
        print(f"F1 score: {metrics.get('f1_score', 0):.3f}")
        print(f"Neural enhanced: {metrics.get('neural_enhanced', False)}")
        print(f"AVX2 acceleration: {metrics.get('avx2_acceleration', False)}")

        await api.close()

    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
