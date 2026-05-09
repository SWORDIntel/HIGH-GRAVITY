#!/usr/bin/env python3
"""
HIGH-GRAVITY Pegasus Dashboard v3.1
Fully integrated with new script hierarchy and advanced telemetry.
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

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts" / "internal"
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
        self.install_status = {}
        self.status_msg = "[dim]Initializing Pegasus Control Plane...[/dim]"
        self.view = "main"   # main | logs | agents
        self.log_name = "proxy.log"
        self.log_lines = []
        self.console = Console()

    # ── data fetchers ────────────────────────────────────────────────
    def fetch(self):
        try:
            r = requests.get(f"{PROXY_URL}/hg/telemetry", timeout=0.5)
            self.tel = r.json() if r.ok else {}
            self.khoj = self.tel.get("khoj", {})
        except Exception:
            self.tel = {}
            self.khoj = {}
        self._check_install_status()
    
    def _check_install_status(self):
        """Check installation completeness"""
        import shutil
        self.install_status = {
            "python3": shutil.which("python3") is not None,
            "docker": shutil.which("docker") is not None,
            "hg_proxy": self._check_port(9998),
            "hg_https": self._check_port(443),
            "khoj": self._check_port(42110),
            "js_patch": self._check_file_patched(REPO_ROOT / "src" / "patch_all.py"), # Dummy, checked in system panel
            "binary": (REPO_ROOT / "hg.sh").exists(),
        }
    
    def _check_port(self, port):
        import socket
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=0.1)
            s.close()
            return True
        except:
            return False

    def _check_file_patched(self, path):
        return path.exists()

    def read_log_tail(self, name, n=40):
        p = LOG_DIR / name
        if not p.exists():
            return [f"(not found: {p})"]
        try:
            lines = p.read_text(errors="replace").splitlines()
            return lines[-n:] if lines else ["(empty)"]
        except Exception as e:
            return [f"Error reading log: {e}"]

    def mitm_event_count(self):
        p = LOG_DIR / "cascade_midway.log"
        if not p.exists():
            return 0
        try:
            return sum(1 for l in p.read_text(errors="replace").splitlines() if "PROTOCOL EVENT" in l)
        except: return 0

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
        except Exception:
            pass
        return None

    # ── actions ──────────────────────────────────────────────────────
    def action(self, name):
        try:
            requests.post(f"{PROXY_URL}/hg/manage", json={"action": name}, timeout=1)
            self.status_msg = f"[green]{name} sent[/green]"
        except Exception:
            self.status_msg = f"[red]{name} failed[/red]"

    def run_cmd(self, label, cmd_str):
        self.status_msg = f"[yellow]{label}...[/yellow]"
        try:
            # Use absolute path for hg.sh and ensure it runs in background via shell
            full_cmd = cmd_str.replace("./hg.sh", f"bash {REPO_ROOT}/hg.sh")
            subprocess.Popen(full_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=REPO_ROOT)
            self.status_msg = f"[green]{label} triggered[/green]"
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
        tbl.add_row("HTTP Port", str(t.get("proxy_port", PROXY_PORT)))
        tbl.add_row("Active Keys", f"{t.get('active_keys', 0)} / {t.get('total_keys', 0)}")
        tbl.add_row("Cache Hits", str(t.get("cache_hits", 0)))
        tbl.add_row("Tokens Saved", f"{t.get('tokens_saved', 0):,}")
        tbl.add_row("Total Req", str(t.get("total_requests", 0)))
        tbl.add_row("Rotation", str(t.get("rotation_mode", "round-robin")))
        return Panel(tbl, title="Quantum Proxy", border_style="green")

    def _ai_agent_panel(self):
        k = self.khoj
        t = self.tel
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        # Khoj Agent
        khoj_status = "[green]ACTIVE[/green]" if k.get("enabled") else "[red]IDLE[/red]"
        tbl.add_row("Khoj Status", khoj_status)
        tbl.add_row("Searches", str(k.get("search_count", 0)))
        tbl.add_row("Injections", str(k.get("injection_count", 0)))
        
        # Reasoner/Thinking
        thinking = t.get("mitm_thinking_by_level", {})
        deep_hits = thinking.get("high", 0) + thinking.get("xhigh", 0)
        tbl.add_row("Deep Think", f"[bold yellow]{deep_hits}[/bold yellow]")
        
        # Telemetry
        detected = set(t.get("mitm_detected_services", []) or [])
        svc_text = Text()
        for svc in ("gemini", "codex", "openai"):
            style = "bold green" if svc in detected else "dim"
            svc_text.append(f" {svc.upper()} ", style=style)
        tbl.add_row("Intercepted", svc_text)
        
        return Panel(tbl, title="AI Agent Intelligence", border_style="blue")

    def _system_panel(self):
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        # Windsurf
        api_url = self.windsurf_api_url()
        if api_url:
            is_proxied = "proxy.windsurf.com" in api_url or "inferapi.windsurf.com" in api_url
            tbl.add_row("Windsurf", "[green]PROXIED[/green]" if is_proxied else f"[red]DIRECT[/red]")
        else:
            tbl.add_row("Windsurf", "[dim]STOPPED[/dim]")

        # Redirection
        ipt = subprocess.run(
            ["sudo", "-n", "iptables", "-t", "nat", "-C", "OUTPUT", "-p", "tcp", "--dport", "50001", "-j", "REDIRECT", "--to-port", "9998"],
            capture_output=True
        ).returncode == 0
        tbl.add_row("ipt Redir", "[green]ACTIVE[/green]" if ipt else "[red]MISSING[/red]")

        # Patches
        ext = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js")
        if ext.exists():
            patched = "globalThis.HG_OPT" in ext.read_text(errors="ignore")
            tbl.add_row("JS Patch", "[green]OK[/green]" if patched else "[red]NONE[/red]")
        
        bin_real = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64.real")
        if bin_real.exists():
            with open(bin_real, "rb") as f:
                f.seek(0x818b87d); b = f.read(2)
            tbl.add_row("Bin Patch", "[green]NOP[/green]" if b == b'\x90\x90' else "[red]ORIG[/red]")

        # Latency
        lat = self.tel.get("latency_ms", {})
        p50 = lat.get("p50", 0) or 0
        tbl.add_row("p50 Latency", f"{p50:.1f}ms")

        return Panel(tbl, title="System Health", border_style="yellow")

    def _events_panel(self):
        events = self.tel.get("mitm_recent_events", []) or []
        tbl = Table(expand=True, box=None)
        tbl.add_column("Time", style="dim", no_wrap=True, width=10)
        tbl.add_column("Agent", no_wrap=True, width=12)
        tbl.add_column("Intelligence Event")
        colors = {"detect": "cyan", "upgrade": "yellow", "thinking": "blue", "ratelimit": "red", "khoj": "green"}
        for ev in list(reversed(events))[:8]:
            ts = datetime.fromtimestamp(ev.get("ts", 0)).strftime("%H:%M:%S")
            kind = ev.get("kind", "?")
            detail = ev.get("detail", "")
            agent = "ROUTER" if kind == "detect" else "OVERRIDE" if kind == "upgrade" else "REASONER" if kind == "thinking" else "KHOJ" if kind == "khoj" else "SYSTEM"
            tbl.add_row(ts, Text(agent, style=colors.get(kind, "white")), detail)
        return Panel(tbl, title="Pegasus Swarm Activity", border_style="red")

    def _thinking_panel(self):
        by_lvl = self.tel.get("mitm_thinking_by_level", {}) or {}
        total = sum(by_lvl.values()) or 1
        tbl = Table(expand=True, box=None)
        tbl.add_column("Thinking Tier", no_wrap=True)
        tbl.add_column("Count", justify="right")
        tbl.add_column("Intensity", ratio=2)
        for key, label, color in THINKING_TIERS:
            n = int(by_lvl.get(key, 0))
            bar_len = int((n / total) * 20)
            bar = Text("█" * bar_len + "░" * (20 - bar_len), style=color)
            tbl.add_row(Text(label, style=f"bold {color}"), str(n), bar)
        return Panel(tbl, title="AI Reasoning Profile", border_style="magenta")

    def _hotkey_panel(self):
        tbl = Table(expand=True, box=None, padding=(0, 0))
        tbl.add_column("Key", style="bold cyan", no_wrap=True, width=3)
        tbl.add_column("Function", no_wrap=True)
        tbl.add_row("S", "Start All")
        tbl.add_row("X", "Stop All")
        tbl.add_row("P", "Deep Patch")
        tbl.add_row("U", "Undo Patch")
        tbl.add_row("W", "Launch Windsurf")
        tbl.add_row("K", "Khoj Reindex")
        tbl.add_row("L", "Central Logs")
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
            elif "PROTOCOL EVENT" in line:
                content.append(line + "\n", style="bold green")
            else:
                content.append(line + "\n")
        
        footer = Text(
            "[1] proxy.log  [2] cascade.log  [3] khoj.log  [4] proxy_https.log  [B] Back",
            style="bold cyan", justify="center"
        )
        inner = Layout()
        inner.split_column(
            Layout(Panel(content, title=f"Central Intelligence Log: {self.log_name}", border_style="green"), ratio=9),
            Layout(Panel(footer, border_style="dim"), size=3),
        )
        return inner

    # ── layout ───────────────────────────────────────────────────────
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
            Layout(name="mid", size=10),
            Layout(name="events"),
            Layout(name="footer", size=3),
        )

        root["header"].update(Panel(
            Text("HIGH-GRAVITY PEGASUS CONTROL PLANE v3.1", justify="center", style="bold cyan"),
            border_style="cyan",
        ))

        root["top"].split_row(
            Layout(self._proxy_panel(), ratio=3),
            Layout(self._ai_agent_panel(), ratio=3),
            Layout(self._hotkey_panel(), ratio=2),
        )

        root["mid"].split_row(
            Layout(self._system_panel(), ratio=1),
            Layout(self._thinking_panel(), ratio=1),
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
                    r, _, _ = select.select([sys.stdin], [], [], 0.2)
                    if not r:
                        continue
                    c = sys.stdin.read(1).lower()

                    if self.view == "logs":
                        if c == "b" or c == "\x1b":
                            self.view = "main"
                        elif c == "1": self.log_name = "proxy.log"
                        elif c == "2": self.log_name = "cascade_midway.log"
                        elif c == "3": self.log_name = "khoj.log"
                        elif c == "4": self.log_name = "proxy_https.log"
                        elif c == "q": break
                        continue

                    # Main view keys
                    if c == "q":
                        break
                    elif c == "s":
                        self.run_cmd("System Start", "./hg.sh start")
                    elif c == "x":
                        self.run_cmd("System Stop", "./hg.sh stop")
                    elif c == "p":
                        self.run_cmd("Deep Patch", "./hg.sh patch")
                    elif c == "u":
                        self.run_cmd("Undo Patches", "./hg.sh undo")
                    elif c == "w":
                        # Launch Windsurf as detached background process
                        subprocess.Popen(
                            "nohup /usr/share/windsurf-next/windsurf-next > /dev/null 2>&1 &",
                            shell=True, start_new_session=True, cwd=REPO_ROOT
                        )
                        self.status_msg = "[green]Launching Windsurf Next...[/green]"
                    elif c == "k":
                        self.run_cmd("Khoj Reindex", "./hg.sh khoj reindex")
                    elif c == "l":
                        self.view = "logs"
                        self.log_name = "proxy.log"
                    elif c == "r":
                        self.action("rotate_keys")
                    elif c == "c":
                        self.action("clear_cache")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


if __name__ == "__main__":
    Dashboard().run()
