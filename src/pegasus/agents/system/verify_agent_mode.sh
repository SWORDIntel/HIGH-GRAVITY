#!/bin/bash
# ============================================================================
# CLAUDE AGENT MODE VERIFICATION
# 
# Verifies which agent system is active and ensures consistent operation
# Usage: ./verify_agent_mode.sh
# ============================================================================

CLAUDE_BASE="/home/ubuntu/Documents/Claude"
AGENTS_DIR="$CLAUDE_BASE/agents"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== Claude Agent Mode Verification ===${NC}"

# Check if binary system is running
BINARY_RUNNING=false
if pgrep -f "agent_bridge" > /dev/null; then
    BINARY_RUNNING=true
    echo -e "${RED}⚠️  Binary system detected running${NC}"
fi

# Check for Python bridges
PYTHON_BRIDGE_RUNNING=false
if pgrep -f "claude_agent_bridge" > /dev/null || pgrep -f "agent_server.py" > /dev/null; then
    PYTHON_BRIDGE_RUNNING=true
    echo -e "${YELLOW}🔗 Python bridge detected running${NC}"
fi

# Check agent directory
if [ -L "$AGENTS_DIR" ]; then
    TARGET=$(readlink "$AGENTS_DIR")
    echo -e "Agents directory: ${YELLOW}SYMLINK${NC} → $TARGET"
    AGENT_COUNT=$(find "$AGENTS_DIR" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l)
elif [ -d "$AGENTS_DIR" ]; then
    echo -e "Agents directory: ${GREEN}DIRECT${NC} (original directory)"
    AGENT_COUNT=$(find "$AGENTS_DIR" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l)
else
    echo -e "Agents directory: ${RED}NOT FOUND${NC}"
    exit 1
fi

echo "Agent .md files found: $AGENT_COUNT"

# Test Optimizer agent accessibility
if [ -f "$AGENTS_DIR/Optimizer.md" ]; then
    echo -e "Optimizer agent: ${GREEN}ACCESSIBLE${NC}"
else
    echo -e "Optimizer agent: ${RED}NOT FOUND${NC}"
fi

# Determine recommended mode
echo ""
echo -e "${YELLOW}=== System Analysis ===${NC}"

if [ "$BINARY_RUNNING" = true ] && [ "$PYTHON_BRIDGE_RUNNING" = true ]; then
    echo -e "${RED}⚠️  CONFLICT: Both binary system and bridge running${NC}"
    echo "Recommendation: Stop binary system or use binary agents"
elif [ "$BINARY_RUNNING" = true ]; then
    echo -e "${YELLOW}Binary system active${NC}"
    echo "Recommendation: Use binary C agents for optimal performance"
elif [ "$PYTHON_BRIDGE_RUNNING" = true ]; then
    echo -e "${YELLOW}Python bridge active${NC}"
    echo "Recommendation: Use .md agents with bridge coordination"
elif [ "$AGENT_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ .md agents ready, no conflicts${NC}"
    echo "Recommendation: Proceed with .md agent system"
else
    echo -e "${RED}No agents found${NC}"
    echo "Recommendation: Check agent installation"
fi

# Check for specific linter files
echo ""
echo -e "${YELLOW}=== Linter Agent Status ===${NC}"

if [ -f "$AGENTS_DIR/src/c/linter_agent.c" ]; then
    LINES=$(wc -l < "$AGENTS_DIR/src/c/linter_agent.c")
    echo "C implementation: ${GREEN}$LINES lines${NC}"
else
    echo -e "C implementation: ${RED}NOT FOUND${NC}"
fi

if [ -f "$AGENTS_DIR/Linter.md" ]; then
    echo -e "Linter.md definition: ${GREEN}FOUND${NC}"
else
    echo -e "Linter.md definition: ${RED}NOT FOUND${NC}"
fi

# Final recommendation
echo ""
echo -e "${YELLOW}=== Final Recommendation ===${NC}"
if [ "$BINARY_RUNNING" = false ] && [ "$AGENT_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Safe to proceed with .md agent optimization${NC}"
    echo "System is ready for Optimizer agent enhancement task"
else
    echo -e "${YELLOW}⚠️  System conflicts detected${NC}"
    echo "Resolve binary/bridge conflicts before proceeding"
fi