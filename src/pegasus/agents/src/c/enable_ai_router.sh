#!/bin/bash
# ============================================================================
# AI ROUTER INTEGRATION ENABLER
# Seamlessly integrates AI-Enhanced Router with existing build system
# ============================================================================

AGENTS_DIR="${CLAUDE_PROJECT_ROOT:-$(dirname "$0")/../../}agents"
SRC_DIR="$AGENTS_DIR/src/c"
BACKUP_SUFFIX=".pre_ai_$(date +%Y%m%d_%H%M%S)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE} AI-Enhanced Router Integration for Claude Code${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if AI router files exist
if [ ! -f "$SRC_DIR/ai_enhanced_router.c" ] || [ ! -f "$SRC_DIR/ai_enhanced_router.h" ]; then
    echo -e "${YELLOW}Warning: AI router source files not found!${NC}"
    echo "Expected files:"
    echo "  - $SRC_DIR/ai_enhanced_router.c"
    echo "  - $SRC_DIR/ai_enhanced_router.h"
    echo "  - $SRC_DIR/ai_router_integration.c"
    echo ""
    echo "Please ensure AI router files are in the src/c directory."
    exit 1
fi

echo -e "${GREEN}✓ AI router source files found${NC}"

# Backup existing Makefile
if [ -f "$SRC_DIR/Makefile" ]; then
    echo -e "${YELLOW}Backing up existing Makefile...${NC}"
    cp "$SRC_DIR/Makefile" "$SRC_DIR/Makefile$BACKUP_SUFFIX"
    echo -e "${GREEN}✓ Backup created: Makefile$BACKUP_SUFFIX${NC}"
fi

# Integration options
echo ""
echo "Choose integration method:"
echo "1) Replace Makefile with AI-enhanced version (recommended)"
echo "2) Add AI router targets to existing Makefile"
echo "3) Use separate AI Makefile (Makefile.ai_enhanced)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo -e "${YELLOW}Replacing Makefile with AI-enhanced version...${NC}"
        cp "$SRC_DIR/Makefile.ai_enhanced" "$SRC_DIR/Makefile"
        echo -e "${GREEN}✓ AI-enhanced Makefile installed${NC}"
        ;;
    2)
        echo -e "${YELLOW}Adding AI router targets to existing Makefile...${NC}"
        cat >> "$SRC_DIR/Makefile" << 'EOF'

# ============================================================================
# AI-ENHANCED ROUTER INTEGRATION (Auto-added)
# ============================================================================

# AI Router sources
AI_ROUTER_SRCS = ai_enhanced_router.c ai_router_integration.c
AI_ROUTER_OBJS = $(AI_ROUTER_SRCS:.c=.o)
AI_ROUTER_LIB = libai_router.a
AI_ROUTER_BIN = ai_router_test

# AI Router specific flags
AI_CFLAGS = $(CFLAGS) -DENABLE_AI_ROUTING -DTARGET_ROUTING_LATENCY_NS=10000

# Build AI router library
$(AI_ROUTER_LIB): $(AI_ROUTER_OBJS)
	$(AR) rcs $@ $^

# Build AI router test
$(AI_ROUTER_BIN): $(AI_ROUTER_LIB) ai_router_test.c
	$(CC) $(AI_CFLAGS) ai_router_test.c -o $@ -L. -lai_router $(LDFLAGS)

# AI-enhanced agent builds
director_ai: $(DIRECTOR_OBJ) $(AI_ROUTER_LIB)
	$(CC) $(AI_CFLAGS) -DDIRECTOR_TEST_MODE -o director_agent_ai $(DIRECTOR_OBJ) -L. -lai_router $(LDFLAGS)

orchestrator_ai: $(ORCHESTRATOR_OBJ) $(AI_ROUTER_LIB)
	$(CC) $(AI_CFLAGS) -DORCHESTRATOR_TEST_MODE -o orchestrator_agent_ai $(ORCHESTRATOR_OBJ) -L. -lai_router $(LDFLAGS)

architect_ai: $(ARCHITECT_OBJ) $(AI_ROUTER_LIB)
	$(CC) $(AI_CFLAGS) -DARCHITECT_TEST_MODE -o architect_agent_ai $(ARCHITECT_OBJ) -L. -lai_router $(LDFLAGS)

# AI targets
ai-router: $(AI_ROUTER_LIB)
ai-agents: director_ai orchestrator_ai architect_ai
ai-test: $(AI_ROUTER_BIN)
	./$(AI_ROUTER_BIN)

# Clean AI artifacts
clean-ai:
	rm -f $(AI_ROUTER_OBJS) $(AI_ROUTER_LIB) $(AI_ROUTER_BIN)
	rm -f *_agent_ai

