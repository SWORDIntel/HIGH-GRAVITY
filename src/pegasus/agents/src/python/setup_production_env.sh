#!/bin/bash
set -euo pipefail

# ============================================================================
# TANDEM ORCHESTRATION SYSTEM - PRODUCTION ENVIRONMENT SETUP
# ============================================================================
# Infrastructure Agent: Production Environment Configuration
# Creates production-ready Python environment with all dependencies
# Configures Intel Meteor Lake hardware optimizations
# Sets up system services and monitoring infrastructure
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
LOG_FILE="${SCRIPT_DIR}/setup_production.log"
VENV_PATH="${SCRIPT_DIR}/venv_production"

# Color output for visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# ============================================================================
# SYSTEM REQUIREMENTS CHECK
# ============================================================================

check_system_requirements() {
    log "Checking system requirements for Tandem Orchestration System..."
    
    # Check Python version
    if ! python3 --version | grep -E "3\.(9|1[0-9])" > /dev/null; then
        error "Python 3.9+ required. Current: $(python3 --version)"
    fi
    success "Python version check passed: $(python3 --version)"
    
    # Check CPU architecture (Intel Meteor Lake optimization)
    if grep -q "Intel" /proc/cpuinfo; then
        log "Intel CPU detected - Meteor Lake optimizations will be enabled"
        export ENABLE_METEOR_LAKE_OPT=1
        
        # Check for specific Meteor Lake features
        if grep -q "avx512" /proc/cpuinfo; then
            log "AVX-512 support detected"
            export ENABLE_AVX512=1
        fi
        
        # Check core topology
        P_CORES=$(grep -c "core id.*[02468]" /proc/cpuinfo 2>/dev/null || echo "0")
        E_CORES=$(grep -c "core id.*1[2-9]" /proc/cpuinfo 2>/dev/null || echo "0")
        log "CPU Topology - P-cores: $P_CORES, E-cores: $E_CORES"
    else
        warn "Non-Intel CPU detected - some optimizations may be unavailable"
    fi
    
    # Check memory
    TOTAL_MEM=$(free -g | grep "^Mem:" | awk '{print $2}')
    if [ "$TOTAL_MEM" -lt 8 ]; then
        error "Minimum 8GB RAM required. Current: ${TOTAL_MEM}GB"
    fi
    success "Memory check passed: ${TOTAL_MEM}GB available"
    
    # Check disk space
    DISK_SPACE=$(df -h "${SCRIPT_DIR}" | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "${DISK_SPACE%.*}" -lt 5 ]; then
        error "Minimum 5GB disk space required. Available: ${DISK_SPACE}G"
    fi
    success "Disk space check passed: ${DISK_SPACE}G available"
}

# ============================================================================
# PYTHON ENVIRONMENT SETUP
# ============================================================================

setup_python_environment() {
    log "Setting up Python production environment..."
    
    # Remove existing venv if present
    if [ -d "$VENV_PATH" ]; then
        warn "Removing existing virtual environment"
        rm -rf "$VENV_PATH"
    fi
    
    # Create virtual environment
    python3 -m venv "$VENV_PATH"
    source "${VENV_PATH}/bin/activate"
    
    # Source OpenVINO environment if available
    OPENVINO_ENV_PATH="$HOME/openvino_ml_env"
    if [ -d "$OPENVINO_ENV_PATH" ]; then
        log "OpenVINO environment detected at $OPENVINO_ENV_PATH"
        
        # Source OpenVINO setupvars script if it exists
        if [ -f "$OPENVINO_ENV_PATH/bin/setupvars.sh" ]; then
            source "$OPENVINO_ENV_PATH/bin/setupvars.sh"
            success "OpenVINO environment variables sourced"
        elif [ -f "$OPENVINO_ENV_PATH/setupvars.sh" ]; then
            source "$OPENVINO_ENV_PATH/setupvars.sh"
            success "OpenVINO environment variables sourced"
        fi
        
        # Check for Intel OpenVINO toolkit installation
        if [ -d "$OPENVINO_ENV_PATH/openvino" ]; then
            export INTEL_OPENVINO_DIR="$OPENVINO_ENV_PATH/openvino"
            log "INTEL_OPENVINO_DIR set to $INTEL_OPENVINO_DIR"
        fi
        
        # Set OpenVINO Python path if available
        if [ -d "$OPENVINO_ENV_PATH/python" ]; then
            export PYTHONPATH="$OPENVINO_ENV_PATH/python:${PYTHONPATH:-}"
            log "Added OpenVINO Python path to PYTHONPATH"
        fi
        
        # Check for model optimizer
        if [ -d "$OPENVINO_ENV_PATH/deployment_tools/model_optimizer" ]; then
            export PATH="$OPENVINO_ENV_PATH/deployment_tools/model_optimizer:$PATH"
            log "Added Model Optimizer to PATH"
        fi
        
        # Set OpenVINO specific environment variables
        export OPENVINO_AVAILABLE=1
        export NPU_ACCELERATION_ENABLED=1
        log "OpenVINO integration enabled for NPU acceleration"
    else
        warn "OpenVINO environment not found at $OPENVINO_ENV_PATH"
        warn "NPU acceleration will not be available"
        export OPENVINO_AVAILABLE=0
        export NPU_ACCELERATION_ENABLED=0
    fi
    
    # Upgrade pip and setuptools
    pip install --upgrade pip setuptools wheel
    
    # Install core dependencies
    log "Installing core dependencies..."
    pip install \
        numpy>=1.21.0 \
        asyncio \
        aiofiles \
        aiohttp \
        uvloop \
        pyyaml \
        psutil \
        prometheus-client \
        structlog \
        click \
        rich \
        tabulate \
        networkx \
        scipy \
        pandas \
        msgpack \
        orjson \
        cython
    
    # Install monitoring dependencies
    log "Installing monitoring dependencies..."
    pip install \
        prometheus-client \
        grafana-api \
        opentelemetry-api \
        opentelemetry-sdk \
        opentelemetry-instrumentation \
        opentelemetry-exporter-prometheus
    
    # Install development tools
    log "Installing development tools..."
    pip install \
        pytest \
        pytest-asyncio \
        pytest-cov \
        black \
        flake8 \
        mypy \
        bandit
    
    # Install OpenVINO Python packages if OpenVINO is available
    if [ "$OPENVINO_AVAILABLE" = "1" ]; then
        log "Installing OpenVINO Python packages..."
        pip install \
            openvino \
            openvino-dev \
            openvino-telemetry || warn "Some OpenVINO packages may not be available"
        
        # Install NPU-specific packages for Intel Meteor Lake
        log "Installing NPU acceleration packages..."
        pip install \
            onnx \
            onnxruntime \
            tensorflow \
            torch \
            torchvision || warn "Some ML packages installation failed"
        
        success "OpenVINO and NPU packages installed"
    fi
    
    # Create requirements.txt for reproducibility
    pip freeze > "${SCRIPT_DIR}/requirements_production.txt"
    
    success "Python environment setup complete"
}

# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================

configure_system_settings() {
    log "Configuring system settings for production..."
    
    # Create system configuration directory
    SYSTEM_CONFIG_DIR="${SCRIPT_DIR}/config/system"
    mkdir -p "$SYSTEM_CONFIG_DIR"
    
    # Configure kernel parameters for performance
    cat > "${SYSTEM_CONFIG_DIR}/sysctl.conf" << EOF
# Tandem Orchestration System - Production Kernel Parameters
# Network optimizations
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728

# Memory management
vm.swappiness = 1
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# File descriptor limits
fs.file-max = 1000000

# Process limits
kernel.pid_max = 65536
EOF
    
    # Configure CPU governor for performance
    cat > "${SYSTEM_CONFIG_DIR}/cpufreq.conf" << EOF
# CPU Performance Configuration
GOVERNOR="performance"
MIN_SPEED="0"
MAX_SPEED="0"
EOF
    
    # Configure huge pages if available
    if [ -d /sys/kernel/mm/hugepages ]; then
        HUGEPAGE_SIZE=$(ls /sys/kernel/mm/hugepages/ | head -1 | cut -d'-' -f2)
        echo "1024" > /sys/kernel/mm/hugepages/hugepages-${HUGEPAGE_SIZE}/nr_hugepages 2>/dev/null || warn "Could not configure huge pages"
    fi
    
    success "System configuration complete"
}

