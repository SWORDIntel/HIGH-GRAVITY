#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import logging
import time
import secrets
import uuid
import re
import sqlite3
import shutil
import tempfile
import threading
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import aiohttp

# --- Configuration ---
PROXY_PORT = int(os.environ.get("HG_PROXY_PORT", 9999))
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KEYS_FILE = REPO_ROOT / "config" / "gemini_keys.json"
PERSISTENCE_FILE = REPO_ROOT / "config" / "windsurf_session_keys.json"
LOG_FILE = REPO_ROOT / "logs" / "proxy.log"

# Setup Logging
os.makedirs(REPO_ROOT / "logs", exist_ok=True)
os.makedirs(REPO_ROOT / "config", exist_ok=True)
log_level = os.environ.get("HG_LOG_LEVEL", "INFO").upper()

# Custom formatter to ensure it's easy to parse
log_format = '%(asctime)s [%(levelname)s] %(message)s'

# Configure root logger
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format=log_format,
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HG-Proxy")

# Force flush on all handlers
for handler in logging.root.handlers:
    handler.setFormatter(logging.Formatter(log_format))

app = FastAPI(title="HIGHGRAVITY Optimization Proxy")

# --- Ghost Cache System ---
class GhostCache:
    def __init__(self):
        self.db_path = REPO_ROOT / "kp14_cache" / "ghost_cache.db"
        os.makedirs(self.db_path.parent, exist_ok=True)
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        hash TEXT PRIMARY KEY, response BLOB, timestamp REAL, model TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON cache(timestamp)")
        except: pass

    def get(self, messages: List[Dict]) -> Optional[bytes]:
        try:
            msg_hash = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("SELECT response FROM cache WHERE hash = ? AND timestamp > ?", 
                                 (msg_hash, time.time() - 3600)).fetchone()
                if row: return row[0]
        except: pass
        return None

    def set(self, messages: List[Dict], response: bytes, model: str):
        try:
            msg_hash = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT OR REPLACE INTO cache (hash, response, timestamp, model) VALUES (?, ?, ?, ?)",
                            (msg_hash, response, time.time(), model))
        except: pass

ghost_cache = GhostCache()

