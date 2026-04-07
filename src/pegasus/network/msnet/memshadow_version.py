"""
MEMSHADOW Protocol Version Compatibility

Handles version negotiation, backward compatibility, and upgrade mechanisms.
"""

import logging
import struct
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger(__name__)


class VersionCompatibility(IntEnum):
    """Version compatibility result"""
    COMPATIBLE = 0
    INCOMPATIBLE_MAJOR = 1  # Different major version - log but don't respond
    BACKWARD_COMPATIBLE = 2  # Higher minor version - suggest upgrade
    UPGRADE_REQUIRED = 3  # Lower version - requires upgrade


@dataclass
class ProtocolVersion:
    """Protocol version information"""
    major: int
    minor: int
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"
    
    def pack(self) -> bytes:
        """Pack version to 2 bytes (major:1, minor:1)"""
        return struct.pack(">BB", self.major, self.minor)
    
    @classmethod
    def unpack(cls, data: bytes) -> "ProtocolVersion":
        """Unpack version from 2 bytes"""
        if len(data) < 2:
            raise ValueError("Version data too short")
        major, minor = struct.unpack(">BB", data[:2])
        return cls(major=major, minor=minor)
    
    def compare(self, other: "ProtocolVersion") -> VersionCompatibility:
        """
        Compare versions and return compatibility result
        
        Rules:
        - Same major version: Compatible
        - Different major version: Incompatible (log but don't respond)
        - Higher minor version: Backward compatible (suggest upgrade)
        - Lower version: Upgrade required
        """
        if self.major == other.major:
            if self.minor == other.minor:
                return VersionCompatibility.COMPATIBLE
            elif self.minor > other.minor:
                return VersionCompatibility.BACKWARD_COMPATIBLE
            else:
                return VersionCompatibility.UPGRADE_REQUIRED
        else:
            return VersionCompatibility.INCOMPATIBLE_MAJOR


# Current protocol version
CURRENT_VERSION = ProtocolVersion(major=3, minor=1)


class VersionManager:
    """
    Manages protocol version compatibility and upgrade mechanisms
    
    Version 3.1+ behavior:
    - Log but don't respond to newer versions
    - Support backward compatibility for older versions
    - Suggest upgrade, stage for 12h, then send binary upgrade
    - Keep old version as fallback if connection fails
    """
    
    def __init__(self, current_version: ProtocolVersion = CURRENT_VERSION):
        self.current_version = current_version
        self._upgrade_staging: Dict[str, Tuple[float, bytes]] = {}  # peer_id -> (staged_time, binary_data)
        self._upgrade_alerts: Dict[str, bool] = {}  # peer_id -> alert_sent
        self._fallback_versions: Dict[str, ProtocolVersion] = {}  # peer_id -> fallback_version
        
    def check_compatibility(self, peer_version: ProtocolVersion) -> VersionCompatibility:
        """Check compatibility with peer version"""
        return self.current_version.compare(peer_version)
    
    def handle_version_mismatch(
        self,
        peer_id: str,
        peer_version: ProtocolVersion,
        peer_address: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Handle version mismatch
        
        Returns:
            Tuple of (should_respond, upgrade_message)
        """
        compat = self.check_compatibility(peer_version)
        
        if compat == VersionCompatibility.COMPATIBLE:
            return True, None
        
        elif compat == VersionCompatibility.INCOMPATIBLE_MAJOR:
            # Different major version - log but don't respond
            logger.warning(
                f"Peer {peer_id} has incompatible major version {peer_version} "
                f"(we are {self.current_version}). Not responding."
            )
            return False, None
        
        elif compat == VersionCompatibility.BACKWARD_COMPATIBLE:
            # Higher minor version - suggest upgrade
            logger.info(
                f"Peer {peer_id} has newer version {peer_version} "
                f"(we are {self.current_version}). Suggesting upgrade."
            )
            return True, f"Upgrade recommended: {peer_version} > {self.current_version}"
        
        elif compat == VersionCompatibility.UPGRADE_REQUIRED:
            # Lower version - requires upgrade
            logger.info(
                f"Peer {peer_id} has older version {peer_version} "
                f"(we are {self.current_version}). Upgrade required."
            )
            
            # Stage upgrade for 12 hours
            import time
            if peer_id not in self._upgrade_staging:
                # Start staging period
                self._upgrade_staging[peer_id] = (time.time(), None)
                self._upgrade_alerts[peer_id] = False
                logger.info(f"Staging upgrade for peer {peer_id} (12 hour grace period)")
            
            staged_time, binary_data = self._upgrade_staging[peer_id]
            elapsed = time.time() - staged_time
            
            # Send alert to node owner after 1 hour
            if elapsed > 3600 and not self._upgrade_alerts.get(peer_id):
                self._upgrade_alerts[peer_id] = True
                logger.warning(
                    f"UPGRADE ALERT: Peer {peer_id} (version {peer_version}) "
                    f"needs upgrade to {self.current_version}. "
                    f"Binary upgrade will be sent in {12*3600 - elapsed:.0f} seconds."
                )
            
            # After 12 hours, send binary upgrade
            if elapsed > 12 * 3600:
                if binary_data is None:
                    # Generate binary upgrade (placeholder - actual implementation depends on platform)
                    binary_data = self._generate_upgrade_binary(peer_version, self.current_version)
                    self._upgrade_staging[peer_id] = (staged_time, binary_data)
                
                return True, f"UPGRADE_REQUIRED:{self.current_version}:{binary_data.hex()}"
            
            return True, f"UPGRADE_PENDING:{self.current_version}:{int(12*3600 - elapsed)}"
        
        return True, None
    
    def _generate_upgrade_binary(
        self,
        from_version: ProtocolVersion,
        to_version: ProtocolVersion
    ) -> bytes:
        """
        Generate binary upgrade package
        
        This is a placeholder - actual implementation would:
        1. Package the new binary for the peer's platform
        2. Include upgrade instructions
        3. Sign the upgrade package
        4. Compress if needed
        """
        # Placeholder: return version info as binary
        upgrade_info = f"UPGRADE:{from_version}->{to_version}".encode()
        return upgrade_info
    
    def register_fallback_version(self, peer_id: str, version: ProtocolVersion):
        """Register fallback version for peer (if upgrade fails)"""
        self._fallback_versions[peer_id] = version
        logger.info(f"Registered fallback version {version} for peer {peer_id}")
    
    def get_fallback_version(self, peer_id: str) -> Optional[ProtocolVersion]:
        """Get fallback version for peer"""
        return self._fallback_versions.get(peer_id)
    
    def should_use_fallback(self, peer_id: str) -> bool:
        """Check if we should use fallback version for peer"""
        return peer_id in self._fallback_versions


# Global version manager instance
_version_manager: Optional[VersionManager] = None


def get_version_manager() -> VersionManager:
    """Get global version manager instance"""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager
