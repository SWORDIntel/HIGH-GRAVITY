#!/usr/bin/env python3
"""
Automated "Wire-In" script for HIGH-GRAVITY.
Detects running Windsurf session and deploys hooks/profiles.
"""

import os
import sys
import json
import re
import subprocess
import shutil
from pathlib import Path

# Base configuration
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KEYS_FILE = REPO_ROOT / "config" / "gemini_keys.json"

def get_running_windsurf_session():
    """Detects running Windsurf Next instance and its workspace."""
    try:
        ps_output = subprocess.check_output(["ps", "aux"], text=True)
        # Look for the language server process which contains workspace_id
        lsp_match = re.search(r'language_server_linux_x64.*--workspace_id\s+([^\s]+)', ps_output)
        if not lsp_match:
            return None
        
        workspace_id = lsp_match.group(1)
        # Re-scan to get the full command line for other params
        for line in ps_output.splitlines():
            if workspace_id in line and "language_server" in line:
                api_server_url = re.search(r'--api_server_url\s+([^\s]+)', line)
                inference_url = re.search(r'--inference_api_server_url\s+([^\s]+)', line)
                return {
                    "workspace_id": workspace_id,
                    "api_server_url": api_server_url.group(1) if api_server_url else None,
                    "inference_api_server_url": inference_url.group(1) if inference_url else None,
                    "full_command": line
                }
    except Exception as e:
        print(f"[!] Error detecting Windsurf session: {e}")
    return None

def resolve_workspace_path(workspace_id):
    """Maps workspace_id to a real filesystem path using storage.json."""
    storage_json = Path.home() / ".config" / "Windsurf - Next" / "User" / "globalStorage" / "storage.json"
    if not storage_json.exists():
        return None
    
    try:
        with open(storage_json) as f:
            data = json.load(f)
            # Collect all known folders
            folders = []
            for folder in data.get("backupWorkspaces", {}).get("folders", []):
                uri = folder.get("folderUri", "")
                if uri.startswith("file://"):
                    folders.append(uri[len("file://"):])
            for uri in data.get("profileAssociations", {}).get("workspaces", {}):
                if uri.startswith("file://"):
                    folders.append(uri[len("file://"):])
            
            # Match workspace_id to path
            # Example: file_home_john_W_SLAM matches /home/john/W-SLAM
            for path in set(folders):
                # Normalize both for comparison
                norm_path = path.lower().replace("/", "_").replace("-", "_")
                norm_id = workspace_id.lower().replace("-", "_")
                if norm_id.endswith(norm_path) or norm_path.endswith(norm_id.replace("file_", "")):
                    return path
                # Try last component match
                if Path(path).name.lower() in workspace_id.lower():
                    return path
    except Exception as e:
        print(f"[!] Error reading storage.json: {e}")
    return None

def get_api_key():
    """Extracts the first active key from config/gemini_keys.json."""
    if not KEYS_FILE.exists():
        return None
    try:
        with open(KEYS_FILE) as f:
            data = json.load(f)
            for key_data in data.get("keys", []):
                if key_data.get("status") == "active":
                    return key_data["key"]
    except Exception:
        pass
    return None

def wire_in():
    print("[*] Detecting running Windsurf session...")
    session = get_running_windsurf_session()
    if not session:
        print("[!] No active Windsurf Next session found.")
        return

    workspace_id = session["workspace_id"]
    print(f"[+] Found session: {workspace_id}")
    
    workspace_path = resolve_workspace_path(workspace_id)
    if not workspace_path:
        # Fallback to heuristic guess if storage.json didn't help
        if workspace_id.startswith("file_"):
            workspace_path = "/" + workspace_id[5:].replace("_", "/")
        else:
            print(f"[!] Could not resolve path for workspace: {workspace_id}")
            return
    
    if not os.path.exists(workspace_path):
        print(f"[!] Resolved path does not exist: {workspace_path}")
        return

    print(f"[+] Workspace path: {workspace_path}")
    
    api_key = get_api_key()
    if not api_key:
        print("[!] No active Gemini API key found in config/gemini_keys.json")
        return

    # 1. Create Windsurf profile in HIGH-GRAVITY
    print("[*] Creating HIGH-GRAVITY profile...")
    launcher = REPO_ROOT / "tools/integration" / "gemini_session_launcher.py"
    subprocess.run([
        sys.executable, str(launcher),
        "--api-key", api_key,
        "--window-name", workspace_id,
        "--mode", "windsurf",
        "--provider", "proxy",
        "--proxy-url", "http://localhost:9999"
    ], check=True)

    # 2. Deploy hooks to the target workspace
    print(f"[*] Deploying HIGH-GRAVITY hooks to {workspace_path}...")
    target_windsurf = Path(workspace_path) / ".windsurf"
    target_windsurf.mkdir(parents=True, exist_ok=True)
    
    hooks_json = REPO_ROOT / ".windsurf" / "hooks.json"
    hook_py = REPO_ROOT / ".windsurf" / "cascade_highgravity_hook.py"
    
    shutil.copy2(hooks_json, target_windsurf / "hooks.json")
    
    # Customize the Python hook to point to the absolute path of the launcher
    with open(hook_py) as f:
        content = f.read()
    
    # Point to the current HIGH-GRAVITY installation
    content = content.replace(
        "REPO_ROOT = Path(__file__).resolve().parent.parent",
        f"REPO_ROOT = Path(\"{REPO_ROOT}\")"
    )
    
    with open(target_windsurf / "cascade_highgravity_hook.py", "w") as f:
        f.write(content)
    
    (target_windsurf / "cascade_highgravity_hook.py").chmod(0o755)
    
    print("\n[✓] HIGH-GRAVITY successfully wired in.")
    print(f"    - Workspace: {workspace_path}")
    print(f"    - Profile:   {workspace_id}")
    print(f"    - Hooks:     {target_windsurf}")
    print("\nTrigger a Cascade action in Windsurf to activate.")

if __name__ == "__main__":
    wire_in()
