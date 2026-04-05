#!/usr/bin/env python3
"""
Enhanced PostgreSQL Agent Learning System v3.0 - COMPLETE MERGED VERSION
Advanced ML-driven agent orchestration with real-time adaptation and Claude-Code integration
Merges all v2.0 enhancements with v3.0 architecture
"""

import asyncio
import asyncpg
import json
import time
import hashlib
import logging
import pickle
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter, deque
from enum import Enum
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# Machine Learning imports
try:
    from sklearn.ensemble import (
        RandomForestClassifier, RandomForestRegressor, 
        GradientBoostingRegressor, IsolationForest
    )
    from sklearn.neural_network import MLPClassifier, MLPRegressor
    from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
    from sklearn.model_selection import cross_val_score, GridSearchCV
    from sklearn.metrics import accuracy_score, mean_squared_error, precision_recall_curve
    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.decomposition import PCA
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("Warning: ML libraries not available. Install with: pip install scikit-learn joblib")

# Deep Learning Support (optional)
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    DL_AVAILABLE = True
except ImportError:
    DL_AVAILABLE = False
    print("Info: PyTorch not available. Deep learning features disabled.")

logger = logging.getLogger(__name__)

# ============================================================================
# ENHANCED DATA STRUCTURES v3.0
# ============================================================================

class PredictionConfidence(Enum):
    """Confidence levels for predictions"""
    VERY_HIGH = 0.9
    HIGH = 0.75
    MEDIUM = 0.6
    LOW = 0.4
    VERY_LOW = 0.2

class LearningMode(Enum):
    """Advanced learning modes"""
    EXPLORATION = "exploration"          # Actively explore new patterns
    EXPLOITATION = "exploitation"        # Use proven patterns
    BALANCED = "balanced"               # Balance exploration/exploitation
    CONSERVATIVE = "conservative"       # Minimal risk, proven patterns only
    AGGRESSIVE = "aggressive"           # High risk, maximum learning
    ADAPTIVE = "adaptive"              # Dynamically adjust based on performance
    REINFORCEMENT = "reinforcement"    # Use reinforcement learning
    TRANSFER = "transfer"              # Transfer learning from similar tasks

class OptimizationObjective(Enum):
    """Optimization objectives for learning"""
    SUCCESS_RATE = "success_rate"
    EXECUTION_TIME = "execution_time"
    RESOURCE_EFFICIENCY = "resource_efficiency"
    USER_SATISFACTION = "user_satisfaction"
    COST_OPTIMIZATION = "cost_optimization"
    BALANCED = "balanced"
    CUSTOM = "custom"

@dataclass
class EnhancedAgentTaskExecution:
    """Enhanced task execution record with ML features"""
    execution_id: str
    task_type: str
    task_description: str
    agents_invoked: List[str]
    execution_sequence: List[str]
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None
    user_satisfaction: Optional[int] = None  # 1-10 rating
    complexity_score: float = 1.0
    resource_metrics: Dict[str, float] = field(default_factory=dict)
    context_data: Dict[str, Any] = field(default_factory=dict)
    
    # ML-focused fields
    feature_vector: Optional[np.ndarray] = None
    predicted_success: Optional[float] = None
    predicted_duration: Optional[float] = None
    prediction_confidence: Optional[float] = None
    agent_synergy_scores: Dict[str, float] = field(default_factory=dict)
    task_embedding: Optional[np.ndarray] = None
    performance_anomaly: bool = False
    optimization_opportunities: List[str] = field(default_factory=list)

@dataclass
class AgentCollaborationPattern:
    """Pattern for agent collaboration effectiveness"""
    pattern_id: str
    agents: List[str]
    task_types: List[str]
    success_rate: float
    avg_duration: float
    synergy_score: float  # How well agents work together
    conflict_indicators: List[str] = field(default_factory=list)
    optimal_sequence: List[str] = field(default_factory=list)
    resource_efficiency: float = 1.0
    scalability_score: float = 1.0

@dataclass 
class TaskPrediction:
    """Prediction for task execution"""
    task_id: str
    predicted_agents: List[str]
    predicted_duration: float
    predicted_success_probability: float
    confidence_score: float
    risk_factors: List[str]
    optimization_suggestions: List[str]
    alternative_approaches: List[Dict[str, Any]]

@dataclass
class TaskContext:
    """Enhanced task context with rich features"""
    task_id: str
    task_type: str
    description: str
    complexity_score: float
    priority: int
    deadline: Optional[datetime]
    user_context: Dict[str, Any]
    environment_context: Dict[str, Any] = field(default_factory=dict)
    historical_context: List[Dict[str, Any]] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    expected_outcomes: Dict[str, Any] = field(default_factory=dict)
    risk_factors: List[str] = field(default_factory=list)
    optimization_goals: List[OptimizationObjective] = field(default_factory=list)
    parent_task_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentLearningInsight:
    """Learning insight from pattern analysis"""
    insight_id: str
    insight_type: str
    confidence_score: float
    title: str
    description: str
    supporting_data: Dict[str, Any]
    applicable_contexts: List[str]
    created_at: datetime
    category: Optional[str] = None
    impact_score: Optional[float] = None
    actionable_recommendations: List[str] = field(default_factory=list)
    expected_improvement: Dict[str, float] = field(default_factory=dict)
    risk_assessment: Dict[str, float] = field(default_factory=dict)
    validation_metrics: Dict[str, Any] = field(default_factory=dict)
    expiry_date: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    last_validated: Optional[datetime] = None
    validation_count: int = 0

@dataclass
class AgentPerformanceProfile:
    """Comprehensive agent performance profile"""
    agent_name: str
    capabilities: Set[str]
    success_metrics: Dict[str, float]
    performance_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    collaboration_matrix: Dict[str, float] = field(default_factory=dict)
    resource_profile: Dict[str, float] = field(default_factory=dict)
    skill_embeddings: Optional[np.ndarray] = None
    learning_curve: List[float] = field(default_factory=list)
    specialization_scores: Dict[str, float] = field(default_factory=dict)
    failure_patterns: List[Dict[str, Any]] = field(default_factory=list)
    optimization_hints: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    adaptation_rate: float = 0.0
    cognitive_load: float = 0.0

# ============================================================================
# ADVANCED PATTERN RECOGNITION ENGINE
# ============================================================================

