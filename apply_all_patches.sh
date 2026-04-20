#!/bin/bash
# Apply ALL Windsurf patches (extension + binary + DNS)

SUDO_PASS="1786"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Apply ALL Windsurf Patches (Complete Solution)        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check Windsurf not running
if pgrep -f "windsurf" > /dev/null; then
    echo "❌ Windsurf is running! Close it first:"
    echo "   pkill -f windsurf"
    exit 1
fi

echo "✓ Windsurf not running"
echo ""

# Patch 1: Extension.js
echo "[1/3] Patching extension.js..."
python3 src/patch_windsurf_client.py --force
if [ $? -eq 0 ]; then
    echo "  ✓ Extension patched"
else
    echo "  ❌ Extension patch failed"
    exit 1
fi
echo ""

# Patch 2: Language server binary
echo "[2/3] Patching language server binary..."
python3 src/patch_language_server_binary.py
if [ $? -eq 0 ]; then
    echo "  ✓ Binary patched"
else
    echo "  ❌ Binary patch failed"
    exit 1
fi
echo ""

# Patch 3: /etc/hosts DNS redirect
echo "[3/3] Adding /etc/hosts redirects..."

# Check if already present
if grep -q "server.self-serve.windsurf.com" /etc/hosts; then
    echo "  ✓ /etc/hosts already configured"
else
    cat > /tmp/windsurf_hosts << 'EOF'

# HIGH-GRAVITY Windsurf DNS redirects
127.0.0.1 server.self-serve.windsurf.com
127.0.0.1 server.codeium.com
127.0.0.1 inference.codeium.com
EOF
    
    echo "$SUDO_PASS" | sudo -S bash -c "cat /tmp/windsurf_hosts >> /etc/hosts"
    if [ $? -eq 0 ]; then
        echo "  ✓ /etc/hosts updated"
    else
        echo "  ❌ /etc/hosts update failed"
        exit 1
    fi
fi
echo ""

# Verify all patches
echo "════════════════════════════════════════════════════════════"
echo "VERIFICATION"
echo "════════════════════════════════════════════════════════════"
echo ""

echo "[✓] Extension patches:"
python3 src/patch_windsurf_client.py --verify --quiet

echo ""
echo "[✓] Binary patches:"
python3 src/patch_language_server_binary.py --verify | grep "Found"

echo ""
echo "[✓] DNS redirects:"
for domain in "server.self-serve.windsurf.com" "server.codeium.com" "inference.codeium.com"; do
    if grep -q "$domain" /etc/hosts; then
        echo "  ✓ $domain"
    else
        echo "  ✗ $domain MISSING"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ ALL PATCHES APPLIED"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Start proxy: bash hg_start.sh --clean --no-dashboard"
echo "  2. Start Windsurf: /usr/share/windsurf-next/windsurf-next &"
echo "  3. Wait 30 seconds"
echo "  4. Verify: lsof -i -n -P | grep windsurf | grep 9999"
echo ""
echo "To remove /etc/hosts entries:"
echo "  sudo sed -i '/HIGH-GRAVITY Windsurf/,+3d' /etc/hosts"
echo ""
