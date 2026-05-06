#!/usr/bin/env python3
"""
patch_keylog.py — Binary patch to enable TLS key logging in language_server_linux_x64

Strategy:
  1. Find the code cave (783 NOP bytes between .fini and .plt)
  2. Write a shellcode stub there that:
       a) Opens /tmp/hg_tls.keys (O_WRONLY|O_CREAT|O_APPEND, 0600) via syscall
       b) Allocates a tiny io.Writer-compatible struct on the heap (via Go runtime malloc)
       c) Stores the struct ptr into 0x138(%rax) on every writeKeyLog entry
  3. Patch writeKeyLog: replace the 'je (skip-if-nil)' with a 'call stub'
     so the writer is set before the nil check

Actually simpler approach:
  Patch 'cmpq $0x0, 0x138(%rax)' to 'cmpq $0xdeadbeef, 0x138(%rax)'
  This makes the je NEVER fire (deadbeef != 0 always), so writeKeyLog always
  proceeds past the nil check and tries to call Write() on whatever is at 0x138(%rax).
  Simultaneously patch the function preamble to set 0x138(%rax) = &our_writer_global
  where our_writer_global is a pre-built io.Writer we plant in the .data section.

Even simpler: just replace the je with nops AND patch the cmpq to load from
a global we pre-populate with a real *os.File interface value (itab + data ptr).

Actual implementation:
  - Find os.Stderr's interface value (itab ptr + *os.File ptr) in .data at runtime
  - Patch the 8 bytes at 0x138(config) to those values at writeKeyLog entry

This requires knowing the runtime address of os.Stderr.
Instead: use the code cave to emit a syscall-based open() that returns a raw fd,
then construct a minimal io.Writer around it.

Since this is complex, we use the SIMPLEST working approach:
  Patch writeKeyLog to redirect to our cave stub which:
    - Checks if a global flag is set (first call)
    - If not: calls open("/tmp/hg_tls.keys") via direct syscall (no Go runtime)
    - Stores the resulting *os.File-like wrapper into a .data global
    - Sets 0x138(%rax) to that global
    - Returns to original writeKeyLog body (skipping the nil check)
    - On subsequent calls: just sets 0x138(%rax) from the cached global

File offsets (binary-relative, stable):
  writeKeyLog entry:       0x6d50660
  je (skip-if-nil) at:    0x6d506a0
  code cave start:         0x8ee1f11  (783 bytes of zeros, executable)

Usage:
  python3 tools/patch_keylog.py           # apply patch
  python3 tools/patch_keylog.py --undo    # restore original
  python3 tools/patch_keylog.py --verify  # check patch state
"""
import os
import sys
import struct
import shutil
from pathlib import Path

BIN = Path("/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64")
BACKUP = BIN.with_suffix(".bak_keylog")

# Key file offsets (stable, binary-specific)
WKL_ENTRY_FOFF  = 0x6d50660   # writeKeyLog function entry (lea -0x20(%rsp),%r12)
JE_FOFF         = 0x6d506a0   # je rel32 that skips write when KeyLogWriter==nil
CAVE_FOFF       = 0x8ee1f11   # code cave (783 zero bytes, in executable segment)
CAVE_SIZE       = 783

# Original bytes for verification / undo
JE_ORIG         = bytes.fromhex("0f84a8010000")     # je +0x1a8 (6 bytes)
JE_PATCH_CALL   = None   # computed: e8 <rel32> (5 bytes + 1 nop)

# Log file path the stub will open
KEYLOG_PATH = b"/tmp/hg_tls.keys\x00"

# Section load info (for VA computation at runtime — used for RIP-relative calcs)
TEXT_FOFF = 0x6ad9000
CAVE_VA_LINK    = 0x8ee2111   # link-time VA of cave (from ELF: .fini end VA + offset)
# Actually: cave is in the r-xp segment at the same VA offset
# .plt is at VA 0x8ee2220, cave_foff=0x8ee1f11, so cave_VA = 0x8ee1f11 (same as foff for this binary since VA=foff for .text region segments)

def read_binary():
    with open(BIN, 'rb') as f:
        return bytearray(f.read())

