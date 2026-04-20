#!/bin/bash
# Verify complete HTTPS proxy setup

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     HIGH-GRAVITY HTTPS Setup Verification                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

PASS=0
FAIL=0

# Check 1: Certificates exist
echo "[1/6] Checking certificates..."
if [ -f "certs/proxy.crt" ] && [ -f "certs/proxy.key" ]; then
    echo "  ✓ Certificates found"
    ((PASS++))
else
    echo "  ✗ Certificates missing"
    ((FAIL++))
fi

# Check 2: System trust
echo "[2/6] Checking system trust..."
if [ -f "/usr/local/share/ca-certificates/high-gravity-proxy.crt" ]; then
    echo "  ✓ Certificate installed to system trust"
    ((PASS++))
else
    echo "  ✗ Certificate not in system trust"
    ((FAIL++))
fi

# Check 3: /etc/hosts entries
echo "[3/6] Checking /etc/hosts..."
DOMAINS=(
    "server.codeium.com"
    "inference.codeium.com"
    "server.self-serve.windsurf.com"
)

HOSTS_OK=true
for domain in "${DOMAINS[@]}"; do
    if grep -q "127.0.0.1 $domain" /etc/hosts; then
        echo "  ✓ $domain"
    else
        echo "  ✗ $domain missing"
        HOSTS_OK=false
    fi
done

if [ "$HOSTS_OK" = true ]; then
    ((PASS++))
else
    ((FAIL++))
fi

# Check 4: HTTP proxy running
echo "[4/6] Checking HTTP proxy (port 9999)..."
if lsof -i :9999 >/dev/null 2>&1; then
    PID=$(lsof -i :9999 | grep LISTEN | awk '{print $2}')
    echo "  ✓ HTTP proxy running (PID: $PID)"
    ((PASS++))
else
    echo "  ✗ HTTP proxy not running"
    ((FAIL++))
fi

# Check 5: HTTPS proxy running
echo "[5/6] Checking HTTPS proxy (port 443)..."
if sudo lsof -i :443 2>/dev/null | grep -q LISTEN; then
    PID=$(sudo lsof -i :443 2>/dev/null | grep LISTEN | awk '{print $2}')
    echo "  ✓ HTTPS proxy running (PID: $PID)"
    ((PASS++))
else
    echo "  ✗ HTTPS proxy not running"
    ((FAIL++))
fi

# Check 6: HTTPS connectivity
echo "[6/6] Testing HTTPS connectivity..."
if curl -k -s -o /dev/null -w "%{http_code}" https://server.codeium.com:443/hg/telemetry | grep -q 200; then
    echo "  ✓ HTTPS proxy responding"
    ((PASS++))
else
    echo "  ✗ HTTPS proxy not responding"
    ((FAIL++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Results: ✓ $PASS passed, ✗ $FAIL failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo "🎉 All checks passed! HTTPS proxy is fully operational."
    echo ""
    echo "Next steps:"
    echo "  1. Restart Windsurf: pkill -f windsurf && /usr/share/windsurf-next/windsurf-next &"
    echo "  2. Wait 30 seconds for language server to start"
    echo "  3. Check connections: lsof -i -n -P | grep windsurf | grep 443"
    echo "  4. Use Cascade (Ctrl+L) and watch: tail -f logs/cascade_midway.log"
    exit 0
else
    echo ""
    echo "⚠️  Some checks failed. Run: bash hg_start.sh --clean"
    exit 1
fi
