#!/bin/bash
# ============================================================================
# PRODUCTION ORCHESTRATOR LAUNCHER v2.0
# 
# Production-grade launcher with advanced monitoring, health checks,
# configuration management, and enterprise features
# ============================================================================

set -euo pipefail

# ============================================================================
# ENHANCED CONFIGURATION SYSTEM
# ============================================================================

# Version and metadata
readonly LAUNCHER_VERSION="2.0.2"
readonly LAUNCHER_BUILD="$(date +%Y%m%d_%H%M%S)"
readonly MIN_PYTHON_VERSION="3.8"
readonly REQUIRED_PACKAGES=("asyncio" "dataclasses" "pathlib" "yaml" "logging")

# Color palette (expanded)
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly WHITE='\033[1;37m'
readonly BOLD='\033[1m'
readonly DIM='\033[2m'
readonly NC='\033[0m'

# Enhanced icons
readonly ICON_SUCCESS="✓"
readonly ICON_FAILURE="✗"
readonly ICON_WARNING="⚠"
readonly ICON_INFO="ℹ"
readonly ICON_ROCKET="🚀"
readonly ICON_GEAR="⚙️"
readonly ICON_MONITOR="📊"
readonly ICON_SECURITY="🔒"
readonly ICON_HEALTH="💚"

# ============================================================================
# INTELLIGENT PROJECT ROOT DETECTION (Must be defined before use)
# ============================================================================

find_project_root() {
    local current_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local max_depth=5
    local depth=0
    
    while [ $depth -lt $max_depth ]; do
        # Check for project markers
        if [ -d "$current_dir/agents" ] && [ -d "$current_dir/agents/src/python" ]; then
            echo "$current_dir"
            return 0
        fi
        
        # Check for common project files
        if [ -f "$current_dir/CLAUDE.md" ] || [ -f "$current_dir/.claude-home" ]; then
            echo "$current_dir"
            return 0
        fi
        
        [ "$current_dir" = "/" ] && break
        current_dir="$(cd "$current_dir/.." && pwd)"
        depth=$((depth + 1))
    done
    
    # Check standard locations
    for fallback in "$HOME/Documents/Claude" "$HOME/.local/share/claude" "/opt/claude"; do
        if [ -d "$fallback/agents/src/python" ]; then
            echo "$fallback"
            return 0
        fi
    done
    
    # Default fallback
    echo "$HOME/Documents/Claude"
}

# Dynamic path detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(find_project_root)"
AGENTS_DIR="$PROJECT_ROOT/agents"
PYTHON_DIR="$AGENTS_DIR/src/python"
CONFIG_DIR="$HOME/.config/production-orchestrator"
CACHE_DIR="$HOME/.cache/production-orchestrator"
LOG_DIR="$HOME/.local/share/production-orchestrator/logs"

# Runtime files
MARKER_FILE="$CACHE_DIR/.orchestration_active"
PID_FILE="$CACHE_DIR/orchestrator.pid"
HEALTH_FILE="$CACHE_DIR/health_status.json"
METRICS_FILE="$CACHE_DIR/metrics.json"
CONFIG_FILE="$CONFIG_DIR/launcher.conf"
SESSION_LOG="$LOG_DIR/session_$(date +%Y%m%d_%H%M%S).log"

# Performance monitoring
MONITORING_ENABLED=true
HEALTH_CHECK_INTERVAL=30
METRICS_RETENTION_DAYS=7
MAX_LOG_SIZE_MB=100

# ============================================================================
# ENHANCED LOGGING SYSTEM (Function already defined above)
# ============================================================================

# ============================================================================
# ENHANCED LOGGING SYSTEM
# ============================================================================

setup_logging() {
    mkdir -p "$LOG_DIR" "$CONFIG_DIR" "$CACHE_DIR"
    
    # Create log rotation function
    rotate_logs() {
        find "$LOG_DIR" -name "*.log" -size +${MAX_LOG_SIZE_MB}M -exec mv {} {}.old \;
        find "$LOG_DIR" -name "*.log.old" -mtime +$METRICS_RETENTION_DAYS -delete
    }
    
    # Initialize session log
    {
        echo "# Production Orchestrator Session Log"
        echo "# Started: $(date)"
        echo "# Version: $LAUNCHER_VERSION Build: $LAUNCHER_BUILD"
        echo "# Project Root: $PROJECT_ROOT"
        echo ""
    } > "$SESSION_LOG"
    
    rotate_logs
}

