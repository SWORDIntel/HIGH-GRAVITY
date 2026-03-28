#!/usr/bin/env python3
import sys
import os
import subprocess
import threading
import time
from pathlib import Path

# Paths
REAL_LS = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64.real")
LOG_DIR = Path("/home/john/HIGH-GRAVITY/logs/lsp")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_stream(stream, name, session_id):
    log_file = LOG_DIR / f"{session_id}_{name}.log"
    with open(log_file, "wb") as f:
        while True:
            chunk = stream.read(4096)
            if not chunk:
                break
            f.write(chunk)
            f.flush()
            # Also write to the original destination
            if name == "stdin":
                proc.stdin.write(chunk)
                proc.stdin.flush()
            elif name == "stdout":
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
            elif name == "stderr":
                sys.stderr.buffer.write(chunk)
                sys.stderr.buffer.flush()

if __name__ == "__main__":
    session_id = int(time.time())
    
    # Pass all arguments to the real binary
    args = [str(REAL_LS)] + sys.argv[1:]
    
    proc = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )

    # Start logging threads
    t_stdin = threading.Thread(target=log_stream, args=(sys.stdin.buffer, "stdin", session_id))
    t_stdout = threading.Thread(target=log_stream, args=(proc.stdout, "stdout", session_id))
    t_stderr = threading.Thread(target=log_stream, args=(proc.stderr, "stderr", session_id))

    t_stdin.start()
    t_stdout.start()
    t_stderr.start()

    # Wait for process to exit
    exit_code = proc.wait()
    sys.exit(exit_code)
