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
log_format = '%(asctime)s [%(levelname)s] %(message)s'

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format=log_format,
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HG-Proxy")

for handler in logging.root.handlers:
    handler.setFormatter(logging.Formatter(log_format))

app = FastAPI(title="HIGHGRAVITY Optimization Proxy")

# --- Ghost Cache System ---
class GhostCache:
    def __init__(self):
        self.db_path = REPO_ROOT / "kp14_cache" / "ghost_cache.db"
        os.makedirs(self.db_path.parent, exist_ok=True)
        self.tokens_saved = 0
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        hash TEXT PRIMARY KEY, response BLOB, timestamp REAL, model TEXT
                    )
                """)
                conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON cache(timestamp)")
                row = conn.execute("SELECT value FROM metadata WHERE key = 'tokens_saved'").fetchone()
                if row: self.tokens_saved = int(row[0])
        except: pass

    def _persist_metrics(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('tokens_saved', ?)", (str(self.tokens_saved),))
        except: pass

    def get(self, messages: List[Dict]) -> Optional[bytes]:
        try:
            msg_hash = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("SELECT response FROM cache WHERE hash = ? AND timestamp > ?", 
                                 (msg_hash, time.time() - 3600)).fetchone()
                if row:
                    resp_len = len(row[0])
                    req_len = len(json.dumps(messages))
                    self.tokens_saved += (resp_len + req_len) // 4
                    self._persist_metrics()
                    return row[0]
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

# --- Feature 2 & 5: Compression and Local RAG ---
_rag_injection_counter = 0
def compress_context(text: str) -> str:
    if not isinstance(text, str): return text
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +\n', '\n', text)
    return text

def inject_local_rules(messages: List[Dict]):
    global _rag_injection_counter
    _rag_injection_counter += 1
    if _rag_injection_counter % 4 != 0: return
    rules_path = Path(".highgravity_rules")
    if not rules_path.exists(): return
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = f.read().strip()
        if not rules: return
        reminder = f"\n\n# OCCASIONAL REMINDER - LOCAL PROJECT RULES:\n{rules}"
        for msg in messages:
            if msg.get("role") == "system":
                msg["content"] = msg.get("content", "") + reminder
                return
        messages.insert(0, {"role": "system", "content": reminder.strip()})
    except: pass

# --- Key Extraction ---
def get_realtime_windsurf_key():
    try:
        import subprocess
        ps = subprocess.check_output(["ps", "aux"], text=True)
        active_flavor = "Windsurf - Next" if "windsurf-next" in ps else "Windsurf" if "windsurf" in ps else None
        possible_paths = [Path.home() / ".config" / p / "User" / "globalStorage" / "state.vscdb" for p in ["Windsurf - Next", "Windsurf", "Windsurf - Insiders"]]
        for db_path in possible_paths:
            if not db_path.exists(): continue
            with tempfile.NamedTemporaryFile(suffix=".vscdb", delete=False) as tmp_file:
                shutil.copy2(db_path, tmp_file.name)
                conn = sqlite3.connect(tmp_file.name)
                cursor = conn.cursor()
                found_key = None
                for k in ['windsurfAuthStatus', 'codeium.windsurf-windsurf_auth', 'windsurf_auth']:
                    cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (k,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        val = row[0] if isinstance(row[0], str) else row[0].decode('utf-8', errors='ignore')
                        m = re.search(r'["\']apiKey["\']\s*:\s*["\'](sk-ws-[a-zA-Z0-9_-]+)["\']', val)
                        if m: found_key = m.group(1); break
                conn.close(); os.unlink(tmp_file.name)
                if found_key: return found_key
    except: pass
    return None

class TokenPool:
    def __init__(self):
        self.keys = []; self.exhausted_keys = {}; self.active_keys = {}; self.shadow_profiles = {}
        self.current_index = 0; self.rotation_mode = os.environ.get("HG_ROTATION_MODE", "round-robin")
        self.load_keys()
        rk = get_realtime_windsurf_key()
        if rk: self.add_key(rk)
        threading.Thread(target=self._validation_loop, daemon=True).start()

    def get_shadow_profile(self, key: str) -> dict:
        if key not in self.shadow_profiles:
            self.shadow_profiles[key] = {"sessionId": str(uuid.uuid4()), "installationId": str(uuid.uuid4()), "machineId": secrets.token_hex(32), "deviceFingerprint": secrets.token_hex(16)}
        return self.shadow_profiles[key]

    def _validation_loop(self):
        while True:
            time.sleep(30); now = time.time()
            tr = [k for k, exp in self.exhausted_keys.items() if now > exp]
            for k in tr: del self.exhausted_keys[k]; logger.info(f"KEY_RECOVERED: KEY={k[:15]}...")

    def load_keys(self):
        try:
            if KEYS_FILE.exists():
                with open(KEYS_FILE) as f:
                    for k in json.load(f).get("keys", []):
                        if k.get("status") == "active": self.add_key(k["key"], persist=False)
            if PERSISTENCE_FILE.exists():
                with open(PERSISTENCE_FILE) as f:
                    for k in json.load(f): self.add_key(k, persist=False)
        except: pass

    def save_keys(self):
        try:
            with open(PERSISTENCE_FILE, "w") as f: json.dump(list(self.keys), f)
        except: pass

    def add_key(self, key: str, persist: bool = True):
        ck = key.replace("Bearer ", "").strip()
        if ck and ck not in self.keys and ck != "sk-ws-test-123":
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
            logger.warning(f"KEY_EXHAUSTED: KEY={ck[:15]}... COOLDOWN={cs}s")

    def get_key(self, is_windsurf: bool = False) -> Optional[str]:
        provider = "windsurf" if is_windsurf else "llm"
        def is_ws(k): return k.startswith("sk-ws-")
        candidates = [k for k in self.keys if k not in self.exhausted_keys and (is_ws(k) == is_windsurf)]
        if not candidates: return None
        self.current_index = (self.current_index + 1) % len(candidates)
        sel = candidates[self.current_index]
        self.active_keys[provider] = sel
        logger.info(f"ROTATION ({provider}): KEY={sel[:15]}... TOTAL_ACTIVE={len(candidates)}")
        return sel

pool = TokenPool()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_request(path: str, request: Request):
    request_id = secrets.token_hex(4)
    logger.info(f"[{request_id}] CONNECTION: {request.method} /{path}")
    body_bytes = await request.body(); is_json = False; raw_body_json = {}
    if "application/json" in request.headers.get("Content-Type", ""):
        try: raw_body_json = json.loads(body_bytes); is_json = True
        except: pass

    if is_json and "messages" in raw_body_json:
        inject_local_rules(raw_body_json["messages"])
        for msg in raw_body_json["messages"]:
            if isinstance(msg.get("content"), str): msg["content"] = compress_context(msg["content"])
        if not raw_body_json.get("stream"):
            cr = ghost_cache.get(raw_body_json["messages"])
            if cr: return StreamingResponse(iter([cr]), media_type="application/json")

    if "unleash" in path.lower():
        if "client/features" in path.lower():
            mock_features = {"version": 1, "features": [{"name": f, "enabled": True, "strategies": [{"name": "default"}]} for f in ["unlimited_context", "enable_cascade_v2", "is_enterprise", "ENTERPRISE_SAAS", "CASCADE_ENABLE_MCP_TOOLS", "enable_mcp", "cascade_web_search_enabled"]]}
            return StreamingResponse(iter([json.dumps(mock_features).encode()]), media_type="application/json")
        return StreamingResponse(iter([b"{}"]), media_type="application/json")

    max_retries = max(3, len(pool.keys))
    for attempt in range(max_retries):
        try:
            is_ws_rpc = "exa." in path
            if is_ws_rpc:
                target_base_url = "https://server.self-serve.windsurf.com"; wk = pool.get_key(is_windsurf=True)
                if not wk: raise HTTPException(503, "No Windsurf keys"); resolved_api_key = f"Bearer {wk}"; tp = path
            else:
                model = str(raw_body_json.get("model", "unknown") if is_json else "unknown")
                pk = pool.get_key(is_windsurf=False)
                if not pk: raise HTTPException(503, "No LLM keys")
                if pk.startswith("AIzaSy"):
                    target_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"; resolved_api_key = f"Bearer {pk}"
                    if any(x in model.lower() for x in ["claude", "gpt"]): raw_body_json["model"] = "gemini-2.0-flash-exp"
                else: target_base_url = "https://api.openai.com"; resolved_api_key = f"Bearer {pk}"
                tp = path if path.startswith("v1/") else f"v1/{path}"
                if "generativelanguage" in target_base_url and tp.startswith("v1/"): tp = tp[3:]

            target_url = f"{target_base_url.rstrip('/')}/{tp.lstrip('/')}"
            fh = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "authorization", "x-api-key", "connection"]}
            active_key_str = resolved_api_key.replace("Bearer ", "").strip()
            if active_key_str != "NONE":
                shadow = pool.get_shadow_profile(active_key_str)
                if is_json:
                    meta = raw_body_json.setdefault("metadata", {})
                    meta.update({"sessionId": shadow["sessionId"], "installationId": shadow["installationId"], "deviceFingerprint": shadow["deviceFingerprint"]})
                fh.update({"x-session-id": shadow["sessionId"], "x-installation-id": shadow["installationId"], "Authorization": resolved_api_key})

            async with aiohttp.ClientSession() as session:
                async with session.request(method=request.method, url=target_url, json=raw_body_json if is_json else None, data=body_bytes if not is_json else None, headers=fh, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                    if resp.status == 429: pool.mark_exhausted(resolved_api_key); await asyncio.sleep(1); continue
                    if resp.status in [401, 403] and not is_ws_rpc: pool.mark_exhausted(resolved_api_key, False); continue
                    
                    if is_ws_rpc and (resp.status != 200 or any(x in path for x in ["Status", "Profile"])):
                        if any(x in path for x in ["Status", "Profile", "Ping"]):
                            rescue = {"status": "ACTIVE", "tier": "ENTERPRISE", "isEnterprise": True, "email": "dev@highgravity.ai"}
                            return StreamingResponse(iter([json.dumps(rescue).encode()]), media_type="application/json")

                    async def stream_generator():
                        full_content = b""
                        try:
                            async for chunk in resp.content.iter_any():
                                if chunk: full_content += chunk; yield chunk
                            if resp.status == 200 and is_json and "messages" in raw_body_json and not raw_body_json.get("stream"): ghost_cache.set(raw_body_json["messages"], full_content, str(raw_body_json.get("model", "unknown")))
                            logger.info(f"PULSE: BYTES={len(full_content)} STATUS={resp.status}")
                        except: pass
                    return StreamingResponse(stream_generator(), status_code=resp.status, media_type=resp.headers.get("Content-Type"))
        except Exception as e:
            if attempt < max_retries - 1: await asyncio.sleep(0.5); continue
            raise HTTPException(500, str(e))
    raise HTTPException(503, "Max retries")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PROXY_PORT, log_level="error")
