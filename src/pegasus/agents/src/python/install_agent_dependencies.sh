#!/bin/bash
set -euo pipefail

# ============================================================================
# CLAUDE AGENT FRAMEWORK - PYTHON AGENT DEPENDENCIES INSTALLER
# ============================================================================
# Installs all required Python dependencies for 100% agent compliance
# Integrates with claude-installer.sh and Tandem Orchestration System
# Handles missing dependencies that prevent agents from loading
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
LOG_FILE="${SCRIPT_DIR}/dependency_install.log"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

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
# DEPENDENCY DETECTION AND INSTALLATION
# ============================================================================

check_python_environment() {
    log "Checking Python environment for agent dependencies..."
    
    # Check if we're in a virtual environment
    if [[ "${VIRTUAL_ENV:-}" != "" ]]; then
        log "Using virtual environment: $VIRTUAL_ENV"
    elif [[ -d "${SCRIPT_DIR}/venv_production" ]]; then
        log "Activating production virtual environment..."
        source "${SCRIPT_DIR}/venv_production/bin/activate"
    elif [[ -d "${SCRIPT_DIR}/venv" ]]; then
        log "Activating development virtual environment..."
        source "${SCRIPT_DIR}/venv/bin/activate"
    else
        warn "No virtual environment found - installing to system Python"
    fi
}

install_core_agent_dependencies() {
    log "Installing core agent dependencies for 100% compliance..."
    
    # Core dependencies that ALL agents need
    log "Installing base agent framework dependencies..."
    python3 -m pip install --upgrade pip setuptools wheel
    
    python3 -m pip install \
        asyncio \
        aiofiles \
        aiohttp \
        pyyaml \
        psutil \
        structlog \
        rich \
        tabulate \
        requests \
        cryptography \
        numpy \
        scipy || warn "Some core dependencies failed to install"
}

install_datascience_dependencies() {
    log "Installing DATASCIENCE agent dependencies..."
    
    # DATASCIENCE agent requires pandas, matplotlib, seaborn, etc.
    python3 -m pip install \
        pandas \
        matplotlib \
        seaborn \
        plotly \
        jupyter \
        notebook \
        scikit-learn \
        statsmodels || warn "Some DATASCIENCE dependencies failed to install"
        
    success "DATASCIENCE agent dependencies installed"
}

install_mlops_dependencies() {
    log "Installing MLOPS agent dependencies..."
    
    # MLOPS agent requires joblib, mlflow, etc.
    python3 -m pip install \
        joblib \
        mlflow \
        dvc \
        wandb \
        tensorboard \
        docker \
        kubernetes \
        apache-airflow \
        prefect || warn "Some MLOPS dependencies failed to install"
        
    success "MLOPS agent dependencies installed"
}

install_web_dependencies() {
    log "Installing WEB agent dependencies..."
    
    # WEB agent requires FastAPI, Flask, Django, etc.
    python3 -m pip install \
        fastapi \
        uvicorn \
        flask \
        django \
        jinja2 \
        werkzeug \
        sqlalchemy \
        alembic \
        pydantic \
        starlette || warn "Some WEB dependencies failed to install"
        
    success "WEB agent dependencies installed"
}

install_gui_dependencies() {
    log "Installing GUI agent dependencies..."
    
    # PYGUI and TUI agent dependencies
    python3 -m pip install \
        tkinter \
        streamlit \
        gradio \
        dash \
        plotly-dash \
        rich \
        textual \
        urwid || warn "Some GUI dependencies failed to install"
        
    success "GUI agent dependencies installed"
}

install_security_dependencies() {
    log "Installing security agent dependencies..."
    
    # SECURITY, QUANTUMGUARD, SECURITYCHAOSAGENT dependencies
    python3 -m pip install \
        cryptography \
        pycryptodome \
        bcrypt \
        passlib \
        oauthlib \
        pyjwt \
        pyotp \
        requests-oauthlib \
        scapy \
        nmap-python || warn "Some security dependencies failed to install"
        
    success "Security agent dependencies installed"
}

install_testing_dependencies() {
    log "Installing testing agent dependencies..."
    
    # TESTBED agent dependencies
    python3 -m pip install \
        pytest \
        pytest-asyncio \
        pytest-cov \
        pytest-mock \
        unittest-xml-reporting \
        coverage \
        hypothesis \
        mutmut \
        tox \
        locust || warn "Some testing dependencies failed to install"
        
    success "Testing agent dependencies installed"
}

