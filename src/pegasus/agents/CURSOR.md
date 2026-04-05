# CURSOR Agent - IDE Integration Specialist

## Agent Identity
- **Name**: CURSOR
- **UUID**: cursor-integration-001
- **Category**: IDE_INTEGRATION
- **Priority**: HIGH
- **Status**: PRODUCTION
- **Health**: 100%

## Purpose
The CURSOR agent serves as the primary integration point between the Cursor IDE and the SWORDSwarm multi-agent orchestration system. It enables developers to access all 88+ agents, hardware acceleration features, testing infrastructure, and documentation directly from the Cursor IDE interface.

## Core Capabilities

### 1. AI-Powered Code Completion
- Context-aware suggestions based on SWORDSwarm patterns
- Agent method and property auto-completion
- Hardware optimization hints
- Test generation suggestions
- Documentation integration

### 2. Multi-Agent Orchestration
- Invoke agents via `@agent <name> <task>` command
- Query agent capabilities with `@ask <agent-name>`
- Visualize agent dependency graphs
- Real-time agent status monitoring
- Load balancing suggestions

### 3. Hardware Acceleration Integration
- Real-time NPU status display in status bar
- AVX instruction level detection (AVX-512, AVX2, SSE)
- GPU utilization monitoring
- Performance metrics dashboard
- Automatic hardware optimization suggestions

### 4. Testing Integration
- 567+ tests accessible via test explorer
- One-click test execution
- Coverage visualization (current: 82%)
- Failed test navigation
- Test result inline annotations

### 5. Documentation Access
- 50+ markdown files indexed and searchable
- Quick search via `@docs <query>` command
- Inline documentation viewer
- Hover tooltips for agent methods
- Auto-generated API documentation

### 6. Cross-Language Support
- Python, C, Rust, TypeScript, Julia, Go
- Language server integration
- Cross-language navigation
- Polyglot refactoring
- FFI boundary checking

## Tools

### IDE Integration Tools
1. **Agent Command Parser**: Parses `@agent` syntax for agent invocation
2. **Hardware Monitor**: Real-time NPU/AVX/GPU status tracking
3. **Test Runner**: Integrated pytest execution with coverage
4. **Documentation Indexer**: Fast search across 50+ doc files
5. **Code Completion Engine**: Context-aware AI suggestions

### Hardware Optimization Tools
1. **NPU Detector**: Intel AI Boost (VPU) detection and configuration
2. **AVX Profiler**: SIMD instruction level detection
3. **Performance Benchmark**: Multi-device performance comparison
4. **Memory Analyzer**: Alignment and optimization checks

### Development Tools
1. **Code Formatter**: Black + isort integration
2. **Linter**: Pylint with project-specific rules
3. **Type Checker**: MyPy integration
4. **Debugger Interface**: Python debugger integration

## Agent Architecture

### Three-Tier Integration
```
┌─────────────────────────────────────────────┐
│           Cursor IDE Interface              │
│  (AI Completion, Commands, Status Bar)      │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         CURSOR Agent Layer (Python)         │
│  - Agent orchestration                      │
│  - Command parsing                          │
│  - Hardware monitoring                      │
│  - Test execution                           │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      SWORDSwarm Core (88+ Agents)           │
│  - Agent registry                           │
│  - Hardware optimizer                       │
│  - Database manager                         │
│  - Hook system                              │
└─────────────────────────────────────────────┘
```

## Configuration Files

### .cursor/settings.json
Cursor-specific settings mirroring VSCode configuration with additional Cursor features:
- Python interpreter path
- Testing configuration
- Linting and formatting
- AI model settings
- Agent awareness configuration

### .cursor/agent_registry.json
Complete registry of all 88+ agents with:
- Agent metadata (name, UUID, category, priority)
- Capabilities and tools
- File locations
- Command syntax
- Keybindings

