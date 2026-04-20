#!/usr/bin/env python3
"""
run_keylog.py — Launch TLS key capture for language_server_linux_x64

Steps:
  1. Read /tmp/hg_writer_ptrs  (written by keylog_preload.so on LS startup)
  2. Read symbol offsets from keylog_preload.so to compute live VAs
  3. Generate a bpftrace script with the real itab/data ptrs embedded as
     literals, then run it under sudo.

The bpftrace script:
  - PLANT probes at all 10 writeKeyLog call sites: use bpf_probe_write_user
    to write {itab_ptr, data_ptr} into tls.Config+0x138 before the nil check.
  - CAPTURE probe at writeKeyLog entry: dump label/rand/secret as SSLKEYLOGFILE.

Usage:
  echo 1786 | sudo -S python3 tools/run_keylog.py
  echo 1786 | sudo -S python3 tools/run_keylog.py --decrypt
"""

import os, sys, struct, subprocess, textwrap, time, signal

BIN        = "/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64"
SO_PATH    = "/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/keylog_preload.so"
PTRS_FILE  = "/tmp/hg_writer_ptrs"
KEYLOG_OUT = "logs/cascade_tls.keys"
PCAP_FILE  = "logs/cascade_passive.pcap"

# writeKeyLog file offset within binary
WKL_FOFF   = 0x6d50660   # = 114624096
# tls.Config.KeyLogWriter interface offset
WRITER_OFF = 0x138        # itab word
DATA_OFF   = 0x140        # data word

# All 10 call sites to writeKeyLog (file offsets)
CALL_SITES = [
    0x6d66174,   # = 114761076
    0x6d6c0c5,   # = 114786501
    0x6d6c115,   # = 114786581
    0x6d6d580,   # = 114792832
    0x6d6d5cd,   # = 114792909
    0x6d8a88c,   # = 114868364
    0x6d90565,   # = 114892133
    0x6d905b5,   # = 114892213
    0x6d91851,   # = 114897233
    0x6d918a0,   # = 114897312
]


def get_text_base():
    """Get the r-xp base VA for language_server from a running process."""
    pid = None
    try:
        pid = subprocess.check_output(
            ["pgrep", "-f", "language_server_linux_x64"], text=True
        ).split()[0].strip()
    except subprocess.CalledProcessError:
        return None, None

    with open(f"/proc/{pid}/maps") as f:
        for line in f:
            if "language_server_linux_x64" in line and "r-xp" in line:
                parts = line.split()
                base = int(parts[0].split('-')[0], 16)
                foff = int(parts[2], 16)
                return base, foff
    return None, None


def get_writer_ptrs():
    """Read {itab_ptr, data_ptr} from /tmp/hg_writer_ptrs."""
    if not os.path.exists(PTRS_FILE):
        return None, None
    with open(PTRS_FILE, 'rb') as f:
        raw = f.read(16)
    if len(raw) < 16:
        return None, None
    itab_ptr, data_ptr = struct.unpack('<QQ', raw)
    return itab_ptr, data_ptr


def foff_to_va(base, text_foff, file_offset):
    return base + (file_offset - text_foff)


