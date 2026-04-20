#!/usr/bin/env python3
"""
Cascade Traffic Sniffer — transparent HTTPS pass-through logger.

Redirects Windsurf domains to 127.0.0.1 via /etc/hosts, terminates TLS
locally, logs full request + response, forwards to real upstream.

Run with sudo (needs port 443):
    echo 1786 | sudo -S -E python3 tools/sniff_cascade.py

Logs to: logs/cascade_sniff.jsonl  (machine-readable)
         logs/cascade_sniff.log    (human-readable)
"""
import asyncio
import gzip
import hashlib
import json
import os
import signal
import ssl
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

CERT = REPO_ROOT / "certs" / "proxy.crt"
KEY  = REPO_ROOT / "certs" / "proxy.key"

# Real upstream IPs (bypass /etc/hosts by connecting directly)
UPSTREAM_MAP = {
    "server.self-serve.windsurf.com": "34.49.14.144",
    "server.codeium.com":            "34.49.14.144",
    "inference.codeium.com":         "192.34.20.166",
    "eu.windsurf.com":               "34.49.14.144",
    "register.windsurf.com":         "34.49.14.144",
    "unleash.codeium.com":           "34.49.14.144",
    "shield.windsurf.com":           "34.49.14.144",
}

# Domains to hijack
SNIFF_DOMAINS = list(UPSTREAM_MAP.keys())

HOSTS_MARKER = "# HG-SNIFF"

# ─── logging ─────────────────────────────────────────────────────────
jsonl_file = open(LOG_DIR / "cascade_sniff.jsonl", "a")
human_file = open(LOG_DIR / "cascade_sniff.log", "a")

seq = 0

def log_exchange(method, host, path, req_headers, req_body, status, resp_headers, resp_body, elapsed_ms):
    global seq
    seq += 1
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    # Truncate large bodies for human log
    req_preview = (req_body[:2000] + "...") if len(req_body) > 2000 else req_body
    resp_preview = (resp_body[:2000] + "...") if len(resp_body) > 2000 else resp_body

    # Human-readable
    human_file.write(f"\n{'='*80}\n")
    human_file.write(f"[{seq:04d}] {ts}  {method} https://{host}/{path}  → {status}  ({elapsed_ms:.0f}ms)\n")
    human_file.write(f"{'─'*80}\n")
    human_file.write(f"REQ HEADERS:\n")
    for k, v in req_headers.items():
        if k.lower() in ("authorization", "x-api-key"):
            v = v[:20] + "..."
        human_file.write(f"  {k}: {v}\n")
    if req_body:
        human_file.write(f"\nREQ BODY ({len(req_body)} bytes):\n{req_preview}\n")
    human_file.write(f"{'─'*80}\n")
    human_file.write(f"RESP HEADERS:\n")
    for k, v in resp_headers.items():
        human_file.write(f"  {k}: {v}\n")
    if resp_body:
        human_file.write(f"\nRESP BODY ({len(resp_body)} bytes):\n{resp_preview}\n")
    human_file.flush()

    # JSONL for machine processing
    entry = {
        "seq": seq,
        "ts": time.time(),
        "method": method,
        "host": host,
        "path": path,
        "req_headers": dict(req_headers),
        "req_body_len": len(req_body),
        "req_body_hash": hashlib.sha256(req_body.encode()).hexdigest()[:16],
        "status": status,
        "resp_body_len": len(resp_body),
        "elapsed_ms": round(elapsed_ms, 1),
    }
    # Store small bodies inline
    if len(req_body) < 10000:
        entry["req_body"] = req_body
    if len(resp_body) < 10000:
        entry["resp_body"] = resp_body
    jsonl_file.write(json.dumps(entry) + "\n")
    jsonl_file.flush()

    # Console
    color = "\033[32m" if status < 400 else "\033[33m" if status < 500 else "\033[31m"
    nc = "\033[0m"
    content_hint = ""
    try:
        j = json.loads(req_body)
        if "messages" in j:
            content_hint = f" msgs={len(j['messages'])}"
        if "model" in j:
            content_hint += f" model={j['model']}"
    except:
        pass
    print(f"  {color}[{seq:04d}]{nc} {method:6s} {host}/{path[:50]}  → {status} {elapsed_ms:.0f}ms  body={len(resp_body)}{content_hint}")


# ─── /etc/hosts management ───────────────────────────────────────────
def install_hosts():
    hosts_path = Path("/etc/hosts")
    content = hosts_path.read_text()
    lines = [l for l in content.splitlines() if HOSTS_MARKER not in l]
    for domain in SNIFF_DOMAINS:
        lines.append(f"127.0.0.1 {domain} {HOSTS_MARKER}")
    hosts_path.write_text("\n".join(lines) + "\n")
    print(f"  [+] Redirected {len(SNIFF_DOMAINS)} domains to 127.0.0.1")

