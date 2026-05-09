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

options=("Patch" "Unpatch" "Start" "Dashboard" "Stop" "Exit")
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
                "Dashboard") bash ./hg.sh dashboard ;;
                "Stop") bash ./hg.sh stop ;;
                "Exit") clear; exit 0 ;;
            esac
            read -p "Press Enter to return to menu..."
            ;;
    esac
done
