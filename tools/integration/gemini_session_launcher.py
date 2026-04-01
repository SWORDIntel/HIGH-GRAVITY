#!/usr/bin/env python3
"""
Gemini and Windsurf Launch Helper
=================================

Launches Gemini surfaces or prepares Windsurf profiles from a selected API key.
Key health checks remain API-based; they do not verify GUI state or editor state.
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
from typing import Optional, Dict

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("[!] Rich library not available. Install with: pip install rich")
    print("[*] Falling back to basic mode...")

class GeminiSessionLauncher:
    def __init__(self, keys_file: str = None):
        """Initialize with Gemini API keys"""
        if keys_file is None:
            keys_file = self._default_keys_file()
        
        self.keys_file = Path(keys_file)
        self.keys = self._load_keys()

    def _default_keys_file(self) -> Path:
        """Find the preferred local keys file"""
        candidates = [
            REPO_ROOT / "config" / "gemini_keys.json",
            REPO_ROOT / "gemini_keys.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]
        
    def _load_keys(self) -> list:
        """Load API keys from JSON file"""
        if not self.keys_file.exists():
            return []
        with open(self.keys_file) as f:
            data = json.load(f)
        return data["keys"]

    def ensure_keys_file(self) -> bool:
        """
        Ensure a usable keys file exists, prompting interactively when possible.
        """
        if self.keys:
            return True

        print(f"[!] No Gemini keys file found at: {self.keys_file}")
        print("[*] Expected location: config/gemini_keys.json")

        if not sys.stdin.isatty():
            print("[!] Non-interactive mode: provide --api-key, --key-index, or create config/gemini_keys.json")
            return False

        choice = input("Create a keys file now? (y/n): ").strip().lower()
        if choice != "y":
            return False

        raw_keys = input("Paste one or more Gemini API keys separated by commas: ").strip()
        keys = [key.strip() for key in raw_keys.split(",") if key.strip()]

        if not keys:
            print("[!] No keys provided.")
            return False

        self.keys_file.parent.mkdir(parents=True, exist_ok=True)
        self.keys_file.write_text(json.dumps({
            "keys": [{"key": key, "status": "active"} for key in keys]
        }, indent=2) + "\n")
        try:
            self.keys_file.chmod(0o600)
        except OSError:
            pass

        self.keys = self._load_keys()
        print(f"[+] Saved {len(self.keys)} key(s) to {self.keys_file}")
        return True

    def _mask_key(self, api_key: str) -> str:
        """Mask API key for safe display"""
        if len(api_key) <= 12:
            return "*" * len(api_key)
        return api_key[:12] + "..." + api_key[-6:]

    def _slugify(self, value: str) -> str:
        """Convert a profile label into a filesystem-safe identifier"""
        cleaned = "".join(
            c.lower() if c.isalnum() else "-" for c in value.strip()
        )
        cleaned = "-".join(filter(None, cleaned.split("-")))
        return cleaned or "default"

    def _coerce_bool(self, value):
        """Interpret common string/int forms as bools"""
        if isinstance(value, bool):
            return value
        if value is None:
            return None
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    def _parse_env_like_lines(self, text: str) -> Dict[str, str]:
        """Parse KEY=VALUE or export KEY=VALUE lines"""
        parsed = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip().strip("'\"")
        return parsed

    def _normalize_integration_overrides(self, raw: Dict) -> Dict:
        """
        Normalize flat JSON, nested editor payloads, and Windsurf hook payloads.
        """
        if not isinstance(raw, dict):
            return {}

        sources = [raw]
        for nested_key in ("tool_info", "options", "variables", "env"):
            nested = raw.get(nested_key)
            if isinstance(nested, dict):
                sources.append(nested)
                if nested_key == "tool_info":
                    for tool_info_nested_key in ("variables", "options", "env"):
                        tool_nested = nested.get(tool_info_nested_key)
                        if isinstance(tool_nested, dict):
                            sources.append(tool_nested)

        aliases = {
            "api_key": [
                "api_key", "apiKey", "key", "apikey",
                "gemini_api_key", "google_api_key", "openai_api_key",
                "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "HIGHGRAVITY_API_KEY", "WINDSURF_API_KEY"
            ],
            "key_index": ["key_index", "keyIndex", "HIGHGRAVITY_KEY_INDEX"],
            "mode": ["mode"],
            "provider": ["provider"],
            "proxy_url": [
                "proxy_url", "proxyUrl", "highgravity_proxy_url", "openai_base_url", "openai_api_base",
                "HIGHGRAVITY_PROXY_URL", "OPENAI_BASE_URL", "OPENAI_API_BASE"
            ],
            "model": ["model", "HIGHGRAVITY_MODEL"],
            "window_name": [
                "window_name", "windowName", "profile", "profile_name", "profileName",
                "HIGHGRAVITY_WINDOW_NAME", "HIGHGRAVITY_WINDOW_ID"
            ],
            "windsurf_binary": ["windsurf_binary", "windsurfBinary", "binary", "WINDSURF_BIN", "WINDSURF_BINARY"],
            "monitor": ["monitor", "monitor_seconds", "monitorSeconds", "HIGHGRAVITY_MONITOR"],
            "check": ["check", "HIGHGRAVITY_CHECK"],
            "dry_run": ["dry_run", "dryRun", "HIGHGRAVITY_DRY_RUN"],
            "new_window": ["new_window", "newWindow", "HIGHGRAVITY_NEW_WINDOW"],
        }

        normalized = {}
        for dest, keys in aliases.items():
            for source in sources:
                for key in keys:
                    if source.get(key) not in {None, ""}:
                        normalized[dest] = source[key]
                        break
                if dest in normalized:
                    break

        if "window_name" not in normalized:
            trajectory_id = raw.get("trajectory_id")
            execution_id = raw.get("execution_id")
            if trajectory_id and execution_id:
                normalized["window_name"] = f"{trajectory_id}-{execution_id}"
            elif trajectory_id:
                normalized["window_name"] = str(trajectory_id)

        return normalized

    def load_stdin_overrides(self, stdin_format: str = "auto") -> Dict:
        """
        Load piped variables from stdin for editor/Cascade integrations.
        """
        if sys.stdin.isatty():
            return {}

        payload = sys.stdin.read().strip()
        if not payload:
            return {}

        if stdin_format == "json" or (stdin_format == "auto" and payload[:1] in {"{", "["}):
            data = json.loads(payload)
            if isinstance(data, list):
                raise ValueError("stdin JSON payload must be an object, not a list")
            return self._normalize_integration_overrides(data)

        return self._normalize_integration_overrides(self._parse_env_like_lines(payload))

    def load_environment_overrides(self) -> Dict:
        """
        Load variables from env so Windsurf/Cascade can invoke the tool directly.
        """
        aliases = {
            "api_key": [
                "CASCADE_API_KEY", "HIGHGRAVITY_API_KEY", "GEMINI_API_KEY",
                "GOOGLE_API_KEY", "OPENAI_API_KEY", "WINDSURF_API_KEY"
            ],
            "key_index": [
                "CASCADE_KEY_INDEX", "HIGHGRAVITY_KEY_INDEX"
            ],
            "mode": [
                "CASCADE_MODE", "HIGHGRAVITY_MODE"
            ],
            "provider": [
                "CASCADE_PROVIDER", "HIGHGRAVITY_PROVIDER"
            ],
            "proxy_url": [
                "CASCADE_PROXY_URL", "HIGHGRAVITY_PROXY_URL", "OPENAI_BASE_URL", "OPENAI_API_BASE"
            ],
            "model": [
                "CASCADE_MODEL", "HIGHGRAVITY_MODEL"
            ],
            "window_name": [
                "CASCADE_WINDOW_NAME", "HIGHGRAVITY_WINDOW_NAME", "HIGHGRAVITY_WINDOW_ID"
            ],
            "windsurf_binary": [
                "WINDSURF_BIN", "WINDSURF_BINARY"
            ],
            "monitor": [
                "CASCADE_MONITOR", "HIGHGRAVITY_MONITOR"
            ],
            "check": [
                "CASCADE_CHECK", "HIGHGRAVITY_CHECK"
            ],
            "dry_run": [
                "CASCADE_DRY_RUN", "HIGHGRAVITY_DRY_RUN"
            ],
            "new_window": [
                "CASCADE_NEW_WINDOW", "HIGHGRAVITY_NEW_WINDOW"
            ],
        }

        overrides = {}
        for dest, names in aliases.items():
            for name in names:
                value = os.environ.get(name)
                if value not in {None, ""}:
                    overrides[dest] = value
                    break

        return overrides

    def resolve_runtime_options(self, args, stdin_overrides: Dict, env_overrides: Dict) -> Dict:
        """
        Merge CLI, stdin, and environment inputs with explicit precedence.

        Precedence:
        1. CLI arguments
        2. stdin payload
        3. environment variables
        4. built-in defaults
        """
        defaults = {
            "api_key": None,
            "key_index": None,
            "mode": "studio",
            "provider": "proxy",
            "proxy_url": "http://localhost:9999",
            "model": "gemini-2.0-flash-exp",
            "window_name": "default",
            "windsurf_binary": "windsurf",
            "monitor": None,
            "check": False,
            "dry_run": False,
            "new_window": True,
        }

        cli_values = {
            "api_key": args.api_key,
            "key_index": args.key_index,
            "mode": args.mode,
            "provider": args.provider,
            "proxy_url": args.proxy_url,
            "model": args.model,
            "window_name": args.window_name,
            "windsurf_binary": args.windsurf_binary,
            "monitor": args.monitor,
            "check": args.check,
            "dry_run": args.dry_run,
            "new_window": None if args.no_new_window is None else not args.no_new_window,
        }

        resolved = {}
        for key, default in defaults.items():
            value = cli_values.get(key)
            if value is None and key in stdin_overrides:
                value = stdin_overrides[key]
            if value is None and key in env_overrides:
                value = env_overrides[key]
            if value is None:
                value = default
            resolved[key] = value

        if resolved["key_index"] is not None:
            resolved["key_index"] = int(resolved["key_index"])
        if resolved["monitor"] is not None:
            resolved["monitor"] = int(resolved["monitor"])

        resolved["check"] = bool(self._coerce_bool(resolved["check"]))
        resolved["dry_run"] = bool(self._coerce_bool(resolved["dry_run"]))
        new_window_value = self._coerce_bool(resolved["new_window"])
        resolved["new_window"] = True if new_window_value is None else bool(new_window_value)

        return resolved

    def build_windsurf_profile(
        self,
        api_key: str,
        window_name: str = "default",
        provider: str = "proxy",
        model: str = "gemini-2.0-flash-exp",
        proxy_url: str = "http://localhost:9999",
        fallback_to_direct: bool = True
    ) -> Dict:
        """
        Build a Windsurf-friendly profile with env vars and metadata.

        This avoids guessing Windsurf's internal config schema and instead
        provides a stable launch/env contract for wrapper scripts.
        """
        profile_id = self._slugify(window_name)
        env = {
            "GEMINI_API_KEY": api_key,
            "GOOGLE_API_KEY": api_key,
            "HIGHGRAVITY_WINDOW_ID": profile_id,
            "HIGHGRAVITY_WINDOW_NAME": window_name,
            "HIGHGRAVITY_PROVIDER": provider,
            "HIGHGRAVITY_MODEL": model,
            "HIGHGRAVITY_FALLBACK_TO_DIRECT": "true" if fallback_to_direct else "false",
        }

        if provider == "proxy":
            env.update({
                "HIGHGRAVITY_PROXY_URL": proxy_url,
                "OPENAI_BASE_URL": proxy_url,
                "OPENAI_API_BASE": proxy_url,
                "OPENAI_API_KEY": api_key,
                "ANTHROPIC_BASE_URL": proxy_url,
                "ANTHROPIC_API_BASE": proxy_url,
                "ANTHROPIC_API_KEY": api_key,
            })

        profile = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "profile_id": profile_id,
            "window_name": window_name,
            "provider": provider,
            "model": model,
            "proxy_url": proxy_url if provider == "proxy" else None,
            "fallback_to_direct": fallback_to_direct,
            "windsurf": {
                "binary": "windsurf",
                "recommended_launch_args": ["--new-window"],
            },
            "env": env,
        }

        return profile

    def _render_env_file(self, env: Dict[str, str]) -> str:
        """Render env vars in a shell-compatible .env format"""
        lines = [
            "# Generated by gemini_session_launcher.py",
            "# shellcheck disable=SC2034",
        ]
        for key in sorted(env):
            lines.append(f"{key}={shlex.quote(str(env[key]))}")
        return "\n".join(lines) + "\n"

    def write_windsurf_profile(
        self,
        profile: Dict,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Path]:
        """Write Windsurf profile metadata and env file to disk"""
        if output_dir is None:
            output_dir = REPO_ROOT / "windsurf_profiles" / profile["profile_id"]

        output_dir.mkdir(parents=True, exist_ok=True)

        env_path = output_dir / "profile.env"
        metadata_path = output_dir / "profile.json"
        launch_path = output_dir / "launch_windsurf.sh"

        env_path.write_text(self._render_env_file(profile["env"]))
        env_path.chmod(0o600)
        metadata_path.write_text(json.dumps(profile, indent=2) + "\n")
        metadata_path.chmod(0o600)
        launch_path.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            'set -a\n'
            f'. "{env_path}"\n'
            'set +a\n'
            'exec "${WINDSURF_BIN:-windsurf}" --new-window "$@"\n'
        )
        launch_path.chmod(0o755)

        return {
            "directory": output_dir,
            "env_file": env_path,
            "metadata_file": metadata_path,
            "launch_script": launch_path,
        }

    def print_windsurf_profile_summary(self, profile: Dict, files: Optional[Dict[str, Path]] = None):
        """Display Windsurf integration details"""
        print("\n" + "="*70)
        print("WINDSURF PROFILE")
        print("="*70)
        print(f"Window:   {profile['window_name']}")
        print(f"Provider: {profile['provider']}")
        print(f"Model:    {profile['model']}")
        if profile.get("proxy_url"):
            print(f"Proxy:    {profile['proxy_url']}")
        print(f"Fallback: {profile['fallback_to_direct']}")
        print("\nEnvironment:")
        for key, value in sorted(profile["env"].items()):
            if key.endswith("_KEY"):
                value = self._mask_key(value)
            print(f"  {key}={value}")

        if files:
            print("\nArtifacts:")
            print(f"  Env file:      {files['env_file']}")
            print(f"  Profile JSON:  {files['metadata_file']}")
            print(f"  Launch script: {files['launch_script']}")

        print("="*70 + "\n")

    def launch_windsurf(
        self,
        api_key: str,
        window_name: str = "default",
        provider: str = "proxy",
        model: str = "gemini-2.0-flash-exp",
        proxy_url: str = "http://localhost:9999",
        fallback_to_direct: bool = True,
        binary: str = "windsurf",
        new_window: bool = True,
        write_profile: bool = True,
        dry_run: bool = False
    ) -> Dict:
        """
        Prepare and optionally launch Windsurf with a generated profile.
        """
        profile = self.build_windsurf_profile(
            api_key=api_key,
            window_name=window_name,
            provider=provider,
            model=model,
            proxy_url=proxy_url,
            fallback_to_direct=fallback_to_direct,
        )

        files = None
        if write_profile:
            files = self.write_windsurf_profile(profile)
            profile["profile_dir"] = str(files["directory"])

        self.print_windsurf_profile_summary(profile, files=files)

        cmd = [binary]
        if new_window:
            cmd.append("--new-window")

        if dry_run:
            print("[*] Dry run enabled; not launching Windsurf")
            print(f"[*] Launch command: {' '.join(shlex.quote(part) for part in cmd)}")
            if files:
                print(f"[*] Recommended: {files['launch_script']}")
            return {
                "launched": False,
                "profile": profile,
                "files": files,
                "command": cmd,
            }

        resolved_binary = shutil.which(binary)
        if not resolved_binary:
            print(f"[!] Windsurf binary not found in PATH: {binary}")
            if files:
                print(f"[*] Use launch script once Windsurf is installed: {files['launch_script']}")
            return {
                "launched": False,
                "profile": profile,
                "files": files,
                "command": cmd,
                "error": "binary_not_found",
            }

        env = os.environ.copy()
        env.update(profile["env"])

        print(f"[*] Launching Windsurf binary: {resolved_binary}")
        subprocess.Popen(cmd, env=env)
        print("[+] Windsurf launch requested")

        return {
            "launched": True,
            "profile": profile,
            "files": files,
            "command": cmd,
        }
    
    def list_keys(self):
        """Display available API keys"""
        print("\n" + "="*70)
        print("AVAILABLE GEMINI API KEYS")
        print("="*70)
        
        for i, key_data in enumerate(self.keys, 1):
            key = key_data["key"]
            status = key_data.get("status", "unknown")
            has_veo = key_data.get("has_veo_files", False)
            
            # Mask key for display
            masked = key[:20] + "..." + key[-10:]
            
            veo_indicator = " [VEO ✓]" if has_veo else ""
            print(f"{i:2d}. {masked} - {status}{veo_indicator}")
        
        print("="*70 + "\n")
    
    def check_key_validity(self, api_key: str) -> Dict:
        """
        Check if API key is valid and what models it can access
        
        Returns:
            Dict with validity status and available models
        """
        print(f"[*] Checking key validity...")
        
        # Try to list models
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                
                # Extract model names
                model_names = [m["name"] for m in models]
                
                # Check for Veo access
                veo_models = [m for m in model_names if "veo" in m.lower()]
                gemini_models = [m for m in model_names if "gemini" in m.lower()]
                
                result = {
                    "valid": True,
                    "total_models": len(models),
                    "veo_models": veo_models,
                    "gemini_models": gemini_models,
                    "has_veo": len(veo_models) > 0
                }
                
                print(f"[+] Key is VALID")
                print(f"    Total models: {len(models)}")
                print(f"    Veo models: {len(veo_models)}")
                print(f"    Gemini models: {len(gemini_models)}")
                
                return result
                
            elif response.status_code == 403:
                print(f"[!] Key is INVALID or EXPIRED")
                return {"valid": False, "error": "Permission denied"}
                
            elif response.status_code == 429:
                print(f"[!] Key has EXCEEDED QUOTA")
                return {"valid": False, "error": "Quota exceeded"}
                
            else:
                print(f"[!] Unexpected response: {response.status_code}")
                return {"valid": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"[!] Error checking key: {e}")
            return {"valid": False, "error": str(e)}
    
    def launch_gemini_web(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        """
        Launch Gemini web interface with API key
        
        Args:
            api_key: Gemini API key
            model: Model to use (default: gemini-2.0-flash-exp)
        """
        # Gemini AI Studio URL with API key parameter
        url = f"https://aistudio.google.com/app/apikey?key={api_key}"
        
        print(f"\n[*] Launching Gemini AI Studio...")
        print(f"    URL: https://aistudio.google.com/app/apikey")
        print(f"    Model: {model}")
        print(f"    Key: {api_key[:20]}...{api_key[-10:]}")
        
        # Open in default browser
        webbrowser.open(url)
        
        print(f"[+] Browser launched")
        print(f"[*] Waiting for session initialization...")
        
        return url
    
    def launch_gemini_chat(self, api_key: str):
        """
        Launch Gemini chat interface
        
        Args:
            api_key: Gemini API key
        """
        # Direct chat URL
        url = "https://gemini.google.com/"
        
        print(f"\n[*] Launching Gemini Chat...")
        print(f"    URL: {url}")
        print(f"    Key ready for injection: {self._mask_key(api_key)}")
        
        # Open in default browser
        webbrowser.open(url)
        
        print(f"[+] Browser launched")
        print(f"\n[!] MANUAL STEP REQUIRED:")
        print(f"    1. Click on your profile icon")
        print(f"    2. Go to 'Settings'")
        print(f"    3. Navigate to 'API Keys'")
        print(f"    4. Paste the selected key from your local key store")
        
        return url
    
    def monitor_session_tui(self, api_key: str, duration: int = 300, interval: int = 30):
        """
        Monitor Gemini API key health with rich TUI dashboard
        
        Args:
            api_key: API key to monitor
            duration: Total monitoring duration in seconds
            interval: Check interval in seconds
        """
        if not RICH_AVAILABLE:
            return self.monitor_session(api_key, duration, interval)
        
        console = Console()
        start_time = time.time()
        check_count = 0
        status_history = []
        
        def generate_dashboard():
            elapsed = time.time() - start_time
            remaining = max(0, duration - elapsed)
            progress_pct = min(100, (elapsed / duration) * 100)
            
            # Header
            header = Panel(
                f"[bold cyan]GEMINI SESSION MONITOR[/bold cyan]\n"
                f"Key: {self._mask_key(api_key)}",
                style="bold blue"
            )
            
            # Status table
            table = Table(title="API Key Health", show_header=True, header_style="bold magenta")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Checks Performed", str(check_count))
            table.add_row("Elapsed Time", f"{elapsed:.0f}s ({elapsed/60:.1f} min)")
            table.add_row("Remaining Time", f"{remaining:.0f}s ({remaining/60:.1f} min)")
            table.add_row("Progress", f"{progress_pct:.1f}%")
            table.add_row("Check Interval", f"{interval}s")
            
            if status_history:
                last_status = status_history[-1]
                status_str = "[green]✓ VALID[/green]" if last_status.get("valid") else "[red]✗ INVALID[/red]"
                table.add_row("Current Status", status_str)
                
                if last_status.get("valid"):
                    table.add_row("Total Models", str(last_status.get("total_models", 0)))
                    table.add_row("Veo Models", str(len(last_status.get("veo_models", []))))
                    table.add_row("Gemini Models", str(len(last_status.get("gemini_models", []))))
            
            # Status history
            history_text = Text()
            for i, status in enumerate(status_history[-10:], 1):
                if status.get("valid"):
                    history_text.append(f"✓ ", style="green")
                else:
                    history_text.append(f"✗ ", style="red")
            
            history_panel = Panel(history_text, title="Recent Checks (last 10)", border_style="yellow")
            
            # Combine layout
            layout = Layout()
            layout.split_column(
                Layout(header, size=3),
                Layout(table),
                Layout(history_panel, size=3)
            )
            
            return layout
        
        with Live(generate_dashboard(), refresh_per_second=1, console=console) as live:
            while time.time() - start_time < duration:
                check_count += 1
                
                # Check key validity
                status = self.check_key_validity(api_key)
                status_history.append(status)
                
                # Update dashboard
                live.update(generate_dashboard())
                
                # Wait for next check
                elapsed = time.time() - start_time
                remaining = duration - elapsed
                
                if remaining > interval:
                    time.sleep(interval)
                else:
                    if remaining > 0:
                        time.sleep(remaining)
                    break
        
        # Final summary
        console.print("\n[bold green]MONITORING COMPLETE[/bold green]")
        console.print(f"Total checks: {check_count}")
        console.print(f"Duration: {time.time() - start_time:.0f}s")
        
        valid_checks = sum(1 for s in status_history if s.get("valid"))
        console.print(f"Success rate: {valid_checks}/{check_count} ({valid_checks/check_count*100:.1f}%)")
    
    def monitor_session(self, api_key: str, duration: int = 300, interval: int = 30):
        """
        Monitor Gemini API key health (fallback without TUI)
        
        Args:
            api_key: API key to monitor
            duration: Total monitoring duration in seconds
            interval: Check interval in seconds
        """
        print(f"\n{'='*70}")
        print(f"MONITORING GEMINI API KEY HEALTH")
        print(f"{'='*70}")
        print(f"Duration: {duration}s ({duration/60:.1f} min)")
        print(f"Check interval: {interval}s")
        print(f"{'='*70}\n")
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < duration:
            check_count += 1
            elapsed = time.time() - start_time
            
            print(f"\n[Check {check_count}] Elapsed: {elapsed:.0f}s")
            
            # Check key validity
            status = self.check_key_validity(api_key)
            
            if not status.get("valid"):
                print(f"[!] Key check failed")
            else:
                print(f"[+] Key is usable")
            
            # Wait for next check
            remaining = duration - elapsed
            if remaining > interval:
                print(f"[*] Next check in {interval}s...")
                time.sleep(interval)
            else:
                if remaining > 0:
                    time.sleep(remaining)
                break
        
        print(f"\n{'='*70}")
        print(f"MONITORING COMPLETE")
        print(f"{'='*70}")
        print(f"Total checks: {check_count}")
        print(f"Duration: {time.time() - start_time:.0f}s")
        print(f"{'='*70}\n")
    
    def interactive_launch(self):
        """Interactive session launcher"""
        print("\n" + "="*70)
        print("GEMINI SESSION LAUNCHER")
        print("="*70)

        if not self.ensure_keys_file():
            print("Exiting...")
            return
        
        # List available keys
        self.list_keys()
        
        # Select key
        while True:
            try:
                choice = input("Select key number (or 'q' to quit): ").strip()
                
                if choice.lower() == 'q':
                    print("Exiting...")
                    return
                
                key_idx = int(choice) - 1
                
                if 0 <= key_idx < len(self.keys):
                    selected_key = self.keys[key_idx]["key"]
                    break
                else:
                    print(f"[!] Invalid selection. Choose 1-{len(self.keys)}")
            except ValueError:
                print("[!] Please enter a number")
        
        print(f"\n[+] Selected key: {self._mask_key(selected_key)}")
        
        # Check key validity
        status = self.check_key_validity(selected_key)
        
        if not status.get("valid"):
            print(f"\n[!] Warning: Key may not be valid")
            proceed = input("Continue anyway? (y/n): ").strip().lower()
            if proceed != 'y':
                print("Cancelled.")
                return
        
        # Choose launch mode
        print(f"\nLaunch mode:")
        print(f"  1. AI Studio (API key injection)")
        print(f"  2. Gemini Chat (manual setup)")
        print(f"  3. Windsurf (profile + launch helper)")
        
        mode = input("Select mode (1, 2, or 3): ").strip()
        
        if mode == "1":
            url = self.launch_gemini_web(selected_key)
        elif mode == "2":
            url = self.launch_gemini_chat(selected_key)
        elif mode == "3":
            window_name = input("Windsurf window/profile name (default: default): ").strip() or "default"
            provider = input("Provider mode [proxy/direct] (default: proxy): ").strip().lower() or "proxy"
            if provider not in {"proxy", "direct"}:
                print("[!] Invalid provider; use 'proxy' or 'direct'")
                return
            proxy_url = "http://localhost:9999"
            if provider == "proxy":
                proxy_url = input("Proxy URL (default: http://localhost:9999): ").strip() or "http://localhost:9999"
            result = self.launch_windsurf(
                selected_key,
                window_name=window_name,
                provider=provider,
                proxy_url=proxy_url,
                dry_run=False,
            )
            url = result.get("files", {}).get("launch_script") if result.get("files") else None
        else:
            print("[!] Invalid mode")
            return
        
        # Wait for initialization
        if mode in {"1", "2"}:
            print(f"\n[*] Waiting 10 seconds for page load...")
            time.sleep(10)
        
        # Ask if user wants monitoring
        monitor = input("\nMonitor session? (y/n): ").strip().lower()
        
        if monitor == 'y':
            duration = input("Duration in seconds (default: 300): ").strip()
            duration = int(duration) if duration else 300
            
            # Use TUI if available
            if RICH_AVAILABLE:
                self.monitor_session_tui(selected_key, duration=duration)
            else:
                self.monitor_session(selected_key, duration=duration)
        else:
            print(f"\n[+] Launch flow completed")
            print(f"    Selected key: {self._mask_key(selected_key)}")
            print(f"    Profile or browser state has been prepared")


def main():
    parser = argparse.ArgumentParser(description="Gemini and Windsurf launch helper")
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

    args = parser.parse_args()
    
    launcher = GeminiSessionLauncher(keys_file=args.keys_file)
    stdin_overrides = launcher.load_stdin_overrides(stdin_format=args.stdin_format)
    env_overrides = launcher.load_environment_overrides()
    runtime = launcher.resolve_runtime_options(args, stdin_overrides, env_overrides)

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
        else:
            launcher.launch_windsurf(
                selected_key,
                window_name=runtime["window_name"],
                provider=runtime["provider"],
                model=runtime["model"],
                proxy_url=runtime["proxy_url"],
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