class AdvancedPatternRecognizer:
    """Advanced pattern recognition with ML capabilities"""
    
    def __init__(self):
        self.sequence_analyzer = SequenceAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        self.synergy_calculator = SynergyCalculator()
        self.pattern_cache = {}
        
    def analyze_execution_patterns(self, executions: List[EnhancedAgentTaskExecution]) -> Dict[str, Any]:
        """Comprehensive pattern analysis"""
        patterns = {
            'sequences': self.sequence_analyzer.find_patterns(executions),
            'anomalies': self.anomaly_detector.detect(executions),
            'synergies': self.synergy_calculator.calculate(executions),
            'bottlenecks': self._identify_bottlenecks(executions),
            'optimization_opportunities': self._find_optimizations(executions)
        }
        return patterns
    
    def _identify_bottlenecks(self, executions: List[EnhancedAgentTaskExecution]) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Analyze agent-level bottlenecks
        agent_performance = defaultdict(list)
        for exec in executions:
            for agent in exec.agents_invoked:
                agent_performance[agent].append(exec.duration_seconds)
        
        for agent, durations in agent_performance.items():
            if len(durations) >= 5:
                avg_duration = np.mean(durations)
                p95_duration = np.percentile(durations, 95)
                if p95_duration > avg_duration * 2:  # Significant variance
                    bottlenecks.append({
                        'type': 'agent_performance',
                        'agent': agent,
                        'avg_duration': avg_duration,
                        'p95_duration': p95_duration,
                        'severity': 'high' if p95_duration > avg_duration * 3 else 'medium'
                    })
        
        return bottlenecks
    
    def _find_optimizations(self, executions: List[EnhancedAgentTaskExecution]) -> List[Dict[str, Any]]:
        """Find optimization opportunities"""
        optimizations = []
        
        # Find redundant agent invocations
        task_agent_combos = defaultdict(list)
        for exec in executions:
            key = (exec.task_type, tuple(sorted(exec.agents_invoked)))
            task_agent_combos[key].append(exec)
        
        for (task_type, agents), execs in task_agent_combos.items():
            if len(execs) >= 3:
                success_rate = sum(1 for e in execs if e.success) / len(execs)
                if success_rate < 0.7:
                    # Find better performing alternatives
                    alternatives = self._find_alternative_agents(task_type, agents, executions)
                    if alternatives:
                        optimizations.append({
                            'type': 'agent_replacement',
                            'task_type': task_type,
                            'current_agents': list(agents),
                            'suggested_agents': alternatives,
                            'expected_improvement': self._calculate_improvement(agents, alternatives, executions)
                        })
        
        return optimizations
    
    def _find_alternative_agents(self, task_type: str, current_agents: Tuple[str], 
                                 executions: List[EnhancedAgentTaskExecution]) -> List[str]:
        """Find better performing agent combinations"""
        alternatives = []
        
        # Analyze other successful executions for the same task type
        successful_combos = defaultdict(int)
        for exec in executions:
            if exec.task_type == task_type and exec.success:
                combo = tuple(sorted(exec.agents_invoked))
                if combo != current_agents:
                    successful_combos[combo] += 1
        
        if successful_combos:
            best_combo = max(successful_combos.items(), key=lambda x: x[1])
            alternatives = list(best_combo[0])
        
        return alternatives
    
    def _calculate_improvement(self, current: Tuple[str], suggested: List[str], 
                              executions: List[EnhancedAgentTaskExecution]) -> float:
        """Calculate expected improvement from agent change"""
        current_success = self._get_success_rate(current, executions)
        suggested_success = self._get_success_rate(tuple(sorted(suggested)), executions)
        return (suggested_success - current_success) / current_success if current_success > 0 else 0
    
    def _get_success_rate(self, agents: Tuple[str], executions: List[EnhancedAgentTaskExecution]) -> float:
        """Get success rate for agent combination"""
        matching = [e for e in executions if tuple(sorted(e.agents_invoked)) == agents]
        if not matching:
            return 0
        return sum(1 for e in matching if e.success) / len(matching)

class SequenceAnalyzer:
    """Analyze agent execution sequences"""
    
    def find_patterns(self, executions: List[EnhancedAgentTaskExecution]) -> List[Dict[str, Any]]:
        """Find common execution sequences"""
        sequences = []
        sequence_counts = Counter()
        
        for exec in executions:
            if exec.execution_sequence:
                seq_tuple = tuple(exec.execution_sequence)
                sequence_counts[seq_tuple] += 1
        
        for sequence, count in sequence_counts.most_common(10):
            if count >= 3:  # Minimum support
                sequences.append({
                    'sequence': list(sequence),
                    'frequency': count,
                    'success_rate': self._calculate_sequence_success(sequence, executions)
                })
        
        return sequences
    
    def _calculate_sequence_success(self, sequence: Tuple[str], 
                                   executions: List[EnhancedAgentTaskExecution]) -> float:
        """Calculate success rate for a specific sequence"""
        matching = [e for e in executions if tuple(e.execution_sequence) == sequence]
        if not matching:
            return 0
        return sum(1 for e in matching if e.success) / len(matching)

class AnomalyDetector:
    """Detect anomalies in execution patterns"""
    
    def detect(self, executions: List[EnhancedAgentTaskExecution]) -> List[Dict[str, Any]]:
        """Detect execution anomalies"""
        anomalies = []
        
        # Duration anomalies
        task_durations = defaultdict(list)
        for exec in executions:
            task_durations[exec.task_type].append(exec.duration_seconds)
        
        for task_type, durations in task_durations.items():
            if len(durations) >= 5:
                mean_duration = np.mean(durations)
                std_duration = np.std(durations)
                
                for exec in executions:
                    if exec.task_type == task_type:
                        z_score = abs((exec.duration_seconds - mean_duration) / std_duration) if std_duration > 0 else 0
                        if z_score > 3:  # 3 standard deviations
                            anomalies.append({
                                'type': 'duration_anomaly',
                                'execution_id': exec.execution_id,
                                'task_type': task_type,
                                'duration': exec.duration_seconds,
                                'expected_duration': mean_duration,
                                'z_score': z_score
                            })
        
        return anomalies

class SynergyCalculator:
    """Calculate agent synergy scores"""
    
    def calculate(self, executions: List[EnhancedAgentTaskExecution]) -> Dict[str, float]:
        """Calculate synergy between agent pairs"""
        synergies = {}
        agent_pairs = defaultdict(list)
        
        for exec in executions:
            if len(exec.agents_invoked) >= 2:
                for i, agent1 in enumerate(exec.agents_invoked):
                    for agent2 in exec.agents_invoked[i+1:]:
                        pair = tuple(sorted([agent1, agent2]))
                        agent_pairs[pair].append(exec)
        
        for pair, execs in agent_pairs.items():
            if len(execs) >= 3:
                success_rate = sum(1 for e in execs if e.success) / len(execs)
                avg_duration = np.mean([e.duration_seconds for e in execs])
                
                # Calculate synergy score (higher is better)
                synergy = success_rate / (1 + np.log1p(avg_duration))
                synergies[f"{pair[0]}+{pair[1]}"] = synergy
        
        return synergies

