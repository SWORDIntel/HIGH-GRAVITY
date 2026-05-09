#!/usr/bin/env python3
"""
HIGH-GRAVITY Unified Windsurf Patcher
Patches all three layers in one pass:
  1. Language server binary  (URL replace + domain-validation NOP)
  2. extension.js URLs        (hardcoded constants + config map)
  3. extension.js JS logic    (getApiServerUrlFromContext override etc.)

All traffic is redirected to:
  https://proxy.windsurf.com    (API / gRPC)
  https://inferapi.windsurf.com (inference)

Add to /etc/hosts:
  127.0.0.1  proxy.windsurf.com
  127.0.0.1  inferapi.windsurf.com

Then start the proxy in HTTPS mode:
  sudo python3 src/proxy.py --https
"""
import os
import sys
import hashlib
import argparse
from pathlib import Path
from typing import Optional, Tuple, List

SUDO_PASS = "1786"

# Resolved dynamically at runtime; defaults kept for backward compatibility.
# The real patch target is the ELF binary. The small language_server_linux_x64
# shell wrapper is a launcher shim and should not be treated as the binary.
DEFAULT_BINARY_PATH = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64.real")
DEFAULT_EXT_PATH = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js")
BINARY_PATH: Path = DEFAULT_BINARY_PATH
EXT_PATH: Path = DEFAULT_EXT_PATH

PROXY_URL   = "https://proxy.windsurf.com"
INFER_URL   = "https://inferapi.windsurf.com"

GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BLUE   = '\033[0;34m'
NC     = '\033[0m'

# ── Binary patches ────────────────────────────────────────────────────────────
# URL replacements: MUST be exactly same byte length as originals (Go ptr+len).
# Each tuple is (original, replacement). Legacy intermediate values are also
# listed as sources so re-patching an already-patched binary upgrades cleanly.
BINARY_URL_REPLACEMENTS = [
    # 26-byte slot
    (b"https://server.codeium.com",    b"https://proxy.windsurf.com"),
    (b"https://xxxxx.windsurf.com",    b"https://proxy.windsurf.com"),   # legacy intermediate
    # 29-byte slot
    (b"https://inference.codeium.com", b"https://inferapi.windsurf.com"),
    (b"https://xxxxxxxx.windsurf.com", b"https://inferapi.windsurf.com"), # legacy intermediate
]

# Raw byte patches: NOP the domain validation branch (fcn.0818ef40 @ file offset).
# RE finding: JE at 0x818b87d (previously 0x818e12d) jumps to error path if host not *.codeium.com or *.windsurf.com.
# NOP it so any URL passes. (r2 VA = file_offset + 0x1000 for this PIE binary.)
BINARY_BYTE_PATCHES = [
    (
        0x818b87d,
        bytes([0x74, 0x2E]),  # JE +0x2e → error path
        bytes([0x90, 0x90]),  # NOP NOP  → always passes
        "NOP domain validation branch #1",
    ),
    (
        0x818ba9d,
        bytes([0x74, 0x2E]),
        bytes([0x90, 0x90]),
        "NOP domain validation branch #2",
    ),
    (
        0x81973fd,
        bytes([0x74, 0x2E]),
        bytes([0x90, 0x90]),
        "NOP domain validation branch #3",
    ),
]

# ── JS URL constant patches ───────────────────────────────────────────────────
JS_URL_REPLACEMENTS = [
    # Config map constants
    (f'INFERENCE_API_SERVER_URL,"https://inference.codeium.com"',
     f'INFERENCE_API_SERVER_URL,"{INFER_URL}"'),
    (f'DEFAULT_API_SERVER_URL="https://server.codeium.com"',
     f'DEFAULT_API_SERVER_URL="{PROXY_URL}"'),
    # Route URLs (variable length — string replace safe in JS)
    ('"https://eu.windsurf.com/_route/api_server"',      f'"{PROXY_URL}"'),
    ('"https://windsurf.fedstart.com/_route/api_server"', f'"{PROXY_URL}"'),
    ('"https://server.self-serve.windsurf.com"', f'"{PROXY_URL}"'),
    (f'DEFAULT_REGISTER_API_SERVER_URL="https://register.windsurf.com"',
     f'DEFAULT_REGISTER_API_SERVER_URL="{PROXY_URL}"'),
    # Unleash feature flags
    ('url:"https://unleash.codeium.com/api/"',
     f'url:"{PROXY_URL}/unleash/"'),
]