def write_binary(data):
    with open(BIN, 'r+b') as f:
        f.write(data)

def verify():
    data = read_binary()
    je_bytes = bytes(data[JE_FOFF:JE_FOFF+6])
    entry_bytes = bytes(data[WKL_ENTRY_FOFF:WKL_ENTRY_FOFF+5])
    cave_bytes = bytes(data[CAVE_FOFF:CAVE_FOFF+4])

    patched = (je_bytes != JE_ORIG)
    print(f"  Binary:      {BIN}")
    print(f"  Backup:      {'EXISTS' if BACKUP.exists() else 'NONE'}")
    print(f"  je@{hex(JE_FOFF)}: {je_bytes.hex()}  ({'PATCHED' if patched else 'ORIGINAL'})")
    print(f"  entry@{hex(WKL_ENTRY_FOFF)}: {entry_bytes.hex()}")
    print(f"  cave@{hex(CAVE_FOFF)}: {cave_bytes.hex()}  ({'HAS CODE' if cave_bytes != b'\\x00'*4 else 'EMPTY'})")
    return patched

def do_undo():
    if not BACKUP.exists():
        print("  ERROR: No backup found at", BACKUP)
        print("  Cannot undo — binary was never patched by this tool")
        sys.exit(1)

    if os.geteuid() != 0:
        print("  ERROR: Need root to write to", BIN)
        sys.exit(1)

    shutil.copy2(BACKUP, BIN)
    print(f"  [+] Restored {BIN} from {BACKUP}")
    print(f"  [+] TLS keylog patch removed")