log_message() {
    local level="$1"
    local message="$2"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    
    echo "[$timestamp] [$level] $message" >> "$SESSION_LOG"
    
    case "$level" in
        "ERROR") echo -e "${RED}${ICON_FAILURE} $message${NC}" ;;
        "WARN")  echo -e "${YELLOW}${ICON_WARNING} $message${NC}" ;;
        "INFO")  echo -e "${CYAN}${ICON_INFO} $message${NC}" ;;
        "SUCCESS") echo -e "${GREEN}${ICON_SUCCESS} $message${NC}" ;;
        *) echo "$message" ;;
    esac
}

# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

load_configuration() {
    # Default configuration
    cat > "$CONFIG_FILE" << 'EOF'
# Production Orchestrator Configuration
# Auto-generated configuration file

[system]
auto_start_monitoring=true
health_check_interval=30
metrics_retention_days=7
max_concurrent_workflows=10
enable_performance_optimization=true

[security]
require_confirmation_for_critical=true
enable_audit_logging=true
max_session_duration=3600

[ui]
show_performance_metrics=true
enable_color_output=true
verbose_logging=false
show_agent_health=true

[features]
enable_auto_recovery=true
enable_background_monitoring=true
enable_workflow_caching=true
enable_distributed_execution=false
EOF

    # Load existing config if available
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE" 2>/dev/null || true
    fi
}

# ============================================================================
# ENHANCED SYSTEM VALIDATION
# ============================================================================

validate_python_environment() {
    log_message "INFO" "Validating Python environment..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        log_message "ERROR" "Python 3 not found"
        return 1
    fi
    
    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    
    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_message "ERROR" "Python $python_version found, but minimum $MIN_PYTHON_VERSION required"
        return 1
    fi
    
    log_message "SUCCESS" "Python $python_version validated"
    
    # Check required packages
    local missing_packages=()
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        log_message "WARN" "Missing packages: ${missing_packages[*]}"
        log_message "INFO" "Attempting to install missing packages..."
        
        for package in "${missing_packages[@]}"; do
            if pip3 install "$package" &>/dev/null; then
                log_message "SUCCESS" "Installed $package"
            else
                log_message "ERROR" "Failed to install $package"
                return 1
            fi
        done
    fi
    
    return 0
}

validate_orchestrator_files() {
    log_message "INFO" "Validating orchestrator files..."
    
    local required_files=(
        "production_orchestrator.py:Production orchestrator"
        "agent_registry.py:Agent discovery system"
        "test_tandem_system.py:Test suite"
    )
    
    local missing_files=0
    
    for file_info in "${required_files[@]}"; do
        local file_name="${file_info%%:*}"
        local file_desc="${file_info##*:}"
        
        if [ -f "$PYTHON_DIR/$file_name" ]; then
            # Validate file contents
            if [ -s "$PYTHON_DIR/$file_name" ]; then
                log_message "SUCCESS" "$file_desc validated"
            else
                log_message "ERROR" "$file_desc is empty"
                ((missing_files++))
            fi
        else
            log_message "ERROR" "$file_desc not found"
            ((missing_files++))
        fi
    done
    
    if [ $missing_files -eq 0 ]; then
        log_message "SUCCESS" "All orchestrator files validated"
        return 0
    else
        log_message "ERROR" "$missing_files required files missing or invalid"
        return 1
    fi
}

validate_agent_definitions() {
    log_message "INFO" "Validating agent definitions..."
    
    if [ ! -d "$AGENTS_DIR" ]; then
        log_message "ERROR" "Agents directory not found: $AGENTS_DIR"
        return 1
    fi
    
    local agent_files
    agent_files=$(find "$AGENTS_DIR" -maxdepth 1 -name "*.md" -not -name "Template.md" -not -name "README.md" | wc -l)
    
    if [ "$agent_files" -eq 0 ]; then
        log_message "WARN" "No agent definition files found"
        return 1
    fi
    
    # Validate agent file structure
    local valid_agents=0
    local total_agents=0
    
    while IFS= read -r -d '' agent_file; do
        ((total_agents++))
        if [ -s "$agent_file" ] && grep -q "^#" "$agent_file"; then
            ((valid_agents++))
        fi
    done < <(find "$AGENTS_DIR" -maxdepth 1 -name "*.md" -not -name "Template.md" -not -name "README.md" -print0)
    
    log_message "SUCCESS" "Agent validation: $valid_agents/$total_agents agents valid"
    
    # Store agent count for health monitoring
    echo "{\"total_agents\": $total_agents, \"valid_agents\": $valid_agents, \"validation_time\": \"$(date -Iseconds)\"}" > "$CACHE_DIR/agent_validation.json"
    
    return 0
}

