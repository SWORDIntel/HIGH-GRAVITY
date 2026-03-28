#!/usr/bin/env python3
import os
import sys
import shutil
from pathlib import Path

# Configuration
LOG_PATH = Path("/home/john/HIGH-GRAVITY/logs/cascade_midway.log")
SUDO_PASS = "1786"

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

def patch_file(ext_path: Path):
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
    if "globalThis.HG_OPT" in content:
        print(f"    - Already patched. Checking for updates...")
        # We can still proceed if we want to update the optimization logic
    
    modified = False

    # Patch A: Redirect Inference API to HIGH-GRAVITY Proxy (localhost:9999)
    old_arg = 'n.push("--inference_api_server_url",A.inferenceApiServerUrl)'
    new_arg = 'n.push("--inference_api_server_url","http://localhost:9999")'
    
    if old_arg in content:
        content = content.replace(old_arg, new_arg)
        print("    [✓] Redirection applied.")
        modified = True

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
        print(f"    [✓] Successfully updated {ext_path.parent.parent.parent.parent.parent.name}")
    else:
        print(f"    - No changes needed.")

def main():
    extensions = find_extension_files()
    if not extensions:
        print("[!] No Windsurf installations found.")
        return

    print(f"[*] Found {len(extensions)} Windsurf installation(s).")
    for ext in extensions:
        try:
            patch_file(ext)
        except Exception as e:
            print(f"[!] Error patching {ext}: {e}")

    print("\n[✓] All patches applied. Please restart any running Windsurf instances.")

if __name__ == "__main__":
    main()
