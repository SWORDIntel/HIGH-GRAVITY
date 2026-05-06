# GDB script: hook crypto/tls writeKeyLog and dump NSS SSLKEYLOGFILE format
# Usage: echo 1786 | sudo -S gdb -quiet -batch -x tools/keylog_hook.gdb
# Requires: KEYLOG_FILE and PID set via -ex before -x

set pagination off
set confirm off

# Attach
attach $arg0

python
import gdb
import os

KEYLOG_FILE = os.environ.get("HG_KEYLOG", "/mnt/DSMIL/HIGH-GRAVITY/logs/cascade_tls.keys")

# writeKeyLog address (found by scanning for CLIENT_HANDSHAKE_TRAFFIC_SECRET xrefs)
WRITKEYLOG_ADDR = 0x5621e26fd660

class KeyLogBreakpoint(gdb.Breakpoint):
    def __init__(self):
        super().__init__(f"*{WRITKEYLOG_ADDR}", gdb.BP_BREAKPOINT)
        self.silent = True
        self.count = 0
        self.f = open(KEYLOG_FILE, "a", buffering=1)
        if self.f.tell() == 0:
            self.f.write("# TLS Session Keys dumped by HG keylog hook\n")
        print(f"[HG-KEYLOG] Breakpoint at writeKeyLog ({hex(WRITKEYLOG_ADDR)})")
        print(f"[HG-KEYLOG] Writing keys to: {KEYLOG_FILE}")

    def stop(self):
        try:
            # Go register calling convention (go1.17+):
            # writeKeyLog(c *tls.Config, label string, clientRandom []byte, secret []byte)
            # AX = *Config (receiver)
            # BX = label ptr, CX = label len
            # DI = clientRandom ptr, SI = clientRandom len
            # R8 = secret ptr, R9 = secret len

            inf = gdb.selected_inferior()

            label_ptr = int(gdb.parse_and_eval("$rbx"))
            label_len = int(gdb.parse_and_eval("$rcx"))
            rand_ptr  = int(gdb.parse_and_eval("$rdi"))
            rand_len  = int(gdb.parse_and_eval("$rsi"))
            sec_ptr   = int(gdb.parse_and_eval("$r8"))
            sec_len   = int(gdb.parse_and_eval("$r9"))

            if label_len > 64 or rand_len > 64 or sec_len > 128:
                return False  # sanity check

            label = bytes(inf.read_memory(label_ptr, label_len)).decode("utf-8", errors="replace")
            rand_hex = bytes(inf.read_memory(rand_ptr, rand_len)).hex()
            sec_hex  = bytes(inf.read_memory(sec_ptr, sec_len)).hex()

            line = f"{label} {rand_hex} {sec_hex}\n"
            self.f.write(line)
            self.count += 1
            print(f"[HG-KEYLOG] #{self.count}: {label} rand={rand_hex[:12]}... secret={sec_hex[:12]}...")

        except Exception as e:
            print(f"[HG-KEYLOG] Error: {e}")

        return False  # never stop execution

bp = KeyLogBreakpoint()
gdb.execute("continue")
end
