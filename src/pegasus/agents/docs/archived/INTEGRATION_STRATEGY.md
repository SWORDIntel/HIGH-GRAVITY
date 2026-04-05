# Agent Integration Strategy - Dual System Approach

## Current Situation
- New v7.0 agents (31 total) exist but aren't compatible with Claude Code's Task tool
- Old v2.0 agents were designed for Task tool compatibility
- Binary communication system exists but needs proper launch mechanism

## Solution: Dual System Bridge

### Phase 1: Immediate Functionality (NOW)
1. **Restore Old Director** - Copy old Director.md as Director-Legacy.md for Task tool use
2. **Create Agent Bridge** - Build bridge between Task tool and binary system
3. **Launch Binary System** - Use BRING_ONLINE.sh to start communication system

### Phase 2: Full Integration (Next)
1. **Task Tool Integration** - Register new agents with Claude Code
2. **Binary System Completion** - Complete agent business logic
3. **Unified Interface** - Single interface for both systems

### Implementation Plan

#### Immediate Actions:
1. Copy `deprecated/oldagents/Director.md` as working Director
2. Test Director agent through Task tool
3. Launch binary communication system via BRING_ONLINE.sh
4. Create integration bridge script

#### Agent Availability Strategy:
- **Legacy agents** (via Task tool) - Immediate use
- **Binary agents** (via BRING_ONLINE.sh) - Full functionality
- **Bridge system** - Seamless coordination between both

## File Locations:
- Legacy agents: `deprecated/oldagents/*.md`
- New agents: `agents/*.md` (current directory)
- Binary system: `BRING_ONLINE.sh` + `src/c/` + `binary-communications-system/`
- Bridge: `INTEGRATION_BRIDGE.py` (to create)

## Decision: 
Use BRING_ONLINE.sh to launch the binary system properly, then restore legacy Director for Task tool compatibility until full integration is complete.