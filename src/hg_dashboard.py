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

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs"
PROXY_PORT = 9998
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
        self.install_status = {}
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
        self._check_install_status()
    
    def _check_install_status(self):
        """Check installation completeness"""
        import shutil
        self.install_status = {
            "python3": shutil.which("python3") is not None,
            "docker": shutil.which("docker") is not None,
            "aiohttp": self._check_python_pkg("aiohttp"),
            "fastapi": self._check_python_pkg("fastapi"),
            "khoj_image": self._check_docker_image("ghcr.io/khoj-ai/khoj"),
            "pgvector_image": self._check_docker_image("pgvector/pgvector"),
            "certs": (REPO_ROOT / "certs" / "proxy.crt").exists(),
            "patch_script": (REPO_ROOT / "src" / "patch_all.py").exists(),
        }
    
    def _check_python_pkg(self, pkg):
        try:
            __import__(pkg)
            return True
        except ImportError:
            return False
    
    def _check_docker_image(self, name):
        try:
            result = subprocess.run(
                ["docker", "images", "-q", name],
                capture_output=True, text=True, timeout=2
            )
            return bool(result.stdout.strip())
        except:
            return False

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
                if "server_url" in tok and not tok.startswith("http"):
                    continue
                if tok.startswith("http"):
                    return tok.strip("'").strip('"')
            # fallback: parse --api_server_url
            if "--api_server_url" in out:
                idx = out.index("--api_server_url")
                return out[idx:].split()[1].strip("'").strip('"')
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
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=REPO_ROOT)
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
        import subprocess, socket
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        # Windsurf
        api_url = self.windsurf_api_url()
        if api_url:
            proxied_domains = ["proxy.windsurf.com", "inferapi.windsurf.com", "server.self-serve.windsurf.com", "127.0.0.1"]
            if any(d in api_url for d in proxied_domains):
                tbl.add_row("Windsurf", "[green]PROXIED[/green]")
            else:
                tbl.add_row("Windsurf", f"[red]DIRECT {api_url[:28]}[/red]")
        else:
            tbl.add_row("Windsurf", "[dim]not running[/dim]")

        # Proxy ports
        def port_up(p):
            try:
                s = socket.create_connection(("127.0.0.1", p), timeout=0.5); s.close(); return True
            except: return False
        tbl.add_row("HTTP  :9998", "[green]UP[/green]" if port_up(9998) else "[red]DOWN[/red]")
        tbl.add_row("HTTPS :443",  "[green]UP[/green]" if port_up(443)  else "[yellow]DOWN[/yellow]")

        # iptables 50001→9998
        ipt = subprocess.run(
            ["sudo","-n","iptables","-t","nat","-C","OUTPUT","-p","tcp",
             "--dport","50001","-j","REDIRECT","--to-port","9998"],
            capture_output=True, text=True
        ).returncode == 0
        if not ipt:
            # Fallback to the hardcoded password if sudo -n fails
            ipt = subprocess.run(
                ["sudo","-S","iptables","-t","nat","-C","OUTPUT","-p","tcp",
                 "--dport","50001","-j","REDIRECT","--to-port","9998"],
                input="1786\n", capture_output=True, text=True
            ).returncode == 0
        tbl.add_row("ipt 50001→9998", "[green]ACTIVE[/green]" if ipt else "[red]MISSING[/red]")

        # Patches
        ext = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js")
        if ext.exists():
            try:
                is_opt = subprocess.run(
                    f"strings {ext} | grep -q 'globalThis.HG_OPT'",
                    shell=True
                ).returncode == 0
                if is_opt:
                    tbl.add_row("JS patch", "[green]✓ OK[/green]")
                else:
                    tbl.add_row("JS patch", "[red]✗ none[/red]")
            except:
                tbl.add_row("JS patch", "[yellow]~ unknown[/yellow]")
        from pathlib import Path as _P
        bin_path = _P("/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64")
        if bin_path.exists():
            is_shim = False
            try:
                with open(bin_path, "rb") as f:
                    header = f.read(16)
                    if b"#!/bin/bash" in header or b"#!/bin/sh" in header:
                        is_shim = True
            except: pass
            tbl.add_row("LSP Shield", "[green]✓ ACTIVE[/green]" if is_shim else "[yellow]~ binary[/yellow]")

        bin_real = _P("/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64.real")
        if bin_real.exists():
            with open(bin_real, "rb") as f:
                f.seek(0x818e12d); b = f.read(2)
            tbl.add_row("Bin patch", "[green]✓ NOP[/green]" if b == b'\x90\x90' else "[red]✗ orig[/red]")

        # TurboQuant cache stats
        tbl.add_row("TQ hits",  str(self.tel.get("tq_ann_hits", 0)))
        tbl.add_row("TQ index", str(self.tel.get("tq_index_size", 0)))
        ratio = self.tel.get("tq_raw_bytes", 0)
        cmp   = self.tel.get("tq_compressed_bytes", 0)
        if ratio > 0:
            tbl.add_row("TQ ratio", f"{cmp/ratio:.2f}x")

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

    def _install_panel(self):
        tbl = Table(expand=True, box=None, show_header=False)
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()
        
        checks = [
            ("Python3", "python3"),
            ("Docker", "docker"),
            ("aiohttp", "aiohttp"),
            ("FastAPI", "fastapi"),
            ("Khoj image", "khoj_image"),
            ("PGVector", "pgvector_image"),
            ("TLS certs", "certs"),
            ("Patcher", "patch_script"),
        ]
        
        for label, key in checks:
            status = self.install_status.get(key, False)
            icon = "[green]✓[/green]" if status else "[red]✗[/red]"
            tbl.add_row(label, icon)
        
        all_ok = all(self.install_status.values())
        color = "green" if all_ok else "yellow"
        return Panel(tbl, title="Installation", border_style=color)
    
    def _hotkey_panel(self):
        tbl = Table(expand=True, box=None, padding=(0, 0))
        tbl.add_column("Key", style="bold cyan", no_wrap=True, width=3)
        tbl.add_column("Action", no_wrap=True)
        tbl.add_row("S", "Start All")
        tbl.add_row("X", "Stop All")
        tbl.add_row("P", "Patch Client")
        tbl.add_row("H", "LSP Shield")
        tbl.add_row("W", "Launch Editor")
        tbl.add_row("C", "Clear Cache")
        tbl.add_row("R", "Rotate Keys")
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
            Layout(self._mitm_panel(), ratio=2),
            Layout(self._install_panel(), ratio=2),
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
                    elif c == "s":
                        self.run_cmd("Start", ["bash", "scripts/hg_start.sh", "start"])
                    elif c == "x":
                        self.run_cmd("Stop", ["bash", "scripts/hg_stop.sh", "--direct"])
                    elif c == "h":
                        self.run_cmd("Shield", ["bash", "scripts/deploy_lsp_shim.sh"])
                    elif c == "c":
                        self.action("clear_cache")
                    elif c == "r":
                        self.action("rotate_keys")
                    elif c == "p":
                        self.run_cmd("Patch", ["python3", "src/patch_all.py", "--force"])
                    elif c == "u":
                        self.run_cmd("Undo", ["python3", "src/patch_all.py", "--restore"])
                    elif c == "w":
                        subprocess.Popen(
                            ["/usr/share/windsurf-next/windsurf-next"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                        self.status_msg = "[green]Windsurf launching...[/green]"
                    elif c == "i":
                        self.run_cmd("Install", ["bash", "scripts/install.sh"])
                    elif c == "x":
                        self.run_cmd("Git push", ["git", "push", "origin", "main", "--no-verify"])
                    elif c == "l":
                        self.view = "logs"
                        self.log_name = "proxy.log"
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


if __name__ == "__main__":
    Dashboard().run()
