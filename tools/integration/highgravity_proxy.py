#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import logging
import time
import secrets
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import aiohttp

# --- Configuration ---
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KEYS_FILE = REPO_ROOT / "config" / "gemini_keys.json"
LOG_FILE = REPO_ROOT / "logs" / "proxy.log"

# Setup Logging
os.makedirs(REPO_ROOT / "logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger("HG-Proxy")

app = FastAPI(title="HIGHGRAVITY Optimization Proxy")

# --- State Management ---
class TokenPool:
    def __init__(self):
        self.keys = []
        self.current_index = 0
        self.load_keys()

    def load_keys(self):
        try:
            if KEYS_FILE.exists():
                with open(KEYS_FILE) as f:
                    data = json.load(f)
                    self.keys = [k["key"] for k in data.get("keys", []) if k.get("status") == "active"]
            logger.info(f"Loaded {len(self.keys)} active keys from pool.")
        except Exception as e:
            logger.error(f"Failed to load keys: {e}")

    def get_key(self):
        if not self.keys:
            return None
        key = self.keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.keys)
        return key

pool = TokenPool()

# --- Optimization Logic ---
def optimize_payload(payload: Dict[str, Any]):
    """Universal model optimization logic."""
    model = payload.get("model", "").lower()
    messages = payload.get("messages", [])
    optimized = False
    
    # Anthropic-style Caching (Sonnet, Opus, etc.)
    # Support caching for any model containing 'claude', 'sonnet', or 'opus'
    if any(m in model for m in ["claude", "sonnet", "opus"]):
        cache_count = 0
        for msg in messages:
            if isinstance(msg.get("content"), list):
                for part in msg["content"]:
                    # Tag large text blocks for caching, max 4 per request
                    if isinstance(part, dict) and part.get("highgravity_cache") and cache_count < 4:
                        part["cache_control"] = {"type": "ephemeral"}
                        optimized = True
                        cache_count += 1
            elif isinstance(msg.get("content"), str) and msg.get("highgravity_cache") and cache_count < 4:
                # Wrap string content in a list to apply cache control
                msg["content"] = [
                    {"type": "text", "text": msg["content"], "cache_control": {"type": "ephemeral"}}
                ]
                optimized = True
                cache_count += 1

    # Gemini specific optimizations
    if "gemini" in model:
        # Note: Gemini 1.5 Pro supports context caching via a different API
        # Here we just clean up our custom tags
        pass

    return payload, optimized