# High-level MITM event logger and optimizer
JS_MIDWAY_LOG = Path("/home/john/HIGH-GRAVITY/logs/cascade_midway.log")
JS_OPTIMIZER_CODE = f"""
globalThis.HG_CACHE = globalThis.HG_CACHE || new Set();
globalThis.HG_OPT = (items, config) => {{
    try {{
        const logData = {{
            timestamp: new Date().toISOString(),
            model: config?.requestedModelUid,
            itemCount: items?.length,
            metadata: config?.metadata
        }};
        require("fs").appendFileSync("{JS_MIDWAY_LOG}", "\\n--- PROTOCOL EVENT ---\\n" + JSON.stringify(logData, null, 2) + "\\n");
    }} catch(e) {{}}
    if (!Array.isArray(items)) return items;
    return items.map(item => {{
        if (item.chunk?.case === "text") {{
            const val = item.chunk.value;
            const hash = val.substring(0, 200);
            if (globalThis.HG_CACHE.has(hash)) {{
                item.chunk.value = `[HG:CACHED] ${{val.substring(0, 30)}}`;
                return item;
            }}
            globalThis.HG_CACHE.add(hash);
        }}
        return item;
    }});
}};
"""

# ── JS function override patches ──────────────────────────────────────────────
JS_FUNC_PATCHES = [
    ('"use strict";', '"use strict";' + JS_OPTIMIZER_CODE, "Inject HG_OPT global"),
    ("items:e,cascadeConfig", "items:globalThis.HG_OPT(e,t),cascadeConfig", "Wrap send call (e,t)"),
    ("items:g,cascadeConfig", "items:globalThis.HG_OPT(g,t),cascadeConfig", "Wrap send call (g,t)"),
]


