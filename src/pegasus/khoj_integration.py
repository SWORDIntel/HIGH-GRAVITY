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
import gzip
import re
import zlib
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
        self.fast_timeout_s = float(os.environ.get("HG_KHOJ_FAST_TIMEOUT_SECONDS", "0.8"))
        self.deep_timeout_s = float(os.environ.get("HG_KHOJ_DEEP_TIMEOUT_SECONDS", "1.5"))
        self.inject_mode = os.environ.get("HG_KHOJ_INJECT_MODE", "compact").strip().lower()
        if self.inject_mode not in {"compact", "full", "off"}:
            self.inject_mode = "compact"
        self.default_n = int(os.environ.get("HG_KHOJ_TOP_K", "3"))
        self.max_snippets = int(os.environ.get("HG_KHOJ_MAX_SNIPPETS", "2"))
        self.max_chars_per_snippet = int(os.environ.get("HG_KHOJ_MAX_CHARS_PER_SNIPPET", "260"))
        self.max_total_context_chars = int(os.environ.get("HG_KHOJ_MAX_TOTAL_CONTEXT_CHARS", "900"))
        self.cache_ttl_s = int(os.environ.get("HG_KHOJ_CACHE_TTL_SECONDS", "90"))
        self.binary_inject_ttl_s = int(os.environ.get("HG_KHOJ_BINARY_INJECT_TTL_SECONDS", "600"))
        self.cb_fail_threshold = int(os.environ.get("HG_KHOJ_CB_FAIL_THRESHOLD", "5"))
        self.cb_window_s = int(os.environ.get("HG_KHOJ_CB_WINDOW_SECONDS", "120"))
        self.cb_open_s = int(os.environ.get("HG_KHOJ_CB_OPEN_SECONDS", "180"))
        self.store_observations = os.environ.get("HG_KHOJ_STORE_OBSERVATIONS", "1").lower() in {"1", "true", "yes", "on"}
        self.observation_path = self.repo_root / "logs" / "khoj_intelligence.jsonl"
        self.accel_status_path = self.repo_root / "logs" / "khoj_accel.json"
        
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
        self.last_passive_status = "idle"
        self.last_passive_query = ""
        self.last_passive_query_hash = ""
        self.last_passive_sources: List[str] = []
        self.last_passive_snippet_count = 0
        self.last_passive_ms = 0.0
        self.search_latencies_ms = deque(maxlen=300)
        self.injection_latencies_ms = deque(maxlen=300)
        self.passive_latencies_ms = deque(maxlen=300)
        self.empty_result_count = 0
        self.search_cache_hit_count = 0
        self.passive_lookup_count = 0
        self.passive_hit_count = 0
        self.binary_inject_dedupe_skips = 0
        self.binary_inject_disabled_skips = 0
        self.recent_binary_injections: Dict[str, float] = {}
        self.stored_observation_count = 0
        self.last_store_status = "idle"
        self.last_store_path = ""
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

    def _store_observation(
        self,
        mode: str,
        path: str,
        query: str,
        status: str,
        snippets: List[str],
        sources: List[str],
        request_id: str = "",
        injected: bool = False,
    ) -> bool:
        """Persist useful local intelligence gathered from live work."""
        if not self.store_observations or not query:
            self.last_store_status = "skipped"
            return False

        payload = {
            "ts": time.time(),
            "mode": mode,
            "path": path,
            "request_id": request_id,
            "query": query[:500],
            "query_hash": hashlib.sha256(query.encode()).hexdigest()[:16],
            "status": status,
            "injected": bool(injected),
            "snippet_count": len(snippets),
            "sources": sources[: self.max_snippets],
            "snippets": snippets[: self.max_snippets],
        }

        try:
            self.observation_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.observation_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, sort_keys=True) + "\n")
            self.stored_observation_count += 1
            self.last_store_status = "ok"
            self.last_store_path = str(self.observation_path)
            return True
        except Exception as exc:
            self.last_store_status = type(exc).__name__
            logger.debug(f"Khoj observation store failed: {exc}")
            return False

    def _observation_file_stats(self) -> Dict[str, Any]:
        """Summarize persisted observations so sibling proxy processes share a baseline."""
        if not self.observation_path.exists():
            return {"observation_file_count": 0}

        total = 0
        injected = 0
        hits = 0
        latest: Dict[str, Any] = {}
        try:
            with open(self.observation_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    total += 1
                    if item.get("injected"):
                        injected += 1
                    if int(item.get("snippet_count") or 0) > 0:
                        hits += 1
                    latest = item
        except Exception as exc:
            logger.debug(f"Khoj observation stats failed: {exc}")
            return {"observation_file_count": total, "observation_file_error": type(exc).__name__}

        stats = {
            "observation_file_count": total,
            "observation_injection_count": injected,
            "observation_hit_count": hits,
        }
        if latest:
            query = str(latest.get("query", ""))
            stats.update({
                "last_observation_status": latest.get("status", ""),
                "last_observation_path": latest.get("path", ""),
                "last_observation_query": query[:200],
                "last_observation_query_hash": latest.get("query_hash", ""),
                "last_observation_snippet_count": int(latest.get("snippet_count") or 0),
                "last_observation_injected": bool(latest.get("injected")),
                "last_observation_ts": latest.get("ts", 0),
            })
        return stats

    def _acceleration_stats(self) -> Dict[str, Any]:
        if not self.accel_status_path.exists():
            return {"configured": False}
        try:
            with open(self.accel_status_path, "r", encoding="utf-8") as fh:
                status = json.load(fh)
            status["configured"] = True
            return status
        except Exception as exc:
            return {"configured": False, "error": type(exc).__name__}

    def _check_enabled(self) -> bool:
        """Check if Khoj should be enabled"""
        env_enabled = os.environ.get("HG_KHOJ_ENABLED", "").lower()
        if env_enabled in ["true", "1", "yes"]:
            return True
        if env_enabled in ["false", "0", "no"]:
            return False
        # Auto-detect: enabled if khoj directory exists
        return (self.repo_root / "khoj").exists()
    
    def _headers(self, include_content_type: bool = True, use_auth: bool = True) -> Dict[str, str]:
        """Get request headers with optional auth/content-type"""
        headers: Dict[str, str] = {}
        if include_content_type:
            headers["Content-Type"] = "application/json"
        if self.token and use_auth:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _auth_attempts(self) -> List[bool]:
        if self.token:
            return [True, False]
        return [False]
    
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
    
    async def search(self, query: str, n: int = None, timeout_override: Optional[float] = None) -> Dict[str, Any]:
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
            self.search_cache_hit_count += 1
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
            timeout = aiohttp.ClientTimeout(total=timeout_override if timeout_override is not None else self.timeout_s)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                params = {"q": query, "n": n, "r": "true"}
                for use_auth in self._auth_attempts():
                    async with session.get(
                        f"{self.base_url}/api/search",
                        params=params,
                        headers=self._headers(include_content_type=False, use_auth=use_auth),
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

                        if use_auth and resp.status in (401, 403, 500):
                            continue

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
                self._mark_failure("auth_fallback_exhausted")
                self.last_search_status = "auth_fallback_exhausted"
                return {"status": "error", "message": "auth_fallback_exhausted"}
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
        """Extract search query from message history (hardened for Cascade/Claude)"""
        if not messages:
            return ""
        
        # Get last user message
        for msg in reversed(messages):
            # Support both OpenAI/Anthropic 'role' and Cascade 'author'
            role = str(msg.get("role") or msg.get("author") or "").lower()
            if role in {"user", "human"}:
                content = msg.get("content", "")
                
                # Handle string content
                if isinstance(content, str):
                    return content[:200]
                
                # Handle list-based content (standard in Claude/Cascade)
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                        elif isinstance(part, str):
                            text_parts.append(part)
                    return " ".join(text_parts)[:200]
        return ""

    def _read_binary_varint(self, data: bytes, offset: int, max_bytes: int = 5) -> Tuple[Optional[int], int]:
        value = 0
        shift = 0
        for idx in range(offset, min(len(data), offset + max_bytes)):
            byte = data[idx]
            value |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return value, idx + 1
            shift += 7
        return None, offset

    def _decompress_binary_payload(self, data: bytes, limit: int) -> List[bytes]:
        """Return bounded gzip/zlib decodes for likely-compressed payloads."""
        if not data:
            return []

        payloads = []
        attempts = []
        if data.startswith(b"\x1f\x8b"):
            attempts.append(16 + zlib.MAX_WBITS)
        if len(data) >= 2:
            attempts.append(zlib.MAX_WBITS)

        for wbits in dict.fromkeys(attempts):
            try:
                decompressor = zlib.decompressobj(wbits)
                decoded = decompressor.decompress(data, limit + 1)
            except zlib.error:
                continue
            if decoded:
                payloads.append(decoded[:limit])

        # Some test fixtures and clients produce plain gzip members that zlib
        # rejects after the bounded attempt; keep a fallback for small bodies.
        if data.startswith(b"\x1f\x8b") and len(data) <= limit:
            try:
                decoded = gzip.decompress(data)
            except (OSError, EOFError, zlib.error):
                decoded = b""
            if decoded:
                payloads.append(decoded[:limit])

        return payloads

    def _connect_frame_payloads(self, data: bytes, limit: int) -> List[bytes]:
        """Extract bounded Connect envelope payloads without mutating frames."""
        payloads = []
        offset = 0
        frames = 0
        max_frames = 32

        while offset + 5 <= len(data) and frames < max_frames:
            flags = data[offset]
            if flags & ~0x01:
                break
            length = int.from_bytes(data[offset + 1: offset + 5], "big")
            start = offset + 5
            end = start + length
            if length <= 0 or length > limit or end > len(data):
                break

            payload = data[start:end]
            if flags & 0x01:
                payloads.extend(self._decompress_binary_payload(payload, limit))
            else:
                payloads.append(payload[:limit])
                payloads.extend(self._decompress_binary_payload(payload, limit))

            offset = end
            frames += 1

        if frames and offset == len(data):
            return payloads
        return []

    def _extract_proto_strings(self, data: bytes, limit: int) -> List[str]:
        strings = []
        max_field_len = min(8192, limit)

        for offset in range(0, max(0, len(data) - 2)):
            key, pos = self._read_binary_varint(data, offset, max_bytes=3)
            if key is None or key == 0 or key & 0x07 != 2:
                continue
            field_number = key >> 3
            if field_number <= 0 or field_number > 4096:
                continue
            length, pos = self._read_binary_varint(data, pos, max_bytes=5)
            if length is None or length < 4 or length > max_field_len or pos + length > len(data):
                continue

            chunk = data[pos: pos + length]
            try:
                text = chunk.decode("utf-8")
            except UnicodeDecodeError:
                continue
            strings.append(text)

        return strings

    def _binary_candidate_texts(self, body: bytes, scan_limit: int) -> List[str]:
        payloads = [body[:scan_limit]]
        payloads.extend(self._decompress_binary_payload(body[:scan_limit], scan_limit))
        payloads.extend(self._connect_frame_payloads(body[:scan_limit], scan_limit))

        for match in re.finditer(rb"\x1f\x8b", body[:scan_limit]):
            if len(payloads) >= 24:
                break
            payloads.extend(self._decompress_binary_payload(body[match.start():scan_limit], scan_limit))

        texts = []
        seen_payloads = set()
        for payload in payloads[:32]:
            if not payload:
                continue
            payload_key = hashlib.sha256(payload[:4096]).hexdigest()
            if payload_key in seen_payloads:
                continue
            seen_payloads.add(payload_key)

            for item in re.findall(rb"[\x09\x0a\x0d\x20-\x7e]{6,}", payload):
                texts.append(item.decode("utf-8", errors="ignore"))
            texts.extend(self._extract_proto_strings(payload, scan_limit))

        return texts

    def _clean_binary_candidate(self, text: str) -> str:
        text = text.replace(str(Path.home()), "~")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip(" \t\r\n'\"`")
        if not text:
            return ""

        lower = text.lower()
        action_markers = (
            "error", "fix", "debug", "root cause", "patch", "test", "failure",
            "failing", "implement", "improve", "update", "remove", "add",
            "regression", "issue", "problem", "without", "broken", "missing",
        )
        semantic_markers = (
            "error", "fix", "debug", "root cause", "patch", "test", "failure",
            "failing", "implement", "improve", "update", "remove", "add",
            "regression", "issue", "problem", "workspace", "file", "function",
            "class", "proxy", "provider", "unreachable", "stream", "http",
            "cert", "khoj", "integration", "protobuf", "connect", "binary",
            "gzip", "frame", "message", "request", "chat", "windsurf", "exa",
        )
        noise_markers = (
            "application/",
            "connect-go/",
            "grpc-",
            "authorization",
            "bearer ",
            "server.self-serve",
            "inferapi.",
            "product_analytics",
            "trajectory",
            "request_id",
            "user-agent",
            "content-type",
            "api_server_pb",
            "codeium",
        )
        has_action = any(marker in lower for marker in action_markers)
        has_semantic = has_action or any(marker in lower for marker in semantic_markers)
        if any(marker in lower for marker in noise_markers) and not has_action:
            return ""
        if re.fullmatch(r"[a-f0-9-]{16,}", lower):
            return ""
        if re.fullmatch(r"[A-Za-z0-9+/=_-]{40,}", text) and " " not in text:
            return ""

        words = re.findall(r"[A-Za-z][A-Za-z0-9_./+-]*", text)
        if len(words) < 3 and len(text) < 40:
            return ""
        if not has_semantic and len(words) < 5:
            return ""
        alpha_chars = sum(1 for char in text if char.isalpha())
        if alpha_chars < 8:
            return ""
        if len(text) > 300:
            text = text[:300].rsplit(" ", 1)[0] or text[:300]
        return text

    def _extract_binary_query(self, body: bytes, path: str = "") -> str:
        """Extract a bounded semantic query from Connect/protobuf bodies.

        This is intentionally passive. It gives Khoj enough text to retrieve
        nearby workspace context without mutating opaque protobuf frames.
        """
        if not body:
            return ""

        scan_limit = int(os.environ.get("HG_KHOJ_BINARY_SCAN_BYTES", "262144"))
        candidates = []
        for text in self._binary_candidate_texts(body, scan_limit):
            candidate = self._clean_binary_candidate(text)
            if candidate:
                candidates.append(candidate)

        if not candidates:
            return ""

        def score(text: str) -> Tuple[int, int, int]:
            lower = text.lower()
            keyword_score = sum(
                1
                for marker in (
                    "error", "fix", "debug", "root cause", "patch", "test",
                    "function", "class", "proxy", "provider", "unreachable",
                    "stream", "http", "cert", "khoj", "integration", "protobuf",
                    "connect", "binary", "gzip", "frame", "windsurf", "chat",
                )
                if marker in lower
            )
            word_count = len(re.findall(r"[A-Za-z][A-Za-z0-9_./+-]*", text))
            return keyword_score, min(word_count, 40), min(len(text), 300)

        ranked = sorted(dict.fromkeys(candidates), key=score, reverse=True)
        return " ".join(ranked[:3])[:500]
    
    def _minify_snippet(self, text: str) -> str:
        """Heuristic code minification to save tokens."""
        if not text: return text
        # Remove single-line comments (Python, C, JS, etc.)
        text = re.sub(r'#.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
        # Collapse multiple empty lines
        text = re.sub(r'\n{2,}', '\n', text)
        # Trim whitespace from lines
        text = "\n".join([line.rstrip() for line in text.splitlines() if line.strip()])
        return text

    def _to_snippets(self, results: Any, limit_chars: int = 800) -> List[str]:
        """Convert Khoj results to formatted snippets with distillation."""
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
            
            # OPSEC: Redact common path identifiers from snippets
            text = text.replace(str(Path.home()), "~")
            
            # Distillation pass (Token Reduction)
            is_code = any(source.endswith(ext) for ext in [".py", ".c", ".h", ".js", ".ts", ".sh", ".rs", ".go"])
            if is_code:
                text = self._minify_snippet(text)
            
            # Format snippet with source
            key = f"{source}:{text[:120]}"
            if key in seen:
                continue
            seen.add(key)
            snippet_sources.append(source)
            if self.inject_mode == "compact":
                source_label = Path(source).name or "unknown"
                text = re.sub(r"\s+", " ", text).strip()
                snippet = f"{source_label}: {text[:limit_chars]}"
                if len(text) > limit_chars:
                    snippet += "..."
            else:
                snippet = f"`{source}`\n{text[:limit_chars]}"
                if len(text) > limit_chars:
                    snippet += "..."
            if total_chars + len(snippet) > self.max_total_context_chars:
                break
            total_chars += len(snippet)
            snippets.append(snippet)
        self.last_snippet_sources = snippet_sources
        return snippets

    def _format_context_message(self, snippets: List[str]) -> str:
        if self.inject_mode == "off" or not snippets:
            return ""
        if self.inject_mode == "compact":
            return "KHOJ_CONTEXT:\n" + "\n".join(f"- {s}" for s in snippets)
        return (
            "# KHOJ SEMANTIC SEARCH CONTEXT\n"
            "Relevant code/documentation from indexed workspace:\n\n"
            + "\n\n".join(f"**{i+1}.** {s}" for i, s in enumerate(snippets))
        )

    def should_inject_binary_context(self, context_result: Dict[str, Any]) -> Tuple[bool, str]:
        """Keep live protobuf prompts from growing on repeated retries/continues."""
        if self.inject_mode == "off":
            self.binary_inject_disabled_skips += 1
            self.last_injection_status = "disabled"
            return False, "injection_mode_off"

        qhash = str(context_result.get("query_hash") or "")
        if not qhash:
            return True, "ok"

        now = time.time()
        expired = [
            key for key, seen_at in self.recent_binary_injections.items()
            if now - seen_at > self.binary_inject_ttl_s
        ]
        for key in expired:
            self.recent_binary_injections.pop(key, None)

        if qhash in self.recent_binary_injections:
            self.binary_inject_dedupe_skips += 1
            self.last_injection_status = "deduped"
            return False, "duplicate_query"

        self.recent_binary_injections[qhash] = now
        return True, "ok"

    async def get_binary_context(
        self,
        path: str,
        body: bytes,
        request_id: str = "",
        content_type: str = "",
        limit_chars: int = 400,
    ) -> Dict[str, Any]:
        """Retrieve Khoj context for Connect/protobuf work without mutating it."""
        if not self.enabled:
            self.last_passive_status = "disabled"
            return {"status": "disabled"}
        if self._cb_open():
            self.last_passive_status = "circuit_open"
            self._emit_trace("passive_blocked", path=path, status="circuit_open")
            return {"status": "circuit_open"}

        query = self._extract_binary_query(body, path)
        if not query:
            self.last_passive_status = "no_query"
            self._emit_trace("passive_no_query", path=path, content_type=content_type)
            return {"status": "no_query"}

        t0 = time.time()
        self.passive_lookup_count += 1
        qhash = hashlib.sha256(query.encode()).hexdigest()
        self.last_passive_query = query[:200]
        self.last_passive_query_hash = qhash[:16]

        result = await self.search(
            query,
            n=min(2, self.max_snippets),
            timeout_override=self.fast_timeout_s,
        )
        took = (time.time() - t0) * 1000.0
        self.last_passive_ms = took
        self.passive_latencies_ms.append(took)

        if result.get("status") != "ok":
            self.last_passive_status = result.get("status", "search_error")
            failure_detail = str(
                result.get("message")
                or result.get("code")
                or self.last_search_status
                or self.last_passive_status
            )
            self._emit_trace(
                "passive_search_failed",
                path=path,
                request_id=request_id,
                query=query[:200],
                query_hash=qhash[:16],
                status=self.last_passive_status,
                detail=failure_detail[:200],
                took_ms=round(took, 2),
            )
            return {
                "status": self.last_passive_status,
                "query": query[:100],
                "query_hash": qhash[:16],
                "message": failure_detail[:300],
                "search_status": self.last_search_status,
                "search_ms": round(took, 2),
            }

        snippets = self._to_snippets(result.get("results", []), limit_chars=limit_chars)
        self.last_passive_sources = self.last_snippet_sources[: self.max_snippets]
        self.last_passive_snippet_count = len(snippets)
        if snippets:
            self.passive_hit_count += 1
            self.last_passive_status = "ok"
        else:
            self.last_passive_status = "no_results"

        self._emit_trace(
            "passive_observe",
            path=path,
            request_id=request_id,
            query=query[:200],
            query_hash=qhash[:16],
            status=self.last_passive_status,
            snippets=len(snippets),
            sources=self.last_passive_sources,
            took_ms=round(took, 2),
        )
        return {
            "status": self.last_passive_status,
            "query": query[:500],
            "query_hash": qhash[:16],
            "snippets": len(snippets),
            "snippet_text": snippets,
            "context": self._format_context_message(snippets) if snippets else "",
            "sources": self.last_passive_sources,
            "search_ms": round(took, 2),
        }

    def store_binary_context(
        self,
        mode: str,
        path: str,
        context_result: Dict[str, Any],
        request_id: str = "",
        injected: bool = False,
    ) -> bool:
        return self._store_observation(
            mode=mode,
            path=path,
            query=context_result.get("query", ""),
            status=context_result.get("status", ""),
            snippets=context_result.get("snippet_text", []),
            sources=context_result.get("sources", []),
            request_id=request_id,
            injected=injected,
        )
    
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
        timeout_override = self.deep_timeout_s if deep_mode else self.fast_timeout_s
        
        # Search Khoj
        search_result = await self.search(query, timeout_override=timeout_override)
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
        if self.last_search_status == "idle":
            self.last_search_status = "ok"
        
        # Convert to snippets
        snippets = self._to_snippets(search_result.get("results", []))
        
        # Deep Intelligence Recovery: Try broad search if no results found
        if not snippets and len(query.split()) > 2:
            logger.info(f"KHOJ_RECOVERY: No results for {query!r}. Attempting broad search...")
            # Broaden query by removing small words and symbols
            broad_query = " ".join([w for w in re.sub(r'[^a-zA-Z0-9\s]', ' ', query).split() if len(w) > 3])
            if broad_query and broad_query != query:
                search_result = await self.search(broad_query, timeout_override=timeout_override)
                if search_result.get("status") == "ok":
                    snippets = self._to_snippets(search_result.get("results", []))
                    if snippets:
                        logger.info(f"KHOJ_RECOVERY_SUCCESS: Found {len(snippets)} snippets via broad query.")

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
        context_content = self._format_context_message(snippets)
        if not context_content:
            self.last_injection_status = "disabled"
            return {"status": "disabled"}
        context_msg = {
            "role": "system",
            "content": context_content
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
        stored = self._store_observation(
            mode="json_injection",
            path="messages",
            query=query,
            status="ok",
            snippets=snippets,
            sources=self.last_snippet_sources[: self.max_snippets],
            injected=True,
        )
        
        return {
            "status": "ok",
            "injected": len(snippets),
            "stored": stored,
            "query": query[:100],
            "search_ms": round(self.last_search_ms, 2),
            "inject_ms": round(self.last_injection_ms, 2),
            "sources": self.last_snippet_sources[: self.max_snippets],
        }

    async def observe_binary_request(
        self,
        path: str,
        body: bytes,
        request_id: str = "",
        content_type: str = "",
    ) -> Dict[str, Any]:
        """Run passive Khoj lookup for real Windsurf Connect/proto work.

        The live Cascade path is binary Connect/protobuf. Until protobuf schemas
        are available, this records retrieval context instead of altering the
        request body.
        """
        context_result = await self.get_binary_context(
            path=path,
            body=body,
            request_id=request_id,
            content_type=content_type,
            limit_chars=400,
        )
        if context_result.get("status") not in {"ok", "no_results"}:
            return {"status": context_result.get("status", "error"), "query": context_result.get("query", "")[:100]}
        stored = False
        if context_result.get("status") in {"ok", "no_results"}:
            stored = self.store_binary_context(
                mode="binary_passive",
                path=path,
                context_result=context_result,
                request_id=request_id,
                injected=False,
            )
        logger.info(
            "KHOJ_PASSIVE: status=%s snippets=%s stored=%s query_hash=%s path=%s",
            self.last_passive_status,
            context_result.get("snippets", 0),
            stored,
            context_result.get("query_hash", ""),
            path,
        )
        return {
            "status": self.last_passive_status,
            "query": context_result.get("query", "")[:100],
            "snippets": context_result.get("snippets", 0),
            "stored": stored,
            "sources": self.last_passive_sources,
            "search_ms": context_result.get("search_ms", 0),
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
        """Update Khoj content sources to include Windsurf workspaces.

        Khoj configures content sources via Django models (LocalMarkdownConfig,
        LocalPlaintextConfig, etc.), not via REST endpoints. The /api/content/computer
        endpoint only supports GET (returns list of indexed files).

        Strategy: Use PATCH /api/content with file uploads for direct content injection,
        or fall back to PUT /api/content to trigger re-indexing of DB-configured sources.
        """
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
        globs = [g.strip() for g in include_globs.split(",") if g.strip()]
        exclude_dirs = {
            ".git",
            ".hg_proxy_venv",
            ".venv",
            "__pycache__",
            "node_modules",
            "venv",
            "venv_production",
            "dist",
            "build",
            "tmp",
            "logs",
            "data",
            "kp14_cache",
            "windsurf_profiles",
        }
        env_excludes = os.environ.get("HG_KHOJ_EXCLUDE_DIRS", "")
        exclude_dirs.update({d.strip() for d in env_excludes.split(",") if d.strip()})
        max_file_bytes = int(os.environ.get("HG_KHOJ_MAX_FILE_BYTES", "524288"))
        max_files = int(os.environ.get("HG_KHOJ_MAX_FILES", "2000"))

        # Collect files matching globs from configured paths
        files_to_index = []
        for dir_path in existing_paths:
            p = Path(dir_path)
            if not p.is_dir():
                continue
            for glob_pattern in globs:
                for f in p.rglob(glob_pattern):
                    if not f.is_file():
                        continue
                    if any(part in exclude_dirs for part in f.parts):
                        continue
                    try:
                        if f.stat().st_size > max_file_bytes:
                            continue
                    except OSError:
                        continue
                    files_to_index.append(f)

        if len(files_to_index) > max_files:
            logger.warning(
                "Khoj index file cap applied: selected %s of %s files",
                max_files,
                len(files_to_index),
            )
            files_to_index = sorted(files_to_index, key=lambda item: str(item))[:max_files]

        if not files_to_index:
            logger.warning("No files found to index from configured paths")
            return False

        logger.info(f"Uploading {len(files_to_index)} files to Khoj for indexing")

        # Use PATCH /api/content to upload files directly (replaces existing content)
        # This works even when DB-based content sources aren't configured.
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Prepare multipart form data with file contents
                data = aiohttp.FormData()
                batch_size = int(os.environ.get("HG_KHOJ_INDEX_BATCH_SIZE", "50"))
                total_uploaded = 0

                for i in range(0, len(files_to_index), batch_size):
                    batch = files_to_index[i:i + batch_size]
                    data = aiohttp.FormData()
                    for f in batch:
                        try:
                            content = f.read_text(errors="ignore")
                            data.add_field(
                                "files",
                                content.encode("utf-8"),
                                filename=str(f),
                                content_type="text/plain",
                            )
                        except Exception as exc:
                            logger.debug(f"Skipping file {f}: {exc}")
                            continue

                    uploaded = False
                    for use_auth in self._auth_attempts():
                        async with session.patch(
                            f"{self.base_url}/api/content",
                            data=data,
                            headers=self._headers(include_content_type=False, use_auth=use_auth),
                        ) as resp:
                            if resp.status in [200, 201, 202]:
                                total_uploaded += len(batch)
                                logger.info(f"Indexed batch {i // batch_size + 1}: {len(batch)} files (status={resp.status})")
                                uploaded = True
                                break
                            if use_auth and resp.status in (401, 403, 500):
                                continue
                            body = await resp.text()
                            logger.warning(f"Content upload batch failed: {resp.status} body={body[:200]}")
                    if not uploaded:
                        # fallback trigger
                        async with session.get(
                            f"{self.base_url}/api/update",
                            params={"force": "true"},
                            headers=self._headers(include_content_type=False, use_auth=False),
                        ) as upd_resp:
                            if upd_resp.status in [200, 201, 202]:
                                logger.info("Re-index triggered via GET /api/update")
                                return True
                        return False

                logger.info(f"Content sources updated: {total_uploaded} files uploaded")
                return True
        except Exception as exc:
            logger.warning(f"Content source update error: {exc}")
            # Last resort: try PUT /api/content to re-index DB-configured sources
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    async with session.get(
                        f"{self.base_url}/api/update",
                        params={"force": "true"},
                        headers=self._headers(include_content_type=False, use_auth=False),
                    ) as resp:
                        if resp.status in [200, 201, 202]:
                            logger.info("Re-index triggered via GET /api/update fallback")
                            return True
            except Exception:
                pass
            return False
    
    async def trigger_reindex(self) -> bool:
        """Trigger workspace re-indexing (includes Windsurf workspaces).

        Khoj uses PUT /api/content to trigger indexing of DB-configured sources.
        The old /api/update and /api/index/update endpoints don't exist in current Khoj.
        """
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
                success = False
                detail = ""
                for use_auth in self._auth_attempts():
                    async with session.get(
                        f"{self.base_url}/api/update",
                        params={"force": "true"},
                        headers=self._headers(include_content_type=False, use_auth=use_auth),
                    ) as resp:
                        if resp.status in (200, 201, 202):
                            self.last_index_time = current_time
                            self.last_reindex_status = "ok"
                            self.last_reindex_detail = f"GET /api/update -> {resp.status}"
                            self.last_reindex_progress = {"state": "ok", "updated_at": int(time.time())}
                            logger.info("Workspace re-indexed successfully")
                            return True
                        if use_auth and resp.status in (401, 403, 500):
                            continue
                        body = await resp.text()
                        detail = f"GET /api/update -> {resp.status} {body[:200]}"
                        break
                if detail:
                    self.last_reindex_detail = detail

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
        observation_stats = self._observation_file_stats()
        injection_count = max(self.injection_count, int(observation_stats.get("observation_injection_count") or 0))
        passive_hit_count = max(self.passive_hit_count, int(observation_stats.get("observation_hit_count") or 0))
        stored_observation_count = max(self.stored_observation_count, int(observation_stats.get("observation_file_count") or 0))
        last_passive_status = self.last_passive_status
        last_passive_query = self.last_passive_query
        last_passive_query_hash = self.last_passive_query_hash
        last_passive_snippet_count = self.last_passive_snippet_count
        if last_passive_status == "idle" and observation_stats.get("last_observation_status"):
            last_passive_status = str(observation_stats.get("last_observation_status", "idle"))
            last_passive_query = str(observation_stats.get("last_observation_query", ""))
            last_passive_query_hash = str(observation_stats.get("last_observation_query_hash", ""))
            last_passive_snippet_count = int(observation_stats.get("last_observation_snippet_count") or 0)

        stats = {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "search_count": self.search_count,
            "injection_count": injection_count,
            "last_query": self.last_query[:200],
            "last_query_hash": self.last_query_hash[:16],
            "last_snippet_count": self.last_snippet_count,
            "last_snippet_sources": self.last_snippet_sources[: self.max_snippets],
            "last_search_status": self.last_search_status,
            "last_injection_status": self.last_injection_status,
            "last_passive_status": last_passive_status,
            "last_passive_query": last_passive_query[:200],
            "last_passive_query_hash": last_passive_query_hash[:16],
            "last_passive_sources": self.last_passive_sources[: self.max_snippets],
            "last_passive_snippet_count": last_passive_snippet_count,
            "passive_lookup_count": self.passive_lookup_count,
            "passive_hit_count": passive_hit_count,
            "store_observations": self.store_observations,
            "stored_observation_count": stored_observation_count,
            "last_store_status": self.last_store_status,
            "last_store_path": self.last_store_path,
            "last_index_time": self.last_index_time,
            "last_reindex_status": self.last_reindex_status,
            "last_reindex_detail": self.last_reindex_detail,
            "reindex_progress": self.last_reindex_progress,
            "last_search_ms": round(self.last_search_ms, 2),
            "last_injection_ms": round(self.last_injection_ms, 2),
            "last_passive_ms": round(self.last_passive_ms, 2),
            "search_latency_ms": {
                "p50": pct(list(self.search_latencies_ms), 50),
                "p95": pct(list(self.search_latencies_ms), 95),
            },
            "injection_latency_ms": {
                "p50": pct(list(self.injection_latencies_ms), 50),
                "p95": pct(list(self.injection_latencies_ms), 95),
            },
            "passive_latency_ms": {
                "p50": pct(list(self.passive_latencies_ms), 50),
                "p95": pct(list(self.passive_latencies_ms), 95),
            },
            "empty_result_count": self.empty_result_count,
            "error_reasons": self.search_error_reasons,
            "injection_mode": self.inject_mode,
            "context_budget_chars": self.max_total_context_chars,
            "cache_entries": len(self.query_cache),
            "search_cache_hits": self.search_cache_hit_count,
            "binary_inject_dedupe_skips": self.binary_inject_dedupe_skips,
            "binary_inject_disabled_skips": self.binary_inject_disabled_skips,
            "recent_binary_injections": len(self.recent_binary_injections),
            "circuit_open": self._cb_open(),
            "circuit_open_until": int(self.cb_open_until) if self.cb_open_until else 0,
        }
        stats.update(observation_stats)
        stats["acceleration"] = self._acceleration_stats()
        return stats