def remove_hosts():
    hosts_path = Path("/etc/hosts")
    content = hosts_path.read_text()
    lines = [l for l in content.splitlines() if HOSTS_MARKER not in l]
    hosts_path.write_text("\n".join(lines) + "\n")
    print(f"  [+] Removed {len(SNIFF_DOMAINS)} domain redirects")


# ─── HTTPX client that bypasses /etc/hosts ───────────────────────────
class DirectTransport(httpx.AsyncHTTPTransport):
    """Connects to real IP, sends correct SNI/Host header."""
    async def handle_async_request(self, request):
        host = request.url.host
        real_ip = UPSTREAM_MAP.get(host, host)
        # Rewrite URL to IP but keep Host header
        url = request.url.copy_with(host=real_ip)
        request = httpx.Request(
            method=request.method,
            url=url,
            headers=request.headers,
            content=request.content,
            extensions=request.extensions,
        )
        return await super().handle_async_request(request)

client = httpx.AsyncClient(
    transport=DirectTransport(verify=False),
    timeout=60.0,
    follow_redirects=True,
)

# ─── FastAPI sniffer ─────────────────────────────────────────────────
app = FastAPI()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def sniff(request: Request, path: str):
    host = request.headers.get("host", "unknown")
    method = request.method
    body_bytes = await request.body()

    # Decompress if gzipped
    req_body_str = ""
    try:
        if request.headers.get("content-encoding") == "gzip":
            body_bytes = gzip.decompress(body_bytes)
        req_body_str = body_bytes.decode("utf-8", errors="replace")
    except:
        req_body_str = f"<binary {len(body_bytes)} bytes>"

    # Build upstream URL
    upstream_url = f"https://{host}/{path}"
    if request.url.query:
        upstream_url += f"?{request.url.query}"

    # Forward headers (strip hop-by-hop)
    fwd_headers = {}
    for k, v in request.headers.items():
        if k.lower() not in ("host", "connection", "transfer-encoding", "content-length"):
            fwd_headers[k] = v

    t0 = time.time()
    try:
        resp = await client.request(
            method=method,
            url=upstream_url,
            headers=fwd_headers,
            content=body_bytes,
        )
        elapsed = (time.time() - t0) * 1000

        resp_body_bytes = resp.content
        try:
            if resp.headers.get("content-encoding") == "gzip":
                resp_body_bytes = gzip.decompress(resp_body_bytes)
            resp_body_str = resp_body_bytes.decode("utf-8", errors="replace")
        except:
            resp_body_str = f"<binary {len(resp_body_bytes)} bytes>"

        log_exchange(
            method, host, path,
            dict(request.headers), req_body_str,
            resp.status_code, dict(resp.headers), resp_body_str,
            elapsed,
        )

        # Return to Windsurf
        excluded = {"transfer-encoding", "content-encoding", "content-length"}
        resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}
        return Response(
            content=resp_body_bytes,
            status_code=resp.status_code,
            headers=resp_headers,
        )

    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        print(f"  \033[31m[ERR]\033[0m {method} {host}/{path}: {e}")
        log_exchange(
            method, host, path,
            dict(request.headers), req_body_str,
            502, {}, str(e),
            elapsed,
        )
        return Response(content=str(e).encode(), status_code=502)


# ─── main ────────────────────────────────────────────────────────────
def cleanup(sig=None, frame=None):
    print("\n  [*] Cleaning up /etc/hosts...")
    remove_hosts()
    jsonl_file.close()
    human_file.close()
    print("  [*] Done. Logs in logs/cascade_sniff.*")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("ERROR: Must run as root (needs port 443)")
        print("  echo 1786 | sudo -S -E python3 tools/sniff_cascade.py")
        sys.exit(1)

    if not CERT.exists() or not KEY.exists():
        print(f"ERROR: Certs not found at {CERT}")
        sys.exit(1)

    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │    CASCADE TRAFFIC SNIFFER                   │")
    print("  │    Transparent HTTPS pass-through logger     │")
    print("  └─────────────────────────────────────────────┘")
    print()
    print("  [*] Installing /etc/hosts redirects...")
    install_hosts()
    print(f"  [*] Logging to: logs/cascade_sniff.log")
    print(f"  [*] JSONL to:   logs/cascade_sniff.jsonl")
    print(f"  [*] Listening on 0.0.0.0:443 (TLS)")
    print(f"  [*] Press Ctrl+C to stop and restore /etc/hosts")
    print()
    print("  Waiting for Windsurf traffic...")
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=443,
        ssl_certfile=str(CERT),
        ssl_keyfile=str(KEY),
        log_level="warning",
    )