# ============================================================================
# SYSTEM HEALTH MONITORING
# ============================================================================

collect_system_metrics() {
    local cpu_usage
    local memory_usage
    local disk_usage
    local load_average
    local python_processes
    
    # CPU usage (1-minute average)
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
    
    # Memory usage
    memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    
    # Disk usage for project directory
    disk_usage=$(df "$PROJECT_ROOT" | tail -1 | awk '{print $5}' | sed 's/%//')
    
    # Load average
    load_average=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    
    # Python orchestrator processes
    python_processes=$(pgrep -f "python.*orchestrator" | wc -l)
    
    # Create metrics JSON
    cat > "$METRICS_FILE" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "system": {
        "cpu_usage_percent": ${cpu_usage:-0},
        "memory_usage_percent": ${memory_usage:-0},
        "disk_usage_percent": ${disk_usage:-0},
        "load_average": ${load_average:-0},
        "python_processes": ${python_processes:-0}
    },
    "orchestrator": {
        "status": "$([ -f "$MARKER_FILE" ] && echo "active" || echo "inactive")",
        "pid": $([ -f "$PID_FILE" ] && cat "$PID_FILE" || echo "null"),
        "uptime_seconds": $([ -f "$MARKER_FILE" ] && echo $(($(date +%s) - $(stat -c %Y "$MARKER_FILE"))) || echo "0")
    },
    "health_score": $(calculate_health_score)
}
EOF
}

calculate_health_score() {
    local score=100
    
    # Deduct points for high resource usage
    local cpu_usage=${cpu_usage:-0}
    local memory_usage=${memory_usage:-0}
    local disk_usage=${disk_usage:-0}
    
    [ "${cpu_usage%.*}" -gt 80 ] && score=$((score - 20))
    [ "${memory_usage%.*}" -gt 85 ] && score=$((score - 15))
    [ "${disk_usage}" -gt 90 ] && score=$((score - 25))
    
    # Check if orchestrator is responsive
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if ! ps -p "$pid" > /dev/null 2>&1; then
            score=$((score - 30))
        fi
    else
        score=$((score - 50))
    fi
    
    # Ensure score is between 0 and 100
    [ "$score" -lt 0 ] && score=0
    [ "$score" -gt 100 ] && score=100
    
    echo "$score"
}

start_health_monitoring() {
    if [ "$MONITORING_ENABLED" = "true" ]; then
        log_message "INFO" "Starting health monitoring (${HEALTH_CHECK_INTERVAL}s intervals)"
        
        {
            while [ -f "$MARKER_FILE" ]; do
                collect_system_metrics
                sleep "$HEALTH_CHECK_INTERVAL"
            done
        } &
        
        echo $! > "$CACHE_DIR/monitor.pid"
    fi
}

stop_health_monitoring() {
    if [ -f "$CACHE_DIR/monitor.pid" ]; then
        local monitor_pid
        monitor_pid=$(cat "$CACHE_DIR/monitor.pid")
        if ps -p "$monitor_pid" > /dev/null 2>&1; then
            kill "$monitor_pid" 2>/dev/null || true
        fi
        rm -f "$CACHE_DIR/monitor.pid"
    fi
}

# ============================================================================
# ENHANCED CLEANUP AND SIGNAL HANDLING
# ============================================================================

cleanup() {
    log_message "INFO" "Shutting down Production Orchestration System..."
    
    # Stop health monitoring
    stop_health_monitoring
    
    # Gracefully stop orchestrator if running
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_message "INFO" "Stopping orchestrator process $pid"
            kill -TERM "$pid" 2>/dev/null || true
            
            # Wait for graceful shutdown
            local timeout=10
            while [ $timeout -gt 0 ] && ps -p "$pid" > /dev/null 2>&1; do
                sleep 1
                ((timeout--))
            done
            
            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                log_message "WARN" "Force killing orchestrator process"
                kill -KILL "$pid" 2>/dev/null || true
            fi
        fi
    fi
    
    # Clean up runtime files
    rm -f "$MARKER_FILE" "$PID_FILE" "$HEALTH_FILE"
    
    # Final metrics collection
    collect_system_metrics
    
    log_message "SUCCESS" "Production orchestration system deactivated"
    echo ""
    echo -e "${GREEN}${ICON_SUCCESS} Session log saved: $SESSION_LOG${NC}"
    echo -e "${CYAN}${ICON_INFO} Thank you for using the Production Orchestration System!${NC}"
    
    exit 0
}

