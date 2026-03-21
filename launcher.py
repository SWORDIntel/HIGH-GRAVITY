#!/usr/bin/env python3
"""
Gemini and Windsurf Launch Helper
=================================

Launches Gemini surfaces or prepares Windsurf profiles from a selected API key.
Key health checks remain API-based; they do not verify GUI state or editor state.

This script is now also responsible for launching and managing a TUI dashboard
for monitoring Windsurf and proxy performance.
"""

import os
import sys
import json
import time
import shlex
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone
import requests
import webbrowser
from typing import Optional, Dict, Any
import threading
import socket # Added for port checking

# Attempt to import rich; fallback if not available
try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("[!] Rich library not available. Install with: pip install rich")
    print("[*] Falling back to basic mode for dashboard...")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR

# --- Constants ---
DEFAULT_PROXY_HOST = "127.0.0.1" # Default host for proxy
DEFAULT_PROXY_PORT = 9999      # Default port for proxy
DEFAULT_PROXY_URL = f"http://{DEFAULT_PROXY_HOST}:{DEFAULT_PROXY_PORT}" # Derived default URL
DEFAULT_PROXY_TARGET_URL = "https://inference.codeium.com" # Default Codeium backend
DEFAULT_PROXY_CACHE_TTL = 3600 # 1 hour default cache TTL

DEFAULT_MONITOR_DURATION = 300 # seconds
DEFAULT_MONITOR_INTERVAL = 30  # seconds

