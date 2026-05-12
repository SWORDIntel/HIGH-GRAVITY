#!/bin/bash
# HIGH-GRAVITY Khoj Docker Launcher

set -e
set -o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SCRIPT_DIR"
LAUNCH_LOCK="$SCRIPT_DIR/logs/khoj_docker.launch.lock"
mkdir -p logs

# Prevent concurrent launcher runs from stepping on each other and creating
# container name races.
if command -v flock >/dev/null 2>&1; then
    exec 9>"$LAUNCH_LOCK"
    if ! flock -n 9; then
        echo "[*] Khoj launcher already running; skipping concurrent start."
        exit 0
    fi
fi

echo "[*] Starting Khoj via Docker..."

# Use a dedicated user-defined bridge network (avoid legacy --link behavior)
KHOJ_NET="khoj-net"
docker network inspect "$KHOJ_NET" >/dev/null 2>&1 || docker network create "$KHOJ_NET" >/dev/null
LAN_IP="${HG_KHOJ_DOMAIN:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
ACCEL_STATUS_FILE="$SCRIPT_DIR/logs/khoj_accel.json"
KHOJ_DEFAULT_TORCH_VERSION="${HG_KHOJ_CUDA_TORCH_VERSION:-2.5.1+cu121}"
KHOJ_OPENVINO_VERSION=""
KHOJ_OPENVINO_SOURCE=""
KHOJ_OPENVINO_HOST_DIR="${HG_KHOJ_OPENVINO_HOST_DIR:-/opt/intel/openvino_2022.3.1}"

container_state() {
    docker inspect -f '{{.State.Status}}' "$1" 2>/dev/null || echo "missing"
}

container_is_running() {
    [ "$(container_state "$1")" = "running" ]
}

wait_for_db() {
    local user="${1:-khoj}"
    local db="${2:-khoj}"
    for _ in {1..120}; do
        container_is_running khoj-pg || return 1
        if docker exec khoj-pg pg_isready -U "$user" -d "$db" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

bool_true() {
    case "${1,,}" in
        1|true|yes|on)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

json_status() {
    local phase="$1"
    local runtime_file="${2:-}"
    PHASE="$phase" \
    ACCEL_MODE="${HG_KHOJ_ACCEL:-auto}" \
    CUDA_HOST_DETECTED="${CUDA_HOST_DETECTED:-0}" \
    CUDA_ENABLED="${CUDA_ENABLED:-0}" \
    OPENVINO_HOST_DETECTED="${OPENVINO_HOST_DETECTED:-0}" \
    OPENVINO_ENABLED="${OPENVINO_ENABLED:-0}" \
    MYRIAD_HOST_DETECTED="${MYRIAD_HOST_DETECTED:-0}" \
    MYRIAD_ENABLED="${MYRIAD_ENABLED:-0}" \
    NPU_HOST_DETECTED="${NPU_HOST_DETECTED:-0}" \
    NPU_ENABLED="${NPU_ENABLED:-0}" \
    NVIDIA_NAME="${NVIDIA_NAME:-}" \
    OPENVINO_HOST_DEVICES="${OPENVINO_HOST_DEVICES:-}" \
    MYRIAD_COUNT="${MYRIAD_COUNT:-0}" \
    python3 "$SCRIPT_DIR/scripts/internal/khoj_accel_status.py" \
        --phase "$phase" \
        --runtime-file "$runtime_file" > "$ACCEL_STATUS_FILE"
}

detect_acceleration() {
    local mode="${HG_KHOJ_ACCEL:-auto}"
    local openvino_device_override="${HG_KHOJ_OPENVINO_DEVICE:-}"
    CUDA_ENABLED=0
    CUDA_HOST_DETECTED=0
    OPENVINO_ENABLED=0
    OPENVINO_HOST_DETECTED=0
    MYRIAD_ENABLED=0
    MYRIAD_HOST_DETECTED=0
    NPU_ENABLED=0
    NPU_HOST_DETECTED=0
    MYRIAD_COUNT=0
    NVIDIA_NAME=""
    OPENVINO_HOST_DEVICES=""
    DOCKER_ACCEL_ARGS=()
    DOCKER_ACCEL_ENVS=()

    if command -v nvidia-smi >/dev/null 2>&1; then
        CUDA_HOST_DETECTED=1
        NVIDIA_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || true)"
    fi
    if [ "$CUDA_HOST_DETECTED" = "1" ] && docker info 2>/dev/null | grep -q "nvidia"; then
        case "$mode" in
            auto|cuda|gpu|all)
                CUDA_ENABLED=1
                DOCKER_ACCEL_ARGS+=(--gpus all)
                DOCKER_ACCEL_ENVS+=(
                    -e NVIDIA_VISIBLE_DEVICES=all
                    -e NVIDIA_DRIVER_CAPABILITIES=compute,utility
                    -e CUDA_VISIBLE_DEVICES=0
                    -e PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
                )
                ;;
        esac
    fi

    if [ -x "$SCRIPT_DIR/.hg_proxy_venv/bin/python" ]; then
        OPENVINO_HOST_DEVICES="$("$SCRIPT_DIR/.hg_proxy_venv/bin/python" - <<'PY' 2>/dev/null || true
