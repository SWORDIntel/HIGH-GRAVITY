#!/bin/bash
# Proxmox-native KP14 runner: execute KP14 inside a Proxmox VM through qm + guest-agent.

set -euo pipefail

VMID="${KP14_VMID:-9211}"
NODE="${KP14_NODE:-r320}"
VM_USER="${KP14_VM_USER:-debian}"
DEFAULT_LS_DIR="/usr/share/windsurf-next/resources/app/extensions/windsurf/bin"
if [[ -x "$DEFAULT_LS_DIR/language_server_linux_x64.real" ]]; then
  TARGET="${1:-$DEFAULT_LS_DIR/language_server_linux_x64.real}"
elif [[ -x "$DEFAULT_LS_DIR/language_server_linux_x64.original" ]]; then
  TARGET="${1:-$DEFAULT_LS_DIR/language_server_linux_x64.original}"
else
  TARGET="${1:-$DEFAULT_LS_DIR/language_server_linux_x64}"
fi

QM_BIN="$(command -v qm 2>/dev/null || true)"
PVESH_BIN="$(command -v pvesh 2>/dev/null || true)"
SUDO_BIN="$(command -v sudo 2>/dev/null || true)"
[[ -n "$QM_BIN" ]] || QM_BIN="/usr/sbin/qm"
[[ -n "$PVESH_BIN" ]] || PVESH_BIN="/usr/sbin/pvesh"

[[ -x "$QM_BIN" ]] || { echo "[!] Missing required command: qm" >&2; exit 1; }
[[ -x "$PVESH_BIN" ]] || { echo "[!] Missing required command: pvesh" >&2; exit 1; }
[[ -x "$SUDO_BIN" ]] || { echo "[!] Missing required command: sudo" >&2; exit 1; }

if [[ ! -f "$TARGET" ]]; then
  echo "[!] Target binary not found on host: $TARGET" >&2
  exit 1
fi

echo "[*] Ensuring VM $VMID is running..."
if ! echo 1786 | sudo -S "$QM_BIN" status "$VMID" | grep -q "running"; then
  echo 1786 | sudo -S "$QM_BIN" start "$VMID" >/dev/null
fi

echo "[*] Waiting for QEMU guest agent in VM $VMID..."
for _ in $(seq 1 20); do
  if echo 1786 | sudo -S "$QM_BIN" guest cmd "$VMID" ping >/dev/null 2>&1; then
    AGENT_UP=1
    break
  fi
  sleep 3
done

if [[ "${AGENT_UP:-0}" != "1" ]]; then
  echo "[!] VM $VMID is up but QEMU guest agent is not responding." >&2
  echo "    Fix inside guest then re-run:" >&2
  echo "    1) sudo apt-get update && sudo apt-get install -y qemu-guest-agent" >&2
  echo "    2) sudo systemctl enable --now qemu-guest-agent" >&2
  echo "    3) verify from host: sudo $QM_BIN guest cmd $VMID ping" >&2
  exit 1
fi

TARGET_BASE="$(basename "$TARGET")"
TARGET_DIR="$(dirname "$TARGET")"
HOST_VM_IP="$(ip -4 -o addr show vmbr0 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -1 || true)"
if [[ -z "$HOST_VM_IP" ]]; then
  HOST_VM_IP="$(hostname -I | awk '{print $1}')"
fi
if [[ -z "$HOST_VM_IP" ]]; then
  echo "[!] Could not determine host IP for VM transfer." >&2
  exit 1
fi

HTTP_PORT="${KP14_HTTP_PORT:-18080}"
echo "[*] Hosting $TARGET_BASE on http://$HOST_VM_IP:$HTTP_PORT ..."
pushd "$TARGET_DIR" >/dev/null
python3 -m http.server "$HTTP_PORT" --bind "$HOST_VM_IP" >/tmp/hg_kp14_http.log 2>&1 &
HTTP_PID=$!
popd >/dev/null
cleanup() {
  kill "$HTTP_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[*] Copying target into VM $VMID..."
COPY_JSON="$(echo 1786 | sudo -S "$QM_BIN" guest exec "$VMID" --synchronous 1 -- /bin/sh -lc \
  "set -e; mkdir -p /tmp/hg_kp14; \
   if command -v curl >/dev/null 2>&1; then \
     curl -fsSL http://$HOST_VM_IP:$HTTP_PORT/$TARGET_BASE -o /tmp/hg_kp14/$TARGET_BASE; \
   else \
     wget -qO /tmp/hg_kp14/$TARGET_BASE http://$HOST_VM_IP:$HTTP_PORT/$TARGET_BASE; \
   fi")"
COPY_PID="$(printf '%s' "$COPY_JSON" | jq -r '.pid // empty' 2>/dev/null || true)"
if [[ -n "$COPY_PID" ]]; then
  for _ in $(seq 1 240); do
    COPY_JSON="$(echo 1786 | sudo -S "$QM_BIN" guest exec-status "$VMID" "$COPY_PID")"
    COPY_DONE="$(printf '%s' "$COPY_JSON" | jq -r '.exited // 0' 2>/dev/null || echo 0)"
    [[ "$COPY_DONE" == "1" ]] && break
    sleep 2
  done
fi
COPY_EXIT="$(printf '%s' "$COPY_JSON" | jq -r '.exitcode // 1' 2>/dev/null || echo 1)"
if [[ "$COPY_EXIT" != "0" ]]; then
  echo "[!] Failed to copy target into VM. guest-exec output:" >&2
  echo "$COPY_JSON" >&2
  exit 1
fi

echo "[*] Running KP14 inside VM $VMID..."
REMOTE_CMD='
set -euo pipefail
TARGET_GUEST="/tmp/hg_kp14/'"$TARGET_BASE"'"
if [ -x /home/debian/KP14/kp14 ]; then
  KP14_ROOT=/home/debian/KP14
elif [ -x /home/'"$VM_USER"'/KP14/kp14 ]; then
  KP14_ROOT=/home/'"$VM_USER"'/KP14
elif [ -x /opt/KP14_PROJECT/kp14 ]; then
  KP14_ROOT=/opt/KP14_PROJECT
elif [ -x /home/'"$VM_USER"'/KP14_PROJECT/kp14 ]; then
  KP14_ROOT=/home/'"$VM_USER"'/KP14_PROJECT
else
  echo "[!] KP14 launcher not found inside guest." >&2
  exit 2
fi
cd "$KP14_ROOT"
./kp14 analyze "$TARGET_GUEST"
'

RUN_JSON="$(echo 1786 | sudo -S "$QM_BIN" guest exec "$VMID" --synchronous 1 -- /bin/sh -lc "$REMOTE_CMD")"
RUN_PID="$(printf '%s' "$RUN_JSON" | jq -r '.pid // empty' 2>/dev/null || true)"
if [[ -n "$RUN_PID" ]]; then
  for _ in $(seq 1 720); do
    RUN_JSON="$(echo 1786 | sudo -S "$QM_BIN" guest exec-status "$VMID" "$RUN_PID")"
    RUN_DONE="$(printf '%s' "$RUN_JSON" | jq -r '.exited // 0' 2>/dev/null || echo 0)"
    [[ "$RUN_DONE" == "1" ]] && break
    sleep 5
  done
fi
RUN_EXIT="$(printf '%s' "$RUN_JSON" | jq -r '.exitcode // 1' 2>/dev/null || echo 1)"
if [[ "$RUN_EXIT" != "0" ]]; then
  echo "$RUN_JSON"
  exit "$RUN_EXIT"
fi
echo "[*] KP14 execution completed via Proxmox guest agent."
