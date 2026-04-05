---
name: Readme Learning System
---
# PostgreSQL Agent Learning System v2.0

A PostgreSQL 17-powered self-improving AI orchestration system that learns from agent execution patterns to optimize performance over time. Fully integrated with the existing `claude_auth` database for persistent learning across sessions.

## 🚀 **What It Does**

The learning system analyzes every agent execution to:
- **Learn optimal agent combinations** for different task types
- **Predict success rates** using machine learning models
- **Identify problematic patterns** and suggest improvements
- **Adapt execution strategies** based on historical performance
- **Generate actionable insights** for system optimization

## 📊 **Key Features**

### 🧠 **Machine Learning Models**
- **Success Prediction**: Predicts likelihood of task success
- **Duration Estimation**: Estimates execution time 
- **Agent Recommendation**: Suggests optimal agent combinations
- **Pattern Recognition**: Identifies success and failure patterns

### 📈 **Performance Tracking**
- **Agent Performance Metrics**: Success rates, average durations, error patterns
- **Task Execution History**: Complete audit trail of all executions
- **Insight Generation**: Automated discovery of optimization opportunities
- **Adaptive Thresholds**: Dynamic adjustment based on performance

### 🔄 **Integration**
- **Binary Communication Ready**: Leverages existing binary infrastructure
- **Python-First Fallback**: Works immediately in Python mode
- **Production Orchestrator Bridge**: Seamless integration with existing system
- **Real-time Learning**: Continuous improvement during operation

## 🛠 **Installation**

### PostgreSQL Database Configuration
The system uses the self-contained PostgreSQL database:
- **Database**: `claude_auth`
- **User**: `claude_auth`
- **Password**: `claude_auth_pass`

### Quick Setup
```bash
# Run the PostgreSQL setup script
cd $HOME/Documents/Claude/agents/src/python
python3 setup_learning_system.py

# This will:
# - Install dependencies (psycopg2-binary, asyncpg, numpy, scikit-learn, joblib)
# - Connect to PostgreSQL claude_auth database
# - Create learning schema and tables
# - Initialize all 40 agents
# - Set up PostgreSQL functions
# - Run initial tests
# - Create postgresql-learning launcher script
```

## 🎯 **Quick Start**

### 1. **Check Status**
```bash
./postgresql-learning status
```

### 2. **Run Tests**
```bash
./postgresql-learning test
```

### 3. **Access CLI Interface**
```bash
# View comprehensive dashboard
./postgresql-learning cli dashboard

# Simulate executions
./postgresql-learning cli simulate web_development 10
./postgresql-learning cli simulate security_audit 5

# Analyze patterns
./postgresql-learning cli analyze

# View insights
./postgresql-learning cli insights
```

### 4. **Direct SQL Access**
```bash
# Connect to database
psql -U claude_auth -d claude_auth

# Check learning metrics
SELECT COUNT(*) as total_executions,
       AVG(duration_seconds) as avg_duration,
       SUM(CASE WHEN success THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as success_rate
FROM agent_task_executions;
```

## 🔧 **Integration with Existing System**

### **Option 1: Enhanced Orchestrator (Recommended)**
```python
from learning_orchestrator_bridge import EnhancedLearningOrchestrator

orchestrator = EnhancedLearningOrchestrator()
await orchestrator.initialize()

result = await orchestrator.execute_with_learning(
    task_description="Create user authentication",
    task_type="web_development", 
    complexity=2.5
)
```

### **Option 2: Direct Learning System**
```python
from agent_learning_system import AgentLearningSystem

learning = AgentLearningSystem()

# Get agent recommendations
agents = learning.predict_optimal_agents("security_audit", complexity=3.0)

# Record execution results
execution = TaskExecution(
    task_id="unique_id",
    task_type="security_audit",
    agents_used=agents,
    duration=45.2,
    success=True
)
learning.record_execution(execution)
```

### **Option 3: Modify Existing Orchestrator**
```python
# In your production_orchestrator.py
from agent_learning_system import AgentLearningSystem

class ProductionOrchestrator:
    def __init__(self):
        self.learning = AgentLearningSystem()
        # ... existing code ...
    
    async def execute_command_set(self, command_set):
        # Get learned optimizations
        if hasattr(command_set, 'task_type'):
            recommended_agents = self.learning.predict_optimal_agents(
                command_set.task_type
            )
            # Apply recommendations...
        
        # Execute normally
        result = await super().execute_command_set(command_set)
        
        # Record for learning
        # ... record execution ...
        
        return result
```

## 📊 **How Learning Works**

### **1. Data Collection**
Every task execution is recorded with:
- Task type and complexity
- Agents used and execution order
- Duration and success/failure
- Error messages and resource usage

### **2. Pattern Analysis**
The system automatically identifies:
- **Best Combinations**: Agent combinations with high success rates
- **Problematic Patterns**: Combinations that frequently fail
- **Performance Bottlenecks**: Slow or resource-intensive patterns
- **Optimization Opportunities**: Areas for improvement

### **3. Model Training**
Machine learning models are trained on historical data to:
- Predict task success probability
- Estimate execution duration  
- Recommend optimal agent combinations
- Classify task complexity

### **4. Adaptive Optimization**
The system continuously adapts by:
- Adjusting agent selection based on learned patterns
- Modifying execution strategies for better performance
- Updating confidence thresholds based on results
- Generating new insights from emerging patterns

