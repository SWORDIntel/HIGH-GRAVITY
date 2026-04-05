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
        self.total_bytes_transmitted = 0
        
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
                    
                    byte_match = re.search(r'BYTES=(\d+)', line)
                    if byte_match:
                        self.total_bytes_transmitted += int(byte_match.group(1))
                
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
        
        # Calculate Overage (Optimization Gain over normal LAN)
        # Normal tokens = total_bytes / 4 (est) + tokens_saved
        est_total_tokens = (self.total_bytes_transmitted // 4) + self.tokens_saved
        overage_pct = (self.tokens_saved / (est_total_tokens + 1)) * 100
        metrics.add_row(Text("Uplink Overage:", style="bold"), f"[bold white]{overage_pct:.2f}%[/bold white] (vs Normal LAN)")
        
        metrics.add_row(Text("Blocked Retries:", style="bold"), f"[bold bright_red]{self.retry_count}[/bold bright_red]")
        metrics.add_row(Text("Active / Dead Nodes:", style="bold"), f"[bold white]{self.active_keys_count}[/bold white] / [bold red]{self.exhausted_keys_count}[/bold red]")
        metrics.add_row(Text("Injection Mode:", style="bold"), f"[bold dark_red]{self.rotation_mode.upper()}[/bold dark_red]")
        
        # New Phantom Features Status
        metrics.add_row(Text("Shadow Spoofing:", style="bold"), "[bold red]ENABLED[/bold red]")
        metrics.add_row(Text("RAM Cache:", style="bold"), "[bold green]VOLATILE (SHM)[/bold green]")
        
        # Check if QIHSE is active (proxy-side info, here mocked based on availability)
        try:
            from tools.integration.qihse_wrapper import QIHSE
            q = QIHSE()
            if q.is_available():
                search_status = "[bold blue]QIHSE (QUANTUM-INSPIRED)[/bold blue]"
            else:
                search_status = "[bold yellow]CLASSICAL (LINEAR)[/bold yellow]"
        except:
            search_status = "[bold dim]DISABLED[/bold dim]"
            
        metrics.add_row(Text("Search Engine:", style="bold"), search_status)
        
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

        # Swarm Monitor Section
        swarm_logs = Table(title="Pegasus Swarm - Granular Telemetry", expand=True)
        swarm_logs.add_column("Agent ID", style="cyan")
        swarm_logs.add_column("Task", style="white")
        swarm_logs.add_column("Progress", style="green")
        swarm_logs.add_column("CPU %", style="yellow")
        swarm_logs.add_column("Memory", style="magenta")
        swarm_logs.add_column("Status", style="bold green")
        
        # Dynamically fetch granular data
        found_agent = False
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
                if proc.info['cmdline'] and 'dist/cli.mjs' in ' '.join(proc.info['cmdline']):
                    cmd = ' '.join(proc.info['cmdline'])
                    
                    task = "GENERAL_OPS"
                    if "RESEARCHER" in cmd: task = "INDEXING_REPO"
                    elif "SECURITYAUDITOR" in cmd: task = "AUDITING_SRC"
                    elif "ARCHITECT" in cmd: task = "MAPPING_FLOW"
                    elif "COMPRESSOR" in cmd: task = "OPTIMIZING_CONTEXT"
                    elif "SHUFFLER" in cmd: task = "ENTROPY_INJECTION"
                    elif "MONITOR" in cmd: task = "TELEMETRY_GATING"
                    
                    cpu = proc.cpu_percent(interval=0.01)
                    mem = proc.memory_info().rss / (1024 * 1024)
                    
                    # Detect Idle Status
                    status = "ACTIVE"
                    progress = f"{int(cpu * 5)}%" # Simulated progress
                    if cpu < 0.5:
                        status = "REASSIGNING"
                        progress = "0%"
                        task = f"IDLE -> DISCOVERING_VULNS"
                    
                    # Map task to human-readable names
                    agent_name = "OPERATIVE"
                    if "INDEXING_REPO" in task: agent_name = "RESEARCHER"
                    elif "AUDITING_SRC" in task: agent_name = "AUDITOR"
                    elif "MAPPING_FLOW" in task: agent_name = "ARCHITECT"
                    elif "OPTIMIZING_CONTEXT" in task: agent_name = "COMPRESSOR"
                    elif "ENTROPY_INJECTION" in task: agent_name = "SHUFFLER"
                    elif "TELEMETRY_GATING" in task: agent_name = "MONITOR"
                    
                    swarm_logs.add_row(
                        f"{agent_name}-{proc.pid}", 
                        task,
                        progress,
                        f"{cpu}%", 
                        f"{mem:.1f}MB", 
                        status
                    )
                    found_agent = True
        except Exception as e:
            swarm_logs.add_row("Monitor Error", "N/A", "N/A", "N/A", "N/A", str(e))
            
        if not found_agent:
            swarm_logs.add_row("No agents active", "IDLE", "0%", "0%", "0MB", "IDLE")

