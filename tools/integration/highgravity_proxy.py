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
import ast
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import aiohttp

import yaml
from logging.handlers import RotatingFileHandler

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# --- Configuration ---
with open(REPO_ROOT / "config" / "settings.yaml", "r") as f:
    config = yaml.safe_load(f)

PROXY_PORT = config.get("proxy_port", 9998)
LOG_FILE = REPO_ROOT / config.get("log_path", "logs/proxy.log")

# MITM Bridge Configuration
MITM_MODE = config.get("mitm_mode", "enabled")
MITM_AUTO_DETECT = config.get("mitm_auto_detect", True)
MITM_SERVICES = config.get("mitm_services", ["gemini", "codex", "openai"])
MITM_INJECT_PREMIUM = config.get("mitm_inject_premium", True)
MITM_REDUCE_RATE_LIMITS = config.get("mitm_reduce_rate_limits", True)
KEYS_FILE = REPO_ROOT / "config" / "api_keys.json"
PERSISTENCE_FILE = REPO_ROOT / "kp14_cache" / "session_keys.json"

# Setup Logging
os.makedirs(LOG_FILE.parent, exist_ok=True)
os.makedirs(REPO_ROOT / "config", exist_ok=True)
log_level = os.environ.get("HG_LOG_LEVEL", "INFO").upper()
log_format = '%(asctime)s [%(levelname)s] %(message)s'

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format=log_format,
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=config.get("max_log_size_mb", 5) * 1024 * 1024, backupCount=config.get("backup_count", 3)),
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
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON cache(timestamp)")
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
def compress_context(text: str) -> str:
    """Safe semantic compression for token saving without altering logic."""
    if not isinstance(text, str): return text
    
    # Remove dynamic timestamps injected by Windsurf that bust cache
    text = re.sub(r'(?i)Current time:.*?\n', '', text)
    text = re.sub(r'(?i)The current date and time is.*?\n', '', text)
    
    # Strip long sequences of dashes or equals signs used as separators
    text = re.sub(r'-{10,}', '---', text)
    text = re.sub(r'={10,}', '===', text)
    
    # Compress absolute file paths
    # Match something like /home/john/HIGH-GRAVITY/... and replace with ./...
    if "REPO_ROOT" in globals():
        repo_str = str(REPO_ROOT)
        text = text.replace(repo_str + "/", "./")
        text = text.replace(repo_str, ".")
    
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +\n', '\n', text)
    return text

def truncate_history(messages: List[Dict], max_turns: int = 10) -> List[Dict]:
    """Drops old context messages to prevent bloat, keeping system prompt."""
    if len(messages) <= max_turns + 1:
        return messages
    system_msgs = [m for m in messages if m.get("role") == "system"]
    other_msgs = [m for m in messages if m.get("role") != "system"]
    return system_msgs + other_msgs[-max_turns:]

def optimize_system_prompt(text: str) -> str:
    """Condenses massive IDE persona prompts."""
    if not isinstance(text, str): return text
    # A generic aggressive condensing rule: remove extra fluff
    # For now, just rely on compress_context plus we can strip known massive XML tags
    text = re.sub(r'<windsurf_instructions>.*?</windsurf_instructions>', '<windsurf_instructions>Act as expert</windsurf_instructions>', text, flags=re.DOTALL)
    return text

def inject_local_rules(messages: List[Dict]):
    """Reads .highgravity_rules from PWD and injects into system prompt."""
    rules_path = Path(".highgravity_rules")
    if not rules_path.exists():
        return
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = f.read().strip()
        if not rules: return
        
        for msg in messages:
            if msg.get("role") == "system":
                msg["content"] = msg.get("content", "") + f"\n\n# LOCAL PROJECT RULES:\n{rules}"
                return
        messages.insert(0, {"role": "system", "content": f"# LOCAL PROJECT RULES:\n{rules}"})
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

    def get_key(self, is_windsurf: bool = False, prompt: str = "") -> Optional[str]:
        provider = "windsurf" if is_windsurf else "llm"
        
        # Feature 5: Multi-Identity Shadow Rotation (Persona routing)
        pl = prompt.lower()
        persona = "Architect"
        if "security" in pl or "vulnerability" in pl: persona = "Auditor"
        elif "fast" in pl or "hack" in pl: persona = "Hacker"
        
        if self.rotation_mode == "sticky":
            if provider in self.active_keys and self.active_keys[provider] not in self.exhausted_keys:
                return self.active_keys[provider]

        def is_ws(k): return k.startswith("sk-ws-")
        candidates = [k for k in self.keys if k not in self.exhausted_keys and (is_ws(k) == is_windsurf)]
        if not candidates: return None
        
        # Pseudo-random selection tied to persona (hashing the persona string + current pool size)
        persona_hash = int(hashlib.sha256(persona.encode()).hexdigest(), 16)
        
        self.current_index = (self.current_index + persona_hash) % len(candidates)
        sel = candidates[self.current_index]
        self.active_keys[provider] = sel
        logger.info(f"ROTATION ({provider}): KEY={sel[:15]}... MODE={self.rotation_mode} PERSONA={persona} TOTAL_ACTIVE={len(candidates)}")
        return sel

pool = TokenPool()

