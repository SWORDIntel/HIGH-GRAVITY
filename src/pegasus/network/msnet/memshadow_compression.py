"""
MEMSHADOW Protocol Compression

Hardware-accelerated compression support (Kanzi/QATZip) for file transfers.
Only used if hardware supports it.
"""

import logging
from typing import Optional, Tuple
from enum import IntEnum

logger = logging.getLogger(__name__)


class CompressionType(IntEnum):
    """Compression algorithm type"""
    NONE = 0
    GZIP = 1
    ZLIB = 2
    KANZI = 3  # Hardware-accelerated Kanzi
    QATZIP = 4  # Intel QAT Zip (hardware-accelerated)


class HardwareCompressionDetector:
    """
    Detects available hardware compression support
    
    Checks for:
    - Kanzi hardware acceleration
    - Intel QAT (QuickAssist Technology) Zip
    """
    
    def __init__(self):
        self._kanzi_available: Optional[bool] = None
        self._qatzip_available: Optional[bool] = None
        self._detected = False
    
    def detect(self) -> Tuple[bool, bool]:
        """
        Detect hardware compression availability
        
        Returns:
            Tuple of (kanzi_available, qatzip_available)
        """
        if self._detected:
            return self._kanzi_available, self._qatzip_available
        
        kanzi_available = self._check_kanzi()
        qatzip_available = self._check_qatzip()
        
        self._kanzi_available = kanzi_available
        self._qatzip_available = qatzip_available
        self._detected = True
        
        logger.info(
            f"Hardware compression detection: Kanzi={kanzi_available}, QATZip={qatzip_available}"
        )
        
        return kanzi_available, qatzip_available
    
    def _check_kanzi(self) -> bool:
        """Check if Kanzi hardware acceleration is available"""
        try:
            # Try to import Kanzi library
            import kanzi
            # Check if hardware acceleration is available
            # This is a placeholder - actual implementation would check Kanzi API
            return hasattr(kanzi, 'hardware_acceleration')
        except ImportError:
            logger.debug("Kanzi library not available")
            return False
        except Exception as e:
            logger.debug(f"Kanzi detection failed: {e}")
            return False
    
    def _check_qatzip(self) -> bool:
        """Check if Intel QAT Zip is available"""
        try:
            # Try to import QATZip library
            import qatzip
            # Check if QAT hardware is available
            # This is a placeholder - actual implementation would check QAT API
            return hasattr(qatzip, 'is_qat_available') and qatzip.is_qat_available()
        except ImportError:
            logger.debug("QATZip library not available")
            return False
        except Exception as e:
            logger.debug(f"QATZip detection failed: {e}")
            return False
    
    def is_kanzi_available(self) -> bool:
        """Check if Kanzi is available"""
        if not self._detected:
            self.detect()
        return self._kanzi_available or False
    
    def is_qatzip_available(self) -> bool:
        """Check if QATZip is available"""
        if not self._detected:
            self.detect()
        return self._qatzip_available or False
    
    def get_preferred_compression(self) -> CompressionType:
        """
        Get preferred compression type based on hardware availability
        
        Priority:
        1. QATZip (if available)
        2. Kanzi (if available)
        3. GZIP (software fallback)
        """
        if not self._detected:
            self.detect()
        
        if self._qatzip_available:
            return CompressionType.QATZIP
        elif self._kanzi_available:
            return CompressionType.KANZI
        else:
            return CompressionType.GZIP


