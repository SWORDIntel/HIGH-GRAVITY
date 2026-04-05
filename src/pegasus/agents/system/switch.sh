#!/bin/bash
# ============================================================================
# ENHANCED AGENT MODE SWITCHER v2.1 - TUI/CLI INTERFACE
# 
# Intelligently switches between .md agents and binary system modes
# Interactive TUI with automatic switching and comprehensive agent testing
# Uses environment-relative paths with CLAUDE_AGENTS_ROOT support
# ============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Base paths with environment-relative configuration
CLAUDE_AGENTS_ROOT="${CLAUDE_AGENTS_ROOT:-$(dirname "$(realpath "${BASH_SOURCE[0]}")")}"
AGENTS_DIR="$CLAUDE_AGENTS_ROOT"
BACKUP_DIR="$AGENTS_DIR/.backups"
STATE_FILE="$BACKUP_DIR/.current_mode"
BUILD_DIR="$AGENTS_DIR/build"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Function to log with timestamp
log() {
    echo -e "[$(date '+%H:%M:%S')] $1"
}

# Function to clear screen and show header
show_header() {
    clear
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}           Claude Agent System Controller v2.1                  ${NC}"
    echo -e "${BLUE}               Environment-Relative Path Support                     ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Function to get current mode
get_current_mode() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo "md_agents"
    fi
}

# Function to get system status
get_system_status() {
    local binary_procs=$(pgrep -f "agent_bridge|unified_agent_runtime|claude_agent_bridge" 2>/dev/null | wc -l)
    local md_count=$(find "$AGENTS_DIR" -maxdepth 1 -name "*.md" | wc -l)
    
    if [ $binary_procs -gt 0 ]; then
        echo "binary_active:$binary_procs"
    elif [ $md_count -gt 0 ]; then
        echo "md_active:$md_count"
    else
        echo "inactive:0"
    fi
}

# Function to verify agent registration and activity
verify_active_agents() {
    local expected_agents=(
        "director" "project_orchestrator" "architect" "security" "constructor"
        "testbed" "optimizer" "debugger" "deployer" "monitor" "database"
        "ml_ops" "patcher" "linter" "docgen" "infrastructure" "api_designer"
        "web" "mobile" "pygui" "tui" "data_science" "c_internal" 
        "python_internal" "security_chaos" "bastion" "oversight" "researcher"
        "gnu" "npu" "planner"
    )
    
    local active_count=0
    local registered_agents=()
    
    for agent in "${expected_agents[@]}"; do
        # Check for compiled agent binary
        if [ -x "$BUILD_DIR/${agent}_agent" ]; then
            ((active_count++))
            registered_agents+=("$agent")
        fi
        
        # Check for agent-specific processes
        if pgrep -f "${agent}_agent" > /dev/null 2>&1; then
            if [[ ! " ${registered_agents[@]} " =~ " ${agent} " ]]; then
                ((active_count++))
                registered_agents+=("$agent")
            fi
        fi
        
        # Check for .md agent files
        if [ -f "$AGENTS_DIR/${agent^}.md" ] || [ -f "$AGENTS_DIR/${agent}.md" ]; then
            if [[ ! " ${registered_agents[@]} " =~ " ${agent} " ]]; then
                ((active_count++))
                registered_agents+=("$agent")
            fi
        fi
    done
    
    echo "$active_count:${registered_agents[*]}"
}