### .cursor/commands.json
Custom commands for SWORDSwarm operations:
- List all agents
- Hardware status
- Run tests
- Search documentation
- Benchmark hardware
- Check agent health
- Orchestrator execution

### .cursorrules
AI completion rules including:
- Project context
- Architecture patterns
- Code style guidelines
- Agent development workflow
- Security best practices
- Performance considerations

## Usage Examples

### Example 1: Invoke Agent from Cursor
```bash
# In Cursor command palette (Cmd+Shift+P):
@agent OPTIMIZER "optimize database queries in user_service.py"

# CURSOR agent:
# 1. Parses command
# 2. Locates OPTIMIZER agent
# 3. Passes task to agent
# 4. Displays results inline
```

### Example 2: Check Hardware Status
```bash
# Keyboard shortcut: Cmd+Shift+H
# Or command: SWORDSwarm: Show Hardware Status

Output:
═══════════════════════════════════
Hardware Status
═══════════════════════════════════
NPU: Available (Intel Core Ultra)
Speedup: 7.2x
AVX: AVX-512
GPU: Intel Arc Graphics
Agents Loaded: 88
═══════════════════════════════════
```

### Example 3: Run Tests with Coverage
```bash
# Keyboard shortcut: Cmd+Shift+T
# Or command: SWORDSwarm: Run Tests with HTML Coverage

Output:
Running pytest...
========= 567 tests passed in 23.45s =========
Coverage: 82%
Report: htmlcov/index.html
```

### Example 4: Search Documentation
```bash
# In Cursor: @docs NPU acceleration

Results:
- docs/HARDWARE_OPTIMIZATION.md:45 (NPU setup)
- docs/PERFORMANCE.md:123 (NPU benchmarks)
- CURSOR_INTEGRATION_PLAN.md:234 (NPU integration)
```

### Example 5: Multi-Agent Workflow
```python
# In Python file, CURSOR provides intelligent completion:

from claude_agents import agent_registry

# Type "agent_registry." → CURSOR suggests:
# - get(name: str)
# - list_by_category(category: str)
# - health_check()

coordinator = agent_registry.get("COORDINATOR")
researcher = agent_registry.get("RESEARCHER")
optimizer = agent_registry.get("OPTIMIZER")

# CURSOR suggests multi-agent pattern:
workflow = coordinator.orchestrate([
    researcher.gather_data(topic="performance bottlenecks"),
    optimizer.analyze_and_optimize(target="database_queries")
])

# CURSOR shows hardware optimization opportunity:
# 💡 Tip: Enable NPU acceleration for 7x speedup
# if HardwareOptimizer().npu_available:
#     workflow.enable_npu()
```

## Integration Points

### 1. Agent Registry Integration
**File**: `config/agent-registry.json`
- Loads all 88+ agents on Cursor startup
- Provides auto-completion for agent names
- Displays agent metadata on hover

### 2. Hardware Optimizer Integration
**File**: `agents/src/python/claude_agents/hardware_optimizer.py`
- Real-time NPU status in status bar
- Performance metrics display
- Optimization suggestions

### 3. Test Suite Integration
**Directory**: `tests/`
- 567+ tests indexed in test explorer
- One-click execution
- Coverage visualization

### 4. Documentation Integration
**Directory**: `docs/`
- 50+ files indexed for search
- Quick access via `@docs`
- Hover documentation

### 5. Hook System Integration
**Directory**: `hooks/`
- C/Rust hook visualization
- Performance profiling
- Execution tracing

## Performance Metrics

### Response Times
- Agent command parsing: <10ms
- Code completion suggestions: <100ms
- Hardware status update: <50ms
- Documentation search: <200ms
- Test execution: Variable (23s for full suite)

### Resource Usage
- Memory footprint: ~50MB (agent registry + cache)
- CPU usage: <2% idle, <15% during completion
- Disk I/O: Minimal (cached agent registry)