try:
    import openvino as ov
    print(",".join(ov.Core().available_devices))
except Exception:
    pass
PY
)"
        [ -n "$OPENVINO_HOST_DEVICES" ] && OPENVINO_HOST_DETECTED=1
    fi

    if [ -d /dev/dri ]; then
        OPENVINO_HOST_DETECTED=1
        case "$mode" in
            auto|openvino|gpu|npu|all)
                OPENVINO_ENABLED=1
                DOCKER_ACCEL_ARGS+=(-v /dev/dri:/dev/dri)
                render_gid="$(getent group render 2>/dev/null | awk -F: '{print $3}' || true)"
                video_gid="$(getent group video 2>/dev/null | awk -F: '{print $3}' || true)"
                [ -n "$render_gid" ] && DOCKER_ACCEL_ARGS+=(--group-add "$render_gid")
                [ -n "$video_gid" ] && DOCKER_ACCEL_ARGS+=(--group-add "$video_gid")
                ;;
        esac
    fi

    if [ -d /dev/accel ]; then
        NPU_HOST_DETECTED=1
        OPENVINO_HOST_DETECTED=1
        case "$mode" in
            auto|openvino|npu|all)
                NPU_ENABLED=1
                OPENVINO_ENABLED=1
                DOCKER_ACCEL_ARGS+=(-v /dev/accel:/dev/accel)
                ;;
        esac
    fi

    if command -v lsusb >/dev/null 2>&1; then
        MYRIAD_COUNT="$(
            lsusb 2>/dev/null | awk '
                /03e7:2485/ || /03e7:2491/ || /Intel.*Movidius/ || /Intel.*Myriad/ || /Intel.*Neural Compute/ {count++}
                END {print count+0}
            '
        )"
    fi
    if [ "${MYRIAD_COUNT:-0}" -gt 0 ]; then
        MYRIAD_HOST_DETECTED=1
        OPENVINO_HOST_DETECTED=1
        case "$mode" in
            auto|openvino|myriad|npu|all)
                MYRIAD_ENABLED=1
                OPENVINO_ENABLED=1
                DOCKER_ACCEL_ARGS+=(
                    -v /dev/bus/usb:/dev/bus/usb
                    --device-cgroup-rule "c 189:* rmw"
                )
                [ -d /run/udev ] && DOCKER_ACCEL_ARGS+=(-v /run/udev:/run/udev:ro)
                users_gid="$(getent group users 2>/dev/null | awk -F: '{print $3}' || true)"
                [ -n "$users_gid" ] && DOCKER_ACCEL_ARGS+=(--group-add "$users_gid")
                [ -z "$openvino_device_override" ] && openvino_device_override="MYRIAD"
                if [ -d "$KHOJ_OPENVINO_HOST_DIR" ]; then
                    KHOJ_OPENVINO_SOURCE="${HG_KHOJ_OPENVINO_SOURCE:-host}"
                    KHOJ_OPENVINO_VERSION="${HG_KHOJ_OPENVINO_VERSION:-2022.3.1-host}"
                    DOCKER_ACCEL_ARGS+=(-v "$KHOJ_OPENVINO_HOST_DIR:$KHOJ_OPENVINO_HOST_DIR:ro")
                else
                    KHOJ_OPENVINO_SOURCE="${HG_KHOJ_OPENVINO_SOURCE:-pip}"
                    KHOJ_OPENVINO_VERSION="${HG_KHOJ_OPENVINO_VERSION:-2022.3.2}"
                fi
                ;;
        esac
    fi

    if [ "$OPENVINO_ENABLED" = "1" ]; then
        OPENVINO_DEVICE="${openvino_device_override:-AUTO}"
        KHOJ_OPENVINO_VERSION="${KHOJ_OPENVINO_VERSION:-${HG_KHOJ_OPENVINO_VERSION:-}}"
        KHOJ_OPENVINO_SOURCE="${KHOJ_OPENVINO_SOURCE:-${HG_KHOJ_OPENVINO_SOURCE:-pip}}"
        DOCKER_ACCEL_ENVS+=(
            -e OPENVINO_DEVICE="${OPENVINO_DEVICE}"
            -e OV_CACHE_DIR=/root/.cache/openvino
            -e KHOJ_ACCEL_OPENVINO=1
            -e KHOJ_OPENVINO_VERSION="${KHOJ_OPENVINO_VERSION}"
            -e KHOJ_OPENVINO_SOURCE="${KHOJ_OPENVINO_SOURCE}"
        )
        if [ "$KHOJ_OPENVINO_SOURCE" = "host" ]; then
            DOCKER_ACCEL_ENVS+=(
                -e INTEL_OPENVINO_DIR="$KHOJ_OPENVINO_HOST_DIR"
                -e HDDL_INSTALL_DIR="$KHOJ_OPENVINO_HOST_DIR/runtime/3rdparty/hddl"
                -e PYTHONPATH="$KHOJ_OPENVINO_HOST_DIR/python/python3.10:/app/src:/workspace"
                -e LD_LIBRARY_PATH="$KHOJ_OPENVINO_HOST_DIR/tools/compile_tool:$KHOJ_OPENVINO_HOST_DIR/runtime/3rdparty/tbb/lib:$KHOJ_OPENVINO_HOST_DIR/runtime/3rdparty/hddl/lib:$KHOJ_OPENVINO_HOST_DIR/runtime/lib/intel64"
            )
        fi
    fi
    if [ "$CUDA_ENABLED" = "1" ]; then
        DOCKER_ACCEL_ENVS+=(
            -e KHOJ_ACCEL_CUDA=1
            -e KHOJ_INSTALL_CUDA_TORCH="${HG_KHOJ_INSTALL_CUDA_TORCH:-1}"
            -e KHOJ_CUDA_TORCH_VERSION="${KHOJ_DEFAULT_TORCH_VERSION}"
            -e KHOJ_CUDA_TORCH_INDEX="${HG_KHOJ_CUDA_TORCH_INDEX:-https://download.pytorch.org/whl/cu121}"
        )
    fi
    if [ "$MYRIAD_ENABLED" = "1" ]; then
        DOCKER_ACCEL_ENVS+=(-e KHOJ_ACCEL_MYRIAD=1)
    fi
    if [ "$OPENVINO_ENABLED" = "1" ]; then
        DOCKER_ACCEL_ENVS+=(-e KHOJ_INSTALL_OPENVINO="${HG_KHOJ_INSTALL_OPENVINO:-1}")
    fi

    json_status "detected"
    echo "[*] Accel mode    : $mode"
    echo "[*] CUDA host     : $CUDA_HOST_DETECTED ${NVIDIA_NAME:+($NVIDIA_NAME)}"
    echo "[*] CUDA exposed  : $CUDA_ENABLED"
    echo "[*] OpenVINO devs : ${OPENVINO_HOST_DEVICES:-none}"
    echo "[*] Myriad sticks : $MYRIAD_COUNT"
}

