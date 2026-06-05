#!/usr/bin/env python3
"""
HIGH-GRAVITY Pegasus Dashboard v3.2
Expert-Tier Shield & Intelligence Control Plane.
"""
import os
import socket
import sys
import time
import select
import termios
import tty
import subprocess
import requests
import json
import random
import shlex
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markup import escape

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs"
PROXY_PORT = int(os.environ.get("HG_PROXY_PORT", "9998"))
PROXY_HOST = "127.0.0.1"
PROXY_URL = f"http://{PROXY_HOST}:{PROXY_PORT}"

THINKING_TIERS = [
    ("low",    "Basic",      "cyan"),
    ("medium", "Advanced",   "green"),
    ("high",   "Deep",       "yellow"),
    ("xhigh",  "Extreme",    "magenta"),
]

JS_ORIGINAL_URLS = [
    b"https://api.codeium.com",
    b"https://server.codeium.com",
    b"https://inference.codeium.com",
    b"https://server.self-serve.windsurf.com",
]
JS_PATCHED_URLS = [
    b"https://proxy.windsurf.com",
    b"https://inferapi.windsurf.com",
]
WB_ORIGINAL_INTEGRITY = b"isPure(){return this.isPurePromise}"
WB_PATCHED_INTEGRITY = b"isPure(){return Promise.resolve({isPure:!0})}"


