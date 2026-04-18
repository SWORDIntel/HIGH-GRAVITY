#!/usr/bin/env python3
import os
import socket
import sys

def run_diagnostics():
    print("--- Windsurf Connection Debugger ---")
    
    # 1. DNS Resolution
    try:
        ip = socket.gethostbyname("shield.windsurf.com")
        print(f"[+] DNS check: shield.windsurf.com resolves to {ip}")
        if ip != "127.0.0.1":
            print("[!] WARNING: DNS resolves to non-local IP.")
    except:
        print("[!] ERROR: shield.windsurf.com not found. Did you update /etc/hosts?")

    # 2. Proxy Port
    port = 9999
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)) == 0:
            print(f"[+] Proxy Server: Responding on {port}")
        else:
            print("[!] ERROR: Proxy Server not responding on port {port}. Run 'hg.py' or start proxy.")

    # 3. Environment Audit
    vars = ["HG_PROXY_PORT", "OPENAI_BASE_URL"]
    for v in vars:
        val = os.environ.get(v)
        print(f"[*] {v}: {val if val else 'NOT SET'}")

if __name__ == "__main__":
    run_diagnostics()
