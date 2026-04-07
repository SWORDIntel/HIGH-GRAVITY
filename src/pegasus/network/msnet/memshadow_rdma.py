"""
MEMSHADOW Protocol - RDMA Support

RDMA (Remote Direct Memory Access) support for ultra-low latency
and high-throughput local communication between AI nodes.
"""

import os
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from enum import IntEnum


class RDMAType(IntEnum):
    """RDMA types"""
    NONE = 0
    INFINIBAND = 1  # InfiniBand
    ROCE = 2  # RDMA over Converged Ethernet
    IWARP = 3  # Internet Wide Area RDMA Protocol


@dataclass
class RDMADevice:
    """RDMA device information"""
    device_name: str
    rdma_type: RDMAType
    guid: str  # Device GUID
    available: bool = False
    max_mr_size: int = 0  # Maximum memory region size
    max_qp: int = 0  # Maximum queue pairs


class RDMADetector:
    """
    RDMA device detection
    
    Detects available RDMA hardware.
    """
    
    def __init__(self):
        self.devices: Dict[str, RDMADevice] = {}
        self.detected = False
    
    def detect_devices(self) -> List[RDMADevice]:
        """
        Detect available RDMA devices
        
        Returns:
            List of detected RDMA devices
        """
        devices = []
        
        # Check for InfiniBand devices
        ib_devices = self._detect_infiniband()
        devices.extend(ib_devices)
        
        # Check for RoCE devices
        roce_devices = self._detect_roce()
        devices.extend(roce_devices)
        
        # Check for iWARP devices
        iwarp_devices = self._detect_iwarp()
        devices.extend(iwarp_devices)
        
        self.detected = True
        return devices
    
    def _detect_infiniband(self) -> List[RDMADevice]:
        """Detect InfiniBand devices"""
        devices = []
        
        # Check for InfiniBand devices in /sys/class/infiniband
        ib_path = "/sys/class/infiniband"
        if os.path.exists(ib_path):
            for device_name in os.listdir(ib_path):
                device = RDMADevice(
                    device_name=device_name,
                    rdma_type=RDMAType.INFINIBAND,
                    guid=self._get_device_guid(ib_path, device_name),
                    available=True
                )
                devices.append(device)
                self.devices[device_name] = device
        
        return devices
    
    def _detect_roce(self) -> List[RDMADevice]:
        """Detect RoCE devices"""
        devices = []
        
        # RoCE devices appear as Ethernet devices with RDMA capability
        # Check /sys/class/net for devices with rdma_cap
        net_path = "/sys/class/net"
        if os.path.exists(net_path):
            for device_name in os.listdir(net_path):
                rdma_cap_path = os.path.join(net_path, device_name, "device", "rdma_cap")
                if os.path.exists(rdma_cap_path):
                    device = RDMADevice(
                        device_name=device_name,
                        rdma_type=RDMAType.ROCE,
                        guid=self._get_device_guid(net_path, device_name),
                        available=True
                    )
                    devices.append(device)
                    self.devices[device_name] = device
        
        return devices
    
    def _detect_iwarp(self) -> List[RDMADevice]:
        """Detect iWARP devices"""
        devices = []
        
        # iWARP devices are typically Ethernet devices
        # Would check for iWARP capability
        # Placeholder implementation
        
        return devices
    
    def _get_device_guid(self, base_path: str, device_name: str) -> str:
        """Get device GUID"""
        guid_path = os.path.join(base_path, device_name, "node_guid")
        if os.path.exists(guid_path):
            try:
                with open(guid_path, 'r') as f:
                    return f.read().strip()
            except Exception:
                pass
        return "unknown"
    
    def is_available(self) -> bool:
        """Check if RDMA is available"""
        if not self.detected:
            self.detect_devices()
        return len(self.devices) > 0
    
    def get_preferred_device(self) -> Optional[RDMADevice]:
        """Get preferred RDMA device"""
        if not self.devices:
            return None
        
        # Prefer InfiniBand, then RoCE, then iWARP
        for rdma_type in [RDMAType.INFINIBAND, RDMAType.ROCE, RDMAType.IWARP]:
            for device in self.devices.values():
                if device.rdma_type == rdma_type and device.available:
                    return device
        
        return None


class RDMATransport:
    """
    RDMA transport implementation
    
    Provides RDMA-based zero-copy communication.
    """
    
    def __init__(self, device: Optional[RDMADevice] = None):
        self.device = device
        self.initialized = False
        self.queue_pairs: Dict[str, object] = {}  # peer_id -> queue pair
    
    def initialize(self) -> bool:
        """Initialize RDMA transport"""
        if not self.device or not self.device.available:
            return False
        
        # Would initialize RDMA verbs/API here
        # Placeholder - would use librdmacm or similar
        self.initialized = True
        return True
    
    def create_queue_pair(self, peer_id: str) -> bool:
        """Create queue pair for peer"""
        if not self.initialized:
            return False
        
        # Would create RDMA queue pair
        # Placeholder
        self.queue_pairs[peer_id] = object()  # Placeholder QP object
        return True
    
    def send_rdma(
        self,
        peer_id: str,
        local_addr: int,
        remote_addr: int,
        length: int
    ) -> bool:
        """
        Send data using RDMA write
        
        Args:
            peer_id: Peer identifier
            local_addr: Local memory address
            remote_addr: Remote memory address
            length: Data length
        
        Returns:
            True if successful
        """
        if peer_id not in self.queue_pairs:
            return False
        
        # Would perform RDMA write operation
        # Placeholder
        return True
    
    def receive_rdma(
        self,
        peer_id: str,
        local_addr: int,
        length: int
    ) -> bool:
        """
        Receive data using RDMA read
        
        Args:
            peer_id: Peer identifier
            local_addr: Local memory address
            length: Data length
        
        Returns:
            True if successful
        """
        if peer_id not in self.queue_pairs:
            return False
        
        # Would perform RDMA read operation
        # Placeholder
        return True
    
    def register_memory_region(self, addr: int, length: int) -> Optional[int]:
        """
        Register memory region for RDMA
        
        Returns:
            Memory region handle or None
        """
        if not self.initialized:
            return None
        
        # Would register memory region with RDMA
        # Placeholder
        return 0  # Placeholder MR handle
    
    def deregister_memory_region(self, mr_handle: int):
        """Deregister memory region"""
        # Would deregister memory region
        pass


class RDMAManager:
    """
    RDMA manager
    
    Coordinates RDMA operations for high-performance communication.
    """
    
    def __init__(self):
        self.detector = RDMADetector()
        self.transport: Optional[RDMATransport] = None
        self.enabled = False
    
    def enable(self) -> bool:
        """Enable RDMA if available"""
        devices = self.detector.detect_devices()
        if not devices:
            return False
        
        preferred_device = self.detector.get_preferred_device()
        if not preferred_device:
            return False
        
        self.transport = RDMATransport(preferred_device)
        if self.transport.initialize():
            self.enabled = True
            return True
        
        return False
    
    def disable(self):
        """Disable RDMA"""
        self.enabled = False
        self.transport = None
    
    def is_enabled(self) -> bool:
        """Check if RDMA is enabled"""
        return self.enabled and self.transport is not None
    
    def get_device_info(self) -> Optional[RDMADevice]:
        """Get RDMA device information"""
        if self.transport:
            return self.transport.device
        return None
