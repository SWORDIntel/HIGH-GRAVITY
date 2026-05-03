#!/usr/bin/env python3
"""
Pegasus-Khoj Integration Bridge
Enhanced Khoj client with auto-indexing and Windsurf workspace detection
"""
import os
import time
import json
import logging
import aiohttp
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)


class PegasusKhojBridge:
    """Enhanced Khoj integration with Pegasus features"""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.enabled = self._check_enabled()
        self.base_url = os.environ.get("HG_KHOJ_URL", "http://127.0.0.1:42110").rstrip("/")
        self.token = os.environ.get("HG_KHOJ_TOKEN", "").strip()
        self.timeout_s = float(os.environ.get("HG_KHOJ_TIMEOUT_SECONDS", "4"))
        self.fast_timeout_s = float(os.environ.get("HG_KHOJ_FAST_TIMEOUT_SECONDS", "0.3"))
        self.deep_timeout_s = float(os.environ.get("HG_KHOJ_DEEP_TIMEOUT_SECONDS", "1.5"))
        self.default_n = int(os.environ.get("HG_KHOJ_TOP_K", "4"))
        self.max_snippets = int(os.environ.get("HG_KHOJ_MAX_SNIPPETS", "4"))
        self.max_chars_per_snippet = int(os.environ.get("HG_KHOJ_MAX_CHARS_PER_SNIPPET", "600"))
        self.max_total_context_chars = int(os.environ.get("HG_KHOJ_MAX_TOTAL_CONTEXT_CHARS", "2200"))
        self.cache_ttl_s = int(os.environ.get("HG_KHOJ_CACHE_TTL_SECONDS", "90"))
        self.cb_fail_threshold = int(os.environ.get("HG_KHOJ_CB_FAIL_THRESHOLD", "5"))
        self.cb_window_s = int(os.environ.get("HG_KHOJ_CB_WINDOW_SECONDS", "120"))
        self.cb_open_s = int(os.environ.get("HG_KHOJ_CB_OPEN_SECONDS", "180"))
        
        # Statistics
        self.search_count = 0
        self.injection_count = 0
        self.last_index_time = 0.0
        self.index_interval = 300  # 5 minutes
        self.last_reindex_status = "never"
        self.last_reindex_detail = ""
        self.last_reindex_progress = {"state": "idle", "updated_at": 0}
        self.last_search_ms = 0.0
        self.last_injection_ms = 0.0
        self.last_query = ""
        self.last_query_hash = ""
        self.last_snippet_count = 0
        self.last_snippet_sources: List[str] = []
        self.last_search_status = "idle"
        self.last_injection_status = "idle"
        self.search_latencies_ms = deque(maxlen=300)
        self.injection_latencies_ms = deque(maxlen=300)
        self.empty_result_count = 0
        self.search_error_reasons = {}
        self.query_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self.cb_failures = deque(maxlen=200)
        self.cb_open_until = 0.0
        
        logger.info(f"PegasusKhojBridge initialized: enabled={self.enabled}, url={self.base_url}")

    def _trace_enabled(self) -> bool:
        if (self.repo_root / "logs" / "khoj_trace.enabled").exists():
            return True
        return os.environ.get("HG_KHOJ_TRACE", "").lower() in {"1", "true", "yes", "on"}

    def _emit_trace(self, event: str, **fields):
        if not self._trace_enabled():
            return
        payload = {
            "ts": time.time(),
            "event": event,
            "enabled": self.enabled,
            "base_url": self.base_url,
            **fields,
        }
        try:
            trace_path = self.repo_root / "logs" / "khoj_trace.jsonl"
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with open(trace_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, sort_keys=True) + "\n")
        except Exception as exc:
            logger.debug(f"Khoj trace write failed: {exc}")
    
    def _check_enabled(self) -> bool:
        """Check if Khoj should be enabled"""
        env_enabled = os.environ.get("HG_KHOJ_ENABLED", "").lower()
        if env_enabled in ["true", "1", "yes"]:
            return True
        if env_enabled in ["false", "0", "no"]:
            return False
        # Auto-detect: enabled if khoj directory exists
        return (self.repo_root / "khoj").exists()
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers with optional auth"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def health_check(self) -> bool:
        """Check if Khoj is healthy"""
        if not self.enabled:
            return False
        try:
            timeout = aiohttp.ClientTimeout(total=2)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/api/health") as resp:
                    return resp.status == 200
        except Exception:
            return False
    
    async def search(self, query: str, n: int = None) -> Dict[str, Any]:
        """Search Khoj index"""
        if not self.enabled:
            return {"status": "disabled"}
        
        if n is None:
            n = self.default_n
        n = min(max(1, n), self.max_snippets)
        qhash = hashlib.sha256(query.encode()).hexdigest()
        self.last_query = query
        self.last_query_hash = qhash
        cached = self.query_cache.get(qhash)
        now = time.time()
        if cached and (now - cached[0] <= self.cache_ttl_s):
            self.last_search_status = "cache_hit"
            self._emit_trace(
                "search_cache_hit",
                query=query[:200],
                query_hash=qhash[:16],
                n=n,
                cached_at=cached[0],
            )
            return cached[1]
        if self._cb_open():
            self.last_search_status = "circuit_open"
            self._emit_trace("search_blocked", query=query[:200], query_hash=qhash[:16], n=n)
            return {"status": "error", "message": "circuit_open"}
        
        try:
            t0 = time.time()
            self.search_count += 1
            timeout = aiohttp.ClientTimeout(total=self.timeout_s)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                params = {"q": query, "n": n, "r": "true"}
                async with session.get(
                    f"{self.base_url}/api/search",
                    params=params,
                    headers=self._headers()
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        took = (time.time() - t0) * 1000.0
                        self.last_search_ms = took
                        self.last_search_status = "ok"
                        self.search_latencies_ms.append(took)
                        out = {"status": "ok", "results": data}
                        self.query_cache[qhash] = (now, out)
                        self._emit_trace(
                            "search_ok",
                            query=query[:200],
                            query_hash=qhash[:16],
                            n=n,
                            took_ms=round(took, 2),
                            result_count=len(data) if hasattr(data, "__len__") else None,
                        )
                        return out
                    else:
                        self._mark_failure(f"http_{resp.status}")
                        self.last_search_status = f"http_{resp.status}"
                        self._emit_trace(
                            "search_http_error",
                            query=query[:200],
                            query_hash=qhash[:16],
                            n=n,
                            status=resp.status,
                        )
                        return {"status": "error", "code": resp.status}
        except Exception as exc:
            logger.debug(f"Khoj search error: {exc}")
            self._mark_failure(type(exc).__name__)
            self.last_search_status = type(exc).__name__
            self._emit_trace(
                "search_exception",
                query=query[:200],
                query_hash=qhash[:16],
                n=n,
                error=type(exc).__name__,
            )
            return {"status": "error", "message": str(exc)}
    
    def _extract_query(self, messages: List[Dict]) -> str:
        """Extract search query from message history"""
        if not messages:
            return ""
        
        # Get last user message
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    # Take first 200 chars as query
                    return content[:200]
        return ""
    
    def _to_snippets(self, results: Any, limit_chars: int = 800) -> List[str]:
        """Convert Khoj results to formatted snippets"""
        snippets = []
        snippet_sources = []
        
        if not results:
            return snippets
        
        # Handle different result formats
        if isinstance(results, list):
            items = results
        elif isinstance(results, dict):
            items = results.get("results", [])
        else:
            return snippets
        
        seen = set()
        total_chars = 0
        for item in items[: self.max_snippets]:
            # Extract text and source
            if isinstance(item, dict):
                text = item.get("entry", item.get("content", ""))
                source = item.get("file", item.get("source", "unknown"))
            else:
                text = str(item)
                source = "unknown"
            
            if not text:
                continue
            
            # Format snippet with source
            key = f"{source}:{text[:120]}"
            if key in seen:
                continue
            seen.add(key)
            snippet_sources.append(source)
            snippet = f"`{source}`\n{text[:limit_chars]}"
            if len(text) > limit_chars:
                snippet += "..."
            if total_chars + len(snippet) > self.max_total_context_chars:
                break
            total_chars += len(snippet)
            snippets.append(snippet)
        self.last_snippet_sources = snippet_sources
        return snippets
    
    async def inject_context(self, messages: List[Dict]) -> Dict[str, Any]:
        """Inject Khoj search context into messages"""
        if not self.enabled:
            return {"status": "disabled"}
        
        t0 = time.time()
        self.last_injection_status = "running"
        if self._cb_open():
            self.last_injection_status = "circuit_open"
            self._emit_trace("inject_blocked", status="circuit_open")
            return {"status": "circuit_open"}
        # Extract query from messages
        query = self._extract_query(messages)
        if not query:
            self.last_injection_status = "no_query"
            self._emit_trace("inject_no_query")
            return {"status": "no_query"}
        self.last_query = query
        self.last_query_hash = hashlib.sha256(query.encode()).hexdigest()
        deep_mode = any(tok in query.lower() for tok in ["deep", "thorough", "investigate", "comprehensive"])
        self.timeout_s = self.deep_timeout_s if deep_mode else self.fast_timeout_s
        
        # Search Khoj
        search_result = await self.search(query)
        if search_result.get("status") != "ok":
            self.last_injection_status = search_result.get("status", "search_error")
            self._emit_trace(
                "inject_search_failed",
                query=query[:200],
                query_hash=self.last_query_hash[:16],
                status=search_result.get("status"),
                search_status=self.last_search_status,
            )
            return search_result
        self.last_search_status = "ok"
        
        # Convert to snippets
        snippets = self._to_snippets(search_result.get("results", []))
        if not snippets:
            self.empty_result_count += 1
            self.last_snippet_count = 0
            self.last_injection_status = "no_results"
            self._emit_trace(
                "inject_no_results",
                query=query[:200],
                query_hash=self.last_query_hash[:16],
                search_status=self.last_search_status,
            )
            return {"status": "no_results"}
        
        # Inject as system message
        context_msg = {
            "role": "system",
            "content": (
                "# KHOJ SEMANTIC SEARCH CONTEXT\n"
                "Relevant code/documentation from indexed workspace:\n\n"
                + "\n\n".join(f"**{i+1}.** {s}" for i, s in enumerate(snippets))
            )
        }
        
        messages.insert(0, context_msg)
        self.injection_count += 1
        took = (time.time() - t0) * 1000.0
        self.last_injection_ms = took
        self.last_snippet_count = len(snippets)
        self.last_injection_status = "ok"
        self.injection_latencies_ms.append(took)
        self._emit_trace(
            "inject_ok",
            query=query[:200],
            query_hash=self.last_query_hash[:16],
            injected=len(snippets),
            sources=self.last_snippet_sources[: self.max_snippets],
            took_ms=round(took, 2),
            search_status=self.last_search_status,
            search_ms=round(self.last_search_ms, 2),
        )
        
        return {
            "status": "ok",
            "injected": len(snippets),
            "query": query[:100],
            "search_ms": round(self.last_search_ms, 2),
            "inject_ms": round(self.last_injection_ms, 2),
            "sources": self.last_snippet_sources[: self.max_snippets],
        }

    def _cb_open(self) -> bool:
        return time.time() < self.cb_open_until

    def _mark_failure(self, reason: str):
        now = time.time()
        self.cb_failures.append(now)
        self.search_error_reasons[reason] = self.search_error_reasons.get(reason, 0) + 1
        while self.cb_failures and now - self.cb_failures[0] > self.cb_window_s:
            self.cb_failures.popleft()
        if len(self.cb_failures) >= self.cb_fail_threshold:
            self.cb_open_until = now + self.cb_open_s
            logger.warning("Khoj circuit breaker opened")
    
    def _get_windsurf_workspaces(self) -> List[str]:
        """Detect active Windsurf workspaces from storage.json"""
        storage_json = Path.home() / ".config" / "Windsurf - Next" / "User" / "globalStorage" / "storage.json"
        workspaces = []
        
        if not storage_json.exists():
            return workspaces
        
        try:
            with open(storage_json) as f:
                data = json.load(f)
            
            # Collect workspace folders
            for folder in data.get("backupWorkspaces", {}).get("folders", []):
                uri = folder.get("folderUri", "")
                if uri.startswith("file://"):
                    path = uri[len("file://"):]
                    if Path(path).exists() and path != str(self.repo_root):
                        workspaces.append(path)
            
            # Also check profileAssociations
            for uri in data.get("profileAssociations", {}).get("workspaces", {}):
                if uri.startswith("file://"):
                    path = uri[len("file://"):]
                    if Path(path).exists() and path != str(self.repo_root) and path not in workspaces:
                        workspaces.append(path)
            
            return workspaces
        except Exception as exc:
            logger.debug(f"Error reading Windsurf workspaces: {exc}")
            return []
    
    async def update_content_sources(self) -> bool:
        """Update Khoj content sources to include Windsurf workspaces"""
        if not self.enabled:
            return False
        
        # Build index paths
        index_paths = [
            str(self.repo_root / "src"),
            str(self.repo_root / "bin"),
            str(self.repo_root / "lib"),
            str(self.repo_root / "config"),
            str(self.repo_root / "docs"),
        ]
        
        # Add Windsurf workspaces
        windsurf_workspaces = self._get_windsurf_workspaces()
        if windsurf_workspaces:
            logger.info(f"Adding {len(windsurf_workspaces)} Windsurf workspace(s) to index")
            index_paths.extend(windsurf_workspaces)
        
        # Filter to existing paths
        existing_paths = [p for p in index_paths if Path(p).exists()]
        
        include_globs = os.environ.get(
            "HG_KHOJ_INCLUDE_GLOBS",
            "*.py,*.md,*.txt,*.json,*.yaml,*.yml,*.sh,*.c,*.cpp,*.h,*.rs,*.go,*.js,*.ts,*.jsx,*.tsx,*.java,*.kt,*.swift,*.rb"
        )
        payload = {
            "name": "HIGH-GRAVITY + Windsurf Workspaces",
            "input_files": existing_paths,
            "input_filter": [g.strip() for g in include_globs.split(",") if g.strip()],
            "index_heading_entries": True,
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/api/content/computer",
                    json=payload,
                    headers=self._headers()
                ) as resp:
                    if resp.status in [200, 201]:
                        logger.info("Content sources updated successfully")
                        return True
                    else:
                        logger.warning(f"Content source update failed: {resp.status}")
                        return False
        except Exception as exc:
            logger.warning(f"Content source update error: {exc}")
            return False
    
    async def trigger_reindex(self) -> bool:
        """Trigger workspace re-indexing (includes Windsurf workspaces)"""
        if not self.enabled:
            return False
        
        current_time = time.time()
        if current_time - self.last_index_time < self.index_interval:
            logger.debug("Skipping re-index (too soon)")
            return False
        
        self.last_reindex_progress = {"state": "starting", "updated_at": int(time.time())}
        # Update content sources first to include any new Windsurf workspaces
        await self.update_content_sources()
        
        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                candidates = [
                    ("POST", f"{self.base_url}/api/update"),
                    ("POST", f"{self.base_url}/api/index/update"),
                    ("GET", f"{self.base_url}/api/update"),
                ]
                for method, url in candidates:
                    if method == "POST":
                        resp_ctx = session.post(url, headers=self._headers())
                    else:
                        resp_ctx = session.get(url, headers=self._headers())
                    async with resp_ctx as resp:
                        if resp.status in (200, 201, 202):
                            self.last_index_time = current_time
                            self.last_reindex_status = "ok"
                            self.last_reindex_detail = f"{method} {url} -> {resp.status}"
                            self.last_reindex_progress = {"state": "ok", "updated_at": int(time.time())}
                            logger.info("Workspace re-indexed successfully (including Windsurf workspaces)")
                            return True
                        self.last_reindex_detail = f"{method} {url} -> {resp.status}"
                self.last_reindex_status = "failed"
                self.last_reindex_progress = {"state": "failed", "updated_at": int(time.time())}
                logger.warning(f"Re-index failed: {self.last_reindex_detail}")
                return False
        except Exception as exc:
            logger.warning(f"Re-index error: {exc}")
            self.last_reindex_status = "error"
            self.last_reindex_detail = str(exc)
            self.last_reindex_progress = {"state": "error", "updated_at": int(time.time())}
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        def pct(vals, p):
            if not vals:
                return None
            arr = sorted(vals)
            idx = min(len(arr) - 1, int(round((p / 100.0) * (len(arr) - 1))))
            return round(arr[idx], 2)
        return {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "search_count": self.search_count,
            "injection_count": self.injection_count,
            "last_query": self.last_query[:200],
            "last_query_hash": self.last_query_hash[:16],
            "last_snippet_count": self.last_snippet_count,
            "last_snippet_sources": self.last_snippet_sources[: self.max_snippets],
            "last_search_status": self.last_search_status,
            "last_injection_status": self.last_injection_status,
            "last_index_time": self.last_index_time,
            "last_reindex_status": self.last_reindex_status,
            "last_reindex_detail": self.last_reindex_detail,
            "reindex_progress": self.last_reindex_progress,
            "last_search_ms": round(self.last_search_ms, 2),
            "last_injection_ms": round(self.last_injection_ms, 2),
            "search_latency_ms": {
                "p50": pct(list(self.search_latencies_ms), 50),
                "p95": pct(list(self.search_latencies_ms), 95),
            },
            "injection_latency_ms": {
                "p50": pct(list(self.injection_latencies_ms), 50),
                "p95": pct(list(self.injection_latencies_ms), 95),
            },
            "empty_result_count": self.empty_result_count,
            "error_reasons": self.search_error_reasons,
            "cache_entries": len(self.query_cache),
            "circuit_open": self._cb_open(),
            "circuit_open_until": int(self.cb_open_until) if self.cb_open_until else 0,
        }
