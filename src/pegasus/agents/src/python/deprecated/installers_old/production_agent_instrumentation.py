#!/usr/bin/env python3
"""
Production Agent Instrumentation System v1.0
Deploy enterprise instrumentation for all 89 agents

Transforms pathetic 4-record data collection into enterprise intelligence:
- Real-time agent execution tracking
- Workflow pattern analysis
- Performance intelligence
- Repository activity monitoring
- User journey intelligence
"""

import os
import sys
import time
import uuid
import functools
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import inspect

# Import enterprise learning system
try:
    from enterprise_learning_orchestrator import (
        EnterpriseLearningOrchestrator,
        AgentExecution,
        WorkflowPattern,
        PerformanceMetric,
        initialize_enterprise_learning
    )
except ImportError:
    print("❌ Enterprise learning orchestrator not found")
    sys.exit(1)

class ProductionAgentInstrumentation:
    """Production-grade instrumentation for 89-agent ecosystem"""

    def __init__(self):
        self.orchestrator = initialize_enterprise_learning()
        self.active_sessions = {}
        self.workflow_tracking = {}
        self.agent_registry = self._discover_agents()
        self.instrumentation_active = True

        print(f"🚀 Production Agent Instrumentation ACTIVATED")
        print(f"📊 Discovered {len(self.agent_registry)} agents")
        print(f"🎯 Target: 2,000-5,000 records/day from {len(self.agent_registry)} agents")

    def _discover_agents(self) -> Dict[str, Dict]:
        """Discover all 89 agents in the ecosystem"""
        agents_dir = "${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents"
        agent_registry = {}

        if not os.path.exists(agents_dir):
            print(f"❌ Agents directory not found: {agents_dir}")
            return {}

        for file in os.listdir(agents_dir):
            if file.endswith('.md') and file != 'Template.md':
                agent_name = file.replace('.md', '').upper()
                agent_path = os.path.join(agents_dir, file)

                # Extract agent metadata
                agent_info = self._extract_agent_metadata(agent_path)
                agent_registry[agent_name] = agent_info

        return agent_registry

    def _extract_agent_metadata(self, agent_path: str) -> Dict:
        """Extract agent metadata from .md files"""
        try:
            with open(agent_path, 'r') as f:
                content = f.read()

            # Extract basic info (simplified for production)
            metadata = {
                'file_path': agent_path,
                'category': 'UNKNOWN',
                'priority': 'MEDIUM',
                'status': 'ACTIVE'
            }

            # Parse YAML frontmatter for metadata
            if '---' in content:
                yaml_section = content.split('---')[1] if len(content.split('---')) > 1 else ''

                for line in yaml_section.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip().strip('"\'')

                        if key in ['category', 'priority', 'status', 'name']:
                            metadata[key] = value

            return metadata

        except Exception as e:
            print(f"⚠️  Failed to parse agent metadata for {agent_path}: {e}")
            return {'category': 'UNKNOWN', 'priority': 'LOW', 'status': 'ERROR'}

    def instrument_agent_execution(self, agent_name: str, task_type: str = 'unknown'):
        """Decorator for automatic agent execution instrumentation"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.instrumentation_active:
                    return func(*args, **kwargs)

                # Generate session tracking
                session_id = str(uuid.uuid4())
                start_time = time.time()

                # Estimate input size
                input_size = self._estimate_size(args) + self._estimate_size(kwargs)

                try:
                    # Execute function
                    result = func(*args, **kwargs)
                    execution_time = int((time.time() - start_time) * 1000)

                    # Estimate output size
                    output_size = self._estimate_size(result)

                    # Record successful execution
                    execution = AgentExecution(
                        agent_name=agent_name.upper(),
                        task_type=task_type,
                        execution_time_ms=execution_time,
                        memory_usage_mb=self._get_memory_usage(),
                        cpu_usage_percent=self._get_cpu_usage(),
                        success=True,
                        input_size_bytes=input_size,
                        output_size_bytes=output_size,
                        session_id=session_id,
                        user_id=self._get_current_user(),
                        repository_path=self._get_repository_context()
                    )

                    if self.orchestrator:
                        self.orchestrator.record_agent_execution(execution)

                    # Track for workflow analysis
                    self._track_workflow_pattern(agent_name, session_id, execution_time, True)

                    return result

                except Exception as e:
                    execution_time = int((time.time() - start_time) * 1000)

                    # Record failed execution
                    execution = AgentExecution(
                        agent_name=agent_name.upper(),
                        task_type=task_type,
                        execution_time_ms=execution_time,
                        success=False,
                        error_message=str(e)[:500],  # Limit error message length
                        input_size_bytes=input_size,
                        session_id=session_id,
                        user_id=self._get_current_user(),
                        repository_path=self._get_repository_context()
                    )

                    if self.orchestrator:
                        self.orchestrator.record_agent_execution(execution)

                    # Track failed workflow
                    self._track_workflow_pattern(agent_name, session_id, execution_time, False)

                    raise

            return wrapper
        return decorator

    def _track_workflow_pattern(self, agent_name: str, session_id: str, execution_time: int, success: bool):
        """Track workflow patterns for enterprise intelligence"""
        workflow_key = f"workflow_{int(time.time() // 300)}"  # 5-minute windows

        if workflow_key not in self.workflow_tracking:
            self.workflow_tracking[workflow_key] = {
                'workflow_id': str(uuid.uuid4()),
                'agents': [],
                'start_time': time.time(),
                'executions': [],
                'success_count': 0,
                'total_count': 0
            }

        workflow = self.workflow_tracking[workflow_key]
        workflow['agents'].append(agent_name)
        workflow['executions'].append({
            'agent': agent_name,
            'duration': execution_time,
            'success': success,
            'timestamp': time.time()
        })
        workflow['total_count'] += 1
        if success:
            workflow['success_count'] += 1

        # Complete workflow if enough activity
        if len(workflow['executions']) >= 3:
            self._finalize_workflow_pattern(workflow_key, workflow)

    def _finalize_workflow_pattern(self, workflow_key: str, workflow: Dict):
        """Finalize and record workflow pattern"""
        try:
            total_duration = int((time.time() - workflow['start_time']) * 1000)
            success_rate = workflow['success_count'] / workflow['total_count'] if workflow['total_count'] > 0 else 0

            # Determine pattern type
            unique_agents = list(set(workflow['agents']))
            pattern_type = self._classify_workflow_pattern(unique_agents, workflow['executions'])

            # Calculate complexity
            complexity_score = len(unique_agents) + (len(workflow['executions']) // 2)

            pattern = WorkflowPattern(
                workflow_id=workflow['workflow_id'],
                pattern_type=pattern_type,
                agent_sequence=unique_agents,
                total_duration_ms=total_duration,
                success_rate=success_rate,
                complexity_score=complexity_score,
                repository_context=self._get_repository_context(),
                task_category=self._classify_task_category(unique_agents),
                parallel_execution=len(unique_agents) > 1,
                dependency_count=len(workflow['executions']) - len(unique_agents)
            )

            if self.orchestrator:
                self.orchestrator.record_workflow_pattern(pattern)

            # Clean up
            del self.workflow_tracking[workflow_key]

        except Exception as e:
            print(f"⚠️  Failed to finalize workflow pattern: {e}")

    def _classify_workflow_pattern(self, agents: List[str], executions: List[Dict]) -> str:
        """Classify workflow pattern for enterprise intelligence"""
        if len(agents) == 1:
            return "single_agent_task"
        elif len(agents) <= 3:
            return "simple_coordination"
        elif len(agents) <= 6:
            return "complex_workflow"
        else:
            return "enterprise_orchestration"

    def _classify_task_category(self, agents: List[str]) -> str:
        """Classify task category based on agents involved"""
        agent_categories = []
        for agent in agents:
            if agent in self.agent_registry:
                category = self.agent_registry[agent].get('category', 'UNKNOWN')
                agent_categories.append(category)

        # Determine primary category
        if 'SECURITY' in agent_categories:
            return "security_operations"
        elif 'INFRASTRUCTURE' in agent_categories:
            return "infrastructure_management"
        elif 'DEVELOPMENT' in agent_categories:
            return "development_workflow"
        elif 'STRATEGIC' in agent_categories:
            return "strategic_planning"
        else:
            return "general_coordination"

    def record_performance_metric(self, metric_name: str, value: float,
                                 category: str = "system_performance",
                                 agent_name: Optional[str] = None,
                                 unit: Optional[str] = None,
                                 severity: int = 1):
        """Record performance metric for enterprise intelligence"""
        if not self.orchestrator:
            return False

        metric = PerformanceMetric(
            metric_category=category,
            metric_name=metric_name,
            metric_value=value,
            unit=unit,
            agent_name=agent_name,
            severity_level=severity,
            correlation_id=str(uuid.uuid4())
        )

        return self.orchestrator.record_performance_metric(metric)

    def _estimate_size(self, obj) -> int:
        """Estimate object size in bytes"""
        try:
            if hasattr(obj, '__len__'):
                return len(str(obj))
            else:
                return len(str(obj))
        except:
            return 0

    def _get_memory_usage(self) -> Optional[int]:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return int(process.memory_info().rss / (1024 * 1024))
        except:
            return None

    def _get_cpu_usage(self) -> Optional[float]:
        """Get current CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except:
            return None

    def _get_current_user(self) -> str:
        """Get current user identifier"""
        return os.getenv('USER', 'system_user')

    def _get_repository_context(self) -> Optional[str]:
        """Get current repository context"""
        try:
            cwd = os.getcwd()
            if 'claude-backups' in cwd:
                return cwd
            return None
        except:
            return None

    def get_instrumentation_statistics(self) -> Dict[str, Any]:
        """Get real-time instrumentation statistics"""
        if not self.orchestrator:
            return {"error": "Orchestrator not available"}

        try:
            dashboard = self.orchestrator.get_enterprise_dashboard()

            stats = {
                "agents_discovered": len(self.agent_registry),
                "instrumentation_active": self.instrumentation_active,
                "active_workflows": len(self.workflow_tracking),
                "enterprise_dashboard": dashboard
            }

            return stats

        except Exception as e:
            return {"error": f"Failed to get statistics: {e}"}

    def shutdown(self):
        """Graceful shutdown of instrumentation system"""
        print("🔄 Shutting down Production Agent Instrumentation...")
        self.instrumentation_active = False

        if self.orchestrator:
            self.orchestrator.shutdown()

        print("✅ Production Agent Instrumentation shutdown complete")

