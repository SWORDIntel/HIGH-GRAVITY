#!/bin/bash

# Hiz-TUI Setup Wrapper
# Enhanced Granular Control for High-Gravity

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Bootstrap Virtual Environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Bootstrapping virtual environment...${NC}"
    python3 -m venv $VENV_DIR
    $VENV_DIR/bin/pip install --upgrade pip
    if [ -f "requirements.txt" ]; then
        $VENV_DIR/bin/pip install -r requirements.txt
    fi
    echo -e "${GREEN}Virtual environment ready.${NC}"
fi

PYTHON_CMD="$VENV_DIR/bin/python"

check_status() {
    echo -e "\n${BLUE}--- System Status ---${NC}"
    if pgrep -f "highgravity_proxy.py" > /dev/null; then
        echo -e "Proxy Server: ${GREEN}[RUNNING]${NC}"
    else
        echo -e "Proxy Server: ${RED}[STOPPED]${NC}"
    fi
    # Simple check for patched file
    if [ -f "/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js.original" ]; then
        echo -e "Patch Status: ${GREEN}[APPLIED]${NC}"
    else
        echo -e "Patch Status: ${YELLOW}[NOT FOUND]${NC}"
    fi
}

show_menu() {
    clear
    echo -e "${BLUE}=== HIGH-GRAVITY Control Center ===${NC}"
    check_status
    echo -e "\n${BLUE}Select Action:${NC}"
    echo "1) Apply/Update Patches"
    echo "2) Wire Current Project"
    echo "3) Start Proxy Server"
    echo "4) Stop Proxy Server"
    echo "5) View Logs"
    echo "6) Diagnostics Debugger"
    echo "7) Sync Session (Export WS Next Keys)"
    echo "8) Export Proxy Vars (Pipe to Shell)"
    echo "9) System Reset"
    echo "10) Exit"
}

while true; do
    show_menu
    read -p "Selection [1-10]: " opt
    case $opt in
        1) sudo ./tools/integration/auto_modifier.sh; read -p "Press Enter...";;
        2) $PYTHON_CMD ./tools/integration/detect_and_wire_windsurf.py; read -p "Press Enter...";;
        3) $PYTHON_CMD tools/integration/highgravity_proxy.py & echo "Proxy started."; read -p "Press Enter...";;
        4) pkill -f "highgravity_proxy.py"; echo "Proxy stopped."; read -p "Press Enter...";;
        5) tail -n 20 logs/proxy.log; read -p "Press Enter...";;
        6) $PYTHON_CMD tools/debug/windsurf_debugger.py; read -p "Press Enter...";;
        7) 
           $PYTHON_CMD ./tools/integration/extract_ws_config.py
           echo -e "\n${YELLOW}Run 'eval \$(./scripts/hiz_setup.sh | grep export)' to sync keys to proxy env.${NC}"
           read -p "Press Enter..."
           ;;
        8) 
           echo "export HG_PROXY_PORT=9999"
           echo "export OPENAI_BASE_URL=http://localhost:9999"
           echo -e "\n${YELLOW}Run 'eval \$(./scripts/hiz_setup.sh | grep export)' to apply to current shell.${NC}"
           read -p "Press Enter..."
           ;;
        9) 
           echo "Resetting HIGH-GRAVITY..."
           pkill -f "highgravity_proxy.py"
           rm -rf kp14_cache/*
           echo "System reset."
           read -p "Press Enter..."
           ;;
        10) exit 0 ;;
        *) echo "Invalid option."; sleep 1 ;;
    esac
done
