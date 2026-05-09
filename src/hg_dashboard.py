#!/usr/bin/env python3
"""
HIGH-GRAVITY Pegasus Dashboard v3.2
Expert-Tier Shield & Intelligence Control Plane.
"""
import os
import sys
import time
import select
import termios
import tty
import subprocess
import requests
import json
import random
import numpy as np
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs"
PROXY_PORT = 9998
PROXY_URL = f"http://127.0.0.1:{PROXY_PORT}"

THINKING_TIERS = [
    ("low",    "Basic",      "cyan"),
    ("medium", "Advanced",   "green"),
    ("high",   "Deep",       "yellow"),
    ("xhigh",  "Extreme",    "magenta"),
]


class Dashboard:
    def __init__(self):
        self.tel = {}
        self.khoj = {}
        self.status_msg = "[dim]Initializing Expert-Tier Control Plane...[/dim]"
        self.view = "main"   # main | logs
        self.log_name = "proxy.log"
        self.console = Console()

    def fetch(self):
        try:
            r = requests.get(f"{PROXY_URL}/hg/telemetry", timeout=0.4)
            self.tel = r.json() if r.ok else {}
            self.khoj = self.tel.get("khoj", {})
        except Exception:
            self.tel = {}
            self.khoj = {}

    def read_log_tail(self, name, n=40):
        p = LOG_DIR / name
        if not p.exists():
            return [f"(not found: {p})"]
        try:
            lines = p.read_text(errors="replace").splitlines()
            return lines[-n:] if lines else ["(empty)"]
        except Exception as e:
            return [f"Error reading log: {e}"]

    def windsurf_api_url(self):
        try:
            out = subprocess.check_output(
                "ps aux | grep language_server_linux | grep -v grep",
                shell=True, text=True, timeout=1
            )
            if "--api_server_url" in out:
                parts = out.split()
                for i, part in enumerate(parts):
                    if part == "--api_server_url" and i+1 < len(parts):
                        return parts[i+1].strip("'").strip('"')
        except: pass
        return None

    def action(self, name):
        try:
            requests.post(f"{PROXY_URL}/hg/manage", json={"action": name}, timeout=1)
            self.status_msg = f"[green]Action '{name}' sent successfully[/green]"
        except Exception:
            self.status_msg = f"[red]Action '{name}' failed[/red]"

    def run_cmd(self, label, cmd_str):
        self.status_msg = f"[yellow]{label}...[/yellow]"
        try:
            full_cmd = cmd_str.replace("./hg.sh", f"bash {REPO_ROOT}/hg.sh")
            subprocess.Popen(full_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=REPO_ROOT)
            self.status_msg = f"[green]{label} triggered[/green]"
        except Exception as e:
            self.status_msg = f"[red]{label} error: {e}[/red]"

    # --- Panels ---
    def _proxy_panel(self):
        t = self.tel
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        online = bool(t)
        tbl.add_row("Status", "[green]ONLINE[/green]" if online else "[red]OFFLINE[/red]")
        tbl.add_row("Port", str(t.get("proxy_port", PROXY_PORT)))
        tbl.add_row("Active Keys", f"{t.get('active_keys', 0)} / {t.get('total_keys', 0)}")
        tbl.add_row("Cache Hits", str(t.get("cache_hits", 0)))
        tbl.add_row("Tokens Saved", f"{t.get('tokens_saved', 0):,}")
        tbl.add_row("Throughput", f"{t.get('total_requests', 0)} req")
        return Panel(tbl, title="Quantum Proxy", border_style="green")

    def _intelligence_panel(self):
        k = self.khoj
        t = self.tel
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        tbl.add_row("Khoj RAG", "[green]ACTIVE[/green]" if k.get("enabled") else "[dim]IDLE[/dim]")
        tbl.add_row("RAG Injects", str(k.get("injection_count", 0)))
        
        # Expert Shield Stats
        thinking = t.get("mitm_thinking_by_level", {})
        deep_hits = thinking.get("high", 0) + thinking.get("xhigh", 0)
        tbl.add_row("Deep Think", f"[bold yellow]{deep_hits}[/bold yellow]")
        
        mutations = 0
        for ev in t.get("mitm_recent_events", []):
            if ev.get("kind") == "mutation": mutations += 1
        tbl.add_row("Anti-Reject", f"[bold magenta]{mutations}[/bold magenta] hits")
        
        return Panel(tbl, title="Intelligence Layer", border_style="blue")

    def _shield_panel(self):
        t = self.tel
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        # Routing
        api_url = self.windsurf_api_url()
        is_proxied = api_url and ("proxy.windsurf.com" in api_url or "inferapi.windsurf.com" in api_url)
        tbl.add_row("Editor Link", "[green]PROXIED[/green]" if is_proxied else "[red]DIRECT[/red]")

        # OPSEC
        shuffler = "[green]ACTIVE[/green]" if t else "[dim]--[/dim]"
        tbl.add_row("Jitter/Entropy", shuffler)
        tbl.add_row("Redactor", "[green]WATERTIGHT[/green]" if t else "[dim]--[/dim]")

        # Binary Patch Check
        bin_target = None
        for p in ["language_server_linux_x64.real", "language_server_linux_x64"]:
            full_p = Path(f"/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/{p}")
            if full_p.exists():
                bin_target = full_p
                break
        
        if bin_target:
            with open(bin_target, "rb") as f:
                f.seek(0x818b87d); b = f.read(2)
            tbl.add_row("Bin Patch", "[green]PATCHED[/green]" if b == b'\x90\x90' else "[red]ORIGINAL[/red]")
        else:
            tbl.add_row("Bin Patch", "[red]NOT FOUND[/red]")

        # Latency
        lat = self.tel.get("latency_ms", {})
        p50 = lat.get("p50", 0) or 0
        tbl.add_row("p50 Latency", f"{p50:.1f}ms")

        return Panel(tbl, title="Expert Shield Status", border_style="yellow")

    def _events_panel(self):
        events = self.tel.get("mitm_recent_events", []) or []
        tbl = Table(expand=True, box=None)
        tbl.add_column("Time", style="dim", no_wrap=True, width=10)
        tbl.add_column("Agent", no_wrap=True, width=12)
        tbl.add_column("Activity")
        colors = {
            "detect": "cyan", "upgrade": "yellow", "thinking": "blue", 
            "ratelimit": "red", "khoj": "green", "mutation": "magenta"
        }
        for ev in list(reversed(events))[:10]:
            ts = datetime.fromtimestamp(ev.get("ts", 0)).strftime("%H:%M:%S")
            kind = ev.get("kind", "?")
            detail = ev.get("detail", "")
            agent = "ROUTER" if kind == "detect" else "OVERRIDE" if kind == "upgrade" else \
                    "REASONER" if kind == "thinking" else "KHOJ" if kind == "khoj" else \
                    "MUTATOR" if kind == "mutation" else "SYSTEM"
            tbl.add_row(ts, Text(agent, style=colors.get(kind, "white")), detail)
        return Panel(tbl, title="Pegasus Swarm Activity", border_style="red")

    def _thinking_panel(self):
        by_lvl = self.tel.get("mitm_thinking_by_level", {}) or {}
        total = sum(by_lvl.values()) or 1
        tbl = Table(expand=True, box=None)
        tbl.add_column("Reasoning Tier", no_wrap=True)
        tbl.add_column("Count", justify="right")
        tbl.add_column("Intensity", ratio=2)
        for key, label, color in THINKING_TIERS:
            n = int(by_lvl.get(key, 0))
            bar_len = int((n / total) * 20)
            bar = Text("█" * bar_len + "░" * (20 - bar_len), style=color)
            tbl.add_row(Text(label, style=f"bold {color}"), str(n), bar)
        return Panel(tbl, title="AI Reasoning Profile", border_style="magenta")

    def _controls_panel(self):
        tbl = Table(expand=True, box=None, padding=(0, 0))
        tbl.add_column("Key", style="bold cyan", no_wrap=True, width=3)
        tbl.add_column("Action", no_wrap=True)
        tbl.add_row("S", "Start All")
        tbl.add_row("X", "Stop All")
        tbl.add_row("P", "Deep Patch")
        tbl.add_row("U", "Unpatch")
        tbl.add_row("D", "Doctor")
        tbl.add_row("W", "Launch Editor")
        tbl.add_row("R", "Rotate Keys")
        tbl.add_row("C", "Clear Cache")
        tbl.add_row("L", "Intelligence Logs")
        tbl.add_row("Q", "Exit Plane")
        return Panel(tbl, title="Controls", border_style="white")

    def _log_panel(self):
        lines = self.read_log_tail(self.log_name, 35)
        content = Text()
        for line in lines:
            if "ERROR" in line or "FAIL" in line or "CRITICAL" in line:
                content.append(line + "\n", style="bold red")
            elif "WARNING" in line or "WARN" in line:
                content.append(line + "\n", style="yellow")
            elif "INFO" in line:
                content.append(line + "\n", style="dim")
            elif "PROTOCOL EVENT" in line or "KHOJ_CONTEXT" in line:
                content.append(line + "\n", style="bold green")
            elif "PROACTIVE_TRIGGER" in line or "mutation" in line:
                content.append(line + "\n", style="bold magenta")
            else:
                content.append(line + "\n")
        
        footer = Text(
            "[1] proxy.log  [2] cascade.log  [3] khoj.log  [4] proxy_https.log  [B] Back",
            style="bold cyan", justify="center"
        )
        inner = Layout()
        inner.split_column(
            Layout(Panel(content, title=f"Intelligence Log: {self.log_name}", border_style="green"), ratio=9),
            Layout(Panel(footer, border_style="dim"), size=3),
        )
        return inner

    def build_layout(self):
        self.fetch()
        if self.view == "logs":
            root = Layout()
            root.split_column(
                Layout(Panel(Text("HIGH-GRAVITY CENTRAL INTELLIGENCE", justify="center", style="bold cyan"), border_style="cyan"), size=3),
                Layout(self._log_panel()),
                Layout(Panel(Text(f"Status: {self.status_msg}    {datetime.now().strftime('%H:%M:%S')}", justify="center"), border_style="dim"), size=3),
            )
            return root

        root = Layout()
        root.split_column(
            Layout(name="header", size=3),
            Layout(name="top", size=10),
            Layout(name="mid", size=12),
            Layout(name="bottom", size=12),
            Layout(name="footer", size=3),
        )

        root["header"].update(Panel(
            Text("HIGH-GRAVITY PEGASUS CONTROL PLANE v3.2", justify="center", style="bold cyan"),
            border_style="cyan",
        ))

        root["top"].split_row(
            Layout(self._proxy_panel(), ratio=3),
            Layout(self._intelligence_panel(), ratio=3),
            Layout(self._controls_panel(), ratio=2),
        )

        root["mid"].split_row(
            Layout(self._shield_panel(), ratio=1),
            Layout(self._thinking_panel(), ratio=1),
        )

        # Bottom section: Swarm Events on left, Live Log on right
        root["bottom"].split_row(
            Layout(self._events_panel(), ratio=1),
            Layout(Panel(self._mini_log_content(), title="Intelligence Stream", border_style="dim"), ratio=1),
        )

        root["footer"].update(Panel(
            Text(f"Status: {self.status_msg}    {datetime.now().strftime('%H:%M:%S')}", justify="center"),
            border_style="dim",
        ))
        return root

    def _mini_log_content(self):
        lines = self.read_log_tail("proxy.log", 10)
        content = Text()
        for line in lines:
            if "ERROR" in line or "FAIL" in line: style = "bold red"
            elif "WARNING" in line: style = "yellow"
            elif "PROTOCOL EVENT" in line: style = "bold green"
            elif "mutation" in line: style = "bold magenta"
            else: style = "dim"
            # Extract just the message after the log level for mini view
            msg = line.split("] ", 1)[-1] if "] " in line else line
            content.append(msg[:80] + "\n", style=style)
        return content

    def run(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        try:
            with Live(self.build_layout(), refresh_per_second=2, screen=True) as live:
                while True:
                    live.update(self.build_layout())
                    r, _, _ = select.select([sys.stdin], [], [], 0.2)
                    if not r: continue
                    c = sys.stdin.read(1).lower()

                    if self.view == "logs":
                        if c == "b" or c == "\x1b": self.view = "main"
                        elif c == "1": self.log_name = "proxy.log"
                        elif c == "2": self.log_name = "cascade_midway.log"
                        elif c == "3": self.log_name = "khoj.log"
                        elif c == "4": self.log_name = "proxy_https.log"
                        elif c == "q": break
                        continue

                    if c == "q": break
                    elif c == "s": self.run_cmd("System Start", "./hg.sh start")
                    elif c == "x": self.run_cmd("System Stop", "./hg.sh stop")
                    elif c == "p": self.run_cmd("Deep Patch", "./hg.sh patch")
                    elif c == "u": self.run_cmd("Unpatch", "./hg.sh unpatch")
                    elif c == "d":
                        live.stop()
                        subprocess.run(f"bash {REPO_ROOT}/hg.sh doctor", shell=True)
                        input("\nPress Enter to return to dashboard...")
                        live.start()
                    elif c == "w":
                        subprocess.Popen("nohup /usr/share/windsurf-next/windsurf-next > /dev/null 2>&1 &", shell=True, start_new_session=True, cwd=REPO_ROOT)
                        self.status_msg = "[green]Launching Editor...[/green]"
                    elif c == "k": self.run_cmd("Khoj Reindex", "./hg.sh khoj reindex")
                    elif c == "l": self.view = "logs"; self.log_name = "proxy.log"
                    elif c == "r": self.action("rotate_keys")
                    elif c == "c": self.action("clear_cache")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

if __name__ == "__main__":
    Dashboard().run()