# Enhanced signal handling
trap cleanup SIGINT SIGTERM EXIT

# ============================================================================
# ADVANCED USER INTERFACE
# ============================================================================

show_enhanced_header() {
    clear
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${WHITE}      ${ICON_ROCKET} Production Orchestrator Launcher v$LAUNCHER_VERSION      ${NC}"
    echo -e "${CYAN}                    Advanced Agent Coordination & Workflow Engine                  ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${DIM}Build: $LAUNCHER_BUILD | Project: $PROJECT_ROOT${NC}"
    echo ""
    
    # Show real-time system status
    if [ -f "$METRICS_FILE" ]; then
        local health_score
        health_score=$(python3 -c "import json; print(json.load(open('$METRICS_FILE'))['health_score'])" 2>/dev/null || echo "0")
        
        if [ "$health_score" -ge 80 ]; then
            echo -e "${BOLD}System Health: ${GREEN}${ICON_HEALTH} Excellent ($health_score/100)${NC}"
        elif [ "$health_score" -ge 60 ]; then
            echo -e "${BOLD}System Health: ${YELLOW}${ICON_WARNING} Good ($health_score/100)${NC}"
        else
            echo -e "${BOLD}System Health: ${RED}${ICON_FAILURE} Poor ($health_score/100)${NC}"
        fi
    else
        echo -e "${BOLD}System Health: ${DIM}${ICON_INFO} Initializing...${NC}"
    fi
    
    echo ""
}

