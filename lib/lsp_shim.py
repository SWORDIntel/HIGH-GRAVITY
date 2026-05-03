import sys
import os
import subprocess
import threading
import time
from pathlib import Path

# Paths
# The installer will rename the real binary to .real
REAL_LS = Path(__file__).resolve().parent / "language_server_linux_x64.real"
LOG_DIR = Path("/mnt/DSMIL/HIGH-GRAVITY/logs/lsp")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def force_proxy_args(args):
    """Rewrite LS URLs with safe defaults.
    Default: force both API and inference URLs through proxy.
    Set HG_PROXY_MODE=inference-only to only rewrite inference URL.
    """
    proxy_url = os.environ.get("HG_PROXY_URL", "https://proxy.windsurf.com")
    proxy_mode = os.environ.get("HG_PROXY_MODE", "full").strip().lower()
    rewrite_api = proxy_mode == "full"
    rewrite_inference = True

    new_args = []
    skip_next = False
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        
        if arg == "--api_server_url":
            new_args.append(arg)
            if rewrite_api and i + 1 < len(args):
                new_args.append(proxy_url)
                skip_next = True
            elif i + 1 < len(args):
                new_args.append(args[i + 1])
                skip_next = True
        elif arg == "--inference_api_server_url":
            new_args.append(arg)
            if rewrite_inference and i + 1 < len(args):
                new_args.append(proxy_url)
                skip_next = True
            elif i + 1 < len(args):
                new_args.append(args[i + 1])
                skip_next = True
        elif arg.startswith("--api_server_url="):
            if rewrite_api:
                new_args.append(f"--api_server_url={proxy_url}")
            else:
                new_args.append(arg)
        elif arg.startswith("--inference_api_server_url="):
            if rewrite_inference:
                new_args.append(f"--inference_api_server_url={proxy_url}")
            else:
                new_args.append(arg)
        elif arg == "--api_server_url" or arg == "--inference_api_server_url":
            skip_next = True
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
