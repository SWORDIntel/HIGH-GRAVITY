#!/bin/bash
# Safe NCS2/MYRIAD probe and explicit USB reset helper.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SCRIPT_DIR"

SUDO_PASS="${SUDO_PASS:-1786}"
ACTION="${1:-status}"
SUMMARY_FILE="${HG_NCS2_SUMMARY_FILE:-logs/khoj_ncs2_recovery.json}"

sudo_cmd() {
    printf '%s\n' "$SUDO_PASS" | sudo -S "$@"
}

ensure_logs() {
    mkdir -p logs
}

run_accel_probe() {
    bash scripts/hg_khoj.sh accel >/dev/null
}

write_summary() {
    local lsusb_tmp
    lsusb_tmp="$(mktemp)"
    if command -v lsusb >/dev/null 2>&1; then
        lsusb > "$lsusb_tmp" 2>/dev/null || true
    fi
    python3 scripts/internal/khoj_ncs2_recover.py \
        --status-file logs/khoj_accel.json \
        --lsusb-file "$lsusb_tmp" > "$SUMMARY_FILE"
    rm -f "$lsusb_tmp"
}

print_summary() {
    if command -v jq >/dev/null 2>&1; then
        jq . "$SUMMARY_FILE"
    else
        cat "$SUMMARY_FILE"
    fi
}

device_paths() {
    python3 - "$SUMMARY_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)
for device in data.get("usb_devices", []):
    path = device.get("path")
    if path:
        print(path)
PY
}

reset_one_device() {
    local dev_path="$1"
    local bus
    local dev
    local sysdev=""

    if [ ! -e "$dev_path" ]; then
        echo "[*] Skipping stale NCS2 USB path $dev_path"
        return 0
    fi

    bus="$(basename "$(dirname "$dev_path")")"
    dev="$(basename "$dev_path")"

    for candidate in /sys/bus/usb/devices/*; do
        [ -f "$candidate/busnum" ] && [ -f "$candidate/devnum" ] || continue
        if [ "$(cat "$candidate/busnum" 2>/dev/null)" = "$bus" ] && [ "$(cat "$candidate/devnum" 2>/dev/null)" = "$dev" ]; then
            sysdev="$candidate"
            break
        fi
    done

    echo "[*] Resetting NCS2 USB device $dev_path"
    if command -v usbreset >/dev/null 2>&1; then
        if sudo_cmd usbreset "$bus/$dev"; then
            return
        fi
        if [ ! -e "$dev_path" ]; then
            echo "[*] NCS2 path disappeared during reset: $dev_path"
            return 0
        fi
        echo "[*] usbreset failed for $dev_path; trying sysfs authorized toggle if available."
    fi

    if [ -n "$sysdev" ] && [ -f "$sysdev/authorized" ]; then
        echo "    using sysfs authorized toggle at $sysdev"
        printf '0\n' | sudo_cmd tee "$sysdev/authorized" >/dev/null
        sleep 2
        printf '1\n' | sudo_cmd tee "$sysdev/authorized" >/dev/null
        return
    fi

    if [ ! -e "$dev_path" ]; then
        echo "[*] NCS2 path disappeared before fallback reset: $dev_path"
        return 0
    fi

    echo "[-] Cannot reset $dev_path: install usbutils with usbreset support or physically replug the stick." >&2
    return 1
}

case "$ACTION" in
    status)
        ensure_logs
        if [ ! -f logs/khoj_accel.json ]; then
            echo "[*] No accel status yet; running probe first."
            run_accel_probe
        fi
        write_summary
        print_summary
        ;;
    probe)
        ensure_logs
        run_accel_probe
        write_summary
        print_summary
        ;;
    reset)
        ensure_logs
        write_summary
        if ! device_paths | grep -q .; then
            print_summary
            echo "[-] No NCS2/Movidius USB devices found to reset."
            exit 1
        fi
        while IFS= read -r dev_path; do
            [ -n "$dev_path" ] || continue
            reset_one_device "$dev_path"
        done < <(device_paths)
        echo "[*] Waiting for USB re-enumeration..."
        sleep 5
        run_accel_probe
        write_summary
        print_summary
        ;;
    restart-khoj)
        echo "[*] Recreating Khoj after NCS2 recovery."
        HG_KHOJ_RECREATE=1 bash scripts/internal/khoj_docker.sh
        bash "$0" probe
        ;;
    *)
        echo "Usage: ./hg.sh khoj ncs2 {status|probe|reset|restart-khoj}"
        exit 1
        ;;
esac
