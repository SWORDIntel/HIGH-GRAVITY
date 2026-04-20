#!/bin/bash
# Network-level redirect for Windsurf API traffic
# Redirects HTTPS traffic to HIGH-GRAVITY proxy

SUDO_PASS="1786"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     HIGH-GRAVITY Network Redirect Setup                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# List of Codeium/Windsurf IPs to redirect
CODEIUM_IPS=(
    "35.223.238.178"  # server.codeium.com / inference.codeium.com
    "34.49.14.144"    # Other Codeium endpoint
)

echo "[*] Setting up iptables rules to redirect Codeium traffic..."
echo ""

for IP in "${CODEIUM_IPS[@]}"; do
    echo "  Redirecting: $IP:443 → 127.0.0.1:9999"
    
    # Redirect outgoing HTTPS to Codeium to our proxy
    echo "$SUDO_PASS" | sudo -S iptables -t nat -A OUTPUT \
        -p tcp -d "$IP" --dport 443 \
        -j DNAT --to-destination 127.0.0.1:9999 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "    ✓ Rule added"
    else
        echo "    ✗ Failed to add rule"
    fi
done

echo ""
echo "[*] Current iptables NAT rules:"
echo "$SUDO_PASS" | sudo -S iptables -t nat -L OUTPUT -n -v | grep -E "127.0.0.1:9999|Chain OUTPUT"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     To remove these rules later:                           ║"
echo "║     sudo iptables -t nat -F OUTPUT                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
