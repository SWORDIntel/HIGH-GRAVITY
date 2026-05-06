#!/bin/bash
# HIGH-GRAVITY Khoj Docker Launcher

set -e
cd "$(dirname "$0")/.."

echo "[*] Starting Khoj via Docker..."

# Use a dedicated user-defined bridge network (avoid legacy --link behavior)
KHOJ_NET="khoj-net"
docker network inspect "$KHOJ_NET" >/dev/null 2>&1 || docker network create "$KHOJ_NET" >/dev/null
LAN_IP="${HG_KHOJ_DOMAIN:-$(hostname -I 2>/dev/null | awk '{print $1}')}"

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
sleep 10

# Start khoj if not running
if ! docker ps | grep -q "khoj$"; then
    echo "[*] Starting Khoj..."
    docker rm -f khoj >/dev/null 2>&1 || true
    docker run -d --name khoj \
        --privileged \
        --network "$KHOJ_NET" \
        --dns 8.8.8.8 --dns 1.1.1.1 \
        -p 42110:42110 \
        -e POSTGRES_HOST=khoj-pg \
        -e POSTGRES_PORT=5432 \
        -e POSTGRES_USER=khoj \
        -e POSTGRES_PASSWORD=khoj \
        -e POSTGRES_DB=khoj \
        -e KHOJ_DOMAIN="${LAN_IP:-127.0.0.1}" \
        -e KHOJ_ADMIN_EMAIL=admin@local \
        -e KHOJ_ADMIN_PASSWORD=admin123 \
        -e HF_HOME=/root/.cache/huggingface \
        -v "$(pwd):/workspace:ro" \
        -v "$KHOJ_CACHE_DIR:/root/.cache" \
        -v "$KHOJ_APPDATA_DIR:/root/.khoj" \
        ghcr.io/khoj-ai/khoj:latest \
        python3 src/khoj/main.py --host 0.0.0.0 --port 42110 --anonymous-mode
fi

# Wait for health
echo "[*] Waiting for Khoj to be ready..."
for i in {1..60}; do
    if curl -fsS --max-time 3 http://127.0.0.1:42110/api/health >/dev/null 2>&1; then
        echo "[+] Khoj is ready!"
        exit 0
    fi
    sleep 2
done

echo "[-] Khoj failed to start. Check: docker logs khoj"
exit 1