# --- Key Extraction ---
def get_realtime_windsurf_key():
    active_flavor = None
    try:
        import subprocess
        ps = subprocess.check_output(["ps", "aux"], text=True)
        if "windsurf-next" in ps: active_flavor = "Windsurf - Next"
        elif "windsurf-insiders" in ps: active_flavor = "Windsurf - Insiders"
        elif "windsurf" in ps: active_flavor = "Windsurf"
    except: pass

    possible_paths = [
        Path.home() / ".config" / "Windsurf - Next" / "User" / "globalStorage" / "state.vscdb",
        Path.home() / ".config" / "Windsurf" / "User" / "globalStorage" / "state.vscdb",
        Path.home() / ".config" / "Windsurf - Insiders" / "User" / "globalStorage" / "state.vscdb"
    ]
    if active_flavor:
        ap = Path.home() / ".config" / active_flavor / "User" / "globalStorage" / "state.vscdb"
        if ap in possible_paths: possible_paths.remove(ap); possible_paths.insert(0, ap)

    for db_path in possible_paths:
        if not db_path.exists(): continue
        try:
            with tempfile.NamedTemporaryFile(suffix=".vscdb", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                tmp_file.close()
                shutil.copy2(db_path, tmp_path)
                conn = sqlite3.connect(tmp_path)
                cursor = conn.cursor()
                found_key = None
                for k in ['windsurfAuthStatus', 'codeium.windsurf-windsurf_auth', 'windsurf_auth']:
                    cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (k,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        val = row[0] if isinstance(row[0], str) else row[0].decode('utf-8', errors='ignore')
                        m = re.search(r'["\']apiKey["\']\s*:\s*["\'](sk-ws-[a-zA-Z0-9_-]+)["\']', val)
                        if m: found_key = m.group(1); break
                conn.close(); os.unlink(tmp_path)
                if found_key: return found_key
        except: pass
    return None

# --- State Management ---
class TokenPool:
    def __init__(self):
        self.keys = []
        self.exhausted_keys = {} 
        self.active_keys = {} 
        self.current_index = 0
        self.rotation_mode = os.environ.get("HG_ROTATION_MODE", "round-robin")
        self.load_keys()
        
        rk = get_realtime_windsurf_key()
        if rk: self.add_key(rk)
        threading.Thread(target=self._validation_loop, daemon=True).start()

    def _validation_loop(self):
        while True:
            time.sleep(30); now = time.time()
            tr = [k for k, exp in self.exhausted_keys.items() if now > exp]
            for k in tr: 
                del self.exhausted_keys[k]
                logger.info(f"KEY_RECOVERED: KEY={k[:15]}...")

    def load_keys(self):
        try:
            if KEYS_FILE.exists():
                with open(KEYS_FILE) as f:
                    d = json.load(f)
                    for k in d.get("keys", []):
                        if k.get("status") == "active": self.add_key(k["key"], persist=False)
        except: pass
        try:
            if PERSISTENCE_FILE.exists():
                with open(PERSISTENCE_FILE) as f:
                    sk = json.load(f)
                    for k in sk: self.add_key(k, persist=False)
        except: pass

    def save_keys(self):
        try:
            with open(PERSISTENCE_FILE, "w") as f: json.dump(list(self.keys), f)
        except: pass

    def add_key(self, key: str, persist: bool = True):
        ck = key.replace("Bearer ", "").strip()
        if ck and ck not in self.keys:
            self.keys.append(ck)
            if persist: self.save_keys()
            logger.info(f"NEW_SESSION_KEY_DISCOVERED: KEY={ck[:15]}...")

    def mark_exhausted(self, key: str, is_rate_limit: bool = True):
        ck = key.replace("Bearer ", "").strip()
        if ck in self.keys:
            cs = 60 if is_rate_limit else 3600
            self.exhausted_keys[ck] = time.time() + cs
            for p, k in list(self.active_keys.items()):
                if k == ck: del self.active_keys[p]
            reason = "Rate Limit" if is_rate_limit else "Auth Failure"
            logger.warning(f"KEY_EXHAUSTED: KEY={ck[:15]}... REASON={reason} COOLDOWN={cs}s")

    def get_key(self, is_windsurf: bool = False) -> Optional[str]:
        provider = "windsurf" if is_windsurf else "llm"
        if self.rotation_mode == "sticky":
            if provider in self.active_keys and self.active_keys[provider] not in self.exhausted_keys:
                return self.active_keys[provider]

        def is_ws(k): return k.startswith("sk-ws-")
        candidates = [k for k in self.keys if k not in self.exhausted_keys and (is_ws(k) == is_windsurf)]
        if not candidates: return None
        
        self.current_index = (self.current_index + 1) % len(candidates)
        sel = candidates[self.current_index]
        self.active_keys[provider] = sel
        logger.info(f"ROTATION ({provider}): KEY={sel[:15]}... MODE={self.rotation_mode} TOTAL_ACTIVE={len(candidates)}")
        return sel

pool = TokenPool()

@app.post("/hg/config")
async def update_config(request: Request):
    d = await request.json()
    if "rotation_mode" in d: pool.rotation_mode = d["rotation_mode"]
    return {"status": "ok", "mode": pool.rotation_mode}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_request(path: str, request: Request):
    request_id = secrets.token_hex(4)
    logger.info(f"[{request_id}] CONNECTION ATTEMPT: {request.method} /{path}")
    body_bytes = await request.body()
    raw_body_json = {}; is_json = False
    if "application/json" in request.headers.get("Content-Type", "") or not request.headers.get("Content-Type"):
        try:
            if body_bytes: raw_body_json = json.loads(body_bytes); is_json = True
        except: pass

    if is_json and "messages" in raw_body_json and not raw_body_json.get("stream"):
        cr = ghost_cache.get(raw_body_json["messages"])
        if cr:
            logger.info(f"[{request_id}] GHOST_CACHE_HIT: KEY=LOCAL")
            return StreamingResponse(iter([cr]), media_type="application/json")

    is_windsurf_rpc = "exa.api_server_pb" in path
    max_retries = max(5, len(pool.keys))
    for attempt in range(max_retries):
        try:
            if is_windsurf_rpc:
                target_base_url = "https://server.self-serve.windsurf.com"
                wk = pool.get_key(is_windsurf=True)
                if not wk: 
                    wk = get_realtime_windsurf_key()
                    if wk: pool.add_key(wk)
                if not wk: raise HTTPException(status_code=503, detail="No Windsurf keys.")
                resolved_api_key = f"Bearer {wk}"
            else:
                model = raw_body_json.get("model", "unknown") if is_json else "unknown"
                if "gpt" in str(model): target_base_url = "https://api.openai.com"
                elif any(k in str(model) for k in ["claude", "sonnet", "opus"]): target_base_url = "https://api.anthropic.com"
                else: target_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
                resolved_api_key = os.environ.get("GOOGLE_API_KEY") 
                if not resolved_api_key:
                    pk = pool.get_key(is_windsurf=False)
                    if not pk: raise HTTPException(status_code=503, detail="No LLM keys.")
                    resolved_api_key = f"Bearer {pk}"

            tp = path if is_windsurf_rpc else (path if path.startswith("v1/") else f"v1/{path}")
            if not is_windsurf_rpc and "generativelanguage.googleapis.com" in target_base_url and tp.startswith("v1/"): tp = tp[3:]
            target_url = f"{target_base_url.rstrip('/')}/{tp.lstrip('/')}"
            fh = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "authorization", "x-api-key", "content-length"]}
            if "anthropic.com" in target_url:
                fh["x-api-key"] = resolved_api_key.replace("Bearer ", "")
                fh["anthropic-version"] = "2023-06-01"
            else: fh["Authorization"] = resolved_api_key

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=request.method, url=target_url,
                    json=raw_body_json if is_json else None,
                    data=body_bytes if not is_json else None,
                    headers=fh, params=request.query_params,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 429:
                        pool.mark_exhausted(resolved_api_key, is_rate_limit=True)
                        if attempt < max_retries - 1: await asyncio.sleep(1); continue
                        raise HTTPException(status_code=503, detail="Rate-limited.")
                    if resp.status in [401, 403]:
                        pool.mark_exhausted(resolved_api_key, is_rate_limit=False)
                        if attempt < max_retries - 1: continue
                        raise HTTPException(status_code=resp.status, detail="Auth failed.")

                    content = await resp.read()
                    if resp.status == 200 and is_json and "messages" in raw_body_json and not raw_body_json.get("stream"):
                        ghost_cache.set(raw_body_json["messages"], content, str(raw_body_json.get("model", "unknown")))
                    
                    logger.info(f"PULSE_METRIC: BYTES={len(content)} STATUS={resp.status} KEY={resolved_api_key[:15]}...")
                    return StreamingResponse(iter([content]), status_code=resp.status, media_type=resp.headers.get("Content-Type"))
        except HTTPException: raise
        except Exception as e:
            if attempt < max_retries - 1: await asyncio.sleep(0.5); continue
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=503, detail="Max retries.")

if __name__ == "__main__":
    logger.info("HG_PROXY_ONLINE: High-Gravity Gateway is listening.")
    uvicorn.run(app, host="127.0.0.1", port=PROXY_PORT, log_level="error")
