#!/bin/bash
# Verify all Windsurf patches are applied correctly

EXT_FILE="/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Windsurf Patch Verification                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ ! -f "$EXT_FILE" ]; then
    echo "❌ Extension file not found: $EXT_FILE"
    exit 1
fi

echo "📁 Extension file: $EXT_FILE"
echo ""

# Check each patch
PASS=0
FAIL=0

echo "🔍 Checking patches..."
echo ""

# Patch 1: INFERENCE_API_SERVER_URL
COUNT=$(grep -c 'INFERENCE_API_SERVER_URL,"http://shield.windsurf.com:9999"' "$EXT_FILE")
if [ "$COUNT" -eq 1 ]; then
    echo "✅ INFERENCE_API_SERVER_URL redirected (1 instance)"
    ((PASS++))
else
    echo "❌ INFERENCE_API_SERVER_URL not patched (found $COUNT, expected 1)"
    ((FAIL++))
fi

# Patch 2: DEFAULT_API_SERVER_URL
COUNT=$(grep -c 'DEFAULT_API_SERVER_URL="http://shield.windsurf.com:9999"' "$EXT_FILE")
if [ "$COUNT" -eq 1 ]; then
    echo "✅ DEFAULT_API_SERVER_URL redirected (1 instance)"
    ((PASS++))
else
    echo "❌ DEFAULT_API_SERVER_URL not patched (found $COUNT, expected 1)"
    ((FAIL++))
fi

# Patch 3: DEFAULT_REGISTER_API_SERVER_URL
COUNT=$(grep -c 'DEFAULT_REGISTER_API_SERVER_URL="http://shield.windsurf.com:9999"' "$EXT_FILE")
if [ "$COUNT" -eq 1 ]; then
    echo "✅ DEFAULT_REGISTER_API_SERVER_URL redirected (1 instance)"
    ((PASS++))
else
    echo "❌ DEFAULT_REGISTER_API_SERVER_URL not patched (found $COUNT, expected 1)"
    ((FAIL++))
fi

# Patch 4: EU routes
COUNT=$(grep -c '"http://shield.windsurf.com:9999"' "$EXT_FILE" | grep -v "INFERENCE\|DEFAULT")
if [ "$COUNT" -ge 2 ]; then
    echo "✅ EU/Fed routes redirected (multiple instances)"
    ((PASS++))
else
    echo "⚠️  EU/Fed routes may not be fully patched"
fi

# Patch 5: Unleash
COUNT=$(grep -c 'url:"http://shield.windsurf.com:9999/unleash/"' "$EXT_FILE")
if [ "$COUNT" -eq 1 ]; then
    echo "✅ Unleash redirected (1 instance)"
    ((PASS++))
else
    echo "❌ Unleash not patched (found $COUNT, expected 1)"
    ((FAIL++))
fi

# Patch 6: HG_OPT function
COUNT=$(grep -c "globalThis.HG_OPT" "$EXT_FILE")
if [ "$COUNT" -gt 0 ]; then
    echo "✅ HG_OPT function present ($COUNT references)"
    ((PASS++))
else
    echo "❌ HG_OPT function not found"
    ((FAIL++))
fi

# Patch 7: Total proxy references
TOTAL=$(grep -o "shield.windsurf.com:9999" "$EXT_FILE" | wc -l)
echo ""
echo "📊 Total proxy references: $TOTAL"

# Check for any remaining external URLs
echo ""
echo "🔍 Checking for unpatched external URLs..."
EXTERNAL=$(grep -o "https://inference.codeium.com\|https://server.codeium.com\|https://register.windsurf.com" "$EXT_FILE" | wc -l)
if [ "$EXTERNAL" -eq 0 ]; then
    echo "✅ No external API URLs found (all redirected)"
    ((PASS++))
else
    echo "⚠️  Found $EXTERNAL external API URL(s) - may need patching"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Results: ✅ $PASS passed, ❌ $FAIL failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$FAIL" -eq 0 ]; then
    echo ""
    echo "🎉 All patches verified successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Windsurf if not already done"
    echo "  2. Test Cascade (Ctrl+L)"
    echo "  3. Monitor: tail -f logs/cascade_midway.log"
    exit 0
else
    echo ""
    echo "⚠️  Some patches missing - run: python3 src/patch_windsurf_client.py"
    exit 1
fi