## 📈 **Learning Insights Examples**

```json
{
  "insight_type": "best_combo",
  "confidence": 0.85,
  "description": "Agent combination [SECURITY, TESTBED, MONITOR] has 90% success rate",
  "data": {
    "agents": ["SECURITY", "TESTBED", "MONITOR"],
    "success_rate": 0.90,
    "sample_size": 20
  }
}
```

```json
{
  "insight_type": "avoid_pattern", 
  "confidence": 0.75,
  "description": "Avoid combination [CONSTRUCTOR, DEPLOYER] - common error: dependency conflict",
  "data": {
    "agents": ["CONSTRUCTOR", "DEPLOYER"],
    "error_pattern": "dependency conflict",
    "failure_count": 8
  }
}
```

## 🎛 **CLI Commands**

| Command | Description | Example |
|---------|-------------|---------|
| `status` | Show system status | `./learning-system status` |
| `insights` | Show recent insights | `./learning-system insights` |
| `analyze` | Run learning analysis | `./learning-system analyze` |
| `dashboard` | Comprehensive dashboard | `./learning-system dashboard` |
| `simulate` | Simulate executions | `./learning-system simulate security_audit 10` |
| `predict` | Predict optimal agents | `./learning-system predict web_development 2.0` |
| `export` | Export learning data | `./learning-system export data.json` |

## 🔍 **Monitoring & Analytics**

### **Learning Dashboard**
```bash
./learning-system dashboard
```

Shows:
- Overall system health
- Success rate trends  
- Agent performance rankings
- Recent insights
- Model prediction accuracy
- Resource utilization patterns

### **Performance Metrics**
- **Success Rate**: Percentage of successful executions
- **Average Duration**: Mean execution time
- **Agent Efficiency**: Performance score per agent
- **Insight Generation**: Rate of new pattern discovery
- **Model Accuracy**: Prediction correctness

## 🧪 **Advanced Features**

### **Custom Task Types**
Define your own task categories:
```python
# The system will learn patterns specific to your task types
await orchestrator.execute_with_learning(
    "Optimize database queries",
    task_type="database_optimization",
    complexity=3.5
)
```

### **User Feedback Integration**
```python
execution = TaskExecution(
    task_id="task_123",
    user_satisfaction=8,  # 1-10 rating
    # ... other fields ...
)
learning.record_execution(execution)
```

### **Resource-Aware Learning**
```python
execution = TaskExecution(
    resource_usage={
        "cpu_percent": 75.5,
        "memory_mb": 512,
        "duration_seconds": 42.3
    },
    # ... other fields ...
)
```

## 🔒 **Data & Privacy**

- **PostgreSQL Storage**: All learning data stored in PostgreSQL 17 database
- **No External Calls**: Learning happens entirely offline
- **Data Export**: Full control over data export/import via SQL or CLI
- **Configurable Retention**: Adjust how long data is kept
- **Secure Credentials**: Uses dedicated `claude_auth` user with limited privileges

## 🚦 **Production Deployment**

### **Gradual Rollout**
1. **Start in observation mode** - collect data without changing behavior
2. **Enable low-confidence recommendations** - apply only obvious optimizations
3. **Increase adaptation threshold** - apply more learned patterns as confidence grows
4. **Full learning mode** - let the system optimize autonomously

### **Monitoring**
- Track learning system performance alongside agent performance
- Monitor for degradation if learned patterns perform poorly
- Set up alerts for learning system health

### **Rollback Strategy**
- Disable learning with single flag: `learning_enabled = False`
- Export current learning state before major changes
- Keep baseline performance metrics for comparison

## 🤝 **Contributing**

The learning system is designed to be extensible:

- **Custom Metrics**: Add your own performance indicators
- **New Insight Types**: Define additional pattern recognition
- **Enhanced Models**: Integrate more sophisticated ML algorithms
- **Visualization**: Build dashboards and reporting tools

## 📚 **Technical Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Task Request  │────│  Learning Bridge │────│ Production      │
│                 │    │                  │    │ Orchestrator    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Learning System  │
                       │ - Data Collection│
                       │ - Pattern Analysis│
                       │ - Model Training │
                       │ - Predictions    │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ PostgreSQL 17    │
                       │ claude_auth DB   │
                       │ - Learning Tables│
                       │ - Agent Metadata │
                       │ - Stored Procs   │
                       └──────────────────┘
```

### Database Schema Overview
- **agent_metadata**: All 40 agents with capabilities and performance metrics
- **agent_task_executions**: Complete history of task executions
- **agent_collaboration_patterns**: Learned agent combinations
- **learning_insights**: Generated insights and patterns
- **agent_performance_metrics**: Per-agent performance statistics

## 🔮 **Future Enhancements**

- **Federated Learning**: Share insights across multiple deployments
- **Real-time Model Updates**: Hot-swap models without restart
- **A/B Testing**: Compare different orchestration strategies  
- **Anomaly Detection**: Identify unusual execution patterns
- **Resource Prediction**: Predict and optimize resource usage
- **Multi-objective Optimization**: Balance speed, accuracy, and resource usage

---

**Ready to make your agent system learn and improve itself? Run the setup and start collecting intelligence! 🚀**