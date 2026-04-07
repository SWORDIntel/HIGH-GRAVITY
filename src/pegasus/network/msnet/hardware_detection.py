"""
Hardware Acceleration Detection

Automatically detects available hardware accelerators for compression.
QATzip is only used when Intel QAT hardware is actually present.
"""

import os
import subprocess
from typing import Optional, Dict

# Cache hardware detection results
_hardware_cache: Optional[Dict[str, bool]] = None


def detect_qat_hardware() -> bool:
    """
    Detect if Intel QAT hardware is present.
    
    Checks multiple methods:
    1. QATzip library hardware detection
    2. System device files (/dev/qat_*)
    3. Kernel modules (qat_*)
    4. PCI devices (QAT devices)
    
    Returns:
        True if QAT hardware detected, False otherwise
    """
    global _hardware_cache
    
    # Check cache
    if _hardware_cache is not None:
        return _hardware_cache.get("qat", False)
    
    _hardware_cache = {}
    
    # Method 1: Try QATzip library detection
    try:
        import qatzip
        if hasattr(qatzip, 'is_hardware_available'):
            _hardware_cache["qat"] = qatzip.is_hardware_available()
            return _hardware_cache["qat"]
        elif hasattr(qatzip, 'check_hardware'):
            _hardware_cache["qat"] = qatzip.check_hardware()
            return _hardware_cache["qat"]
        elif hasattr(qatzip, 'QzCompress'):
            # Try to initialize - will fail if no hardware
            try:
                test = qatzip.QzCompress()
                _hardware_cache["qat"] = True
                return True
            except Exception:
                _hardware_cache["qat"] = False
    except ImportError:
        pass
    
    # Method 2: Check for QAT device files
    qat_devices = [
        "/dev/qat_adf_ctl",
        "/dev/qat_dev0",
        "/dev/qat_dev1",
    ]
    for device in qat_devices:
        if os.path.exists(device):
            _hardware_cache["qat"] = True
            return True
    
    # Method 3: Check for QAT kernel modules
    try:
        result = subprocess.run(
            ["lsmod"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        if result.returncode == 0:
            modules = result.stdout.lower()
            if any(module in modules for module in ["qat", "intel_qat", "qat_c62x"]):
                _hardware_cache["qat"] = True
                return True
    except Exception:
        pass
    
    # Method 4: Check PCI devices for QAT
    try:
        result = subprocess.run(
            ["lspci"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            pci_output = result.stdout.lower()
            # Intel QAT device IDs
            qat_ids = ["37c8", "19e2", "19e3", "4940", "4942", "4944"]
            if any(qat_id in pci_output for qat_id in qat_ids):
                _hardware_cache["qat"] = True
                return True
    except Exception:
        pass
    
    # No hardware detected
    _hardware_cache["qat"] = False
    return False


def get_available_accelerators() -> Dict[str, bool]:
    """
    Get all available hardware accelerators.
    
    Returns:
        Dictionary of accelerator name -> availability
    """
    return {
        "qat": detect_qat_hardware(),
        # Future: Add other accelerators (GPU, FPGA, etc.)
    }


def has_compression_accelerator() -> bool:
    """
    Check if any compression accelerator is available.
    
    Returns:
        True if any accelerator available
    """
    accelerators = get_available_accelerators()
    return any(accelerators.values())


# Update QATZIP_HARDWARE_AVAILABLE on import
try:
    from src.pegasus.network.msnet.hardware_detection import detect_qat_hardware
    QATZIP_HARDWARE_AVAILABLE = detect_qat_hardware()
except Exception:
    QATZIP_HARDWARE_AVAILABLE = False