probe_container_acceleration() {
    local tmp
    tmp="$(mktemp)"
    if docker exec -i khoj python3 - < "$SCRIPT_DIR/scripts/internal/khoj_accel_runtime_probe.py" > "$tmp" 2>/dev/null; then
        :
    else
        echo '{"error":"docker_exec_failed"}' > "$tmp"
    fi
    json_status "runtime_probed" "$tmp"
    rm -f "$tmp"
}

# Persistent on-disk state (models/cache/db)
if [ -d "/tank" ]; then
    DEFAULT_KHOJ_STATE_DIR="/tank/khoj"
else
    DEFAULT_KHOJ_STATE_DIR="$(pwd)/data/khoj"
fi
KHOJ_STATE_DIR="${HG_KHOJ_STATE_DIR:-$DEFAULT_KHOJ_STATE_DIR}"
KHOJ_PGDATA_DIR="${HG_KHOJ_PGDATA_DIR:-$KHOJ_STATE_DIR/postgres}"
KHOJ_CACHE_DIR="${HG_KHOJ_CACHE_DIR:-$KHOJ_STATE_DIR/cache}"
KHOJ_APPDATA_DIR="${HG_KHOJ_APPDATA_DIR:-$KHOJ_STATE_DIR/app}"
mkdir -p "$KHOJ_PGDATA_DIR" "$KHOJ_CACHE_DIR" "$KHOJ_APPDATA_DIR"
echo "[*] Khoj state dir: $KHOJ_STATE_DIR"
echo "[*] Postgres data : $KHOJ_PGDATA_DIR"
echo "[*] Model cache   : $KHOJ_CACHE_DIR"
echo "[*] App data      : $KHOJ_APPDATA_DIR"
detect_acceleration