def build_bpftrace_script(itab_ptr, data_ptr, text_base, text_foff):
    """Generate bpftrace script with embedded pointer literals."""

    # PLANT probe body — writes interface value into tls.Config
    plant_body = f"""\
    $config = reg("ax");
    if ($config == 0) {{ return; }}
    /* plant itab ptr at config+0x{WRITER_OFF:x} */
    bpf_probe_write_user((void*)($config + 0x{WRITER_OFF:x}), &@itab_lit, 8);
    /* plant data ptr at config+0x{DATA_OFF:x} */
    bpf_probe_write_user((void*)($config + 0x{DATA_OFF:x}), &@data_lit, 8);
    @planted++;
"""

    # Build all PLANT probes
    plant_probes = []
    for foff in CALL_SITES:
        va_foff = foff - text_foff  # offset relative to text start
        bt_offset = foff           # bpftrace uses file offset directly
        plant_probes.append(
            f"uprobe:{BIN}:{bt_offset}\n{{\n{plant_body}}}"
        )

    wkl_offset = WKL_FOFF  # file offset for writeKeyLog entry

    capture_probe = f"""\
uprobe:{BIN}:{wkl_offset}
{{
    $label_ptr = reg("bx");
    $label_len = reg("cx");
    $rand_ptr  = reg("di");
    $rand_len  = reg("si");
    $sec_ptr   = reg("r8");
    $sec_len   = reg("r9");

    if ($label_len == 0 || $label_len > 64)  {{ return; }}
    if ($rand_len  == 0 || $rand_len  > 64)  {{ return; }}
    if ($sec_len   == 0 || $sec_len   > 128) {{ return; }}

    $label = str($label_ptr, $label_len);
    printf("%s ", $label);

    $r = (uint8*)$rand_ptr;
    printf("%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x"
           "%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x ",
        $r[0],$r[1],$r[2],$r[3],$r[4],$r[5],$r[6],$r[7],
        $r[8],$r[9],$r[10],$r[11],$r[12],$r[13],$r[14],$r[15],
        $r[16],$r[17],$r[18],$r[19],$r[20],$r[21],$r[22],$r[23],
        $r[24],$r[25],$r[26],$r[27],$r[28],$r[29],$r[30],$r[31]);

    $s = (uint8*)$sec_ptr;
    printf("%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x"
           "%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x",
        $s[0],$s[1],$s[2],$s[3],$s[4],$s[5],$s[6],$s[7],
        $s[8],$s[9],$s[10],$s[11],$s[12],$s[13],$s[14],$s[15],
        $s[16],$s[17],$s[18],$s[19],$s[20],$s[21],$s[22],$s[23],
        $s[24],$s[25],$s[26],$s[27],$s[28],$s[29],$s[30],$s[31]);
    if ($sec_len > 32) {{
        printf("%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x",
            $s[32],$s[33],$s[34],$s[35],$s[36],$s[37],$s[38],$s[39],
            $s[40],$s[41],$s[42],$s[43],$s[44],$s[45],$s[46],$s[47]);
    }}
    printf("\\n");
    @count++;
}}"""

    script = f"""\
/* HG keylog — auto-generated by run_keylog.py */
BEGIN {{
    printf("# NSS SSLKEYLOGFILE\\n");
    @itab_lit = (uint64){itab_ptr};
    @data_lit = (uint64){data_ptr};
    @planted  = (uint64)0;
    @count    = (uint64)0;
    printf("[HG] probes armed (itab=0x{itab_ptr:x} data=0x{data_ptr:x})\\n");
}}

{chr(10).join(plant_probes)}

{capture_probe}

END {{
    printf("[HG] planted=%lld keys=%lld\\n", @planted, @count);
    clear(@itab_lit); clear(@data_lit);
    clear(@planted);  clear(@count);
}}
"""
    return script


def do_decrypt():
    print("[*] Decrypting pcap with captured keys...")
    if not os.path.exists(KEYLOG_OUT):
        print(f"  ERROR: {KEYLOG_OUT} not found")
        sys.exit(1)
    if not os.path.exists(PCAP_FILE):
        print(f"  ERROR: {PCAP_FILE} not found")
        sys.exit(1)
    out = "logs/cascade_decrypted.json"
    cmd = [
        "tshark", "-r", PCAP_FILE,
        "-o", f"tls.keylog_file:{KEYLOG_OUT}",
        "-T", "json",
        "-Y", "http2 || http",
    ]
    print(f"  {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    with open(out, 'w') as f:
        f.write(result.stdout)
    if result.returncode == 0:
        print(f"  [+] Decrypted -> {out}  ({len(result.stdout)} bytes)")
    else:
        print(f"  [!] tshark error: {result.stderr[:200]}")


def main():
    os.makedirs("logs", exist_ok=True)

    if "--decrypt" in sys.argv:
        do_decrypt()
        return

    print("[*] HG TLS Key Capture")
    print()

    # Check preload ptrs
    itab_ptr, data_ptr = get_writer_ptrs()
    if not itab_ptr:
        print(f"  [!] {PTRS_FILE} not found or empty.")
        print( "      Ensure keylog wrapper is installed and Windsurf was reloaded.")
        print( "      Run: sudo bash tools/install_keylog_wrapper.sh")
        sys.exit(1)
    print(f"  [+] Writer ptrs: itab=0x{itab_ptr:x}  data=0x{data_ptr:x}")

    # Get text base
    text_base, text_foff = get_text_base()
    if not text_base:
        print("  [!] language_server_linux_x64 not running.")
        sys.exit(1)
    print(f"  [+] text_base=0x{text_base:x}  text_foff=0x{text_foff:x}")

    # Generate script
    script = build_bpftrace_script(itab_ptr, data_ptr, text_base, text_foff)
    script_path = "/tmp/hg_keylog_live.bt"
    with open(script_path, 'w') as f:
        f.write(script)
    print(f"  [+] Script: {script_path}")
    print(f"  [+] Output: {KEYLOG_OUT}")
    print()
    print("  Trigger TLS handshakes by triggering Windsurf AI completions...")
    print("  (Ctrl+C to stop)")
    print()

    with open(KEYLOG_OUT, 'a') as kf:
        kf.write("# NSS SSLKEYLOGFILE\n")

    cmd = ["bpftrace", "--unsafe", script_path, "-o", KEYLOG_OUT]
    proc = subprocess.run(cmd)


if __name__ == "__main__":
    main()