# Global instrumentation instance
production_instrumentation = None

def initialize_production_instrumentation():
    """Initialize production agent instrumentation"""
    global production_instrumentation
    try:
        production_instrumentation = ProductionAgentInstrumentation()
        return production_instrumentation
    except Exception as e:
        print(f"❌ Failed to initialize production instrumentation: {e}")
        return None

# Convenience decorators for agent developers
def track_agent_execution(agent_name: str, task_type: str = 'task'):
    """Simple decorator for agent execution tracking"""
    def decorator(func):
        if production_instrumentation:
            return production_instrumentation.instrument_agent_execution(agent_name, task_type)(func)
        return func
    return decorator

def track_performance(metric_name: str, category: str = "performance", unit: str = "ms"):
    """Decorator for performance metric tracking"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000

                if production_instrumentation:
                    production_instrumentation.record_performance_metric(
                        metric_name=metric_name,
                        value=execution_time,
                        category=category,
                        unit=unit
                    )

                return result
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000

                if production_instrumentation:
                    production_instrumentation.record_performance_metric(
                        metric_name=f"{metric_name}_failed",
                        value=execution_time,
                        category=category,
                        unit=unit,
                        severity=3
                    )

                raise
        return wrapper
    return decorator

if __name__ == "__main__":
    # Production instrumentation demonstration
    instrumentation = initialize_production_instrumentation()

    if instrumentation:
        print("\n🔥 PRODUCTION AGENT INSTRUMENTATION DEMONSTRATION")

        # Example: Simulate enterprise agent coordination
        @track_agent_execution("DIRECTOR", "strategic_planning")
        def director_planning():
            time.sleep(0.1)  # Simulate work
            return "Strategic plan created"

        @track_agent_execution("ARCHITECT", "system_design")
        def architect_design():
            time.sleep(0.05)  # Simulate work
            return "System architecture designed"

        @track_agent_execution("CONSTRUCTOR", "implementation")
        def constructor_build():
            time.sleep(0.08)  # Simulate work
            return "System implemented"

        @track_performance("workflow_coordination", "orchestration", "ms")
        def enterprise_workflow():
            # Simulate enterprise multi-agent workflow
            result1 = director_planning()
            result2 = architect_design()
            result3 = constructor_build()
            return [result1, result2, result3]

        # Execute enterprise workflow
        print("📊 Executing enterprise workflow simulation...")
        for i in range(3):
            try:
                results = enterprise_workflow()
                print(f"   ✅ Workflow {i+1}/3 completed: {len(results)} agents coordinated")
            except Exception as e:
                print(f"   ❌ Workflow {i+1}/3 failed: {e}")

        time.sleep(2)  # Allow processing

        # Show instrumentation statistics
        stats = instrumentation.get_instrumentation_statistics()
        print(f"\n📈 PRODUCTION INSTRUMENTATION STATISTICS:")
        print(f"   🤖 Agents Discovered: {stats.get('agents_discovered', 'N/A')}")
        print(f"   🔄 Active Workflows: {stats.get('active_workflows', 'N/A')}")
        print(f"   📊 Enterprise Intelligence: Active")

        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            instrumentation.shutdown()
            print("✅ Production instrumentation demonstration complete")