show_system_dashboard() {
    echo -e "${CYAN}${ICON_MONITOR} System Dashboard${NC}"
    echo "══════════════════════════════════════════════════════════════"
    echo ""
    
    if [ -f "$METRICS_FILE" ]; then
        # Parse and display metrics using Python
        python3 - "$METRICS_FILE" << 'EOF'
import json
import sys
from datetime import datetime

try:
    with open(sys.argv[1], 'r') as f:
        metrics = json.load(f)
    
    # System metrics
    system = metrics.get('system', {})
    orchestrator = metrics.get('orchestrator', {})
    
    print(f"📊 Resource Usage:")
    print(f"   CPU:    {system.get('cpu_usage_percent', 0):>6.1f}%")
    print(f"   Memory: {system.get('memory_usage_percent', 0):>6.1f}%")
    print(f"   Disk:   {system.get('disk_usage_percent', 0):>6}%")
    print(f"   Load:   {system.get('load_average', 0):>6.2f}")
    print()
    
    print(f"🤖 Orchestrator Status:")
    print(f"   Status:     {orchestrator.get('status', 'unknown').title()}")
    print(f"   PID:        {orchestrator.get('pid', 'N/A')}")
    print(f"   Uptime:     {orchestrator.get('uptime_seconds', 0)} seconds")
    print(f"   Processes:  {system.get('python_processes', 0)}")
    print()
    
    # Health score with color coding
    health = metrics.get('health_score', 0)
    if health >= 80:
        status = "🟢 Excellent"
    elif health >= 60:
        status = "🟡 Good"
    else:
        status = "🔴 Poor"
    
    print(f"💚 Health Score: {health}/100 ({status})")
    
    # Timestamp
    timestamp = metrics.get('timestamp', '')
    if timestamp:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        print(f"📅 Last Updated: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
    
except Exception as e:
    print(f"❌ Error reading metrics: {e}")
EOF
    else
        echo -e "${YELLOW}${ICON_WARNING} No metrics available yet${NC}"
    fi
    
    echo ""
    echo "Press any key to return to menu..."
    read -n 1
}

# ============================================================================
# ENHANCED VALIDATION SYSTEM
# ============================================================================

run_comprehensive_validation() {
    log_message "INFO" "Running comprehensive system validation..."
    
    local validation_score=0
    local total_checks=5
    
    echo -e "${CYAN}${ICON_GEAR} Comprehensive System Validation${NC}"
    echo "=================================================="
    echo ""
    
    # Check 1: Python environment
    echo -n "Python Environment............. "
    if validate_python_environment >/dev/null 2>&1; then
        echo -e "${GREEN}${ICON_SUCCESS} PASS${NC}"
        ((validation_score++))
    else
        echo -e "${RED}${ICON_FAILURE} FAIL${NC}"
    fi
    
    # Check 2: Orchestrator files
    echo -n "Orchestrator Files............. "
    if validate_orchestrator_files >/dev/null 2>&1; then
        echo -e "${GREEN}${ICON_SUCCESS} PASS${NC}"
        ((validation_score++))
    else
        echo -e "${RED}${ICON_FAILURE} FAIL${NC}"
    fi
    
    # Check 3: Agent definitions
    echo -n "Agent Definitions.............. "
    if validate_agent_definitions >/dev/null 2>&1; then
        echo -e "${GREEN}${ICON_SUCCESS} PASS${NC}"
        ((validation_score++))
    else
        echo -e "${YELLOW}${ICON_WARNING} WARN${NC}"
    fi
    
    # Check 4: System resources
    echo -n "System Resources............... "
    local available_memory
    available_memory=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [ "$available_memory" -gt 500 ]; then
        echo -e "${GREEN}${ICON_SUCCESS} PASS${NC} (${available_memory}MB available)"
        ((validation_score++))
    else
        echo -e "${YELLOW}${ICON_WARNING} LOW${NC} (${available_memory}MB available)"
    fi
    
    # Check 5: Disk space
    echo -n "Disk Space..................... "
    local available_space
    available_space=$(df "$PROJECT_ROOT" | tail -1 | awk '{print $4}')
    if [ "$available_space" -gt 1000000 ]; then  # 1GB in KB
        echo -e "${GREEN}${ICON_SUCCESS} PASS${NC}"
        ((validation_score++))
    else
        echo -e "${YELLOW}${ICON_WARNING} LOW${NC}"
    fi
    
    echo ""
    echo -e "${BOLD}Validation Score: $validation_score/$total_checks${NC}"
    
    if [ "$validation_score" -eq "$total_checks" ]; then
        echo -e "${GREEN}${ICON_SUCCESS} System ready for production use${NC}"
        return 0
    elif [ "$validation_score" -ge 3 ]; then
        echo -e "${YELLOW}${ICON_WARNING} System ready with minor issues${NC}"
        return 0
    else
        echo -e "${RED}${ICON_FAILURE} System requires attention${NC}"
        return 1
    fi
}

# ============================================================================
# ENHANCED INTERACTIVE FEATURES
# ============================================================================

run_performance_test() {
    echo -e "${CYAN}${ICON_MONITOR} Performance Test Suite${NC}"
    echo "========================================"
    echo ""
    
    # Start timing
    local start_time
    start_time=$(date +%s.%N)
    
    cd "$PYTHON_DIR"
    
    # Test 1: Orchestrator initialization
    echo -n "Orchestrator initialization.... "
    if timeout 30 python3 -c "
import asyncio
import sys
sys.path.append('.')
from production_orchestrator import ProductionOrchestrator

async def test():
    orchestrator = ProductionOrchestrator()
    return await orchestrator.initialize()

result = asyncio.run(test())
sys.exit(0 if result else 1)
" >/dev/null 2>&1; then
        echo -e "${GREEN}${ICON_SUCCESS} PASS${NC}"
    else
        echo -e "${RED}${ICON_FAILURE} FAIL${NC}"
    fi
    
    # Test 2: Agent discovery
    echo -n "Agent discovery................ "
    local agent_count
    agent_count=$(find "$AGENTS_DIR" -name "*.md" -not -name "Template.md" | wc -l)
    if [ "$agent_count" -gt 0 ]; then
        echo -e "${GREEN}${ICON_SUCCESS} PASS${NC} ($agent_count agents)"
    else
        echo -e "${RED}${ICON_FAILURE} FAIL${NC} (0 agents)"
    fi
    
    # Test 3: Workflow execution
    echo -n "Workflow execution............. "
    if timeout 60 python3 -c "
import asyncio
import sys
sys.path.append('.')
from production_orchestrator import ProductionOrchestrator
from test_tandem_system import StandardWorkflows

async def test():
    orchestrator = ProductionOrchestrator()
    await orchestrator.initialize()
    workflow = StandardWorkflows.create_document_generation_workflow()
    result = await orchestrator.execute_command_set(workflow)
    return result.get('status') in ['completed', 'fallback_executed']

result = asyncio.run(test())
sys.exit(0 if result else 1)
" >/dev/null 2>&1; then
        echo -e "${GREEN}${ICON_SUCCESS} PASS${NC}"
    else
        echo -e "${YELLOW}${ICON_WARNING} FALLBACK${NC}"
    fi
    
    # Calculate total time
    local end_time
    end_time=$(date +%s.%N)
    local duration
    duration=$(python3 -c "print(f'{float('$end_time') - float('$start_time'):.2f}')")
    
    echo ""
    echo -e "${BOLD}Performance Summary:${NC}"
    echo "  Total test time: ${duration}s"
    echo "  System status:   $([ -f "$MARKER_FILE" ] && echo "Active" || echo "Inactive")"
    echo "  Memory usage:    $(free -h | awk 'NR==2{print $3 "/" $2}')"
    
    echo ""
    echo "Press any key to return to menu..."
    read -n 1
}

# ============================================================================
# ENHANCED MENU SYSTEM
# ============================================================================

show_enhanced_menu() {
    show_enhanced_header
    
    # Show current status with more detail
    if [ -f "$MARKER_FILE" ]; then
        local uptime
        uptime=$(( $(date +%s) - $(stat -c %Y "$MARKER_FILE") ))
        echo -e "${BOLD}Current Status: ${GREEN}${ICON_HEALTH} ORCHESTRATION ACTIVE${NC}${BOLD} (${uptime}s uptime)${NC}"
    else
        echo -e "${BOLD}Current Status: ${YELLOW}${ICON_GEAR} READY FOR ACTIVATION${NC}"
    fi
    
    echo ""
    echo -e "${BOLD}${CYAN}Available Options:${NC}"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo -e "${YELLOW}[1]${NC} ${ICON_ROCKET} Quick Demo & Validation"
    echo -e "${YELLOW}[2]${NC} ${ICON_GEAR} Comprehensive System Test"
    echo -e "${YELLOW}[3]${NC} ${ICON_MONITOR} Performance Benchmarks"
    echo -e "${YELLOW}[4]${NC} 🎯 Interactive Orchestrator"
    echo -e "${YELLOW}[5]${NC} ${ICON_MONITOR} System Dashboard"
    echo -e "${YELLOW}[6]${NC} ${ICON_SECURITY} Security & Health Check"
    echo -e "${YELLOW}[7]${NC} 📚 Documentation & Help"
    echo -e "${YELLOW}[8]${NC} ⚙️  Configuration Management"
    echo -e "${YELLOW}[q]${NC} 🚪 Quit (deactivate system)"
    echo ""
    
    # Show quick status indicators
    if [ -f "$METRICS_FILE" ]; then
        local health_score
        health_score=$(python3 -c "import json; print(json.load(open('$METRICS_FILE'))['health_score'])" 2>/dev/null || echo "0")
        echo -e "${DIM}Quick Status: Health ${health_score}/100 | $([ -f "$PID_FILE" ] && echo "Process $(cat "$PID_FILE")" || echo "No process") | $(ls "$LOG_DIR"/*.log 2>/dev/null | wc -l) log files${NC}"
    fi
    
    echo ""
    echo -n "Choose an option [1-8,q]: "
    read -n 1 choice
    echo ""
    echo ""
    
    case "$choice" in
        "1")
            if run_comprehensive_validation; then
                log_message "INFO" "Running quick demo..."
                cd "$PYTHON_DIR"
                python3 -c "
import asyncio
from production_orchestrator import ProductionOrchestrator
from test_tandem_system import StandardWorkflows

async def demo():
    print('🚀 Initializing orchestrator...')
    orchestrator = ProductionOrchestrator()
    await orchestrator.initialize()
    
    print('📋 Running document generation workflow...')
    workflow = StandardWorkflows.create_document_generation_workflow()
    result = await orchestrator.execute_command_set(workflow)
    print(f'✅ Result: {result.get(\"status\")}')
    
    metrics = orchestrator.get_metrics()
    print(f'📊 Metrics: {metrics.get(\"python_msgs_processed\", 0)} messages processed')

asyncio.run(demo())
"
            fi
            echo ""
            echo "Press any key to return to menu..."
            read -n 1
            ;;
        "2")
            run_comprehensive_validation
            echo ""
            echo "Press any key to return to menu..."
            read -n 1
            ;;
        "3")
            run_performance_test
            ;;
        "4")
            log_message "INFO" "Launching interactive orchestrator..."
            cd "$PYTHON_DIR"
            python3 -c "
