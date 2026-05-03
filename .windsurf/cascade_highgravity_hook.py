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
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


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


TRACE_LOG_PATH = REPO_ROOT / "logs" / "cascade_hook_trace.jsonl"
TRACE_SUMMARY_PATH = REPO_ROOT / "logs" / "cascade_midway.log"


def _is_truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _trace_enabled():
    if (REPO_ROOT / "logs" / "cascade_trace.enabled").exists():
        return True
    return any(
        _is_truthy(os.environ.get(name))
        for name in ("HIGHGRAVITY_CASCADE_TRACE", "CASCADE_TRACE", "HG_TRACE")
    )


def _pick_first(mapping, keys):
    for key in keys:
        value = mapping.get(key)
        if value not in {None, ""}:
            return value
    return None


def build_trace_record(stage, hook_input, payload=None, returncode=None, note=None):
    tool_info = hook_input.get("tool_info")
    if not isinstance(tool_info, dict):
        tool_info = {}

    variables = tool_info.get("variables")
    if not isinstance(variables, dict):
        variables = {}

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "stage": stage,
        "agent_action_name": hook_input.get("agent_action_name"),
        "trajectory_id": hook_input.get("trajectory_id"),
        "execution_id": hook_input.get("execution_id"),
        "tool_info_keys": sorted(tool_info.keys()),
        "variable_keys": sorted(variables.keys()),
        "file_uri": _pick_first(hook_input, ("file_uri", "fileUri", "uri", "path")),
        "command_line": _pick_first(tool_info, ("command_line", "commandLine", "command")),
        "mode": variables.get("mode"),
        "provider": variables.get("provider"),
        "proxyUrl": variables.get("proxyUrl"),
        "windowName": variables.get("windowName"),
        "dryRun": variables.get("dryRun"),
    }
    if returncode is not None:
        record["returncode"] = returncode
    if note:
        record["note"] = note
    if payload is not None:
        record["payload_keys"] = sorted(payload.keys())
    return record


def emit_trace(stage, hook_input, payload=None, returncode=None, note=None):
    if not _trace_enabled():
        return

    record = build_trace_record(
        stage,
        hook_input,
        payload=payload,
        returncode=returncode,
        note=note,
    )

    try:
        TRACE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TRACE_LOG_PATH, "a", encoding="utf-8") as trace_file:
            trace_file.write(json.dumps(record, sort_keys=True) + "\n")
    except Exception:
        pass

    try:
        TRACE_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TRACE_SUMMARY_PATH, "a", encoding="utf-8") as summary_file:
            summary_file.write(
                "[CASCADE TRACE] "
                f"stage={stage} "
                f"action={record['agent_action_name'] or 'unknown'} "
                f"trajectory={record['trajectory_id'] or 'unknown'} "
                f"file={record['file_uri'] or 'unknown'} "
                f"mode={record['mode'] or 'unknown'} "
                f"provider={record['provider'] or 'unknown'} "
                f"proxy={record['proxyUrl'] or 'unknown'} "
                f"returncode={returncode if returncode is not None else 'n/a'}"
                "\n"
            )
    except Exception:
        pass


def main():
    hook_input = json.load(sys.stdin)
    repo_root = Path(__file__).resolve().parent.parent
    launcher = repo_root / "bin" / "gemini_session_launcher.py"

    emit_trace("receive", hook_input, note="cascade hook input received")
    payload = build_payload(hook_input)
    emit_trace("forward", hook_input, payload=payload, note="forwarding to gemini_session_launcher")

    result = subprocess.run(
        [sys.executable, str(launcher), "--stdin-format", "json"],
        input=json.dumps(payload),
        text=True,
        cwd=repo_root,
        env=os.environ.copy(),
    )
    emit_trace("exit", hook_input, payload=payload, returncode=result.returncode, note="launcher completed")
    raise SystemExit(result.returncode)

if __name__ == "__main__":
    main()
