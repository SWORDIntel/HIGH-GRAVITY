#!/usr/bin/env python3
"""
Direct binary patcher for Windsurf language server.
Replaces hardcoded API URLs with HIGH-GRAVITY proxy URLs.

IMPORTANT: Go binaries store strings as pointer+length.
Replacements MUST be exactly same length as originals.
"""
import os
import sys
import shutil
import hashlib
from pathlib import Path

SUDO_PASS = "1786"

BINARY_PATH = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64")
BACKUP_PATH = BINARY_PATH.with_suffix(".original")

# URL replacements (MUST be same length as original)
# Original → Replacement
REPLACEMENTS = [
    # 26 chars each
    (b"https://server.codeium.com", b"http://127.0.0.1:9999/aaaa"),
    # 29 chars each
    (b"https://inference.codeium.com", b"http://127.0.0.1:9999/aaaaaaa"),
]

# Colors
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'


def print_banner():
    print(f"{BLUE}╔════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BLUE}║     Windsurf Language Server Binary Patcher              ║{NC}")
    print(f"{BLUE}╚════════════════════════════════════════════════════════════╝{NC}")
    print()


def validate_replacements():
    """Ensure all replacements are same length as originals"""
    for old, new in REPLACEMENTS:
        if len(old) != len(new):
            print(f"{RED}[!] Length mismatch: {old!r} ({len(old)}) vs {new!r} ({len(new)}){NC}")
            return False
    return True


def create_backup():
    """Create backup of original binary"""
    if BACKUP_PATH.exists():
        print(f"{YELLOW}[*] Backup already exists: {BACKUP_PATH}{NC}")
        # Verify backup matches current (before patching)
        return True
    
    print(f"{BLUE}[*] Creating backup...{NC}")
    result = os.system(f"echo {SUDO_PASS} | sudo -S cp {BINARY_PATH} {BACKUP_PATH}")
    if result == 0:
        print(f"{GREEN}[✓] Backup created: {BACKUP_PATH}{NC}")
        return True
    else:
        print(f"{RED}[!] Failed to create backup{NC}")
        return False


def compute_hash(path):
    """Compute SHA256 of file"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def patch_binary():
    """Apply URL replacements to binary"""
    print(f"{BLUE}[*] Reading binary...{NC}")
    with open(BINARY_PATH, "rb") as f:
        content = f.read()
    
    original_hash = compute_hash(BINARY_PATH)
    print(f"    Original size: {len(content):,} bytes")
    print(f"    Original hash: {original_hash}")
    print()
    
    modified = False
    for old, new in REPLACEMENTS:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            print(f"{GREEN}[✓]{NC} Replaced {count}x: {old.decode()} → {new.decode()}")
            modified = True
        else:
            # Check if already patched
            if new in content:
                print(f"{YELLOW}[-]{NC} Already patched: {new.decode()}")
            else:
                print(f"{RED}[!]{NC} Not found: {old.decode()}")
    
    if not modified:
        # Check if already patched
        already_patched = any(new in content for _, new in REPLACEMENTS)
        if already_patched:
            print(f"\n{YELLOW}[*] Binary already patched{NC}")
            return True
        else:
            print(f"\n{RED}[!] No changes made{NC}")
            return False
    
    # Write patched binary via sudo
    print(f"\n{BLUE}[*] Writing patched binary...{NC}")
    temp_path = Path(f"/tmp/language_server_patched_{os.getpid()}")
    with open(temp_path, "wb") as f:
        f.write(content)
    
    # Preserve executable permissions
    result = os.system(f"echo {SUDO_PASS} | sudo -S cp {temp_path} {BINARY_PATH}")
    os.system(f"echo {SUDO_PASS} | sudo -S chmod +x {BINARY_PATH}")
    temp_path.unlink()
    
    if result == 0:
        new_hash = compute_hash(BINARY_PATH)
        print(f"{GREEN}[✓] Binary patched successfully{NC}")
        print(f"    New hash: {new_hash}")
        return True
    else:
        print(f"{RED}[!] Failed to write patched binary{NC}")
        return False


def verify_patch():
    """Verify patches are present in binary"""
    print(f"\n{BLUE}[*] Verifying patches...{NC}")
    with open(BINARY_PATH, "rb") as f:
        content = f.read()
    
    all_ok = True
    for old, new in REPLACEMENTS:
        if new in content:
            count = content.count(new)
            print(f"  {GREEN}✓{NC} Found {count}x: {new.decode()}")
        elif old in content:
            print(f"  {RED}✗{NC} Still has original: {old.decode()}")
            all_ok = False
        else:
            print(f"  {YELLOW}?{NC} Neither found: {old.decode()}")
    
    return all_ok


def restore_backup():
    """Restore from backup"""
    if not BACKUP_PATH.exists():
        print(f"{RED}[!] No backup found at {BACKUP_PATH}{NC}")
        return False
    
    print(f"{BLUE}[*] Restoring from backup...{NC}")
    result = os.system(f"echo {SUDO_PASS} | sudo -S cp {BACKUP_PATH} {BINARY_PATH}")
    os.system(f"echo {SUDO_PASS} | sudo -S chmod +x {BINARY_PATH}")
    
    if result == 0:
        print(f"{GREEN}[✓] Restored from backup{NC}")
        return True
    else:
        print(f"{RED}[!] Restore failed{NC}")
        return False


def main():
    print_banner()
    
    # Parse args
    if len(sys.argv) > 1:
        if sys.argv[1] == "--verify":
            return 0 if verify_patch() else 1
        elif sys.argv[1] == "--restore":
            return 0 if restore_backup() else 1
        elif sys.argv[1] in ("-h", "--help"):
            print("Usage:")
            print(f"  {sys.argv[0]}           # Patch binary (with backup)")
            print(f"  {sys.argv[0]} --verify  # Verify patches")
            print(f"  {sys.argv[0]} --restore # Restore from backup")
            return 0
    
    # Check binary exists
    if not BINARY_PATH.exists():
        print(f"{RED}[!] Binary not found: {BINARY_PATH}{NC}")
        return 1
    
    # Validate replacements
    if not validate_replacements():
        return 1
    
    # Create backup
    if not create_backup():
        return 1
    
    # Patch binary
    if not patch_binary():
        return 1
    
    # Verify
    if not verify_patch():
        print(f"\n{YELLOW}[!] Verification had issues{NC}")
        return 1
    
    print(f"\n{GREEN}╔════════════════════════════════════════════════════════════╗{NC}")
    print(f"{GREEN}║     ✓ Binary patched successfully!                         ║{NC}")
    print(f"{GREEN}╚════════════════════════════════════════════════════════════╝{NC}")
    print()
    print("URLs redirected:")
    print(f"  https://server.codeium.com    → http://127.0.0.1:9999/aaaa")
    print(f"  https://inference.codeium.com → http://127.0.0.1:9999/aaaaaaa")
    print()
    print(f"Backup: {BACKUP_PATH}")
    print()
    print(f"{YELLOW}[!] Restart Windsurf for changes to take effect:{NC}")
    print(f"    pkill -f windsurf && /usr/share/windsurf-next/windsurf-next &")
    print()
    print("To restore original binary:")
    print(f"    python3 {sys.argv[0]} --restore")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