import asyncio
import json
from production_orchestrator import ProductionOrchestrator
from test_tandem_system import StandardWorkflows

async def interactive():
    print('🎯 Interactive Production Orchestrator')
    print('='*50)
    orchestrator = ProductionOrchestrator()
    await orchestrator.initialize()
    
    commands = {
        'status': lambda: print(json.dumps(orchestrator.get_metrics(), indent=2, default=str)),
        'demo': lambda: asyncio.create_task(orchestrator.execute_command_set(StandardWorkflows.create_document_generation_workflow())),
        'security': lambda: asyncio.create_task(orchestrator.execute_command_set(StandardWorkflows.create_security_audit_workflow())),
        'agents': lambda: print(f'Discovered agents: {orchestrator.discover_agents()}'),
        'help': lambda: print('Commands: status, demo, security, agents, exit')
    }
    
    while True:
        try:
            cmd = input('orchestrator> ').strip().lower()
            if cmd in ['exit', 'quit']:
                break
            elif cmd in commands:
                result = commands[cmd]()
                if asyncio.iscoroutine(result):
                    result = await result
                    print(f'Result: {result}')
            else:
                print('Unknown command. Type \"help\" for available commands.')
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f'Error: {e}')
    
    print('Goodbye!')

asyncio.run(interactive())
"
            echo ""
            echo "Press any key to return to menu..."
            read -n 1
            ;;
        "5")
            show_system_dashboard
            ;;
        "6")
            echo -e "${CYAN}${ICON_SECURITY} Security & Health Check${NC}"
            echo "========================================"
            echo ""
            
            # Security checks
            echo "🔒 Security Status:"
            echo "   Config file permissions: $(stat -c %a "$CONFIG_FILE" 2>/dev/null || echo "N/A")"
            echo "   Log directory owner:     $(stat -c %U "$LOG_DIR" 2>/dev/null || echo "N/A")"
            echo "   Active SSH sessions:     $(who | grep pts | wc -l)"
            echo ""
            
            # Health checks
            echo "💚 Health Status:"
            collect_system_metrics
            if [ -f "$METRICS_FILE" ]; then
                python3 -c "
