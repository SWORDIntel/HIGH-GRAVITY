# Pegasus Orchestrator & E2E Code Audit System

**Version:** 2.0  
**Date:** 2026-04-19  
**Status:** ✅ Fully Operational

## Overview

The Pegasus Orchestrator provides centralized command and control for all agents with:
- **Random API Key Assignment** - Each agent gets a random Gemini API key
- **E2E Code Auditing** - Comprehensive codebase security and quality analysis
- **Task Distribution** - Automatic task assignment across swarm
- **Agent Registry** - Central tracking of all agents and their capabilities

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PEGASUS ORCHESTRATOR                         │
│  ┌───────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  API Key Pool │  │ Agent Registry│  │  Task Queue        │  │
│  │  (19 keys)    │  │  (All agents) │  │  (Distributed)     │  │
│  └───────────────┘  └──────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │         AGENT SWARM (Random Keys)           │
        ├─────────────┬─────────────┬─────────────────┤
        │ SECURITY-a1 │ ANALYST-b2  │ RECON-c3        │
        │ Key: AIza.. │ Key: AIza.. │ Key: AIza...    │
        └─────────────┴─────────────┴─────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │          E2E CODE AUDIT TASKS               │
        ├─────────────────────────────────────────────┤
        │ • Security Scan                             │
        │ • Code Quality Analysis                     │
        │ • Dependency CVE Check                      │
        │ • Secret Detection                          │
        │ • API Key Audit                             │
        │ • Permission Check                          │
        │ • Import Analysis                           │
        │ • Dead Code Detection                       │
        └─────────────────────────────────────────────┘
```

## Features

### 🔑 Random API Key Assignment

Every agent spawned receives a **random Gemini API key** from the pool:

```python
# Automatic on spawn
agent_id = spawn_agent("SECURITY", "Audit task")
# Agent receives: AIzaSyBMAvo9xWuzFN4u...bIWYMczM8E (random)

# Manual rotation
rotate_agent_key(agent_id)
# Agent receives: AIzaSyDEDyD7mQHamBGj...R9bembXCcg (new random)
```

**Benefits:**
- Load distribution across API keys
- Rate limit avoidance
- Anonymity and isolation
- Automatic failover

### 🔍 E2E Code Audit

Comprehensive codebase analysis with 8 parallel audit tasks:

| Task | Description | Output |
|------|-------------|--------|
| **SECURITY_SCAN** | Vulnerability detection | CVE list, exploits |
| **CODE_QUALITY** | Pattern analysis | Quality score, issues |
| **DEPENDENCY_CHECK** | CVE scanning | Vulnerable packages |
| **SECRET_DETECTION** | Hardcoded secrets | API keys, tokens |
| **API_AUDIT** | Key usage analysis | Key locations, exposure |
| **PERMISSION_CHECK** | File permissions | Insecure permissions |
| **IMPORT_ANALYSIS** | Dependency chains | Import graph |
| **DEAD_CODE** | Unused code detection | Dead functions/files |

### 📊 Orchestrator Dashboard

Press **E** in `hg.py` to view:

```
┌─ Pegasus Orchestrator ─────────────────┐
│ Status          Active                 │
│ Active Agents   5                      │
│ Registered      12                     │
│ Available Keys  19                     │
│ Queued Tasks    3                      │
│ Assigned Tasks  8                      │
│ Active Audits   1                      │
│ GSL             Memory-mapped          │
│ Auto-Tasker     Running                │
│ Agents          SECURITY-a1b2c3, ...   │
└────────────────────────────────────────┘
```

## Usage

### Dashboard Controls

| Key | Action | Description |
|-----|--------|-------------|
| **E** | Toggle Pegasus | Show orchestrator panel |
| **1** | Spawn Agent | Create agent with random key |
| **2** | Checkpoint | Save swarm state |
| **3** | Terminate | Shutdown all agents |
| **4** | E2E Audit | Start code audit |

### Spawn Agent with Random Key

```bash
# From dashboard
python3 hg.py
# Press 1

# Agent spawned with random API key from pool
# Example: SECURITY-a1b2c3 assigned AIzaSyBMAvo9xWuzFN4u...
```

### Initiate E2E Code Audit

```bash
# From dashboard
python3 hg.py
# Press 4

# Or programmatically
python3 -c "
from src.pegasus.subagent_manager import SubAgentManager
mgr = SubAgentManager()
audit_id = mgr.initiate_code_audit('.')
print(f'Audit started: {audit_id}')
"
```

### Check Audit Status

```python
from src.pegasus.orchestrator import PegasusOrchestrator

orch = PegasusOrchestrator()
audit_id = "AUDIT-20260419032200"

# Get status
status = orch.get_audit_status(audit_id)
print(f"Progress: {status['progress']}")
print(f"Completion: {status['completion_pct']}%")

