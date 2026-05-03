#!/bin/bash
# HIGH-GRAVITY Khoj Docker Launcher

set -e
cd "$(dirname "$0")/.."

echo "[*] Starting Khoj via Docker..."

# Start postgres if not running
if ! docker ps | grep -q khoj-pg; then
    echo "[*] Starting PostgreSQL with pgvector..."
    docker run -d --name khoj-pg --privileged \
        -e POSTGRES_USER=khoj \
        -e POSTGRES_PASSWORD=khoj \
        -e POSTGRES_DB=khoj \
        pgvector/pgvector:pg15 2>/dev/null || docker start khoj-pg
    sleep 10
fi

# Start khoj if not running
if ! docker ps | grep -q "khoj$"; then
    echo "[*] Starting Khoj..."
    docker rm khoj 2>/dev/null || true
    docker run -d --name khoj --privileged \
        --link khoj-pg:postgres \
        -p 42110:42110 \
        -e POSTGRES_HOST=postgres \
        -e POSTGRES_PORT=5432 \
        -e POSTGRES_USER=khoj \
        -e POSTGRES_PASSWORD=khoj \
        -e POSTGRES_DB=khoj \
        -e KHOJ_ADMIN_EMAIL=admin@local \
        -e KHOJ_ADMIN_PASSWORD=admin123 \
        -e KHOJ_ANONYMOUS_MODE=true \
        -v "$(pwd):/workspace:ro" \
        ghcr.io/khoj-ai/khoj:latest \
        python3 src/khoj/main.py --host 0.0.0.0 --port 42110
fi

# Wait for health
echo "[*] Waiting for Khoj to be ready..."
for i in {1..60}; do
    if curl -s http://127.0.0.1:42110/api/health 2>/dev/null | grep -q OK; then
        echo "[+] Khoj is ready!"
        exit 0
    fi
    sleep 2
done

echo "[-] Khoj failed to start. Check: docker logs khoj"
exit 1