# --- Helper Functions ---
def is_port_in_use(host: str, port: int) -> bool:
    """Check if a port is already in use by attempting to connect to it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(0.1) # Short timeout
            s.connect((host, port))
            return True
        except (socket.error, socket.timeout):
            return False

# --- Agent Classes ---

class DashboardAgent:
    """Base class for dashboard agents."""
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self._stop_event = threading.Event()

    def fetch_data(self):
        """Abstract method to fetch data. Should update self.data."""
        raise NotImplementedError

    def render_display(self) -> Panel:
        """Abstract method to render data into a rich Panel."""
        raise NotImplementedError

    def run_fetch_loop(self, interval: float = 1.0):
        """Runs fetch_data periodically until stop_event is set."""
        while not self._stop_event.is_set():
            try:
                self.fetch_data()
            except Exception as e:
                self.data = {"error": f"Error fetching: {e}"}
                print(f"Error in {self.__class__.__name__}: {e}") # Log to console as TUI might not catch it
            
            if self._stop_event.wait(timeout=interval):
                break

    def stop(self):
        self._stop_event.set()

class UsageCostAgent(DashboardAgent):
    """Agent for tracking usage (data volume) and displaying costs."""
    def __init__(self, cost_data: Dict[str, float]):
        super().__init__()
        self.cost_data = cost_data
        # Initialize data with defaults
        self.data = {
            "usage_data_mb": 0.0,
            "api_token_cost_estimate": 0.0,
            "combined_service_cost_estimate": 0.0,
            "status": "Initializing...",
        }

    def fetch_data(self):
        """
        Usage data is updated by the proxy agent's measurements.
        Cost is estimated based on monthly figures and current usage.
        """
        # Usage data (data_mb) is expected to be updated externally by the proxy agent
        # or a shared state. For now, assume it's available in self.data['usage_data_mb']
        # set by another part of the application.
        
        # Estimate costs based on fetched data volume and monthly rates.
        # This is a very rough approximation as the doc doesn't give per-GB cost.
        # We'll use the monthly figures as a baseline.
        
        data_mb = self.data.get("usage_data_mb", 0.0)
        
        # Approximate cost for data transfer based on monthly API token cost.
        # This assumes API token cost is proportional to data volume, which is a simplification.
        # If $0.75 covers X GB/month, then cost per MB is $0.75 / (X*1024).
        # Without X, we can only show monthly baseline costs.
        
        api_token_monthly = self.cost_data.get("api_token_monthly", 0.75)
        combined_monthly = self.cost_data.get("combined_monthly", 7.20)
        
        self.data["status"] = "Monitoring..."
        self.data["api_token_cost_estimate"] = api_token_monthly # Display baseline
        self.data["combined_service_cost_estimate"] = combined_monthly # Display baseline
        
        # If we had a way to link data volume to cost, we'd calculate it here.
        # For now, we display the baseline monthly costs.

    def render_display(self) -> Panel:
        table = Table(title="Usage & Costs", show_header=False, expand=True)
        table.add_column(style="dim", width=15) # Metric column
        table.add_column(style="green")         # Value column

        table.add_row("Data Volume:", f"{self.data.get('usage_data_mb', 0):.2f} MB")
        table.add_row("API Token Cost:", f"${self.data.get('api_token_cost_estimate', 0.0):.2f}/month (Baseline)")
        table.add_row("Combined Service Cost:", f"${self.data.get('combined_service_cost_estimate', 0.0):.2f}/month (Baseline)")
        table.add_row("Status:", self.data.get("status", "N/A"))
        
        return Panel(table, title="Usage & Costs", expand=True)

class ProxyAgent(DashboardAgent):
    """Agent for checking proxy status and measuring throughput."""
    def __init__(self, proxy_url: str, test_data_size_mb: int = 1, num_requests: int = 10):
        super().__init__()
        self.proxy_url = proxy_url
        self.test_data_size_mb = test_data_size_mb
        self.num_requests = num_requests
        self.data = {
            "status": "Initializing...",
            "throughput_rps": 0.0,
            "throughput_mbps": 0.0,
            "total_data_mb": 0.0,
        }
        self.shared_usage_data = {} # To share data with UsageCostAgent

    def _simulate_request(self) -> Dict[str, Any]:
        """Simulates a single request to the proxy."""
        start_time = time.time()
        test_data = b'A' * (self.test_data_size_mb * 1024 * 1024) # Generate test data
        headers = {'Content-Type': 'application/octet-stream'}
        
        try:
            # Use a POST request to send data and measure response
            response = requests.post(self.proxy_url, data=test_data, headers=headers, timeout=10)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Data sent + received (approximate received as response body size)
            data_sent_mb = len(test_data) / (1024 * 1024)
            data_received_mb = len(response.content) / (1024 * 1024)
            total_data_mb = data_sent_mb + data_received_mb
            
            return {
                "success": True,
                "duration": duration,
                "data_mb": total_data_mb,
                "status_code": response.status_code,
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
                "data_mb": 0.0,
            }

    def fetch_data(self):
        """Measures proxy status and throughput via simulated requests."""
        # Check connectivity
        try:
            response = requests.get(self.proxy_url, timeout=5)
            if response.status_code == 200:
                self.data["status"] = f"Connected ({response.status_code})"
            else:
                self.data["status"] = f"Connected (HTTP {response.status_code})"
        except requests.exceptions.RequestException as e:
            self.data["status"] = f"Error: {e}"
            self.data["throughput_rps"] = 0.0
            self.data["throughput_mbps"] = 0.0
            self.data["total_data_mb"] = 0.0
            # Update shared data for UsageCostAgent
            self.shared_usage_data["usage_data_mb"] = 0.0
            return

        # Measure throughput
        total_data_mb_transferred = 0.0
        total_duration = 0.0
        successful_requests = 0
        
        # Use progress bar for simulation if rich is available
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                transient=True,
            ) as progress:
                progress.add_task("Simulating requests...", total=self.num_requests)
                for _ in range(self.num_requests):
                    result = self._simulate_request()
                    if result["success"]:
                        successful_requests += 1
                        total_data_mb_transferred += result["data_mb"]
                        total_duration += result["duration"]
                    # Update progress for each simulated request
                    progress.update(progress.tasks[0].id, advance=1)
                    if self._stop_event.is_set(): break # Allow interruption

        else: # Fallback if rich is not available
            for _ in range(self.num_requests):
                result = self._simulate_request()
                if result["success"]:
                    successful_requests += 1
                    total_data_mb_transferred += result["data_mb"]
                    total_duration += result["duration"]
                if self._stop_event.is_set(): break
        
        if total_duration > 0 and successful_requests > 0:
            avg_duration_per_req = total_duration / successful_requests
            rps = successful_requests / total_duration if total_duration > 0 else 0
            mbps = total_data_mb_transferred / total_duration if total_duration > 0 else 0
            
            self.data["throughput_rps"] = rps
            self.data["throughput_mbps"] = mbps
            self.data["total_data_mb"] = total_data_mb_transferred
            self.data["status"] += f" | {successful_requests}/{self.num_requests} requests OK"
        else:
            self.data["throughput_rps"] = 0.0
            self.data["throughput_mbps"] = 0.0
            self.data["total_data_mb"] = 0.0
            if successful_requests == 0 and self.num_requests > 0:
                 self.data["status"] += " | No requests successful"


        # Update shared usage data for Agent 1
        self.shared_usage_data["usage_data_mb"] = self.data["total_data_mb"]
        self.shared_usage_data["last_measurement_time"] = time.time()


    def render_display(self) -> Panel:
        table = Table(title="Proxy Status", show_header=False, expand=True)
        table.add_column(style="dim", width=15) # Metric column
        table.add_column(style="green")         # Value column

        table.add_row("URL:", self.proxy_url)
        table.add_row("Status:", self.data.get("status", "N/A"))
        table.add_row("Throughput (RPS):", f"{self.data.get('throughput_rps', 0.0):.2f}")
        table.add_row("Throughput (MB/s):", f"{self.data.get('throughput_mbps', 0.0):.2f}")
        table.add_row("Total Data (MB):", f"{self.data.get('total_data_mb', 0.0):.2f}")
        
        return Panel(table, title="Proxy Monitor", expand=True)


class ThroughputComparisonAgent(DashboardAgent):
    """Agent for comparing throughput against costs."""
    def __init__(self, cost_data: Dict[str, float]):
        super().__init__()
        self.cost_data = cost_data
        self.data = {"comparison": "N/A", "status": "Waiting for data..."}

    def fetch_data(self):
        """Compares measured throughput with cost data."""
        # Rely on other agents to update their data
        usage_data_mb = self.shared_usage_data.get("usage_data_mb", 0.0)
        throughput_mbps = self.shared_proxy_data.get("throughput_mbps", 0.0)
        
        api_token_monthly_cost = self.cost_data.get("api_token_monthly", 0.75)
        combined_monthly_cost = self.cost_data.get("combined_monthly", 7.20)

        if not usage_data_mb or not combined_monthly_cost:
            self.data["status"] = "Waiting for data..."
            return

        self.data["status"] = "Calculating..."

        # Approximate cost based on measured throughput and monthly cost.
        # This is a rough estimate as monthly cost depends on *total* usage, not just peak throughput.
        # For simplicity, we can state the baseline monthly cost.
        
        # If we want to estimate cost for the *measured throughput*, we'd need to know
        # how many hours the proxy runs per month and how many requests/MBs that translates to.
        # Example: If $7.20/month is for 1000GB/month, then cost/MB is $7.20 / 1000000
        # Without a cost per GB, we'll present the baseline monthly costs for context.
        
        self.data["comparison"] = f"Baseline: ${combined_monthly_cost:.2f}/month (Total Service)"
        if api_token_monthly_cost > 0:
             self.data["comparison"] += f" | ${api_token_monthly_cost:.2f}/month (API Tokens)"

        # Could add a simple RPS vs API token cost comparison if we assume an average data size per request.
        # For example, if avg request is 10KB, and API cost is $0.75/month for X requests/month,
        # we can estimate cost per request. This requires assumptions.
        
        # For now, let's just display the baseline costs alongside the measured throughput.

    def render_display(self) -> Panel:
        table = Table(title="Throughput Comparison", show_header=False, expand=True)
        table.add_column(style="dim", width=25) # Metric column
        table.add_column(style="cyan")         # Value column

        table.add_row("Throughput (MB/s):", f"{self.data.get('throughput_mbps', 0.0):.2f}")
        table.add_row("Status:", self.data.get("status", "N/A"))
        table.add_row("Estimated Cost:", self.data.get("comparison", "N/A"))
        
        return Panel(table, title="Throughput Cost Analysis", expand=True)

# --- Main Application Class ---

class WindsurfDashboardApp:
    def __init__(self, proxy_url: str, cost_data: Dict[str, float]):
        self.console = Console()
        self.proxy_url = proxy_url
        self.cost_data = cost_data
        
        # Initialize agents
        self.usage_cost_agent = UsageCostAgent(cost_data=self.cost_data)
        self.proxy_agent = ProxyAgent(proxy_url=self.proxy_url, num_requests=20) # 20 simulated requests for test
        self.comparison_agent = ThroughputComparisonAgent(cost_data=self.cost_data)
        
        # Share data between agents where needed
        self.proxy_agent.shared_usage_data = self.usage_cost_agent.data
        self.comparison_agent.shared_usage_data = self.usage_cost_agent.data
        self.comparison_agent.shared_proxy_data = self.proxy_agent.data
        
        self.agents = [self.usage_cost_agent, self.proxy_agent, self.comparison_agent]
        
        self.layout = Layout()
        self.layout.split_column(
            Layout(name="usage_cost_panel", size=5),
            Layout(name="proxy_panel", size=5),
            Layout(name="comparison_panel", size=5),
        )
        
        self.live_display = None

    def start_agents(self):
        """Starts the data fetching threads for each agent."""
        self.stop_agents() # Ensure any previous threads are stopped
        for agent in self.agents:
            # Run fetch_data periodically in a thread
            thread = threading.Thread(target=agent.run_fetch_loop, args=(5.0,), daemon=True) # Update every 5 seconds
            thread.start()
            
    def stop_agents(self):
        """Signals all agent threads to stop."""
        for agent in self.agents:
            agent.stop()

    def run(self):
        """Runs the TUI dashboard."""
        self.start_agents()
        self.live_display = Live(self.layout, refresh_per_second=4, console=self.console)
        
        try:
            with self.live_display as live:
                while True:
                    # Update the layout with current agent data
                    self.layout["usage_cost_panel"].update(self.usage_cost_agent.render_display())
                    self.layout["proxy_panel"].update(self.proxy_agent.render_display())
                    self.layout["comparison_panel"].update(self.comparison_agent.render_display())
                    live.update(self.layout)
                    time.sleep(1) # Small sleep to prevent busy-waiting
        except KeyboardInterrupt:
            self.console.print("[yellow]Dashboard stopped by user.[/yellow]")
        except Exception as e:
            self.console.print(f"[bold red]Dashboard Error: {e}[/bold red]")
        finally:
            self.stop_agents()
            if self.live_display:
                self.live_display.stop()
            self.console.print("[dim]Dashboard closed.[/dim]")


# --- Main Logic ---

def parse_cost_data_from_file(file_content: str) -> Dict[str, float]:
    """Parses cost data from the COMPLETE_ANALYSIS.md content."""
    cost_data = {
        "api_token_monthly": 0.75, # Default from doc
        "combined_monthly": 7.20,  # Default from doc
        "infrastructure_per_user_monthly": 0.305 # Approx. $305.60/1000 users
    }

    # Simple parsing for specific lines, can be made more robust
    lines = file_content.splitlines()
    for i, line in enumerate(lines):
        if "API Tokens" in line and "$" in line:
            try:
                parts = line.split('$')
                if len(parts) > 1:
                    cost_str = parts[1].split('/')[0].strip()
                    cost_data["api_token_monthly"] = float(cost_str)
            except Exception:
                pass # Keep default if parsing fails

        if "Combined:" in line and "$" in line:
            try:
                parts = line.split('$')
                if len(parts) > 1:
                    cost_str = parts[1].split('/')[0].strip()
                    cost_data["combined_monthly"] = float(cost_str)
            except Exception:
                pass # Keep default if parsing fails
                
        # Infrastructure cost is harder to tie to a single user without knowing their specific usage
        # We'll keep the monthly baseline costs for simplicity as requested by the user.
        
    print(f"Parsed Cost Data: {cost_data}")
    return cost_data

def main():
    parser = argparse.ArgumentParser(description="Gemini and Windsurf launch helper / Dashboard")
    parser.add_argument("--list", "-l", action="store_true", help="List available keys")
    parser.add_argument("--api-key", help="Direct API key input for non-interactive/editor integrations")
    parser.add_argument("--key-index", "-k", type=int, help="Key index to use (1-based)")
    parser.add_argument("--check", "-c", action="store_true", default=None, help="Check key validity only")
    parser.add_argument("--monitor", "-m", type=int, help="Monitor duration in seconds")
    parser.add_argument("--mode", choices=["studio", "chat", "windsurf"], help="Launch mode")
    parser.add_argument("--keys-file", help="Path to a keys file, usually config/gemini_keys.json")
    parser.add_argument("--provider", choices=["proxy", "direct"], help="Windsurf provider mode")
    parser.add_argument("--proxy-url", help="HIGHGRAVITY/OpenAI-compatible proxy URL for Windsurf mode")
    parser.add_argument("--model", help="Model label to record in Windsurf profile")
    parser.add_argument("--window-name", help="Logical Windsurf window/profile name")
    parser.add_argument("--windsurf-binary", help="Windsurf executable name or path")
    parser.add_argument("--no-new-window", action="store_true", default=None, help="Don't pass --new-window when launching Windsurf")
    parser.add_argument("--dry-run", action="store_true", default=None, help="Prepare artifacts but do not launch Windsurf")
    parser.add_argument("--stdin-format", choices=["auto", "json", "env"], default="auto", help="How to parse piped stdin variables")

    # Arguments for dashboard and proxy modes
    parser.add_argument("--dashboard", action="store_true", help="Launch the TUI dashboard")
    parser.add_argument("--start-proxy", action="store_true", help="Start the HIGHGRAVITY proxy in the background")
    parser.add_argument("--proxy-target-url", default=DEFAULT_PROXY_TARGET_URL, help="The URL of the upstream AI API for the proxy to forward to")
    parser.add_argument("--proxy-listen-port", type=int, default=DEFAULT_PROXY_PORT, help="The port for the HIGHGRAVITY proxy to listen on")
    parser.add_argument("--proxy-cache-ttl", type=int, default=DEFAULT_PROXY_CACHE_TTL, help="Cache TTL for the proxy in seconds")

    args = parser.parse_args()
    
    # --- Load and Resolve Options ---
    launcher = GeminiSessionLauncher(keys_file=args.keys_file) # Keep Gemini context for key management
    stdin_overrides = launcher.load_stdin_overrides(stdin_format=args.stdin_format)
    env_overrides = launcher.load_environment_overrides()
    runtime = launcher.resolve_runtime_options(args, stdin_overrides, env_overrides)

    # Resolve proxy specific options, giving CLI args highest precedence
    proxy_listen_host = DEFAULT_PROXY_HOST
    proxy_listen_port = args.proxy_listen_port if args.proxy_listen_port != DEFAULT_PROXY_PORT else int(runtime.get("proxy_url", DEFAULT_PROXY_URL).split(':')[-1]) if ':' in runtime.get("proxy_url", "") else DEFAULT_PROXY_PORT
    proxy_target_url = args.proxy_target_url
    proxy_cache_ttl = args.proxy_cache_ttl
    
    # Ensure runtime's proxy_url reflects the chosen listen port
    resolved_proxy_url = f"http://{proxy_listen_host}:{proxy_listen_port}"
    runtime["proxy_url"] = resolved_proxy_url # Update runtime with actual proxy URL

    # --- Proxy Launch Sequence ---
    should_launch_proxy = args.start_proxy or args.dashboard or runtime["mode"] == "windsurf"
    if should_launch_proxy:
        if not is_port_in_use(proxy_listen_host, proxy_listen_port):
            print(f"[*] Launching HIGHGRAVITY proxy on {proxy_listen_host}:{proxy_listen_port}...")
            proxy_cmd = [sys.executable, str(SCRIPT_DIR / "scripts" / "proxy.py")]
            
            proxy_env = os.environ.copy()
            proxy_env["PROXY_LISTEN_HOST"] = proxy_listen_host
            proxy_env["PROXY_LISTEN_PORT"] = str(proxy_listen_port)
            proxy_env["PROXY_TARGET_URL"] = proxy_target_url
            proxy_env["PROXY_CACHE_TTL"] = str(proxy_cache_ttl)

            # Start proxy in a new process group so it doesn't die with launcher.py
            subprocess.Popen(proxy_cmd, env=proxy_env, preexec_fn=os.setsid)
            print(f"[+] Proxy started in background. Waiting 3 seconds for startup...")
            time.sleep(3) # Give proxy time to start
        else:
            print(f"[*] HIGHGRAVITY proxy already running on {proxy_listen_host}:{proxy_listen_port}.")

    # --- Handle Dashboard Launch ---
    if args.dashboard:
        if not RICH_AVAILABLE:
            print("[!] Rich library is required for the dashboard. Please install it: pip install rich")
            sys.exit(1)
            
        print("[*] Initializing Windsurf Dashboard...")
        
        # Read cost data from file
        try:
            # Assuming the file path is relative to the script directory
            cost_file_path = REPO_ROOT / "docs" / "analysis" / "COMPLETE_ANALYSIS.md"
            if not cost_file_path.exists():
                print(f"[!] Cost analysis file not found at: {cost_file_path}")
                # Use default costs if file is missing
                parsed_costs = parse_cost_data_from_file("") # Pass empty to use defaults
            else:
                cost_file_content = cost_file_path.read_text()
                parsed_costs = parse_cost_data_from_file(cost_file_content)
        except Exception as e:
            print(f"[!] Error reading or parsing cost analysis file: {e}")
            parsed_costs = parse_cost_data_from_file("") # Use defaults on error

        dashboard_app = WindsurfDashboardApp(proxy_url=resolved_proxy_url, cost_data=parsed_costs)
        dashboard_app.run()
        return # Exit after dashboard runs

    # --- Handle Non-Dashboard Launch Modes ---
    if not launcher.keys and not runtime["api_key"] and not runtime["key_index"] and not sys.stdin.isatty():
        print("[!] No keys available. Create config/gemini_keys.json or pass --api-key.")
        raise SystemExit(1)
    
    if args.list:
        launcher.list_keys()
        return
    
    if runtime["api_key"] or runtime["key_index"]:
        if runtime["api_key"]:
            selected_key = runtime["api_key"]
        elif 1 <= runtime["key_index"] <= len(launcher.keys):
            selected_key = launcher.keys[runtime["key_index"] - 1]["key"]
        else:
            print(f"[!] Invalid key index. Use 1-{len(launcher.keys)}")
            return

        if runtime["check"]:
            launcher.check_key_validity(selected_key)
            return

        if runtime["mode"] == "studio":
            launcher.launch_gemini_web(selected_key)
        elif runtime["mode"] == "chat":
            launcher.launch_gemini_chat(selected_key)
        else: # windsurf mode or default
            # Ensure provider is 'proxy' if proxy_url is set, otherwise use default from runtime
            provider = runtime["provider"]
            # Force provider to 'proxy' if it's explicitly set to use a proxy or proxy is started
            if (runtime["proxy_url"] and runtime["proxy_url"] != DEFAULT_PROXY_URL) or should_launch_proxy:
                print(f"[*] Proxy URL provided/launched ({runtime['proxy_url']}), setting provider to 'proxy'.")
                provider = "proxy"
                
            launcher.launch_windsurf(
                selected_key,
                window_name=runtime["window_name"],
                provider=provider,
                proxy_url=resolved_proxy_url, # Pass the actual resolved proxy URL
                binary=runtime["windsurf_binary"],
                new_window=runtime["new_window"],
                dry_run=runtime["dry_run"],
            )

        # Wait for initialization
        if runtime["mode"] in {"studio", "chat"}:
            time.sleep(10)

        # Monitor if requested
        if runtime["monitor"]:
            launcher.monitor_session(selected_key, duration=runtime["monitor"])
    else:
        # Interactive mode
        launcher.interactive_launch()


if __name__ == "__main__":
    main()
