#!/usr/bin/env python3
import os
import sys
import shutil
import argparse
from pathlib import Path

# Configuration
REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = REPO_ROOT / "logs" / "cascade_midway.log"
SUDO_PASS = "1786"

# Color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def find_extension_files():
    """Locates all Windsurf extension entry points (Stable, Next, Insiders, etc)."""
    search_paths = [
        Path("/usr/share"),
        Path("/opt"),
        Path.home() / ".local/share"
    ]
    
    found = []
    for base in search_paths:
        if not base.exists():
            continue
        # Search for windsurf directories
        for entry in base.glob("windsurf*"):
            ext_file = entry / "resources/app/extensions/windsurf/dist/extension.js"
            if ext_file.exists():
                found.append(ext_file)
    return found

def patch_file(ext_path: Path, force=False, verify_only=False):
    print(f"[*] Patching: {ext_path}")
    
    backup_path = ext_path.with_suffix(".js.original")
    
    # 1. Backup if not already backed up
    if not backup_path.exists():
        print(f"    - Creating backup at {backup_path}")
        os.system(f"echo {SUDO_PASS} | sudo -S cp {ext_path} {backup_path}")

    # 2. Read content
    with open(ext_path, "r") as f:
        content = f.read()

    # Check if already patched
    already_patched = "globalThis.HG_OPT" in content
    if already_patched and not force:
        print(f"    {YELLOW}- Already patched. Use --force to re-patch.{NC}")
        if verify_only:
            return verify_patches(content)
        return True
    elif already_patched and force:
        print(f"    {YELLOW}! Force mode: Re-applying patches...{NC}")
    
    if verify_only:
        return verify_patches(content)
    
    modified = False

    # Patch A: Redirect Inference API to HIGH-GRAVITY Proxy
    # Handle both n.push and array literal formats
    old_arg_inf = 'n.push("--inference_api_server_url",A.inferenceApiServerUrl)'
    new_arg_inf = 'n.push("--inference_api_server_url","http://shield.windsurf.com:9999")'
    
    old_lit_inf = '"--inference_api_server_url",A.inferenceApiServerUrl'
    new_lit_inf = '"--inference_api_server_url","http://shield.windsurf.com:9999"'
    
    # Patch A2: Redirect Base API to HIGH-GRAVITY Proxy
    old_arg_base = 'n.push("--api_server_url",A.apiServerUrl)'
    new_arg_base = 'n.push("--api_server_url","http://shield.windsurf.com:9999")'
    
    old_lit_base = '"--api_server_url",A.apiServerUrl'
    new_lit_base = '"--api_server_url","http://shield.windsurf.com:9999"'
    
    if old_arg_inf in content:
        content = content.replace(old_arg_inf, new_arg_inf)
        print("    [✓] Inference push redirection applied.")
        modified = True
    elif old_lit_inf in content:
        content = content.replace(old_lit_inf, new_lit_inf)
        print("    [✓] Inference literal redirection applied.")
        modified = True
    elif 'http://localhost:9999' in content:
        content = content.replace('http://localhost:9999', 'http://shield.windsurf.com:9999')
        print("    [✓] Updated localhost to shield.windsurf.com.")
        modified = True
        
    # Patch A3: Redirect Unleash (Feature Flags) to HIGH-GRAVITY Proxy
    old_unleash = 'url:"https://unleash.codeium.com/api/"'
    new_unleash = 'url:"http://shield.windsurf.com:9999/unleash/"'
    
    if old_unleash in content:
        content = content.replace(old_unleash, new_unleash)
        print("    [✓] Unleash redirection applied.")
        modified = True
    elif "http://shield.windsurf.com:9999/unleash/" in content:
        print("    [-] Unleash redirection already present.")
    
    # Patch A4: Hardcoded INFERENCE_API_SERVER_URL in config map
    old_inference_config = 'INFERENCE_API_SERVER_URL,"https://inference.codeium.com"'
    new_inference_config = 'INFERENCE_API_SERVER_URL,"http://shield.windsurf.com:9999"'
    
    if old_inference_config in content:
        content = content.replace(old_inference_config, new_inference_config)
        print("    [✓] Hardcoded INFERENCE_API_SERVER_URL redirected.")
        modified = True
    
    # Patch A5: Hardcoded DEFAULT_API_SERVER_URL
    old_api_default = 'DEFAULT_API_SERVER_URL="https://server.codeium.com"'
    new_api_default = 'DEFAULT_API_SERVER_URL="http://shield.windsurf.com:9999"'
    
    if old_api_default in content:
        content = content.replace(old_api_default, new_api_default)
        print("    [✓] Hardcoded DEFAULT_API_SERVER_URL redirected.")
        modified = True
    
    # Patch A6: Hardcoded DEFAULT_REGISTER_API_SERVER_URL
    old_register = 'DEFAULT_REGISTER_API_SERVER_URL="https://register.windsurf.com"'
    new_register = 'DEFAULT_REGISTER_API_SERVER_URL="http://shield.windsurf.com:9999"'
    
    if old_register in content:
        content = content.replace(old_register, new_register)
        print("    [✓] Hardcoded DEFAULT_REGISTER_API_SERVER_URL redirected.")
        modified = True
    
    # Patch A7: EU API routes
    old_eu_route = '"https://eu.windsurf.com/_route/api_server"'
    new_eu_route = '"http://shield.windsurf.com:9999"'
    
    eu_count = content.count(old_eu_route)
    if eu_count > 0:
        content = content.replace(old_eu_route, new_eu_route)
        print(f"    [✓] Redirected {eu_count} EU API route(s).")
        modified = True
    
    # Patch A8: Fed API routes
    old_fed_route = '"https://windsurf.fedstart.com/_route/api_server"'
    new_fed_route = '"http://shield.windsurf.com:9999"'
    
    fed_count = content.count(old_fed_route)
    if fed_count > 0:
        content = content.replace(old_fed_route, new_fed_route)
        print(f"    [✓] Redirected {fed_count} Fed API route(s).")
        modified = True
    
    # Patch A9: Self-serve API route (used by language server)
    old_self_serve = '"https://server.self-serve.windsurf.com"'
    new_self_serve = '"http://shield.windsurf.com:9999"'
    
    self_serve_count = content.count(old_self_serve)
    if self_serve_count > 0:
        content = content.replace(old_self_serve, new_self_serve)
        print(f"    [✓] Redirected {self_serve_count} self-serve API route(s).")
        modified = True

    # Patch A10: Override getApiServerUrlFromContext to always return proxy
    # ROOT CAUSE: This function reads a stored URL from VS Code globalState
    # (set during login) which returns "https://server.self-serve.windsurf.com"
    # and passes it as --api_server_url to the language server.
    old_getApiUrl = 'e.getApiServerUrlFromContext=A=>{'
    new_getApiUrl = 'e.getApiServerUrlFromContext=A=>{return"http://shield.windsurf.com:9999";'
    
    if old_getApiUrl in content:
        content = content.replace(old_getApiUrl, new_getApiUrl)
        print("    [✓] getApiServerUrlFromContext overridden (ROOT CAUSE FIX)")
        modified = True
    elif 'e.getApiServerUrlFromContext=A=>{return"http://shield.windsurf.com:9999"' in content:
        print("    [-] getApiServerUrlFromContext already overridden")
    else:
        print("    [!] getApiServerUrlFromContext pattern not found")

    # Patch A11: Override getApiServerUrl to always return proxy
    old_getApiUrl2 = 'e.getApiServerUrl=A=>(0,'
    new_getApiUrl2 = 'e.getApiServerUrl=A=>"http://shield.windsurf.com:9999"||A=>(0,'
    
    if old_getApiUrl2 in content:
        content = content.replace(old_getApiUrl2, new_getApiUrl2)
        print("    [✓] getApiServerUrl overridden")
        modified = True
    elif 'e.getApiServerUrl=A=>"http://shield.windsurf.com:9999"' in content:
        print("    [-] getApiServerUrl already overridden")

    # Patch A12: Override getRegisterApiServerUrl to always return proxy
    old_getRegUrl = 'e.getRegisterApiServerUrl=()=>(0,'
    new_getRegUrl = 'e.getRegisterApiServerUrl=()=>"http://shield.windsurf.com:9999"||()=>(0,'
    
    if old_getRegUrl in content:
        content = content.replace(old_getRegUrl, new_getRegUrl)
        print("    [✓] getRegisterApiServerUrl overridden")
        modified = True
    elif 'e.getRegisterApiServerUrl=()=>"http://shield.windsurf.com:9999"' in content:
        print("    [-] getRegisterApiServerUrl already overridden")

    # Patch B: Universal Optimizer & Protocol Interceptor
    optimizer_code = f"""
globalThis.HG_CACHE = globalThis.HG_CACHE || new Set();
globalThis.HG_OPT = (items, config) => {{
    try {{
        const logData = {{
            timestamp: new Date().toISOString(),
            model: config?.requestedModelUid,
            itemCount: items?.length,
            metadata: config?.metadata
        }};
        require("fs").appendFileSync("{LOG_PATH}", "\\n--- PROTOCOL EVENT ---\\n" + JSON.stringify(logData, null, 2) + "\\n");
    }} catch(e) {{}}

    if (!Array.isArray(items)) return items;
    
    items.sort((a, b) => {{
        const valA = a.chunk?.value || "";
        const valB = b.chunk?.value || "";
        return valA.localeCompare(valB);
    }});

    return items.map(item => {{
        if (item.chunk?.case === "text") {{
            const val = item.chunk.value;
            const hash = val.substring(0, 200);
            if (globalThis.HG_CACHE.has(hash)) {{
                item.chunk.value = `[HG:CACHED] ${{val.substring(0, 30)}}`;
                return item;
            }}
            globalThis.HG_CACHE.add(hash);
            if (val.length > 2500) {{
                item.highgravity_cache = true;
            }}
        }}
        return item;
    }});
}};
"""
    if '"use strict";' in content and "globalThis.HG_OPT" not in content:
        content = content.replace('"use strict";', '"use strict";' + optimizer_code)
        print("    [✓] Global Optimizer injected.")
        modified = True

    # Patch C: Wrap Send Calls
    if "items:globalThis.HG_OPT" not in content:
        content = content.replace("items:e,cascadeConfig", "items:globalThis.HG_OPT(e,t),cascadeConfig")
        content = content.replace("items:g,cascadeConfig", "items:globalThis.HG_OPT(g,t),cascadeConfig")
        print("    [✓] Send calls wrapped.")
        modified = True

    if modified:
        # Save patched file
        temp_patch = Path(f"/tmp/extension.js.{os.getpid()}")
        with open(temp_patch, "w") as f:
            f.write(content)

        # Write back with sudo
        os.system(f"echo {SUDO_PASS} | sudo -S cp {temp_patch} {ext_path}")
        os.system(f"rm {temp_patch}")
        print(f"    {GREEN}[✓] Successfully updated {ext_path.parent.parent.parent.parent.parent.name}{NC}")
        return True
    else:
        print(f"    - No changes needed.")
        return False