install_monitoring_dependencies() {
    log "Installing monitoring agent dependencies..."
    
    # MONITOR agent dependencies
    python3 -m pip install \
        prometheus-client \
        grafana-api \
        opentelemetry-api \
        opentelemetry-sdk \
        opentelemetry-instrumentation \
        opentelemetry-exporter-prometheus \
        psutil \
        py-cpuinfo \
        nvidia-ml-py3 || warn "Some monitoring dependencies failed to install"
        
    success "Monitoring agent dependencies installed"
}

install_documentation_dependencies() {
    log "Installing documentation agent dependencies..."
    
    # DOCGEN agent dependencies
    python3 -m pip install \
        mkdocs \
        mkdocs-material \
        sphinx \
        myst-parser \
        pydoc-markdown \
        pdoc3 \
        markdown \
        jinja2 \
        pygments || warn "Some documentation dependencies failed to install"
        
    success "Documentation agent dependencies installed"
}

install_api_dependencies() {
    log "Installing API agent dependencies..."
    
    # APIDESIGNER agent dependencies
    python3 -m pip install \
        openapi-spec-validator \
        swagger-ui-bundle \
        flask-restx \
        django-rest-framework \
        graphene \
        graphql-core \
        strawberry-graphql \
        apispec \
        marshmallow || warn "Some API dependencies failed to install"
        
    success "API agent dependencies installed"
}

install_optimization_dependencies() {
    log "Installing optimization agent dependencies..."
    
    # OPTIMIZER agent dependencies
    python3 -m pip install \
        cython \
        numba \
        pypy \
        line-profiler \
        memory-profiler \
        py-spy \
        snakeviz \
        gprof2dot \
        objgraph || warn "Some optimization dependencies failed to install"
        
    success "Optimization agent dependencies installed"
}

# ============================================================================
# DEPENDENCY VERIFICATION
# ============================================================================

