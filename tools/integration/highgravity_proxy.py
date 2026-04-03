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
import random
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
                
                # Load persisted tokens
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
                    # Token vault analytics
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
    """Safe semantic compression for token saving without altering logic."""
    if not isinstance(text, str): return text
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +\n', '\n', text)
    return text

def inject_local_rules(messages: List[Dict]):
    """Reads .highgravity_rules from PWD and injects into system prompt occasionally."""
    global _rag_injection_counter
    _rag_injection_counter += 1
    
    # Only inject every 4th request to prevent context bloat
    if _rag_injection_counter % 4 != 0:
        return
        
    rules_path = Path(".highgravity_rules")
    if not rules_path.exists():
        return
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = f.read().strip()
        if not rules: return
        
        reminder_text = f"\n\n# OCCASIONAL REMINDER - LOCAL PROJECT RULES:\n{rules}"
        for msg in messages:
            if msg.get("role") == "system":
                msg["content"] = msg.get("content", "") + reminder_text
                return
        messages.insert(0, {"role": "system", "content": reminder_text.strip()})
    except Exception as e:
        logger.debug(f"Failed to inject local rules: {e}")

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
        self.shadow_profiles = {} # Mapping of key -> identity profile
        self.last_used_time = {} # Track when keys were last used for cooldown
        self.current_index = 0
        self.rotation_mode = os.environ.get("HG_ROTATION_MODE", "round-robin")
        self.load_keys()
        
        rk = get_realtime_windsurf_key()
        if rk: self.add_key(rk)
        threading.Thread(target=self._validation_loop, daemon=True).start()

    def get_shadow_profile(self, key: str) -> dict:
        """Feature 4: Complete Session Spoofing per key."""
        if key not in self.shadow_profiles:
            self.shadow_profiles[key] = {
                "sessionId": str(uuid.uuid4()),
                "installationId": str(uuid.uuid4()),
                "machineId": secrets.token_hex(32),
                "deviceFingerprint": secrets.token_hex(16)
            }
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
        if ck == "sk-ws-test-123": return # Block dummy key
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
        now = time.time()
        
        if self.rotation_mode == "sticky":
            if provider in self.active_keys and self.active_keys[provider] not in self.exhausted_keys:
                k = self.active_keys[provider]
                self.last_used_time[k] = now
                return k

        def is_ws(k): return k.startswith("sk-ws-")
        candidates = [k for k in self.keys if k not in self.exhausted_keys and (is_ws(k) == is_windsurf)]
        if not candidates: return None
        
        # Warm Cooldown: Try to find a key that hasn't been used in the last 1.5 seconds
        available_candidates = [k for k in candidates if now - self.last_used_time.get(k, 0) > 1.5]
        if not available_candidates:
            available_candidates = candidates # Fallback if all keys are warm
            
        self.current_index = (self.current_index + 1) % len(available_candidates)
        sel = available_candidates[self.current_index]
        self.active_keys[provider] = sel
        self.last_used_time[sel] = now
        logger.info(f"ROTATION ({provider}): KEY={sel[:15]}... MODE={self.rotation_mode} TOTAL_ACTIVE={len(available_candidates)}")
        return sel

pool = TokenPool()

@app.post("/hg/config")
async def update_config(request: Request):
    d = await request.json()
    if "rotation_mode" in d: pool.rotation_mode = d["rotation_mode"]
    return {"status": "ok", "mode": pool.rotation_mode}

def wrap_grpc_web(data: Union[dict, bytes], is_json: bool = True) -> bytes:
    """Feature 6: gRPC-web framing for status rescues (JSON or Binary Protobuf)."""
    try:
        payload = json.dumps(data).encode() if is_json else data
        header = b'\x00' + len(payload).to_bytes(4, 'big')
        return header + payload
    except: return b"\x00\x00\x00\x00\x00"