# Start postgres (always recreate to avoid stale host-network mode)
echo "[*] Starting PostgreSQL with pgvector..."
docker rm -f khoj-pg >/dev/null 2>&1 || true
docker run -d --name khoj-pg \
    --privileged \
    --network "$KHOJ_NET" \
    -e POSTGRES_USER=khoj \
    -e POSTGRES_PASSWORD=khoj \
    -e POSTGRES_DB=khoj \
    -v "$KHOJ_PGDATA_DIR:/var/lib/postgresql/data" \
    pgvector/pgvector:pg15 >/dev/null
if ! wait_for_db; then
    echo "[-] PostgreSQL did not become ready in time."
    exit 1
fi

if docker ps --format '{{.Names}}' | grep -qx "khoj"; then
    current_mode="$(docker inspect -f '{{ index .Config.Labels "highgravity.accel.mode" }}' khoj 2>/dev/null || true)"
    current_mode="${current_mode:-unknown}"
    current_usb_passthru="$(docker inspect -f '{{ index .Config.Labels "highgravity.accel.usb_passthru" }}' khoj 2>/dev/null || true)"
    current_openvino_version="$(docker inspect -f '{{ index .Config.Labels "highgravity.accel.openvino_version" }}' khoj 2>/dev/null || true)"
    current_openvino_device="$(docker inspect -f '{{ index .Config.Labels "highgravity.accel.openvino_device" }}' khoj 2>/dev/null || true)"
    current_openvino_source="$(docker inspect -f '{{ index .Config.Labels "highgravity.accel.openvino_source" }}' khoj 2>/dev/null || true)"
    current_devices="$(docker inspect -f '{{ json .HostConfig.DeviceRequests }}' khoj 2>/dev/null || true)"
    recreate=0
    [ "${HG_KHOJ_RECREATE:-0}" = "1" ] && recreate=1
    [ "$current_mode" != "${HG_KHOJ_ACCEL:-auto}" ] && recreate=1
    [ "$CUDA_ENABLED" = "1" ] && { [ -z "$current_devices" ] || [ "$current_devices" = "null" ]; } && recreate=1
    [ "$MYRIAD_ENABLED" = "1" ] && [ "$current_usb_passthru" != "v2" ] && recreate=1
    [ "$OPENVINO_ENABLED" = "1" ] && [ "${current_openvino_version:-}" != "${KHOJ_OPENVINO_VERSION:-}" ] && recreate=1
    [ "$OPENVINO_ENABLED" = "1" ] && [ "${current_openvino_device:-}" != "${OPENVINO_DEVICE:-}" ] && recreate=1
    [ "$OPENVINO_ENABLED" = "1" ] && [ "${current_openvino_source:-}" != "${KHOJ_OPENVINO_SOURCE:-}" ] && recreate=1
    if [ "$recreate" = "1" ]; then
        echo "[*] Recreating Khoj to apply acceleration devices..."
        docker rm -f khoj >/dev/null 2>&1 || true
    fi