def build_stub(data):
    """
    Build x86-64 shellcode stub for the code cave.

    The stub is called by a CALL instruction replacing the je in writeKeyLog.
    On entry: RAX = *tls.Config (the receiver)
    Goal: ensure 0x138(%rax) points to a valid io.Writer before returning.

    Approach: use Linux write(2) syscall directly via a raw fd stored in a global.
    Build a minimal Go io.Writer interface around a file descriptor:
      - itab ptr: use the real *os.File itab from the binary
      - data ptr: a fake os.File struct with just the fd field set

    Simpler: store the fd in a .data global; patch writeKeyLog to use a
    custom Write function we put in the cave that just does write(2) syscall.

    The stub structure:
      [0..7]:   int64 global_fd = 0             (initialized to 0 = not open)
      [8..23]:  Write itab slot (16 bytes)       (our Write func ptr)
      [24..31]: os.File ptr (fake, just fd slot) (points to global_fd)
      [32..]:   the actual stub code

    Cave VA = CAVE_FOFF (VA == file offset for this binary's load segment)
    """
    cave_va = CAVE_FOFF   # VA == file offset for this binary (PIE base 0 link)

    # Offsets within cave
    OFF_FD       = 0    # int64: the open fd (-1 = not open, 0 = not init)
    OFF_ITAB     = 8    # [2]uint64: itab for *rawFileWriter (our fake io.Writer)
    OFF_WRITER   = 24   # *rawFileWriter struct
    OFF_WRITE_FN = 32   # our Write(p []byte) function
    OFF_STUB     = 96   # main stub (called from je patch)
    OFF_PATH     = 200  # /tmp/hg_tls.keys\0

    stub = bytearray(CAVE_SIZE)

    # Store the keylog path string
    path_off = OFF_PATH
    stub[path_off:path_off+len(KEYLOG_PATH)] = KEYLOG_PATH

    # ------------------------------------------------------------------
    # Write function at OFF_WRITE_FN:
    # Go register ABI: func (w *rawWriter) Write(p []byte) (n int, err error)
    # RAX = *rawWriter, RBX = p.ptr, RCX = p.len
    # Returns: RAX = n, RBX = 0 (err)
    # We do: syscall SYS_WRITE(fd, p.ptr, p.len) -> n
    # ------------------------------------------------------------------
    wf = bytearray()
    # push rbp; mov rbp,rsp
    wf += b'\x55\x48\x89\xe5'
    # mov rdi, [rax+0] (fd from *rawWriter)
    wf += b'\x48\x8b\x38'
    # mov rsi, rbx (buf ptr)
    wf += b'\x48\x89\xde'
    # mov rdx, rcx (length)
    wf += b'\x48\x89\xca'
    # mov rax, 1 (SYS_WRITE)
    wf += b'\x48\xc7\xc0\x01\x00\x00\x00'
    # syscall
    wf += b'\x0f\x05'
    # mov rbx, 0 (no error)
    wf += b'\x48\x31\xdb'
    # pop rbp; ret
    wf += b'\x5d\xc3'
    stub[OFF_WRITE_FN:OFF_WRITE_FN+len(wf)] = wf

    write_fn_va = cave_va + OFF_WRITE_FN

    # itab: [typeptr(8), ifaceptr(8), ...methods...]
    # For a minimal io.Writer itab we need: [0]=type, [1]=iface, [2]=Write ptr
    # Go only checks the method pointer at [2] (Write), so:
    stub[OFF_ITAB:OFF_ITAB+8]   = struct.pack('<Q', 0)             # type (unused)
    stub[OFF_ITAB+8:OFF_ITAB+16] = struct.pack('<Q', write_fn_va)  # Write method

    itab_va     = cave_va + OFF_ITAB
    writer_va   = cave_va + OFF_WRITER
    fd_va       = cave_va + OFF_FD

    # rawWriter struct at OFF_WRITER: just one int64 (fd)
    # points to OFF_FD
    stub[OFF_WRITER:OFF_WRITER+8] = struct.pack('<Q', fd_va)

    # ------------------------------------------------------------------
    # Main stub at OFF_STUB (called from writeKeyLog via CALL replacing je)
    # On entry: RAX = *tls.Config, return address on stack
    # Goal: set 0x138(%rax) = itab_va (ptr to our io.Writer interface)
    #        set 0x140(%rax) = writer_va (data ptr)
    #        if fd not open yet: open the file
    # ------------------------------------------------------------------
    ms = bytearray()
    ms_va = cave_va + OFF_STUB

    # Save registers we'll clobber
    ms += b'\x53'               # push rbx
    ms += b'\x41\x54'           # push r12
    ms += b'\x41\x55'           # push r13

    # Save rax (*Config) in r12
    ms += b'\x49\x89\xc4'      # mov r12, rax

    # Check if fd is already open: mov rbx, [fd_va]
    fd_rip_off = fd_va - (ms_va + len(ms) + 7)
    ms += b'\x48\x8b\x1d' + struct.pack('<i', fd_rip_off)   # mov rbx, [rip+fd_rip_off]

    # test rbx,rbx; jnz already_open
    ms += b'\x48\x85\xdb'      # test rbx, rbx
    jnz_placeholder = len(ms)
    ms += b'\x75\x00'           # jnz (fill in later)

    # Open the file: syscall open(path, O_WRONLY|O_CREAT|O_APPEND, 0600)
    # SYS_OPEN = 2
    path_va = cave_va + OFF_PATH
    path_rip_off = path_va - (ms_va + len(ms) + 7)
    ms += b'\x48\x8d\x3d' + struct.pack('<i', path_rip_off)  # lea rdi, [rip+path]
    ms += b'\x48\xc7\xc6\x41\x04\x00\x00'  # mov rsi, O_WRONLY|O_CREAT|O_APPEND = 0x441
    ms += b'\x48\xc7\xc2\x80\x01\x00\x00'  # mov rdx, 0600 (octal) = 0x180
    ms += b'\x48\xc7\xc0\x02\x00\x00\x00'  # mov rax, SYS_OPEN=2
    ms += b'\x0f\x05'                        # syscall -> rax=fd

    # Store fd in global
    fd_store_rip_off = fd_va - (ms_va + len(ms) + 7)
    ms += b'\x48\x89\x05' + struct.pack('<i', fd_store_rip_off)  # mov [rip+off], rax
    ms += b'\x48\x89\xc3'   # mov rbx, rax (rbx = fd for jnz target)

    # Patch jnz offset
    already_open_pos = len(ms)
    ms[jnz_placeholder+1] = already_open_pos - (jnz_placeholder + 2)

    # already_open: rbx = fd
    # Set 0x138(%r12) = itab_va (interface type word)
    itab_rip_off = itab_va - (ms_va + len(ms) + 7)
    ms += b'\x48\x8d\x05' + struct.pack('<i', itab_rip_off)  # lea rax, [rip+itab]
    ms += b'\x49\x89\x84\x24\x38\x01\x00\x00'               # mov [r12+0x138], rax

    # Set 0x140(%r12) = writer_va (data word)
    writer_rip_off = writer_va - (ms_va + len(ms) + 7)
    ms += b'\x48\x8d\x05' + struct.pack('<i', writer_rip_off) # lea rax, [rip+writer]
    ms += b'\x49\x89\x84\x24\x40\x01\x00\x00'                # mov [r12+0x140], rax

    # Restore rax = *Config, pop saved regs, ret
    ms += b'\x4c\x89\xe0'   # mov rax, r12
    ms += b'\x41\x5d'       # pop r13
    ms += b'\x41\x5c'       # pop r12
    ms += b'\x5b'           # pop rbx
    ms += b'\xc3'           # ret

    stub[OFF_STUB:OFF_STUB+len(ms)] = ms

    # ------------------------------------------------------------------
    # Compute the CALL rel32 to replace the 6-byte je at JE_FOFF
    # CALL is 5 bytes: e8 <rel32>
    # call_site_va = JE_FOFF (VA == foff for this binary)
    # after_call_va = JE_FOFF + 5
    # rel32 = stub_va - after_call_va
    # ------------------------------------------------------------------
    call_site_va = JE_FOFF
    after_call   = call_site_va + 5
    stub_va      = ms_va
    rel32 = stub_va - after_call
    call_bytes = b'\xe8' + struct.pack('<i', rel32) + b'\x90'  # call + 1 nop

    return bytes(stub), call_bytes


def do_patch():
    if os.geteuid() != 0:
        print("  ERROR: Need root to write to", BIN)
        sys.exit(1)

    data = read_binary()

    # Verify not already patched
    je_bytes = bytes(data[JE_FOFF:JE_FOFF+6])
    if je_bytes != JE_ORIG:
        print(f"  [!] Already patched (je bytes = {je_bytes.hex()})")
        print(f"  Run with --verify to check state, --undo to restore")
        sys.exit(1)

    # Verify cave is empty
    cave = bytes(data[CAVE_FOFF:CAVE_FOFF+32])
    if any(b != 0 for b in cave[:16]):
        print(f"  [!] Code cave not empty: {cave[:16].hex()}")
        sys.exit(1)

    print(f"  [*] Building stub...")
    stub, call_bytes = build_stub(data)
    print(f"  [*] Call bytes: {call_bytes.hex()}  (replaces je at {hex(JE_FOFF)})")
    print(f"  [*] Stub size: {len(stub)} bytes -> cave at {hex(CAVE_FOFF)}")

    # Backup
    if not BACKUP.exists():
        shutil.copy2(BIN, BACKUP)
        print(f"  [*] Backed up to {BACKUP}")

    # Write stub into cave
    data[CAVE_FOFF:CAVE_FOFF+len(stub)] = stub

    # Replace je with call
    data[JE_FOFF:JE_FOFF+6] = call_bytes

    write_binary(data)
    print(f"  [+] Patch applied")
    print(f"  [+] TLS keys will be written to /tmp/hg_tls.keys")
    print(f"  [+] Restart Windsurf language server to activate")


if __name__ == "__main__":
    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │    KeyLog Binary Patcher                     │")
    print("  └─────────────────────────────────────────────┘")
    print()

    mode = sys.argv[1] if len(sys.argv) > 1 else "--patch"

    if mode == "--verify":
        patched = verify()
        sys.exit(0 if patched else 1)

    elif mode == "--undo":
        print("  [*] Restoring original binary...")
        do_undo()

    elif mode in ("--patch", "--apply"):
        print("  [*] Applying keylog patch...")
        do_patch()

    else:
        print(f"  Usage: {sys.argv[0]} [--patch|--undo|--verify]")
        sys.exit(1)
