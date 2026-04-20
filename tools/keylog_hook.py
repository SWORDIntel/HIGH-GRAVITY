#!/usr/bin/env python3
"""
Go TLS KeyLog extractor using GDB.

Attaches to the running language_server_linux_x64 process and hooks
crypto/tls.(*Config).writeKeyLog to dump session keys as NSS SSLKEYLOGFILE format.
These keys + the pcap let wireshark/tshark decrypt TLS traffic.

IMPORTANT: writeKeyLog address (0x5621e26fd660) was found by scanning
for RIP-relative references to CLIENT_HANDSHAKE_TRAFFIC_SECRET in the
live text segment. This address is ASLR-stable between restarts of the
same binary on the same machine, but will change on binary updates.

Run find_keylog_addr.py first to confirm the address is still valid.

Usage:
    echo 1786 | sudo -S python3 tools/keylog_hook.py
    # Then trigger a Windsurf completion / chat message
    # Keys appear in logs/cascade_tls.keys
    # Decrypt: python3 tools/keylog_hook.py --decrypt
"""
import os
import sys
import subprocess
import signal
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
KEYLOG_FILE = LOG_DIR / "cascade_tls.keys"
PCAP_FILE   = LOG_DIR / "cascade_passive.pcap"
DECRYPTED   = LOG_DIR / "cascade_decrypted.json"

# Address of crypto/tls.(*Config).writeKeyLog in the running process.
# Validated against: /usr/share/windsurf-next/.../language_server_linux_x64
# Build: Go BuildID embedded in binary, loaded at 0x5621e2486000 (text r-xp)
WRITKEYLOG_ADDR = 0x5621e26fd660


def get_load_addr(pid):
    """Get actual text segment load address to validate ASLR slide."""
    try:
        with open(f"/proc/{pid}/maps") as f:
            for line in f:
                if "language_server_linux_x64" in line and "r-xp" in line:
                    return int(line.split('-')[0], 16)
    except:
        pass
    return None


GDB_SCRIPT_TMPL = '''
set pagination off
set confirm off

python
import gdb, os

KEYLOG_FILE = "{keylog_file}"
FUNC_ADDR   = {func_addr}

class KeyLogBreakpoint(gdb.Breakpoint):
    def __init__(self):
        super().__init__(f"*{{FUNC_ADDR}}", gdb.BP_BREAKPOINT)
        self.silent = True
        self.count  = 0
        self.f = open(KEYLOG_FILE, "a", buffering=1)
        if os.path.getsize(KEYLOG_FILE) == 0:
            self.f.write("# NSS SSLKEYLOGFILE — dumped by HG keylog hook\\n")
            self.f.flush()
        print(f"[HG-KEYLOG] Hooked writeKeyLog at {{hex(FUNC_ADDR)}}")
        print(f"[HG-KEYLOG] Keys -> {{KEYLOG_FILE}}")

    def stop(self):
        try:
            inf = gdb.selected_inferior()
            # Go register ABI (1.17+):
            # func writeKeyLog(c *Config, label string, clientRandom, secret []byte)
            # RAX = *Config
            # RBX = label.ptr,   RCX = label.len
            # RDI = random.ptr,  RSI = random.len
            # R8  = secret.ptr,  R9  = secret.len
            label_ptr = int(gdb.parse_and_eval("$rbx"))
            label_len = min(int(gdb.parse_and_eval("$rcx")), 64)
            rand_ptr  = int(gdb.parse_and_eval("$rdi"))
            rand_len  = min(int(gdb.parse_and_eval("$rsi")), 64)
            sec_ptr   = int(gdb.parse_and_eval("$r8"))
            sec_len   = min(int(gdb.parse_and_eval("$r9")), 128)

            label    = bytes(inf.read_memory(label_ptr, label_len)).decode("utf-8", errors="replace").strip()
            rand_hex = bytes(inf.read_memory(rand_ptr,  rand_len)).hex()
            sec_hex  = bytes(inf.read_memory(sec_ptr,   sec_len)).hex()

            line = f"{{label}} {{rand_hex}} {{sec_hex}}\\n"
            self.f.write(line)
            self.count += 1
            print(f"[HG-KEYLOG] #{{self.count}} {{label}} rand={{rand_hex[:16]}}... secret={{sec_hex[:16]}}...")
        except Exception as e:
            print(f"[HG-KEYLOG] error: {{e}}")
        return False  # never pause execution

bp = KeyLogBreakpoint()
gdb.execute("continue")
end
'''


