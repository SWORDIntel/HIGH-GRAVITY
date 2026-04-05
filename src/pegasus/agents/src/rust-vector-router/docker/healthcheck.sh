#!/bin/bash

# Health Check Script for Claude Agent Communication System
# Validates agent status and ultra-fast protocol connectivity

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_HOME="${AGENT_HOME:-/app}"
UFP_SOCKET_PATH="${UFP_SHARED_MEMORY_PATH:-/dev/shm/claude_agents}"
MESSAGE_ROUTER_HOST="${MESSAGE_ROUTER_HOST:-message-router:8081}"
TIMEOUT=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >&2
}

# Check if running as correct user
check_user() {
    if [[ $(id -u) -eq 0 ]]; then
        log "${RED}ERROR: Health check should not run as root${NC}"
        exit 1
    fi
}

# Check ultra-fast protocol shared memory
check_ufp_shared_memory() {
    log "Checking Ultra-Fast Protocol shared memory..."
    
    if [[ ! -d "/dev/shm" ]]; then
        log "${RED}ERROR: /dev/shm not available${NC}"
        return 1
    fi
    
    # Check if shared memory region exists
    if [[ -e "${UFP_SOCKET_PATH}" ]]; then
        log "${GREEN}✓ UFP shared memory available${NC}"
        return 0
    else
        log "${YELLOW}WARN: UFP shared memory not initialized${NC}"
        return 1
    fi
}

# Check agent-specific health based on type
check_agent_health() {
    local agent_type="${1:-unknown}"
    
    case "${agent_type}" in
        "message-router")
            check_message_router
            ;;
        "director")
            check_director_agent
            ;;
        "voice-recognition")
            check_voice_agent
            ;;
        "monitor")
            check_monitor_agent
            ;;
        *)
            check_generic_agent "${agent_type}"
            ;;
    esac
}

# Check message router health
check_message_router() {
    log "Checking Message Router health..."
    
    # Check if process is running
    if pgrep -f "ultra_message_router" > /dev/null; then
        log "${GREEN}✓ Message Router process running${NC}"
    else
        log "${RED}ERROR: Message Router process not found${NC}"
        exit 1
    fi
    
    # Check admin interface
    if curl -sf "http://localhost:8080/health" > /dev/null 2>&1; then
        log "${GREEN}✓ Message Router admin interface responsive${NC}"
    else
        log "${RED}ERROR: Message Router admin interface not accessible${NC}"
        exit 1
    fi
    
    # Check agent discovery port
    if netstat -ln | grep -q ":8081"; then
        log "${GREEN}✓ Message Router discovery port listening${NC}"
    else
        log "${RED}ERROR: Message Router discovery port not listening${NC}"
        exit 1
    fi
    
    # Check UFP statistics
    if [[ -f "${AGENT_HOME}/bin/ufp_stats" ]]; then
        stats_output=$("${AGENT_HOME}/bin/ufp_stats" 2>/dev/null || echo "")
        if [[ -n "${stats_output}" ]]; then
            log "${GREEN}✓ UFP statistics available${NC}"
            # Extract key metrics
            msg_rate=$(echo "${stats_output}" | grep -o 'msg_rate: [0-9]*' | cut -d' ' -f2)
            if [[ -n "${msg_rate}" && ${msg_rate} -gt 0 ]]; then
                log "${GREEN}✓ Message processing rate: ${msg_rate} msg/sec${NC}"
            fi
        else
            log "${YELLOW}WARN: UFP statistics not available${NC}"
        fi
    fi
}

# Check Director agent health
check_director_agent() {
    log "Checking Director Agent health..."
    
    # Check Python process
    if pgrep -f "director_agent.py" > /dev/null; then
        log "${GREEN}✓ Director Agent process running${NC}"
    else
        log "${RED}ERROR: Director Agent process not found${NC}"
        exit 1
    fi
    
    # Check agent registration with message router
    if check_agent_registration "DIRECTOR"; then
        log "${GREEN}✓ Director Agent registered with message router${NC}"
    else
        log "${RED}ERROR: Director Agent not registered${NC}"
        exit 1
    fi
    
    # Check working directory permissions
    if [[ -w "${AGENT_DATA_DIR:-/app/data}" ]]; then
        log "${GREEN}✓ Data directory writable${NC}"
    else
        log "${RED}ERROR: Data directory not writable${NC}"
        exit 1
    fi
}

