#!/bin/bash
# High-Gravity Adaptive Throttler
echo "[*] Monitoring Windsurf children for CPU spikes..."
while true; do
    # Target windsurf child processes that consume > 50% CPU
    # Use awk to get PID and CPU%
    ps -eo pid,ppid,pcpu,comm | grep -E "windsurf|python" | while read -r pid ppid pcpu comm; do
        # Convert pcpu to integer for comparison
        cpu_int=${pcpu%.*}
        if [ "$cpu_int" -ge 50 ]; then
            echo "[!] Throttling high-CPU process $pid ($comm, ${pcpu}% CPU)"
            # Set to lowest priority (nice 19)
            sudo renice -n 19 -p $pid >/dev/null 2>&1
            # Optionally use cpulimit if available
            if command -v cpulimit >/dev/null; then
                sudo cpulimit -p $pid -l 20 --background >/dev/null 2>&1
            fi
        fi
    done
    sleep 5
done
