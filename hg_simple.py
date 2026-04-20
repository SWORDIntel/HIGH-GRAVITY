#!/usr/bin/env python3
"""
HIGH-GRAVITY Simple Dashboard
Lightweight monitoring with working hotkeys
"""
import sys
import time
import requests
from datetime import datetime

PROXY_URL = "http://127.0.0.1:9999"

def clear_screen():
    print("\033[2J\033[H", end="")

def get_telemetry():
    try:
        r = requests.get(f"{PROXY_URL}/hg/telemetry", timeout=1)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

def get_khoj_status():
    try:
        r = requests.get(f"{PROXY_URL}/hg/khoj/status", timeout=1)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

def display_status():
    clear_screen()
    tel = get_telemetry()
    khoj = get_khoj_status()
    
    print("╔════════════════════════════════════════════════════════════╗")
    print("║          HIGH-GRAVITY Dashboard (Simple Mode)             ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    # Proxy status
    print("📡 PROXY STATUS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if tel:
        print(f"  Status: ✓ RUNNING")
        print(f"  Cache hits: {tel.get('cache_hits', 0)}")
        print(f"  Active keys: {tel.get('active_keys', 0)}")
        print(f"  Total requests: {tel.get('total_requests', 0)}")
    else:
        print(f"  Status: ✗ OFFLINE")
    print()
    
    # Khoj status
    print("🔍 KHOJ STATUS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if khoj.get('enabled'):
        print(f"  Status: ✓ ENABLED")
        print(f"  URL: {khoj.get('base_url', 'N/A')}")
        print(f"  Searches: {khoj.get('search_count', 0)}")
        print(f"  Injections: {khoj.get('injection_count', 0)}")
    else:
        print(f"  Status: ○ DISABLED")
    print()
    
    # MITM status
    print("🎯 MITM STATUS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        with open("logs/cascade_midway.log", "r") as f:
            lines = f.readlines()
            events = len([l for l in lines if "PROTOCOL EVENT" in l])
            print(f"  Events captured: {events}")
            if lines:
                print(f"  Last event: {lines[-1][:60]}...")
    except:
        print(f"  Events captured: 0")
    print()
    
    # Controls
    print("⌨️  CONTROLS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  [R] Refresh now")
    print("  [L] View proxy log")
    print("  [M] View MITM log")
    print("  [K] View Khoj log")
    print("  [S] System status")
    print("  [Q] Quit")
    print()
    print(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
    print()
    print("Press key + ENTER: ", end="", flush=True)

def view_log(logfile):
    clear_screen()
    print(f"╔════════════════════════════════════════════════════════════╗")
    print(f"║  {logfile:^58}  ║")
    print(f"╚════════════════════════════════════════════════════════════╝")
    print()
    try:
        with open(f"logs/{logfile}", "r") as f:
            lines = f.readlines()
            for line in lines[-50:]:
                print(line.rstrip())
    except Exception as e:
        print(f"Error reading log: {e}")
    print()
    input("Press ENTER to return...")

def system_status():
    clear_screen()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║              System Status                                 ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    import subprocess
    
    # Check proxy
    result = subprocess.run(["lsof", "-i", ":9999"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Proxy running on port 9999")
    else:
        print("✗ Proxy not running")
    
    # Check Khoj
    result = subprocess.run(["lsof", "-i", ":42110"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Khoj running on port 42110")
    else:
        print("○ Khoj not running")
    
    # Check Windsurf
    result = subprocess.run(["pgrep", "-f", "windsurf"], capture_output=True, text=True)
    if result.stdout.strip():
        print("✓ Windsurf running")
        # Check if connected to proxy
        result = subprocess.run(
            ["lsof", "-i", "-n", "-P"],
            capture_output=True,
            text=True
        )
        if "windsurf" in result.stdout and "127.0.0.1:9999" in result.stdout:
            print("  ✓ Connected to proxy (127.0.0.1:9999)")
        else:
            print("  ⚠ Not connected to proxy")
    else:
        print("○ Windsurf not running")
    
    print()
    input("Press ENTER to return...")

def main():
    print("Starting HIGH-GRAVITY Simple Dashboard...")
    print("(Use Ctrl+C to quit)")
    time.sleep(1)
    
    while True:
        display_status()
        try:
            choice = input().strip().lower()
            if choice == 'q':
                print("\nGoodbye!")
                break
            elif choice == 'r':
                continue  # Refresh
            elif choice == 'l':
                view_log("proxy.log")
            elif choice == 'm':
                view_log("cascade_midway.log")
            elif choice == 'k':
                view_log("khoj.log")
            elif choice == 's':
                system_status()
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
