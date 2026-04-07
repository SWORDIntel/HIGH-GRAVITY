import sys
import os
import subprocess
import threading
import time
from pathlib import Path

# Paths
# The installer will rename the real binary to .real
REAL_LS = Path(__file__).resolve().parent / "language_server_linux_x64.real"
LOG_DIR = Path("/home/john/HIGH-GRAVITY/logs/lsp")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def force_proxy_args(args):
    """Overrides any server URL arguments to point to the local proxy."""
    new_args = []
    skip_next = False
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        
        if arg in ["--api_server_url", "--inference_api_server_url"]:
            new_args.append(arg)
            new_args.append("http://localhost:9999")
            skip_next = True
        elif arg.startswith("--api_server_url="):
            new_args.append("--api_server_url=http://localhost:9999")
        elif arg.startswith("--inference_api_server_url="):
            new_args.append("--inference_api_server_url=http://localhost:9999")
        else:
            new_args.append(arg)
    return new_args

def log_stream(stream, target_stream, name, session_id):
    log_file = LOG_DIR / f"{session_id}_{name}.log"
    try:
        with open(log_file, "wb") as f:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                f.write(chunk)
                f.flush()
                if target_stream:
                    target_stream.write(chunk)
                    target_stream.flush()
    except Exception:
        pass

if __name__ == "__main__":
    session_id = int(time.time())
    
    # Process arguments to enforce proxy
    original_args = sys.argv[1:]
    proxied_args = force_proxy_args(original_args)
    
    # Path to real binary - usually in the same dir as the shim
    bin_dir = Path(sys.argv[0]).parent
    real_binary = bin_dir / "language_server_linux_x64.real"
    
    if not real_binary.exists():
        # Fallback to absolute path if relative fails
        real_binary = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64.real")

    if not real_binary.exists():
        print(f"Error: Real binary not found at {real_binary}", file=sys.stderr)
        sys.exit(1)

    args = [str(real_binary)] + proxied_args
    
    proc = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )

    # Start logging and forwarding threads
    # stdin: sys.stdin -> proc.stdin
    t_stdin = threading.Thread(target=log_stream, args=(sys.stdin.buffer, proc.stdin, "stdin", session_id))
    # stdout: proc.stdout -> sys.stdout
    t_stdout = threading.Thread(target=log_stream, args=(proc.stdout, sys.stdout.buffer, "stdout", session_id))
    # stderr: proc.stderr -> sys.stderr
    t_stderr = threading.Thread(target=log_stream, args=(proc.stderr, sys.stderr.buffer, "stderr", session_id))

    t_stdin.daemon = True
    t_stdout.daemon = True
    t_stderr.daemon = True

    t_stdin.start()
    t_stdout.start()
    t_stderr.start()

    # Wait for process to exit
    exit_code = proc.wait()
    sys.exit(exit_code)