fi

KHOJ_BOOTSTRAP='
set -e
is_true() {
  case "${1,,}" in
    1|true|yes|on)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

if [ "${KHOJ_ACCEL_CUDA:-0}" = "1" ] && is_true "${KHOJ_INSTALL_CUDA_TORCH:-0}"; then
  torch_version="${KHOJ_CUDA_TORCH_VERSION:-2.5.1+cu121}"
  torch_index="${KHOJ_CUDA_TORCH_INDEX:-https://download.pytorch.org/whl/cu121}"
  if ! KHOJ_CUDA_TORCH_VERSION="${torch_version}" python3 -c "import os; import torch; required = os.environ.get(\"KHOJ_CUDA_TORCH_VERSION\", \"\"); raise SystemExit(0 if (torch.__version__ == required and torch.cuda.is_available()) else 1)" >/dev/null 2>&1; then
    echo "[khoj-accel] Installing CUDA torch ${torch_version} from ${torch_index}"
    if ! python3 -m pip install --no-cache-dir --index-url "${torch_index}" "torch==${torch_version}"; then
      if ! KHOJ_CUDA_TORCH_VERSION="${torch_version}" python3 -c "import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)" >/dev/null 2>&1; then
        echo "[khoj-accel] Requested CUDA torch ${torch_version} unavailable and current install has no CUDA; keeping bootstrap from continuing."
        exit 1
      fi
      existing_torch="$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null || echo unknown)"
      echo "[khoj-accel] Requested torch ${torch_version} unavailable; continuing with existing CUDA runtime ${existing_torch}."
    fi
  fi
fi
if [ "${KHOJ_ACCEL_OPENVINO:-0}" = "1" ] && is_true "${KHOJ_INSTALL_OPENVINO:-0}"; then
  if [ "${KHOJ_OPENVINO_SOURCE:-}" = "host" ] && [ -n "${INTEL_OPENVINO_DIR:-}" ]; then
    if ! ldconfig -p 2>/dev/null | grep -q "libpugixml.so.1"; then
      echo "[khoj-accel] Installing host OpenVINO runtime system deps"
      apt-get update -qq
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libpugixml1v5 libusb-1.0-0 libudev1 libcap2
    fi
    if [ -f "${INTEL_OPENVINO_DIR}/setupvars.sh" ]; then
      source "${INTEL_OPENVINO_DIR}/setupvars.sh" -pyver 3.10 >/dev/null 2>&1 || true
    fi
    export PYTHONPATH="${INTEL_OPENVINO_DIR}/python/python3.10:/app/src:/workspace:${PYTHONPATH:-}"
    export LD_LIBRARY_PATH="${INTEL_OPENVINO_DIR}/tools/compile_tool:${INTEL_OPENVINO_DIR}/runtime/3rdparty/tbb/lib:${INTEL_OPENVINO_DIR}/runtime/3rdparty/hddl/lib:${INTEL_OPENVINO_DIR}/runtime/lib/intel64:${LD_LIBRARY_PATH:-}"
  fi