def sha256_short(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def sudo_cp(src: str, dst: str, remove_dest: bool = False):
    flag = "--remove-destination " if remove_dest else ""
    return os.system(f"echo {SUDO_PASS} | sudo -S cp {flag}{src} {dst}") == 0


def sudo_chmod(path: str, mode: str = "+x"):
    os.system(f"echo {SUDO_PASS} | sudo -S chmod {mode} {path}")


def resolve_windsurf_paths() -> Tuple[Optional[Path], Optional[Path]]:
    """Discover current Windsurf install paths for LS binary and extension.js."""
    candidates: List[Path] = [
        Path("/usr/share/windsurf-next"),
        Path("/usr/share/windsurf"),
        Path("/opt/windsurf-next"),
        Path("/opt/windsurf"),
    ]

    bins_real: List[Path] = []
    bins_wrapper: List[Path] = []
    exts: List[Path] = []
    for root in candidates:
        if not root.exists():
            continue
        bins_real.extend(root.glob("**/extensions/windsurf/bin/language_server_linux_x64.real"))
        bins_wrapper.extend(root.glob("**/extensions/windsurf/bin/language_server_linux_x64"))
        exts.extend(root.glob("**/extensions/windsurf/dist/extension.js"))

    bin_path = bins_real[0] if bins_real else (bins_wrapper[0] if bins_wrapper else None)
    ext_path = exts[0] if exts else None
    return bin_path, ext_path


def preflight_check(enable_auth_patch: bool = False) -> bool:
    """Validate that current build is patchable without modifying files."""
    print(f"\n{BLUE}Preflight check (no changes){NC}")
    ok = True

    if not BINARY_PATH.exists():
        print(f"  {RED}[✗] Binary path not found: {BINARY_PATH}{NC}")
        ok = False
    else:
        b = BINARY_PATH.read_bytes()
        if not any(src in b or dst in b for src, dst in BINARY_URL_REPLACEMENTS):
            print(f"  {RED}[✗] Binary URL signatures not found (likely new build layout).{NC}")
            ok = False
        else:
            print(f"  {GREEN}[✓]{NC} Binary URL signatures detected")
        for off, old, new, desc in BINARY_BYTE_PATCHES:
            actual = b[off:off + len(old)] if len(b) >= off + len(old) else b""
            if actual in (old, new):
                print(f"  {GREEN}[✓]{NC} Binary byte patch signature detected ({desc})")
            else:
                print(f"  {RED}[✗] Binary byte signature mismatch @ {hex(off)} ({desc}){NC}")
                ok = False

    if not EXT_PATH.exists():
        print(f"  {RED}[✗] extension.js path not found: {EXT_PATH}{NC}")
        ok = False
    else:
        text = EXT_PATH.read_text(errors="replace")
        url_rules = JS_URL_REPLACEMENTS
        missing = 0
        for old, new in url_rules:
            if old not in text and new not in text:
                missing += 1
        if missing == len(url_rules):
            print(f"  {RED}[✗] No expected JS URL markers found (likely new minified layout).{NC}")
            ok = False
        else:
            print(f"  {GREEN}[✓]{NC} JS URL markers detected")

    if ok:
        print(f"\n{GREEN}Preflight OK: patch targets look compatible.{NC}")
    else:
        print(f"\n{RED}Preflight FAILED: do not patch until signatures are updated.{NC}")
    return ok


# Strings that must be absent from a clean binary/JS backup.
# If any are present the backup was taken from an already-patched file.
_PATCHED_MARKERS_BINARY = [b"https://proxy.windsurf.com", b"https://inferapi.windsurf.com",
                            b"https://xxxxx.windsurf.com", b"https://xxxxxxxx.windsurf.com"]
_PATCHED_MARKERS_JS     = ["https://proxy.windsurf.com", "https://inferapi.windsurf.com",
                            "https://xxxxx.windsurf.com", "https://xxxxxxxx.windsurf.com",
                            "shield.windsurf.com"]


def _is_clean_binary(path: Path) -> bool:
    data = path.read_bytes()
    return not any(m in data for m in _PATCHED_MARKERS_BINARY)


def _is_clean_js(path: Path) -> bool:
    text = path.read_text(errors="replace")
    return not any(m in text for m in _PATCHED_MARKERS_JS)


def ensure_clean_backup(path: Path, is_binary: bool = True) -> bool:
    """
    Guarantee a clean (unpatched) .original backup exists.
    - If .original is missing: take it now (only if the live file is also clean).
    - If .original exists but is tainted: rename it .original.tainted and refuse.
    - If .original exists and is clean: nothing to do.
    Returns True only when a clean backup is confirmed present.
    """
    bak = Path(str(path) + ".original")
    compat_bak = None
    if is_binary and str(path).endswith(".real"):
        compat_bak = Path(str(path).removesuffix(".real") + ".original")
    is_clean = _is_clean_binary if is_binary else _is_clean_js

    if bak.exists():
        if is_clean(bak):
            print(f"  {GREEN}[✓] Clean backup verified: {bak.name}{NC}")
            return True
        else:
            tainted = Path(str(bak) + ".tainted")
            print(f"  {YELLOW}[!] Backup is tainted (taken from patched file).{NC}")
            print(f"  {YELLOW}    Saving as {tainted.name} — cannot use for restore.{NC}")
            if sudo_cp(str(bak), str(tainted)):
                os.system(f"echo {SUDO_PASS} | sudo -S rm -f {bak}")
            # Fall through: try to grab a clean copy from the live file
    elif compat_bak and compat_bak.exists():
        if is_clean(compat_bak):
            print(f"  {GREEN}[✓] Reusing compatible clean backup: {compat_bak.name}{NC}")
            if sudo_cp(str(compat_bak), str(bak)):
                return True
            print(f"  {RED}[!] Failed to seed backup from {compat_bak.name}{NC}")
            return False
        else:
            print(f"  {YELLOW}[!] Compatible backup exists but is tainted: {compat_bak.name}{NC}")
            # Fall through: try to grab a clean copy from the live file
    else:
        print(f"  {BLUE}[*] No backup found for {path.name}{NC}")

    # Attempt to create backup from live file — only if it is clean
    if not path.exists():
        print(f"  {RED}[!] Source not found: {path}{NC}")
        return False

    if is_clean(path):
        print(f"  {BLUE}[*] Live file is clean — taking backup now...{NC}")
        if sudo_cp(str(path), str(bak)):
            print(f"  {GREEN}[✓] Backup created: {bak}{NC}")
            return True
        print(f"  {RED}[!] Backup write failed{NC}")
        return False
    else:
        print(f"  {RED}[!] Live file is already patched and no clean backup exists.{NC}")
        print(f"  {RED}    Cannot proceed — restore the original file manually.{NC}")
        print(f"  {RED}    Binary backup from Windsurf update/reinstall required.{NC}")
        return False


# ── Binary patching ───────────────────────────────────────────────────────────

def patch_binary(verify_only: bool = False) -> bool:
    print(f"\n{BLUE}{'Verifying' if verify_only else 'Patching'} binary: {BINARY_PATH.name}{NC}")

    if not BINARY_PATH.exists():
        print(f"  {RED}[!] Not found: {BINARY_PATH}{NC}")
        return False

    with open(BINARY_PATH, "rb") as f:
        data = bytearray(f.read())

    if not verify_only:
        if not ensure_clean_backup(BINARY_PATH, is_binary=True):
            return False
        print(f"  Original hash: {sha256_short(BINARY_PATH)}")

    ok = True

    # URL replacements — deduplicate by target slot (repl value) to avoid double-reporting
    seen_repls: set = set()
    for orig, repl in BINARY_URL_REPLACEMENTS:
        assert len(orig) == len(repl), f"Length mismatch: {orig!r}"
        data_bytes = bytes(data)
        if repl in data_bytes:
            if repl not in seen_repls:
                print(f"  {GREEN}[✓]{NC} {'Present' if verify_only else 'Already patched'}: {repl.decode()}")
                seen_repls.add(repl)
        elif orig in data_bytes:
            if verify_only:
                print(f"  {RED}[✗] Still original: {orig.decode()}{NC}")
                ok = False
            else:
                data = bytearray(data_bytes.replace(orig, repl))
                print(f"  {GREEN}[✓]{NC} {orig.decode()} → {repl.decode()}")
                seen_repls.add(repl)
        # else: this is a legacy source that is no longer present — silently skip

    # Verify canonical repls are all present after patching
    canonical_repls = list(dict.fromkeys(r for _, r in BINARY_URL_REPLACEMENTS))
    for repl in canonical_repls:
        if repl not in seen_repls and repl not in bytes(data):
            print(f"  {RED}[!] Slot missing entirely: {repl.decode()}{NC}")
            ok = False

    # Byte patches
    for foff, old, new, desc in BINARY_BYTE_PATCHES:
        actual = bytes(data[foff:foff + len(old)])
        if actual == old:
            if verify_only:
                print(f"  {RED}[✗] Byte patch not applied @ {hex(foff)}: {desc}{NC}")
                ok = False
            else:
                data[foff:foff + len(new)] = new
                print(f"  {GREEN}[✓]{NC} Byte patch @ {hex(foff)}: {old.hex()} → {new.hex()}  ({desc})")
        elif actual == new:
            print(f"  {GREEN}[✓]{NC} Byte patch already applied @ {hex(foff)}  ({desc})")
        else:
            print(f"  {RED}[!] Byte mismatch @ {hex(foff)}: got {actual.hex()}, expected {old.hex()}{NC}")
            ok = False

    if verify_only or not ok:
        return ok

    # Write — use --remove-destination to replace inode (bypasses 'Text file busy')
    tmp = Path(f"/tmp/ls_patched_{os.getpid()}")
    tmp.write_bytes(bytes(data))
    if sudo_cp(str(tmp), str(BINARY_PATH), remove_dest=True):
        sudo_chmod(str(BINARY_PATH))
        tmp.unlink(missing_ok=True)
        print(f"  {GREEN}[✓] Written. New hash: {sha256_short(BINARY_PATH)}{NC}")
        return True
    tmp.unlink(missing_ok=True)
    print(f"  {RED}[!] Write failed{NC}")
    return False


def restore_binary() -> bool:
    bak = Path(str(BINARY_PATH) + ".original")
    compat_bak = None
    if str(BINARY_PATH).endswith(".real"):
        compat_bak = Path(str(BINARY_PATH).removesuffix(".real") + ".original")
    if not bak.exists():
        if compat_bak and compat_bak.exists():
            bak = compat_bak
        else:
            print(f"  {RED}[!] No backup: {bak}{NC}")
            return False
    if sudo_cp(str(bak), str(BINARY_PATH), remove_dest=True):
        sudo_chmod(str(BINARY_PATH))
        print(f"  {GREEN}[✓] Binary restored{NC}")
        return True
    return False


# ── JS patching ───────────────────────────────────────────────────────────────

def patch_js(verify_only: bool = False, force: bool = False, enable_auth_patch: bool = False) -> bool:
    print(f"\n{BLUE}{'Verifying' if verify_only else 'Patching'} extension.js{NC}")

    if not EXT_PATH.exists():
        print(f"  {RED}[!] Not found: {EXT_PATH}{NC}")
        return False

    with open(EXT_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    already = PROXY_URL in content
    if already and not force and not verify_only:
        print(f"  {YELLOW}[~] Already patched (use --force to re-patch){NC}")
        return True

    ok = True
    modified = False

    # URL constant replacements
    replacements = JS_URL_REPLACEMENTS
    for old, new in replacements:
        if old in content:
            if verify_only:
                print(f"  {RED}[✗] Unpatched: {old[:60]}{NC}")
                ok = False
            else:
                count = content.count(old)
                content = content.replace(old, new)
                print(f"  {GREEN}[✓]{NC} {count}x: {old[:55]} → {new[:40]}")
                modified = True
        elif new in content:
            print(f"  {GREEN}[✓]{NC} Already: {new[:55]}")
        # silently skip if neither found (pattern may not exist in this version)

    # Function override patches
    for old, new, desc in JS_FUNC_PATCHES:
        if new in content or new[:50] in content:
            print(f"  {GREEN}[✓]{NC} Already: {desc}")
        elif old in content:
            if verify_only:
                print(f"  {RED}[✗] Not overridden: {desc}{NC}")
                ok = False
            else:
                content = content.replace(old, new)
                print(f"  {GREEN}[✓]{NC} {desc}")
                modified = True

    if verify_only or not modified:
        return ok

    if not ensure_clean_backup(EXT_PATH, is_binary=False):
        return False

    tmp = Path(f"/tmp/extension_patched_{os.getpid()}.js")
    tmp.write_text(content, encoding="utf-8")
    if sudo_cp(str(tmp), str(EXT_PATH)):
        tmp.unlink(missing_ok=True)
        print(f"  {GREEN}[✓] extension.js written{NC}")
        return True
    tmp.unlink(missing_ok=True)
    print(f"  {RED}[!] Write failed{NC}")
    return False


def restore_js() -> bool:
    bak = Path(str(EXT_PATH) + ".original")
    if not bak.exists():
        print(f"  {RED}[!] No backup: {bak}{NC}")
        return False
    if sudo_cp(str(bak), str(EXT_PATH)):
        print(f"  {GREEN}[✓] extension.js restored{NC}")
        return True
    return False


def patch_wb(verify_only: bool = False) -> bool:
    print(f"\n{BLUE}{'Verifying' if verify_only else 'Patching'} workbench.js{NC}")
    if not WB_PATH.exists():
        print(f"  {RED}[!] Not found: {WB_PATH}{NC}")
        return False

    content = WB_PATH.read_text(encoding="utf-8")
    
    # Generic regex for the login banner component:
    # Looks for a variable assignment of an arrow function that renders "Log in to use Windsurf"
    import re
    # Pattern: [name]=({isOpen:[m],onClose:[d]})=>{... "Log in to use Windsurf" ...}
    # We target the start of the function body.
    pattern = r'([a-zA-Z0-9]+)=\(\{isOpen:[a-z],onClose:[a-z]\}\)=>\{'
    
    # We verify it's the right component by checking if "Log in to use Windsurf" follows shortly after
    # (within 200 chars)
    matches = list(re.finditer(pattern, content))
    target_match = None
    for m in matches:
        snippet = content[m.start():m.start()+500]
        if "Log in to use Windsurf" in snippet:
            target_match = m
            break
    
    if not target_match:
        print(f"  {RED}[✗] Login banner signature not found{NC}")
        return False

    comp_name = target_match.group(1)
    full_target = target_match.group(0)
    replacement = f"{comp_name}=({{isOpen:m,onClose:d}})=>{{return null;"

    if replacement in content:
        print(f"  {GREEN}[✓]{NC} Login Banner already suppressed")
        return True

    if verify_only:
        print(f"  {RED}[✗] Login banner not suppressed{NC}")
        return False

    content = content.replace(full_target, replacement)
    print(f"  {GREEN}[✓]{NC} Patch applied surgically ({comp_name})")

    if verify_only: return True

    if not ensure_clean_backup(WB_PATH, is_binary=False):
        return False

    tmp = Path(f"/tmp/wb_patched_{os.getpid()}.js")
    tmp.write_text(content, encoding="utf-8")
    if sudo_cp(str(tmp), str(WB_PATH)):
        tmp.unlink(missing_ok=True)
        print(f"  {GREEN}[✓] workbench.js written{NC}")
        return True
    return False


def restore_wb() -> bool:
    bak = Path(str(WB_PATH) + ".original")
    if not bak.exists():
        print(f"  {RED}[!] No backup: {bak}{NC}")
        return False
    if sudo_cp(str(bak), str(WB_PATH)):
        print(f"  {GREEN}[✓] workbench.js restored{NC}")
        return True
    return False


# ── /etc/hosts ────────────────────────────────────────────────────────────────

def patch_hosts(verify_only: bool = False) -> bool:
    hosts = Path("/etc/hosts")
    content = hosts.read_text()
    needed = {
        "proxy.windsurf.com":    "127.0.0.1  proxy.windsurf.com",
        "inferapi.windsurf.com": "127.0.0.1  inferapi.windsurf.com",
        "server.codeium.com":    "127.0.0.1  server.codeium.com",
        "inference.codeium.com": "127.0.0.1  inference.codeium.com",
        "server.self-serve.windsurf.com": "127.0.0.1  server.self-serve.windsurf.com",
        "unleash.codeium.com":   "127.0.0.1  unleash.codeium.com",
        "southcentral-lb.codeium.com": "127.0.0.1  southcentral-lb.codeium.com",
        "api.codeium.com":       "127.0.0.1  api.codeium.com",
    }
    missing = [line for host, line in needed.items() if host not in content]

    if not missing:
        print(f"  {GREEN}[✓]{NC} /etc/hosts already configured")
        return True

    if verify_only:
        for line in missing:
            print(f"  {RED}[✗] Missing: {line}{NC}")
        return False

    entries = "\n".join(missing) + "  # HG-PATCH"
    tmp = Path(f"/tmp/hosts_patch_{os.getpid()}")
    tmp.write_text(content.rstrip("\n") + "\n" + entries + "\n")
    if sudo_cp(str(tmp), str(hosts)):
        tmp.unlink(missing_ok=True)
        for line in missing:
            print(f"  {GREEN}[✓]{NC} Added: {line}")
        return True
    tmp.unlink(missing_ok=True)
    print(f"  {RED}[!] /etc/hosts write failed{NC}")
    return False


def restore_hosts():
    hosts = Path("/etc/hosts")
    content = hosts.read_text()
    cleaned = "\n".join(l for l in content.splitlines() if "HG-PATCH" not in l)
    tmp = Path(f"/tmp/hosts_clean_{os.getpid()}")
    tmp.write_text(cleaned + "\n")
    if sudo_cp(str(tmp), str(hosts)):
        tmp.unlink(missing_ok=True)
        print(f"  {GREEN}[✓] /etc/hosts entries removed{NC}")
    else:
        tmp.unlink(missing_ok=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HIGH-GRAVITY unified Windsurf patcher")
    parser.add_argument("--verify",        action="store_true", help="Verify patches without modifying")
    parser.add_argument("--restore",       action="store_true", help="Restore all files from backups")
    parser.add_argument("--force",         action="store_true", help="Re-patch even if already patched")
    parser.add_argument("--check-backups", action="store_true", help="Verify clean backups exist, exit 1 if not")
    parser.add_argument("--binary-only",   action="store_true")
    parser.add_argument("--js-only",        action="store_true")
    parser.add_argument("--wb-only",        action="store_true", help="Only patch workbench.js")
    parser.add_argument("--hosts-only",     action="store_true")
    parser.add_argument("--iptables",       action="store_true", help="Apply iptables 50001→9998 redirect")
    parser.add_argument("--iptables-undo",  action="store_true", help="Remove iptables 50001→9998 redirect")
    parser.add_argument("--preflight",      action="store_true", help="Validate patch targets/signatures without modifying files")
    parser.add_argument("--enable-auth-patch", action="store_true", help="Allow patching auth/login-related Windsurf URLs")
    args = parser.parse_args()

    global BINARY_PATH, EXT_PATH, WB_PATH
    WB_PATH = Path("/usr/share/windsurf-next/resources/app/out/vs/workbench/workbench.desktop.main.js")
    discovered_bin, discovered_ext = resolve_windsurf_paths()
    if discovered_bin:
        BINARY_PATH = discovered_bin
    if discovered_ext:
        EXT_PATH = discovered_ext

    all_targets = not (args.binary_only or args.js_only or args.wb_only or args.hosts_only)

    print(f"{BLUE}╔══════════════════════════════════════════════════════════════╗")
    print(f"║        HIGH-GRAVITY  Unified Patcher                        ║")
    print(f"╚══════════════════════════════════════════════════════════════╝{NC}")
    print(f"  Proxy URL:  {PROXY_URL}")
    print(f"  Infer URL:  {INFER_URL}")
    print(f"  Binary:     {BINARY_PATH}")
    print(f"  Extension:  {EXT_PATH}")
    print(f"  Auth patch: {'ENABLED' if args.enable_auth_patch else 'disabled (safe default)'}")

    if args.preflight:
        return 0 if preflight_check(enable_auth_patch=args.enable_auth_patch) else 1

    if args.check_backups:
        print(f"\n{BLUE}Checking backups...{NC}")
        ok = True
        if all_targets or args.binary_only:
            ok &= ensure_clean_backup(BINARY_PATH, is_binary=True)
        if all_targets or args.js_only:
            ok &= ensure_clean_backup(EXT_PATH, is_binary=False)
        if ok:
            print(f"\n{GREEN}All backups are clean and present.{NC}")
            return 0
        else:
            print(f"\n{RED}One or more backups are missing or tainted — see above.{NC}")
            return 1

    if args.iptables:
        ret = os.system(
            f"echo {SUDO_PASS} | sudo -S iptables -t nat -C OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998 2>/dev/null "
            f"|| echo {SUDO_PASS} | sudo -S iptables -t nat -A OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998"
        )
        if ret == 0:
            print(f"  {GREEN}[✓] iptables 50001→9998 active{NC}")
        else:
            print(f"  {RED}[!] iptables rule failed{NC}")
        return 0

    if args.iptables_undo:
        os.system(f"echo {SUDO_PASS} | sudo -S iptables -t nat -D OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998 2>/dev/null")
        print(f"  {GREEN}[✓] iptables 50001→9998 removed{NC}")
        return 0

    if args.restore:
        print(f"\n{YELLOW}Restoring all files...{NC}")
        if all_targets or args.binary_only: restore_binary()
        if all_targets or args.js_only:     restore_js()
        if all_targets or args.wb_only:     restore_wb()
        if all_targets or args.hosts_only:  restore_hosts()
        if all_targets:
            os.system(f"echo {SUDO_PASS} | sudo -S iptables -t nat -D OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998 2>/dev/null")
            print(f"  {GREEN}[✓] iptables 50001→9998 removed{NC}")
        return 0

    results = []
    if all_targets or args.binary_only:
        results.append(("Binary",    patch_binary(verify_only=args.verify)))
    if all_targets or args.js_only:
        results.append(("JS",        patch_js(verify_only=args.verify, force=args.force, enable_auth_patch=args.enable_auth_patch)))
    if all_targets or args.wb_only:
        results.append(("Workbench", patch_wb(verify_only=args.verify)))
    if all_targets or args.hosts_only:
        results.append(("/etc/hosts", patch_hosts(verify_only=args.verify)))
    if all_targets and args.verify:
        rule_ok = os.system("iptables -t nat -C OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998 2>/dev/null") == 0
        results.append(("iptables",   rule_ok))
        if rule_ok:
            print(f"  {GREEN}[✓] iptables 50001→9998 active{NC}")
        else:
            print(f"  {RED}[✗] iptables 50001→9998 not set{NC}")

    print()
    all_ok = all(r for _, r in results)
    for name, r in results:
        status = f"{GREEN}✓ OK{NC}" if r else f"{RED}✗ FAIL{NC}"
        print(f"  {name:15s} {status}")

    if not args.verify and all_ok:
        # Also apply iptables rule automatically on full patch
        if all_targets:
            os.system(
                f"echo {SUDO_PASS} | sudo -S iptables -t nat -C OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998 2>/dev/null "
                f"|| echo {SUDO_PASS} | sudo -S iptables -t nat -A OUTPUT -p tcp --dport 50001 -j REDIRECT --to-port 9998"
            )
            print(f"  {GREEN}[✓] iptables 50001→9998 active{NC}")
        print(f"\n{GREEN}All patches applied.{NC}")
        print(f"{YELLOW}Reload Windsurf window:{NC} Ctrl+Shift+P → Reload Window")
    elif args.verify and all_ok:
        print(f"\n{GREEN}All patches verified.{NC}")
    elif not all_ok:
        print(f"\n{RED}Some patches failed — check output above.{NC}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
