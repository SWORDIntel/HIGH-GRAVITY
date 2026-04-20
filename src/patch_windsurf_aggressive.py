#!/usr/bin/env python3
"""
Aggressive MITM patch - logs ALL function calls
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = REPO_ROOT / "logs" / "cascade_midway.log"
SUDO_PASS = "1786"

ext_path = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/dist/extension.js")

print(f"[*] Aggressive patching: {ext_path}")

with open(ext_path, "r") as f:
    content = f.read()

# Add aggressive logging at the very start
aggressive_logger = f"""
(function() {{
    const fs = require('fs');
    const logPath = '{LOG_PATH}';
    
    // Log when file loads
    try {{
        fs.appendFileSync(logPath, `\\n=== EXTENSION LOADED: ${{new Date().toISOString()}} ===\\n`);
    }} catch(e) {{}}
    
    // Intercept ALL object creations that might be cascade responses
    const originalStringify = JSON.stringify;
    let callCount = 0;
    
    setInterval(() => {{
        if (globalThis.HG_OPT && typeof globalThis.HG_OPT === 'function') {{
            try {{
                fs.appendFileSync(logPath, `\\n[HEARTBEAT] HG_OPT exists, calls: ${{callCount}}\\n`);
            }} catch(e) {{}}
        }}
    }}, 30000);
    
    // Wrap HG_OPT to log when it's called
    if (globalThis.HG_OPT) {{
        const original_HG_OPT = globalThis.HG_OPT;
        globalThis.HG_OPT = function(...args) {{
            callCount++;
            try {{
                fs.appendFileSync(logPath, `\\n[HG_OPT CALLED #${{callCount}}] args: ${{args.length}}\\n`);
            }} catch(e) {{}}
            return original_HG_OPT.apply(this, args);
        }};
    }}
}})();
"""

# Inject at the very beginning
if "=== EXTENSION LOADED:" not in content:
    content = aggressive_logger + content
    print("[✓] Aggressive logging injected")
    
    # Write back
    temp_patch = Path(f"/tmp/extension.js.aggressive")
    with open(temp_patch, "w") as f:
        f.write(content)
    
    os.system(f"echo {SUDO_PASS} | sudo -S cp {temp_patch} {ext_path}")
    os.system(f"rm {temp_patch}")
    print("[✓] Patch applied - restart Windsurf")
else:
    print("[-] Already aggressively patched")