# Best-effort generic empty protobuf responses for binary RPC rescues
BINARY_TEMPLATES = {
    "ping": b"",
    "status": b"",
    "profile": b"",
    "getfeature": b"",
    "model": b""
}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_request(path: str, request: Request):
    request_id = secrets.token_hex(4)
    logger.info(f"[{request_id}] CONNECTION ATTEMPT: {request.method} /{path}")
    
    # Track content type for framing decisions
    content_type = request.headers.get("Content-Type", "")
    is_grpc_web = "grpc-web" in content_type
    is_grpc_web_proto = "grpc-web+proto" in content_type

    body_bytes = await request.body()
    raw_body_json = {}; is_json = False
    if "application/json" in request.headers.get("Content-Type", "") or not request.headers.get("Content-Type"):
        try:
            if body_bytes: raw_body_json = json.loads(body_bytes); is_json = True
        except: pass

    # --- Feature 2 & 5: Local RAG and Context Compression ---
    if is_json and "messages" in raw_body_json:
        inject_local_rules(raw_body_json["messages"])
        for msg in raw_body_json["messages"]:
            if isinstance(msg.get("content"), str):
                msg["content"] = compress_context(msg["content"])

    if is_json and "messages" in raw_body_json and not raw_body_json.get("stream"):
        cr = ghost_cache.get(raw_body_json["messages"])
        if cr:
            logger.info(f"[{request_id}] GHOST_CACHE_HIT: KEY=LOCAL (Saved: {ghost_cache.tokens_saved} tokens)")
            return StreamingResponse(iter([cr]), media_type="application/json")

    is_unleash = "unleash" in path.lower()
    if is_unleash:
        if "client/features" in path.lower():
            all_flags = [
                # --- Feature Enablers (Keep these ALL ON) ---
                "unlimited_context", "priority_queue", "enable_opus", "enable_gpt4o", "enable_cascade_v2",
                "enable_fast_completions", "enable_experimental_models", "enable_mcp", "enable_mcp_tools",
                "CASCADE_ENABLE_MCP_TOOLS", "CASCADE_ENABLE_AUTOMATED_MEMORIES", "CASCADE_ENABLE_CUSTOM_RECIPES",
                "CASCADE_WEB_SEARCH_TOOL_ENABLED", "CASCADE_WINDSURF_BROWSER_TOOLS_ENABLED", "cascade_web_search_enabled",
                "enable_terminal_auto_suggest", "enable_terminal_completion", "enable_ide_terminal_execution",
                "enable_deep_search", "enable_indexed_search", "enable_context_graph", "knowledge_base_enabled",
                "browser_enabled", "allow_browser_experimental_features", "allow_app_deployments",
                "allow_cascade_in_background", "can_allow_cascade_in_background", "allow_auto_run_commands",
                "enable_model_auto_run", "allow_github_auto_reviews", "allow_github_reviews",
                "enable_feedback_loop", "enable_instant_context_agent",
                "enable_fuzzy_sandwich_match", "enable_path_resolution", "cc_enable_arenas", "enable_background_linting",
                "enable_search_in_file_tool", "ENABLE_SUPERCOMPLETE", "ENABLE_SMART_COPY", "ENABLE_SUGGESTED_RESPONSES",
                "ENABLE_QUICK_ACTIONS", "ENABLE_AUTOCOMPLETE_DURING_INTELLISENSE", "enable_sounds_for_special_events",
                "allow_cascade_access_gitignore_files", "allow_view_gitignore", "allow_edit_gitignore",
                
                # --- Future/Experimental Models ---
                "enable_o3_models", "MODEL_O3_PRO_2025_06_10", "MODEL_O3_PRO_2025_06_10_HIGH", "MODEL_O3_PRO_2025_06_10_LOW",
                "enable_gemini_3_0", "MODEL_GOOGLE_GEMINI_3_0_PRO_HIGH", "MODEL_GOOGLE_GEMINI_3_0_PRO_MEDIUM",
                "MODEL_GOOGLE_GEMINI_3_0_PRO_LOW", "MODEL_GOOGLE_GEMINI_3_0_PRO_MINIMAL", "DEEP_WIKI_MODEL_TYPE_PREMIUM",
                "MODEL_TAB_EXPERIMENTAL_1", "MODEL_TAB_EXPERIMENTAL_2", "MODEL_TAB_EXPERIMENTAL_3", "MODEL_TAB_EXPERIMENTAL_4",
                "MODEL_TAB_EXPERIMENTAL_5", "MODEL_TAB_EXPERIMENTAL_6", "MODEL_TAB_EXPERIMENTAL_7", "MODEL_TAB_EXPERIMENTAL_8",
                "MODEL_TAB_EXPERIMENTAL_9", "MODEL_TAB_EXPERIMENTAL_10",
                
                # --- Logical Identity (Consolidated to Enterprise) ---
                "is_enterprise", "ENTERPRISE_SAAS", "PRO_ULTIMATE", "TEAMS_TIER_ENTERPRISE_SAAS",
                "DEVIN_ENTERPRISE", "TEAMS_TIER_DEVIN_ENTERPRISE",
                "allow_premium_command_models", "allow_sticky_premium_models", "allow_codemap_sharing",
                "enable_auto_cascade_seat_provisioning", "attribution_enabled", "audit_logs_enabled",

                # --- Internal Unleash & Experimental Overrides ---
                "force_enable_experiments", "force_enable_experiment_strings", "force_enable_experiments_with_variants",
                "ShouldEnableUnleash", "browser_experimental_features_config", "BROWSER_EXPERIMENTAL_FEATURES_CONFIG_ENABLED"
            ]
            # Flags to explicitly DISABLE to avoid conflicts or telemetry
            disable_flags = ["is_pro", "is_premium", "is_free", "is_trial", "LSP_TELEMETRY_ENABLED"]
            
            features = []
            for f in all_flags:
                features.append({"name": f, "enabled": True, "strategies": [{"name": "default"}]})
            for f in disable_flags:
                features.append({"name": f, "enabled": False, "strategies": [{"name": "default"}]})

            mock_features = {"version": 1, "features": features}
            logger.info(f"[{request_id}] UNLEASH_SHIELD: Served logically consistent ENTERPRISE profile.")
            return StreamingResponse(iter([json.dumps(mock_features).encode()]), media_type="application/json")
        else:
            logger.info(f"[{request_id}] UNLEASH_SHIELD: Absorbed {path}")
            return StreamingResponse(iter([b"{}"]), status_code=200, media_type="application/json")

    is_windsurf_rpc = "exa." in path
    max_retries = max(5, len(pool.keys))
    for attempt in range(max_retries):
        try:
            if is_windsurf_rpc:
                # Primary Windsurf RPC Target
                target_base_url = "https://server.self-serve.windsurf.com"
                wk = pool.get_key(is_windsurf=True)
                if not wk: 
                    wk = get_realtime_windsurf_key()
                    if wk: pool.add_key(wk)
                if not wk: raise HTTPException(status_code=503, detail="No Windsurf keys.")
                resolved_api_key = f"Bearer {wk}"
                tp = path
            else:
                model = str(raw_body_json.get("model", "unknown") if is_json else "unknown")
                pk = pool.get_key(is_windsurf=False)
                if not pk: raise HTTPException(status_code=503, detail="No LLM keys.")
                
                # Smart Routing & Remapping
                if pk.startswith("AIzaSy"): # Google Key
                    target_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
                    resolved_api_key = f"Bearer {pk}"
                    # Remap models to Gemini if using a Google key
                    if any(x in model.lower() for x in ["claude", "gpt", "opus", "sonnet"]):
                        logger.info(f"[{request_id}] MODEL_REMAP: {model} -> gemini-2.0-flash-exp (via Google Key)")
                        if is_json: raw_body_json["model"] = "gemini-2.0-flash-exp"
                elif pk.startswith("sk-ant"): # Anthropic Key
                    target_base_url = "https://api.anthropic.com"
                    resolved_api_key = f"Bearer {pk}"
                elif pk.startswith("sk-ws"): # Windsurf Key used as LLM key
                    target_base_url = "https://server.self-serve.windsurf.com/v1"
                    resolved_api_key = f"Bearer {pk}"
                else: # Default to OpenAI for sk- keys
                    target_base_url = "https://api.openai.com"
                    resolved_api_key = f"Bearer {pk}"
                
                tp = path if path.startswith("v1/") else f"v1/{path}"
                if "generativelanguage.googleapis.com" in target_base_url and tp.startswith("v1/"): tp = tp[3:]

            target_url = f"{target_base_url.rstrip('/')}/{tp.lstrip('/')}"
            # Keep Content-Length for binary/RPC integrity
            fh = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "authorization", "x-api-key", "connection"]}
            
            # --- Feature 4: Apply Shadow Profile ---
            active_key_str = resolved_api_key.replace("Bearer ", "").strip()
            if active_key_str != "NONE":
                shadow = pool.get_shadow_profile(active_key_str)
                if is_json:
                    if "metadata" not in raw_body_json or not isinstance(raw_body_json["metadata"], dict):
                        raw_body_json["metadata"] = {}
                    raw_body_json["metadata"]["sessionId"] = shadow["sessionId"]
                    raw_body_json["metadata"]["installationId"] = shadow["installationId"]
                    raw_body_json["metadata"]["deviceFingerprint"] = shadow["deviceFingerprint"]
                
                # Spoof Headers
                for k in list(fh.keys()):
                    lower_k = k.lower()
                    if lower_k == "x-session-id": fh[k] = shadow["sessionId"]
                    if lower_k == "x-installation-id": fh[k] = shadow["installationId"]
            
            # Unleash cache bypass
            if is_unleash:
                fh = {k: v for k, v in fh.items() if k.lower() not in ["if-none-match", "if-modified-since"]}

            if "anthropic.com" in target_url:
                fh["x-api-key"] = resolved_api_key.replace("Bearer ", "")
                fh["anthropic-version"] = "2023-06-01"
            else: fh["Authorization"] = resolved_api_key

            # Behavioral Jitter: Randomize headers and add a micro-delay
            header_items = list(fh.items())
            random.shuffle(header_items)
            fh = dict(header_items)
            await asyncio.sleep(random.uniform(0.05, 0.2))

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=request.method, url=target_url,
                    json=raw_body_json if is_json else None,
                    data=body_bytes if not is_json else None,
                    headers=fh, params=request.query_params,
                    timeout=aiohttp.ClientTimeout(total=300) # Increased timeout for streaming
                ) as resp:
                    if resp.status == 429:
                        pool.mark_exhausted(resolved_api_key, is_rate_limit=True)
                        if attempt < max_retries - 1: await asyncio.sleep(1); continue
                        raise HTTPException(status_code=503, detail="Rate-limited.")
                    
                    if resp.status in [401, 403]:
                        err_body = await resp.text()
                        logger.error(f"[{request_id}] AUTH_FAIL: STATUS={resp.status} BODY={err_body[:200]}")
                        pool.mark_exhausted(resolved_api_key, is_rate_limit=False)
                        if attempt < max_retries - 1: continue
                        raise HTTPException(status_code=resp.status, detail=f"Auth failed: {err_body[:100]}")

                    # Feature 6: Aggressive Status & Auth Rescue
                    lc_path = path.lower()
                    status_rpc_keywords = ["status", "profile", "ping", "jwt", "metadata", "getfeature"]
                    is_status_rpc = any(k in lc_path for k in status_rpc_keywords)
                    
                    if is_status_rpc:
                        try:
                            content = await resp.read()
                        except:
                            content = b""
                            
                        if resp.status != 200 or len(content) < 2:
                            logger.warning(f"[{request_id}] RESCUE_MOCK: Serving Elite failover for {path}")
                            if "jwt" in lc_path:
                                rescue_data = {"jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.fake_jwt"}
                            elif "profile" in lc_path:
                                rescue_data = {
                                    "email": "dev@highgravity.ai",
                                    "name": "High-Gravity Elite",
                                    "isEnterprise": True
                                }
                            elif "status" in lc_path:
                                if "model" in lc_path:
                                    rescue_data = {
                                        "modelStatuses": [
                                            {"modelId": "claude-3-5-sonnet", "status": "HEALTHY"},
                                            {"modelId": "claude-3-opus", "status": "HEALTHY"},
                                            {"modelId": "gpt-4o", "status": "HEALTHY"},
                                            {"modelId": "gemini-2.0-flash-exp", "status": "HEALTHY"}
                                        ]
                                    }
                                else:
                                    rescue_data = {
                                        "status": "ACTIVE",
                                        "seatStatus": "ASSIGNED",
                                        "tier": "ENTERPRISE",
                                        "isEnterprise": True
                                    }
                            else: # Ping, etc.
                                rescue_data = {}
                            
                            if is_grpc_web_proto:
                                # Client requires strictly binary protobuf
                                res_bytes = wrap_grpc_web(b"", is_json=False)
                            else:
                                # Client can handle JSON
                                res_bytes = wrap_grpc_web(rescue_data, is_json=True) if is_grpc_web else json.dumps(rescue_data).encode()
                                
                            return StreamingResponse(iter([res_bytes]), media_type=content_type if is_grpc_web else "application/json")
                        
                        return StreamingResponse(iter([content]), status_code=resp.status, media_type=resp.headers.get("Content-Type"))

                    # Streaming implementation
                    async def stream_generator():
                        full_content = b""
                        try:
                            async for chunk in resp.content.iter_any():
                                if chunk:
                                    full_content += chunk
                                    yield chunk
                            
                            # Cache the full response if appropriate
                            if resp.status == 200 and is_json and "messages" in raw_body_json and not raw_body_json.get("stream"):
                                ghost_cache.set(raw_body_json["messages"], full_content, str(raw_body_json.get("model", "unknown")))
                            
                            logger.info(f"PULSE_METRIC: BYTES={len(full_content)} STATUS={resp.status} KEY={resolved_api_key[:15]}...")
                        except Exception as e:
                            logger.error(f"[{request_id}] STREAM_ERROR: {e}")

                    return StreamingResponse(stream_generator(), status_code=resp.status, media_type=resp.headers.get("Content-Type"))
        except HTTPException: raise
        except Exception as e:
            if attempt < max_retries - 1: await asyncio.sleep(0.5); continue
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=503, detail="Max retries.")

if __name__ == "__main__":
    logger.info("HG_PROXY_ONLINE: High-Gravity Gateway is listening.")
    uvicorn.run(app, host="127.0.0.1", port=PROXY_PORT, log_level="error")
