# Tandem Orchestrator - Quick Start Guide

## 🚀 30-Second Start

```bash
cd $HOME/Documents/Claude/agents/src/python
python3 tandem_orchestrator.py
```

## 📋 Quick Examples

### 1. Simple TUI Message
```python
from tandem_orchestrator import TandemOrchestrator, CommandSet, CommandStep

orchestrator = TandemOrchestrator()
await orchestrator.initialize()

simple_cmd = CommandSet(
    name="Hello TUI",
    steps=[CommandStep(agent="tui", action="display", payload={"msg": "Hello!"})]
)

result = await orchestrator.execute_command_set(simple_cmd)
```

### 2. TUI + DOCGEN Pipeline
```python
doc_pipeline = CommandSet(
    name="Interactive Docs",
    mode=ExecutionMode.INTELLIGENT,
    steps=[
        CommandStep(agent="tui", action="get_input"),
        CommandStep(agent="docgen", action="generate"),
        CommandStep(agent="tui", action="display_results")
    ]
)

result = await orchestrator.execute_command_set(doc_pipeline)
```

### 3. Critical Operation (Redundant)
```python
critical_cmd = CommandSet(
    name="Security Scan",
    mode=ExecutionMode.REDUNDANT,  # Both Python and C
    priority=Priority.CRITICAL,
    steps=[CommandStep(agent="security", action="scan")]
)

result = await orchestrator.execute_command_set(critical_cmd)
```

### 4. Speed-Critical (C Only)
```python
speed_cmd = CommandSet(
    name="Fast Routing",
    mode=ExecutionMode.SPEED_CRITICAL,  # C only - 100K+ msg/sec
    steps=[CommandStep(agent="router", action="route_batch")]
)

result = await orchestrator.execute_command_set(speed_cmd)
```

## 🔧 Essential Modes

| Mode | Use Case | Speed | Intelligence |
|------|----------|-------|--------------|
| INTELLIGENT | Default - best of both | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| REDUNDANT | Critical operations | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| SPEED_CRITICAL | Maximum performance | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| PYTHON_ONLY | ML/AI libraries | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| CONSENSUS | Maximum safety | ⭐⭐ | ⭐⭐⭐⭐⭐ |

## 📊 Check Status

```python
# Get metrics
metrics = orchestrator.get_metrics()
print(f"Messages processed: Python={metrics['python_msgs_processed']}, C={metrics['c_msgs_processed']}")

# Health check
health = await orchestrator.health_check()
print(f"System status: {health['status']}")
```

## 🛠️ Configuration

Quick config via environment:
```bash
export TANDEM_DEFAULT_MODE=INTELLIGENT
export TANDEM_PYTHON_WORKERS=8
export TANDEM_C_BUFFER_SIZE=16777216
```

## 🎯 Ready-Made Workflows

```python
from tandem_orchestrator import StandardWorkflows

# Pre-built workflows
doc_workflow = StandardWorkflows.create_document_generation_workflow()
security_workflow = StandardWorkflows.create_security_audit_workflow()

# Execute
result = await orchestrator.execute_command_set(doc_workflow)
```

## 🔍 Troubleshooting

```bash
# Check if C layer is running
ps aux | grep agent_bridge

# Start C layer if needed
cd ../binary-communications-system
./agent_bridge &

# Check logs
tail -f tandem_orchestrator.log
```

## 📖 Full Documentation

See [TANDEM_ORCHESTRATION_SYSTEM.md](./TANDEM_ORCHESTRATION_SYSTEM.md) for complete reference.