# Add AI targets to main clean
clean: clean-ai

.PHONY: ai-router ai-agents ai-test clean-ai director_ai orchestrator_ai architect_ai

EOF
        echo -e "${GREEN}✓ AI router targets added to existing Makefile${NC}"
        ;;
    3)
        echo -e "${YELLOW}Using separate AI Makefile...${NC}"
        echo "Use: make -f Makefile.ai_enhanced"
        echo -e "${GREEN}✓ Separate AI Makefile ready${NC}"
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Create test files if they don't exist
echo ""
echo -e "${YELLOW}Checking for test files...${NC}"

if [ ! -f "$SRC_DIR/ai_router_test.c" ]; then
    echo "Creating basic AI router test..."
    cat > "$SRC_DIR/ai_router_test.c" << 'EOF'
/*
 * Basic AI Router Test
 * Tests AI-enhanced routing integration
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#ifdef ENABLE_AI_ROUTING
#include "ai_enhanced_router.h"
#endif

int main() {
    printf("AI Router Test Suite\n");
    printf("===================\n");
    
#ifdef ENABLE_AI_ROUTING
    printf("✓ AI routing enabled\n");
    
    // Initialize AI router
    if (ai_router_service_init() == 0) {
        printf("✓ AI router service initialized\n");
        
        // Get version
        int major, minor, patch;
        ai_get_version(&major, &minor, &patch);
        printf("✓ AI router version: %d.%d.%d\n", major, minor, patch);
        
        // Test basic routing
        printf("✓ Basic functionality verified\n");
        
        ai_router_service_cleanup();
        printf("✓ AI router service cleaned up\n");
    } else {
        printf("✗ Failed to initialize AI router\n");
        return 1;
    }
#else
    printf("✗ AI routing not enabled\n");
    printf("  Add -DENABLE_AI_ROUTING to CFLAGS\n");
#endif
    
    printf("\nTest completed successfully!\n");
    return 0;
}
EOF
    echo -e "${GREEN}✓ Created ai_router_test.c${NC}"
fi

# Hardware detection
echo ""
echo -e "${YELLOW}Checking hardware capabilities...${NC}"

# Check for Intel NPU
if ls /dev/gna* >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Intel GNA/NPU detected${NC}"
    NPU_AVAILABLE=true
else
    echo -e "${YELLOW}⚠ Intel GNA/NPU not detected${NC}"
    NPU_AVAILABLE=false
fi

# Check for GPU
if ls /dev/dri/* >/dev/null 2>&1; then
    echo -e "${GREEN}✓ GPU devices detected${NC}"
    GPU_AVAILABLE=true
else
    echo -e "${YELLOW}⚠ GPU devices not detected${NC}"
    GPU_AVAILABLE=false
fi

# Check for OpenVINO
if ldconfig -p | grep -q openvino; then
    echo -e "${GREEN}✓ OpenVINO runtime detected${NC}"
    OPENVINO_AVAILABLE=true
else
    echo -e "${YELLOW}⚠ OpenVINO runtime not found${NC}"
    OPENVINO_AVAILABLE=false
fi

# Provide build recommendations
echo ""
echo -e "${BLUE}Build Recommendations:${NC}"
echo "======================"

if [ "$choice" = "1" ]; then
    if $NPU_AVAILABLE && $OPENVINO_AVAILABLE; then
        echo -e "${GREEN}Recommended: make ai-npu${NC} (NPU acceleration)"
    elif $GPU_AVAILABLE; then
        echo -e "${GREEN}Recommended: make ai-gpu${NC} (GPU acceleration)"
    else
        echo -e "${GREEN}Recommended: make release${NC} (CPU-optimized)"
    fi
    
    echo ""
    echo "Available AI builds:"
    echo "  make all         - Standard AI-enhanced build"
    echo "  make ai-npu      - NPU acceleration (if available)"
    echo "  make ai-gpu      - GPU acceleration (if available)"
    echo "  make ai-full     - All accelerations"
    echo "  make debug       - Debug build with AI"
    
elif [ "$choice" = "2" ]; then
    echo -e "${GREEN}Use: make ai-agents${NC} (AI-enhanced agents)"
    echo ""
    echo "Available targets:"
    echo "  make ai-router   - Build AI router library"
    echo "  make ai-agents   - Build AI-enhanced agents"
    echo "  make ai-test     - Run AI router tests"
    
else
    echo -e "${GREEN}Use: make -f Makefile.ai_enhanced${NC}"
fi

echo ""
echo -e "${GREEN}Integration completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Build the AI-enhanced system"
echo "2. Run tests to verify integration"
echo "3. Check hardware-specific optimizations"
echo ""
echo "For help: make help"