"""
MEMSHADOW Protocol Version Information
"""

__version__ = "3.1.0"
__version_tuple__ = (3, 1, 0)

# Version compatibility information
MINIMUM_COMPATIBLE_VERSION = "3.0.0"
SUPPORTED_VERSIONS = ["3.0.x", "3.1.x"]

# Protocol version constants
PROTOCOL_VERSION_MAJOR = 3
PROTOCOL_VERSION_MINOR = 1
PROTOCOL_VERSION_PATCH = 0

def get_version():
    """Get the current version string"""
    return __version__

def get_version_tuple():
    """Get the current version as a tuple"""
    return __version_tuple__

def is_compatible(version_string):
    """Check if a version string is compatible"""
    # For now, only v3.0.x is compatible
    return version_string.startswith("3.0.")
