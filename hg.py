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
from typing import Optional, Dict, List

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
VERSION = "2.1.0-HG"
PROXY_PORT = 9999
REPO_ROOT = Path(__file__).resolve().parent
PROXY_SCRIPT = REPO_ROOT / "tools" / "integration" / "highgravity_proxy.py"
LAUNCHER_SCRIPT = REPO_ROOT / "tools" / "integration" / "gemini_session_launcher.py"
KEYS_FILE = REPO_ROOT / "config" / "gemini_keys.json"
LOG_FILE = REPO_ROOT / "logs" / "proxy.log"
PROFILE_DIR = REPO_ROOT / "windsurf_profiles" / "high-gravity"
LAUNCH_SCRIPT = PROFILE_DIR / "launch_windsurf.sh"

console = Console()

class HighGravityDashboard:
    def __init__(self):
        self.proxy_proc = None
        self.running = True
        self.last_logs = []
        self.status_msg = "Dashboard initialized."
        self.proxy_status = "Stopped"
        self.proxy_port = PROXY_PORT
        self.session_keys = set()
        self.request_count = 0
        self.last_request_time = None

    def check_proxy_alive(self) -> bool:
        """Check if port 9999 is being listened on."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', self.proxy_port)) == 0

    def start_proxy(self):
        """Starts the highgravity_proxy.py in a background process."""
        if self.check_proxy_alive():
            self.status_msg = f"Proxy already running on port {self.proxy_port}."
            return

        self.status_msg = "Starting proxy server..."
        self.proxy_proc = subprocess.Popen(
            [sys.executable, str(PROXY_SCRIPT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid # Run in its own process group
        )
        time.sleep(2) # Give it a moment to start
        if self.check_proxy_alive():
            self.proxy_status = "Running"
            self.status_msg = "Proxy server started successfully."
        else:
            self.proxy_status = "Error"
            self.status_msg = "Failed to start proxy. Check logs/proxy.log."

    def stop_proxy(self):
        """Stops the proxy process if we started it."""
        if self.proxy_proc:
            os.killpg(os.getpgid(self.proxy_proc.pid), signal.SIGTERM)
            self.proxy_proc = None
            self.proxy_status = "Stopped"
            self.status_msg = "Proxy server stopped."

    def update_stats(self):
        """Parses log file for recent activity stats."""
        if not LOG_FILE.exists():
            return

        try:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
                self.last_logs = []
                
                # Filter for interesting logs
                for l in reversed(lines):
                    if len(self.last_logs) >= 12:
                        break
                    line = l.strip()
                    if any(x in line for x in ["Incoming", "Forwarding", "NEW_SESSION_KEY_DISCOVERED", "Upstream Error"]):
                        self.last_logs.append(line)
                
                self.last_logs.reverse()

                # Count total requests and discovered keys
                self.request_count = sum(1 for l in lines if "Incoming" in l)
                
                for line in lines:
                    if "NEW_SESSION_KEY_DISCOVERED" in line:
                        try:
                            key_part = line.split("DISCOVERED: ")[1].strip()
                            self.session_keys.add(key_part)
                        except:
                            pass
                
                # Find last request details
                for line in reversed(lines):
                    if "Incoming" in line:
                        parts = line.split("] ")
                        if len(parts) > 1:
                            self.last_request_time = parts[0].lstrip("[")
                            break
        except:
            pass

    def launch_windsurf(self):
        """Executes the Windsurf launch script."""
        if not LAUNCH_SCRIPT.exists():
            self.status_msg = "[red]Error: launch_windsurf.sh not found. Run wire-in first.[/red]"
            return

        # Determine which binary to use
        cmd = "windsurf-next" if shutil.which("windsurf-next") else "windsurf"
        self.status_msg = f"Launching {cmd} via profile..."
        
        env = os.environ.copy()
        env["WINDSURF_BIN"] = cmd
        
        subprocess.Popen(
            [str(LAUNCH_SCRIPT)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.status_msg = f"{cmd} launch requested."

    def create_layout(self) -> Layout:
        """Creates the rich layout for the dashboard."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="sidebar", ratio=1),
            Layout(name="body", ratio=3)
        )
        layout["body"].split_column(
            Layout(name="status", size=10),
            Layout(name="logs")
        )
        return layout

    def generate_dashboard(self) -> Layout:
        """Populates the layout with updated data."""
        self.update_stats()
        is_alive = self.check_proxy_alive()
        self.proxy_status = "Running" if is_alive else "Stopped"

        layout = self.create_layout()

        # Header
        header_text = Text.assemble(
            (" HIGH-GRAVITY ", "bold white on blue"),
            " Optimization & Identity Proxy Dashboard",
            justify="center"
        )
        layout["header"].update(Panel(header_text, border_style="blue"))

        # Sidebar - Actions/Info
        sidebar_table = Table(show_header=False, box=None)
        sidebar_table.add_row("[cyan]W[/cyan] - Launch Windsurf")
        sidebar_table.add_row("[cyan]P[/cyan] - Start/Stop Proxy")
        sidebar_table.add_row("[cyan]Q[/cyan] - Quit Dashboard")
        
        info_table = Table(show_header=False, box=None, padding=(0, 1))
        info_table.add_row("Version:", VERSION)
        key_status = f"[green]{len(self.session_keys)}[/green]" if self.session_keys else "[yellow]Waiting for Windsurf...[/yellow]"
        info_table.add_row("Session Keys:", key_status)
        info_table.add_row("Port:", str(self.proxy_port))
        
        sidebar_content = Table.grid(expand=True)
        sidebar_content.add_row(sidebar_table)
        sidebar_content.add_row(Panel(info_table, title="[bold]Info[/bold]", border_style="dim"))

        layout["sidebar"].update(Panel(
            sidebar_content,
            title="[bold]Actions[/bold]",
            border_style="cyan"
        ))

        # Status Panel
        status_grid = Table.grid(expand=True)
        status_grid.add_column(ratio=1)
        status_grid.add_column(ratio=2)
        
        proxy_color = "green" if is_alive else "red"
        status_grid.add_row(
            "Proxy Status:", 
            Text(self.proxy_status, style=f"bold {proxy_color}")
        )
        status_grid.add_row("Total Requests:", f"[bold white]{self.request_count}[/bold white]")
        status_grid.add_row("Last Request:", f"[dim]{self.last_request_time or 'N/A'}[/dim]")
        status_grid.add_row("Latest Message:", f"[italic yellow]{self.status_msg}[/italic yellow]")

        layout["status"].update(Panel(
            status_grid,
            title="[bold]System Status[/bold]",
            border_style="white"
        ))

        # Logs Panel
        log_text = Text("\n".join(self.last_logs) if self.last_logs else "No recent logs found.")
        layout["logs"].update(Panel(
            log_text,
            title="[bold]Real-time Proxy Logs (Last 10)[/bold]",
            border_style="dim",
            padding=(0, 1)
        ))

        # Footer
        footer_text = Text(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | Press Q to quit.", justify="center", style="dim")
        layout["footer"].update(Panel(footer_text, border_style="blue"))

        return layout

    def run(self):
        """Main loop for the dashboard with optimized non-blocking input."""
        import select
        import tty
        import termios

        fd = sys.stdin.fileno()
        is_tty = os.isatty(fd)
        
        if is_tty:
            old_settings = termios.tcgetattr(fd)
        
        # Auto-start proxy if not running
        if not self.check_proxy_alive():
            self.start_proxy()

        console.clear()
        try:
            if is_tty:
                tty.setcbreak(fd) # Less invasive than setraw

            with Live(self.generate_dashboard(), refresh_per_second=4, screen=True) as live:
                while self.running:
                    # Only update the layout if needed or at regular intervals
                    live.update(self.generate_dashboard())
                    
                    if is_tty:
                        [r, w, e] = select.select([sys.stdin], [], [], 0.05)
                        if r:
                            char = sys.stdin.read(1).lower()
                            if char == 'q':
                                self.running = False
                            elif char == 'w':
                                self.launch_windsurf()
                            elif char == 'p':
                                if self.check_proxy_alive():
                                    self.stop_proxy()
                                else:
                                    self.start_proxy()
                    else:
                        time.sleep(0.1)
        except Exception as e:
            self.status_msg = f"Dashboard Error: {e}"
        finally:
            if is_tty:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            self.stop_proxy()

def main():
    dashboard = HighGravityDashboard()
    
    # Handle signals for clean exit
    def signal_handler(sig, frame):
        dashboard.running = False
        dashboard.stop_proxy()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    dashboard.run()

if __name__ == "__main__":
    main()
