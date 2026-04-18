#!/usr/bin/env python3
"""
HIGH-GRAVITY Cybernetic Dashboard v3.6.0
Live monitor for the proxy + MITM bridge.

Surfaces:
  * Proxy core (cache hits, key pool, rotation, exhausted keys)
  * MITM mode + auto-detected services (Gemini / Codex / OpenAI)
  * Premium model upgrades (total, per-service, per-tier)
  * Codex 4-tier reasoning distribution (Low / Medium / High / Extra High)
  * Rate-limit interceptions
  * Recent event ring buffer
"""

import sys
import time
from datetime import datetime

import requests
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# Codex CLI tier names + colors so the dashboard mirrors the Codex picker.
THINKING_TIERS = [
    ("low",     "Low",        "Fast responses, light reasoning",         "cyan"),
    ("medium",  "Medium",     "Balanced speed/depth (everyday tasks)",   "green"),
    ("high",    "High",       "Greater depth (Codex default)",           "yellow"),
    ("xhigh",   "Extra High", "Non-latency-sensitive deep reasoning",    "magenta"),
]



class CyberDashboard:
    def __init__(self, proxy_port: int = 9999):
        self.proxy_port = proxy_port
        self.telemetry: dict = {}
        self.status = "Initializing..."
        self.last_fetch = 0.0


    # ---------- transport ------------------------------------------------
    def fetch_telemetry(self):
        try:
            r = requests.get(
                f"http://127.0.0.1:{self.proxy_port}/hg/telemetry", timeout=1
            )
            self.telemetry = r.json()
            self.status = "[green]Proxy Online[/green]"
        except Exception:
            self.status = "[red]Proxy Offline[/red]"
        self.last_fetch = time.time()

    def send_action(self, action: str):
        try:
            requests.post(
                f"http://127.0.0.1:{self.proxy_port}/hg/manage",
                json={"action": action},
                timeout=1,
            )
            self.status = f"[green]Action: {action} \u2192 OK[/green]"
        except Exception:
            self.status = f"[red]Action: {action} \u2192 failed[/red]"

    # ---------- panels ---------------------------------------------------
    def _proxy_panel(self) -> Panel:
        t = self.telemetry
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()
        tbl.add_row("Status",          str(t.get("status", "?")))
        tbl.add_row("Proxy port",      str(t.get("proxy_port", "?")))
        tbl.add_row("Active keys",     str(t.get("active_keys", 0)))
        tbl.add_row("Exhausted keys",  str(t.get("exhausted_keys", 0)))
        tbl.add_row("Rotation",        str(t.get("rotation_mode", "?")))
        tbl.add_row("Cache hits",      str(t.get("cache_hits", 0)))
        return Panel(tbl, title="Proxy Core", border_style="green")

    def _mitm_panel(self) -> Panel:
        t = self.telemetry
        mode = t.get("mitm_mode", "?")
        auto = "on" if t.get("mitm_auto_detect") else "off"
        prem = "on" if t.get("mitm_inject_premium") else "off"
        rl   = "on" if t.get("mitm_reduce_rate_limits") else "off"

        enabled  = t.get("mitm_services_enabled", []) or []
        detected = set(t.get("mitm_detected_services", []) or [])

        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()
        tbl.add_row("Mode",         mode)
        tbl.add_row("Auto-detect",  auto)
        tbl.add_row("Inject premium", prem)
        tbl.add_row("RL reduction", rl)

        # Per-service detection grid (online = detected, idle = enabled, off = disabled)
        svc_grid = Text()
        for svc in ("gemini", "codex", "openai"):
            if svc in detected:
                svc_grid.append(f" [{svc.upper()}] ", style="bold green on black")
            elif svc in enabled:
                svc_grid.append(f" [{svc.upper()}] ", style="dim white")
            else:
                svc_grid.append(f" [{svc.upper()}] ", style="bold red")
            svc_grid.append("  ")
        tbl.add_row("Services", svc_grid)

        tbl.add_row("Upgrades",   str(t.get("mitm_upgrades_total", 0)))
        tbl.add_row("RL hits",    str(t.get("mitm_rate_limit_hits", 0)))
        return Panel(tbl, title="MITM Bridge", border_style="magenta")

    def _upgrades_panel(self) -> Panel:
        by_svc  = self.telemetry.get("mitm_upgrades_by_service", {}) or {}
        by_tier = self.telemetry.get("mitm_upgrades_by_tier", {}) or {}

        tbl = Table(expand=True, box=None)
        tbl.add_column("Service", style="cyan")
        tbl.add_column("Upgrades", justify="right")
        for svc in ("gemini", "codex", "openai"):
            tbl.add_row(svc.title(), str(by_svc.get(svc, 0)))
        tbl.add_row("", "")
        tbl.add_row("[bold]Tier[/bold]", "[bold]Count[/bold]")
        tbl.add_row("Fast", str(by_tier.get("fast", 0)))
        tbl.add_row("Deep", str(by_tier.get("deep", 0)))
        return Panel(tbl, title="Premium Upgrades", border_style="yellow")

    def _thinking_panel(self) -> Panel:
        by_lvl = self.telemetry.get("mitm_thinking_by_level", {}) or {}
        total  = sum(by_lvl.values()) or 1

        tbl = Table(expand=True, box=None)
        tbl.add_column("Tier", no_wrap=True)
        tbl.add_column("Count", justify="right")
        tbl.add_column("Bar", ratio=2)
        tbl.add_column("Description")

        for key, label, desc, color in THINKING_TIERS:
            n = int(by_lvl.get(key, 0))
            bar_len = int((n / total) * 20)
            bar = Text("\u2588" * bar_len + "\u2591" * (20 - bar_len), style=color)
            tbl.add_row(
                Text(label, style=f"bold {color}"),
                str(n),
                bar,
                Text(desc, style="dim"),
            )
        # Always show minimal as well if it ever fires.
        m = int(by_lvl.get("minimal", 0))
        if m:
            tbl.add_row("Minimal", str(m), "", "Reasoning disabled")

        return Panel(tbl, title="Codex Reasoning Distribution", border_style="blue")

    def _events_panel(self) -> Panel:
        events = self.telemetry.get("mitm_recent_events", []) or []
        tbl = Table(expand=True, box=None)
        tbl.add_column("Time",  style="dim", no_wrap=True)
        tbl.add_column("Kind",  no_wrap=True)
        tbl.add_column("Detail")
        kind_colors = {
            "detect":    "cyan",
            "upgrade":   "yellow",
            "thinking":  "blue",
            "ratelimit": "red",
        }
        for ev in list(reversed(events))[:14]:  # newest first
            ts = datetime.fromtimestamp(ev.get("ts", 0)).strftime("%H:%M:%S")
            kind = ev.get("kind", "?")
            color = kind_colors.get(kind, "white")
            tbl.add_row(ts, Text(kind, style=color), ev.get("detail", ""))
        return Panel(tbl, title="Recent MITM Events", border_style="red")

    def _controls_panel(self) -> Panel:
        ctrl = Table(expand=True, box=None)
        ctrl.add_column("Key", style="bold cyan", no_wrap=True)
        ctrl.add_column("Action")
        ctrl.add_row("C", "Clear local ghost cache")
        ctrl.add_row("R", "Force key rotation")
        ctrl.add_row("Q", "Quit dashboard")
        return Panel(ctrl, title="Controls", border_style="yellow")

    # ---------- layout ---------------------------------------------------
    def generate_layout(self) -> Layout:
        self.fetch_telemetry()
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="top", size=11),
            Layout(name="middle", size=12),
            Layout(name="events"),
            Layout(name="footer", size=3),
        )

        layout["header"].update(
            Panel(
                Text(
                    "HIGH-GRAVITY  \u2014  PROXY + MITM BRIDGE  MONITOR",
                    justify="center",
                    style="bold cyan",
                ),
                border_style="cyan",
            )
        )

        layout["top"].split_row(
            Layout(self._proxy_panel(), name="proxy"),
            Layout(self._mitm_panel(),  name="mitm"),
            Layout(self._controls_panel(), name="controls"),
        )

        layout["middle"].split_row(
            Layout(self._upgrades_panel(),  name="upgrades", ratio=1),
            Layout(self._thinking_panel(),  name="thinking", ratio=2),
        )

        layout["events"].update(self._events_panel())

        layout["footer"].update(
            Panel(
                Text(
                    f"Status: {self.status}    "
                    f"Last fetch: {datetime.fromtimestamp(self.last_fetch).strftime('%H:%M:%S')}",
                    justify="center",
                ),
                border_style="dim",
            )
        )
        return layout

    # ---------- main loop ------------------------------------------------
    def run(self):
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)

        try:
            with Live(self.generate_layout(), refresh_per_second=2, screen=True) as live:
                while True:
                    live.update(self.generate_layout())
                    r, _, _ = select.select([sys.stdin], [], [], 0.25)
                    if r:
                        c = sys.stdin.read(1).lower()
                        if c == "q":
                            break
                        elif c == "c":
                            self.send_action("clear_cache")
                        elif c == "r":
                            self.send_action("rotate_keys")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


if __name__ == "__main__":
    CyberDashboard().run()
