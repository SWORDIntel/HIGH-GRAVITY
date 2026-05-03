#!/usr/bin/env bash

set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run this script as root: sudo $0 [--timeout SECONDS] [--config PATH]" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_CONFIG="${SCRIPT_DIR}/../config/mullvad.conf"
CONFIG_FILE="$DEFAULT_CONFIG"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-90}"
LOG_FILE="${LOG_FILE:-${XDG_RUNTIME_DIR:-/tmp}/mullvad-autodown.log}"

usage() {
  cat <<'EOF'
Usage: sudo mullvad-temp-up.sh [--timeout SECONDS] [--config PATH]

Brings the Mullvad WireGuard tunnel up and schedules a detached teardown
after the timeout. The teardown survives if the interactive session dies.
EOF
}

while (($#)); do
  case "$1" in
    -t|--timeout)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Missing value for --timeout" >&2
        exit 2
      fi
      TIMEOUT_SECONDS="$1"
      ;;
    -c|--config)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Missing value for --config" >&2
        exit 2
      fi
      CONFIG_FILE="$1"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if ! [[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$TIMEOUT_SECONDS" -le 0 ]]; then
  echo "TIMEOUT_SECONDS must be a positive integer" >&2
  exit 2
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Config file not found: $CONFIG_FILE" >&2
  exit 1
fi

if ! command -v wg-quick >/dev/null 2>&1; then
  echo "wg-quick is not installed or not on PATH" >&2
  exit 1
fi

INTERFACE="$(basename "$CONFIG_FILE" .conf)"
mkdir -p "$(dirname "$LOG_FILE")"

nohup bash -c "sleep '$TIMEOUT_SECONDS'; wg-quick down '$INTERFACE'" \
  >"$LOG_FILE" 2>&1 &

echo "Mullvad tunnel teardown scheduled in ${TIMEOUT_SECONDS}s; log: ${LOG_FILE}"
echo "Bringing up ${CONFIG_FILE}..."
wg-quick up "$CONFIG_FILE"
echo "Tunnel up. It will be torn down automatically when the timer expires."
