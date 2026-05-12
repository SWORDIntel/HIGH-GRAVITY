#!/bin/bash
# HIGH-GRAVITY TUI Dashboard
# Arrow-key navigation for system management

show_menu() {
    clear
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "              HIGH-GRAVITY Control Plane                  "
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  [↑/↓] Navigate | [Enter] Select"
    echo ""
    for i in "${!options[@]}"; do
        if [ "$i" == "$current_idx" ]; then
            echo -e "  > \e[32m${options[$i]}\e[0m"
        else
            echo "    ${options[$i]}"
        fi
    done
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

show_proxy_mode_menu() {
    local action="$1"
    local mode_idx=0
    local modes=("cache-first" "cache-only" "confirm" "block" "local-only" "Back")
    local descriptions=(
        "Forward cache misses upstream; safest normal Windsurf mode"
        "Replay cache hits only; block misses locally"
        "Block misses locally with explicit gate telemetry"
        "Block all upstream inference misses"
        "Local-only alias for block behavior"
        "Return to main menu"
    )

    while true; do
        clear
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "              HIGH-GRAVITY Proxy Mode Select              "
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  Action: $action C proxy"
        echo "  [↑/↓] Navigate | [Enter] Select"
        echo ""
        for i in "${!modes[@]}"; do
            if [ "$i" == "$mode_idx" ]; then
                echo -e "  > \e[32m${modes[$i]}\e[0m - ${descriptions[$i]}"
            else
                echo "    ${modes[$i]} - ${descriptions[$i]}"
            fi
        done
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        read -rsn1 key
        case "$key" in
            $'\x1b')
                read -rsn2 -t 0.1 key
                case "$key" in
                    '[A') ((mode_idx--)); [ $mode_idx -lt 0 ] && mode_idx=$((${#modes[@]}-1)) ;;
                    '[B') ((mode_idx++)); [ $mode_idx -ge ${#modes[@]} ] && mode_idx=0 ;;
                esac
                ;;
            "")
                if [ "${modes[$mode_idx]}" = "Back" ]; then
                    return 0
                fi
                if [ "$action" = "Restart" ]; then
                    bash ./hg.sh restart-proxy-c "${modes[$mode_idx]}"
                else
                    bash ./hg.sh start-proxy-c "${modes[$mode_idx]}"
                fi
                return $?
                ;;
        esac
    done
}

options=("Patch" "Unpatch" "Start" "Start C Proxy Mode" "Restart C Proxy Mode" "Dashboard" "HMI Dashboard" "Stop" "Exit")
current_idx=0

while true; do
    show_menu
    read -rsn1 key
    case "$key" in
        $'\x1b') 
            read -rsn2 -t 0.1 key
            case "$key" in
                '[A') ((current_idx--)); [ $current_idx -lt 0 ] && current_idx=$((${#options[@]}-1)) ;;
                '[B') ((current_idx++)); [ $current_idx -ge ${#options[@]} ] && current_idx=0 ;;
            esac
            ;;
        "") 
            case "${options[$current_idx]}" in
                "Patch") bash ./hg.sh patch ;;
                "Unpatch") bash ./hg.sh unpatch ;;
                "Start") bash ./hg.sh start ;;
                "Start C Proxy Mode") show_proxy_mode_menu "Start" ;;
                "Restart C Proxy Mode") show_proxy_mode_menu "Restart" ;;
                "Dashboard") bash ./hg.sh dashboard ;;
                "HMI Dashboard") bash ./hg.sh hmi-dashboard ;;
                "Stop") bash ./hg.sh stop ;;
                "Exit") clear; exit 0 ;;
            esac
            read -p "Press Enter to return to menu..."
            ;;
    esac
done