class Dashboard:
    def __init__(self):
        self.tel = {}
        self.khoj = {}
        self.tel_error = ""
        self.status_msg = "[dim]Initializing Expert-Tier Control Plane...[/dim]"
        self.view = "main"   # main | logs
        self.log_name = "proxy.log"
        self.console = Console()

    def _proxy_listener_reachable(self):
        try:
            with socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=1.0):
                return True
        except OSError:
            return False

    def fetch(self):
        if not self._proxy_listener_reachable():
            self.tel = {}
            self.khoj = {}
            self.tel_error = "LISTENER_OFFLINE"
            return
        try:
            r = requests.get(f"{PROXY_URL}/hg/telemetry", timeout=2.0)
            if r.ok:
                self.tel = r.json()
            else:
                self.tel = {}
                self.tel_error = f"HTTP_{r.status_code}"
                self.khoj = {}
                return
            self.khoj = self.tel.get("khoj", {})
            if self.tel.get("proxy_port"):
                os.environ.setdefault("HG_PROXY_PORT", str(self.tel.get("proxy_port")))
            self.tel_error = ""
        except Exception as e:
            self.tel = {}
            self.khoj = {}
            self.tel_error = type(e).__name__
            return

    def read_log_tail(self, name, n=40):
        p = LOG_DIR / name
        if not p.exists():
            return [f"(not found: {p})"]
        try:
            lines = p.read_text(errors="replace").splitlines()
            return lines[-n:] if lines else ["(empty)"]
        except Exception as e:
            return [f"Error reading log: {e}"]

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
        except: pass
        return None

    def action(self, name):
        try:
            requests.post(f"{PROXY_URL}/hg/manage", json={"action": name}, timeout=2)
            self.status_msg = f"[green]Action '{name}' sent successfully[/green]"
        except Exception:
            self.status_msg = f"[red]Action '{name}' failed[/red]"

    def _command_env(self, args, extra_env=None):
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        hg_cmd = ""
        if len(args) >= 2 and Path(args[0]).name == "hg.sh":
            hg_cmd = args[1]
        elif len(args) >= 2 and args[0] == "bash" and Path(args[1]).name == "hg.sh":
            hg_cmd = args[2] if len(args) >= 3 else ""
        if "proxy" in hg_cmd:
            env.setdefault("HG_PROXY_WATCHDOG", "0")
            env.setdefault("HG_CLIENT_TARGET", "antigravity")
            env.setdefault("HG_TRAFFIC_MUTATION_ENABLED", "0")
            env.setdefault("HG_DECRYPTED_TRAFFIC_LOG", "1")
            env.setdefault("HG_DECRYPTED_TRAFFIC_FULL_BODY", "1")
            env.setdefault("HG_KHOJ_BINARY_INJECT", "0")
            env.setdefault("HG_TOKEN_SAVER", "0")
            env.setdefault("HG_TOKEN_SAVER_DISABLE_CONTEXT_INJECTION", "1")
            env.setdefault("HG_TOKEN_SAVER_FORCE_LOW_REASONING", "0")
            env.setdefault("HG_EXACT_RESPONSE_CACHE", "0")
            env.setdefault("HG_CANONICAL_RESPONSE_CACHE", "0")
            env.setdefault("HG_LOCAL_ACK_TELEMETRY", "0")
            env.setdefault("HG_PEGASUS_SWARM_TRIGGER", "0")
            env.setdefault("HG_PROXY_VERBOSE_REQUEST_LOGS", "0")
            env.setdefault("HG_PROXY_LOG_DEEP_INTEL", "0")
            env.setdefault("HG_PROXY_LOG_ACCESS", "0")
        return env

    def run_cmd(self, label, cmd):
        self.status_msg = f"[yellow]{label}...[/yellow]"
        try:
            args = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
            extra_env = {}
            while args and "=" in args[0] and not args[0].startswith("./"):
                key, value = args.pop(0).split("=", 1)
                if key:
                    extra_env[key] = value
            if args and args[0] == "./hg.sh":
                args = ["bash", str(REPO_ROOT / "hg.sh")] + args[1:]
            subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=REPO_ROOT,
                env=self._command_env(args, extra_env),
                start_new_session=True,
            )
            self.status_msg = f"[green]{label} triggered[/green]"
        except Exception as e:
            self.status_msg = f"[red]{label} error: {e}[/red]"

    # --- Panels ---
    def _status_badge(self, ok, true_label="ON", false_label="OFF"):
        return f"[green]{true_label}[/green]" if ok else f"[dim]{false_label}[/dim]"

    def _int_value(self, data, key):
        try:
            return int(data.get(key, 0) or 0)
        except Exception:
            return 0

    def _ratio_value(self, numerator, denominator):
        try:
            denominator = float(denominator or 0)
            if denominator <= 0:
                return 0.0
            return max(0.0, min(100.0, (float(numerator or 0) / denominator) * 100.0))
        except Exception:
            return 0.0

    def _upstream_mode_style(self, mode):
        mode = str(mode or "cache-first")
        if mode == "cache-first":
            return "green"
        if mode in {"cache-only", "local-only"}:
            return "yellow"
        if mode in {"confirm", "block"}:
            return "red"
        return "cyan"

    def restart_proxy_mode(self, mode):
        if mode not in {"cache-first", "cache-only", "confirm", "block", "local-only"}:
            self.status_msg = f"[red]Invalid proxy mode: {escape(str(mode))}[/red]"
            return
        self.run_cmd(f"C Proxy {mode}", f"./hg.sh proxy start {mode}")

    def _first_error(self, errors, limit=50):
        if not errors:
            return ""
        return str(errors[0])[:limit]

    def _myriad_status(self, accel):
        active = accel.get("runtime_active", {}) or {}
        proof = accel.get("proof", {}) or {}
        proof_compile = ((proof.get("myriad") or {}).get("compile") or {})
        proof_error = str(proof_compile.get("error", "") or "")
        devices = active.get("myriad_devices") or [
            device
            for device in active.get("openvino_devices_visible", [])
            if str(device).upper() == "MYRIAD" or str(device).upper().startswith("MYRIAD.")
        ]
        errors = active.get("myriad_compile_errors") or ([proof_error] if proof_error else [])
        boot_failed = bool(active.get("myriad_boot_failed")) or any(
            marker in error.lower()
            for error in errors
            for marker in ("not opened", "failed to find booted device", "allocate graph", "boot")
        )
        compile_failed = bool(active.get("myriad_compile_failed")) or bool(
            devices and proof_compile and proof_compile.get("ok") is False
        )
        compile_ok = bool(active.get("myriad_compile_ok") or active.get("myriad"))
        visible = bool(active.get("myriad_visible") or devices)
        return {
            "compile_ok": compile_ok,
            "boot_failed": boot_failed,
            "compile_failed": compile_failed,
            "visible": visible,
            "errors": errors,
        }

    def _acceleration_summary(self):
        accel = self.khoj.get("acceleration", {}) or {}
        active = accel.get("runtime_active", {}) or {}
        runtime = accel.get("runtime", {}) or {}
        torch_info = runtime.get("torch", {}) or {}
        ov_info = runtime.get("openvino", {}) or {}
        bits = []
        if active.get("cuda") or torch_info.get("cuda_runtime_ok"):
            bits.append("CUDA runtime")
        elif torch_info.get("cuda_available"):
            bits.append("CUDA visible")
        elif accel.get("cuda"):
            bits.append("CUDA exposed")
        ov_devices = active.get("openvino_devices_visible") or ov_info.get("devices") or []
        if ov_devices:
            ov_state = "OV compile" if active.get("openvino_compile_ok", active.get("openvino")) else "OV visible"
            bits.append(f"{ov_state}:" + ",".join(ov_devices[:3]))
        elif accel.get("openvino"):
            bits.append("OV exposed")
        requested_device = (ov_info.get("requested_device") or "").strip()
        if requested_device and requested_device.upper() != "AUTO":
            if not ov_info.get("requested_device_supported", True):
                bits.append(f"OV req {requested_device} unavailable")
        myriad_count = accel.get("myriad_count", 0)
        myriad = self._myriad_status(accel)
        if myriad["compile_ok"]:
            bits.append(f"MYRIAD compile x{myriad_count}")
        elif myriad["boot_failed"]:
            bits.append(f"MYRIAD boot failed x{myriad_count}")
        elif myriad["compile_failed"]:
            bits.append(f"MYRIAD compile failed x{myriad_count}")
        elif myriad["visible"]:
            bits.append(f"MYRIAD visible x{myriad_count}")
        elif accel.get("myriad"):
            bits.append(f"MYRIAD exposed x{myriad_count}")
        return " | ".join(bits) if bits else "CPU"

    def _proxy_panel(self):
        t = self.tel
        k = self.khoj
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        online = bool(t)
        if self.tel_error:
            status = f"[yellow]DEGRADED[/yellow] ({self.tel_error})"
            if self.tel_error == "LISTENER_OFFLINE":
                status = "[red]OFFLINE[/red] (listener down)"
        elif online:
            status = "[green]ONLINE[/green]"
        else:
            status = "[red]OFFLINE[/red]"
        tbl.add_row("Status", status)
        tbl.add_row("Port", str(t.get("proxy_port", PROXY_PORT)))
        mode = str(t.get("upstream_inference_mode") or (t.get("shared_metrics", {}) or {}).get("upstream_inference_mode") or "cache-first")
        mode_style = self._upstream_mode_style(mode)
        tbl.add_row("Inference Mode", f"[{mode_style}]{escape(mode)}[/{mode_style}]")
        tbl.add_row("Active Keys", f"{t.get('active_keys', 0)} / {t.get('total_keys', 0)}")
        tbl.add_row("Cache Hits", str(t.get("cache_hits", 0)))
        shared = t.get("shared_metrics", {}) or {}
        cp_hits = self._int_value(shared, "control_plane_cache_hits")
        cp_stores = self._int_value(shared, "control_plane_cache_stores")
        tbl.add_row("Control-Plane Cache", f"{cp_hits:,} / {cp_stores:,}")
        exact_hits = self._int_value(shared, "exact_response_cache_hits")
        exact_stores = self._int_value(shared, "exact_response_cache_stores")
        canonical_hits = self._int_value(shared, "canonical_response_cache_hits")
        canonical_stores = self._int_value(shared, "canonical_response_cache_stores")
        cache_total_hits = exact_hits + canonical_hits
        cache_total_stores = exact_stores + canonical_stores
        tbl.add_row(
            "Response Cache",
            f"{cache_total_hits:,} hit / {cache_total_stores:,} store "
            f"[dim]({self._ratio_value(cache_total_hits, cache_total_stores):.0f}%)[/dim]",
        )
        forwards = self._int_value(shared, "upstream_inference_forwards")
        misses = self._int_value(shared, "upstream_inference_cache_misses")
        blocks = self._int_value(shared, "upstream_inference_blocks") + self._int_value(shared, "upstream_inference_cache_only_blocks")
        gate_style = "red" if blocks else "yellow" if forwards else "green"
        tbl.add_row(
            "Upstream Gate",
            f"[{gate_style}]{forwards:,} fwd / {misses:,} miss / {blocks:,} block[/{gate_style}]",
        )
        local_acks = self._int_value(shared, "local_ack_telemetry")
        local_ack_bytes = self._int_value(shared, "local_ack_bytes_avoided")
        tbl.add_row("Local ACK", f"{local_acks:,} req / {local_ack_bytes / 1024.0:.1f} KiB")
        guard_blocks = self._int_value(shared, "billing_guard_blocks")
        guard_allows = self._int_value(shared, "billing_guard_allows")
        guard_style = "red" if guard_blocks else "green"
        tbl.add_row("Billing Guard", f"[{guard_style}]{guard_blocks:,} block / {guard_allows:,} pass[/{guard_style}]")
        tbl.add_row("Tokens Saved", f"{t.get('tokens_saved', 0):,}")
        fail_open = self._int_value(shared, "binary_fail_open")
        if fail_open:
            tbl.add_row("Large Fail-open", f"[yellow]{fail_open:,}[/yellow]")
        avoided = self._int_value(k, "binary_tokens_avoided")
        injected = self._int_value(k, "binary_tokens_injected")
        tbl.add_row("RAG Tokens", f"+{injected:,} / -{avoided:,}")
        tbl.add_row("Throughput", f"{t.get('total_requests', 0)} req")
        return Panel(tbl, title="Quantum Proxy", border_style="green")

    def _ebpf_panel(self):
        ebpf = self.tel.get("ebpf", {}) if isinstance(self.tel.get("ebpf"), dict) else {}
        observer = ebpf.get("status") if isinstance(ebpf.get("status"), dict) else {}
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        if not ebpf.get("present"):
            tbl.add_row("Observer", "[dim]inactive[/dim]")
            tbl.add_row("Events", "0")
            tbl.add_row("Path", escape(str(ebpf.get("event_path", "logs/ebpf_events.jsonl"))))
            return Panel(tbl, title="Kernel Observer", border_style="dim")

        rows = self._int_value(ebpf, "events_total")
        read_error = ebpf.get("read_error")
        stale = bool(ebpf.get("stale") or observer.get("stale"))
        active = bool(ebpf.get("active") or observer.get("active") or observer.get("running"))
        if read_error:
            status_style = "red"
            status_label = "READ ERROR"
        elif stale:
            status_style = "yellow"
            status_label = "STALE"
        elif active:
            status_style = "green"
            status_label = "ACTIVE"
        elif rows:
            status_style = "green"
            status_label = "EVENT DATA"
        else:
            status_style = "yellow"
            status_label = "NO EVENTS"
        tbl.add_row("Observer", f"[{status_style}]{status_label}[/{status_style}]")
        mode = (
            ebpf.get("mode")
            or observer.get("mode")
            or observer.get("active_mode")
            or "-"
        )
        tool = (
            ebpf.get("tool")
            or observer.get("tool")
            or observer.get("active_tool")
            or observer.get("backend")
            or "-"
        )
        tbl.add_row("Mode / Tool", escape(f"{mode} / {tool}"))
        tbl.add_row("Events", f"{rows:,} rows")
        event_text = ", ".join(
            f"{key}:{value}" for key, value in (ebpf.get("by_event") or {}).items()
        ) or "none"
        tbl.add_row("Event Types", escape(event_text))
        route_text = ", ".join(
            f"{key}:{value}" for key, value in (ebpf.get("by_route_class") or {}).items()
        ) or "none"
        tbl.add_row("Route Classes", escape(route_text))
        direct = self._int_value(ebpf, "direct_egress")
        direct_style = "red" if direct else "green"
        tbl.add_row("Direct Egress", f"[{direct_style}]{direct:,}[/{direct_style}]")
        retry = ebpf.get("retry_storm") if isinstance(ebpf.get("retry_storm"), dict) else {}
        retry_style = "red" if retry.get("active") else "green"
        retry_state = "active" if retry.get("active") else "quiet"
        tbl.add_row(
            "Retry Storm",
            (
                f"[{retry_style}]{retry_state} / "
                f"{self._int_value(retry, 'max_rate'):,} max[/{retry_style}]"
            ),
        )
        sessions = ebpf.get("sessions") if isinstance(ebpf.get("sessions"), dict) else {}
        session_count = self._int_value(sessions, "session_count")
        required_sessions = self._int_value(sessions, "required_sessions")
        if sessions:
            session_style = "green" if sessions.get("ok") else "yellow"
            tbl.add_row(
                "Sessions",
                (
                    f"[{session_style}]{session_count}/"
                    f"{required_sessions} visible[/{session_style}]"
                ),
            )
        else:
            tbl.add_row("Sessions", "[dim]not reported[/dim]")
        tbl.add_row("Dst Peers", f"{self._int_value(ebpf, 'unique_dst_peers'):,}")
        recent = ebpf.get("recent") if isinstance(ebpf.get("recent"), list) else []
        if recent:
            last = recent[-1] if isinstance(recent[-1], dict) else {}
            comm = escape(str(last.get("comm") or "-")[:24])
            dst = escape(f"{last.get('dst_ip') or '-'}:{last.get('dst_port') or '-'}")
            tbl.add_row("Last", f"{comm} [dim]{dst}[/dim]")
        return Panel(tbl, title="Kernel Observer", border_style=status_style)

    def _intelligence_panel(self):
        k = self.khoj
        t = self.tel
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        tbl.add_row("Khoj RAG", "[green]ACTIVE[/green]" if k.get("enabled") else "[dim]IDLE[/dim]")
        tbl.add_row("RAG Injects", f"{self._int_value(k, 'injection_count'):,}")
        tbl.add_row("Binary Injects", f"{self._int_value(k, 'binary_injection_count'):,}")
        tbl.add_row("RAG Hits", f"{self._int_value(k, 'passive_hit_count'):,}")
        tbl.add_row("RAG Cache", f"{self._int_value(k, 'search_cache_hits'):,}")
        tbl.add_row("RAG Dedupes", f"{self._int_value(k, 'binary_inject_dedupe_skips'):,}")
        tbl.add_row("Stored Intel", f"{self._int_value(k, 'stored_observation_count'):,}")
        summary = self._acceleration_summary()
        accel_style = "green" if summary != "CPU" else "dim"
        tbl.add_row("Khoj Accel", f"[{accel_style}]{escape(summary)}[/{accel_style}]")

        # Expert Shield Stats
        thinking = t.get("mitm_thinking_by_level", {})
        deep_hits = self._int_value(thinking, "high") + self._int_value(thinking, "xhigh")
        tbl.add_row("Deep Think", f"[bold yellow]{deep_hits:,}[/bold yellow]")
        shared = t.get("shared_metrics", {}) or {}
        tbl.add_row(
            "Reasoning Injections",
            f"[bold green]{int(shared.get('mitm_reasoning_injections', 0) or 0):,}[/bold green]",
        )
        swarm = t.get("pegasus_swarm", {}) if isinstance(t.get("pegasus_swarm"), dict) else {}
        active_workers = self._int_value(swarm, "active_workers")
        max_workers = self._int_value(swarm, "max_active_workers") or 3
        active_style = "green" if active_workers < max_workers else "yellow"
        tbl.add_row(
            "Pegasus Active",
            f"[{active_style}]{active_workers:,} / {max_workers:,}[/{active_style}]",
        )
        tbl.add_row(
            "Pegasus Quality",
            f"{self._int_value(swarm, 'success'):,} ok / {self._int_value(swarm, 'failed'):,} fail",
        )
        last = swarm.get("last", {}) if isinstance(swarm.get("last"), dict) else {}
        if last:
            tbl.add_row("Pegasus Last", escape(str(last.get("status", "none"))))
        fail_open = self._int_value(shared, "binary_fail_open")
        if fail_open:
            tbl.add_row("Fail-open Skips", f"[yellow]{fail_open:,} large binary[/yellow]")

        mutations = 0
        for ev in t.get("mitm_recent_events", []):
            if ev.get("kind") == "mutation": mutations += 1
        tbl.add_row("Anti-Reject", f"[bold magenta]{mutations}[/bold magenta] hits")

        return Panel(tbl, title="Intelligence Layer", border_style="blue")

    def _acceleration_panel(self):
        k = self.khoj
        accel = k.get("acceleration", {}) or {}
        active = accel.get("runtime_active", {}) or {}
        host = accel.get("host", {}) or {}
        container = accel.get("container", {}) or {}
        runtime = accel.get("runtime", {}) or {}
        env = runtime.get("env", {}) or {}
        torch_info = runtime.get("torch", {}) or {}
        ov_info = runtime.get("openvino", {}) or {}

        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        phase = accel.get("phase", "unknown")
        mode = accel.get("mode", "auto")
        tbl.add_row("Mode", f"{escape(mode)} / {escape(phase)}")

        cuda_live = bool(active.get("cuda") or torch_info.get("cuda_runtime_ok"))
        cuda_visible = bool(torch_info.get("cuda_available"))
        cuda_exposed = bool(container.get("cuda_exposed", accel.get("cuda")))
        cuda_label = (
            "runtime active" if cuda_live
            else "runtime visible" if cuda_visible
            else "exposed" if cuda_exposed
            else "host" if host.get("cuda")
            else "off"
        )
        cuda_value = self._status_badge(cuda_live, cuda_label, cuda_label)
        if torch_info.get("device_name"):
            cuda_value += f" [dim]{escape(torch_info.get('device_name', ''))}[/dim]"
        elif accel.get("nvidia_name"):
            cuda_value += f" [dim]{escape(accel.get('nvidia_name', ''))}[/dim]"
        tbl.add_row("CUDA", cuda_value)

        torch_version = torch_info.get("version") or runtime.get("torch_error", "")
        tbl.add_row("Torch", escape(str(torch_version)[:46]) if torch_version else "[dim]--[/dim]")

        ov_devices = active.get("openvino_devices_visible") or ov_info.get("devices") or []
        ov_host = accel.get("openvino_host_devices") or []
        ov_env = env.get("OPENVINO_DEVICE", "")
        if ov_devices:
            ov_color = "green" if active.get("openvino_compile_ok", active.get("openvino")) else "yellow"
            ov_state = "compile ok" if active.get("openvino_compile_ok", active.get("openvino")) else "runtime visible"
            ov_value = f"[{ov_color}]{escape(ov_state)}: {escape(','.join(ov_devices))}[/{ov_color}]"
        elif container.get("openvino_exposed", accel.get("openvino")):
            ov_value = "[yellow]exposed[/yellow]"
        elif host.get("openvino"):
            ov_value = "[yellow]host visible[/yellow]"
        else:
            ov_value = "[dim]off[/dim]"
        requested_device = (ov_info.get("requested_device") or env.get("OPENVINO_DEVICE") or "").strip()
        if requested_device and requested_device.upper() != "AUTO":
            if ov_info.get("requested_device_supported") is False:
                ov_value += f" [yellow]requested {escape(requested_device)} unavailable[/yellow]"
            else:
                ov_value += f" [dim]req {escape(requested_device)}[/dim]"
        if ov_host:
            ov_value += f" [dim]host:{escape(','.join(ov_host))}[/dim]"
        tbl.add_row("OpenVINO", ov_value)
        if ov_env:
            tbl.add_row("OV Device", escape(ov_env))
        ov_request_error = ov_info.get("requested_device_error")
        if ov_request_error:
            tbl.add_row("OV Req Error", escape(str(ov_request_error)))

        tbl.add_row("NPU", self._status_badge(active.get("npu"), "runtime", "none"))
        myriad_count = int(accel.get("myriad_count") or 0)
        myriad = self._myriad_status(accel)
        if myriad["compile_ok"]:
            myriad_value = f"[green]compile ok x{myriad_count}[/green]"
        elif myriad["boot_failed"]:
            myriad_value = f"[red]boot failed x{myriad_count}[/red]"
        elif myriad["compile_failed"]:
            myriad_value = f"[red]compile failed x{myriad_count}[/red]"
        elif myriad["visible"]:
            myriad_value = f"[yellow]runtime visible x{myriad_count}[/yellow]"
        elif container.get("myriad_exposed", accel.get("myriad")):
            myriad_value = f"[yellow]exposed x{myriad_count}[/yellow]"
        elif host.get("myriad"):
            myriad_value = f"[yellow]host visible x{myriad_count}[/yellow]"
        else:
            myriad_value = "[dim]none[/dim]"
        err = self._first_error(myriad["errors"])
        if err:
            myriad_value += f" [dim]{escape(err)}[/dim]"
        tbl.add_row("Myriad", myriad_value)
        usb_label = "present" if active.get("usb_passthrough") else "missing"
        tbl.add_row("USB passthru", self._status_badge(active.get("usb_passthrough"), usb_label, usb_label))

        tbl.add_row("nvidia-smi", "[green]OK[/green]" if runtime.get("nvidia_smi") else "[dim]--[/dim]")
        tbl.add_row("Env", escape(",".join(sorted(env.keys()))[:54]) if env else "[dim]--[/dim]")
        return Panel(tbl, title="Khoj Acceleration", border_style="green" if cuda_live else "yellow")

    def _shield_panel(self):
        t = self.tel
        tbl = Table(expand=True, show_header=False, box=None, padding=(0, 1))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column()

        # LSP shield (language server shim) status
        shim_active = False
        shim_path = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64")
        if shim_path.exists():
            try:
                shim_bytes = shim_path.read_bytes()
                if b"language_server_linux_x64.real" in shim_bytes:
                    shim_active = True
            except Exception:
                shim_active = False
        tbl.add_row("LSP Shield", "[green]ACTIVE[/green]" if shim_active else "[dim]OFF[/dim]")
        if shim_active:
            tbl.add_row("LSP Mode", os.environ.get("HG_PROXY_MODE", "full"))

        # Routing
        api_url = self.windsurf_api_url()
        inf_url = None
        try:
            out = subprocess.check_output(
                "ps aux | grep language_server_linux | grep -v grep",
                shell=True, text=True, timeout=1
            )
            if "--inference_api_server_url" in out:
                parts = out.split()
                for i, part in enumerate(parts):
                    if part == "--inference_api_server_url" and i+1 < len(parts):
                        inf_url = parts[i+1].strip("'").strip('"')
        except:
            inf_url = None

        is_api_proxy = bool(api_url and ("proxy.windsurf.com" in api_url or "inferapi.windsurf.com" in api_url))
        is_inf_proxy = bool(inf_url and ("proxy.windsurf.com" in inf_url or "inferapi.windsurf.com" in inf_url))

        if is_api_proxy and is_inf_proxy:
            routing_label = "[green]FULL PROXY[/green]"
        elif api_url and "server.self-serve.windsurf.com" in api_url and is_inf_proxy:
            routing_label = "[cyan]SPLIT (intentional)[/cyan]"
        elif is_inf_proxy:
            routing_label = "[yellow]INFERENCE ONLY[/yellow]"
        else:
            routing_label = "[red]DIRECT[/red]"
        tbl.add_row("Editor Link", routing_label)
        if routing_label == "[cyan]SPLIT (intentional)[/cyan]":
            tbl.add_row("Routing Notes", "[dim]api direct via /etc/hosts, inference via proxy[/dim]")

        # OPSEC
        shuffler = "[green]ACTIVE[/green]" if t else "[dim]--[/dim]"
        tbl.add_row("Jitter/Entropy", shuffler)
        tbl.add_row("Redactor", "[green]WATERTIGHT[/green]" if t else "[dim]--[/dim]")

        # Binary Patch Check (v1.110.1 Multi-Point)
        bin_target = None
        for p in ["language_server_linux_x64.real", "language_server_linux_x64"]:
            full_p = Path(f"/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/{p}")
            if full_p.exists():
                bin_target = full_p
                break

        if bin_target:
            patched_points = 0
            try:
                with open(bin_target, "rb") as f:
                    for off in [0x818b87d, 0x818ba9d, 0x81973fd]:
                        f.seek(off); b = f.read(2)
                        if b in (b'\xeb\x2e', b'\x90\x90'):
                            patched_points += 1
                if patched_points == 3:
                    status = "[green]PATCHED[/green]"
                elif patched_points > 0:
                    status = f"[yellow]PARTIAL ({patched_points}/3)[/yellow]"
                else:
                    status = "[red]ORIGINAL[/red]"
            except Exception:
                status = "[red]READ ERR[/red]"
            tbl.add_row("Bin Patch", status)
        else:
            tbl.add_row("Bin Patch", "[red]NOT FOUND[/red]")

        # JS Patch Check
        ext_path = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js")
        if ext_path.exists():
            try:
                ext_bytes = ext_path.read_bytes()
                old_hits = sum(url in ext_bytes for url in JS_ORIGINAL_URLS)
                new_hits = sum(url in ext_bytes for url in JS_PATCHED_URLS)
                if old_hits == 0 and new_hits:
                    tbl.add_row("JS Patch", "[green]PATCHED[/green]")
                elif old_hits and new_hits:
                    tbl.add_row("JS Patch", f"[yellow]PARTIAL ({old_hits} old)[/yellow]")
                else:
                    tbl.add_row("JS Patch", "[red]ORIGINAL[/red]")
            except Exception:
                tbl.add_row("JS Patch", "[red]READ ERR[/red]")
        else:
            tbl.add_row("JS Patch", "[red]NOT FOUND[/red]")

        # Workbench Patch Check
        wb_path = Path("/usr/share/windsurf-next/resources/app/out/vs/workbench/workbench.desktop.main.js")
        if wb_path.exists():
            try:
                wb_bytes = wb_path.read_bytes()
                wb_integrity = WB_PATCHED_INTEGRITY in wb_bytes
                wb_original = WB_ORIGINAL_INTEGRITY in wb_bytes
                if wb_integrity and not wb_original:
                    tbl.add_row("Workbench", "[green]PATCHED[/green]")
                elif wb_integrity:
                    tbl.add_row("Workbench", "[yellow]PARTIAL[/yellow]")
                else:
                    tbl.add_row("Workbench", "[red]ORIGINAL[/red]")
            except Exception:
                tbl.add_row("Workbench", "[red]READ ERR[/red]")
        else:
            tbl.add_row("Workbench", "[red]NOT FOUND[/red]")

        # /etc/hosts Check
        try:
            hosts = Path("/etc/hosts").read_text()
            hosts_ok = "proxy.windsurf.com" in hosts and "inferapi.windsurf.com" in hosts
            tbl.add_row("DNS Redirect", "[green]ACTIVE[/green]" if hosts_ok else "[red]MISSING[/red]")
        except Exception:
            tbl.add_row("DNS Redirect", "[dim]--[/dim]")

        # iptables Check
        try:
            ipt_ok = subprocess.call(
                ["sudo", "-n", "iptables", "-t", "nat", "-C", "OUTPUT",
                 "-p", "tcp", "--dport", "50001", "-j", "REDIRECT", "--to-port", str(PROXY_PORT)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ) == 0
            tbl.add_row("iptables", f"[green]50001→{PROXY_PORT}[/green]" if ipt_ok else "[red]MISSING[/red]")
        except Exception:
            tbl.add_row("iptables", "[dim]--[/dim]")

        # Latency
        lat = self.tel.get("latency_ms", {})
        p50 = lat.get("p50", 0) or 0
        tbl.add_row("p50 Latency", f"{p50:.1f}ms")

        return Panel(tbl, title="Expert Shield Status", border_style="yellow")

    def _events_panel(self):
        events = self.tel.get("mitm_recent_events", []) or []
        tbl = Table(expand=True, box=None)
        tbl.add_column("Time", style="dim", no_wrap=True, width=10)
        tbl.add_column("Agent", no_wrap=True, width=12)
        tbl.add_column("Activity")
        colors = {
            "detect": "cyan", "upgrade": "yellow", "thinking": "blue",
            "ratelimit": "red", "khoj": "green", "mutation": "magenta"
        }
        for ev in list(reversed(events))[:10]:
            ts = datetime.fromtimestamp(ev.get("ts", 0)).strftime("%H:%M:%S")
            kind = ev.get("kind", "?")
            detail = ev.get("detail", "")
            agent = "ROUTER" if kind == "detect" else "OVERRIDE" if kind == "upgrade" else \
                    "REASONER" if kind == "thinking" else "KHOJ" if kind == "khoj" else \
                    "MUTATOR" if kind == "mutation" else "SYSTEM"
            tbl.add_row(ts, Text(agent, style=colors.get(kind, "white")), detail)
        return Panel(tbl, title="Pegasus Swarm Activity", border_style="red")

    def _thinking_panel(self):
        by_lvl = self.tel.get("mitm_thinking_by_level", {}) or {}
        total = sum(by_lvl.values()) or 1
        tbl = Table(expand=True, box=None)
        tbl.add_column("Reasoning Tier", no_wrap=True)
        tbl.add_column("Count", justify="right")
        tbl.add_column("Intensity", ratio=2)
        for key, label, color in THINKING_TIERS:
            n = int(by_lvl.get(key, 0))
            bar_len = int((n / total) * 20)
            bar = Text("█" * bar_len + "░" * (20 - bar_len), style=color)
            tbl.add_row(Text(label, style=f"bold {color}"), str(n), bar)
        return Panel(tbl, title="AI Reasoning Profile", border_style="magenta")

    def _controls_panel(self):
        tbl = Table(expand=True, box=None, padding=(0, 0))
        tbl.add_column("Key", style="bold cyan", no_wrap=True, width=3)
        tbl.add_column("Action", no_wrap=True)
        tbl.add_row("S", "Start All")
        tbl.add_row("X", "Stop All")
        tbl.add_row("T", "Start Proxy")
        tbl.add_row("Z", "Stop Proxy")
        tbl.add_row("P", "Deep Patch")
        tbl.add_row("R", "Repatch")
        tbl.add_row("U", "Unpatch")
        tbl.add_row("D", "Doctor")
        tbl.add_row("W", "Launch Editor")
        tbl.add_row("K", "Khoj Reindex")
        tbl.add_row("H", "HMI Dashboard")
        tbl.add_row("A", "Probe Accel")
        tbl.add_row("G", "Restart Accel")
        tbl.add_row("O", "Rotate Keys")
        tbl.add_row("C", "Clear Cache")
        tbl.add_row("Y", "Clear Control-Plane Cache")
        tbl.add_row("1", "Proxy cache-first")
        tbl.add_row("2", "Proxy cache-only")
        tbl.add_row("3", "Proxy confirm")
        tbl.add_row("4", "Proxy block")
        tbl.add_row("5", "Proxy local-only")
        tbl.add_row("L", "Intelligence Logs")
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
            elif "PROTOCOL EVENT" in line or "KHOJ_CONTEXT" in line:
                content.append(line + "\n", style="bold green")
            elif "PROACTIVE_TRIGGER" in line or "mutation" in line:
                content.append(line + "\n", style="bold magenta")
            else:
                content.append(line + "\n")

        footer = Text(
            "[1] proxy.log  [2] cascade.log  [3] khoj.log  [4] proxy_https.log  [5] khoj_accel.json  [B] Back",
            style="bold cyan", justify="center"
        )
        inner = Layout()
        inner.split_column(
            Layout(Panel(content, title=f"Intelligence Log: {self.log_name}", border_style="green"), ratio=9),
            Layout(Panel(footer, border_style="dim"), size=3),
        )
        return inner

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
            Layout(name="top", size=12),
            Layout(name="mid", size=14),
            Layout(name="bottom", size=12),
            Layout(name="footer", size=3),
        )

        root["header"].update(Panel(
            Text("HIGH-GRAVITY PEGASUS CONTROL PLANE v3.2", justify="center", style="bold cyan"),
            border_style="cyan",
        ))

        root["top"].split_row(
            Layout(self._proxy_panel(), ratio=3),
            Layout(self._intelligence_panel(), ratio=3),
            Layout(self._controls_panel(), ratio=2),
        )

        root["mid"].split_row(
            Layout(self._shield_panel(), ratio=1),
            Layout(self._thinking_panel(), ratio=1),
            Layout(self._acceleration_panel(), ratio=1),
        )

        # Bottom section: Swarm Events on left, Live Log on right
        root["bottom"].split_row(
            Layout(self._events_panel(), ratio=1),
            Layout(self._ebpf_panel(), ratio=1),
            Layout(Panel(self._mini_log_content(), title="Intelligence Stream", border_style="dim"), ratio=1),
        )

        root["footer"].update(Panel(
            Text(f"Status: {self.status_msg}    {datetime.now().strftime('%H:%M:%S')}", justify="center"),
            border_style="dim",
        ))
        return root

    def _mini_log_content(self):
        lines = self.read_log_tail("proxy.log", 10)
        content = Text()
        for line in lines:
            if "ERROR" in line or "FAIL" in line: style = "bold red"
            elif "WARNING" in line: style = "yellow"
            elif "PROTOCOL EVENT" in line: style = "bold green"
            elif "mutation" in line: style = "bold magenta"
            else: style = "dim"
            # Extract just the message after the log level for mini view
            msg = line.split("] ", 1)[-1] if "] " in line else line
            content.append(msg[:80] + "\n", style=style)
        return content

    def run(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        try:
            with Live(self.build_layout(), refresh_per_second=2, screen=True) as live:
                while True:
                    live.update(self.build_layout())
                    r, _, _ = select.select([sys.stdin], [], [], 0.2)
                    if not r: continue
                    c = sys.stdin.read(1).lower()

                    if self.view == "logs":
                        if c == "b" or c == "\x1b": self.view = "main"
                        elif c == "1": self.log_name = "proxy.log"
                        elif c == "2": self.log_name = "cascade_midway.log"
                        elif c == "3": self.log_name = "khoj.log"
                        elif c == "4": self.log_name = "proxy_https.log"
                        elif c == "5": self.log_name = "khoj_accel.json"
                        elif c == "q": break
                        continue

                    if c == "q": break
                    elif c == "s": self.run_cmd("System Start", "./hg.sh start")
                    elif c == "x": self.run_cmd("System Stop", "./hg.sh stop")
                    elif c == "t": self.run_cmd("Proxy Start", "./hg.sh proxy start cache-first")
                    elif c == "z": self.run_cmd("Proxy Stop", "./hg.sh proxy stop")
                    elif c == "p": self.run_cmd("Deep Patch", "./hg.sh patch")
                    elif c == "r": self.run_cmd("Repatch", "./hg.sh repatch")
                    elif c == "u": self.run_cmd("Unpatch", "./hg.sh unpatch")
                    elif c == "d":
                        live.stop()
                        subprocess.run(f"bash {REPO_ROOT}/hg.sh doctor", shell=True)
                        input("\nPress Enter to return to dashboard...")
                        live.start()
                    elif c == "w":
                        subprocess.Popen(
                            "nohup /usr/local/bin/hg-windsurf-next > /dev/null 2>&1 &",
                            shell=True,
                            start_new_session=True,
                            cwd=REPO_ROOT,
                        )
                        self.status_msg = "[green]Launching Editor...[/green]"
                    elif c == "h":
                        live.stop()
                        subprocess.run(
                            "bash ./hg.sh hmi-dashboard",
                            shell=True,
                            cwd=REPO_ROOT,
                        )
                        live.start()
                    elif c == "k": self.run_cmd("Khoj Reindex", "./hg.sh khoj reindex")
                    elif c == "a": self.run_cmd("Khoj Accel Probe", "./hg.sh khoj accel")
                    elif c == "g":
                        self.run_cmd(
                            "Khoj Accel Restart",
                            "HG_KHOJ_ACCEL=all HG_KHOJ_INSTALL_CUDA_TORCH=1 HG_KHOJ_CUDA_TORCH_VERSION=2.5.1+cu121 HG_KHOJ_INSTALL_OPENVINO=1 HG_KHOJ_RECREATE=1 ./hg.sh khoj start"
                        )
                    elif c == "l": self.view = "logs"; self.log_name = "proxy.log"
                    elif c == "o": self.action("rotate_keys")
                    elif c == "c": self.action("clear_cache")
                    elif c == "y": self.action("clear_control_plane_cache")
                    elif c == "1": self.restart_proxy_mode("cache-first")
                    elif c == "2": self.restart_proxy_mode("cache-only")
                    elif c == "3": self.restart_proxy_mode("confirm")
                    elif c == "4": self.restart_proxy_mode("block")
                    elif c == "5": self.restart_proxy_mode("local-only")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

if __name__ == "__main__":
    Dashboard().run()