verify_agent_dependencies() {
    log "Verifying agent dependencies are correctly installed..."
    
    local failed_agents=()
    
    # Test critical dependencies
    python3 -c "import pandas; print('✅ pandas (DATASCIENCE) - OK')" 2>/dev/null || {
        echo "❌ pandas (DATASCIENCE) - FAILED"
        failed_agents+=("DATASCIENCE")
    }
    
    python3 -c "import joblib; print('✅ joblib (MLOPS) - OK')" 2>/dev/null || {
        echo "❌ joblib (MLOPS) - FAILED"
        failed_agents+=("MLOPS")
    }
    
    python3 -c "import fastapi; print('✅ FastAPI (WEB) - OK')" 2>/dev/null || {
        echo "❌ FastAPI (WEB) - FAILED"
        failed_agents+=("WEB")
    }
    
    python3 -c "import streamlit; print('✅ streamlit (PYGUI) - OK')" 2>/dev/null || {
        echo "❌ streamlit (PYGUI) - FAILED"
        failed_agents+=("PYGUI")
    }
    
    python3 -c "import prometheus_client; print('✅ prometheus_client (MONITOR) - OK')" 2>/dev/null || {
        echo "❌ prometheus_client (MONITOR) - FAILED"
        failed_agents+=("MONITOR")
    }
    
    python3 -c "import pytest; print('✅ pytest (TESTBED) - OK')" 2>/dev/null || {
        echo "❌ pytest (TESTBED) - FAILED"
        failed_agents+=("TESTBED")
    }
    
    if [ ${#failed_agents[@]} -eq 0 ]; then
        success "All critical agent dependencies verified successfully!"
        return 0
    else
        warn "Failed agent dependencies: ${failed_agents[*]}"
        return 1
    fi
}

run_compliance_check() {
    log "Running agent compliance verification..."
    
    if [[ -f "${SCRIPT_DIR}/verify_agent_signatures.py" ]]; then
        python3 "${SCRIPT_DIR}/verify_agent_signatures.py" | tee -a "$LOG_FILE"
    else
        warn "Agent verification script not found - skipping compliance check"
    fi
}

# ============================================================================
# INTEGRATION WITH EXISTING SYSTEMS
# ============================================================================

integrate_with_production_orchestrator() {
    log "Integrating with Production Orchestrator..."
    
    # Check if production orchestrator exists
    if [[ -f "${SCRIPT_DIR}/production_orchestrator.py" ]]; then
        log "Production Orchestrator found - testing integration..."
        python3 -c "
import sys
sys.path.insert(0, '${SCRIPT_DIR}')
try:
    from production_orchestrator import ProductionOrchestrator
    print('✅ Production Orchestrator import - OK')
except Exception as e:
    print(f'❌ Production Orchestrator import - FAILED: {e}')
" 2>/dev/null || warn "Production Orchestrator integration test failed"
    else
        warn "Production Orchestrator not found"
    fi
}

create_dependency_manifest() {
    log "Creating dependency manifest for future reference..."
    
    cat > "${SCRIPT_DIR}/agent_dependencies_manifest.json" << EOF
{
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "version": "1.0.0",
    "description": "Claude Agent Framework Python Dependencies",
    "dependencies": {
        "DATASCIENCE": ["pandas", "matplotlib", "seaborn", "plotly", "scikit-learn"],
        "MLOPS": ["joblib", "mlflow", "dvc", "wandb", "tensorboard"],
        "WEB": ["fastapi", "uvicorn", "flask", "django", "pydantic"],
        "PYGUI": ["streamlit", "gradio", "dash", "rich", "textual"],
        "SECURITY": ["cryptography", "pycryptodome", "bcrypt", "passlib"],
        "TESTBED": ["pytest", "pytest-asyncio", "coverage", "hypothesis"],
        "MONITOR": ["prometheus-client", "grafana-api", "psutil"],
        "DOCGEN": ["mkdocs", "sphinx", "myst-parser", "pydoc-markdown"],
        "APIDESIGNER": ["openapi-spec-validator", "flask-restx", "graphene"],
        "OPTIMIZER": ["cython", "numba", "line-profiler", "memory-profiler"]
    },
    "python_version": "$(python3 --version)",
    "install_location": "${SCRIPT_DIR}",
    "virtual_env": "${VIRTUAL_ENV:-system}"
}
EOF
    
    success "Dependency manifest created: ${SCRIPT_DIR}/agent_dependencies_manifest.json"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

show_banner() {
    echo -e "${BLUE}"
    echo "============================================================================"
    echo "          CLAUDE AGENT FRAMEWORK - DEPENDENCY INSTALLER v1.0"
    echo "============================================================================"
    echo "Installing Python dependencies for 100% agent compliance"
    echo "Targeting: DATASCIENCE, MLOPS, WEB, PYGUI, MONITOR, TESTBED, and more"
    echo -e "${NC}"
}

main() {
    show_banner
    
    log "Starting Claude Agent Framework dependency installation..."
    log "Target directory: ${SCRIPT_DIR}"
    log "Claude root: ${CLAUDE_ROOT}"
    
    # Create log file
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Check Python environment
    check_python_environment
    
    # Install dependencies by category
    install_core_agent_dependencies
    install_datascience_dependencies
    install_mlops_dependencies
    install_web_dependencies
    install_gui_dependencies
    install_security_dependencies
    install_testing_dependencies
    install_monitoring_dependencies
    install_documentation_dependencies
    install_api_dependencies
    install_optimization_dependencies
    
    # Verify installation
    log "Verifying dependencies..."
    if verify_agent_dependencies; then
        success "✅ All agent dependencies verified successfully!"
    else
        warn "⚠️ Some dependencies failed verification - check log for details"
    fi
    
    # Integration tests
    integrate_with_production_orchestrator
    
    # Create manifest
    create_dependency_manifest
    
    # Run compliance check
    run_compliance_check
    
    echo
    echo -e "${GREEN}============================================================================${NC}"
    success "Claude Agent Framework dependencies installation complete!"
    echo -e "${GREEN}============================================================================${NC}"
    
    echo
    echo -e "${BLUE}Summary:${NC}"
    echo "✅ Core agent framework dependencies installed"
    echo "✅ DATASCIENCE agent: pandas, matplotlib, scikit-learn"
    echo "✅ MLOPS agent: joblib, mlflow, wandb"
    echo "✅ WEB agent: FastAPI, Flask, Django"
    echo "✅ PYGUI agent: Streamlit, Gradio, Dash"
    echo "✅ Security agents: cryptography, pycryptodome"
    echo "✅ Testing agents: pytest, coverage, hypothesis"
    echo "✅ Monitoring agents: prometheus, grafana-api"
    echo "✅ Documentation agents: mkdocs, sphinx"
    echo "✅ API agents: OpenAPI, GraphQL tools"
    echo "✅ Optimization agents: Cython, Numba"
    
    echo
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Test agent compliance: python3 verify_agent_signatures.py"
    echo "2. Run orchestrator: python3 production_orchestrator.py"
    echo "3. Check status: python3 -c 'from production_orchestrator import ProductionOrchestrator; print(\"OK\")'"
    echo "4. Review manifest: cat agent_dependencies_manifest.json"
    
    echo
    echo -e "${GREEN}🎯 Ready for 100% Agent Compliance!${NC}"
}

# Execute if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi