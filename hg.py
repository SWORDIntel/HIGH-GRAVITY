#!/usr/bin/env python3
"""
HIGH-GRAVITY Unified Launcher & Dashboard
========================================
The central hub for managing the optimization proxy, 
monitoring request traffic, and launching Windsurf.
"""

import os
import sys
import json
import time
import subprocess
import signal
import socket
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Deque
from collections import deque

import re # Added for pattern matching
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align
    from rich.spinner import Spinner
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.syntax import Syntax
    RICH_AVAILABLE = True
except ImportError:
    print("[!] Rich library not found. Please install with: pip install rich")
    sys.exit(1)

# --- Constants & Paths ---
VERSION = "3.1.0-HG"
PROXY_PORT = 9999
REPO_ROOT = Path(__file__).resolve().parent
PROXY_SCRIPT = REPO_ROOT / "tools" / "integration" / "highgravity_proxy.py"
LOG_FILE = REPO_ROOT / "logs" / "proxy.log"

console = Console()

class HighGravityDashboard:
    def __init__(self):
        self.proxy_proc = None
        self.running = True
        self.last_logs = []
        self.status_msg = "Dashboard initialized."
        self.proxy_status = "Stopped"
        self.proxy_port = PROXY_PORT
        self.active_keys_count = 0
        self.exhausted_keys_count = 0
        self.request_count = 0
        self.cache_hits = 0
        self.retry_count = 0
        self.rotation_mode = "round-robin"
        self.last_request_time = None
        self.selected_model = "auto"
        self.detected_model = "None"

        # High Sensitivity Pulse Data
        self.pulse_data = deque([0]*50, maxlen=50)
        self.key_stats = {}
        self.event_log = []

    def check_proxy_alive(self) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', self.proxy_port)) == 0

    def toggle_rotation(self):
        self.rotation_mode = "sticky" if self.rotation_mode == "round-robin" else "round-robin"
        try:
            import requests
            requests.post(f"http://127.0.0.1:{self.proxy_port}/hg/config", json={"rotation_mode": self.rotation_mode}, timeout=1)
            self.status_msg = f"Rotation set to: [bold magenta]{self.rotation_mode}[/bold magenta]"
        except:
            self.status_msg = "[red]Proxy connection failed for toggle.[/red]"

    def start_proxy(self):
        if self.check_proxy_alive(): return
        env = {**os.environ, "HG_PROXY_PORT": str(self.proxy_port), "HG_ROTATION_MODE": self.rotation_mode}
        self.proxy_proc = subprocess.Popen([sys.executable, str(PROXY_SCRIPT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, start_new_session=True)
        time.sleep(1)

    def stop_proxy(self):
        if self.proxy_proc:
            try: os.killpg(os.getpgid(self.proxy_proc.pid), signal.SIGTERM)
            except: pass
            self.proxy_proc = None

    def update_stats(self):
        if not LOG_FILE.exists(): return

        try:
            # Read last 100 lines for efficiency
            with open(LOG_FILE, 'r') as f:
                # Seek to near end
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - 20000)) # Last ~20KB
                lines = f.readlines()

            self.last_logs = []
            current_pulse = 0
            
            key_pattern = re.compile(r'KEY=([\w-]+)')
            ts_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')

            for line in lines:
                line = line.strip()
                match = ts_pattern.match(line)
                if not match: continue
                ts = match.group(1)

                # Broad Keyword Match for Display
                keywords = ["CONNECTION ATTEMPT", "GHOST_CACHE_HIT", "Silent Retry", "KEY_LIMIT", "ROTATION", "KEY_RECOVERED", "PULSE_METRIC", "NEW_SESSION_KEY_DISCOVERED"]
                if not any(k in line for k in keywords): continue

                if "CONNECTION ATTEMPT" in line:
                    self.request_count += 1
                    self.last_request_time = ts
                elif "GHOST_CACHE_HIT" in line:
                    self.cache_hits += 1
                elif "Silent Retry" in line or "KEY_LIMIT" in line:
                    self.retry_count += 1
                elif "PULSE_METRIC" in line:
                    try: 
                        bytes_val = int(line.split("BYTES=")[1].split(" ")[0])
                        current_pulse += bytes_val
                    except: pass
                
                # Key Tracking
                km = key_pattern.search(line)
                if km:
                    key = km.group(1)
                    self.key_stats.setdefault(key, {'requests': 0, 'status': 'Active'})
                    if "KEY_EXHAUSTED" in line:
                        self.key_stats[key]['status'] = 'Exhausted'
                    elif "KEY_RECOVERED" in line or "ROTATION" in line:
                        self.key_stats[key]['status'] = 'Active'
                    
                    if "ROTATION" in line: self.key_stats[key]['requests'] += 1

                # Format Display Line
                color = "cyan"
                if "CACHE" in line: color = "magenta"
                elif "Retry" in line or "LIMIT" in line: color = "red"
                elif "RECOVERED" in line: color = "green"
                elif "NEW_SESSION" in line: color = "yellow"
                
                clean_msg = line.split("] ")[-1] if "] " in line else line
                self.last_logs.append(f"[bold {color}]»[/bold {color}] {clean_msg}")

            # Sensitive Pulse Scaling (Logarithmic view)
            if current_pulse > 0:
                # Value of 1 for tiny reqs, scales up to 10 for huge ones
                scaled = min(10, (current_pulse.bit_length() // 2) + 1)
                self.pulse_data.append(scaled)
            else:
                self.pulse_data.append(0)
            
            all_keys = self.key_stats.keys()
            self.active_keys_count = len([k for k in all_keys if self.key_stats[k].get('status') == 'Active'])
            self.exhausted_keys_count = len([k for k in all_keys if self.key_stats[k].get('status') == 'Exhausted'])
            self.last_logs = self.last_logs[-12:]

        except: pass

    def generate_dashboard(self) -> Layout:
        self.update_stats()
        is_alive = self.check_proxy_alive()

        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="sidebar", ratio=1),
            Layout(name="body", ratio=4)
        )
        layout["body"].split_column(
            Layout(name="metrics", size=10),
            Layout(name="pulse", size=8),
            Layout(name="logs")
        )

        header_text = Text.assemble((" HIGH-GRAVITY v3.1 ", "bold white on blue"), " Real-time Identity & Data Shield", justify="center")
        layout["header"].update(Panel(header_text, border_style="blue"))

        # Metrics Panel
        metrics = Table.grid(expand=True)
        metrics.add_row(Text("Total Requests:", style="bold"), f"[bold white]{self.request_count}[/bold white]")
        metrics.add_row(Text("Ghost Cache Hits:", style="bold"), f"[bold magenta]{self.cache_hits}[/bold magenta]")
        metrics.add_row(Text("Invisible Retries:", style="bold"), f"[bold red]{self.retry_count}[/bold red]")
        metrics.add_row(Text("Active / Dead Keys:", style="bold"), f"[bold green]{self.active_keys_count}[/bold green] / [bold red]{self.exhausted_keys_count}[/bold red]")
        metrics.add_row(Text("Rotation Mode:", style="bold"), f"[bold yellow]{self.rotation_mode.upper()}[/bold yellow]")
        metrics.add_row(Text("Last Request:", style="bold"), f"[dim]{self.last_request_time or 'Never'}[/dim]")
        layout["metrics"].update(Panel(metrics, title="System Metrics", border_style="white"))

        # Visual Pulse (Highly Sensitive)
        pulse_str = ""
        chars = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█", "█", "█"]
        for val in self.pulse_data:
            color = "dim blue"
            if val > 0: color = "green" if val < 4 else "yellow" if val < 7 else "red"
            char = chars[val]
            pulse_str += f"[{color}]{char}[/{color}]"
        
        layout["pulse"].update(Panel(Align.center(Text.from_markup(pulse_str)), title="Activity Pulse (Data Flow)", border_style="cyan"))

        # Logs
        log_content = Text.from_markup("\n".join(self.last_logs)) if self.last_logs else Text("Monitoring proxy.log...", style="dim")
        layout["logs"].update(Panel(log_content, title="Intercepted Events", border_style="dim"))

        # Sidebar
        sidebar = Table.grid(expand=True)
        sidebar.add_row("[cyan]W[/cyan] - Launch Windsurf")
        sidebar.add_row("[cyan]P[/cyan] - Toggle Proxy")
        sidebar.add_row("[cyan]R[/cyan] - Toggle Rotation")
        sidebar.add_row("[cyan]Q[/cyan] - Quit")
        sidebar_panel = Table.grid(expand=True)
        sidebar_panel.add_row(Panel(sidebar, title="Actions", border_style="cyan"))
        sidebar_panel.add_row(Panel(Text(f"Proxy: {'ON' if is_alive else 'OFF'}", style="bold green" if is_alive else "bold red"), title="Status", border_style="dim"))
        layout["sidebar"].update(sidebar_panel)

        layout["footer"].update(Panel(Text(f"Last sync: {datetime.now().strftime('%H:%M:%S')} | Log: {LOG_FILE}", justify="center", style="dim blue"), border_style="blue"))
        return layout

    def run(self):
        import select, tty, termios
        fd = sys.stdin.fileno()
        is_tty = os.isatty(fd)
        if is_tty: old_settings = termios.tcgetattr(fd)
        if not self.check_proxy_alive(): self.start_proxy()

        try:
            if is_tty: tty.setcbreak(fd)
            with Live(self.generate_dashboard(), refresh_per_second=4, screen=True) as live:
                while self.running:
                    live.update(self.generate_dashboard())
                    if is_tty:
                        r, _, _ = select.select([sys.stdin], [], [], 0.1)
                        if r:
                            c = sys.stdin.read(1).lower()
                            if c == 'q': self.running = False
                            elif c == 'p': (self.stop_proxy() if self.check_proxy_alive() else self.start_proxy())
                            elif c == 'r': self.toggle_rotation()
        finally:
            if is_tty: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    HighGravityDashboard().run()
