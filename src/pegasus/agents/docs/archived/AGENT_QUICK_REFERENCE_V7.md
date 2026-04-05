# Agent Quick Reference v7.0

## Agent Invocation Matrix

### Always Auto-Invoked

| Agent | Triggers |
|-------|----------|
| **ProjectOrchestrator** | Any multi-step task, complex coordination needed |
| **Director** | Strategic planning, high-level architecture decisions |
| **Security** | Security concerns, vulnerability mentions, auth/encryption |
| **Infrastructure** | Deployment, containers, CI/CD, cloud services |

### Frequently Auto-Invoked

| Agent | Triggers |
|-------|----------|
| **Architect** | System design, architecture patterns, refactoring |
| **Constructor** | New project, initialization, scaffolding |
| **Patcher** | Bug fixes, code modifications, hotfixes |
| **Debugger** | Errors, crashes, performance issues |
| **Web** | Frontend, React/Vue/Angular, UI development |
| **APIDesigner** | REST/GraphQL/gRPC, API design, contracts |
| **Database** | Schema design, queries, migrations, data modeling |

### Context-Specific Invocation

| Agent | When to Use |
|-------|-------------|
| **Testbed** | Test creation, coverage improvement, test automation |
| **Linter** | Code review, style improvements, static analysis |
| **Optimizer** | Performance issues, optimization needs, benchmarking |
| **Monitor** | Observability, logging, metrics, alerting |
| **Deployer** | Release management, production rollouts |
| **Docgen** | Documentation updates, README creation, API docs |
| **MLOps** | ML pipelines, model deployment, experiment tracking |
| **DataScience** | Data analysis, statistics, predictive modeling |
| **Mobile** | iOS/Android apps, React Native, mobile optimization |
| **PyGUI** | Python desktop apps, Tkinter/PyQt/Streamlit |
| **TUI** | Terminal interfaces, ncurses, CLI tools |
| **RESEARCHER** | Technology evaluation, tool comparison, feasibility |
| **Oversight** | Compliance, quality assurance, audits |
| **Packager** | Package publishing, dependency management |
| **SecurityChaosAgent** | Chaos testing, stress testing, vulnerability scanning |
| **Bastion** | Defensive security (from external project) |
| **c-internal** | C/C++ optimization, native code, system programming |
| **python-internal** | Python execution, NPU optimization, ML workloads |

## Agent Capability Summary

### Strategic Command
```yaml
Director:
  role: "Strategic planning and coordination"
  invokes: [ProjectOrchestrator, Architect]
  priority: CRITICAL

ProjectOrchestrator:
  role: "Tactical execution coordination"
  invokes: [ALL agents as needed]
  priority: CRITICAL
```

### Core Development
```yaml
Architect:
  specialty: "System design, patterns, refactoring"
  invokes: [Constructor, Testbed, Optimizer]
  
Constructor:
  specialty: "Project initialization, scaffolding"
  invokes: [Architect, Testbed, Linter]
  
Patcher:
  specialty: "Bug fixes, surgical code changes"
  invokes: [Testbed, Linter, Debugger]
  
Debugger:
  specialty: "Failure analysis, root cause identification"
  invokes: [Patcher, Testbed, Monitor]
```

### Security Team
```yaml
Security:
  specialty: "Vulnerability scanning, compliance"
  invokes: [Patcher, Monitor, Oversight]
  
Bastion:
  specialty: "Defensive security, intrusion prevention"
  invokes: [Security, Monitor, Infrastructure]
  
SecurityChaosAgent:
  specialty: "Chaos testing, stress testing"
  invokes: [Security, Bastion, Monitor]
  
Oversight:
  specialty: "Quality assurance, compliance"
  invokes: [Security, Linter, Testbed]
```

### Infrastructure & Deployment
```yaml
Infrastructure:
  specialty: "System setup, containers, CI/CD"
  invokes: [Deployer, Monitor, Security]
  
Deployer:
  specialty: "Release management, rollouts"
  invokes: [Infrastructure, Monitor, Security]
  
Monitor:
  specialty: "Observability, metrics, alerting"
  invokes: [Infrastructure, Security]
  
Packager:
  specialty: "Package management, publishing"
  invokes: [Constructor, Deployer, Security]
```