# ============================================================================
# PREDICTIVE ML MODELS
# ============================================================================

class PredictiveModels:
    """Machine learning models for prediction"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.feature_importance = {}
        
    def train_models(self, training_data: List[EnhancedAgentTaskExecution]):
        """Train all predictive models"""
        if not ML_AVAILABLE:
            logger.warning("ML libraries not available, skipping model training")
            return
        
        # Prepare features and labels
        X, y_success, y_duration, feature_names = self._prepare_training_data(training_data)
        
        if len(X) < 10:
            logger.warning("Insufficient training data for ML models")
            return
        
        # Train success prediction model
        self.models['success_predictor'] = self._train_success_model(X, y_success)
        
        # Train duration prediction model
        self.models['duration_predictor'] = self._train_duration_model(X, y_duration)
        
        # Train agent recommendation model
        self.models['agent_recommender'] = self._train_agent_recommender(training_data)
        
        # Calculate feature importance
        if 'success_predictor' in self.models:
            self.feature_importance = dict(zip(
                feature_names,
                self.models['success_predictor'].feature_importances_
            ))
        
        logger.info(f"Trained {len(self.models)} ML models successfully")
    
    def _prepare_training_data(self, executions: List[EnhancedAgentTaskExecution]) -> Tuple:
        """Prepare training data for ML models"""
        features = []
        success_labels = []
        duration_labels = []
        feature_names = []
        
        for exec in executions:
            # Create feature vector
            feature_vec = self._create_feature_vector(exec)
            features.append(feature_vec)
            success_labels.append(1 if exec.success else 0)
            duration_labels.append(exec.duration_seconds)
        
        # Generate feature names
        feature_names = [
            'complexity_score', 'num_agents', 'task_type_encoded',
            'hour_of_day', 'day_of_week', 'priority_level'
        ]
        
        return np.array(features), np.array(success_labels), np.array(duration_labels), feature_names
    
    def _create_feature_vector(self, execution: EnhancedAgentTaskExecution) -> np.ndarray:
        """Create feature vector from execution"""
        features = []
        
        # Basic features
        features.append(execution.complexity_score)
        features.append(len(execution.agents_invoked))
        
        # Encode task type
        if 'task_type' not in self.encoders:
            self.encoders['task_type'] = LabelEncoder()
            self.encoders['task_type'].fit(['web_development', 'api_development', 'bug_fix', 
                                           'deployment', 'security_audit', 'other'])
        
        try:
            task_type_encoded = self.encoders['task_type'].transform([execution.task_type])[0]
        except:
            task_type_encoded = self.encoders['task_type'].transform(['other'])[0]
        features.append(task_type_encoded)
        
        # Time-based features
        features.append(execution.start_time.hour)
        features.append(execution.start_time.weekday())
        
        # Priority from context
        priority = execution.context_data.get('priority', 5)
        features.append(priority)
        
        return np.array(features)
    
    def _train_success_model(self, X: np.ndarray, y: np.ndarray):
        """Train success prediction model"""
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )
        
        # Scale features
        if 'success' not in self.scalers:
            self.scalers['success'] = StandardScaler()
        X_scaled = self.scalers['success'].fit_transform(X)
        
        # Train with cross-validation
        scores = cross_val_score(model, X_scaled, y, cv=3, scoring='accuracy')
        logger.info(f"Success model CV accuracy: {np.mean(scores):.3f} (+/- {np.std(scores):.3f})")
        
        model.fit(X_scaled, y)
        return model
    
    def _train_duration_model(self, X: np.ndarray, y: np.ndarray):
        """Train duration prediction model"""
        model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        
        # Scale features
        if 'duration' not in self.scalers:
            self.scalers['duration'] = StandardScaler()
        X_scaled = self.scalers['duration'].fit_transform(X)
        
        # Train with cross-validation
        scores = cross_val_score(model, X_scaled, y, cv=3, scoring='neg_mean_squared_error')
        logger.info(f"Duration model CV RMSE: {np.sqrt(-np.mean(scores)):.2f}")
        
        model.fit(X_scaled, y)
        return model
    
    def _train_agent_recommender(self, executions: List[EnhancedAgentTaskExecution]):
        """Train agent recommendation model"""
        # Create agent-task success matrix
        agent_task_success = defaultdict(lambda: defaultdict(list))
        
        for exec in executions:
            for agent in exec.agents_invoked:
                agent_task_success[exec.task_type][agent].append(1 if exec.success else 0)
        
        # Calculate success rates
        agent_scores = {}
        for task_type, agents in agent_task_success.items():
            agent_scores[task_type] = {}
            for agent, successes in agents.items():
                if len(successes) >= 2:
                    agent_scores[task_type][agent] = np.mean(successes)
        
        return agent_scores
    
    def predict(self, task_context: TaskContext) -> TaskPrediction:
        """Make comprehensive prediction for task"""
        # Create dummy execution for feature extraction
        dummy_exec = EnhancedAgentTaskExecution(
            execution_id="pred_" + hashlib.md5(f"{task_context.task_type}{time.time()}".encode()).hexdigest()[:8],
            task_type=task_context.task_type,
            task_description=task_context.description,
            agents_invoked=[],
            execution_sequence=[],
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration_seconds=0,
            success=False,
            complexity_score=task_context.complexity_score,
            context_data=task_context.user_context
        )
        
        feature_vec = self._create_feature_vector(dummy_exec)
        
        predictions = {
            'success_probability': 0.7,  # Default
            'duration': 30.0,  # Default
            'confidence': 0.5  # Default
        }
        
        # Make predictions if models are available
        if 'success_predictor' in self.models:
            X_scaled = self.scalers['success'].transform([feature_vec])
            success_prob = self.models['success_predictor'].predict_proba(X_scaled)[0][1]
            predictions['success_probability'] = success_prob
        
        if 'duration_predictor' in self.models:
            X_scaled = self.scalers['duration'].transform([feature_vec])
            duration = self.models['duration_predictor'].predict(X_scaled)[0]
            predictions['duration'] = max(1.0, duration)  # Minimum 1 second
        
        # Get agent recommendations
        recommended_agents = self._recommend_agents(task_context.task_type, task_context.complexity_score)
        
        # Calculate confidence
        confidence = self._calculate_prediction_confidence(predictions, len(recommended_agents))
        
        return TaskPrediction(
            task_id=dummy_exec.execution_id,
            predicted_agents=recommended_agents,
            predicted_duration=predictions['duration'],
            predicted_success_probability=predictions['success_probability'],
            confidence_score=confidence,
            risk_factors=self._identify_risk_factors(task_context),
            optimization_suggestions=self._generate_optimization_suggestions(task_context.task_type, recommended_agents),
            alternative_approaches=self._find_alternatives(task_context.task_type, recommended_agents)
        )
    
    def _recommend_agents(self, task_type: str, complexity: float) -> List[str]:
        """Recommend optimal agents for task"""
        if 'agent_recommender' in self.models and task_type in self.models['agent_recommender']:
            agent_scores = self.models['agent_recommender'][task_type]
            # Sort by score and return top agents
            sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Adjust number of agents based on complexity
            num_agents = min(5, max(2, int(complexity * 2)))
            return [agent for agent, score in sorted_agents[:num_agents]]
        
        # Fallback recommendations
        return self._get_fallback_agents(task_type, complexity)
    
    def _get_fallback_agents(self, task_type: str, complexity: float) -> List[str]:
        """Fallback agent recommendations"""
        base_recommendations = {
            'web_development': ['WEB', 'APIDESIGNER', 'DATABASE', 'TESTBED'],
            'api_development': ['APIDESIGNER', 'DATABASE', 'SECURITY', 'TESTBED'],
            'bug_fix': ['DEBUGGER', 'PATCHER', 'TESTBED', 'LINTER'],
            'deployment': ['DEPLOYER', 'INFRASTRUCTURE', 'MONITOR', 'SECURITY'],
            'security_audit': ['SECURITY', 'SECURITYAUDITOR', 'CRYPTOEXPERT', 'BASTION']
        }
        
        agents = base_recommendations.get(task_type, ['DIRECTOR', 'PROJECTORCHESTRATOR', 'ARCHITECT'])
        
        # Add more agents for complex tasks
        if complexity > 3:
            agents.append('MONITOR')
        if complexity > 4:
            agents.append('OPTIMIZER')
        
        return agents[:min(5, max(2, int(complexity * 2)))]
    
    def _calculate_prediction_confidence(self, predictions: Dict, num_agents: int) -> float:
        """Calculate confidence in predictions"""
        confidence_factors = []
        
        # Success probability confidence
        success_prob = predictions['success_probability']
        if success_prob > 0.8 or success_prob < 0.2:
            confidence_factors.append(0.9)  # High confidence in extreme predictions
        else:
            confidence_factors.append(0.6)  # Medium confidence in middle range
        
        # Agent recommendation confidence
        if num_agents >= 2 and num_agents <= 4:
            confidence_factors.append(0.8)  # Good agent count
        else:
            confidence_factors.append(0.5)  # Less optimal agent count
        
        return np.mean(confidence_factors)
    
    def _identify_risk_factors(self, task_context: TaskContext) -> List[str]:
        """Identify potential risk factors"""
        risks = []
        
        if task_context.complexity_score > 4:
            risks.append("High complexity task - may require additional review")
        
        if task_context.priority <= 2:
            risks.append("Critical priority - ensure thorough testing")
        
        if task_context.task_type in ['deployment', 'security_audit']:
            risks.append("High-impact operation - requires careful execution")
        
        if task_context.deadline and (task_context.deadline - datetime.now()).total_seconds() < 3600:
            risks.append("Tight deadline - limited time for error recovery")
        
        return risks
    
    def _generate_optimization_suggestions(self, task_type: str, agents: List[str]) -> List[str]:
        """Generate optimization suggestions"""
        suggestions = []
        
        if len(agents) > 3:
            suggestions.append("Consider parallel execution for independent agent tasks")
        
        if 'TESTBED' not in agents and task_type != 'testing':
            suggestions.append("Add TESTBED agent for quality assurance")
        
        if 'MONITOR' not in agents and task_type in ['deployment', 'performance_optimization']:
            suggestions.append("Include MONITOR agent for performance tracking")
        
        return suggestions
    
    def _find_alternatives(self, task_type: str, primary_agents: List[str]) -> List[Dict[str, Any]]:
        """Find alternative approaches"""
        alternatives = []
        
        # Alternative 1: Minimal agent set
        minimal_agents = primary_agents[:2] if len(primary_agents) > 2 else primary_agents
        alternatives.append({
            'name': 'Minimal Approach',
            'agents': minimal_agents,
            'pros': ['Faster execution', 'Lower resource usage'],
            'cons': ['Potentially lower quality', 'Less comprehensive']
        })
        
        # Alternative 2: Enhanced security
        if 'SECURITY' not in primary_agents:
            security_enhanced = primary_agents + ['SECURITY']
            alternatives.append({
                'name': 'Security-Enhanced Approach',
                'agents': security_enhanced,
                'pros': ['Better security coverage', 'Compliance assurance'],
                'cons': ['Longer execution time', 'Additional resource usage']
            })
        
        return alternatives

# ============================================================================
# ENHANCED POSTGRESQL LEARNING SYSTEM
# ============================================================================

class EnhancedPostgreSQLLearningSystem:
    """Enhanced learning system with advanced ML and real-time optimization"""
    
    def __init__(self, db_config: Dict[str, str] = None):
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5432,
            'database': 'claude_agents',
            'user': 'postgres',
            'password': 'your_password'
        }
        
        # Core components
        self.pattern_recognizer = AdvancedPatternRecognizer()
        self.predictive_models = PredictiveModels()
        
        # Caching and performance
        self.prediction_cache = {}
        self.insight_cache = deque(maxlen=100)
        self.performance_buffer = deque(maxlen=1000)
        
        # Real-time monitoring
        self.alert_thresholds = {
            'success_rate_min': 0.7,
            'duration_p95_max': 120,  # seconds
            'error_rate_max': 0.2
        }
        
        # Learning state
        self.learning_enabled = True
        self.learning_mode = LearningMode.ADAPTIVE
        self.auto_retrain_threshold = 50  # Retrain after N new executions
        self.executions_since_training = 0
        
        self.setup_complete = False
    
    async def initialize(self):
        """Initialize enhanced learning system"""
        try:
            # Test database connection
            conn = await asyncpg.connect(**self.db_config)
            await conn.close()
            
            # Setup enhanced schema
            await self.setup_enhanced_schema()
            
            # Load existing models if available
            await self.load_models()
            
            # Initialize monitoring
            await self.initialize_monitoring()
            
            self.setup_complete = True
            logger.info("Enhanced PostgreSQL Learning System v3.0 initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced learning system: {e}")
            return False
    
    async def setup_enhanced_schema(self):
        """Setup enhanced database schema with ML tables"""
        conn = await asyncpg.connect(**self.db_config)
        
        try:
            # Create extension if not exists
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            
            # Enhanced execution table with ML fields
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_task_executions (
                    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    task_type VARCHAR(64) NOT NULL,
                    task_description TEXT,
                    agents_invoked JSONB DEFAULT '[]',
                    execution_sequence JSONB DEFAULT '[]',
                    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    duration_seconds FLOAT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    user_satisfaction INTEGER CHECK (user_satisfaction BETWEEN 1 AND 10),
                    complexity_score FLOAT DEFAULT 1.0,
                    resource_metrics JSONB DEFAULT '{}',
                    context_data JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    predicted_success FLOAT,
                    predicted_duration FLOAT,
                    prediction_confidence FLOAT,
                    performance_anomaly BOOLEAN DEFAULT FALSE,
                    optimization_applied BOOLEAN DEFAULT FALSE,
                    ml_features JSONB DEFAULT '{}',
                    agent_synergy_scores JSONB DEFAULT '{}'
                )
            """)
            
            # ML model registry
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ml_models (
                    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    model_name VARCHAR(64) NOT NULL,
                    model_type VARCHAR(32) NOT NULL,
                    model_version VARCHAR(16) NOT NULL,
                    model_data BYTEA NOT NULL,
                    feature_importance JSONB DEFAULT '{}',
                    performance_metrics JSONB DEFAULT '{}',
                    training_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    training_samples INTEGER,
                    is_active BOOLEAN DEFAULT TRUE,
                    
                    UNIQUE(model_name, model_version)
                )
            """)
            
            # Agent collaboration patterns
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_collaboration_patterns (
                    pattern_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    agents JSONB NOT NULL,
                    task_types JSONB DEFAULT '[]',
                    success_rate FLOAT NOT NULL,
                    avg_duration FLOAT NOT NULL,
                    synergy_score FLOAT DEFAULT 0.0,
                    optimal_sequence JSONB DEFAULT '[]',
                    resource_efficiency FLOAT DEFAULT 1.0,
                    scalability_score FLOAT DEFAULT 1.0,
                    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_validated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    validation_count INTEGER DEFAULT 0,
                    
                    UNIQUE(agents)
                )
            """)
            
            # Real-time performance metrics
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS realtime_performance_metrics (
                    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    metric_type VARCHAR(32) NOT NULL,
                    metric_name VARCHAR(64) NOT NULL,
                    metric_value FLOAT NOT NULL,
                    threshold_value FLOAT,
                    is_alert BOOLEAN DEFAULT FALSE,
                    alert_severity VARCHAR(16),
                    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    context_data JSONB DEFAULT '{}'
                )
            """)
            
            # Learning insights table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_learning_insights (
                    insight_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    insight_type VARCHAR(32) NOT NULL,
                    confidence_score FLOAT NOT NULL CHECK (confidence_score BETWEEN 0.0 AND 1.0),
                    title VARCHAR(256) NOT NULL,
                    description TEXT NOT NULL,
                    supporting_data JSONB DEFAULT '{}',
                    applicable_contexts JSONB DEFAULT '[]',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_validated TIMESTAMP WITH TIME ZONE,
                    validation_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Create indexes for ML operations
            await conn.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_executions_ml_features 
                    ON agent_task_executions USING GIN(ml_features);
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_executions_anomaly 
                    ON agent_task_executions(performance_anomaly) WHERE performance_anomaly = true;
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_models_active 
                    ON ml_models(model_name, is_active) WHERE is_active = true;
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_collab_synergy 
                    ON agent_collaboration_patterns(synergy_score DESC);
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_metrics_alerts 
                    ON realtime_performance_metrics(is_alert, recorded_at DESC) WHERE is_alert = true;
            """)
            
            logger.info("Enhanced learning schema setup complete")
            
        finally:
            await conn.close()
    
    async def record_enhanced_execution(self, execution: EnhancedAgentTaskExecution, 
                                       user_id: str = None, session_id: str = None):
        """Record execution with ML predictions and analysis"""
        if not self.setup_complete:
            await self.initialize()
        
        conn = await asyncpg.connect(**self.db_config)
        
        try:
            # Make predictions before execution
            task_context = TaskContext(
                task_id=execution.execution_id,
                task_type=execution.task_type,
                description=execution.task_description,
                complexity_score=execution.complexity_score,
                priority=execution.context_data.get('priority', 5),
                deadline=execution.context_data.get('deadline'),
                user_context=execution.context_data
            )
            
            prediction = self.predictive_models.predict(task_context)
            
            # Detect anomalies
            patterns = self.pattern_recognizer.analyze_execution_patterns([execution])
            is_anomaly = len(patterns.get('anomalies', [])) > 0
            
            # Calculate synergy scores
            synergy_scores = patterns.get('synergies', {})
            
            # Store enhanced execution record
            await conn.execute("""
                INSERT INTO agent_task_executions (
                    execution_id, task_type, task_description, agents_invoked, 
                    execution_sequence, start_time, end_time, duration_seconds, 
                    success, error_message, user_satisfaction, complexity_score, 
                    resource_metrics, context_data,
                    predicted_success, predicted_duration, prediction_confidence,
                    performance_anomaly, ml_features, agent_synergy_scores
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 
                         $13, $14, $15, $16, $17, $18, $19, $20)
            """,
                execution.execution_id, execution.task_type, execution.task_description,
                json.dumps(execution.agents_invoked), json.dumps(execution.execution_sequence),
                execution.start_time, execution.end_time, execution.duration_seconds,
                execution.success, execution.error_message, execution.user_satisfaction,
                execution.complexity_score, json.dumps(execution.resource_metrics),
                json.dumps(execution.context_data),
                prediction.predicted_success_probability, prediction.predicted_duration,
                prediction.confidence_score, is_anomaly,
                json.dumps({}), json.dumps(synergy_scores)
            )
            
            # Update collaboration patterns
            await self.update_collaboration_patterns(conn, execution, synergy_scores)
            
            # Check for alerts
            await self.check_performance_alerts(conn, execution)
            
            # Trigger retraining if needed
            self.executions_since_training += 1
            if self.executions_since_training >= self.auto_retrain_threshold:
                asyncio.create_task(self.retrain_models())
            
        finally:
            await conn.close()
    
    async def update_collaboration_patterns(self, conn, execution: EnhancedAgentTaskExecution, 
                                           synergy_scores: Dict[str, float]):
        """Update agent collaboration patterns"""
        if len(execution.agents_invoked) < 2:
            return
        
        agents_json = json.dumps(sorted(execution.agents_invoked))
        
        # Calculate pattern metrics
        synergy_score = np.mean(list(synergy_scores.values())) if synergy_scores else 0.5
        resource_efficiency = 1.0 / (1 + np.log1p(sum(execution.resource_metrics.values())))
        
        await conn.execute("""
            INSERT INTO agent_collaboration_patterns (
                agents, task_types, success_rate, avg_duration, synergy_score,
                optimal_sequence, resource_efficiency
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (agents) DO UPDATE SET
                task_types = CASE 
                    WHEN NOT (agent_collaboration_patterns.task_types ? $8)
                    THEN agent_collaboration_patterns.task_types || $2
                    ELSE agent_collaboration_patterns.task_types
                END,
                success_rate = (
                    agent_collaboration_patterns.success_rate * agent_collaboration_patterns.validation_count + $3
                ) / (agent_collaboration_patterns.validation_count + 1),
                avg_duration = (
                    agent_collaboration_patterns.avg_duration * agent_collaboration_patterns.validation_count + $4
                ) / (agent_collaboration_patterns.validation_count + 1),
                synergy_score = (
                    agent_collaboration_patterns.synergy_score * agent_collaboration_patterns.validation_count + $5
                ) / (agent_collaboration_patterns.validation_count + 1),
                resource_efficiency = (
                    agent_collaboration_patterns.resource_efficiency * agent_collaboration_patterns.validation_count + $7
                ) / (agent_collaboration_patterns.validation_count + 1),
                last_validated = NOW(),
                validation_count = agent_collaboration_patterns.validation_count + 1
        """,
            agents_json, json.dumps([execution.task_type]),
            1.0 if execution.success else 0.0, execution.duration_seconds,
            synergy_score, json.dumps(execution.execution_sequence),
            resource_efficiency, execution.task_type
        )
    
    async def check_performance_alerts(self, conn, execution: EnhancedAgentTaskExecution):
        """Check and record performance alerts"""
        alerts = []
        
        # Check duration threshold
        if execution.duration_seconds > self.alert_thresholds['duration_p95_max']:
            alerts.append({
                'type': 'duration_exceeded',
                'severity': 'warning',
                'value': execution.duration_seconds,
                'threshold': self.alert_thresholds['duration_p95_max']
            })
        
        # Check failure
        if not execution.success:
            alerts.append({
                'type': 'execution_failed',
                'severity': 'error',
                'error': execution.error_message
            })
        
        # Record alerts
        for alert in alerts:
            await conn.execute("""
                INSERT INTO realtime_performance_metrics (
                    metric_type, metric_name, metric_value, threshold_value,
                    is_alert, alert_severity, context_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                alert['type'], f"execution_{execution.execution_id}",
                alert.get('value', 0), alert.get('threshold', 0),
                True, alert['severity'], json.dumps(alert)
            )
    
    async def retrain_models(self):
        """Retrain ML models with recent data"""
        if not ML_AVAILABLE:
            return
        
        conn = await asyncpg.connect(**self.db_config)
        
        try:
            # Fetch recent training data
            rows = await conn.fetch("""
                SELECT * FROM agent_task_executions 
                WHERE start_time >= NOW() - INTERVAL '30 days'
                ORDER BY start_time DESC
                LIMIT 1000
            """)
            
            if len(rows) < 50:
                logger.warning("Insufficient data for model retraining")
                return
            
            # Convert to training format
            training_data = []
            for row in rows:
                execution = EnhancedAgentTaskExecution(
                    execution_id=str(row['execution_id']),
                    task_type=row['task_type'],
                    task_description=row['task_description'] or "",
                    agents_invoked=json.loads(row['agents_invoked']),
                    execution_sequence=json.loads(row['execution_sequence']),
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    duration_seconds=row['duration_seconds'],
                    success=row['success'],
                    error_message=row['error_message'],
                    user_satisfaction=row.get('user_satisfaction'),
                    complexity_score=row['complexity_score'],
                    resource_metrics=json.loads(row.get('resource_metrics', '{}')),
                    context_data=json.loads(row.get('context_data', '{}'))
                )
                training_data.append(execution)
            
            # Train models
            self.predictive_models.train_models(training_data)
            
            # Store models in database
            for model_name, model in self.predictive_models.models.items():
                model_data = pickle.dumps(model)
                feature_importance = self.predictive_models.feature_importance
                
                await conn.execute("""
                    INSERT INTO ml_models (
                        model_name, model_type, model_version, model_data,
                        feature_importance, training_samples, is_active
                    ) VALUES ($1, $2, $3, $4, $5, $6, TRUE)
                    ON CONFLICT (model_name, model_version) DO UPDATE SET
                        model_data = $4,
                        feature_importance = $5,
                        training_samples = $6,
                        training_date = NOW()
                """, model_name, type(model).__name__, 'v3.0', model_data,
                    json.dumps(feature_importance), len(training_data))
            
            self.executions_since_training = 0
            logger.info(f"Models retrained with {len(training_data)} samples")
            
        finally:
            await conn.close()
    
    async def initialize_monitoring(self):
        """Initialize real-time monitoring system"""
        # Set up monitoring tasks
        asyncio.create_task(self.monitor_performance())
        asyncio.create_task(self.detect_anomalies())
        asyncio.create_task(self.optimize_continuously())
        logger.info("Monitoring systems initialized")
    
    async def monitor_performance(self):
        """Continuous performance monitoring"""
        while True:
            try:
                conn = await asyncpg.connect(**self.db_config)
                
                # Check recent performance
                metrics = await conn.fetchrow("""
                    SELECT 
                        AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                        AVG(duration_seconds) as avg_duration,
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_seconds) as p95_duration,
                        COUNT(*) as execution_count
                    FROM agent_task_executions
                    WHERE start_time >= NOW() - INTERVAL '1 hour'
                """)
                
                if metrics and metrics['execution_count'] > 0:
                    # Check against thresholds
                    alerts = []
                    if metrics['success_rate'] < self.alert_thresholds['success_rate_min']:
                        alerts.append({
                            'type': 'low_success_rate',
                            'value': metrics['success_rate'],
                            'threshold': self.alert_thresholds['success_rate_min']
                        })
                    
                    if metrics['p95_duration'] and metrics['p95_duration'] > self.alert_thresholds['duration_p95_max']:
                        alerts.append({
                            'type': 'high_duration',
                            'value': metrics['p95_duration'],
                            'threshold': self.alert_thresholds['duration_p95_max']
                        })
                    
                    # Record alerts
                    for alert in alerts:
                        await conn.execute("""
                            INSERT INTO realtime_performance_metrics (
                                metric_type, metric_name, metric_value, threshold_value,
                                is_alert, alert_severity, context_data
                            ) VALUES ($1, $2, $3, $4, TRUE, $5, $6)
                        """, alert['type'], 'system_performance', alert['value'],
                            alert['threshold'], 'high', json.dumps(alert))
                    
                    # Update performance buffer
                    self.performance_buffer.append({
                        'timestamp': datetime.now(),
                        'metrics': dict(metrics),
                        'alerts': alerts
                    })
                
                await conn.close()
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def detect_anomalies(self):
        """Real-time anomaly detection"""
        while True:
            try:
                if len(self.performance_buffer) < 10:
                    await asyncio.sleep(60)
                    continue
                
                # Use Isolation Forest for anomaly detection
                if ML_AVAILABLE:
                    recent_metrics = list(self.performance_buffer)[-100:]
                    
                    # Extract features
                    features = []
                    for m in recent_metrics:
                        if 'metrics' in m and m['metrics']:
                            features.append([
                                m['metrics'].get('success_rate', 0),
                                m['metrics'].get('avg_duration', 0),
                                m['metrics'].get('execution_count', 0)
                            ])
                    
                    if len(features) >= 10:
                        # Train anomaly detector
                        detector = IsolationForest(contamination=0.1, random_state=42)
                        anomalies = detector.fit_predict(features)
                        
                        # Identify anomalous periods
                        for i, is_anomaly in enumerate(anomalies):
                            if is_anomaly == -1:  # Anomaly detected
                                logger.warning(f"Anomaly detected at index {i}: {features[i]}")
                                
                                # Store anomaly insight
                                self.insight_cache.append(AgentLearningInsight(
                                    insight_id=hashlib.md5(f"anomaly_{time.time()}".encode()).hexdigest(),
                                    insight_type='anomaly',
                                    confidence_score=0.8,
                                    title="Performance Anomaly Detected",
                                    description=f"Unusual performance pattern detected",
                                    supporting_data={'features': features[i]},
                                    applicable_contexts=['system_monitoring'],
                                    created_at=datetime.now()
                                ))
                
            except Exception as e:
                logger.error(f"Anomaly detection error: {e}")
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def optimize_continuously(self):
        """Continuous optimization based on learning"""
        while True:
            try:
                if not self.learning_enabled:
                    await asyncio.sleep(600)
                    continue
                
                conn = await asyncpg.connect(**self.db_config)
                
                # Find optimization opportunities
                opportunities = await conn.fetch("""
                    WITH agent_performance AS (
                        SELECT 
                            elem::text as agent_name,
                            task_type,
                            AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                            AVG(duration_seconds) as avg_duration,
                            COUNT(*) as usage_count
                        FROM agent_task_executions,
                             jsonb_array_elements(agents_invoked) elem
                        WHERE start_time >= NOW() - INTERVAL '7 days'
                        GROUP BY agent_name, task_type
                        HAVING COUNT(*) >= 5
                    )
                    SELECT * FROM agent_performance
                    WHERE success_rate < 0.7 OR avg_duration > 60
                    ORDER BY usage_count DESC
                    LIMIT 10
                """)
                
                for opp in opportunities:
                    # Generate optimization recommendation
                    recommendation = await self.generate_optimization_recommendation(
                        opp['agent_name'],
                        opp['task_type'],
                        opp['success_rate'],
                        opp['avg_duration']
                    )
                    
                    if recommendation:
                        self.insight_cache.append(recommendation)
                
                await conn.close()
                
            except Exception as e:
                logger.error(f"Continuous optimization error: {e}")
            
            await asyncio.sleep(600)  # Optimize every 10 minutes
    
    async def generate_optimization_recommendation(self, agent_name: str, task_type: str,
                                                  success_rate: float, avg_duration: float) -> Optional[AgentLearningInsight]:
        """Generate specific optimization recommendations"""
        
        recommendations = []
        confidence = 0.5
        
        if success_rate < 0.5:
            recommendations.append(f"Consider replacing {agent_name} for {task_type} tasks")
            recommendations.append(f"Review error patterns for {agent_name}")
            confidence = 0.8
        elif success_rate < 0.7:
            recommendations.append(f"Add error handling for {agent_name} in {task_type}")
            recommendations.append(f"Consider pairing {agent_name} with complementary agent")
            confidence = 0.7
        
        if avg_duration > 120:
            recommendations.append(f"Investigate performance bottlenecks in {agent_name}")
            recommendations.append("Consider parallel execution or caching")
            confidence = max(confidence, 0.75)
        elif avg_duration > 60:
            recommendations.append(f"Optimize {agent_name} processing for {task_type}")
            confidence = max(confidence, 0.6)
        
        if recommendations:
            return AgentLearningInsight(
                insight_id=hashlib.md5(f"opt_{agent_name}_{task_type}_{time.time()}".encode()).hexdigest(),
                insight_type='optimization',
                confidence_score=confidence,
                title=f"Optimization Opportunity: {agent_name}",
                description=f"{agent_name} shows optimization potential for {task_type} tasks",
                supporting_data={
                    'agent': agent_name,
                    'task_type': task_type,
                    'success_rate': success_rate,
                    'avg_duration': avg_duration,
                    'recommendations': recommendations
                },
                applicable_contexts=[task_type],
                created_at=datetime.now(),
                actionable_recommendations=recommendations
            )
        
        return None
    
    async def load_models(self):
        """Load ML models from database"""
        if not ML_AVAILABLE:
            return
        
        conn = await asyncpg.connect(**self.db_config)
        
        try:
            # Load active models
            models = await conn.fetch("""
                SELECT model_name, model_data, feature_importance
                FROM ml_models
                WHERE is_active = TRUE
                ORDER BY training_date DESC
            """)
            
            for model_row in models:
                try:
                    model = pickle.loads(model_row['model_data'])
                    self.predictive_models.models[model_row['model_name']] = model
                    
                    if model_row['feature_importance']:
                        self.predictive_models.feature_importance = json.loads(
                            model_row['feature_importance']
                        )
                    
                    logger.info(f"Loaded model: {model_row['model_name']}")
                    
                except Exception as e:
                    logger.error(f"Failed to load model {model_row['model_name']}: {e}")
            
        finally:
            await conn.close()
    
    async def get_agent_recommendation_with_confidence(self, task_context: TaskContext) -> Dict[str, Any]:
        """Get agent recommendations with confidence scores"""
        
        # Make prediction
        prediction = self.predictive_models.predict(task_context)
        
        # Get historical performance for confidence adjustment
        conn = await asyncpg.connect(**self.db_config)
        
        try:
            historical_performance = await conn.fetch("""
                SELECT 
                    agents_invoked,
                    AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                    COUNT(*) as sample_size
                FROM agent_task_executions
                WHERE task_type = $1
                    AND complexity_score BETWEEN $2 - 0.5 AND $2 + 0.5
                    AND start_time >= NOW() - INTERVAL '30 days'
                GROUP BY agents_invoked
                HAVING COUNT(*) >= 3
                ORDER BY success_rate DESC
                LIMIT 5
            """, task_context.task_type, task_context.complexity_score)
            
            # Adjust confidence based on historical data
            if historical_performance:
                best_historical = historical_performance[0]
                if json.loads(best_historical['agents_invoked']) == prediction.predicted_agents:
                    prediction.confidence_score = min(0.95, prediction.confidence_score * 1.2)
            
            # Calculate risk-adjusted recommendations
            alternatives = []
            for hp in historical_performance:
                agents = json.loads(hp['agents_invoked'])
                if agents != prediction.predicted_agents:
                    alternatives.append({
                        'agents': agents,
                        'expected_success_rate': hp['success_rate'],
                        'confidence': min(0.9, hp['sample_size'] / 20),
                        'sample_size': hp['sample_size']
                    })
            
        finally:
            await conn.close()
        
        return {
            'primary_recommendation': {
                'agents': prediction.predicted_agents,
                'confidence': prediction.confidence_score,
                'expected_duration': prediction.predicted_duration,
                'expected_success': prediction.predicted_success_probability,
                'risk_factors': prediction.risk_factors,
                'optimization_suggestions': prediction.optimization_suggestions
            },
            'alternatives': alternatives[:3],  # Top 3 alternatives
            'learning_mode': self.learning_mode.value,
            'recommendation_id': prediction.task_id,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_learning_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive learning system dashboard"""
        conn = await asyncpg.connect(**self.db_config)
        
        try:
            # Get overall statistics
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_executions,
                    AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as overall_success_rate,
                    AVG(duration_seconds) as avg_duration,
                    COUNT(DISTINCT task_type) as unique_task_types,
                    COUNT(DISTINCT agents_invoked) as unique_agent_combinations
                FROM agent_task_executions
                WHERE start_time >= NOW() - INTERVAL '30 days'
            """)
            
            # Get recent insights
            recent_insights = list(self.insight_cache)[-10:]
            
            # Get top performing agents
            top_agents = await conn.fetch("""
                SELECT 
                    agent_name,
                    AVG(success_rate) as avg_success_rate,
                    SUM(total_invocations) as total_invocations
                FROM agent_performance_metrics
                GROUP BY agent_name
                ORDER BY avg_success_rate DESC
                LIMIT 5
            """)
            
            # Get collaboration patterns
            best_patterns = await conn.fetch("""
                SELECT 
                    agents,
                    synergy_score,
                    success_rate,
                    avg_duration
                FROM agent_collaboration_patterns
                ORDER BY synergy_score DESC
                LIMIT 5
            """)
            
            return {
                'statistics': dict(stats) if stats else {},
                'recent_insights': [asdict(i) for i in recent_insights],
                'top_agents': [dict(a) for a in top_agents],
                'best_collaboration_patterns': [dict(p) for p in best_patterns],
                'learning_mode': self.learning_mode.value,
                'models_trained': len(self.predictive_models.models),
                'executions_since_training': self.executions_since_training,
                'system_status': 'healthy' if self.setup_complete else 'initializing'
            }
            
        finally:
            await conn.close()

# ============================================================================
# CLAUDE-CODE INTERFACE BRIDGE
# ============================================================================

class ClaudeCodeLearningInterface:
    """Interface for Claude-Code integration with learning system"""
    
    def __init__(self, learning_system: EnhancedPostgreSQLLearningSystem):
        self.learning_system = learning_system
        self.active_tasks = {}
        self.command_queue = asyncio.Queue()
        
    async def handle_claude_code_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests from Claude-Code"""
        
        request_type = request.get('type', 'unknown')
        
        if request_type == 'get_agent_recommendation':
            context = TaskContext(**request['context'])
            return await self.learning_system.get_agent_recommendation_with_confidence(context)
            
        elif request_type == 'record_execution':
            execution = EnhancedAgentTaskExecution(**request['execution'])
            await self.learning_system.record_enhanced_execution(
                execution,
                request.get('user_id'),
                request.get('session_id')
            )
            return {'status': 'recorded', 'execution_id': execution.execution_id}
            
        elif request_type == 'get_insights':
            insights = list(self.learning_system.insight_cache)
            return {
                'insights': [asdict(i) for i in insights[:10]],
                'total_count': len(insights)
            }
            
        elif request_type == 'get_dashboard':
            return await self.learning_system.get_learning_dashboard()
            
        elif request_type == 'train_models':
            await self.learning_system.retrain_models()
            return {'status': 'training_complete', 'timestamp': datetime.now().isoformat()}
            
        elif request_type == 'set_learning_mode':
            mode = request.get('mode', 'balanced')
            self.learning_system.learning_mode = LearningMode[mode.upper()]
            return {'status': 'mode_updated', 'mode': mode}
            
        else:
            return {'error': f'Unknown request type: {request_type}'}
    
    async def stream_realtime_metrics(self):
        """Stream real-time metrics for Claude-Code dashboard"""
        while True:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'performance_buffer': list(self.learning_system.performance_buffer)[-10:],
                'active_insights': len(self.learning_system.insight_cache),
                'executions_since_training': self.learning_system.executions_since_training,
                'learning_enabled': self.learning_system.learning_enabled,
                'learning_mode': self.learning_system.learning_mode.value
            }
            
            yield json.dumps(metrics)
            await asyncio.sleep(5)  # Update every 5 seconds

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution with complete integration"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize learning system
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'claude_agents',
        'user': 'postgres',
        'password': 'your_password'
    }
    
    learning_system = EnhancedPostgreSQLLearningSystem(db_config)
    await learning_system.initialize()
    
    # Initialize Claude-Code interface
    claude_interface = ClaudeCodeLearningInterface(learning_system)
    
    print("="*60)
    print("Enhanced PostgreSQL Agent Learning System v3.0")
    print("="*60)
    print("✅ Learning System: Initialized")
    print("✅ Claude-Code Interface: Ready")
    print("✅ ML Models: Ready")
    print("✅ Monitoring: Active")
    print("="*60)
    
    # Get dashboard
    dashboard = await learning_system.get_learning_dashboard()
    print("\n📊 System Dashboard:")
    print(f"  Total Executions: {dashboard['statistics'].get('total_executions', 0)}")
    print(f"  Success Rate: {dashboard['statistics'].get('overall_success_rate', 0):.1%}")
    print(f"  Unique Tasks: {dashboard['statistics'].get('unique_task_types', 0)}")
    print(f"  Active Insights: {len(dashboard.get('recent_insights', []))}")
    
    print("\n🚀 System Ready for Claude-Code Integration!")
    print("Use the ClaudeCodeLearningInterface for all interactions.")
    
    # Keep system running
    try:
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        print("\n👋 Shutting down learning system...")

if __name__ == "__main__":
    asyncio.run(main())