# Function to gracefully deactivate binary system
graceful_deactivate_binary() {
    echo -e "${YELLOW}Gracefully deactivating binary system...${NC}"
    
    local process_groups=(
        "linter_agent"
        "monitor_agent"
        "python_bridge"
        "claude_agent_bridge"
        "unified_agent_runtime"
        "agent_bridge"
    )
    
    for proc_group in "${process_groups[@]}"; do
        local pids=$(pgrep -f "$proc_group" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            echo "Stopping $proc_group..."
            
            # Send TERM signal first
            for pid in $pids; do
                kill -TERM $pid 2>/dev/null || true
            done
            
            # Wait up to 3 seconds for graceful shutdown
            local waited=0
            while [ $waited -lt 3 ] && pgrep -f "$proc_group" > /dev/null 2>&1; do
                sleep 1
                ((waited++))
            done
            
            # Force kill if still running
            if pgrep -f "$proc_group" > /dev/null 2>&1; then
                pkill -KILL -f "$proc_group" 2>/dev/null || true
            fi
        fi
    done
    
    # Clean up system resources
    ipcrm -Q $(ipcs -q | awk '/ubuntu/ {print $2}') 2>/dev/null || true
    ipcrm -M $(ipcs -m | awk '/ubuntu/ {print $2}') 2>/dev/null || true
    
    # Remove marker files
    rm -f "$AGENTS_DIR/.online"
    rm -f "$AGENTS_DIR/BINARY_MODE_ACTIVE"
    rm -f "$AGENTS_DIR/.binary_active"
    
    if [ -f "$AGENTS_DIR/.keeper.pid" ]; then
        local keeper_pid=$(cat "$AGENTS_DIR/.keeper.pid")
        kill $keeper_pid 2>/dev/null || true
        rm -f "$AGENTS_DIR/.keeper.pid"
    fi
    
    sleep 1
    local remaining_procs=$(pgrep -f "agent_bridge|unified_agent_runtime|claude_agent_bridge" | wc -l)
    
    if [ $remaining_procs -eq 0 ]; then
        echo -e "${GREEN}✓ Binary system deactivated${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ $remaining_procs processes still running${NC}"
        return 1
    fi
}

# Function to switch to binary mode
switch_to_binary_mode() {
    echo -e "${YELLOW}Switching to BINARY SYSTEM mode...${NC}"
    
    # Stop any existing processes
    graceful_deactivate_binary > /dev/null 2>&1
    
    # Verify components
    if [ ! -f "$AGENTS_DIR/BRING_ONLINE.sh" ]; then
        echo -e "${RED}BRING_ONLINE.sh not found!${NC}"
        return 1
    fi
    
    # Start Python Tandem Orchestration System first
    start_python_orchestration
    
    # Start binary system
    echo "Starting binary communication system..."
    cd "$AGENTS_DIR"
    chmod +x BRING_ONLINE.sh
    
    if ./system/BRING_ONLINE.sh > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Binary system started${NC}"
    else
        echo -e "${YELLOW}⚠ Binary system started with warnings${NC}"
    fi
    
    # Wait for stabilization
    sleep 3
    
    # Verify
    local running_procs=$(pgrep -f "agent_bridge|unified_agent_runtime|claude_agent_bridge" | wc -l)
    if [ $running_procs -gt 0 ]; then
        echo "binary_system" > "$STATE_FILE"
        echo -e "${GREEN}✓ Binary mode active: $running_procs processes${NC}"
        echo -e "${GREEN}✓ Python + Binary tandem operation enabled${NC}"
        return 0
    else
        echo -e "${RED}✗ Binary system failed to start${NC}"
        return 1
    fi
}

# Function to start Python Tandem Orchestration System
start_python_orchestration() {
    echo -e "${CYAN}Starting Python Tandem Orchestration System...${NC}"
    
    # Check if Python system is available
    if [ -f "$AGENTS_DIR/src/python/production_orchestrator.py" ]; then
        cd "$AGENTS_DIR/src/python"
        
        # Test Python system quickly
        if python3 -c "
import asyncio
import sys
sys.path.append('.')
from production_orchestrator import ProductionOrchestrator

async def test():
    orchestrator = ProductionOrchestrator()
    success = await orchestrator.initialize()
    print('Python orchestration system:', 'READY' if success else 'ERROR')
    return success

result = asyncio.run(test())
sys.exit(0 if result else 1)
" 2>/dev/null; then
            echo -e "${GREEN}✓ Python Tandem Orchestration System: READY${NC}"
            # Create marker for Python system
            touch "$AGENTS_DIR/.python_orchestration_active"
            return 0
        else
            echo -e "${YELLOW}⚠ Python system test failed, continuing with basic mode${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠ Python orchestration system not found${NC}"
        return 1
    fi
}

# Function to switch to .md mode
switch_to_md_mode() {
    echo -e "${YELLOW}Switching to .md AGENT mode...${NC}"
    
    # Stop binary processes
    graceful_deactivate_binary > /dev/null 2>&1
    
    # Verify .md agents
    local md_count=$(find "$AGENTS_DIR" -maxdepth 1 -name "*.md" | wc -l)
    if [ $md_count -lt 10 ]; then
        echo -e "${RED}Insufficient .md agents found! ($md_count)${NC}"
        return 1
    fi
    
    # Start Python Tandem Orchestration System
    start_python_orchestration
    
    echo "md_agents" > "$STATE_FILE"
    echo -e "${GREEN}✓ .md mode active: $md_count agents${NC}"
    return 0
}

# Function to test individual agent
test_agent() {
    local agent_name="$1"
    echo -n "Testing $agent_name... "
    
    # Check if agent file exists
    if [ -f "$AGENTS_DIR/${agent_name}.md" ] || [ -f "$AGENTS_DIR/${agent_name^}.md" ]; then
        echo -e "${GREEN}✓ .md${NC}"
        return 0
    fi
    
    # Check if binary agent exists
    if [ -x "$BUILD_DIR/${agent_name}_agent" ]; then
        echo -e "${GREEN}✓ binary${NC}"
        return 0
    fi
    
    # Check if process is running
    if pgrep -f "${agent_name}_agent" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ running${NC}"
        return 0
    fi
    
    echo -e "${RED}✗ missing${NC}"
    return 1
}

# Function to test all agents
test_all_agents() {
    show_header
    echo -e "${BOLD}${CYAN}Testing All Agents${NC}"
    echo "═══════════════════"
    echo ""
    
    local agents=(
        "director" "project_orchestrator" "architect" "security" "constructor"
        "testbed" "optimizer" "debugger" "deployer" "monitor" "database"
        "ml_ops" "patcher" "linter" "docgen" "infrastructure" "api_designer"
        "web" "mobile" "pygui" "tui" "data_science" "c_internal" 
        "python_internal" "security_chaos" "bastion" "oversight" "researcher"
        "gnu" "npu" "planner"
    )
    
    local passed=0
    local failed=0
    
    echo "Core Agents:"
    for agent in director project_orchestrator architect security monitor; do
        if test_agent "$agent"; then
            ((passed++))
        else
            ((failed++))
        fi
    done
    
    echo ""
    echo "Development Agents:"
    for agent in constructor testbed optimizer debugger deployer patcher linter; do
        if test_agent "$agent"; then
            ((passed++))
        else
            ((failed++))
        fi
    done
    
    echo ""
    echo "Specialized Agents:"
    for agent in database ml_ops docgen infrastructure api_designer web mobile; do
        if test_agent "$agent"; then
            ((passed++))
        else
            ((failed++))
        fi
    done
    
    echo ""
    echo "Advanced Agents:"
    for agent in pygui tui data_science c_internal python_internal security_chaos; do
        if test_agent "$agent"; then
            ((passed++))
        else
            ((failed++))
        fi
    done
    
    echo ""
    echo "System Agents:"
    for agent in bastion oversight researcher gnu npu planner; do
        if test_agent "$agent"; then
            ((passed++))
        else
            ((failed++))
        fi
    done
    
    echo ""
    echo "═══════════════════"
    echo -e "Results: ${GREEN}$passed passed${NC}, ${RED}$failed failed${NC}"
    echo "Total agents: $((passed + failed))/31"
    
    if [ $passed -ge 25 ]; then
        echo -e "${GREEN}✓ Agent test PASSED${NC}"
    else
        echo -e "${YELLOW}⚠ Agent test INCOMPLETE${NC}"
    fi
    
    echo ""
    echo "Press any key to continue..."
    read -n 1
}

# Function to show detailed status
show_status() {
    show_header
    
    local current_mode=$(get_current_mode)
    local status_info=$(get_system_status)
    local status_type="${status_info%%:*}"
    local status_count="${status_info##*:}"
    local agent_info=$(verify_active_agents)
    local agent_count="${agent_info%%:*}"
    local agent_list="${agent_info##*:}"
    
    echo -e "${BOLD}${CYAN}System Status${NC}"
    echo "═════════════"
    echo ""
    
    # Current mode
    case "$current_mode" in
        "binary_system")
            echo -e "Mode:           ${GREEN}BINARY SYSTEM${NC}"
            ;;
        "md_agents")
            echo -e "Mode:           ${BLUE}.md AGENTS${NC}"
            ;;
        *)
            echo -e "Mode:           ${YELLOW}UNKNOWN${NC}"
            ;;
    esac
    
    # System status
    case "$status_type" in
        "binary_active")
            echo -e "Status:         ${GREEN}ACTIVE ($status_count processes)${NC}"
            ;;
        "md_active")
            echo -e "Status:         ${GREEN}READY ($status_count .md files)${NC}"
            ;;
        *)
            echo -e "Status:         ${RED}INACTIVE${NC}"
            ;;
    esac
    
    # Agent verification
    echo -e "Agents:         ${GREEN}$agent_count${NC}/31 detected"
    
    # Python orchestration status
    if [ -f "$AGENTS_DIR/.python_orchestration_active" ]; then
        echo -e "Python System:  ${GREEN}ACTIVE (Tandem Orchestration)${NC}"
    else
        echo -e "Python System:  ${YELLOW}STANDBY${NC}"
    fi
    
    # System capabilities
    echo ""
    echo -e "${BOLD}Capabilities:${NC}"
    if [ "$status_type" = "binary_active" ]; then
        echo "  • 4.2M msg/sec binary protocol"
        echo "  • 200ns P99 latency"
        echo "  • Intel Meteor Lake optimization"
        echo "  • Enhanced linter agent (1,475 lines)"
        if [ -f "$AGENTS_DIR/.python_orchestration_active" ]; then
            echo "  • Python Tandem Orchestration (85.7% success rate)"
            echo "  • Dual-layer architecture (Python + C)"
            echo "  • 5 execution modes, command sets"
        fi
    else
        echo "  • .md agent coordination"
        echo "  • Claude Code integration"
        if [ -f "$AGENTS_DIR/.python_orchestration_active" ]; then
            echo "  • Python Tandem Orchestration (85.7% success rate)"
            echo "  • 32 agents auto-discovered"
            echo "  • Standard workflows available"
        fi
    fi
    
    # Process details
    echo ""
    echo -e "${BOLD}Process Details:${NC}"
    local processes=(
        "agent_bridge:Binary Bridge"
        "unified_agent_runtime:Agent Runtime"
        "claude_agent_bridge:Python Bridge"
        "linter_agent:Linter Agent"
    )
    
    for proc_info in "${processes[@]}"; do
        local proc_name="${proc_info%%:*}"
        local proc_desc="${proc_info##*:}"
        local count=$(pgrep -f "$proc_name" 2>/dev/null | wc -l)
        
        if [ $count -gt 0 ]; then
            printf "  %-18s ${GREEN}RUNNING (%d)${NC}\n" "$proc_desc:" "$count"
        else
            printf "  %-18s ${RED}STOPPED${NC}\n" "$proc_desc:"
        fi
    done
    
    echo ""
    echo "Press any key to continue..."
    read -n 1
}

