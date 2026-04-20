#!/bin/bash
# Start HIGH-GRAVITY proxy with HTTPS support on port 443

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

SUDO_PASS="1786"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Starting HIGH-GRAVITY Proxy (HTTP + HTTPS)            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Kill existing proxy
pkill -f "python3.*proxy.py" 2>/dev/null
sleep 2

# Check certificates exist
if [ ! -f "certs/proxy.crt" ] || [ ! -f "certs/proxy.key" ]; then
    echo "[!] Certificates not found. Run: python3 add_https_to_proxy.py"
    exit 1
fi

echo "[*] Starting proxy..."
echo "    HTTP:  0.0.0.0:9999"
echo "    HTTPS: 0.0.0.0:443"
echo ""

# Start proxy with sudo (needed for port 443)
echo "$SUDO_PASS" | sudo -S python3 src/proxy.py > logs/proxy.log 2>&1 &
PROXY_PID=$!

sleep 5

# Check if running
if lsof -i :9999 -i :443 2>/dev/null | grep -q python3; then
    echo "[✓] Proxy started successfully"
    echo ""
    lsof -i :9999 -i :443 | grep python3
    echo ""
    echo "Logs: tail -f logs/proxy.log"
else
    echo "[✗] Proxy failed to start"
    echo ""
    echo "Check logs:"
    tail -20 logs/proxy.log
    exit 1
fi
