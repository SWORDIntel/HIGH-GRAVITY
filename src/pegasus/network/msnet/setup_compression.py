#!/usr/bin/env python3
"""
MEMSHADOW Compression Setup Helper

Helps users set up compression binaries (kanzi/QATzip) for MEMSHADOW protocol.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def check_compression_binaries():
    """Check which compression binaries are available"""
    binaries_dir = Path(__file__).parent.parent / "external" / "binaries"
    arch = platform.machine()
    
    results = {
        "gzip": True,  # Always available
        "kanzi": False,
        "qatzip": False,
    }
    
    # Check kanzi
    kanzi_binary = binaries_dir / f"kanzi-linux-{arch}"
    if kanzi_binary.exists() and kanzi_binary.is_file():
        results["kanzi"] = True
    else:
        # Check system PATH
        try:
            result = subprocess.run(["which", "kanzi"], capture_output=True, timeout=1)
            if result.returncode == 0:
                results["kanzi"] = True
        except Exception:
            pass
    
    # Check qatzip
    qatzip_binary = binaries_dir / f"qatzip-linux-{arch}"
    if qatzip_binary.exists() and qatzip_binary.is_file():
        # Also check for hardware
        if os.path.exists("/dev/qat_adf_ctl"):
            results["qatzip"] = True
    else:
        # Check system PATH
        try:
            result = subprocess.run(["which", "qatzip"], capture_output=True, timeout=1)
            if result.returncode == 0:
                if os.path.exists("/dev/qat_adf_ctl"):
                    results["qatzip"] = True
        except Exception:
            pass
    
    return results


def print_setup_status():
    """Print compression setup status"""
    print("MEMSHADOW Compression Setup Status")
    print("=" * 50)
    
    results = check_compression_binaries()
    
    print("\nAvailable Compression:")
    print(f"  ✓ Gzip:   Always available (stdlib/library)")
    print(f"  {'✓' if results['kanzi'] else '✗'} Kanzi:   {'Available' if results['kanzi'] else 'Not found (build from source)'}")
    print(f"  {'✓' if results['qatzip'] else '✗'} QATzip:  {'Available' if results['qatzip'] else 'Not found (build from source + hardware)'}")
    
    print("\nProtocol Behavior:")
    if results["qatzip"]:
        print("  → Using QATzip (best compression)")
    elif results["kanzi"]:
        print("  → Using Kanzi (better compression)")
    else:
        print("  → Using Gzip (standard compression)")
    
    if not results["kanzi"] or not results["qatzip"]:
        print("\n⚠️  To enable better compression:")
        print("  See: external/binaries/BUILD_INSTRUCTIONS.md")
        print("  Quick: git clone https://github.com/flanglet/kanzi-cpp.git && cd kanzi-cpp && make")
    
    print("\n✅ Protocol is ready to use (gzip always available)")


if __name__ == "__main__":
    print_setup_status()
