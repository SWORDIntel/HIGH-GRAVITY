#!/usr/bin/env python3
"""
Bridge Windsurf Cascade hook stdin into gemini_session_launcher.py.

This lets workspace hooks feed native Cascade JSON into the launcher while
supplying default integration settings through environment variables.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def build_payload(hook_input):
    tool_info = hook_input.get("tool_info")
    if not isinstance(tool_info, dict):
        tool_info = {}

    variables = tool_info.get("variables")
    if not isinstance(variables, dict):
        variables = {}

    merged_variables = dict(variables)

    env_aliases = {
        "apiKey": ["HIGHGRAVITY_API_KEY", "WINDSURF_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"],
        "keyIndex": ["HIGHGRAVITY_KEY_INDEX"],
        "mode": ["HIGHGRAVITY_MODE"],
        "provider": ["HIGHGRAVITY_PROVIDER"],
        "proxyUrl": ["HIGHGRAVITY_PROXY_URL", "OPENAI_BASE_URL", "OPENAI_API_BASE"],
        "model": ["HIGHGRAVITY_MODEL"],
        "windowName": ["HIGHGRAVITY_WINDOW_NAME"],
        "monitor": ["HIGHGRAVITY_MONITOR"],
        "check": ["HIGHGRAVITY_CHECK"],
        "dryRun": ["HIGHGRAVITY_DRY_RUN"],
        "newWindow": ["HIGHGRAVITY_NEW_WINDOW"],
    }

    for dest, names in env_aliases.items():
        if merged_variables.get(dest) not in {None, ""}:
            continue
        for name in names:
            value = os.environ.get(name)
            if value not in {None, ""}:
                merged_variables[dest] = value
                break

    if "mode" not in merged_variables:
        merged_variables["mode"] = "windsurf"
    if "provider" not in merged_variables:
        merged_variables["provider"] = "proxy"
    if "proxyUrl" not in merged_variables:
        merged_variables["proxyUrl"] = "http://localhost:9999"
    if "dryRun" not in merged_variables:
        merged_variables["dryRun"] = True

    merged_tool_info = dict(tool_info)
    merged_tool_info["variables"] = merged_variables

    payload = dict(hook_input)
    payload["tool_info"] = merged_tool_info
    return payload


def main():
    hook_input = json.load(sys.stdin)
    repo_root = Path(__file__).resolve().parent.parent
    launcher = repo_root / "launcher.py"

    payload = build_payload(hook_input)

    result = subprocess.run(
        [sys.executable, str(launcher), "--stdin-format", "json"],
        input=json.dumps(payload),
        text=True,
        cwd=repo_root,
        env=os.environ.copy(),
    )
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