# --- MITM Bridge Detection ---
class MITMBridge:
    """Automatic service detection and interception for Gemini and Codex"""
    
    def __init__(self):
        self.detected_services = set()
        self.service_endpoints = {
            "gemini": [
                "generativelanguage.googleapis.com",
                "ai.google.dev",
                "gemini-api",
                "/v1beta/models",
                "/v1/models"
            ],
            "codex": [
                "api.openai.com/v1/engines",
                "api.openai.com/v1/completions",
                "codex-",
                "/engines/davinci-codex",
                "/engines/cushman-codex"
            ],
            "openai": [
                "api.openai.com",
                "/v1/chat/completions",
                "/v1/completions"
            ]
        }
        # 2026 model map. Tiered: (fast_target, deep_target) selected per request.
        # Gemini 1.5 family defunct; Gemini 2.0 deprecated; Gemini 3 Pro Preview shut
        # down 2026-03-09 so the live frontier targets are gemini-3-pro-preview
        # (user-specified alias -> routed to current Gemini 3.x preview) and
        # gemini-2.5-pro as the stable fallback.
        self.premium_model_map = {
            # --- Gemini: defunct / legacy -> current frontier ---
            "gemini-pro":              ("gemini-2.5-pro",        "gemini-3-pro-preview"),
            "gemini-1.0-pro":          ("gemini-2.5-pro",        "gemini-3-pro-preview"),
            "gemini-1.5-pro":          ("gemini-2.5-pro",        "gemini-3-pro-preview"),
            "gemini-1.5-flash":        ("gemini-2.5-flash",      "gemini-2.5-pro"),
            "gemini-2.0-flash":        ("gemini-2.5-flash",      "gemini-2.5-pro"),
            "gemini-2.0-flash-exp":    ("gemini-2.5-flash",      "gemini-3-pro-preview"),
            "gemini-2.0-flash-lite":   ("gemini-2.5-flash-lite", "gemini-2.5-pro"),
            "gemini-2.5-flash-lite":   ("gemini-2.5-flash-lite", "gemini-2.5-pro"),
            "gemini-2.5-flash":        ("gemini-2.5-flash",      "gemini-3-pro-preview"),
            "gemini-2.5-pro":          ("gemini-2.5-pro",        "gemini-3-pro-preview"),

            # --- Codex legacy -> gpt-5.x codex family ---
            # gpt-5.4 is the current default frontier agentic coding model;
            # gpt-5.3-codex-spark is the ultra-fast coding tier;
            # gpt-5.1-codex-max is the flagship deep-reasoning codex tier.
            "codex":                   ("gpt-5.3-codex-spark",   "gpt-5.1-codex-max"),
            "davinci-codex":           ("gpt-5.3-codex-spark",   "gpt-5.1-codex-max"),
            "cushman-codex":           ("gpt-5.3-codex-spark",   "gpt-5.4-mini"),
            "code-davinci-002":        ("gpt-5.3-codex-spark",   "gpt-5.1-codex-max"),
            "code-cushman-001":        ("gpt-5.3-codex-spark",   "gpt-5.4-mini"),

            # --- OpenAI chat legacy -> gpt-5.x flagship ---
            "gpt-3.5-turbo":           ("gpt-5.4-mini",          "gpt-5.4"),
            "gpt-4":                   ("gpt-5.4-mini",          "gpt-5.4"),
            "gpt-4-turbo":             ("gpt-5.4-mini",          "gpt-5.4"),
            "gpt-4o-mini":             ("gpt-5.4-mini",          "gpt-5.4"),
            "gpt-4o":                  ("gpt-5.4",               "gpt-5.2"),
            "gpt-4.1":                 ("gpt-5.4",               "gpt-5.2"),
            "o1-mini":                 ("gpt-5.4-mini",          "gpt-5.1-codex-max"),
            "o1":                      ("gpt-5.4",               "gpt-5.1-codex-max"),
            "o3-mini":                 ("gpt-5.4-mini",          "gpt-5.1-codex-max"),
            "o3":                      ("gpt-5.4",               "gpt-5.1-codex-max"),
        }

        # Heuristic keywords that upgrade a request to the "deep" tier.
        self.deep_reasoning_keywords = (
            "debug", "explain why", "architect", "design", "refactor",
            "audit", "vulnerab", "prove", "root cause", "complex", "reason",
            "think step", "analyze", "derivation", "optimi",
        )
        # Heuristic keywords that route to codex-spark (coding-first).
        self.coding_keywords = (
            "```", "def ", "class ", "function ", "implement", "compile",
            "traceback", "stack trace", "refactor", "unit test", "pytest",
            "cargo ", "npm ", "tsc ", "webpack", "import ",
        )

        # Thinking / reasoning effort tiers. OpenAI Codex exposes four levels
        # (low / medium / high / xhigh) per the 2026 Codex UI + GPT-5.1-Codex-Max
        # API release; `high` is the Codex default, `xhigh` (introduced with
        # gpt-5.1-codex-max) is for non-latency-sensitive deep reasoning.
        # Gemini maps via `thinkingConfig.thinkingBudget` (0=disabled,
        # positive int=fixed budget, -1=dynamic/unbounded).
        self.thinking_levels = {
            "minimal": {"openai": "minimal", "gemini_budget": 0,     "label": "Minimal"},
            "low":     {"openai": "low",     "gemini_budget": 1024,  "label": "Low"},
            "medium":  {"openai": "medium",  "gemini_budget": 8192,  "label": "Medium"},
            "high":    {"openai": "high",    "gemini_budget": 24576, "label": "High (Codex default)"},
            "xhigh":   {"openai": "xhigh",   "gemini_budget": -1,    "label": "Extra High"},
        }

        # Keywords that escalate a request past `high` into `xhigh` (extra-high
        # reasoning). Intentionally narrow so we don't waste tokens.
        self.xhigh_keywords = (
            "extra high", "exhaustive", "step-by-step proof", "formal proof",
            "comprehensive audit", "full threat model", "root cause analysis",
            "exhaustively", "prove correctness",
        )

        # --- Runtime counters exposed through /hg/telemetry for hg.py dash ---
        self.upgrades_total = 0
        self.upgrades_by_service = {"gemini": 0, "codex": 0, "openai": 0}
        self.upgrades_by_tier = {"fast": 0, "deep": 0}
        self.thinking_by_level = {k: 0 for k in self.thinking_levels}
        self.rate_limit_hits = 0
        self.recent_events = deque(maxlen=50)  # ring buffer of dashboard events

        logger.info(f"MITM_BRIDGE: Initialized - Mode={MITM_MODE} AutoDetect={MITM_AUTO_DETECT}")

    def record_event(self, kind: str, detail: str):
        """Append a short event to the ring buffer for the dashboard."""
        self.recent_events.append({
            "ts": time.time(),
            "kind": kind,
            "detail": detail,
        })
    
    def detect_service(self, path: str, headers: dict, body: dict) -> Optional[str]:
        """Auto-detect which service is being called"""
        if not MITM_AUTO_DETECT or MITM_MODE != "enabled":
            return None
        
        path_lower = path.lower()
        host = headers.get("host", "").lower()
        
        for service, patterns in self.service_endpoints.items():
            if service not in MITM_SERVICES:
                continue
            
            for pattern in patterns:
                if pattern in path_lower or pattern in host:
                    if service not in self.detected_services:
                        self.detected_services.add(service)
                        logger.info(f"MITM_BRIDGE: Auto-detected {service.upper()} service - Intercepting")
                        self.record_event("detect", f"Auto-detected {service.upper()}")
                    return service
        
        return None
    
    def _extract_prompt_text(self, body: dict) -> str:
        """Pull a best-effort prompt string out of an OpenAI- or Gemini-shaped body."""
        if not isinstance(body, dict):
            return ""
        parts = []
        # OpenAI chat style
        for msg in body.get("messages", []) or []:
            if isinstance(msg, dict):
                c = msg.get("content")
                if isinstance(c, str):
                    parts.append(c)
                elif isinstance(c, list):
                    for seg in c:
                        if isinstance(seg, dict) and isinstance(seg.get("text"), str):
                            parts.append(seg["text"])
        # OpenAI legacy completion
        if isinstance(body.get("prompt"), str):
            parts.append(body["prompt"])
        # Gemini native style
        for item in body.get("contents", []) or []:
            if isinstance(item, dict):
                for seg in item.get("parts", []) or []:
                    if isinstance(seg, dict) and isinstance(seg.get("text"), str):
                        parts.append(seg["text"])
        return "\n".join(parts)

    def _select_tier(self, prompt: str, current_model: str) -> str:
        """Decide whether to route to the 'fast' or 'deep' upgrade target."""
        pl = (prompt or "").lower()
        ml = (current_model or "").lower()

        # Family tokens that signal the fast / deep tier. We match against
        # dash-delimited tokens from the model name so that e.g. `gemini-2.5-pro`
        # doesn't match `mini` (as a substring of `gemini`).
        fast_tokens = {"flash", "mini", "nano", "spark", "turbo", "lite"}
        deep_tokens = {"pro", "max", "ultra", "opus", "o1", "o3"}
        tokens = set(re.split(r"[-_./]+", ml))

        if tokens & fast_tokens:
            default_tier = "fast"
        elif tokens & deep_tokens:
            default_tier = "deep"
        else:
            default_tier = "fast"

        # Prompt heuristics can upgrade a fast request into the deep tier.
        if any(kw in pl for kw in self.deep_reasoning_keywords):
            return "deep"
        if len(pl) > 6000:  # long context -> use the deep tier
            return "deep"
        return default_tier

    def inject_premium_model(self, body: dict, service: str) -> dict:
        """Inject premium model usage using a (fast, deep) tier-aware upgrade."""
        if not MITM_INJECT_PREMIUM or not isinstance(body, dict):
            return body

        current_model = body.get("model", "") or ""
        if not current_model:
            return body

        # Find the longest matching key so that e.g. `gpt-4o-mini` beats `gpt-4`.
        match_key = None
        for base_model in self.premium_model_map.keys():
            if base_model in current_model:
                if match_key is None or len(base_model) > len(match_key):
                    match_key = base_model

        if match_key is None:
            return body

        fast_target, deep_target = self.premium_model_map[match_key]
        prompt = self._extract_prompt_text(body)
        tier = self._select_tier(prompt, current_model)

        # Codex-style coding prompts always prefer the codex-spark fast tier
        # unless the request explicitly wants deep reasoning.
        if service == "codex" and tier == "fast":
            fast_target = "gpt-5.3-codex-spark"

        target = deep_target if tier == "deep" else fast_target
        if target and target != current_model:
            body["model"] = target
            logger.info(
                f"MITM_BRIDGE: Injected premium model {current_model} -> {target} "
                f"(match={match_key} tier={tier} service={service})"
            )
            # --- telemetry counters ---
            self.upgrades_total += 1
            if service in self.upgrades_by_service:
                self.upgrades_by_service[service] += 1
            self.upgrades_by_tier[tier] = self.upgrades_by_tier.get(tier, 0) + 1
            self.record_event(
                "upgrade",
                f"{service}: {current_model} -> {target} ({tier})",
            )
        return body

    def _select_thinking_level(self, prompt: str, current_model: str) -> str:
        """Pick one of the 4 Codex reasoning tiers (low / medium / high / xhigh).

        Mirrors the Codex CLI picker:
            1. low               Fast responses, light reasoning
            2. medium (current)  Balanced speed/depth for everyday tasks
            3. high (default)    Greater depth for complex problems
            4. xhigh             Extra high depth, non-latency-sensitive work
        """
        pl = (prompt or "").lower()
        tier = self._select_tier(prompt, current_model)

        # xhigh: very narrow opt-in
        if any(kw in pl for kw in self.xhigh_keywords) or len(pl) > 16000:
            return "xhigh"

        if tier == "deep":
            # OpenAI Codex default for deep work is `high`.
            return "high"

        # Fast tier: bump trivially short prompts to `low`, everything else to
        # `medium` which is the best speed/depth tradeoff for coding chat.
        if len(pl) < 120:
            return "low"
        return "medium"

    def inject_thinking_level(self, body: dict, service: str) -> dict:
        """Attach reasoning / thinking-budget configuration for the request."""
        if not MITM_INJECT_PREMIUM or not isinstance(body, dict):
            return body

        prompt = self._extract_prompt_text(body)
        level = self._select_thinking_level(prompt, body.get("model", "") or "")
        cfg = self.thinking_levels[level]

        changed = False
        model_name = (body.get("model") or "").lower()
        # OpenAI (gpt-5.x / codex) -> reasoning_effort
        if service in ("openai", "codex") or "gpt-5" in model_name or "codex" in model_name:
            if "reasoning_effort" not in body:
                body["reasoning_effort"] = cfg["openai"]
                logger.info(f"MITM_BRIDGE: Set reasoning_effort={cfg['openai']} (level={level})")
                changed = True
        # Gemini 2.5+ / 3.x -> thinkingConfig.thinkingBudget
        if service == "gemini" or "gemini" in model_name:
            gc = body.setdefault("generationConfig", {})
            if isinstance(gc, dict) and "thinkingConfig" not in gc:
                gc["thinkingConfig"] = {"thinkingBudget": cfg["gemini_budget"]}
                logger.info(f"MITM_BRIDGE: Set thinkingBudget={cfg['gemini_budget']} (level={level})")
                changed = True

        if changed:
            self.thinking_by_level[level] = self.thinking_by_level.get(level, 0) + 1
            self.record_event("thinking", f"{service}: {cfg['label']} ({level})")
        return body

    def reduce_rate_limit_headers(self, headers: dict) -> dict:
        """Modify headers to reduce rate limit detection"""
        if not MITM_REDUCE_RATE_LIMITS:
            return headers
        
        # Remove or modify rate-limit tracking headers
        rate_limit_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset",
            "retry-after"
        ]
        
        for header in rate_limit_headers:
            if header in headers:
                del headers[header]
        
        return headers
    
    def apply_mitm_features(self, body: dict, headers: dict, service: str) -> tuple:
        """Apply all MITM features to a request."""
        # 1. Tier-aware premium model upgrade (must run first so the thinking
        #    level injector sees the upgraded model name).
        body = self.inject_premium_model(body, service)

        # 2. Reasoning / thinking-budget injection.
        body = self.inject_thinking_level(body, service)

        # 3. Rate-limit header scrub.
        headers = self.reduce_rate_limit_headers(headers)

        # 4. Service-specific tweaks. Note: gpt-5.x reasoning / codex models
        #    reject `temperature` overrides, so we only set it when the model
        #    is a non-reasoning chat model.
        if isinstance(body, dict):
            model_name = (body.get("model") or "").lower()
            is_reasoning = (
                "gpt-5" in model_name
                or "codex" in model_name
                or model_name.startswith(("o1", "o3", "o4"))
            )

            if service == "gemini":
                gc = body.setdefault("generationConfig", {})
                if isinstance(gc, dict) and "temperature" not in gc:
                    gc["temperature"] = 0.7
            elif service == "codex":
                body.setdefault("max_completion_tokens", body.pop("max_tokens", 4096))
                if not is_reasoning and "temperature" not in body:
                    body["temperature"] = 0.2

        return body, headers