### Acceleration
- NPU acceleration: 7-10x speedup on Intel Core Ultra
- AVX-512: 4-5x speedup on compatible CPUs
- AVX2: 2-3x speedup as fallback

## Keyboard Shortcuts

### Agent Operations
- **Cmd+Shift+A**: List all agents
- **Cmd+Shift+O**: Run orchestrator
- **Cmd+Shift+M**: Show agent mapping

### Hardware & Performance
- **Cmd+Shift+H**: Hardware status
- **Cmd+Shift+B**: Benchmark hardware

### Testing & Quality
- **Cmd+Shift+T**: Run all tests
- **Cmd+Shift+L**: Lint code
- **Cmd+Shift+F**: Format code

### Documentation
- **Cmd+Shift+D**: Search docs

## Status Bar Items

### Real-Time Display
1. **Agent Count**: "88 agents loaded"
2. **NPU Status**: "NPU: Active (7.2x)" or "NPU: Unavailable"
3. **AVX Level**: "AVX-512" / "AVX2" / "SSE"
4. **Test Coverage**: "Coverage: 82%"
5. **Active Tasks**: "Tasks: 3" (when agents running)

## Error Handling

### Agent Not Found
```
Error: Agent "UNKNOWNN" not found
Did you mean: UNKNOWN, KNOWN, or AGENTSMITH?
Available agents: Cmd+Shift+A
```

### Hardware Unavailable
```
Warning: NPU not available
Falling back to AVX-512 acceleration
Performance: 4.5x speedup (vs 7-10x with NPU)
```

### Test Failures
```
Tests failed: 3/567
View failures: Click inline annotations
Re-run failed: pytest tests/test_module.py::test_func
```

## Security Considerations

### Sandboxing
- Agent commands executed in isolated environment
- No direct filesystem access without approval
- Network requests logged and monitored

### Secrets Management
- Never commit .env files
- API keys stored in secure keyring
- Database credentials encrypted

### Code Validation
- All agent outputs sanitized
- SQL queries parameterized
- Shell commands escaped

## Future Enhancements

### Planned Features
1. **Visual Agent Builder**: Drag-and-drop agent creation in Cursor
2. **Real-time Collaboration**: Multi-developer agent editing
3. **AI Pair Programming**: Cursor suggests agent combinations
4. **Performance Dashboard**: Interactive hardware utilization graphs
5. **Agent Marketplace**: Share and discover community agents

### Research Areas
1. **Predictive Completion**: AI predicts agent needs before invocation
2. **Auto-Optimization**: Automatic hardware acceleration selection
3. **Smart Refactoring**: Cross-agent code refactoring
4. **Test Generation**: AI-generated tests for agent code

## Troubleshooting

### Issue: Slow Completions
**Solution**: Reduce context window in `.cursor/settings.json`:
```json
{
  "cursor.contextWindow": "medium"
}
```

### Issue: Agents Not Loading
**Solution**: Verify Python path and dependencies:
```bash
which python  # Should be venv/bin/python
pip install -r requirements.txt
```

### Issue: Hardware Status Not Updating
**Solution**: Restart Cursor or manually refresh:
```bash
Cmd+Shift+H  # Refresh hardware status
```

## Support & Resources

### Documentation
- **Integration Plan**: `CURSOR_INTEGRATION_PLAN.md`
- **Agent Mapping**: `docs/ACCURATE_AGENT_MAPPING.md`
- **Configuration**: `config/CLAUDE.md`

### Community
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share ideas

## Changelog

### Version 1.0.0 (2025-11-21)
- Initial CURSOR agent implementation
- Full integration with SWORDSwarm v42.0
- Support for 88+ agents
- Hardware acceleration monitoring
- Testing infrastructure integration
- Documentation indexing
- Multi-language support

## License
See main project LICENSE file.

## Maintainers
See main project MAINTAINERS.md file.

---

**CURSOR Agent** - Empowering developers with AI-powered IDE integration for SWORDSwarm 🚀