# Check Voice Recognition agent health
check_voice_agent() {
    log "Checking Voice Recognition Agent health..."
    
    # Check Rust process
    if pgrep -f "voice-agent-system" > /dev/null; then
        log "${GREEN}✓ Voice Recognition process running${NC}"
    else
        log "${RED}ERROR: Voice Recognition process not found${NC}"
        exit 1
    fi
    
    # Check audio devices
    if [[ -e "/dev/snd" ]]; then
        log "${GREEN}✓ Audio devices available${NC}"
    else
        log "${YELLOW}WARN: Audio devices not available${NC}"
    fi
    
    # Check Intel accelerators
    check_intel_accelerators
    
    # Check voice configuration
    if [[ -f "${AGENT_CONFIG_DIR}/voice_config.json" ]]; then
        if python3 -c "import json; json.load(open('${AGENT_CONFIG_DIR}/voice_config.json'))" 2>/dev/null; then
            log "${GREEN}✓ Voice configuration valid${NC}"
        else
            log "${RED}ERROR: Voice configuration invalid${NC}"
            exit 1
        fi
    else
        log "${YELLOW}WARN: Voice configuration not found${NC}"
    fi
}

# Check Monitor agent health
check_monitor_agent() {
    log "Checking Monitor Agent health..."
    
    # Check process
    if pgrep -f "monitor_agent.py" > /dev/null; then
        log "${GREEN}✓ Monitor Agent process running${NC}"
    else
        log "${RED}ERROR: Monitor Agent process not found${NC}"
        exit 1
    fi
    
    # Check metrics endpoint
    if curl -sf "http://localhost:9090/metrics" > /dev/null 2>&1; then
        log "${GREEN}✓ Metrics endpoint responsive${NC}"
    else
        log "${YELLOW}WARN: Metrics endpoint not accessible${NC}"
    fi
    
    # Check log directory
    if [[ -d "${AGENT_LOG_DIR:-/app/logs}" ]]; then
        log_count=$(find "${AGENT_LOG_DIR:-/app/logs}" -name "*.log" | wc -l)
        log "${GREEN}✓ Log directory accessible (${log_count} log files)${NC}"
    else
        log "${YELLOW}WARN: Log directory not found${NC}"
    fi
}

# Check generic agent health
check_generic_agent() {
    local agent_type="${1}"
    log "Checking ${agent_type} Agent health..."
    
    # Check if any process contains the agent name
    if pgrep -f "${agent_type,,}" > /dev/null; then
        log "${GREEN}✓ ${agent_type} process running${NC}"
    else
        log "${RED}ERROR: ${agent_type} process not found${NC}"
        exit 1
    fi
    
    # Check basic connectivity to message router
    if check_message_router_connectivity; then
        log "${GREEN}✓ Message router connectivity${NC}"
    else
        log "${YELLOW}WARN: Message router connectivity issue${NC}"
    fi
}

# Check agent registration with message router
check_agent_registration() {
    local agent_type="${1}"
    
    # Query message router API for registered agents
    if command -v curl >/dev/null 2>&1; then
        registered_agents=$(curl -sf "http://${MESSAGE_ROUTER_HOST}/api/agents" 2>/dev/null || echo "")
        if echo "${registered_agents}" | grep -q "${agent_type}"; then
            return 0
        fi
    fi
    
    return 1
}

# Check message router connectivity
check_message_router_connectivity() {
    if command -v curl >/dev/null 2>&1; then
        if curl -sf --connect-timeout 5 "http://${MESSAGE_ROUTER_HOST}/health" > /dev/null 2>&1; then
            return 0
        fi
    fi
    
    # Fallback: check if port is open
    if command -v nc >/dev/null 2>&1; then
        if echo | nc -w 5 message-router 8081 2>/dev/null; then
            return 0
        fi
    fi
    
    return 1
}