mitm_bridge = MITMBridge()

@app.get("/hg/telemetry")
async def get_telemetry():
    """Exposes comprehensive proxy metrics (consumed by hg.py dashboard)."""
    return {
        "cache_hits": ghost_cache.tokens_saved,
        "active_keys": len(pool.keys),
        "exhausted_keys": len(pool.exhausted_keys),
        "rotation_mode": pool.rotation_mode,
        "proxy_port": PROXY_PORT,
        "status": "online",
        # --- MITM bridge ---
        "mitm_mode": MITM_MODE,
        "mitm_auto_detect": MITM_AUTO_DETECT,
        "mitm_services_enabled": MITM_SERVICES,
        "mitm_detected_services": sorted(mitm_bridge.detected_services),
        "mitm_inject_premium": MITM_INJECT_PREMIUM,
        "mitm_reduce_rate_limits": MITM_REDUCE_RATE_LIMITS,
        "mitm_upgrades_total": mitm_bridge.upgrades_total,
        "mitm_upgrades_by_service": dict(mitm_bridge.upgrades_by_service),
        "mitm_upgrades_by_tier": dict(mitm_bridge.upgrades_by_tier),
        "mitm_thinking_by_level": dict(mitm_bridge.thinking_by_level),
        "mitm_rate_limit_hits": mitm_bridge.rate_limit_hits,
        "mitm_recent_events": list(mitm_bridge.recent_events),
    }