def verify_patches(content):
    """Verify all patches are present"""
    checks = [
        ('INFERENCE_API_SERVER_URL', 'INFERENCE_API_SERVER_URL,"http://shield.windsurf.com:9999"'),
        ('DEFAULT_API_SERVER_URL', 'DEFAULT_API_SERVER_URL="http://shield.windsurf.com:9999"'),
        ('DEFAULT_REGISTER_API_SERVER_URL', 'DEFAULT_REGISTER_API_SERVER_URL="http://shield.windsurf.com:9999"'),
        ('Unleash', 'url:"http://shield.windsurf.com:9999/unleash/"'),
        ('getApiServerUrlFromContext', 'getApiServerUrlFromContext=A=>{return"http://shield.windsurf.com:9999"'),
        ('HG_OPT function', 'globalThis.HG_OPT'),
    ]
    
    all_pass = True
    for name, pattern in checks:
        if pattern in content:
            print(f"    {GREEN}✓{NC} {name}")
        else:
            print(f"    {RED}✗{NC} {name}")
            all_pass = False
    
    # Count proxy references
    proxy_count = content.count('shield.windsurf.com:9999')
    print(f"\n    {BLUE}Total proxy references: {proxy_count}{NC}")
    
    return all_pass

def main():
    parser = argparse.ArgumentParser(
        description='Patch Windsurf to redirect API calls through HIGH-GRAVITY proxy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                    # Normal patching
  %(prog)s --force            # Force re-patch even if already patched
  %(prog)s --verify           # Verify patches without modifying
  %(prog)s --list             # List Windsurf installations
'''
    )
    parser.add_argument('--force', '-f', action='store_true',
                       help='Force re-patch even if already patched')
    parser.add_argument('--verify', '-v', action='store_true',
                       help='Verify patches without modifying files')
    parser.add_argument('--list', '-l', action='store_true',
                       help='List Windsurf installations and exit')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output')
    
    args = parser.parse_args()
    
    if not args.quiet:
        print(f"{BLUE}╔════════════════════════════════════════════════════════════╗{NC}")
        print(f"{BLUE}║     Windsurf HIGH-GRAVITY Patcher v2.0                     ║{NC}")
        print(f"{BLUE}╚════════════════════════════════════════════════════════════╝{NC}")
        print()
    
    extensions = find_extension_files()
    if not extensions:
        print(f"{RED}[!] No Windsurf installations found.{NC}")
        return 1

    if not args.quiet:
        print(f"[*] Found {len(extensions)} Windsurf installation(s).")
    
    if args.list:
        for ext in extensions:
            print(f"  - {ext}")
        return 0
    
    success_count = 0
    for ext in extensions:
        try:
            if patch_file(ext, force=args.force, verify_only=args.verify):
                success_count += 1
        except Exception as e:
            print(f"{RED}[!] Error patching {ext}: {e}{NC}")
    
    if not args.quiet:
        print()
        if args.verify:
            print(f"{GREEN}[✓] Verification complete: {success_count}/{len(extensions)} passed{NC}")
        else:
            print(f"{GREEN}[✓] Patching complete: {success_count}/{len(extensions)} successful{NC}")
            if success_count > 0:
                print(f"\n{YELLOW}[!] Please restart Windsurf for changes to take effect{NC}")
    
    return 0 if success_count == len(extensions) else 1

if __name__ == "__main__":
    sys.exit(main())
