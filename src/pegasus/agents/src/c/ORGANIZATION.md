# src/c Directory Organization - SINGLE SOURCE OF TRUTH

## Directory Structure
All C source code is now in ONE directory: `src/c/`
- Test files: `src/c/tests/`
- Old/backup files: `src/c/OLD-BACKUP/`

## File Categories

### 1. CORE BINARY COMMUNICATION SYSTEM
**These are compiled into agent_bridge binary:**
- `agent_bridge.c` - Main binary communication protocol (1204 lines)
- `message_router.c` - Message routing between agents
- `agent_discovery.c` - Agent discovery and registration
- `compatibility_layer.c` - Platform compatibility abstractions
- `ring_buffer_adapter.c` - High-performance ring buffer
- `protocol_asm.S` - Assembly optimizations

### 2. AGENT IMPLEMENTATIONS (*_agent.c)
**These are MODULAR - loaded separately, NOT compiled into main binary:**
- `director_agent.c` - Strategic command and control
- `project_orchestrator.c` - Tactical coordination
- `architect_agent.c` - System design
- `security_agent.c` - Security operations
- `constructor_agent.c` - Project initialization
- `debugger_agent.c` - Debugging and analysis
- `deployer_agent.c` - Deployment management
- `monitor_agent.c` - System monitoring
- `linter_agent.c` - Code quality (1475 lines - enhanced)
- `optimizer_agent.c` - Performance optimization
- `patcher_agent.c` - Code modifications
- `database_agent.c` - Data management
- `infrastructure_agent.c` - Infrastructure setup
- `docgen_agent.c` - Documentation generation
- `web_agent.c` - Web framework specialist
- `mobile_agent.c` - Mobile development
- `pygui_agent.c` - Python GUI development
- `tui_agent.c` - Terminal UI
- `mlops_agent.c` - ML operations
- `datascience_agent.c` - Data science
- `c-internal_agent.c` - C/C++ specialist
- `python-internal_agent.c` - Python execution
- `gnu_agent.c` - GNU tools specialist
- `npu_agent.c` - NPU acceleration
- `planner_agent.c` - Planning agent
- `researcher_agent.c` - Technology research
- `bastion_agent.c` - Defensive security
- `oversight_agent.c` - Quality assurance
- `securitychaosagent_agent.c` - Chaos testing
- `apidesigner_agent.c` - API design

### 3. SUPPORT MODULES
**Included in default binary build for full functionality:**
- `auth_security.c` - Authentication and authorization
- `tls_manager.c` - TLS/SSL management
- `memory_optimizer.c` - Memory optimization
- `health_check_endpoints.c` - Health monitoring endpoints
- `prometheus_exporter.c` - Metrics export

### 4. ADVANCED FEATURES (Optional)
**Can be included for advanced capabilities:**
- `digital_twin.c` - Digital twin simulation
- `streaming_pipeline.c` - Stream processing
- `multimodal_fusion.c` - Multi-modal data fusion
- `neural_architecture_search.c` - NAS implementation

### 5. NETWORK/DISTRIBUTED (Optional)
**For distributed deployments:**
- `distributed_network.c` - Network coordination
- `distributed_load_balancer.c` - Load balancing
- `distributed_service_discovery.c` - Service discovery

### 6. AI ROUTER (Optional)
**For AI-enhanced routing:**
- `ai_router_integration.c` - AI router integration
- `ai_enhanced_router.c` - Enhanced routing logic

### 7. RUNTIME/COORDINATION
**Agent runtime and coordination:**
- `unified_agent_runtime.c` - Unified runtime for all agents
- `agent_runtime.c` - Basic agent runtime
- `agent_coordination.c` - Agent coordination logic

### 8. UTILITIES
- `stubs.c` - Minimal stub implementations for linking

### 9. RUST INTEGRATION
- `vector_router.rs` - In `src/rust/` - Enhanced vector database
- `vector_router.h` - C header for Rust FFI

## Build Targets (from Makefile)

1. **make agent_bridge** - Core binary with support modules (DEFAULT)
2. **make agent_bridge_ai** - With AI router and network support  
3. **make agent_bridge_full** - With Rust vector router integration
4. **make clean** - Clean build artifacts
5. **make info** - Show build configuration

## Key Points

- **SINGLE SOURCE**: All C code is in `src/c/` - no more split directories
- **MODULAR AGENTS**: Agents are NOT compiled into the binary, they communicate via protocol
- **CLEAN NAMING**: No more ultra_hybrid_* or confusing _final/_enhanced suffixes
- **ORGANIZED**: Tests in tests/, old files in OLD-BACKUP/
- **DOCUMENTED**: This file maintains the organization

## File Naming Convention

- `*_agent.c` - Agent implementations (modular)
- `agent_*.c` - Core binary system files
- `*.h` - Header files
- `*.S` - Assembly files

Last updated: 2024-08-16