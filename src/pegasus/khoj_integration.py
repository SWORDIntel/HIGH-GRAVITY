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
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class PegasusKhojBridge:
    """Enhanced Khoj integration with Pegasus features"""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.enabled = self._check_enabled()
        self.base_url = os.environ.get("HG_KHOJ_URL", "http://127.0.0.1:42110").rstrip("/")
        self.token = os.environ.get("HG_KHOJ_TOKEN", "").strip()
        self.timeout_s = float(os.environ.get("HG_KHOJ_TIMEOUT_SECONDS", "4"))
        self.default_n = int(os.environ.get("HG_KHOJ_TOP_K", "4"))
        
        # Statistics
        self.search_count = 0
        self.injection_count = 0
        self.last_index_time = 0.0
        self.index_interval = 300  # 5 minutes
        
        logger.info(f"PegasusKhojBridge initialized: enabled={self.enabled}, url={self.base_url}")
    
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
        
        try:
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
                        return {"status": "ok", "results": data}
                    else:
                        return {"status": "error", "code": resp.status}
        except Exception as exc:
            logger.debug(f"Khoj search error: {exc}")
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
        
        if not results:
            return snippets
        
        # Handle different result formats
        if isinstance(results, list):
            items = results
        elif isinstance(results, dict):
            items = results.get("results", [])
        else:
            return snippets
        
        for item in items[:self.default_n]:
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
            snippet = f"`{source}`\n{text[:limit_chars]}"
            if len(text) > limit_chars:
                snippet += "..."
            
            snippets.append(snippet)
        
        return snippets
    
    async def inject_context(self, messages: List[Dict]) -> Dict[str, Any]:
        """Inject Khoj search context into messages"""
        if not self.enabled:
            return {"status": "disabled"}
        
        # Extract query from messages
        query = self._extract_query(messages)
        if not query:
            return {"status": "no_query"}
        
        # Search Khoj
        search_result = await self.search(query)
        if search_result.get("status") != "ok":
            return search_result
        
        # Convert to snippets
        snippets = self._to_snippets(search_result.get("results", []))
        if not snippets:
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
        
        return {
            "status": "ok",
            "injected": len(snippets),
            "query": query[:100]
        }
    
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
        
        payload = {
            "name": "HIGH-GRAVITY + Windsurf Workspaces",
            "input_files": existing_paths,
            "input_filter": [
                "*.py", "*.md", "*.txt", "*.json", "*.yaml", "*.yml",
                "*.sh", "*.c", "*.cpp", "*.h", "*.rs", "*.go", "*.js", "*.ts",
                "*.jsx", "*.tsx", "*.java", "*.kt", "*.swift", "*.rb"
            ],
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
        
        # Update content sources first to include any new Windsurf workspaces
        await self.update_content_sources()
        
        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/api/update",
                    headers=self._headers()
                ) as resp:
                    if resp.status == 200:
                        self.last_index_time = current_time
                        logger.info("Workspace re-indexed successfully (including Windsurf workspaces)")
                        return True
                    else:
                        logger.warning(f"Re-index failed: {resp.status}")
                        return False
        except Exception as exc:
            logger.warning(f"Re-index error: {exc}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "search_count": self.search_count,
            "injection_count": self.injection_count,
            "last_index_time": self.last_index_time,
        }
