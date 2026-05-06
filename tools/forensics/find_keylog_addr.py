#!/usr/bin/env python3
"""
Finds the address of crypto/tls.(*Config).writeKeyLog in the Go binary
by parsing the Go pclntab (function table) embedded in the binary.
"""
import struct
import sys

BIN = "/usr/share/windsurf-next/resources/app/extensions/windsurf/bin/language_server_linux_x64"

with open(BIN, 'rb') as f:
    data = f.read()

# Parse ELF to find load address and section info
def read_elf_sections(data):
    # ELF header
    e_shoff   = struct.unpack_from('<Q', data, 0x28)[0]
    e_shentsize = struct.unpack_from('<H', data, 0x3A)[0]
    e_shnum   = struct.unpack_from('<H', data, 0x3C)[0]
    e_shstrndx = struct.unpack_from('<H', data, 0x3E)[0]

    # String table section
    shstr_off = e_shoff + e_shstrndx * e_shentsize
    shstr_foff = struct.unpack_from('<Q', data, shstr_off + 24)[0]
    shstr_size = struct.unpack_from('<Q', data, shstr_off + 32)[0]
    shstrtab = data[shstr_foff:shstr_foff+shstr_size]

    sections = {}
    for i in range(e_shnum):
        sh = data[e_shoff + i*e_shentsize : e_shoff + (i+1)*e_shentsize]
        name_off = struct.unpack_from('<I', sh, 0)[0]
        name = shstrtab[name_off:shstrtab.index(b'\x00', name_off)].decode()
        sh_addr   = struct.unpack_from('<Q', sh, 16)[0]
        sh_offset = struct.unpack_from('<Q', sh, 24)[0]
        sh_size   = struct.unpack_from('<Q', sh, 32)[0]
        sections[name] = (sh_addr, sh_offset, sh_size)
    return sections

sections = read_elf_sections(data)

# Go pclntab is in .gopclntab section
if '.gopclntab' not in sections:
    print("No .gopclntab section found")
    sys.exit(1)

pclntab_va, pclntab_off, pclntab_size = sections['.gopclntab']
pclntab = data[pclntab_off:pclntab_off+pclntab_size]
print(f".gopclntab: VA={hex(pclntab_va)} size={pclntab_size}")

# Go 1.20+ pclntab magic
magic = struct.unpack_from('<I', pclntab, 0)[0]
print(f"pclntab magic: {hex(magic)}")

# Go 1.18+ format (magic 0xFFFFFAFF or 0xFFFFFAFE)
# Header: magic(4) pad(2) minLC(1) ptrSize(1) nfunc(8) nfiles(8) ...
if magic not in (0xFFFFFAFF, 0xFFFFFAFE, 0xFFFFFAFD):
    print(f"Unknown pclntab magic {hex(magic)}, trying Go 1.2 format")

ptr_size = pclntab[7]
print(f"Pointer size: {ptr_size}")

# Parse function table
# Go 1.18+ header is 8 fields of ptrSize
header_size = 8 * ptr_size
nfunc = struct.unpack_from('<Q', pclntab, 8)[0]
print(f"Number of functions: {nfunc}")

# Go text base from ELF
text_va, text_off, _ = sections.get('.text', (0,0,0))
print(f".text: VA={hex(text_va)}")

# Function table starts after header
# Each entry: funcoff(4), nameoff(4) in Go 1.18+ 
# Actually: (textAddr, funcDataOff) pairs
ftab_off = header_size
target_names = [b"writeKeyLog", b"crypto/tls"]

found = []
# Scan pclntab for function name strings
# In Go 1.18+, func names are stored in .funcnametab
funcnametab_va, funcnametab_off, funcnametab_size = sections.get('.funcnametab', (0,0,0))
if funcnametab_off:
    funcnames = data[funcnametab_off:funcnametab_off+funcnametab_size]
    print(f"\nScanning .funcnametab ({funcnametab_size} bytes) for writeKeyLog...")
    offset = 0
    while offset < len(funcnames):
        nul = funcnames.find(b'\x00', offset)
        if nul < 0:
            break
        name = funcnames[offset:nul]
        if b"writeKeyLog" in name or b"KeyLogWriter" in name:
            print(f"  Found: '{name.decode()}' at funcnametab offset {hex(offset)}")
            found.append((offset, name.decode()))
        offset = nul + 1
