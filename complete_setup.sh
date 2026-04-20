#!/bin/bash
# Complete HIGH-GRAVITY setup and verification

SUDO_PASS="1786"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     HIGH-GRAVITY Complete Setup & Verification            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Check if Windsurf is running
echo "[1/6] Checking Windsurf status..."
if pgrep -f "windsurf" > /dev/null; then
    echo "  ⚠️  Windsurf is running"
    echo "  ❌ Please close Windsurf first: pkill -f windsurf"
    echo ""
    read -p "Close Windsurf now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f windsurf
        sleep 3
        echo "  ✓ Windsurf closed"
    else
        echo "  ❌ Cannot proceed with Windsurf running"
        exit 1
    fi
else
    echo "  ✓ Windsurf not running"
fi
echo ""

# Step 2: Patch language server binary
echo "[2/6] Patching language server binary..."
python3 src/patch_language_server_binary.py
if [ $? -eq 0 ]; then
    echo "  ✓ Binary patched"
else
    echo "  ❌ Binary patch failed"
    exit 1
fi
echo ""

# Step 3: Verify patches
echo "[3/6] Verifying patches..."
python3 src/patch_language_server_binary.py --verify
if [ $? -eq 0 ]; then
    echo "  ✓ Patches verified"
else
    echo "  ❌ Verification failed"
    exit 1
fi
echo ""

# Step 4: Start HIGH-GRAVITY services
echo "[4/6] Starting HIGH-GRAVITY services..."
bash hg_start.sh --clean --no-dashboard
if [ $? -eq 0 ]; then
    echo "  ✓ Services started"
else
    echo "  ❌ Service startup failed"
    exit 1
fi
echo ""

# Step 5: Start Windsurf
echo "[5/6] Starting Windsurf..."
/usr/share/windsurf-next/windsurf-next > /dev/null 2>&1 &
WINDSURF_PID=$!
echo "  ✓ Windsurf started (PID: $WINDSURF_PID)"
echo "  ⏳ Waiting 30 seconds for language server to initialize..."
sleep 30
echo ""

# Step 6: Verify connections
echo "[6/6] Verifying Windsurf connections..."
CONNECTIONS=$(lsof -i -n -P | grep windsurf | grep ESTABLISHED)

# Check for proxy connections
if echo "$CONNECTIONS" | grep -q "127.0.0.1:9999"; then
    echo "  ✅ Windsurf connected to proxy (127.0.0.1:9999)"
    PROXY_OK=true
else
    echo "  ❌ Windsurf NOT connected to proxy"
    PROXY_OK=false
fi

# Check for external connections
if echo "$CONNECTIONS" | grep -qE "35\.|34\."; then
    echo "  ⚠️  Windsurf still connecting to external IPs:"
    echo "$CONNECTIONS" | grep -E "35\.|34\." | head -3
    EXTERNAL=true
else
    echo "  ✅ No external Codeium connections detected"
    EXTERNAL=false
fi
echo ""

# Summary
echo "════════════════════════════════════════════════════════════"
echo "SETUP SUMMARY"
echo "════════════════════════════════════════════════════════════"

if [ "$PROXY_OK" = true ] && [ "$EXTERNAL" = false ]; then
    echo "✅ SUCCESS - All systems operational!"
    echo ""
    echo "Next steps:"
    echo "  1. Use Cascade in Windsurf (Ctrl+L)"
    echo "  2. Watch MITM log: tail -f logs/cascade_midway.log"
    echo "  3. Start dashboard: python3 hg_simple.py"
    echo ""
    exit 0
else
    echo "⚠️  PARTIAL SUCCESS - Some issues detected"
    echo ""
    if [ "$PROXY_OK" = false ]; then
        echo "Issue: Windsurf not using proxy"
        echo "Fix:"
        echo "  1. Close Windsurf: pkill -f windsurf"
        echo "  2. Re-run this script: bash complete_setup.sh"
    fi
    if [ "$EXTERNAL" = true ]; then
        echo "Issue: External connections detected"
        echo "This may be normal for some Windsurf features"
        echo "Check if Cascade requests go through proxy:"
        echo "  tail -f logs/proxy.log | grep 'v1/chat'"
    fi
    echo ""
    exit 1
fi
