#!/usr/bin/env python3
"""
Passive Windsurf Traffic Sniffer — tcpdump-based
Captures packets without modifying traffic (no redirects, no /etc/hosts).

Run with sudo:
    echo 1786 | sudo -S python3 tools/sniff_passive.py

Logs to: logs/cascade_passive.log
"""
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Known Windsurf IPs
TARGET_IPS = ["34.49.14.144", "192.34.20.166", "35.223.238.178"]

def run_tcpdump():
    """Run tcpdump to capture traffic to Windsurf IPs"""
    pcap_file = LOG_DIR / "cascade_passive.pcap"
    log_file = LOG_DIR / "cascade_passive.log"

    # Build tcpdump filter
    ip_filter = " or ".join([f"host {ip}" for ip in TARGET_IPS])

    cmd = [
        "tcpdump",
        "-i", "any",  # All interfaces
        "-n",  # Don't resolve names
        "-s", "0",  # Capture full packets
        "-w", str(pcap_file),
        f"({ip_filter}) and port 443"
    ]

    print(f"  [*] Capturing to: {pcap_file}")
    print(f"  [*] Logging to: {log_file}")
    print(f"  [*] Target IPs: {', '.join(TARGET_IPS)}")
    print(f"  [*] Press Ctrl+C to stop")
    print()

    # Start tcpdump
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Monitor and log
    with open(log_file, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"Passive capture started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Target IPs: {', '.join(TARGET_IPS)}\n")
        f.write(f"{'='*80}\n\n")
        f.flush()

        try:
            while True:
                line = proc.stderr.readline()
                if not line:
                    break
                if "packets captured" in line or "packet" in line.lower():
                    # Log packet counts
                    f.write(f"{datetime.now().strftime('%H:%M:%S')} {line.strip()}\n")
                    f.flush()
                    print(f"  {line.strip()}")
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n  [*] Stopping capture...")
            proc.terminate()
            proc.wait()

    print(f"\n  [*] Capture saved to {pcap_file}")
    print(f"  [*] Analyze with: tcpdump -r {pcap_file} -nn -A")

def analyze_pcap():
    """Analyze captured pcap file"""
    pcap = LOG_DIR / "cascade_passive.pcap"
    if not pcap.exists():
        print(f"  No pcap file at {pcap}")
        return

    print(f"\n  Analyzing {pcap}...")
    print(f"  {'─'*80}")

    # Basic stats
    cmd = ["tcpdump", "-r", str(pcap), "-nn", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    lines = result.stdout.splitlines()

    # Count connections
    connections = {}
    for line in lines:
        if "IP" in line and "443" in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == ">" and i+1 < len(parts):
                    dst = parts[i+1]
                    if ":" in dst:
                        dst = dst.split(":")[0]
                    connections[dst] = connections.get(dst, 0) + 1
                    break

    print(f"  Connections by destination:")
    for ip, count in sorted(connections.items(), key=lambda x: -x[1]):
        print(f"    {ip}: {count} packets")

    # Show sample packets
    print(f"\n  Sample packets (first 10):")
    cmd = ["tcpdump", "-r", str(pcap), "-nn", "-c", "10"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("ERROR: Must run as root (tcpdump needs privileges)")
        print("  echo 1786 | sudo -S python3 tools/sniff_passive.py")
        sys.exit(1)

    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │    PASSIVE WINDSURF TRAFFIC SNIFFER         │")
    print("  │    tcpdump-based, no traffic modification   │")
    print("  └─────────────────────────────────────────────┘")
    print()

    if len(sys.argv) > 1 and sys.argv[1] == "--analyze":
        analyze_pcap()
    else:
        run_tcpdump()