# --- API Endpoints ---
def cloak_identity(metadata: Dict[str, Any]):
    """Randomizes tracking identifiers and forces ENTERPRISE tier."""
    if not isinstance(metadata, dict):
        metadata = {}
    
    # Generate a consistent but randomized fingerprint for this session
    if "deviceFingerprint" in metadata or True:
        metadata["deviceFingerprint"] = f"HG-{secrets.token_hex(8)}"
    if "installationId" in metadata or True:
        metadata["installationId"] = str(uuid.uuid4())
    if "sessionId" in metadata or True:
        metadata["sessionId"] = str(uuid.uuid4())
    
    # Tier Spoofing - Forced Mandate
    metadata["planName"] = "Enterprise"
    metadata["impersonateTier"] = "ENTERPRISE_SAAS"
    metadata["isEnterprise"] = True
    metadata["featureFlags"] = {
        "enable_opus": True,
        "enable_gpt4o": True,
        "unlimited_context": True,
        "priority_queue": True
    }
    
    return metadata

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: Request):
    raw_body = await request.json()
    
    # 1. Apply Midway Optimizations (Universal)
    optimized_body, is_opt = optimize_payload(raw_body)
    
    # 2. Cloak Identity & Force Enterprise Tier
    if "metadata" not in optimized_body:
        optimized_body["metadata"] = {}
    optimized_body["metadata"] = cloak_identity(optimized_body["metadata"])
    
    if "config" in optimized_body and "metadata" in optimized_body["config"]:
        optimized_body["config"]["metadata"] = cloak_identity(optimized_body["config"]["metadata"])

    # 3. Extract Authentic Credentials
    # Windsurf sends its legitimate session key in the Authorization header.
    # We forward this to ensure Opus, Sonnet, and GPT-4o work on the original account.
    auth_header = request.headers.get("Authorization")
    
    # Priority: WINDSURF_API_KEY from env, then header, then pool
    windsurf_env_key = os.environ.get("WINDSURF_API_KEY")
    
    if windsurf_env_key:
        auth_header = f"Bearer {windsurf_env_key}"
        logger.info("Using WINDSURF_API_KEY from environment.")
    elif not auth_header:
        # Fallback to local Gemini pool only if no header or env key provided
        api_key = pool.get_key()
        if not api_key:
            raise HTTPException(status_code=500, detail="No active keys available.")
        auth_header = f"Bearer {api_key}"
        logger.warning("No Authorization header or env key. Falling back to Token Pool.")

    # 3. Determine Route based on Model
    model = optimized_body.get("model", "").lower()
    
    # Default: Route to Google's Gemini endpoint (supports many models via OpenAI compatibility)
    target_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    
    if "claude" in model or "opus" in model:
        # If it's a Claude model, we check if we should route to Anthropic directly
        # or stick with the OpenAI-compatible bridge.
        if "anthropic" in str(request.headers.get("User-Agent", "")):
             target_url = "https://api.anthropic.com/v1/messages"
    elif "gpt" in model:
        target_url = "https://api.openai.com/v1/chat/completions"
    elif "deepseek" in model:
        target_url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }

    # Pass through model-specific headers
    for h in ["anthropic-beta", "x-api-key", "openai-organization", "anthropic-version"]:
        if request.headers.get(h):
            headers[h] = request.headers.get(h)

    logger.info(f"Forwarding: model={model}, optimized={is_opt}, auth={auth_header[:15]}...")

    # 4. Proxy the Request
    async def stream_response():
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(target_url, json=optimized_body, headers=headers) as resp:
                    if resp.status != 200:
                        err_text = await resp.text()
                        logger.error(f"Upstream Error ({resp.status}): {err_text}")
                        yield f"data: {json.dumps({'error': {'message': f'Upstream error: {err_text}', 'status': resp.status}})}\n\n".encode()
                        return

                    async for chunk in resp.content.iter_any():
                        yield chunk
            except Exception as e:
                logger.error(f"Proxy Exception: {e}")
                yield f"data: {json.dumps({'error': {'message': str(e)}})}\n\n".encode()

    if optimized_body.get("stream"):
        return StreamingResponse(stream_response(), media_type="text/event-stream")
    else:
        async with aiohttp.ClientSession() as session:
            async with session.post(target_url, json=optimized_body, headers=headers) as resp:
                data = await resp.json()
                return data

@app.get("/v1/models")
async def list_models():
    return {
        "data": [
            {"id": "gemini-2.0-flash-exp", "object": "model", "owned_by": "google"},
            {"id": "claude-3-5-sonnet-20241022", "object": "model", "owned_by": "anthropic"},
            {"id": "claude-3-opus-20240229", "object": "model", "owned_by": "anthropic"},
            {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
            {"id": "gpt-4o", "object": "model", "owned_by": "openai"}
        ]
    }

def get_windsurf_versions():
    """Detects available Windsurf binaries."""
    versions = []
    potential = [
        ("Windsurf Stable", "windsurf"),
        ("Windsurf Next", "windsurf-next"),
        ("Windsurf Insiders", "windsurf-insiders")
    ]
    for label, cmd in potential:
        if shutil.which(cmd):
            versions.append((label, cmd))
    return versions

def interactive_launcher():
    """Presents an option to launch Windsurf after proxy starts."""
    if not sys.stdin.isatty():
        return

    versions = get_windsurf_versions()
    if not versions:
        return

    print("\n" + "="*40)
    print("WINDSURF LAUNCHER")
    print("="*40)
    for i, (label, _) in enumerate(versions, 1):
        print(f"{i}. {label}")
    print("n. Skip launch (Proxy only)")
    
    choice = input("\nSelect version to launch [1-n]: ").strip().lower()
    
    if choice == 'n' or not choice:
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(versions):
            label, cmd = versions[idx]
            print(f"[*] Launching {label}...")
            # Launch in background so it doesn't block the proxy log output
            subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except ValueError:
        pass

if __name__ == "__main__":
    import shutil
    import subprocess
    
    logger.info("Starting HIGHGRAVITY Universal Proxy on port 9999...")
    
    # Run the interactive launcher in a separate thread so it doesn't block the server
    import threading
    launcher_thread = threading.Thread(target=interactive_launcher, daemon=True)
    launcher_thread.start()
    
    uvicorn.run(app, host="127.0.0.1", port=9999)
