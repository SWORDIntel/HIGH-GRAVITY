#!/usr/bin/env python3
# Name: agy-rotate.py | Version: v1.1.0
# Purpose: Rich, resumable, cooldown-aware Antigravity CLI wrapper for three authorized accounts.
# Features: Rich status UI, JSON state, timeout rotation, resume markers, permissive settings bootstrap.

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = Path(os.environ.get("AGY_CONFIG", "~/.config/high-gravity/antigravity/accounts.json")).expanduser()
DEFAULT_STATE_DIR = Path(os.environ.get("AGY_STATE_DIR", "~/.local/state/high-gravity/antigravity")).expanduser()
DEFAULT_TIMEOUT_PATTERNS = [
    "rate limit",
    "quota exceeded",
    "usage limit",
    "429",
    "resource_exhausted",
    "try again in",
    "temporarily unavailable for this model",
]
PERMISSIVE_ALLOW_LIST = ["read_file(*)", "write_file(*)", "command(*)", "read_url(*)"]


@dataclass
class RunResult:
    return_code: int
    output: str
    log_path: Path
    timed_out: bool
    reset_at: datetime | None


def rich_available(disabled: bool) -> bool:
    return not disabled and importlib.util.find_spec("rich") is not None


def console_print(message: str, *, style: str | None = None, plain: bool = False) -> None:
    if rich_available(plain):
        from rich.console import Console

        Console().print(message, style=style)
    else:
        print(re.sub(r"\[[/?a-zA-Z0-9_ #=.-]+\]", "", message))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)
    path.chmod(0o600)


def load_config(path: Path) -> dict[str, Any]:
    config = load_json(path, {})
    accounts = config.get("accounts", [])
    if not accounts:
        raise SystemExit(f"No accounts configured in {path}. Run setup.sh first.")
    names = [account.get("name") for account in accounts]
    if len(names) != len(set(names)):
        raise SystemExit("Account names must be unique.")
    return config


def default_state() -> dict[str, Any]:
    return {
        "version": 2,
        "current_account": None,
        "cooldowns": {},
        "events": [],
        "active_run": None,
        "last_command": None,
        "runs": {},
    }


def account_cooldown(state: dict[str, Any], account_name: str, model: str) -> datetime | None:
    account_state = state.get("cooldowns", {}).get(account_name, {})
    return parse_iso(account_state.get(model) or account_state.get("*"))


def model_allowed(account: dict[str, Any], model: str) -> bool:
    models = account.get("models") or ["*"]
    return "*" in models or model in models


def choose_account(
    config: dict[str, Any], state: dict[str, Any], model: str, forced: str | None, blocked: set[str] | None = None
) -> dict[str, Any]:
    blocked = blocked or set()
    accounts = config["accounts"]
    if forced:
        for account in accounts:
            if account["name"] == forced:
                return account
        raise SystemExit(f"Forced account {forced!r} is not in config.")

    current = state.get("current_account")
    ordered = sorted(accounts, key=lambda item: item["name"] != current)
    now = utc_now()
    eligible: list[dict[str, Any]] = []
    for account in ordered:
        if account["name"] in blocked:
            continue
        if not model_allowed(account, model):
            continue
        reset_at = account_cooldown(state, account["name"], model)
        if reset_at and reset_at > now:
            continue
        eligible.append(account)
    if eligible:
        return eligible[0]

    soonest: tuple[datetime, str] | None = None
    for account in accounts:
        reset_at = account_cooldown(state, account["name"], model)
        if reset_at and (soonest is None or reset_at < soonest[0]):
            soonest = (reset_at, account["name"])
    if soonest:
        raise SystemExit(f"No eligible account for {model}; soonest reset is {soonest[1]} at {iso(soonest[0])}.")
    raise SystemExit(f"No eligible account supports model {model!r}.")


def expand_path(value: str) -> str:
    return str(Path(os.path.expandvars(value)).expanduser())


def profile_dir(account: dict[str, Any]) -> Path:
    return Path(expand_path(str(account["profile_dir"])))


def antigravity_settings_path(account: dict[str, Any]) -> Path:
    return profile_dir(account) / ".gemini" / "antigravity-cli" / "settings.json"


def merged_permissions(existing: dict[str, Any], config: dict[str, Any], account: dict[str, Any]) -> dict[str, Any]:
    permissions = dict(existing.get("permissions") or {})
    defaults = config.get("permission_defaults") or {}
    account_defaults = account.get("permission_overrides") or {}

    allow = set(permissions.get("allow") or [])
    if defaults.get("auto_bypass_permissions", True):
        allow.update(defaults.get("allow", PERMISSIVE_ALLOW_LIST))
    allow.update(account_defaults.get("allow", []))

    permissions["allow"] = sorted(allow)
    permissions["ask"] = list(account_defaults.get("ask", defaults.get("ask", [])))
    permissions["deny"] = list(account_defaults.get("deny", defaults.get("deny", [])))
    return permissions


