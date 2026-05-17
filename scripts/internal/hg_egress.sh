#!/usr/bin/env bash
# Detect and optionally trap Windsurf language-server direct-IP egress.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SCRIPT_DIR"

SUDO_PASS="${SUDO_PASS:-1786}"
TARGET_USER="${SUDO_USER:-${HG_EGRESS_USER:-john}}"
TARGET_UID="$(id -u "$TARGET_USER" 2>/dev/null || id -u)"
CHAIN="HG-WINDSURF-EGRESS"
PORT="${HG_PROXY_HTTPS_PORT:-443}"
KNOWN_DOMAINS=(
    "proxy.windsurf.com"
    "inference.codeium.com"
    "unleash.codeium.com"
    "server.self-serve.windsurf.com"
)

# Dynamically resolve IPs
resolve_ips() {
    local ips=()
    for domain in "${KNOWN_DOMAINS[@]}"; do
        local ip
        ip=$(dig +short "$domain" @1.1.1.1 | tail -n1)
        if [[ -n "$ip" ]]; then
            ips+=("$ip")
        fi
    done
    echo "${ips[@]}"
}

sudo_iptables() {
    echo "$SUDO_PASS" | sudo -S iptables "$@" >/dev/null 2>&1
}

ensure_chain() {
    sudo_iptables -t nat -N "$CHAIN" || true
    sudo_iptables -t nat -C OUTPUT -j "$CHAIN" || sudo_iptables -t nat -A OUTPUT -j "$CHAIN"
}

clear_chain() {
    sudo_iptables -t nat -D OUTPUT -j "$CHAIN" || true
    sudo_iptables -t nat -F "$CHAIN" || true
    sudo_iptables -t nat -X "$CHAIN" || true
}

enable_shield() {
    ensure_chain
    sudo_iptables -t nat -F "$CHAIN" || true
    sudo_iptables -t nat -A "$CHAIN" -o lo -j RETURN
    sudo_iptables -t nat -A "$CHAIN" -p tcp -m owner ! --uid-owner "$TARGET_UID" -j RETURN
    
    local resolved_ips
    resolved_ips=$(resolve_ips)
    for ip in $resolved_ips; do
        sudo_iptables -t nat -A "$CHAIN" -p tcp -d "$ip" --dport 443 -j REDIRECT --to-ports "$PORT"
    done
    echo "egress shield enabled for uid=$TARGET_UID port=$PORT"
    echo "Shielded IPs: $resolved_ips"
}

status_shield() {
    if sudo iptables -t nat -S "$CHAIN" >/dev/null 2>&1; then
        echo "egress shield: active"
        sudo iptables -t nat -S "$CHAIN" 2>/dev/null | sed 's/^/  /'
    else
        echo "egress shield: inactive"
    fi
    echo "direct language-server sockets:"
    ss -tanpH state established '( dport = :443 )' 2>/dev/null \
        | awk '
            /language_server/ {
                peer = ""
                for (i = 1; i <= NF; i++) {
                    if ($i ~ /:443$/ || $i ~ /:https$/) {
                        if ($i !~ /^127[.]0[.]0[.]1:/ && $i !~ /^\[::1\]:/) {
                            peer = $i
                        }
                    }
                }
                if (peer != "") print "  " $0
            }
        ' \
        || true
}

case "${1:-status}" in
    on|enable|start)
        enable_shield
        status_shield
        ;;
    off|disable|stop)
        clear_chain
        echo "egress shield disabled"
        ;;
    status|check)
        status_shield
        ;;
    *)
        echo "usage: ./hg.sh egress {status|on|off}" >&2
        exit 2
        ;;
esac
