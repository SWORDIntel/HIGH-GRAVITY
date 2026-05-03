#!/bin/bash
# HIGH-GRAVITY Complete Installation Script

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Colors
R='\033[0;31m'
G='\033[0;32m'
Y='\033[1;33m'
B='\033[0;34m'
C='\033[0;36m'
NC='\033[0m'

echo -e "${C}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           HIGH-GRAVITY Installation                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${R}Do not run as root. Run as normal user with sudo access.${NC}"
   exit 1
fi

# Prompt for sudo password once
echo -e "${B}[*] Checking sudo access...${NC}"
sudo -v || { echo -e "${R}Sudo access required${NC}"; exit 1; }
echo -e "${G}[✓] Sudo access confirmed${NC}\n"

# Keep sudo alive
while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &

# ── 1. System Packages ────────────────────────────────────────────
echo -e "${B}[1/6] Installing system packages...${NC}"
sudo apt-get update -qq
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    libxml2-dev libxslt-dev \
    docker.io docker-compose \
    iptables net-tools curl \
    build-essential gcc \
    git 2>&1 | grep -E "Setting up|already" | tail -5
echo -e "${G}[✓] System packages installed${NC}\n"

# Add user to docker group
if ! groups | grep -q docker; then
    echo -e "${B}[*] Adding user to docker group...${NC}"
    sudo usermod -aG docker $USER
    echo -e "${Y}[!] You'll need to log out and back in for docker group to take effect${NC}"
fi

# ── 2. Python Dependencies ────────────────────────────────────────
echo -e "${B}[2/6] Installing Python packages...${NC}"
pip3 install --user --upgrade pip setuptools wheel 2>&1 | tail -2
pip3 install --user \
    aiohttp fastapi uvicorn requests \
    rich textual \
    sentence-transformers 2>&1 | grep -E "Successfully installed|already satisfied" | tail -5
echo -e "${G}[✓] Python packages installed${NC}\n"

# ── 3. Docker Images ──────────────────────────────────────────────
echo -e "${B}[3/6] Pulling Docker images (this may take a while)...${NC}"
docker pull ghcr.io/khoj-ai/khoj:latest 2>&1 | tail -3
docker pull pgvector/pgvector:pg15 2>&1 | tail -3
echo -e "${G}[✓] Docker images pulled${NC}\n"

# ── 4. Directory Structure ────────────────────────────────────────
echo -e "${B}[4/6] Creating directory structure...${NC}"
mkdir -p logs data/khoj certs archive/{old_scripts,old_patchers}
chmod +x scripts/*.sh 2>/dev/null || true
chmod +x hg.sh 2>/dev/null || true
echo -e "${G}[✓] Directories created${NC}\n"

# ── 5. Generate HTTPS Certificates ────────────────────────────────
if [ ! -f "certs/proxy.crt" ]; then
    echo -e "${B}[5/6] Generating self-signed HTTPS certificates...${NC}"
    mkdir -p certs
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout certs/proxy.key \
        -out certs/proxy.crt \
        -days 3650 \
        -subj "/C=US/ST=State/L=City/O=HG/CN=*.windsurf.com" \
        -addext "subjectAltName=DNS:proxy.windsurf.com,DNS:inferapi.windsurf.com,DNS:*.windsurf.com" \
        2>&1 | tail -2
    echo -e "${G}[✓] Certificates generated${NC}\n"
else
    echo -e "${G}[5/6] Certificates already exist${NC}\n"
fi

# ── 6. Verify Installation ────────────────────────────────────────
echo -e "${B}[6/6] Verifying installation...${NC}"
ERRORS=0

# Check Python
python3 --version >/dev/null 2>&1 || { echo -e "${R}[✗] Python3 not found${NC}"; ERRORS=$((ERRORS+1)); }

# Check Docker
docker --version >/dev/null 2>&1 || { echo -e "${R}[✗] Docker not found${NC}"; ERRORS=$((ERRORS+1)); }

# Check Python packages
python3 -c "import aiohttp, fastapi, uvicorn" 2>/dev/null || { echo -e "${R}[✗] Python packages missing${NC}"; ERRORS=$((ERRORS+1)); }

# Check Docker images
docker images | grep -q khoj || { echo -e "${R}[✗] Khoj image not found${NC}"; ERRORS=$((ERRORS+1)); }

# Check scripts
[ -f "hg.sh" ] || { echo -e "${R}[✗] hg.sh not found${NC}"; ERRORS=$((ERRORS+1)); }
[ -f "src/patch_all.py" ] || { echo -e "${R}[✗] patch_all.py not found${NC}"; ERRORS=$((ERRORS+1)); }
[ -f "src/proxy.py" ] || { echo -e "${R}[✗] proxy.py not found${NC}"; ERRORS=$((ERRORS+1)); }

if [ $ERRORS -eq 0 ]; then
    echo -e "${G}[✓] All components verified${NC}\n"
else
    echo -e "${R}[✗] $ERRORS error(s) found${NC}\n"
    exit 1
fi

# ── Success ───────────────────────────────────────────────────────
echo -e "${G}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Installation Complete!                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

echo -e "${C}Next steps:${NC}"
echo -e "  1. Patch Windsurf: ${B}./hg.sh patch${NC}"
echo -e "  2. Start services: ${B}./hg.sh start${NC}"
echo -e "  3. Verify status: ${B}./hg.sh verify${NC}"
echo -e "  4. Launch dashboard: ${B}./hg.sh dashboard${NC}"
echo -e "  5. Reload Windsurf window (Ctrl+Shift+P → Reload Window)"
echo ""
echo -e "${Y}Note: If you added yourself to docker group, log out and back in first.${NC}"
echo ""
