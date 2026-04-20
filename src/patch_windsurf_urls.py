#!/usr/bin/env python3
"""
Patch Windsurf to redirect ALL API URLs to HIGH-GRAVITY proxy
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SUDO_PASS = "1786"

ext_path = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js")

print(f"[*] Patching API URLs in: {ext_path}")

with open(ext_path, "r") as f:
    content = f.read()

# Backup
backup_path = ext_path.with_suffix(".js.original")
if not backup_path.exists():
    print(f"[*] Creating backup: {backup_path}")
    os.system(f"echo {SUDO_PASS} | sudo -S cp {ext_path} {backup_path}")

modified = False

# Patch 1: Hardcoded inference URL in config map
old_inference = 'INFERENCE_API_SERVER_URL,"https://inference.codeium.com"'
new_inference = 'INFERENCE_API_SERVER_URL,"http://shield.windsurf.com:9999"'

if old_inference in content:
    content = content.replace(old_inference, new_inference)
    print("[✓] Patched INFERENCE_API_SERVER_URL in config map")
    modified = True

# Patch 2: Hardcoded API server URL
old_api = 'DEFAULT_API_SERVER_URL="https://server.codeium.com"'
new_api = 'DEFAULT_API_SERVER_URL="http://shield.windsurf.com:9999"'

if old_api in content:
    content = content.replace(old_api, new_api)
    print("[✓] Patched DEFAULT_API_SERVER_URL")
    modified = True

# Patch 3: Register URL
old_register = 'DEFAULT_REGISTER_API_SERVER_URL="https://register.windsurf.com"'
new_register = 'DEFAULT_REGISTER_API_SERVER_URL="http://shield.windsurf.com:9999"'

if old_register in content:
    content = content.replace(old_register, new_register)
    print("[✓] Patched DEFAULT_REGISTER_API_SERVER_URL")
    modified = True

# Patch 4: EU/Fed routes
old_eu = '"https://eu.windsurf.com/_route/api_server"'
new_eu = '"http://shield.windsurf.com:9999"'

count = content.count(old_eu)
if count > 0:
    content = content.replace(old_eu, new_eu)
    print(f"[✓] Patched {count} EU API routes")
    modified = True

old_fed = '"https://windsurf.fedstart.com/_route/api_server"'
new_fed = '"http://shield.windsurf.com:9999"'

count = content.count(old_fed)
if count > 0:
    content = content.replace(old_fed, new_fed)
    print(f"[✓] Patched {count} Fed API routes")
    modified = True

if modified:
    # Write back
    temp_patch = Path(f"/tmp/extension.js.urls")
    with open(temp_patch, "w") as f:
        f.write(content)
    
    os.system(f"echo {SUDO_PASS} | sudo -S cp {temp_patch} {ext_path}")
    os.system(f"rm {temp_patch}")
    print(f"\n[✓] All API URLs redirected to shield.windsurf.com:9999")
    print(f"[!] RESTART WINDSURF for changes to take effect")
else:
    print("[-] No changes needed (already patched)")