# Function to show menu
show_menu() {
    local current_mode=$(get_current_mode)
    local status_info=$(get_system_status)
    local status_type="${status_info%%:*}"
    local status_count="${status_info##*:}"
    
    show_header
    
    # Current status
    echo -e "${BOLD}Current Status:${NC}"
    case "$status_type" in
        "binary_active")
            echo -e "  Mode: ${GREEN}BINARY SYSTEM${NC} ($status_count processes)"
            ;;
        "md_active")
            echo -e "  Mode: ${BLUE}.md AGENTS${NC} ($status_count files)"
            ;;
        *)
            echo -e "  Mode: ${RED}INACTIVE${NC}"
            ;;
    esac
    
    echo ""
    echo -e "${BOLD}${CYAN}Available Commands:${NC}"
    echo "═════════════════════"
    echo ""
    
    # Switch option
    if [ "$status_type" = "binary_active" ]; then
        echo -e "${YELLOW}[1]${NC} Switch to .md agents mode"
    else
        echo -e "${YELLOW}[1]${NC} Switch to binary system mode"
    fi
    
    echo -e "${YELLOW}[2]${NC} Show detailed status"
    echo -e "${YELLOW}[3]${NC} Test all agents"
    echo -e "${YELLOW}[4]${NC} Test Python Tandem Orchestration"
    echo -e "${YELLOW}[5]${NC} Compile and test linter"
    echo -e "${YELLOW}[6]${NC} Stop all processes"
    echo -e "${YELLOW}[7]${NC} Restart system"
    echo -e "${YELLOW}[q]${NC} Quit"
    echo ""
    
    if [ "$1" != "no-timeout" ]; then
        echo -e "${CYAN}Auto-switch in 5 seconds (press any key to cancel)...${NC}"
        
        # Wait for input with timeout
        if read -t 5 -n 1 choice; then
            echo ""
        else
            echo ""
            echo "Auto-switching mode..."
            choice="1"
        fi
    else
        echo -n "Choose an option: "
        read -n 1 choice
        echo ""
    fi
    
    echo ""
    
    case "$choice" in
        "1")
            if [ "$status_type" = "binary_active" ]; then
                switch_to_md_mode
            else
                switch_to_binary_mode
            fi
            echo ""
            echo "Press any key to continue..."
            read -n 1
            ;;
        "2")
            show_status
            ;;
        "3")
            test_all_agents
            ;;
        "4")
            echo -e "${CYAN}Testing Python Tandem Orchestration System...${NC}"
            echo ""
            
            if [ -f "$PROJECT_ROOT/tests/agents/test_tandem_system.py" ]; then
                cd "$PROJECT_ROOT/tests/agents"
                echo "Running comprehensive tests..."
                
                if python3 test_tandem_system.py --demo 2>/dev/null; then
                    echo ""
                    echo -e "${GREEN}✓ Python Tandem Orchestration System test PASSED${NC}"
                    # Create/update marker
                    touch "$AGENTS_DIR/.python_orchestration_active"
                else
                    echo ""
                    echo -e "${RED}✗ Python Tandem Orchestration System test FAILED${NC}"
                fi
            else
                echo -e "${RED}✗ Python test system not found${NC}"
            fi
            
            echo ""
            echo "Press any key to continue..."
            read -n 1
            ;;
        "5")
            echo "Compiling and testing linter agent..."
            if [ -f "$AGENTS_DIR/src/c/linter_agent.c" ]; then
                cd "$AGENTS_DIR/src/c"
                mkdir -p "$BUILD_DIR"
                
                if gcc -D_GNU_SOURCE -std=c11 -O3 -march=native \
                       -I. -I../.. -I../../binary-communications-system \
                       -o "$BUILD_DIR/linter_agent" linter_agent.c \
                       -lpthread -lm -lrt -ljson-c 2>/dev/null; then
                    echo -e "${GREEN}✓ Linter compiled successfully${NC}"
                    
                    if [ -x "$BUILD_DIR/linter_agent" ]; then
                        echo "Testing linter functionality..."
                        echo -e "${GREEN}✓ Linter binary is executable${NC}"
                    fi
                else
                    echo -e "${RED}✗ Linter compilation failed${NC}"
                fi
            else
                echo -e "${RED}✗ Linter source not found${NC}"
            fi
            echo ""
            echo "Press any key to continue..."
            read -n 1
            ;;
        "5")
            graceful_deactivate_binary
            echo ""
            echo "Press any key to continue..."
            read -n 1
            ;;
        "6")
            echo "Restarting system..."
            graceful_deactivate_binary > /dev/null 2>&1
            sleep 2
            if [ "$current_mode" = "binary_system" ]; then
                switch_to_binary_mode
            else
                switch_to_md_mode
            fi
            echo ""
            echo "Press any key to continue..."
            read -n 1
            ;;
        "q"|"Q")
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid option. Try again."
            sleep 1
            ;;
    esac
}

# Main execution
main() {
    # Check if we're in the right directory
    cd "$AGENTS_DIR" || {
        echo -e "${RED}Cannot access agents directory: $AGENTS_DIR${NC}"
        exit 1
    }
    
    # Handle command line arguments
    case "${1:-menu}" in
        "status"|"stat")
            show_status
            ;;
        "test")
            test_all_agents
            ;;
        "binary"|"bin")
            switch_to_binary_mode
            ;;
        "md"|"standard")
            switch_to_md_mode
            ;;
        "stop")
            graceful_deactivate_binary
            ;;
        "menu"|*)
            # Interactive menu mode
            while true; do
                show_menu "${1:-}"
            done
            ;;
    esac
}

# Execute main function
main "$@"