class CompressionManager:
    """
    Manages compression for file transfers
    
    Only uses hardware compression (Kanzi/QATZip) if available.
    Falls back to software compression otherwise.
    """
    
    def __init__(self):
        self.detector = HardwareCompressionDetector()
        self._compression_type: Optional[CompressionType] = None
    
    def compress(
        self,
        data: bytes,
        compression_type: Optional[CompressionType] = None
    ) -> Tuple[bytes, CompressionType]:
        """
        Compress data using preferred method
        
        Args:
            data: Data to compress
            compression_type: Specific compression type to use (None = auto-detect)
        
        Returns:
            Tuple of (compressed_data, compression_type_used)
        """
        if compression_type is None:
            compression_type = self.detector.get_preferred_compression()
        
        self._compression_type = compression_type
        
        if compression_type == CompressionType.NONE:
            return data, CompressionType.NONE
        
        elif compression_type == CompressionType.QATZIP:
            return self._compress_qatzip(data), CompressionType.QATZIP
        
        elif compression_type == CompressionType.KANZI:
            return self._compress_kanzi(data), CompressionType.KANZI
        
        elif compression_type == CompressionType.GZIP:
            import gzip
            return gzip.compress(data), CompressionType.GZIP
        
        elif compression_type == CompressionType.ZLIB:
            import zlib
            return zlib.compress(data), CompressionType.ZLIB
        
        else:
            # Fallback to GZIP
            import gzip
            return gzip.compress(data), CompressionType.GZIP
    
    def decompress(
        self,
        data: bytes,
        compression_type: CompressionType
    ) -> bytes:
        """
        Decompress data
        
        Args:
            data: Compressed data
            compression_type: Compression type used
        
        Returns:
            Decompressed data
        """
        if compression_type == CompressionType.NONE:
            return data
        
        elif compression_type == CompressionType.QATZIP:
            return self._decompress_qatzip(data)
        
        elif compression_type == CompressionType.KANZI:
            return self._decompress_kanzi(data)
        
        elif compression_type == CompressionType.GZIP:
            import gzip
            return gzip.decompress(data)
        
        elif compression_type == CompressionType.ZLIB:
            import zlib
            return zlib.decompress(data)
        
        else:
            raise ValueError(f"Unknown compression type: {compression_type}")
    
    def _compress_qatzip(self, data: bytes) -> bytes:
        """Compress using QATZip (hardware-accelerated)"""
        try:
            import qatzip
            return qatzip.compress(data)
        except ImportError:
            logger.warning("QATZip not available, falling back to GZIP")
            import gzip
            return gzip.compress(data)
        except Exception as e:
            logger.error(f"QATZip compression failed: {e}, falling back to GZIP")
            import gzip
            return gzip.compress(data)
    
    def _decompress_qatzip(self, data: bytes) -> bytes:
        """Decompress using QATZip (hardware-accelerated)"""
        try:
            import qatzip
            return qatzip.decompress(data)
        except ImportError:
            logger.warning("QATZip not available, falling back to GZIP")
            import gzip
            return gzip.decompress(data)
        except Exception as e:
            logger.error(f"QATZip decompression failed: {e}, falling back to GZIP")
            import gzip
            return gzip.decompress(data)
    
    def _compress_kanzi(self, data: bytes) -> bytes:
        """Compress using Kanzi (hardware-accelerated)"""
        try:
            import kanzi
            return kanzi.compress(data)
        except ImportError:
            logger.warning("Kanzi not available, falling back to GZIP")
            import gzip
            return gzip.compress(data)
        except Exception as e:
            logger.error(f"Kanzi compression failed: {e}, falling back to GZIP")
            import gzip
            return gzip.compress(data)
    
    def _decompress_kanzi(self, data: bytes) -> bytes:
        """Decompress using Kanzi (hardware-accelerated)"""
        try:
            import kanzi
            return kanzi.decompress(data)
        except ImportError:
            logger.warning("Kanzi not available, falling back to GZIP")
            import gzip
            return gzip.decompress(data)
        except Exception as e:
            logger.error(f"Kanzi decompression failed: {e}, falling back to GZIP")
            import gzip
            return gzip.decompress(data)


# Global compression manager instance
_compression_manager: Optional[CompressionManager] = None


def get_compression_manager() -> CompressionManager:
    """Get global compression manager instance"""
    global _compression_manager
    if _compression_manager is None:
        _compression_manager = CompressionManager()
    return _compression_manager
