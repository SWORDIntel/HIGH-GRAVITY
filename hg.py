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
import select
import tty
import termios
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Deque
from collections import deque

import re
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
    from rich.prompt import Prompt
    RICH_AVAILABLE = True
except ImportError:
    print("[!] Rich library not found. Please install with: pip install rich")
    sys.exit(1)

# --- Constants & Paths ---
VERSION = "3.4.0-HG"
PROXY_PORT = 9999
REPO_ROOT = Path(__file__).resolve().parent
PROXY_SCRIPT = REPO_ROOT / "src" / "proxy.py"
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
        self.total_bytes_transmitted = 0
        
        self.rotation_mode = "round-robin"
        self.last_request_time = None
        self.selected_model = "auto"
        self.detected_model = "None"

        # --- Dynamic Flow System ---
        self.pulse_width = 60
        self.pulse_data = deque([0]*self.pulse_width, maxlen=self.pulse_width)
        self._last_pulse_val = 0
        self._frame_count = 0
        self.sync_countdown = 60

    def check_proxy_alive(self) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', self.proxy_port)) == 0

    def start_proxy(self):
        if self.check_proxy_alive():
            self.status_msg = "[yellow]Attached to existing proxy process.[/yellow]"
            return
        
        self.status_msg = "Starting Pegasus Proxy Uplink..."
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        try:
            self.proxy_proc = subprocess.Popen([sys.executable, str(PROXY_SCRIPT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, start_new_session=True)
            time.sleep(2)
            if self.check_proxy_alive():
                self.status_msg = "[bold green]Uplink Established.[/bold green]"
            else:
                self.status_msg = "[red]Uplink Failed.[/red]"
        except Exception as e:
            self.status_msg = f"[red]Launch Error: {str(e)}[/red]"

    def stop_proxy(self):
        if self.proxy_proc:
            self.proxy_proc.terminate()
            self.proxy_proc = None
        # Also kill any orphaned proxy processes
        subprocess.run(["pkill", "-f", "src/proxy.py"], stderr=subprocess.DEVNULL)
        self.status_msg = "[yellow]Uplink Severed.[/yellow]"

    def launch_windsurf(self):
        self.status_msg = "Launching [bold cyan]Windsurf[/bold cyan] via shield..."
        script_path = REPO_ROOT / "bin" / "launch_debug.sh"
        if script_path.exists():
            subprocess.Popen(["bash", str(script_path)], start_new_session=True)
        else:
            self.status_msg = "[red]Launch script not found.[/red]"

    def launch_claude(self):
        self.status_msg = "Launching [bold cyan]Claude Interface[/bold cyan] via proxy..."
        script_path = REPO_ROOT / "bin" / "launch_claude_interface.sh"
        if script_path.exists():
            subprocess.Popen(["bash", str(script_path)], start_new_session=True)
        else:
            self.status_msg = "[red]Interface script not found.[/red]"

    def handle_input(self, c):
        if c == 'i':
            directive = Prompt.ask("\n[bold cyan]PEGASUS-DIRECTIVE[/bold cyan]")
            if directive:
                self.status_msg = f"Dispatching to Swarm Director: {directive}"
                # Issue task to DIRECTOR via UFP Bridge
                try:
                    from lib.protocols.ufp_bridge import UFPBridge
                    bridge = UFPBridge()
                    bridge.send_task("DIRECTOR", directive)
                except Exception as e:
                    self.status_msg = f"[red]Directive Dispatch Failed: {str(e)}[/red]"
        elif c == 'e':
            self.status_msg = "Codebase Evolution Loop Dispatched..."
            try:
                from src.pegasus.evolution.patcher_loop import PatcherLoop
                from src.pegasus.subagent_manager import SubAgentManager
                PatcherLoop(SubAgentManager()).execute_cycle(".")
            except Exception as e:
                self.status_msg = f"[red]Evolution Failed: {str(e)}[/red]"
        elif c == 't':
            self.status_msg = "Exploit Research & POC Documentation Dispatched..."
            try:
                from src.pegasus.evolution.red_team_loop import RedTeamLoop
                from src.pegasus.subagent_manager import SubAgentManager
                # Target the current workspace by default
                RedTeamLoop(SubAgentManager()).execute_red_team(".")
            except Exception as e:
                self.status_msg = f"[red]Exploit Research Failed: {str(e)}[/red]"
        elif c == 's':
            self.status_msg = "Global State Superposition Sync..."
            try:
                from src.pegasus.subagent_manager import SubAgentManager
                SubAgentManager().checkpoint_swarm()
            except Exception as e:
                self.status_msg = f"[red]Sync Failed: {str(e)}[/red]"

    def generate_dashboard(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="sidebar", size=40),
            Layout(name="body", ratio=1)
        )
        layout["body"].split_column(
            Layout(name="pulse", size=10),
            Layout(name="logs", ratio=1)
        )

        # Header
        layout["header"].update(Panel(Align.center(Text("HIGH-GRAVITY Pegasus Swarm Control Plane", style="bold red")), border_style="red"))

        # Footer
        is_alive = self.check_proxy_alive()
        layout["footer"].update(Panel(Text(f"v{VERSION} | PID: {os.getpid()} | RECON: {LOG_FILE} | UPLINK: {'STABLE' if is_alive else 'DOWN'}", justify="center"), border_style="dim"))

        # Sidebar - Metrics & Operations
        metrics = Table.grid(expand=True)
        metrics.add_row(Text("Intercepts:", style="bold"), f"[bold white]{self.request_count}[/bold white]")
        metrics.add_row(Text("Cache Hits:", style="bold"), f"[bold green]{self.cache_hits}[/bold green]")
        metrics.add_row(Text("Tokens Saved:", style="bold"), f"[bold cyan]{self.tokens_saved}[/bold cyan]")
        
        status_table = Table(title="Pegasus Core Infrastructure", expand=True)
        status_table.add_column("System", style="bold white")
        status_table.add_column("Status", style="bold green")
        status_table.add_row("GSL", "SYNCED")
        status_table.add_row("Hilbert Index", "MAPPED")
        status_table.add_row("MSHW Node", "ACTIVE")
        status_table.add_row("Sync", f"{self.sync_countdown}s")

        sidebar = Table.grid(expand=True)
        sidebar.add_row(Panel(metrics, title="Metrics", border_style="cyan"))
        sidebar.add_row(Panel(status_table, title="Infrastructure", border_style="magenta"))
        
        ops = Table.grid(expand=True)
        ops.add_row("[red]W[/red] - Windsurf")
        ops.add_row("[red]C[/red] - Claude")
        ops.add_row("[blue]N[/blue] - [bold]Join MSNET[/bold]")
        ops.add_row("[green]E[/green] - Evolve")
        ops.add_row("[yellow]T[/yellow] - Red-Team")
        ops.add_row("[cyan]I[/cyan] - Directive")
        ops.add_row("[red]S[/red] - Sync")
        ops.add_row("[red]Q[/red] - Quit")
        sidebar.add_row(Panel(ops, title="Operations", border_style="red"))
        
        layout["sidebar"].update(sidebar)

        # Pulse View
        chars = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        pulse_str = ""
        for val in self.pulse_data:
            pulse_str += chars[val]
        layout["pulse"].update(Panel(Align.center(Text(pulse_str, style="bold red")), title="Network Pulse", border_style="dim"))

        # Discourse Feed
        discourse = Table(title="Live Agent Discourse", expand=True)
        discourse.add_column("From", style="cyan")
        discourse.add_column("To", style="magenta")
        discourse.add_column("Directive", style="white")
        
        # Pull from logs
        try:
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()[-10:]
                for line in lines:
                    if "UFP_MSG" in line:
                        discourse.add_row("AGENT", "SWARM", "Executing Binary Directive")
        except: pass
        
        layout["logs"].update(Panel(discourse, title="Discourse Feed", border_style="bold blue"))

        return layout

    def run(self):
        fd = sys.stdin.fileno()
        is_tty = os.isatty(fd)
        if is_tty: old_settings = termios.tcgetattr(fd)
        self.start_proxy()
        
        last_sync = time.time()
        try:
            if is_tty: tty.setcbreak(fd)
            with Live(self.generate_dashboard(), refresh_per_second=10, screen=True) as live:
                while self.running:
                    elapsed = time.time() - last_sync
                    self.sync_countdown = max(0, 60 - int(elapsed))
                    if self.sync_countdown == 0:
                        self.status_msg = "Global State Sync..."
                        last_sync = time.time()
                    
                    live.update(self.generate_dashboard())
                    if is_tty:
                        r, _, _ = select.select([sys.stdin], [], [], 0.05)
                        if r:
                            c = sys.stdin.read(1).lower()
                            if c == 'q': self.running = False
                            elif c == 'p': self.stop_proxy(); time.sleep(0.5); self.start_proxy()
                            elif c == 'w': self.launch_windsurf()
                            elif c == 'c': self.launch_claude()
                            elif c == 'n': 
                                self.status_msg = "Joining MSNET Swarm..."
                                try:
                                    from src.pegasus.network.mshw_joiner import join_mshw_network
                                    if join_mshw_network():
                                        self.status_msg = "[bold blue]Joined MSNET Swarm.[/bold blue]"
                                    else:
                                        self.status_msg = "[red]MSNET Join Failed.[/red]"
                                except Exception as e:
                                    self.status_msg = f"[red]MSNET Error: {str(e)}[/red]"
                            elif c == 'i':
                                self.handle_input('i')
                            elif c == 'e': self.handle_input('e')
                            elif c == 't': self.handle_input('t')
                            elif c == 's': self.handle_input('s')
        finally:
            if is_tty: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    HighGravityDashboard().run()
