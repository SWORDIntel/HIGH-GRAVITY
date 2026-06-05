#!/usr/bin/env python3
"""HIGH-GRAVITY end-to-end environment and integration audit.

Name: hg_e2e_audit.py | Version: v1.0.0
Purpose: inventory runtime dependencies, execute non-destructive integration
checks, and write chain-of-custody JSON/Markdown reports under logs/audit/.

The audit is intentionally observe-only: it does not install packages, mutate
system routing, or start privileged live services. Local microproxy smoke checks
use localhost fixture traffic only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

VERSION = "1.1.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = REPO_ROOT / "logs" / "audit"

REQUIRED_IMPORTS: Sequence[Tuple[str, str, str, bool]] = (
    ("rich", "rich", "requirements.txt", True),
    ("fastapi", "fastapi", "requirements.txt", True),
    ("uvicorn", "uvicorn", "requirements.txt", True),
    ("hypercorn", "hypercorn", "requirements.txt", True),
    ("h2", "h2", "requirements.txt", True),
    ("aiohttp", "aiohttp", "requirements.txt", True),
    ("requests", "requests", "requirements.txt", True),
    ("pyyaml", "yaml", "requirements.txt", True),
    ("numpy", "numpy", "requirements-accelerated.txt", False),
    ("psutil", "psutil", "requirements-accelerated.txt", False),
    ("rich", "rich", "tools/antigravity_three_account/requirements.txt", True),
)

TOOL_CHECKS: Sequence[Tuple[str, Sequence[str], bool]] = (
    ("bash", ("bash", "--version"), True),
    ("python3", ("python3", "--version"), True),
    ("make", ("make", "--version"), True),
    ("cc", ("cc", "--version"), True),
    ("curl", ("curl", "--version"), False),
    ("jq", ("jq", "--version"), False),
    ("shellcheck", ("shellcheck", "--version"), False),
    ("pip-audit", ("pip-audit", "--version"), False),
    ("docker", ("docker", "--version"), False),
    ("xl", ("xl", "info"), False),
    ("zfs", ("zfs", "version"), False),
    ("aria2c", ("aria2c", "--version"), False),
)

FOCUSED_COMMANDS: Sequence[Tuple[str, Sequence[str], int, bool]] = (
    ("python_compile_antigravity_tools", ("python3", "-m", "py_compile", "tools/antigravity_three_account/ag-streams.py", "tools/antigravity_three_account/agy-rotate.py"), 30, True),
    ("python_compile_proxy_dashboard", ("python3", "-m", "py_compile", "src/proxy.py", "src/hg_dashboard.py"), 60, True),
    ("shell_syntax", ("bash", "-n", "agy.sh", "hg.sh", "scripts/internal/hg_start.sh", "scripts/internal/hg_antigravity.sh", "scripts/internal/hg_microproxy.sh", "scripts/internal/hg_status.sh"), 30, True),
    ("microproxy_build_check", ("make", "-C", "src/microproxy", "check"), 60, True),
    ("antigravity_stream_paths", ("./hg.sh", "antigravity", "streams", "paths"), 60, True),
    ("antigravity_stream_summary", ("./hg.sh", "antigravity", "streams", "summary", "--json"), 60, True),
    ("microproxy_smoke", ("./hg.sh", "microproxy", "smoke"), 90, True),
    ("microproxy_events_unit", ("python3", "-m", "unittest", "tests/test_microproxy_events.py"), 60, True),
    ("microproxy_status_unit", ("python3", "-m", "unittest", "tests/test_microproxy_status.py"), 60, True),
    ("microproxy_edge_unit", ("python3", "-m", "unittest", "tests/test_microproxy_edge.py"), 120, True),
    ("acceleration_fallback_unit", ("python3", "-m", "unittest", "tests/test_acceleration_fallback.py"), 60, True),
    ("agy_root_launcher_unit", ("python3", "-m", "unittest", "tests/test_agy_launcher.py"), 60, True),
    ("flow_log_unit", ("python3", "-m", "unittest", "tests/test_flow_log.py"), 60, True),
    ("decrypted_flow_proxy_unit", ("python3", "-m", "unittest", "tests/test_decrypted_flow_proxy.py"), 60, True),
    ("antigravity_paths_unit", ("python3", "-m", "unittest", "tests/test_antigravity_paths.py"), 60, True),
    ("antigravity_streams_unit", ("python3", "-m", "unittest", "tests/test_antigravity_streams.py"), 60, True),
    ("e2e_audit_unit", ("python3", "-m", "unittest", "tests/test_e2e_audit.py"), 60, True),
)

FULL_COMMANDS: Sequence[Tuple[str, Sequence[str], int, bool]] = (
    ("full_unittest_discover", ("python3", "-m", "unittest", "discover", "-s", "tests"), 240, True),
)

STATIC_PATTERNS: Sequence[Tuple[str, Sequence[str], bool]] = (
    ("unsafe_python_exec", ("rg", "-n", r"\bexec\(", "src", "tools", "scripts", "tests"), False),
    ("unsafe_python_eval", ("rg", "-n", r"\beval\(", "src", "tools", "scripts", "tests"), False),
    ("pickle_loads", ("rg", "-n", r"pickle\.loads|pickle\.load", "src", "tools", "scripts", "tests"), False),
    ("yaml_load_without_safe_loader", ("rg", "-n", r"yaml\.load\(", "src", "tools", "scripts", "tests"), False),
    ("microproxy_mutation_or_credential_markers", ("rg", "-n", r"inject_api_key|inject_shadow_profile|patch_protobuf_stream|Authorization: Bearer|HG_API_KEYS", "src/microproxy", "scripts/internal/hg_microproxy.sh"), True),
)


@dataclass
class CommandResult:
    name: str
    command: List[str]
    required: bool
    ok: bool
    returncode: Optional[int]
    duration_ms: int
    stdout_tail: str
    stderr_tail: str
    error: Optional[str] = None
    diagnostics: Optional[List[str]] = None


def command_diagnostics(stdout: str, stderr: str) -> List[str]:
    """Extract stable unittest failure/error identifiers from command output."""

    diagnostics: List[str] = []
    for line in f"{stdout}\n{stderr}".splitlines():
        match = re.match(r"^(?:FAIL|ERROR):\s+(.+)$", line.strip())
        if match and match.group(1) not in diagnostics:
            diagnostics.append(match.group(1))
    return diagnostics


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def tail_text(value: str, limit: int = 6000) -> str:
    if len(value) <= limit:
        return value
    return value[-limit:]


def sha256_file(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(name: str, command: Sequence[str], timeout: int, required: bool) -> CommandResult:
    start = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            env={**os.environ, "HG_NON_INTERACTIVE": "1"},
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(
            name=name,
            command=list(command),
            required=required,
            ok=completed.returncode == 0,
            returncode=completed.returncode,
            duration_ms=duration_ms,
            stdout_tail=tail_text(completed.stdout),
            stderr_tail=tail_text(completed.stderr),
            diagnostics=command_diagnostics(completed.stdout, completed.stderr),
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(
            name=name,
            command=list(command),
            required=required,
            ok=False,
            returncode=None,
            duration_ms=duration_ms,
            stdout_tail=tail_text(exc.stdout or ""),
            stderr_tail=tail_text(exc.stderr or ""),
            error=f"timeout after {timeout}s",
        )
    except OSError as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(
            name=name,
            command=list(command),
            required=required,
            ok=False,
            returncode=None,
            duration_ms=duration_ms,
            stdout_tail="",
            stderr_tail="",
            error=str(exc),
        )


def dependency_status() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for distribution, import_name, source, required in REQUIRED_IMPORTS:
        import_present = importlib.util.find_spec(import_name) is not None
        version = None
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            pass
        rows.append({
            "distribution": distribution,
            "import_name": import_name,
            "source": source,
            "required": required,
            "present": import_present,
            "version": version,
        })
    return rows


def tool_status() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for tool, version_command, required in TOOL_CHECKS:
        path = shutil.which(tool)
        result: Optional[CommandResult] = None
        if path:
            result = run_command(f"tool_{tool}", version_command, 10, required)
        rows.append({
            "tool": tool,
            "path": path,
            "required": required,
            "present": path is not None,
            "version_probe": asdict(result) if result else None,
        })
    return rows


def static_scan() -> List[CommandResult]:
    results: List[CommandResult] = []
    for name, command, expect_no_matches in STATIC_PATTERNS:
        result = run_command(name, command, 30, True)
        if expect_no_matches:
            result.ok = result.returncode == 1
        else:
            result.ok = result.returncode in {0, 1}
        results.append(result)
    return results


def command_plan(full: bool, skip_smoke: bool) -> List[Tuple[str, Sequence[str], int, bool]]:
    planned = list(FOCUSED_COMMANDS)
    if skip_smoke:
        planned = [item for item in planned if item[0] != "microproxy_smoke"]
    if full:
        planned.extend(FULL_COMMANDS)
    return planned


def write_markdown(report: Dict[str, Any], markdown_path: Path) -> None:
    lines = [
        f"# HIGH-GRAVITY E2E Audit Report",
        "",
        f"* Generated: `{report['generated_at']}`",
        f"* Overall status: `{'PASS' if report['ok'] else 'FAIL'}`",
        f"* Commit: `{report['git'].get('head', 'unknown')}`",
        "",
        "## Dependency Inventory",
        "",
        "| Dependency | Import | Required | Present | Version | Source |",
        "|---|---|---:|---:|---|---|",
    ]
    for dep in report["dependencies"]:
        lines.append(f"| `{dep['distribution']}` | `{dep['import_name']}` | `{dep['required']}` | `{dep['present']}` | `{dep.get('version') or ''}` | `{dep['source']}` |")
    lines.extend(["", "## Command Results", "", "| Check | Required | OK | Return | Duration ms |", "|---|---:|---:|---:|---:|"])
    for result in report["commands"]:
        lines.append(f"| `{result['name']}` | `{result['required']}` | `{result['ok']}` | `{result.get('returncode')}` | `{result['duration_ms']}` |")
    lines.extend(["", "## Static/Security Scans", "", "| Scan | OK | Return |", "|---|---:|---:|"])
    for result in report["static_scans"]:
        lines.append(f"| `{result['name']}` | `{result['ok']}` | `{result.get('returncode')}` |")
    lines.extend(["", "## Command Diagnostics", ""])
    diagnostic_rows = [
        (result["name"], item)
        for result in report["commands"]
        for item in (result.get("diagnostics") or [])
    ]
    if diagnostic_rows:
        for name, item in diagnostic_rows:
            lines.append(f"* `{name}`: `{item}`")
    else:
        lines.append("* None")
    lines.extend(["", "## Failed Required Checks", ""])
    failed = report.get("failed_required", [])
    if failed:
        for item in failed:
            lines.append(f"* `{item}`")
    else:
        lines.append("* None")
    lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def git_info() -> Dict[str, Any]:
    head = run_command("git_head", ("git", "rev-parse", "--short", "HEAD"), 10, False)
    status = run_command("git_status", ("git", "status", "--short"), 10, False)
    return {
        "head": head.stdout_tail.strip(),
        "dirty": bool(status.stdout_tail.strip()),
        "status_short": status.stdout_tail,
    }


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    commands = [run_command(name, command, timeout, required) for name, command, timeout, required in command_plan(args.full, args.skip_smoke)]
    scans = static_scan() if not args.skip_static else []
    deps = dependency_status()
    tools = tool_status()
    required_failures = [item.name for item in commands if item.required and not item.ok]
    required_failures.extend([f"dependency:{item['distribution']}" for item in deps if item["required"] and not item["present"]])
    required_failures.extend([f"tool:{item['tool']}" for item in tools if item["required"] and not item["present"]])
    required_failures.extend([f"static:{item.name}" for item in scans if item.required and not item.ok])
    microproxy_bin = REPO_ROOT / "src" / "microproxy" / "build" / "hg-edge"
    return {
        "schema_version": 1,
        "tool": "hg_e2e_audit.py",
        "tool_version": VERSION,
        "generated_at": utc_now(),
        "ok": not required_failures,
        "failed_required": required_failures,
        "failed_checks": [item.name for item in commands if not item.ok],
        "system": {
            "platform": platform.platform(),
            "python": sys.version.replace("\n", " "),
            "executable": sys.executable,
            "cwd": str(REPO_ROOT),
            "kernel": platform.release(),
            "machine": platform.machine(),
        },
        "git": git_info(),
        "dependencies": deps,
        "tools": tools,
        "artifacts": {
            "microproxy_bin": str(microproxy_bin),
            "microproxy_bin_sha256": sha256_file(microproxy_bin),
        },
        "commands": [asdict(item) for item in commands],
        "static_scans": [asdict(item) for item in scans],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run HIGH-GRAVITY E2E environment/dependency audit.")
    parser.add_argument("--full", action="store_true", help="Also run strict full unittest discovery; any failure fails the audit.")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip localhost microproxy smoke traffic.")
    parser.add_argument("--skip-static", action="store_true", help="Skip rg-based static/security marker scans.")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--no-fail", action="store_true", help="Always exit 0 after writing reports.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = build_report(args)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = args.report_dir / f"hg_e2e_audit_{stamp}.json"
    md_path = args.report_dir / f"hg_e2e_audit_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report, md_path)
    print(json.dumps({
        "ok": report["ok"],
        "failed_required": report["failed_required"],
        "json_report": str(json_path),
        "markdown_report": str(md_path),
    }, indent=2, sort_keys=True))
    if args.no_fail:
        return 0
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