fi
if [ "${KHOJ_ACCEL_OPENVINO:-0}" = "1" ] && is_true "${KHOJ_INSTALL_OPENVINO:-0}" && [ "${KHOJ_OPENVINO_SOURCE:-}" != "host" ]; then
  ov_req="${KHOJ_OPENVINO_VERSION:-}"
  if [ -n "${ov_req}" ]; then
    ov_pkg="openvino==${ov_req}"
    ov_check="import openvino as ov; raise SystemExit(0 if ov.__version__.startswith(\"${ov_req}\") else 1)"
  else
    ov_pkg="openvino"
    ov_check="import openvino"
  fi
  if ! python3 -c "${ov_check}" >/dev/null 2>&1; then
    echo "[khoj-accel] Installing OpenVINO runtime ${ov_pkg}"
    python3 -m pip install --no-cache-dir --force-reinstall "${ov_pkg}"
  fi
fi
exec python3 src/khoj/main.py --host 0.0.0.0 --port 42110 --anonymous-mode
'

# Start khoj if not running
if container_is_running khoj; then
    echo "[*] Reusing existing running Khoj container."
else
    if docker ps -a --format '{{.Names}}' | grep -qx "khoj"; then
        docker rm -f khoj >/dev/null 2>&1 || true
    fi

    echo "[*] Starting Khoj..."
    docker run -d --name khoj \
        --privileged \
        "${DOCKER_ACCEL_ARGS[@]}" \
        --network "$KHOJ_NET" \
        --dns 8.8.8.8 --dns 1.1.1.1 \
        -p 42110:42110 \
        --entrypoint bash \
        --label highgravity.service=khoj \
        --label highgravity.accel.mode="${HG_KHOJ_ACCEL:-auto}" \
        --label highgravity.accel.usb_passthru=v2 \
        --label highgravity.accel.myriad_count="${MYRIAD_COUNT:-0}" \
        --label highgravity.accel.openvino_version="${KHOJ_OPENVINO_VERSION:-}" \
        --label highgravity.accel.openvino_device="${OPENVINO_DEVICE:-}" \
        --label highgravity.accel.openvino_source="${KHOJ_OPENVINO_SOURCE:-}" \
        "${DOCKER_ACCEL_ENVS[@]}" \
        -e POSTGRES_HOST=khoj-pg \
        -e POSTGRES_PORT=5432 \
        -e POSTGRES_USER=khoj \
        -e POSTGRES_PASSWORD=khoj \
        -e POSTGRES_DB=khoj \
        -e KHOJ_TELEMETRY_DISABLE=true \
        -e KHOJ_DOMAIN="${LAN_IP:-127.0.0.1}" \
        -e KHOJ_ADMIN_EMAIL=admin@local \
        -e KHOJ_ADMIN_PASSWORD=admin123 \
        -e HF_HOME=/root/.cache/huggingface \
        -v "$(pwd):/workspace:ro" \
        -v "$KHOJ_CACHE_DIR:/root/.cache" \
        -v "$KHOJ_APPDATA_DIR:/root/.khoj" \
        ghcr.io/khoj-ai/khoj:latest \
        -lc "$KHOJ_BOOTSTRAP"
fi

# Wait for health
echo "[*] Waiting for Khoj to be ready..."
for i in {1..180}; do
    if curl -fsS --max-time 3 http://127.0.0.1:42110/api/health >/dev/null 2>&1; then
        probe_container_acceleration
        echo "[+] Khoj is ready!"
        exit 0
    fi
    sleep 2
done

echo "[-] Khoj failed to start. Check: docker logs khoj"
exit 1