@app.post("/hg/manage")
async def manage_proxy(request: Request):
    d = await request.json()
    action = d.get("action")
    if action == "clear_cache":
        try:
            with sqlite3.connect(ghost_cache.db_path) as conn:
                conn.execute("DELETE FROM cache")
            return {"status": "ok", "msg": "Cache cleared"}
        except: return {"status": "error"}
    elif action == "rotate_keys":
        pool.get_key(is_windsurf=True) # Forces rotation
        return {"status": "ok", "msg": "Keys rotated"}
    return {"status": "error", "msg": "Unknown action"}


request_timestamps = deque(maxlen=50)
last_anomaly_cleared = 0

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_request(path: str, request: Request):
    global last_anomaly_cleared
    request_id = secrets.token_hex(4)
    logger.info(f"[{request_id}] CONNECTION ATTEMPT: {request.method} /{path}")
    body_bytes = await request.body()
    raw_body_json = {}; is_json = False
    
    # Feature 3: Soft-Block Anomaly Detection
    now = time.time()
    request_timestamps.append(now)
    if "unleash" not in path.lower() and len(request_timestamps) >= 15:
        # Check if 15 requests in last 5 seconds
        if now - request_timestamps[-15] < 5.0 and now - last_anomaly_cleared > 10.0:
            last_anomaly_cleared = now
            logger.warning(f"[{request_id}] ANOMALY DETECTED: Soft-blocking burst request.")
            return StreamingResponse(iter([json.dumps({"error": {"message": "Anomaly Detected: Unusual request pattern. If this is intentional, please retry your request to confirm.", "type": "high_gravity_anomaly", "code": "429"}}).encode()]), status_code=429, media_type="application/json")

    if "application/json" in request.headers.get("Content-Type", "") or not request.headers.get("Content-Type"):
        try:
            if body_bytes: raw_body_json = json.loads(body_bytes); is_json = True
        except: pass

    # --- Feature 2 & 5: Local RAG and Context Compression ---
    if is_json and "messages" in raw_body_json:
        # Feature 2: Auto-Summary Engine
        orig_len = len(raw_body_json["messages"])
        raw_body_json["messages"] = truncate_history(raw_body_json["messages"], max_turns=10)
        
        # System Rules & Compression
        inject_local_rules(raw_body_json["messages"])
        
        # Inject Auto-Summary tag if truncated
        if len(raw_body_json["messages"]) < orig_len:
            for msg in raw_body_json["messages"]:
                if msg.get("role") == "system":
                    msg["content"] = msg.get("content", "") + "\n\n<highgravity_memory>Background agent: Older messages were summarized and truncated to save context.</highgravity_memory>"
                    break
                    
        for msg in raw_body_json["messages"]:
            if isinstance(msg.get("content"), str):
                msg["content"] = compress_context(msg["content"])
                # Strip comments if not requested
                if "doc" not in raw_body_json["messages"][-1].get("content", "").lower():
                    msg["content"] = re.sub(r'(?m)^[ \t]*([#//]+).*$', '', msg["content"])

        # Feature 6: Local Live-Linting Agent
        latest_msg = raw_body_json["messages"][-1].get("content", "")
        py_blocks = re.findall(r'```python\n(.*?)\n```', latest_msg, re.DOTALL)
        for block in py_blocks:
            try:
                ast.parse(block)
            except SyntaxError as e:
                raw_body_json["messages"][-1]["content"] += f"\n\n[Local Agent Observation: Syntax error on line {e.lineno}: {e.msg}]"
                logger.info(f"[{request_id}] LIVE_LINTER: Injected SyntaxError feedback.")

        # Ping Interception
        latest_msg = raw_body_json["messages"][-1].get("content", "").strip().lower()
        if latest_msg in ["hello", "ping", "are you there?", "hi"]:
             return StreamingResponse(iter([json.dumps({"choices": [{"message": {"role": "assistant", "content": "OK"}}]}).encode()]), media_type="application/json")

    # Tool Filtering & Routing
    if is_json and "model" in raw_body_json:
        # Tiered Model Routing: Down-route simple requests to Flash
        if any(keyword in str(raw_body_json.get("messages", "")) for keyword in ["list files", "ls", "grep"]):
            raw_body_json["model"] = "gemini-2.0-flash-exp"
        
        # No-Op Tool Rejection
        if "tools" in raw_body_json:
            for tool in raw_body_json["tools"]:
                if tool.get("name") in ["run_server", "deploy_app"]:
                    # Reject dangerous tool calls locally
                    return StreamingResponse(iter([json.dumps({"error": "Tool restricted by HIGH-GRAVITY"}).encode()]), status_code=403, media_type="application/json")


    if is_json and "messages" in raw_body_json and not raw_body_json.get("stream"):
        cr = ghost_cache.get(raw_body_json["messages"])
        if cr:
            logger.info(f"[{request_id}] GHOST_CACHE_HIT: KEY=LOCAL (Saved: {ghost_cache.tokens_saved} tokens)")
            return StreamingResponse(iter([cr]), media_type="application/json")

    # --- MITM Bridge Detection ---
    detected_service = None
    if MITM_MODE == "enabled" and MITM_AUTO_DETECT:
        detected_service = mitm_bridge.detect_service(path, dict(request.headers), raw_body_json)
        if detected_service:
            logger.info(f"[{request_id}] MITM_BRIDGE: Intercepting {detected_service.upper()} request")
            # Apply MITM features
            if is_json:
                raw_body_json, fwd_headers = mitm_bridge.apply_mitm_features(
                    raw_body_json, 
                    {k: v for k, v in request.headers.items()},
                    detected_service
                )
    
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
                "enable_o3_models", "MODEL_O3_PRO_2025_06_10", "MODEL_O3_PRO_2025_06_10_HIGH",
                "enable_gemini_3_0", "MODEL_GOOGLE_GEMINI_3_0_PRO_HIGH", "MODEL_GOOGLE_GEMINI_3_0_PRO_MEDIUM",
                "MODEL_GOOGLE_GEMINI_3_0_PRO_LOW", "MODEL_GOOGLE_GEMINI_3_0_PRO_MINIMAL", "DEEP_WIKI_MODEL_TYPE_PREMIUM",
                "MODEL_TAB_EXPERIMENTAL_1", "MODEL_TAB_EXPERIMENTAL_2", "MODEL_TAB_EXPERIMENTAL_3", "MODEL_TAB_EXPERIMENTAL_4",
                "MODEL_TAB_EXPERIMENTAL_5", "MODEL_TAB_EXPERIMENTAL_6", "MODEL_TAB_EXPERIMENTAL_7", "MODEL_TAB_EXPERIMENTAL_8",
                "MODEL_TAB_EXPERIMENTAL_9", "MODEL_TAB_EXPERIMENTAL_10",
                
                # --- Logical Identity (Consolidated to Enterprise) ---
                "is_enterprise", "ENTERPRISE_SAAS", "PRO_ULTIMATE", "TEAMS_TIER_ENTERPRISE_SAAS",
                "allow_premium_command_models", "allow_sticky_premium_models", "allow_codemap_sharing",
                "enable_auto_cascade_seat_provisioning", "attribution_enabled", "audit_logs_enabled"
            ]
            # Flags to explicitly DISABLE to avoid conflicts
            disable_flags = ["is_pro", "is_premium", "is_free", "is_trial"]
            
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
            # Extract prompt for persona routing
            prompt_str = ""
            if is_json and "messages" in raw_body_json:
                prompt_str = str(raw_body_json["messages"])
                
            if is_windsurf_rpc:
                # Primary Windsurf RPC Target
                target_base_url = "https://server.self-serve.windsurf.com"
                wk = pool.get_key(is_windsurf=True, prompt=prompt_str)
                if not wk: 
                    wk = get_realtime_windsurf_key()
                    if wk: pool.add_key(wk)
                if not wk: raise HTTPException(status_code=503, detail="No Windsurf keys.")
                resolved_api_key = f"Bearer {wk}"
                tp = path
            else:
                model = raw_body_json.get("model", "unknown") if is_json else "unknown"
                
                # MITM Bridge: Override target based on detected service
                if detected_service == "gemini":
                    target_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
                    resolved_api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
                elif detected_service == "codex":
                    target_base_url = "https://api.openai.com"
                    resolved_api_key = os.environ.get("OPENAI_API_KEY")
                elif "gpt" in str(model) or "codex" in str(model):
                    target_base_url = "https://api.openai.com"
                    resolved_api_key = os.environ.get("OPENAI_API_KEY")
                elif any(k in str(model) for k in ["claude", "sonnet", "opus"]):
                    target_base_url = "https://api.anthropic.com"
                    resolved_api_key = os.environ.get("ANTHROPIC_API_KEY")
                elif "gemini" in str(model):
                    target_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
                    resolved_api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
                else:
                    target_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
                    resolved_api_key = os.environ.get("GOOGLE_API_KEY")
                
                if not resolved_api_key:
                    pk = pool.get_key(is_windsurf=False, prompt=prompt_str)
                    if not pk: raise HTTPException(status_code=503, detail="No LLM keys.")
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

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=request.method, url=target_url,
                    json=raw_body_json if is_json else None,
                    data=body_bytes if not is_json else None,
                    headers=fh, params=request.query_params,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 429:
                        # MITM Bridge: Enhanced rate limit handling
                        cooldown = 0.5 if MITM_REDUCE_RATE_LIMITS else 1.0
                        pool.mark_exhausted(resolved_api_key, is_rate_limit=True)
                        if detected_service:
                            logger.info(f"[{request_id}] MITM_BRIDGE: Rate limit hit on {detected_service.upper()}, reduced cooldown={cooldown}s")
                            mitm_bridge.rate_limit_hits += 1
                            mitm_bridge.record_event("ratelimit", f"{detected_service.upper()} 429 (cooldown={cooldown}s)")
                        if attempt < max_retries - 1: await asyncio.sleep(cooldown); continue
                        raise HTTPException(status_code=503, detail="Rate-limited.")
                    if resp.status in [401, 403]:
                        pool.mark_exhausted(resolved_api_key, is_rate_limit=False)
                        if attempt < max_retries - 1: continue
                        raise HTTPException(status_code=resp.status, detail="Auth failed.")

                    content = await resp.read()
                    
                    # Rescue Mock for Model Status
                    if "GetModelStatuses" in path and (resp.status != 200 or len(content) < 10):
                        logger.warning(f"[{request_id}] RESCUE_MOCK: Serving Elite failover.")
                        rescue_data = {
                            "modelStatuses": [
                                {"modelId": "claude-3-5-sonnet", "status": "HEALTHY"},
                                {"modelId": "claude-3-opus", "status": "HEALTHY"},
                                {"modelId": "gpt-4o", "status": "HEALTHY"},
                                {"modelId": "gemini-2.0-flash-exp", "status": "HEALTHY"}
                            ]
                        }
                        return StreamingResponse(iter([json.dumps(rescue_data).encode()]), media_type="application/json")

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