def ensure_antigravity_settings(account: dict[str, Any], config: dict[str, Any]) -> Path:
    settings_path = antigravity_settings_path(account)
    settings = load_json(settings_path, {})
    defaults = config.get("permission_defaults") or {}
    workspace_roots = account.get("workspace_roots") or defaults.get("workspace_roots") or ["/"]

    settings["allowNonWorkspaceAccess"] = bool(defaults.get("allow_non_workspace_access", True))
    settings["permissionPreset"] = defaults.get("permission_preset", "always-proceed")
    settings["sandbox"] = bool(defaults.get("sandbox", False))
    settings["workspaceRoots"] = [expand_path(str(path)) for path in workspace_roots]
    settings["permissions"] = merged_permissions(settings, config, account)
    save_json(settings_path, settings)
    return settings_path


def build_env(account: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    root = profile_dir(account)
    root.mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "HOME": str(root),
            "XDG_CONFIG_HOME": str(root / ".config"),
            "XDG_DATA_HOME": str(root / ".local" / "share"),
            "XDG_CACHE_HOME": str(root / ".cache"),
            "AGY_ACTIVE_ACCOUNT": account["name"],
            "AGY_ALLOW_NON_WORKSPACE_ACCESS": "1",
        }
    )
    for key, value in (account.get("env") or {}).items():
        env[str(key)] = str(value)
    ensure_antigravity_settings(account, config)
    return env


def cli_default_args(config: dict[str, Any], account: dict[str, Any]) -> list[str]:
    defaults = config.get("permission_defaults") or {}
    args: list[str] = []
    if defaults.get("auto_bypass_permissions", True):
        args.extend(defaults.get("cli_args", ["--dangerously-skip-permissions"]))
    args.extend(account.get("default_cli_args", []))
    return [str(arg) for arg in args]


