#!/usr/bin/env python3
"""
HIGH-GRAVITY Dashboard v3.0
Combined Rich TUI with working hotkeys.
"""
import os
import sys
import time
import select
import termios
import tty
import subprocess
import requests
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

REPO_ROOT = Path(__file__).resolve().parent
LOG_DIR = REPO_ROOT / "logs"
PROXY_PORT = 9999
PROXY_URL = f"http://127.0.0.1:{PROXY_PORT}"

THINKING_TIERS = [
    ("low",    "Low",        "cyan"),
    ("medium", "Medium",     "green"),
    ("high",   "High",       "yellow"),
    ("xhigh",  "Extra High", "magenta"),
]


class Dashboard:
    def __init__(self):
        self.tel = {}
        self.khoj = {}
        self.status_msg = "[dim]Starting...[/dim]"
        self.view = "main"   # main | logs | pegasus
        self.log_name = ""
        self.log_lines = []

    # ── data fetchers ────────────────────────────────────────────────
    def fetch(self):
        try:
            r = requests.get(f"{PROXY_URL}/hg/telemetry", timeout=1)
            self.tel = r.json() if r.ok else {}
        except Exception:
            self.tel = {}
        try:
            r = requests.get(f"{PROXY_URL}/hg/khoj/status", timeout=1)
            self.khoj = r.json() if r.ok else {}
        except Exception:
            self.khoj = {}

    def read_log_tail(self, name, n=40):
        p = LOG_DIR / name
        if not p.exists():
            return [f"(not found: {p})"]
        lines = p.read_text().splitlines()
        return lines[-n:] if lines else ["(empty)"]

    def mitm_event_count(self):
        p = LOG_DIR / "cascade_midway.log"
        if not p.exists():
            return 0
        return sum(1 for l in p.read_text().splitlines() if "PROTOCOL EVENT" in l)

    def windsurf_api_url(self):
        try:
            out = subprocess.check_output(
                "ps aux | grep language_server_linux | grep -v grep",
                shell=True, text=True, timeout=2
            )
            for tok in out.split():
                if "server_url" in tok:
                    continue
                if tok.startswith("http"):
                    return tok
            # fallback: parse --api_server_url
            if "--api_server_url" in out:
                idx = out.index("--api_server_url")
                return out[idx:].split()[1]
        except Exception:
            pass
        return None

    # ── actions ──────────────────────────────────────────────────────
    def action(self, name):
        try:
            requests.post(f"{PROXY_URL}/hg/manage", json={"action": name}, timeout=1)
            self.status_msg = f"[green]{name} → OK[/green]"
        except Exception:
            self.status_msg = f"[red]{name} → failed[/red]"

    def run_cmd(self, label, cmd):
        self.status_msg = f"[yellow]{label}...[/yellow]"
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=REPO_ROOT)
            if r.returncode == 0:
                self.status_msg = f"[green]{label} → OK[/green]"
            else:
                self.status_msg = f"[red]{label} → {r.stderr[:60]}[/red]"
        except Exception as e:
            self.status_msg = f"[red]{label} → {e}[/red]"

    # ── panels ───────────────────────────────────────────────────────
    def _proxy_panel(self):
        t = self.tel
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        online = bool(t)
        tbl.add_row("Status", "[green]ONLINE[/green]" if online else "[red]OFFLINE[/red]")
        tbl.add_row("Port", str(t.get("proxy_port", PROXY_PORT)))
        tbl.add_row("Active keys", str(t.get("active_keys", 0)))
        tbl.add_row("Exhausted", str(t.get("exhausted_keys", 0)))
        tbl.add_row("Cache hits", str(t.get("cache_hits", 0)))
        tbl.add_row("Requests", str(t.get("total_requests", 0)))
        tbl.add_row("Rotation", str(t.get("rotation_mode", "?")))
        return Panel(tbl, title="Proxy", border_style="green")

    def _mitm_panel(self):
        t = self.tel
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        tbl.add_row("Mode", str(t.get("mitm_mode", "?")))
        tbl.add_row("Upgrades", str(t.get("mitm_upgrades_total", 0)))
        tbl.add_row("RL hits", str(t.get("mitm_rate_limit_hits", 0)))

        detected = set(t.get("mitm_detected_services", []) or [])
        svc_text = Text()
        for svc in ("gemini", "codex", "openai"):
            style = "bold green" if svc in detected else "dim"
            svc_text.append(f" {svc.upper()} ", style=style)
            svc_text.append(" ")
        tbl.add_row("Services", svc_text)

        tbl.add_row("MITM events", str(self.mitm_event_count()))
        return Panel(tbl, title="MITM Bridge", border_style="magenta")

    def _khoj_panel(self):
        k = self.khoj
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        if k.get("enabled"):
            tbl.add_row("Status", "[green]ENABLED[/green]")
        else:
            tbl.add_row("Status", "[red]OFFLINE[/red]")
        tbl.add_row("Searches", str(k.get("search_count", 0)))
        tbl.add_row("Injections", str(k.get("injection_count", 0)))
        tbl.add_row("Top-K", str(k.get("top_k", "?")))
        return Panel(tbl, title="Khoj", border_style="blue")

    def _system_panel(self):
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        # Windsurf
        api_url = self.windsurf_api_url()
        if api_url:
            if "shield" in api_url or "127.0.0.1" in api_url:
                tbl.add_row("Windsurf", "[green]→ PROXY[/green]")
            else:
                tbl.add_row("Windsurf", f"[red]→ {api_url[:30]}[/red]")
        else:
            tbl.add_row("Windsurf", "[dim]not running[/dim]")

        # Patches
        ext = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js")
        if ext.exists():
            content = ext.read_text()[:5000]
            if 'getApiServerUrlFromContext=A=>{return"http://shield' in content:
                tbl.add_row("Ext patch", "[green]✓ ROOT FIX[/green]")
            elif "shield.windsurf.com" in content:
                tbl.add_row("Ext patch", "[yellow]~ partial[/yellow]")
            else:
                tbl.add_row("Ext patch", "[red]✗ none[/red]")

        tbl.add_row("Logs", str(LOG_DIR))
        return Panel(tbl, title="System", border_style="yellow")

    def _events_panel(self):
        events = self.tel.get("mitm_recent_events", []) or []
        tbl = Table(expand=True, box=None)
        tbl.add_column("Time", style="dim", no_wrap=True)
        tbl.add_column("Kind", no_wrap=True)
        tbl.add_column("Detail")
        colors = {"detect": "cyan", "upgrade": "yellow", "thinking": "blue", "ratelimit": "red"}
        for ev in list(reversed(events))[:10]:
            ts = datetime.fromtimestamp(ev.get("ts", 0)).strftime("%H:%M:%S")
            kind = ev.get("kind", "?")
            tbl.add_row(ts, Text(kind, style=colors.get(kind, "white")), ev.get("detail", ""))
        return Panel(tbl, title="Recent Events", border_style="red")

    def _thinking_panel(self):
        by_lvl = self.tel.get("mitm_thinking_by_level", {}) or {}
        total = sum(by_lvl.values()) or 1
        tbl = Table(expand=True, box=None)
        tbl.add_column("Tier", no_wrap=True)
        tbl.add_column("Count", justify="right")
        tbl.add_column("Bar", ratio=2)
        for key, label, color in THINKING_TIERS:
            n = int(by_lvl.get(key, 0))
            bar_len = int((n / total) * 20)
            bar = Text("█" * bar_len + "░" * (20 - bar_len), style=color)
            tbl.add_row(Text(label, style=f"bold {color}"), str(n), bar)
        return Panel(tbl, title="Reasoning", border_style="blue")

    def _hotkey_panel(self):
        tbl = Table(expand=True, box=None, padding=(0, 0))
        tbl.add_column("Key", style="bold cyan", no_wrap=True, width=3)
        tbl.add_column("Action", no_wrap=True)
        tbl.add_row("C", "Clear cache")
        tbl.add_row("R", "Rotate keys")
        tbl.add_row("P", "Patch Windsurf")
        tbl.add_row("U", "Undo patches")
        tbl.add_row("W", "Launch Windsurf")
        tbl.add_row("X", "Git push")
        tbl.add_row("L", "Logs view")
        tbl.add_row("Q", "Quit")
        return Panel(tbl, title="Keys", border_style="yellow")

    def _log_panel(self):
        lines = self.read_log_tail(self.log_name, 30)
        content = Text()
        for line in lines:
            if "ERROR" in line or "FAIL" in line:
                content.append(line + "\n", style="red")
            elif "INFO" in line:
                content.append(line + "\n", style="dim")
            else:
                content.append(line + "\n")
        footer = Text(
            "[1] proxy.log  [2] cascade_midway.log  [3] khoj.log  [4] proxy_https.log  [B] back",
            style="bold cyan", justify="center"
        )
        inner = Layout()
        inner.split_column(
            Layout(Panel(content, title=f"📄 {self.log_name}", border_style="green"), ratio=9),
            Layout(Panel(footer, border_style="dim"), size=3),
        )
        return inner

    # ── layout ───────────────────────────────────────────────────────
    def build_layout(self):
        self.fetch()

        if self.view == "logs":
            root = Layout()
            root.split_column(
                Layout(Panel(Text("HIGH-GRAVITY DASHBOARD", justify="center", style="bold cyan"), border_style="cyan"), size=3),
                Layout(self._log_panel()),
                Layout(Panel(Text(f"Status: {self.status_msg}    {datetime.now().strftime('%H:%M:%S')}", justify="center"), border_style="dim"), size=3),
            )
            return root

        root = Layout()
        root.split_column(
            Layout(name="header", size=3),
            Layout(name="top", size=11),
            Layout(name="mid", size=9),
            Layout(name="events"),
            Layout(name="footer", size=3),
        )

        root["header"].update(Panel(
            Text("HIGH-GRAVITY DASHBOARD", justify="center", style="bold cyan"),
            border_style="cyan",
        ))

        root["top"].split_row(
            Layout(self._proxy_panel(), ratio=3),
            Layout(self._mitm_panel(), ratio=3),
            Layout(self._hotkey_panel(), ratio=2),
        )

        root["mid"].split_row(
            Layout(self._khoj_panel(), ratio=1),
            Layout(self._system_panel(), ratio=1),
            Layout(self._thinking_panel(), ratio=2),
        )

        root["events"].update(self._events_panel())

        root["footer"].update(Panel(
            Text(f"Status: {self.status_msg}    {datetime.now().strftime('%H:%M:%S')}", justify="center"),
            border_style="dim",
        ))
        return root

    # ── main loop ────────────────────────────────────────────────────
    def run(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)

        try:
            with Live(self.build_layout(), refresh_per_second=2, screen=True) as live:
                while True:
                    live.update(self.build_layout())
                    r, _, _ = select.select([sys.stdin], [], [], 0.3)
                    if not r:
                        continue
                    c = sys.stdin.read(1).lower()

                    if self.view == "logs":
                        if c == "b" or c == "\x1b":
                            self.view = "main"
                        elif c == "1":
                            self.log_name = "proxy.log"
                        elif c == "2":
                            self.log_name = "cascade_midway.log"
                        elif c == "3":
                            self.log_name = "khoj.log"
                        elif c == "4":
                            self.log_name = "proxy_https.log"
                        elif c == "q":
                            break
                        continue

                    # Main view keys
                    if c == "q":
                        break
                    elif c == "c":
                        self.action("clear_cache")
                    elif c == "r":
                        self.action("rotate_keys")
                    elif c == "p":
                        self.run_cmd("Patch", ["python3", "src/patch_windsurf_client.py", "--force"])
                    elif c == "u":
                        self.run_cmd("Undo", ["python3", "src/patch_windsurf_client.py", "--undo"])
                    elif c == "w":
                        subprocess.Popen(
                            ["/usr/share/windsurf-next/windsurf-next"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                        self.status_msg = "[green]Windsurf launching...[/green]"
                    elif c == "x":
                        self.run_cmd("Git push", ["git", "push", "origin", "main", "--no-verify"])
                    elif c == "l":
                        self.view = "logs"
                        self.log_name = "proxy.log"
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


if __name__ == "__main__":
    Dashboard().run()