### Specialized Development
```yaml
APIDesigner:
  specialty: "API contracts, REST/GraphQL/gRPC"
  invokes: [Architect, Testbed, Docgen]
  
Database:
  specialty: "Schema design, optimization, migrations"
  invokes: [Architect, Monitor, Security]
  
Web:
  specialty: "Frontend frameworks, React/Vue/Angular"
  invokes: [Constructor, Linter, Testbed]
  
Mobile:
  specialty: "iOS/Android, React Native"
  invokes: [Web, APIDesigner, Testbed]
  
PyGUI:
  specialty: "Python GUIs, Tkinter/PyQt/Streamlit"
  invokes: [python-internal, Testbed]
  
TUI:
  specialty: "Terminal UIs, ncurses, CLI tools"
  invokes: [c-internal, python-internal]
```

### Data & ML
```yaml
DataScience:
  specialty: "Data analysis, statistics, ML"
  invokes: [MLOps, Database, Optimizer]
  
MLOps:
  specialty: "ML pipelines, model deployment"
  invokes: [DataScience, Infrastructure, Monitor]
```

### Support & Research
```yaml
Docgen:
  specialty: "Documentation, README, API docs"
  invokes: [APIDesigner, Architect]
  
RESEARCHER:
  specialty: "Technology evaluation, benchmarking"
  invokes: [ProjectOrchestrator, Architect, DataScience]
```

### Internal Execution
```yaml
c-internal:
  specialty: "C/C++ optimization, Meteor Lake tuning"
  invokes: [Optimizer, Debugger, Testbed]
  
python-internal:
  specialty: "Python execution, NPU optimization"
  invokes: [DataScience, MLOps, PyGUI]
```

## Hardware Optimization Levels

| Agent | AVX-512 Benefit | Primary Core Type |
|-------|----------------|-------------------|
| c-internal | HIGH | P-cores exclusive |
| python-internal | HIGH | P-cores + NPU |
| DataScience | HIGH | P-cores for compute |
| MLOps | HIGH | P-cores for training |
| Optimizer | HIGH | P-cores for analysis |
| SecurityChaosAgent | MEDIUM | Distributed |
| Database | MEDIUM | Memory bandwidth |
| Web | MEDIUM | Build processes |
| Debugger | MEDIUM | Analysis tasks |
| Others | LOW | Standard allocation |

## Agent Communication Patterns

### Hierarchical Invocation
```
Director
  → ProjectOrchestrator
    → Architect
      → Constructor
        → Testbed
```

### Parallel Coordination
```
ProjectOrchestrator
  ├→ Security (security scan)
  ├→ Testbed (test creation)
  └→ Docgen (documentation)
```

### Circular Dependencies (Allowed)
```
Patcher ←→ Testbed ←→ Linter
   ↑                      ↓
   └──────────────────────┘
```

## Quick Invocation Examples

### Create New Project
```
Director → ProjectOrchestrator → Constructor → [Testbed, Linter, Docgen]
```

### Fix Bug
```
Debugger → Patcher → Testbed → Linter
```

### Deploy to Production
```
Infrastructure → Deployer → Monitor → Security
```

### Optimize Performance
```
Optimizer → c-internal/python-internal → Testbed → Monitor
```

### Security Audit
```
Security → SecurityChaosAgent → Oversight → Patcher
```

## Performance Targets

| Metric | Target | Agent Owner |
|--------|--------|-------------|
| Code Coverage | >85% | Testbed |
| Lighthouse Score | >95 | Web |
| API Coverage | >98% | Docgen |
| Security Score | A+ | Security |
| Deployment Success | >95% | Deployer |
| Bug Fix Rate | >99% | Patcher |
| Performance Gain | >30% | Optimizer |
| ML Model Accuracy | >90% | DataScience |
| Uptime | >99.9% | Infrastructure |
| Compliance | 100% | Oversight |

## Emergency Procedures

### System Failure
1. **Debugger** performs root cause analysis
2. **Patcher** implements emergency fix
3. **Deployer** executes hotfix rollout
4. **Monitor** validates recovery

### Security Breach
1. **Security** performs immediate assessment
2. **Bastion** implements defensive measures
3. **Patcher** applies security patches
4. **Oversight** documents incident

### Performance Crisis
1. **Monitor** identifies bottleneck
2. **Optimizer** develops solution
3. **c-internal/python-internal** implements optimization
4. **Deployer** rolls out fix

---

*Quick Reference Version: 7.0.0*  
*For detailed documentation, see [AGENT_FRAMEWORK_V7.md](./AGENT_FRAMEWORK_V7.md)*