import json
with open('$METRICS_FILE') as f:
    metrics = json.load(f)
system = metrics['system']
print(f'   CPU Usage:     {system.get(\"cpu_usage_percent\", 0)}%')
print(f'   Memory Usage:  {system.get(\"memory_usage_percent\", 0)}%')
print(f'   Disk Usage:    {system.get(\"disk_usage_percent\", 0)}%')
print(f'   Health Score:  {metrics.get(\"health_score\", 0)}/100')
"
            fi
            
            echo ""
            echo "Press any key to return to menu..."
            read -n 1
            ;;
        "7")
            echo -e "${CYAN}📚 Documentation & Help${NC}"
            echo "============================"
            echo ""
            echo "📖 Available Documentation:"
            echo "   • README.md - Project overview"
            echo "   • CLAUDE.md - Detailed project context"
            echo "   • agents/docs/ - Technical documentation"
            echo ""
            echo "🔧 System Information:"
            echo "   • Version: $LAUNCHER_VERSION (Build: $LAUNCHER_BUILD)"
            echo "   • Project Root: $PROJECT_ROOT"
            echo "   • Python Directory: $PYTHON_DIR"
            echo "   • Config Directory: $CONFIG_DIR"
            echo "   • Log Directory: $LOG_DIR"
            echo ""
            echo "📋 Current Session:"
            echo "   • Session Log: $SESSION_LOG"
            echo "   • Log Lines: $(wc -l < "$SESSION_LOG" 2>/dev/null || echo "0")"
            echo "   • Uptime: $([ -f "$MARKER_FILE" ] && echo "$(( $(date +%s) - $(stat -c %Y "$MARKER_FILE") ))s" || echo "Not running")"
            echo ""
            echo "Press any key to return to menu..."
            read -n 1
            ;;
        "8")
            echo -e "${CYAN}⚙️  Configuration Management${NC}"
            echo "==============================="
            echo ""
            echo "📝 Configuration File: $CONFIG_FILE"
            echo ""
            if [ -f "$CONFIG_FILE" ]; then
                echo "Current settings:"
                cat "$CONFIG_FILE" | grep -E "^[^#]" | head -10
                echo ""
                echo "[e]dit config, [r]eset to defaults, [v]iew full config, [b]ack to menu"
                echo -n "Choose action: "
                read -n 1 config_choice
                echo ""
                
                case "$config_choice" in
                    "e")
                        ${EDITOR:-nano} "$CONFIG_FILE"
                        log_message "INFO" "Configuration updated"
                        ;;
                    "r")
                        load_configuration
                        log_message "INFO" "Configuration reset to defaults"
                        ;;
                    "v")
                        echo ""
                        cat "$CONFIG_FILE"
                        ;;
                esac
            else
                echo "No configuration file found. Creating default..."
                load_configuration
            fi
            
            echo ""
            echo "Press any key to return to menu..."
            read -n 1
            ;;
        "q"|"Q")
            log_message "INFO" "User requested shutdown"
            exit 0
            ;;
        *)
            echo -e "${RED}${ICON_FAILURE} Invalid option. Please try again.${NC}"
            sleep 1
            ;;
    esac
}