def detect_timeout(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def parse_reset(text: str, default_minutes: int) -> datetime:
    lowered = text.lower()
    match = re.search(r"try again in\s+(\d+)\s*(minute|minutes|min|hour|hours|hr|hrs)", lowered)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        minutes = amount * 60 if unit.startswith(("hour", "hr")) else amount
        return utc_now() + timedelta(minutes=minutes)
    return utc_now() + timedelta(minutes=default_minutes)


def write_handoff(state_dir: Path, account: dict[str, Any], model: str, reason: str, command: list[str], log_path: Path) -> Path:
    handoff = state_dir / "handoff.md"
    command_text = " ".join(command) if command else "<interactive/login>"
    handoff.write_text(
        "# Antigravity CLI Handoff\n\n"
        f"* Timestamp UTC: {iso(utc_now())}\n"
        f"* Previous account: {account['name']}\n"
        f"* Model: {model}\n"
        f"* Switch reason: {reason}\n"
        f"* Last command: `{command_text}`\n"
        f"* Session log: `{log_path}`\n\n"
        "## Resume Command\n\n"
        "```bash\n"
        f"python3 tools/antigravity_three_account/agy-rotate.py --model {model} --resume\n"
        "```\n\n"
        "## Continue Without Context Loss\n\n"
        "1. Review the session log above.\n"
        "2. Paste this handoff plus relevant log excerpts into the next account session.\n"
        "3. Ask the next session to restate assumptions before making changes.\n",
        encoding="utf-8",
    )
    handoff.chmod(0o600)
    return handoff


def status_payload(config: dict[str, Any], state: dict[str, Any], model: str) -> dict[str, Any]:
    now = utc_now()
    rows = []
    for account in config["accounts"]:
        reset_at = account_cooldown(state, account["name"], model)
        status = "eligible"
        if not model_allowed(account, model):
            status = "model-not-enabled"
        elif reset_at and reset_at > now:
            status = f"cooldown until {iso(reset_at)}"
        rows.append(
            {
                "account": account["name"],
                "label": account.get("label", ""),
                "models": account.get("models", ["*"]),
                "status": status,
                "profile_dir": str(profile_dir(account)),
                "settings": str(antigravity_settings_path(account)),
            }
        )
    return {
        "model": model,
        "current_account": state.get("current_account"),
        "active_run": state.get("active_run"),
        "last_command": state.get("last_command"),
        "accounts": rows,
    }


def print_status(config: dict[str, Any], state: dict[str, Any], model: str, plain: bool, as_json: bool) -> None:
    payload = status_payload(config, state, model)
    if as_json or not rich_available(plain):
        print(json.dumps(payload, indent=2))
        return

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    table = Table(title=f"Antigravity account rotation // model={model}", show_lines=True)
    table.add_column("Account", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Models", style="green")
    table.add_column("Profile", overflow="fold")
    for row in payload["accounts"]:
        style = "green" if row["status"] == "eligible" else "yellow"
        table.add_row(row["account"], f"[{style}]{row['status']}[/{style}]", ", ".join(row["models"]), row["profile_dir"])
    console.print(Panel.fit("[bold]HIGH-GRAVITY Antigravity Three-Account Control Plane[/bold]", border_style="magenta"))
    console.print(table)
    if payload.get("active_run"):
        console.print(Panel(json.dumps(payload["active_run"], indent=2), title="Active/Resume State", border_style="blue"))


def run_record(run_id: str, account: dict[str, Any], model: str, command: list[str], user_command: list[str], log_path: Path) -> dict[str, Any]:
    return {
        "id": run_id,
        "started_at": iso(utc_now()),
        "updated_at": iso(utc_now()),
        "status": "running",
        "account": account["name"],
        "model": model,
        "command": command,
        "user_command": user_command,
        "cwd": os.getcwd(),
        "log_path": str(log_path),
    }


def save_run_state(state_dir: Path, state: dict[str, Any], record: dict[str, Any]) -> None:
    record["updated_at"] = iso(utc_now())
    state["active_run"] = record
    state.setdefault("runs", {})[record["id"]] = record
    state["last_command"] = {
        "model": record["model"],
        "user_command": record["user_command"],
        "command": record["command"],
        "cwd": record["cwd"],
        "account": record["account"],
        "updated_at": record["updated_at"],
    }
    save_json(state_dir / "state.json", state)


def mark_run_complete(state_dir: Path, state: dict[str, Any], run_id: str, status: str, return_code: int) -> None:
    record = state.get("runs", {}).get(run_id)
    if record:
        record["status"] = status
        record["return_code"] = return_code
        record["updated_at"] = iso(utc_now())
        state["last_command"] = {
            "model": record["model"],
            "user_command": record["user_command"],
            "command": record["command"],
            "cwd": record["cwd"],
            "account": record["account"],
            "updated_at": record["updated_at"],
        }
    state["active_run"] = None
    save_json(state_dir / "state.json", state)


def execute_once(
    args: argparse.Namespace,
    config: dict[str, Any],
    state: dict[str, Any],
    account: dict[str, Any],
    model: str,
    user_command: list[str],
) -> RunResult:
    cli = args.cli or os.environ.get("ANTIGRAVITY_CMD", "agy")
    if not shutil.which(cli):
        raise SystemExit(f"CLI binary {cli!r} not found. Run setup.sh or set ANTIGRAVITY_CMD.")

    env = build_env(account, config)
    state["current_account"] = account["name"]

    command = [cli]
    if args.login:
        command.append("login")
    else:
        command.extend(cli_default_args(config, account))
        command.extend(user_command)

    run_id = f"{iso(utc_now()).replace(':', '-')}-{uuid.uuid4().hex[:8]}"
    log_path = args.state_dir / "sessions" / f"{run_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = run_record(run_id, account, model, command, user_command, log_path)
    save_run_state(args.state_dir, state, record)

    if rich_available(args.plain):
        from rich.console import Console
        from rich.panel import Panel

        Console().print(Panel.fit(f"[bold cyan]{account['name']}[/bold cyan] → [green]{' '.join(command)}[/green]", title="Launching"))
    else:
        print(f"[agy-rotate] launching account={account['name']} command={' '.join(command)}")

    output_chunks: list[str] = []
    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(f"# account={account['name']} model={model} command={' '.join(command)}\n")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        assert process.stdout is not None
        for line in process.stdout:
            output_chunks.append(line)
            print(line, end="")
            log_file.write(line)
        return_code = process.wait()

    output = "".join(output_chunks)
    patterns = config.get("timeout_patterns") or DEFAULT_TIMEOUT_PATTERNS
    timed_out = detect_timeout(output, patterns)
    reset_at = parse_reset(output, int(config.get("cooldown_minutes", 240))) if timed_out else None
    mark_run_complete(args.state_dir, state, run_id, "timeout" if timed_out else "complete", return_code)
    return RunResult(return_code=return_code, output=output, log_path=log_path, timed_out=timed_out, reset_at=reset_at)


def mark_timeout(
    args: argparse.Namespace,
    config: dict[str, Any],
    state: dict[str, Any],
    account: dict[str, Any],
    model: str,
    command: list[str],
    result: RunResult,
) -> Path:
    assert result.reset_at is not None
    state.setdefault("cooldowns", {}).setdefault(account["name"], {})[model] = iso(result.reset_at)
    state.setdefault("events", []).append(
        {"at": iso(utc_now()), "account": account["name"], "model": model, "event": "timeout", "reset_at": iso(result.reset_at)}
    )
    state["events"] = state["events"][-100:]
    handoff = write_handoff(args.state_dir, account, model, "timeout detected", command, result.log_path)
    save_json(args.state_dir / "state.json", state)
    console_print(
        f"[yellow]Timeout detected for {account['name']}[/yellow]. Cooldown until {iso(result.reset_at)}. Handoff: {handoff}",
        plain=args.plain,
    )
    return handoff


def apply_resume(args: argparse.Namespace, state: dict[str, Any], config: dict[str, Any]) -> tuple[str, list[str]]:
    saved = state.get("active_run") or state.get("last_command")
    if not saved:
        raise SystemExit("No saved active_run or last_command is available to resume.")
    model = args.model or saved.get("model") or config.get("default_model") or "standard"
    command = list(saved.get("user_command") or [])
    if not command and saved.get("command"):
        command = list(saved["command"])[1:]
    if saved.get("cwd") and Path(saved["cwd"]).exists():
        os.chdir(saved["cwd"])
    return model, command


def run_command(args: argparse.Namespace, config: dict[str, Any], state: dict[str, Any]) -> int:
    if args.resume:
        model, user_command = apply_resume(args, state, config)
    else:
        model = args.model or config.get("default_model") or "standard"
        user_command = args.command

    forced = args.account or os.environ.get("AGY_ACCOUNT")
    cli = args.cli or os.environ.get("ANTIGRAVITY_CMD", "agy")
    attempts = max(1, args.max_attempts or int(config.get("max_attempts", 3)))
    auto_continue = bool(config.get("auto_continue_on_timeout", True)) and not forced and not args.login

    if args.dry_run:
        account = choose_account(config, state, model, forced)
        command = [cli] + ([] if args.login else cli_default_args(config, account)) + ([] if args.login else user_command)
        print(json.dumps({"selected_account": account["name"], "model": model, "cli": cli, "command": command}, indent=2))
        return 0

    if args.login and not user_command:
        attempts = 1

    blocked: set[str] = set()
    last_result: RunResult | None = None
    for attempt in range(1, attempts + 1):
        account = choose_account(config, state, model, forced, blocked=blocked)
        result = execute_once(args, config, state, account, model, user_command)
        last_result = result
        command = [cli] + ([] if args.login else cli_default_args(config, account)) + ([] if args.login else user_command)
        if not result.timed_out:
            return result.return_code
        mark_timeout(args, config, state, account, model, command, result)
        blocked.add(account["name"])
        if not auto_continue or attempt >= attempts:
            return result.return_code
        console_print(f"[cyan]Rotating to next eligible account for attempt {attempt + 1}/{attempts}[/cyan]", plain=args.plain)
    return last_result.return_code if last_result else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rich, resumable wrapper for three authorized Antigravity CLI accounts.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to accounts.json.")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR, help="State/log directory.")
    parser.add_argument("--model", help="Model/capability name used for cooldown tracking.")
    parser.add_argument("--account", help="Force a configured account name.")
    parser.add_argument("--cli", help="Antigravity CLI binary; default uses ANTIGRAVITY_CMD or agy.")
    parser.add_argument("--status", action="store_true", help="Print rich account eligibility state and exit.")
    parser.add_argument("--json", action="store_true", help="Emit JSON for status output.")
    parser.add_argument("--plain", action="store_true", help="Disable Rich formatting even when Rich is installed.")
    parser.add_argument("--dry-run", action="store_true", help="Print selected account and full command without running the CLI.")
    parser.add_argument("--login", action="store_true", help="Run the CLI login flow in the selected account profile.")
    parser.add_argument("--resume", action="store_true", help="Resume the last active or completed command with its saved cwd/model.")
    parser.add_argument("--max-attempts", type=int, help="Maximum account attempts for automatic timeout rotation.")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Arguments passed to the Antigravity CLI after --.")
    args = parser.parse_args()
    args.config = args.config.expanduser()
    args.state_dir = args.state_dir.expanduser()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    return args


def main() -> int:
    args = parse_args()
    args.state_dir.mkdir(parents=True, exist_ok=True)
    (args.state_dir / "sessions").mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    state = load_json(args.state_dir / "state.json", default_state())
    model = args.model or config.get("default_model") or "standard"

    if args.status:
        print_status(config, state, model, args.plain, args.json)
        return 0
    return run_command(args, config, state)


if __name__ == "__main__":
    sys.exit(main())