else:
    print("No .funcnametab section, scanning pclntab directly...")
    # Fallback: scan pclntab for the string
    idx = 0
    while True:
        idx = pclntab.find(b"writeKeyLog", idx)
        if idx < 0:
            break
        # Find start of null-terminated string
        start = pclntab.rfind(b'\x00', 0, idx) + 1
        end = pclntab.find(b'\x00', idx)
        name = pclntab[start:end]
        print(f"  Found: '{name.decode()}' at pclntab offset {hex(idx)}")
        found.append((idx, name.decode()))
        idx += 1

# Now find the corresponding function PC
# Go 1.18: _func entries in .gofunc, indexed from functab
gofunc_va, gofunc_off, gofunc_size = sections.get('.gofunc', (0,0,0))
functab_va, functab_off, functab_size = sections.get('.go.func', sections.get('go:func.*', (0,0,0)))

print(f"\n.gofunc: VA={hex(gofunc_va)} off={hex(gofunc_off)} size={gofunc_size}")

# Try to find function PCs by scanning pclntab function table
# pclntab format (Go 1.18):
# [header 64 bytes][nfunc * {funcoff uint32, nameoff uint32}][...func data...]
print(f"\nScanning function table for writeKeyLog entries...")

# Function table in pclntab: pairs of (text_offset, func_data_offset)
# Text offset is relative to runtime.text
runtime_text_va = text_va  # approximation

# Parse the function table
# offset to functab in pclntab
func_table_start = struct.unpack_from('<Q', pclntab, ptr_size)[0]  # cutab offset
# Actually the function list starts right after the header
# Let's try reading nfunc entries as (uint32 text_off, uint32 funcdata_off)

print(f"\nTop 5 function entries from pclntab:")
entry_off = 8 * ptr_size  # skip header
for i in range(min(5, nfunc)):
    if entry_off + 8 > len(pclntab):
        break
    text_off = struct.unpack_from('<I', pclntab, entry_off)[0]
    func_off = struct.unpack_from('<I', pclntab, entry_off + 4)[0]
    pc = runtime_text_va + text_off
    print(f"  func[{i}]: text_off={hex(text_off)} PC={hex(pc)} funcdata_off={hex(func_off)}")
    entry_off += 8

# Better: search for the nameoff that points to "writeKeyLog" string
# and trace back to find the PC
for name_file_off, name in found:
    name_pclntab_off = name_file_off  # relative to funcnametab start
    print(f"\nLooking for _func with nameoff pointing to '{name}'")
    # nameoff is relative to funcnametab VA
    target_nameoff = name_file_off  # this is the offset within funcnametab

    # Scan _func entries in pclntab
    # Each _func: pc(4) nameoff(4) args(4) deferreturn(4) pcfile(4) pcln(4) npcdata(4) cuOffset(4) ...
    # We look for nameoff == target_nameoff
    entry_off = 8 * ptr_size
    for i in range(nfunc):
        if entry_off + 8 > len(pclntab):
            break
        text_off = struct.unpack_from('<I', pclntab, entry_off)[0]
        func_data_off = struct.unpack_from('<I', pclntab, entry_off + 4)[0]
        entry_off += 8
        
        if func_data_off + 8 > len(pclntab):
            continue
        
        # _func.nameoff is at offset 4 within the _func struct
        nameoff_val = struct.unpack_from('<I', pclntab, func_data_off + 4)[0]
        
        if nameoff_val == target_nameoff:
            pc = runtime_text_va + text_off
            print(f"  FOUND! PC={hex(pc)} (text_off={hex(text_off)} nameoff={hex(nameoff_val)})")
            print(f"  GDB: break *{hex(pc)}")
            print(f"  GDB: break *{pc}")