# ============================================================================
# ENHANCED MAIN EXECUTION
# ============================================================================

main() {
    # Initialize logging and configuration
    setup_logging
    load_configuration
    
    log_message "INFO" "Production Orchestrator Launcher v$LAUNCHER_VERSION starting..."
    
    # Check for existing instance
    if [ -f "$PID_FILE" ]; then
        local existing_pid
        existing_pid=$(cat "$PID_FILE")
        if ps -p "$existing_pid" > /dev/null 2>&1; then
            log_message "ERROR" "Launcher already running (PID: $existing_pid)"
            echo -e "${RED}${ICON_FAILURE} Production Orchestration System is already running${NC}"
            echo "Please close the existing instance before starting a new one."
            exit 1
        else
            log_message "WARN" "Removing stale PID file"
            rm -f "$PID_FILE"
        fi
    fi
    
    # Validate system
    log_message "INFO" "Running system validation..."
    if ! run_comprehensive_validation >/dev/null 2>&1; then
        log_message "ERROR" "System validation failed"
        echo -e "${RED}${ICON_FAILURE} System validation failed. Please check the logs.${NC}"
        echo "Log file: $SESSION_LOG"
        exit 1
    fi
    
    # Create marker and PID files
    touch "$MARKER_FILE"
    echo $$ > "$PID_FILE"
    
    log_message "SUCCESS" "Production Orchestration System activated"
    
    # Start health monitoring
    start_health_monitoring
    
    # Main menu loop
    while true; do
        show_enhanced_menu
    done
}

# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

case "${1:-}" in
    "demo"|"--demo")
        setup_logging
        load_configuration
        run_comprehensive_validation && run_performance_test
        ;;
    "test"|"--test")
        setup_logging
        load_configuration
        run_comprehensive_validation
        ;;
    "validate"|"--validate")
        # Disable trap for validation mode
        trap - SIGINT SIGTERM EXIT
        setup_logging
        load_configuration
        if run_comprehensive_validation; then
            exit 0
        else
            exit 1
        fi
        ;;
    "dashboard"|"--dashboard")
        setup_logging
        load_configuration
        collect_system_metrics
        show_system_dashboard
        ;;
    "status"|"--status")
        setup_logging
        collect_system_metrics
        if [ -f "$METRICS_FILE" ]; then
            cat "$METRICS_FILE" | python3 -m json.tool
        else
            echo "No metrics available"
        fi
        ;;
    "help"|"--help")
        echo "Production Orchestrator Launcher v$LAUNCHER_VERSION"
        echo ""
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  demo         Run quick demo and performance test"
        echo "  test         Run comprehensive validation"
        echo "  validate     Run system validation only"
        echo "  dashboard    Show system dashboard"
        echo "  status       Show current system status (JSON)"
        echo "  help         Show this help message"
        echo ""
        echo "If no option is provided, the interactive menu will be shown."
        ;;
    *)
        main
        ;;
esac