# Generate report
report = orch.generate_audit_report(audit_id)
print(report)
```

## API Reference

### PegasusOrchestrator

```python
class PegasusOrchestrator:
    def __init__(self, keys_file: Optional[Path] = None)
    
    # Key Management
    def assign_random_key(self, agent_id: str) -> str
    def rotate_agent_key(self, agent_id: str) -> str
    
    # Agent Management
    def register_agent(self, agent_id: str, role: str, capabilities: List[str]) -> Dict
    def get_agent_config(self, agent_id: str) -> Optional[Dict]
    
    # Task Management
    def dispatch_task(self, task_type: str, target: str, priority: int = 5) -> str
    def assign_task_to_agent(self, task_id: str, agent_id: str) -> bool
    def auto_distribute_tasks(self)
    
    # Audit System
    def initiate_e2e_code_audit(self, target_path: str = ".") -> str
    def get_audit_status(self, audit_id: str) -> Optional[Dict]
    def generate_audit_report(self, audit_id: str) -> str
    
    # Status & Monitoring
    def get_swarm_status(self) -> Dict
    def export_agent_configs(self, output_file: Path)
```

### SubAgentManager Integration

```python
class SubAgentManager:
    # Orchestrator-aware spawning
    def spawn_agent(self, role: str, prompt: str, source: str = "HUMAN") -> str
    # Returns agent_id with random API key assigned
    
    # E2E Audit
    def initiate_code_audit(self, target_path: str = ".") -> str
    def get_audit_status(self, audit_id: str) -> dict
    def get_orchestrator_status(self) -> dict
```

## Audit Report Example

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    PEGASUS E2E CODE AUDIT REPORT                         ║
╚══════════════════════════════════════════════════════════════════════════╝

Audit ID:       AUDIT-20260419032200
Target:         .
Started:        2026-04-19T03:22:00
Status:         in_progress
Progress:       5/8 (62.5%)

Task Breakdown:
  [COMPLETED ] SECURITY_SCAN         - TASK-20260419032200-1234
  [COMPLETED ] CODE_QUALITY          - TASK-20260419032200-1235
  [COMPLETED ] DEPENDENCY_CHECK      - TASK-20260419032200-1236
  [COMPLETED ] SECRET_DETECTION      - TASK-20260419032200-1237
  [ASSIGNED  ] API_AUDIT             - TASK-20260419032200-1238
  [ASSIGNED  ] PERMISSION_CHECK      - TASK-20260419032200-1239
  [QUEUED    ] IMPORT_ANALYSIS       - TASK-20260419032200-1240
  [QUEUED    ] DEAD_CODE             - TASK-20260419032200-1241

Total Tasks: 8
==============================================================================
```

## Agent Configuration Example

```json
{
  "agent_id": "SECURITY-a1b2c3",
  "role": "SECURITY",
  "capabilities": ["scan", "audit", "exploit"],
  "api_key": "AIzaSyBMAvo9xWuzFN4u...bIWYMczM8E",
  "status": "active",
  "tasks_completed": 12,
  "registered_at": "2026-04-19T03:22:00",
  "last_heartbeat": "2026-04-19T03:25:00"
}
```

## Security Features

### 🔒 Key Isolation
- Each agent operates with its own API key
- No key sharing between agents
- Automatic key rotation on demand

### 🌐 Network Anonymization
- VPN rotation per agent
- Geo-distributed spawning
- Traffic isolation

### 🛡️ Governance
- Delegation engine validates spawn requests
- Veto system for critical operations
- Resource lock management

## Performance

- **Key Pool**: 19 active Gemini API keys
- **Parallel Tasks**: Up to 8 simultaneous audit tasks
- **Agent Capacity**: Unlimited (hardware-limited)
- **Task Queue**: Unbounded with auto-distribution
- **GSL Latency**: O(1) memory-mapped operations

## Troubleshooting

### No API Keys Available
```bash
# Check keys file
cat config/gemini_keys.json | jq '.keys[] | select(.status=="active") | .key'

# Verify orchestrator loaded keys
python3 -c "from src.pegasus.orchestrator import PegasusOrchestrator; \
    orch = PegasusOrchestrator(); \
    print(f'Keys loaded: {len(orch.api_keys)}')"
```

### Audit Not Starting
```bash
# Check agent availability
python3 -c "from src.pegasus.subagent_manager import SubAgentManager; \
    mgr = SubAgentManager(); \
    status = mgr.get_orchestrator_status(); \
    print(status)"
```

### Task Distribution Failing
```bash
# Manually trigger distribution
python3 -c "from src.pegasus.orchestrator import PegasusOrchestrator; \
    orch = PegasusOrchestrator(); \
    orch.auto_distribute_tasks()"
```

## Files

- **Orchestrator**: `src/pegasus/orchestrator.py`
- **SubAgent Manager**: `src/pegasus/subagent_manager.py`
- **Dashboard**: `hg.py`
- **Keys Config**: `config/gemini_keys.json`
- **Documentation**: `docs/ORCHESTRATOR_E2E_AUDIT.md`

## Future Enhancements

- [ ] Real-time audit progress visualization
- [ ] Agent performance metrics
- [ ] Key usage analytics
- [ ] Automated vulnerability patching
- [ ] Multi-repo audit support
- [ ] Export audit results to JSON/CSV
- [ ] Integration with CI/CD pipelines

---

**Status:** All agents under orchestrator command with random API key assignment and E2E code audit fully operational! 🚀