# Check Intel hardware accelerators
check_intel_accelerators() {
    local gna_available=false
    local npu_available=false
    
    # Check for GNA (Gaussian Neural Accelerator)
    if [[ -e "/dev/gna" ]] || lsmod | grep -q "gna"; then
        gna_available=true
        log "${GREEN}✓ Intel GNA available${NC}"
    else
        log "${YELLOW}WARN: Intel GNA not available${NC}"
    fi
    
    # Check for NPU (Neural Processing Unit)
    if lspci | grep -i "neural\|npu" > /dev/null 2>&1; then
        npu_available=true
        log "${GREEN}✓ Intel NPU detected${NC}"
    else
        log "${YELLOW}WARN: Intel NPU not detected${NC}"
    fi
    
    # Check OpenVINO runtime
    if command -v benchmark_app >/dev/null 2>&1; then
        log "${GREEN}✓ OpenVINO runtime available${NC}"
    else
        log "${YELLOW}WARN: OpenVINO runtime not found${NC}"
    fi
    
    return 0
}

# Check system resources
check_system_resources() {
    log "Checking system resources..."
    
    # Memory usage
    local mem_usage
    mem_usage=$(free | grep Mem | awk '{printf "%.1f", ($3/$2) * 100.0}')
    if (( $(echo "${mem_usage} < 90.0" | bc -l) )); then
        log "${GREEN}✓ Memory usage: ${mem_usage}%${NC}"
    else
        log "${YELLOW}WARN: High memory usage: ${mem_usage}%${NC}"
    fi
    
    # CPU load
    local cpu_load
    cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk -F, '{print $1}' | xargs)
    log "${GREEN}✓ CPU load average: ${cpu_load}${NC}"
    
    # Disk space
    local disk_usage
    disk_usage=$(df "${AGENT_HOME}" 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//' || echo "0")
    if [[ ${disk_usage} -lt 90 ]]; then
        log "${GREEN}✓ Disk usage: ${disk_usage}%${NC}"
    else
        log "${YELLOW}WARN: High disk usage: ${disk_usage}%${NC}"
    fi
}

# Check network connectivity
check_network_connectivity() {
    log "Checking network connectivity..."
    
    # Check internal network
    if ping -c 1 -W 3 message-router > /dev/null 2>&1; then
        log "${GREEN}✓ Internal network connectivity${NC}"
    else
        log "${YELLOW}WARN: Internal network connectivity issue${NC}"
    fi
    
    # Check UFP message throughput
    if [[ -x "${AGENT_HOME}/bin/ufp_benchmark" ]]; then
        local throughput
        throughput=$("${AGENT_HOME}/bin/ufp_benchmark" --quick 2>/dev/null | grep -o '[0-9]*.*msg/sec' | head -1 || echo "unknown")
        if [[ "${throughput}" != "unknown" ]]; then
            log "${GREEN}✓ UFP throughput: ${throughput}${NC}"
        else
            log "${YELLOW}WARN: UFP throughput test failed${NC}"
        fi
    fi
}

# Main health check function
main() {
    local agent_type="${1:-}"
    local exit_code=0
    
    log "Starting health check for ${agent_type:-system}..."
    
    # Check user
    check_user
    
    # Check UFP shared memory
    if ! check_ufp_shared_memory; then
        exit_code=1
    fi
    
    # Check agent-specific health
    if [[ -n "${agent_type}" ]]; then
        if ! check_agent_health "${agent_type}"; then
            exit_code=1
        fi
    fi
    
    # Check system resources
    check_system_resources
    
    # Check network connectivity
    check_network_connectivity
    
    if [[ ${exit_code} -eq 0 ]]; then
        log "${GREEN}✓ Health check passed${NC}"
    else
        log "${RED}✗ Health check failed${NC}"
    fi
    
    exit ${exit_code}
}

# Check if bc is available for floating point arithmetic
if ! command -v bc >/dev/null 2>&1; then
    log "${YELLOW}WARN: bc not available for precise calculations${NC}"
fi

# Run main function
main "$@"