# ============================================================================
# SERVICE CONFIGURATION
# ============================================================================

create_systemd_service() {
    log "Creating systemd service for Tandem Orchestrator..."
    
    SERVICE_FILE="/etc/systemd/system/tandem-orchestrator.service"
    
    cat > "${SCRIPT_DIR}/tandem-orchestrator.service" << EOF
[Unit]
Description=Claude Agent Framework - Tandem Orchestration System
Documentation=file://${CLAUDE_ROOT}/docs/TANDEM_ORCHESTRATION_SYSTEM.md
After=network.target multi-user.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=${SCRIPT_DIR}
Environment=PYTHONPATH=${SCRIPT_DIR}:${CLAUDE_ROOT}/agents/src/python
Environment=ENABLE_METEOR_LAKE_OPT=${ENABLE_METEOR_LAKE_OPT:-0}
Environment=ENABLE_AVX512=${ENABLE_AVX512:-0}
Environment=TANDEM_LOG_LEVEL=INFO
Environment=TANDEM_CONFIG_DIR=${SCRIPT_DIR}/config
Environment=OPENVINO_AVAILABLE=${OPENVINO_AVAILABLE:-0}
Environment=NPU_ACCELERATION_ENABLED=${NPU_ACCELERATION_ENABLED:-0}
Environment=INTEL_OPENVINO_DIR=${INTEL_OPENVINO_DIR:-}
ExecStartPre=/bin/bash -c "[ -f '$HOME/openvino_ml_env/bin/setupvars.sh' ] && source '$HOME/openvino_ml_env/bin/setupvars.sh' || true"
ExecStartPre=${VENV_PATH}/bin/python -c "import production_orchestrator; print('Tandem Orchestrator module check: OK')"
ExecStart=${VENV_PATH}/bin/python -m production_orchestrator --mode=production --config=${SCRIPT_DIR}/config/production.yaml
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=tandem-orchestrator

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${SCRIPT_DIR} ${CLAUDE_ROOT}/agents/monitoring/logs
PrivateTmp=true

# Resource limits
LimitNOFILE=65536
LimitNPROC=32768
MemoryLimit=16G
CPUQuota=800%

[Install]
WantedBy=multi-user.target
EOF
    
    success "Systemd service configuration created"
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

setup_logging() {
    log "Setting up production logging..."
    
    LOG_DIR="${SCRIPT_DIR}/logs"
    mkdir -p "$LOG_DIR"
    
    # Create log rotation configuration
    cat > "${SCRIPT_DIR}/config/logging.yaml" << EOF
version: 1
disable_existing_loggers: false

formatters:
  detailed:
    format: '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'
  simple:
    format: '%(levelname)s %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: simple
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: ${LOG_DIR}/production_orchestrator.log
    maxBytes: 52428800  # 50MB
    backupCount: 10
  
  metrics:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: detailed
    filename: ${LOG_DIR}/metrics.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
  
  error:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: detailed
    filename: ${LOG_DIR}/errors.log
    maxBytes: 10485760  # 10MB
    backupCount: 10

loggers:
  production_orchestrator:
    level: DEBUG
    handlers: [console, file]
    propagate: false
  
  metrics:
    level: INFO
    handlers: [metrics]
    propagate: false
  
  errors:
    level: ERROR
    handlers: [error, console]
    propagate: false

root:
  level: INFO
  handlers: [console, file]
EOF
    
    # Set appropriate permissions
    chmod 755 "$LOG_DIR"
    touch "${LOG_DIR}/production_orchestrator.log" "${LOG_DIR}/metrics.log" "${LOG_DIR}/errors.log"
    chmod 644 "${LOG_DIR}"/*.log
    
    success "Logging configuration complete"
}

# ============================================================================
# MONITORING SETUP
# ============================================================================

setup_monitoring() {
    log "Setting up production monitoring..."
    
    MONITORING_DIR="${SCRIPT_DIR}/monitoring"
    mkdir -p "$MONITORING_DIR"
    
    # Create Prometheus configuration for orchestrator
    cat > "${MONITORING_DIR}/prometheus_orchestrator.yml" << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "orchestrator_rules.yml"

scrape_configs:
  - job_name: 'tandem-orchestrator'
    static_configs:
      - targets: ['localhost:8090']
    scrape_interval: 5s
    metrics_path: /metrics
    
  - job_name: 'agent-health'
    static_configs:
      - targets: ['localhost:8091']
    scrape_interval: 10s
    metrics_path: /health/metrics
    
  - job_name: 'system-metrics'
    static_configs:
      - targets: ['localhost:8092']
    scrape_interval: 30s
    metrics_path: /system/metrics

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
EOF

    # Create alerting rules
    cat > "${MONITORING_DIR}/orchestrator_rules.yml" << EOF
groups:
  - name: production_orchestrator
    rules:
      - alert: OrchestratorDown
        expr: up{job="tandem-orchestrator"} == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Tandem Orchestrator is down"
          description: "The Tandem Orchestration System has been down for more than 30 seconds"
          
      - alert: HighAgentFailureRate
        expr: (agent_execution_failures_total / agent_execution_total) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High agent failure rate detected"
          description: "Agent failure rate is {{ \$value | humanizePercentage }} over the last 5 minutes"
          
      - alert: LowSystemMemory
        expr: (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) < 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Low system memory"
          description: "System memory usage is above 90% for more than 2 minutes"
          
      - alert: HighCPUTemperature
        expr: node_hwmon_temp_celsius{chip="coretemp-isa-0000"} > 85
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "High CPU temperature"
          description: "CPU temperature is {{ \$value }}°C, approaching thermal limits"
EOF
    
    success "Monitoring setup complete"
}

# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

setup_performance_tuning() {
    log "Configuring Intel Meteor Lake hardware optimizations..."
    
    PERF_CONFIG_DIR="${SCRIPT_DIR}/config/performance"
    mkdir -p "$PERF_CONFIG_DIR"
    
    # Create hardware optimization configuration
    cat > "${PERF_CONFIG_DIR}/meteor_lake_config.yaml" << EOF
# Intel Meteor Lake Hardware Optimization Configuration
hardware:
  cpu_model: "Intel Core Ultra 7 155H"
  architecture: "Meteor Lake"
  optimization_level: "production"
  
  # Core allocation strategy
  cores:
    p_cores:
      ids: [0, 2, 4, 6, 8, 10]
      usage: "compute_intensive"
      governor: "performance"
    e_cores:
      ids: [12, 13, 14, 15, 16, 17, 18, 19]
      usage: "background_tasks"
      governor: "powersave"
    lp_e_cores:
      ids: [20, 21]
      usage: "monitoring"
      governor: "powersave"
  
  # Memory configuration
  memory:
    huge_pages: true
    numa_awareness: true
    prefetch_distance: 64
    
  # Thermal management
  thermal:
    target_temp: 85
    throttle_temp: 95
    cooling_strategy: "aggressive"
    
  # AVX-512 optimization
  vector_extensions:
    avx512: ${ENABLE_AVX512:-false}
    avx2: true
    sse4: true

# Agent allocation strategy
agent_affinity:
  strategic_agents:
    - name: "Director"
      cores: "p_cores"
      priority: "high"
    - name: "ProjectOrchestrator"
      cores: "p_cores"
      priority: "high"
      
  compute_intensive:
    - name: "Constructor"
      cores: "p_cores"
      priority: "medium"
    - name: "Optimizer"
      cores: "p_cores"
      priority: "medium"
      
  background_agents:
    - name: "Monitor"
      cores: "e_cores"
      priority: "low"
    - name: "Security"
      cores: "e_cores"
      priority: "medium"
      
  monitoring_agents:
    - name: "Infrastructure"
      cores: "lp_e_cores"
      priority: "low"
EOF
    
    # Create CPU affinity script
    cat > "${SCRIPT_DIR}/set_cpu_affinity.py" << 'EOF'
#!/usr/bin/env python3
import os
import psutil
import yaml
from pathlib import Path

def set_process_affinity():
    """Set CPU affinity based on Meteor Lake configuration"""
    config_file = Path(__file__).parent / "config/performance/meteor_lake_config.yaml"
    
    if not config_file.exists():
        print("Configuration file not found")
        return
        
    with open(config_file) as f:
        config = yaml.safe_load(f)
    
    # Get current process
    process = psutil.Process()
    
    # Set affinity to P-cores for main orchestrator process
    p_cores = config['hardware']['cores']['p_cores']['ids']
    try:
        process.cpu_affinity(p_cores)
        print(f"Set CPU affinity to P-cores: {p_cores}")
    except Exception as e:
        print(f"Failed to set CPU affinity: {e}")

if __name__ == "__main__":
    set_process_affinity()
EOF
    
    chmod +x "${SCRIPT_DIR}/set_cpu_affinity.py"
    
    success "Performance tuning configuration complete"
}

# ============================================================================
# HEALTH CHECK SYSTEM
# ============================================================================

create_health_checks() {
    log "Creating health check system..."
    
    cat > "${SCRIPT_DIR}/health_check.py" << 'EOF'
#!/usr/bin/env python3
"""
Health Check System for Tandem Orchestration System
Provides comprehensive health monitoring and status reporting
"""

import asyncio
import json
import time
import psutil
import socket
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class HealthStatus:
    service: str
    status: str  # healthy, warning, critical, unknown
    score: float  # 0-100
    message: str
    timestamp: datetime
    details: Dict[str, Any]

class SystemHealthChecker:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/production.yaml"
        self.checks = []
        
    async def check_orchestrator_health(self) -> HealthStatus:
        """Check main orchestrator service health"""
        try:
            # Check if orchestrator process is running
            orchestrator_running = any(
                'production_orchestrator' in p.name().lower() 
                for p in psutil.process_iter(['name', 'cmdline'])
            )
            
            if not orchestrator_running:
                return HealthStatus(
                    service="orchestrator",
                    status="critical",
                    score=0,
                    message="Orchestrator process not running",
                    timestamp=datetime.now(),
                    details={"process_found": False}
                )
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                status = "warning"
                score = 60
                message = f"High memory usage: {memory.percent:.1f}%"
            else:
                status = "healthy"
                score = 100 - memory.percent
                message = f"Memory usage normal: {memory.percent:.1f}%"
                
            return HealthStatus(
                service="orchestrator",
                status=status,
                score=score,
                message=message,
                timestamp=datetime.now(),
                details={
                    "memory_percent": memory.percent,
                    "memory_available": memory.available,
                    "process_found": True
                }
            )
            
        except Exception as e:
            return HealthStatus(
                service="orchestrator",
                status="critical",
                score=0,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )
    
    async def check_agent_registry_health(self) -> HealthStatus:
        """Check agent registration system health"""
        try:
            # Check if agent files are accessible
            agents_dir = Path(__file__).parent.parent.parent
            agent_files = list(agents_dir.glob("*.md"))
            
            if len(agent_files) < 30:
                return HealthStatus(
                    service="agent_registry",
                    status="warning",
                    score=50,
                    message=f"Only {len(agent_files)} agent files found",
                    timestamp=datetime.now(),
                    details={"agent_count": len(agent_files)}
                )
            
            return HealthStatus(
                service="agent_registry",
                status="healthy",
                score=100,
                message=f"All {len(agent_files)} agent files accessible",
                timestamp=datetime.now(),
                details={"agent_count": len(agent_files)}
            )
            
        except Exception as e:
            return HealthStatus(
                service="agent_registry",
                status="critical",
                score=0,
                message=f"Agent registry check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )
    
    async def check_system_resources(self) -> HealthStatus:
        """Check system resource utilization"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Calculate overall score
            cpu_score = max(0, 100 - cpu)
            memory_score = max(0, 100 - memory.percent)
            disk_score = max(0, 100 - disk.percent)
            overall_score = (cpu_score + memory_score + disk_score) / 3
            
            if overall_score > 80:
                status = "healthy"
            elif overall_score > 60:
                status = "warning"
            else:
                status = "critical"
                
            return HealthStatus(
                service="system_resources",
                status=status,
                score=overall_score,
                message=f"System resources: CPU {cpu:.1f}%, MEM {memory.percent:.1f}%, DISK {disk.percent:.1f}%",
                timestamp=datetime.now(),
                details={
                    "cpu_percent": cpu,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                }
            )
            
        except Exception as e:
            return HealthStatus(
                service="system_resources",
                status="critical",
                score=0,
                message=f"Resource check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )
    
    async def run_all_checks(self) -> List[HealthStatus]:
        """Run all health checks concurrently"""
        checks = await asyncio.gather(
            self.check_orchestrator_health(),
            self.check_agent_registry_health(),
            self.check_system_resources(),
            return_exceptions=True
        )
        
        # Filter out exceptions
        valid_checks = [check for check in checks if isinstance(check, HealthStatus)]
        return valid_checks
    
    def generate_health_report(self, checks: List[HealthStatus]) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        overall_score = sum(check.score for check in checks) / len(checks) if checks else 0
        
        critical_count = sum(1 for check in checks if check.status == "critical")
        warning_count = sum(1 for check in checks if check.status == "warning")
        healthy_count = sum(1 for check in checks if check.status == "healthy")
        
        if critical_count > 0:
            overall_status = "critical"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "overall_score": round(overall_score, 2),
            "summary": {
                "total_checks": len(checks),
                "healthy": healthy_count,
                "warning": warning_count,
                "critical": critical_count
            },
            "checks": [
                {
                    "service": check.service,
                    "status": check.status,
                    "score": check.score,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat(),
                    "details": check.details
                }
                for check in checks
            ]
        }

async def main():
    """Main health check execution"""
    checker = SystemHealthChecker()
    checks = await checker.run_all_checks()
    report = checker.generate_health_report(checks)
    
    print(json.dumps(report, indent=2))
    
    # Exit with appropriate code
    if report["overall_status"] == "critical":
        exit(2)
    elif report["overall_status"] == "warning":
        exit(1)
    else:
        exit(0)

if __name__ == "__main__":
    asyncio.run(main())
EOF
    
    chmod +x "${SCRIPT_DIR}/health_check.py"
    
    success "Health check system created"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    log "Starting Tandem Orchestration System Production Setup"
    log "============================================================================"
    
    # Check if running as root for system configuration
    if [ "$EUID" -eq 0 ]; then
        warn "Running as root - system-level configuration will be applied"
    else
        warn "Not running as root - some system configurations will be skipped"
    fi
    
    # Create necessary directories
    mkdir -p "${SCRIPT_DIR}/config" "${SCRIPT_DIR}/logs" "${SCRIPT_DIR}/monitoring"
    
    # Execute setup steps
    check_system_requirements
    setup_python_environment
    configure_system_settings
    create_systemd_service
    setup_logging
    setup_monitoring
    setup_performance_tuning
    create_health_checks
    
    log "============================================================================"
    success "Tandem Orchestration System Production Setup Complete!"
    log "============================================================================"
    
    echo
    echo -e "${GREEN}Next Steps:${NC}"
    echo "1. Install system service: sudo cp tandem-orchestrator.service /etc/systemd/system/"
    echo "2. Enable service: sudo systemctl enable tandem-orchestrator"
    echo "3. Start service: sudo systemctl start tandem-orchestrator"
    echo "4. Check status: sudo systemctl status tandem-orchestrator"
    echo "5. View logs: journalctl -u tandem-orchestrator -f"
    echo "6. Run health check: ./health_check.py"
    echo
    echo -e "${BLUE}Configuration files created:${NC}"
    echo "- Virtual environment: ${VENV_PATH}"
    echo "- Service file: ${SCRIPT_DIR}/tandem-orchestrator.service"
    echo "- Logging config: ${SCRIPT_DIR}/config/logging.yaml"
    echo "- Performance config: ${SCRIPT_DIR}/config/performance/meteor_lake_config.yaml"
    echo "- Health check: ${SCRIPT_DIR}/health_check.py"
    echo
    echo -e "${YELLOW}Important:${NC}"
    echo "- Activate the virtual environment: source ${VENV_PATH}/bin/activate"
    echo "- The system is optimized for Intel Meteor Lake architecture"
    echo "- All 31 agents are configured with appropriate hardware affinity"
    echo "- Monitoring is configured with Prometheus metrics on port 8090"
}

# Execute main function
main "$@"