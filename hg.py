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
import random
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
VERSION = "3.4.0-HG"
PROXY_PORT = 9999
REPO_ROOT = Path(__file__).resolve().parent
PROXY_SCRIPT = REPO_ROOT / "tools" / "integration" / "highgravity_proxy.py"
LOG_FILE = REPO_ROOT / "logs" / "proxy.log"

console = Console()

class HighGravityDashboard:
    def __init__(self):
        self.proxy_proc = None
        self.running = True
        self.last_logs = deque(maxlen=15)
        self.status_msg = "Dashboard initialized."
        self.proxy_status = "Stopped"
        self.proxy_port = PROXY_PORT
        
        # Cumulative Metrics
        self.request_count = 0
        self.cache_hits = 0
        self.retry_count = 0
        self.active_keys_count = 0
        self.exhausted_keys_count = 0
        self.tokens_saved = 0
        
        self.rotation_mode = "round-robin"
        self.last_request_time = None
        self.selected_model = "auto"
        self.detected_model = "None"

        # --- Dynamic Flow System ---
        self.pulse_width = 60
        self.pulse_data = deque([0]*self.pulse_width, maxlen=self.pulse_width)
        self.packet_track = [" "] * self.pulse_width
        self._last_pulse_val = 0
        self._frame_count = 0
        
        self.key_stats = {}
        self._last_log_size = 0
        self._initial_scan_done = False

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
        if self.check_proxy_alive():
            self.status_msg = "[yellow]Attached to existing proxy process.[/yellow]"
            return
            
        env = {**os.environ, "HG_PROXY_PORT": str(self.proxy_port), "HG_ROTATION_MODE": self.rotation_mode}
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.proxy_proc = subprocess.Popen([sys.executable, str(PROXY_SCRIPT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, start_new_session=True)
        self.status_msg = "Proxy starting..."
        time.sleep(1)

    def stop_proxy(self):
        subprocess.run(["pkill", "-f", "highgravity_proxy.py"], stderr=subprocess.DEVNULL)
        self.proxy_proc = None
        self.status_msg = "Proxy stopped."

    def update_stats(self):
        self._frame_count += 1
        
        # Advance packet track
        self.packet_track.pop(0)
        self.packet_track.append(" ")

        if not LOG_FILE.exists(): return

        try:
            current_size = LOG_FILE.stat().st_size
            
            if current_size < self._last_log_size or not self._initial_scan_done:
                with open(LOG_FILE, 'r') as f:
                    f.seek(max(0, current_size - 100000))
                    lines = f.readlines()
                self._initial_scan_done = True
                self._last_log_size = current_size
            elif current_size == self._last_log_size:
                # Decay visual pulse if no new data
                if self._frame_count % 2 == 0:
                    self._last_pulse_val = max(0, self._last_pulse_val - 1)
                self.pulse_data.append(self._last_pulse_val)
                return
            else:
                read_bytes = current_size - self._last_log_size
                with open(LOG_FILE, 'rb') as f:
                    f.seek(self._last_log_size)
                    data = f.read(read_bytes).decode('utf-8', errors='ignore')
                    lines = data.splitlines()
                self._last_log_size = current_size

            current_activity_spike = 0
            key_pattern = re.compile(r'KEY=([\w-]+)')
            ts_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')

            for line in lines:
                line = line.strip()
                if not line: continue
                
                match = ts_pattern.match(line)
                ts = match.group(1) if match else None

                if "CONNECTION ATTEMPT" in line:
                    self.request_count += 1
                    if ts: self.last_request_time = ts
                    current_activity_spike = 10
                    # Inject a "packet"
                    self.packet_track[-1] = "[cyan]◆[/cyan]"
                elif "GHOST_CACHE_HIT" in line:
                    self.cache_hits += 1
                    current_activity_spike = 8
                    self.packet_track[-1] = "[magenta]⚡[/magenta]"
                    
                    tok_match = re.search(r'\(Saved:\s*(\d+)\s*tokens\)', line)
                    if tok_match:
                        self.tokens_saved = int(tok_match.group(1))
                        
                elif "Silent Retry" in line or "KEY_LIMIT" in line or "AUTH_FAIL" in line:
                    self.retry_count += 1
                    current_activity_spike = 6
                    self.packet_track[-1] = "[red]✖[/red]"
                elif "PULSE_METRIC" in line:
                    current_activity_spike = max(current_activity_spike, 4)
                    self.packet_track[-1] = "[blue]·[/blue]"
                
                km = key_pattern.search(line)
                if km:
                    key = km.group(1)
                    self.key_stats.setdefault(key, {'requests': 0, 'status': 'Active'})
                    if "KEY_EXHAUSTED" in line:
                        self.key_stats[key]['status'] = 'Exhausted'
                    elif "KEY_RECOVERED" in line or "ROTATION" in line or "NEW_SESSION" in line:
                        self.key_stats[key]['status'] = 'Active'
                    if "ROTATION" in line: self.key_stats[key]['requests'] += 1

                if any(k in line for k in ["CONNECTION", "CACHE", "Retry", "LIMIT", "ROTATION", "RECOVERED", "NEW_SESSION", "AUTH_FAIL", "ONLINE", "UNLEASH"]):
                    color = "cyan"
                    if "CACHE" in line: color = "magenta"
                    elif "Retry" in line or "LIMIT" in line or "AUTH_FAIL" in line: color = "red"
                    elif "RECOVERED" in line: color = "green"
                    elif "NEW_SESSION" in line: color = "yellow"
                    elif "ONLINE" in line: color = "blue"
                    elif "UNLEASH_SHIELD" in line: color = "bold white on green"
                    elif "UNLEASH_INTERCEPT" in line: color = "bold green"
                    elif "UNLEASH_BYPASS" in line: color = "bold yellow"
                    
                    clean_msg = line.split("] ")[-1] if "] " in line else line
                    if len(clean_msg) > 85: clean_msg = clean_msg[:82] + "..."
                    self.last_logs.append(f"[bold {color}]»[/bold {color}] {clean_msg}")

            if current_activity_spike > 0:
                self._last_pulse_val = current_activity_spike
            else:
                self._last_pulse_val = max(0, self._last_pulse_val - 1)
            
            self.pulse_data.append(self._last_pulse_val)
            
            # Key Counts
            all_keys = self.key_stats.keys()
            self.active_keys_count = len([k for k in all_keys if self.key_stats[k].get('status') == 'Active'])
            self.exhausted_keys_count = len([k for k in all_keys if self.key_stats[k].get('status') == 'Exhausted'])

        except Exception as e:
            self.status_msg = f"[red]Update error: {e}[/red]"

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
            Layout(name="metrics", size=12),
            Layout(name="pulse", size=8),
            Layout(name="logs")
        )

        header_text = Text.assemble((" [N]SO-ISOLATION ", "bold white on dark_red"), " Cyber-Intelligence Gateway", justify="center")
        layout["header"].update(Panel(header_text, border_style="bright_black"))

        metrics = Table.grid(expand=True)
        metrics.add_row(Text("Total Intercepts:", style="bold"), f"[bold white]{self.request_count}[/bold white]")
        metrics.add_row(Text("Ghost Cache Hits:", style="bold"), f"[bold red]{self.cache_hits}[/bold red]")
        
        # Calculate estimated savings ($15 per 1M tokens)
        est_savings = (self.tokens_saved / 1000000) * 15.0
        savings_str = f"[bold green]${est_savings:.4f}[/bold green]" if est_savings > 0 else "[dim]$0.0000[/dim]"
        metrics.add_row(Text("Exfiltrated Tokens:", style="bold"), f"[bold red]{self.tokens_saved:,}[/bold red] ({savings_str})")
        
        metrics.add_row(Text("Blocked Retries:", style="bold"), f"[bold bright_red]{self.retry_count}[/bold bright_red]")
        metrics.add_row(Text("Active / Dead Nodes:", style="bold"), f"[bold white]{self.active_keys_count}[/bold white] / [bold red]{self.exhausted_keys_count}[/bold red]")
        metrics.add_row(Text("Injection Mode:", style="bold"), f"[bold dark_red]{self.rotation_mode.upper()}[/bold dark_red]")
        
        # New Phantom Features Status
        metrics.add_row(Text("Shadow Spoofing:", style="bold"), "[bold red]ENABLED[/bold red]")
        has_rules = Path(".highgravity_rules").exists()
        rag_status = "[bold white]ACTIVE[/bold white]" if has_rules else "[dim]INACTIVE[/dim]"
        metrics.add_row(Text("Local Intelligence:", style="bold"), rag_status)
        
        metrics.add_row(Text("Last Contact:", style="bold"), f"[dim]{self.last_request_time or 'None'}[/dim]")
        layout["metrics"].update(Panel(metrics, title="Pegasus-Grade Metrics", border_style="red"))

        # --- Dynamic Flow Pulse ---
        pulse_str = ""
        chars = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█", "█", "█"]
        
        # Build the waveform line
        for i, val in enumerate(self.pulse_data):
            # Check if there is a packet at this position
            packet = self.packet_track[i]
            if packet != " ":
                pulse_str += packet
            else:
                color = "grey37"
                if val > 0: color = "dark_red" if val < 4 else "red" if val < 7 else "bright_red"
                char = chars[val]
                pulse_str += f"[{color}]{char}[/{color}]"
        
        # Animated background noise
        bg_noise = "".join(random.choice(["'", "`", ".", " ", " "]) for _ in range(self.pulse_width - len(self.pulse_data)))
        
        layout["pulse"].update(Panel(Align.center(Text.from_markup(pulse_str + bg_noise)), title="Real-time Packet Interception", border_style="bright_black"))

        log_content = Text.from_markup("\n".join(list(self.last_logs))) if self.last_logs else Text("Scanning uplink...", style="dim")
        layout["logs"].update(Panel(log_content, title="Intercepted Feed", border_style="dim"))

        sidebar = Table.grid(expand=True)
        sidebar.add_row("[red]W[/red] - Infiltrate Windsurf")
        sidebar.add_row("[red]P[/red] - Reset Proxy Uplink")
        sidebar.add_row("[red]R[/red] - Cycle Rotation")
        sidebar.add_row("[red]Q[/red] - Terminate")
        sidebar_panel = Table.grid(expand=True)
        sidebar_panel.add_row(Panel(sidebar, title="Operations", border_style="red"))
        sidebar_panel.add_row(Panel(Text(f"UPLINK: {'STABLE' if is_alive else 'DOWN'}", style="bold white" if is_alive else "bold red"), title="Status", border_style="bright_black"))
        layout["sidebar"].update(sidebar_panel)

        layout["footer"].update(Panel(Text(f"v{VERSION} | PID: {os.getpid()} | RECON: {LOG_FILE}", justify="center", style="dim red"), border_style="red"))
        return layout

    def launch_windsurf(self):
        """Attempts to launch via profile script first, then system binary."""
        self.status_msg = "Locating latest Windsurf profile..."
        try:
            import glob
            profile_scripts = sorted(glob.glob(str(REPO_ROOT / "windsurf_profiles" / "*" / "launch_windsurf.sh")), 
                                   key=os.path.getmtime, reverse=True)
            if profile_scripts:
                script_path = profile_scripts[0]
                self.status_msg = f"Launching via profile: [bold cyan]{Path(script_path).parent.name}[/bold cyan]..."
                env = {**os.environ, "WINDSURF_BIN": "windsurf-next"}
                if not shutil.which("windsurf-next"): env["WINDSURF_BIN"] = "windsurf"
                subprocess.Popen(["bash", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, start_new_session=True)
                return
        except: pass

        potential_cmds = ["windsurf-next", "windsurf", "codeium-windsurf"]
        for cmd in potential_cmds:
            cmd_path = shutil.which(cmd)
            if cmd_path:
                self.status_msg = f"Launching binary: [bold cyan]{cmd_path}[/bold cyan]..."
                subprocess.Popen([cmd_path, "--new-window"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                return
        self.status_msg = "[red]Error: Could not find launch script or binary.[/red]"

    def run(self):
        import select, tty, termios
        fd = sys.stdin.fileno()
        is_tty = os.isatty(fd)
        if is_tty: old_settings = termios.tcgetattr(fd)
        self.start_proxy()

        try:
            if is_tty: tty.setcbreak(fd)
            # Increased refresh rate for smoother animation
            with Live(self.generate_dashboard(), refresh_per_second=10, screen=True) as live:
                while self.running:
                    live.update(self.generate_dashboard())
                    if is_tty:
                        r, _, _ = select.select([sys.stdin], [], [], 0.05)
                        if r:
                            c = sys.stdin.read(1).lower()
                            if c == 'q': self.running = False
                            elif c == 'p': self.stop_proxy(); time.sleep(0.5); self.start_proxy()
                            elif c == 'r': self.toggle_rotation()
                            elif c == 'w': self.launch_windsurf()
        finally:
            if is_tty: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    HighGravityDashboard().run()