def find_pid():
    r = subprocess.run(["pgrep", "-f", "language_server_linux_x64"], capture_output=True, text=True)
    pids = r.stdout.strip().split()
    return int(pids[0]) if pids else None


def run_hook():
    pid = find_pid()
    if not pid:
        print("ERROR: language_server_linux_x64 not running")
        sys.exit(1)

    load_addr = get_load_addr(pid)
    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │    TLS KEYLOG EXTRACTOR (GDB hook)           │")
    print("  └─────────────────────────────────────────────┘")
    print()
    print(f"  PID:            {pid}")
    print(f"  Text load addr: {hex(load_addr) if load_addr else 'unknown'}")
    print(f"  writeKeyLog:    {hex(WRITKEYLOG_ADDR)}")
    print(f"  Key file:       {KEYLOG_FILE}")
    print()

    if load_addr and load_addr != 0x5621e2486000:
        print(f"  [!] ASLR slide detected: expected 0x5621e2486000 got {hex(load_addr)}")
        slide = load_addr - 0x5621e2486000
        adjusted = WRITKEYLOG_ADDR + slide
        print(f"  [!] Adjusting writeKeyLog to {hex(adjusted)}")
    else:
        adjusted = WRITKEYLOG_ADDR

    script = GDB_SCRIPT_TMPL.format(
        keylog_file=str(KEYLOG_FILE),
        func_addr=adjusted,
    )

    with tempfile.NamedTemporaryFile("w", suffix=".gdb", delete=False) as f:
        f.write(script)
        script_path = f.name

    print("  [*] Attaching GDB... (process pauses for ~1s, then continues)")
    print("  [*] Trigger a Windsurf completion to generate keys")
    print("  [*] Ctrl+C to stop")
    print()

    proc = subprocess.Popen(
        ["gdb", "-quiet", "-batch", f"--pid={pid}", "-x", script_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    def on_sigint(sig, frame):
        proc.terminate()
    signal.signal(signal.SIGINT, on_sigint)

    for line in proc.stdout:
        print(" ", line.rstrip())

    proc.wait()
    os.unlink(script_path)

    if KEYLOG_FILE.exists() and KEYLOG_FILE.stat().st_size > 0:
        keys = [l for l in KEYLOG_FILE.read_text().splitlines() if not l.startswith("#")]
        print(f"\n  [+] {len(keys)} session keys captured -> {KEYLOG_FILE}")
    else:
        print("\n  [!] No keys captured. Is Windsurf making TLS connections?")


def run_decrypt():
    if not PCAP_FILE.exists():
        print(f"No pcap at {PCAP_FILE}")
        sys.exit(1)
    if not KEYLOG_FILE.exists() or KEYLOG_FILE.stat().st_size == 0:
        print(f"No keys at {KEYLOG_FILE} — run hook first")
        sys.exit(1)

    print(f"  [*] Decrypting {PCAP_FILE} with {KEYLOG_FILE}...")
    result = subprocess.run([
        "tshark",
        "-r", str(PCAP_FILE),
        "-o", f"tls.keylog_file:{KEYLOG_FILE}",
        "-Y", "http2 or http",
        "-T", "json",
    ], capture_output=True, text=True)

    if result.stdout.strip():
        DECRYPTED.write_text(result.stdout)
        print(f"  [+] Decrypted traffic -> {DECRYPTED}")
        # Print summary
        import json
        try:
            frames = json.loads(result.stdout)
            print(f"  [+] {len(frames)} HTTP/2 frames")
            for fr in frames[:5]:
                layers = fr.get("_source", {}).get("layers", {})
                http2 = layers.get("http2", {})
                if isinstance(http2, list):
                    http2 = http2[0]
                path = http2.get("http2.header.value", "")
                print(f"    {path}")
        except:
            pass
    else:
        print(f"  [!] tshark output empty. stderr: {result.stderr[:300]}")


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Need root: echo 1786 | sudo -S python3 tools/keylog_hook.py")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--decrypt":
        run_decrypt()
    else:
        run_hook()
