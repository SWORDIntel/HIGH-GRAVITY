#!/usr/bin/env python3
"""
Add HTTPS support to HIGH-GRAVITY proxy
Mimics Windsurf's cert by creating a self-signed cert and adding to system trust
"""
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
CERT_DIR = REPO_ROOT / "certs"
CERT_FILE = CERT_DIR / "proxy.crt"
KEY_FILE = CERT_DIR / "proxy.key"

# Domains to include in cert
DOMAINS = [
    "proxy.windsurf.com",
    "inferapi.windsurf.com",
    "server.codeium.com",
    "inference.codeium.com",
    "server.self-serve.windsurf.com",
    "eu.windsurf.com",
    "windsurf.fedstart.com",
    "register.windsurf.com",
    "unleash.codeium.com",
    "shield.windsurf.com",
]

def create_cert():
    """Generate self-signed certificate with all domains"""
    print("[*] Creating certificate directory...")
    CERT_DIR.mkdir(exist_ok=True)
    
    if CERT_FILE.exists() and KEY_FILE.exists():
        print("[*] Certificate already exists")
        return
    
    print("[*] Generating self-signed certificate...")
    
    # Build SAN (Subject Alternative Names) list
    san_list = ",".join([f"DNS:{domain}" for domain in DOMAINS])
    
    # Create OpenSSL config
    config = f"""
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = HIGH-GRAVITY Proxy

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = {san_list}
"""
    
    config_file = CERT_DIR / "openssl.cnf"
    with open(config_file, "w") as f:
        f.write(config)
    
    # Generate certificate
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", str(KEY_FILE),
        "-out", str(CERT_FILE),
        "-days", "365",
        "-nodes",
        "-config", str(config_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Error generating certificate: {result.stderr}")
        return False
    
    print(f"[✓] Certificate created: {CERT_FILE}")
    print(f"[✓] Private key created: {KEY_FILE}")
    
    # Clean up config
    config_file.unlink()
    
    return True

def install_cert_to_system():
    """Install certificate to system trust store"""
    print("\n[*] Installing certificate to system trust store...")
    
    # For Ubuntu/Debian
    system_cert_dir = Path("/usr/local/share/ca-certificates")
    system_cert_file = system_cert_dir / "high-gravity-proxy.crt"
    
    try:
        # Copy cert to system location
        subprocess.run([
            "sudo", "cp", str(CERT_FILE), str(system_cert_file)
        ], check=True)
        
        # Update CA certificates
        subprocess.run(["sudo", "update-ca-certificates"], check=True)
        
        print(f"[✓] Certificate installed to system trust store")
        print(f"    Location: {system_cert_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to install certificate: {e}")
        print("[!] You may need to install manually")
        return False

def update_hosts():
    """Add /etc/hosts entries for all domains"""
    print("\n[*] Updating /etc/hosts...")
    
    hosts_entries = "\n# HIGH-GRAVITY Windsurf/Codeium HTTPS redirects\n"
    for domain in DOMAINS:
        hosts_entries += f"127.0.0.1 {domain}\n"
    
    # Check if already present
    with open("/etc/hosts", "r") as f:
        current_hosts = f.read()
    
    if "HIGH-GRAVITY Windsurf/Codeium HTTPS redirects" in current_hosts:
        print("[*] /etc/hosts already configured")
        return True
    
    # Append to hosts file
    try:
        with open("/tmp/hosts_append", "w") as f:
            f.write(hosts_entries)
        
        subprocess.run([
            "sudo", "bash", "-c",
            "cat /tmp/hosts_append >> /etc/hosts"
        ], check=True)
        
        print("[✓] Updated /etc/hosts with domain redirects")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to update /etc/hosts: {e}")
        return False

def show_proxy_update_instructions():
    """Show how to update proxy.py"""
    print("\n" + "="*60)
    print("NEXT STEPS: Update proxy.py to use HTTPS")
    print("="*60)
    print()
    print("Add to proxy.py imports:")
    print("  import ssl")
    print()
    print("Update uvicorn.run() call:")
    print("  uvicorn.run(")
    print("      app,")
    print("      host='0.0.0.0',")
    print("      port=443,  # Changed from 9998")
    print(f"      ssl_keyfile='{KEY_FILE}',")
    print(f"      ssl_certfile='{CERT_FILE}',")
    print("      log_level='info'")
    print("  )")
    print()
    print("Or run both HTTP (9998) and HTTPS (443) simultaneously:")
    print("  # In separate threads or processes")
    print()
    print("Certificate files:")
    print(f"  Key:  {KEY_FILE}")
    print(f"  Cert: {CERT_FILE}")
    print()
    print("Domains covered:")
    for domain in DOMAINS:
        print(f"  - {domain}")
    print()
    print("="*60)

def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     HIGH-GRAVITY HTTPS Proxy Setup                        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    # Step 1: Create certificate
    if not create_cert():
        print("[!] Certificate creation failed")
        return 1
    
    # Step 2: Install to system trust
    install_cert_to_system()
    
    # Step 3: Update /etc/hosts
    update_hosts()
    
    # Step 4: Show next steps
    show_proxy_update_instructions()
    
    print("\n[✓] HTTPS setup complete!")
    print("\nTo test:")
    print(f"  openssl s_client -connect server.codeium.com:443 -CAfile {CERT_FILE}")
    print()
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
