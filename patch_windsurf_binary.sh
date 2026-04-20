#!/bin/bash
# Complete Windsurf binary patcher - run with Windsurf closed

SUDO_PASS="1786"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Windsurf Language Server Binary Patcher              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if Windsurf is running
if pgrep -f "windsurf" > /dev/null; then
    echo "❌ Windsurf is running! Please close it first:"
    echo "   pkill -f windsurf"
    echo ""
    exit 1
fi

echo "✓ Windsurf is not running"
echo ""

# Run the patcher
python3 src/patch_language_server_binary.py

if [ $? -eq 0 ]; then
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "✅ PATCHING COMPLETE"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "What was patched:"
    echo "  • Language server binary URLs redirected to proxy"
    echo "  • Backup created at: ...language_server_linux_x64.original"
    echo ""
    echo "Next steps:"
    echo "  1. Start HIGH-GRAVITY proxy:"
    echo "     bash hg_start.sh --clean --no-dashboard"
    echo ""
    echo "  2. Start Windsurf:"
    echo "     /usr/share/windsurf-next/windsurf-next &"
    echo ""
    echo "  3. Wait 30 seconds, then verify:"
    echo "     lsof -i -n -P | grep windsurf | grep 9999"
    echo "     # Should show connections to 127.0.0.1:9999"
    echo ""
    echo "  4. Use Cascade (Ctrl+L) and watch MITM log:"
    echo "     tail -f logs/cascade_midway.log"
    echo ""
    echo "To restore original binary:"
    echo "  python3 src/patch_language_server_binary.py --restore"
    echo ""
else
    echo ""
    echo "❌ Patching failed - check errors above"
    exit 1
fi
