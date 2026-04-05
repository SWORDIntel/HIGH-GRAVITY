#!/usr/bin/env python3
"""
Agent Learning System - Python Implementation
Builds on existing binary communications infrastructure for self-improving agent orchestration
"""

import asyncio
import json
import time
import sqlite3
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
import logging
import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib

logger = logging.getLogger(__name__)

@dataclass
class TaskExecution:
    """Records a task execution for learning"""
    task_id: str
    task_type: str
    agents_used: List[str]
    execution_order: List[str]
    duration: float
    success: bool
    error_message: Optional[str] = None
    user_satisfaction: Optional[int] = None  # 1-10 rating
    complexity_score: float = 0.0
    resource_usage: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AgentPerformance:
    """Tracks individual agent performance"""
    agent_name: str
    success_rate: float = 0.0
    avg_duration: float = 0.0
    error_patterns: List[str] = field(default_factory=list)
    best_combinations: List[List[str]] = field(default_factory=list)
    specialties: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class LearningInsight:
    """Represents a learned pattern or insight"""
    insight_type: str  # "best_combo", "avoid_pattern", "optimization", etc.
    confidence: float  # 0.0 to 1.0
    description: str
    data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)

class AgentLearningSystem:
    """Self-learning system for agent orchestration"""
    
    def __init__(self, db_path: str = "agent_learning.db"):
        self.db_path = db_path
        self.execution_history: List[TaskExecution] = []
        self.agent_performance: Dict[str, AgentPerformance] = {}
        self.insights: List[LearningInsight] = []
        self.models: Dict[str, Any] = {}
        self.setup_database()
        self.load_historical_data()
        
    def setup_database(self):
        """Initialize SQLite database for persistent learning data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Task executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_executions (
                id TEXT PRIMARY KEY,
                task_type TEXT,
                agents_used TEXT,
                execution_order TEXT,
                duration REAL,
                success BOOLEAN,
                error_message TEXT,
                user_satisfaction INTEGER,
                complexity_score REAL,
                resource_usage TEXT,
                timestamp DATETIME
            )
        """)
        
        # Agent performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                agent_name TEXT PRIMARY KEY,
                success_rate REAL,
                avg_duration REAL,
                error_patterns TEXT,
                best_combinations TEXT,
                specialties TEXT,
                last_updated DATETIME
            )
        """)
        
        # Learning insights table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_insights (
                id TEXT PRIMARY KEY,
                insight_type TEXT,
                confidence REAL,
                description TEXT,
                data TEXT,
                created_at DATETIME
            )
        """)
        
        conn.commit()
        conn.close()
        
    def record_execution(self, execution: TaskExecution):
        """Record a task execution for learning"""
        self.execution_history.append(execution)
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO task_executions 
            (id, task_type, agents_used, execution_order, duration, success, 
             error_message, user_satisfaction, complexity_score, resource_usage, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution.task_id,
            execution.task_type,
            json.dumps(execution.agents_used),
            json.dumps(execution.execution_order),
            execution.duration,
            execution.success,
            execution.error_message,
            execution.user_satisfaction,
            execution.complexity_score,
            json.dumps(execution.resource_usage),
            execution.timestamp.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Update agent performance
        self.update_agent_performance(execution)
        
    def update_agent_performance(self, execution: TaskExecution):
        """Update performance metrics for agents involved in execution"""
        for agent in execution.agents_used:
            if agent not in self.agent_performance:
                self.agent_performance[agent] = AgentPerformance(agent_name=agent)
            
            perf = self.agent_performance[agent]
            
            # Update success rate (weighted moving average)
            current_success = 1.0 if execution.success else 0.0
            perf.success_rate = 0.8 * perf.success_rate + 0.2 * current_success
            
            # Update average duration
            perf.avg_duration = 0.8 * perf.avg_duration + 0.2 * execution.duration
            
            # Track error patterns
            if not execution.success and execution.error_message:
                perf.error_patterns.append(execution.error_message)
                # Keep only recent errors
                perf.error_patterns = perf.error_patterns[-10:]
            
            # Track successful combinations
            if execution.success and len(execution.agents_used) > 1:
                combo = sorted(execution.agents_used)
                if combo not in perf.best_combinations:
                    perf.best_combinations.append(combo)
                    perf.best_combinations = perf.best_combinations[-20:]  # Keep top 20
            
            perf.last_updated = datetime.now()
        
        self.save_agent_performance()
        
    def analyze_patterns(self) -> List[LearningInsight]:
        """Analyze execution history to extract patterns and insights"""
        insights = []
        
        if len(self.execution_history) < 10:
            return insights  # Need more data
            
        # 1. Find best agent combinations
        combo_success = defaultdict(list)
        for exec in self.execution_history[-100:]:  # Recent executions
            combo = tuple(sorted(exec.agents_used))
            combo_success[combo].append(exec.success)
        
        for combo, successes in combo_success.items():
            if len(successes) >= 3:  # Minimum sample size
                success_rate = sum(successes) / len(successes)
                if success_rate >= 0.8:  # High success rate
                    insights.append(LearningInsight(
                        insight_type="best_combo",
                        confidence=min(success_rate, len(successes) / 10),
                        description=f"Agent combination {list(combo)} has {success_rate:.1%} success rate",
                        data={"agents": list(combo), "success_rate": success_rate, "sample_size": len(successes)}
                    ))
        
        # 2. Identify problematic patterns
        failed_combos = defaultdict(list)
        for exec in self.execution_history[-100:]:
            if not exec.success:
                combo = tuple(sorted(exec.agents_used))
                failed_combos[combo].append(exec.error_message or "Unknown error")
        
        for combo, errors in failed_combos.items():
            if len(errors) >= 3:  # Multiple failures
                error_pattern = Counter(errors).most_common(1)[0][0]
                insights.append(LearningInsight(
                    insight_type="avoid_pattern",
                    confidence=len(errors) / 10,
                    description=f"Avoid combination {list(combo)} - common error: {error_pattern}",
                    data={"agents": list(combo), "error_pattern": error_pattern, "failure_count": len(errors)}
                ))
        
        # 3. Find optimization opportunities
        slow_tasks = [e for e in self.execution_history if e.duration > 60]  # > 1 minute
        if slow_tasks:
            avg_slow_duration = sum(e.duration for e in slow_tasks) / len(slow_tasks)
            insights.append(LearningInsight(
                insight_type="optimization",
                confidence=0.7,
                description=f"Performance optimization needed - {len(slow_tasks)} slow tasks (avg {avg_slow_duration:.1f}s)",
                data={"slow_task_count": len(slow_tasks), "avg_duration": avg_slow_duration}
            ))
        
        # Store insights
        self.insights.extend(insights)
        self.save_insights(insights)
        
        return insights
    
    def train_prediction_models(self):
        """Train ML models to predict optimal agent selection"""
        if len(self.execution_history) < 50:
            logger.info("Not enough data to train models (need 50+ executions)")
            return
        
        # Prepare training data
        X, y_success, y_duration = [], [], []
        label_encoders = {}
        
        for exec in self.execution_history:
            features = []
            
            # Task type encoding
            if 'task_type' not in label_encoders:
                label_encoders['task_type'] = LabelEncoder()
                task_types = [e.task_type for e in self.execution_history]
                label_encoders['task_type'].fit(task_types)
            
            features.append(label_encoders['task_type'].transform([exec.task_type])[0])
            features.append(len(exec.agents_used))  # Number of agents
            features.append(exec.complexity_score)  # Task complexity
            
            # Agent combination encoding (simplified)
            agent_vector = [0] * 40  # Assume 40 possible agents
            agent_names = ['DIRECTOR', 'ARCHITECT', 'CONSTRUCTOR', 'PATCHER', 'TESTBED', 
                          'SECURITY', 'DATABASE', 'WEB', 'MONITOR', 'DEPLOYER']  # Top 10 common
            
            for i, agent in enumerate(agent_names[:10]):
                if agent in exec.agents_used:
                    agent_vector[i] = 1
            
            features.extend(agent_vector[:10])  # Use only top 10 for now
            
            X.append(features)
            y_success.append(1 if exec.success else 0)
            y_duration.append(exec.duration)
        
        X = np.array(X)
        y_success = np.array(y_success)
        y_duration = np.array(y_duration)
        
        # Train success prediction model
        success_model = RandomForestClassifier(n_estimators=100, random_state=42)
        success_model.fit(X, y_success)
        self.models['success_predictor'] = success_model
        
        # Train duration prediction model
        from sklearn.ensemble import RandomForestRegressor
        duration_model = RandomForestRegressor(n_estimators=100, random_state=42)
        duration_model.fit(X, y_duration)
        self.models['duration_predictor'] = duration_model
        
        # Save models
        self.save_models()
        
        logger.info(f"Trained models on {len(X)} examples")
        
    def predict_optimal_agents(self, task_type: str, complexity: float = 1.0) -> List[str]:
        """Predict optimal agent combination for a task"""
        if 'success_predictor' not in self.models:
            # Fallback to rule-based selection
            return self.rule_based_agent_selection(task_type)
        
        # Use trained model to predict
        best_combo = []
        best_score = -1
        
        # Try different combinations (simplified approach)
        common_combos = [
            ['DIRECTOR', 'ARCHITECT', 'CONSTRUCTOR'],
            ['CONSTRUCTOR', 'PATCHER', 'TESTBED'],
            ['SECURITY', 'TESTBED', 'MONITOR'],
            ['DATABASE', 'APIDESIGNER', 'SECURITY'],
            ['WEB', 'APIDESIGNER', 'TESTBED']
        ]
        
        for combo in common_combos:
            score = self.predict_combo_success(task_type, combo, complexity)
            if score > best_score:
                best_score = score
                best_combo = combo
        
        return best_combo if best_combo else ['DIRECTOR', 'PROJECTORCHESTRATOR']
    
    def predict_combo_success(self, task_type: str, agents: List[str], complexity: float) -> float:
        """Predict success probability for agent combination"""
        if 'success_predictor' not in self.models:
            return 0.5  # Default probability
        
        try:
            # Prepare features (simplified)
            features = [0, len(agents), complexity]  # task_type=0 for now
            agent_vector = [0] * 10
            
            agent_names = ['DIRECTOR', 'ARCHITECT', 'CONSTRUCTOR', 'PATCHER', 'TESTBED', 
                          'SECURITY', 'DATABASE', 'WEB', 'MONITOR', 'DEPLOYER']
            
            for i, agent in enumerate(agent_names):
                if agent in agents:
                    agent_vector[i] = 1
            
            features.extend(agent_vector)
            X = np.array([features])
            
            probability = self.models['success_predictor'].predict_proba(X)[0][1]  # Probability of success
            return probability
            
        except Exception as e:
            logger.error(f"Error predicting success: {e}")
            return 0.5
    
    def rule_based_agent_selection(self, task_type: str) -> List[str]:
        """Fallback rule-based agent selection"""
        rules = {
            'web_development': ['WEB', 'APIDESIGNER', 'DATABASE', 'TESTBED'],
            'security_audit': ['SECURITY', 'SECURITYAUDITOR', 'CRYPTOEXPERT', 'TESTBED'],
            'system_design': ['ARCHITECT', 'DATABASE', 'APIDESIGNER', 'INFRASTRUCTURE'],
            'bug_fix': ['DEBUGGER', 'PATCHER', 'TESTBED', 'LINTER'],
            'deployment': ['DEPLOYER', 'INFRASTRUCTURE', 'MONITOR', 'SECURITY'],
            'default': ['DIRECTOR', 'PROJECTORCHESTRATOR', 'ARCHITECT']
        }
        
        return rules.get(task_type, rules['default'])
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of learning progress and insights"""
        total_executions = len(self.execution_history)
        if total_executions == 0:
            return {"status": "no_data", "message": "No execution history available"}
        
        recent_executions = self.execution_history[-50:]  # Last 50
        success_rate = sum(1 for e in recent_executions if e.success) / len(recent_executions)
        avg_duration = sum(e.duration for e in recent_executions) / len(recent_executions)
        
        # Top performing agents
        agent_scores = {}
        for agent, perf in self.agent_performance.items():
            agent_scores[agent] = perf.success_rate * (1 / max(perf.avg_duration, 0.1))
        
        top_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "status": "learning",
            "total_executions": total_executions,
            "recent_success_rate": success_rate,
            "avg_duration": avg_duration,
            "total_insights": len(self.insights),
            "top_agents": [{"name": name, "score": score} for name, score in top_agents],
            "models_trained": len(self.models),
            "last_analysis": datetime.now().isoformat()
        }
    
    def save_agent_performance(self):
        """Save agent performance to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for agent, perf in self.agent_performance.items():
            cursor.execute("""
                INSERT OR REPLACE INTO agent_performance
                (agent_name, success_rate, avg_duration, error_patterns, best_combinations, 
                 specialties, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                agent,
                perf.success_rate,
                perf.avg_duration,
                json.dumps(perf.error_patterns),
                json.dumps(perf.best_combinations),
                json.dumps(perf.specialties),
                perf.last_updated.isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def save_insights(self, insights: List[LearningInsight]):
        """Save insights to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for insight in insights:
            insight_id = hashlib.md5(f"{insight.description}{insight.created_at}".encode()).hexdigest()
            cursor.execute("""
                INSERT OR REPLACE INTO learning_insights
                (id, insight_type, confidence, description, data, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                insight_id,
                insight.insight_type,
                insight.confidence,
                insight.description,
                json.dumps(insight.data),
                insight.created_at.isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def save_models(self):
        """Save trained models to disk"""
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        
        for name, model in self.models.items():
            model_path = models_dir / f"{name}.joblib"
            joblib.dump(model, model_path)
        
        logger.info(f"Saved {len(self.models)} models to disk")
    
    def load_historical_data(self):
        """Load historical data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load executions
            cursor.execute("SELECT * FROM task_executions ORDER BY timestamp DESC LIMIT 1000")
            for row in cursor.fetchall():
                execution = TaskExecution(
                    task_id=row[0],
                    task_type=row[1],
                    agents_used=json.loads(row[2]),
                    execution_order=json.loads(row[3]),
                    duration=row[4],
                    success=bool(row[5]),
                    error_message=row[6],
                    user_satisfaction=row[7],
                    complexity_score=row[8],
                    resource_usage=json.loads(row[9]) if row[9] else {},
                    timestamp=datetime.fromisoformat(row[10])
                )
                self.execution_history.append(execution)
            
            # Load agent performance
            cursor.execute("SELECT * FROM agent_performance")
            for row in cursor.fetchall():
                perf = AgentPerformance(
                    agent_name=row[0],
                    success_rate=row[1],
                    avg_duration=row[2],
                    error_patterns=json.loads(row[3]) if row[3] else [],
                    best_combinations=json.loads(row[4]) if row[4] else [],
                    specialties=json.loads(row[5]) if row[5] else [],
                    last_updated=datetime.fromisoformat(row[6])
                )
                self.agent_performance[row[0]] = perf
            
            conn.close()
            
            # Load models
            models_dir = Path("models")
            if models_dir.exists():
                for model_file in models_dir.glob("*.joblib"):
                    model_name = model_file.stem
                    self.models[model_name] = joblib.load(model_file)
            
            logger.info(f"Loaded {len(self.execution_history)} executions, {len(self.agent_performance)} agent performances, {len(self.models)} models")
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")

# Integration with existing orchestrator
class LearningEnabledOrchestrator:
    """Orchestrator with integrated learning system"""
    
    def __init__(self):
        self.learning_system = AgentLearningSystem()
        # Initialize your existing orchestrator here
        
    async def execute_task(self, task_type: str, description: str, **kwargs) -> Dict[str, Any]:
        """Execute task with learning integration"""
        task_id = hashlib.md5(f"{task_type}_{description}_{time.time()}".encode()).hexdigest()
        
        # Get optimal agents from learning system
        agents = self.learning_system.predict_optimal_agents(task_type, kwargs.get('complexity', 1.0))
        
        start_time = time.time()
        success = False
        error_message = None
        
        try:
            # Execute with your existing orchestrator
            result = await self._execute_with_agents(agents, task_type, description, **kwargs)
            success = True
            return result
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Task execution failed: {e}")
            raise
            
        finally:
            # Record execution for learning
            duration = time.time() - start_time
            execution = TaskExecution(
                task_id=task_id,
                task_type=task_type,
                agents_used=agents,
                execution_order=agents,  # Simplified
                duration=duration,
                success=success,
                error_message=error_message,
                complexity_score=kwargs.get('complexity', 1.0)
            )
            
            self.learning_system.record_execution(execution)
            
            # Periodic learning
            if len(self.learning_system.execution_history) % 10 == 0:
                asyncio.create_task(self._periodic_learning())
    
    async def _periodic_learning(self):
        """Run periodic learning analysis"""
        try:
            insights = self.learning_system.analyze_patterns()
            if insights:
                logger.info(f"Generated {len(insights)} new insights")
            
            # Retrain models periodically
            if len(self.learning_system.execution_history) % 50 == 0:
                self.learning_system.train_prediction_models()
                
        except Exception as e:
            logger.error(f"Error in periodic learning: {e}")
    
    async def _execute_with_agents(self, agents: List[str], task_type: str, description: str, **kwargs):
        """Execute task with specified agents (integrate with your existing system)"""
        # This is where you'd integrate with your existing production_orchestrator.py
        # For now, simulate execution
        await asyncio.sleep(1)  # Simulate work
        return {"status": "success", "agents_used": agents, "result": "Task completed"}

if __name__ == "__main__":
    # Demo usage
    async def demo():
        orchestrator = LearningEnabledOrchestrator()
        
        # Simulate some executions
        await orchestrator.execute_task("web_development", "Create login page", complexity=2.0)
        await orchestrator.execute_task("security_audit", "Review authentication", complexity=3.0)
        await orchestrator.execute_task("bug_fix", "Fix memory leak", complexity=1.5)
        
        # Get learning summary
        summary = orchestrator.learning_system.get_learning_summary()
        print(json.dumps(summary, indent=2))
    
    asyncio.run(demo())