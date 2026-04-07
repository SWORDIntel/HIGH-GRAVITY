"""
Error Correction Code (ECC) and Connection Quality Encoding

Efficiently combines ECC parity bytes with connection quality information
to minimize protocol overhead while providing error correction and quality feedback.
"""

from typing import Tuple, Optional
import struct

# Try to import Reed-Solomon
try:
    import reedsolo
    REED_SOLOMON_AVAILABLE = True
except ImportError:
    REED_SOLOMON_AVAILABLE = False


def compute_parity(data: bytes) -> bytes:
    """Compute simple parity byte for error detection"""
    parity = 0
    for byte in data:
        parity ^= byte
    return bytes([parity])


def encode_quality_in_parity(data: bytes, quality: int) -> Tuple[bytes, bytes]:
    """
    Encode connection quality in parity byte using XOR multiplication.
    
    This allows parity byte to serve double duty:
    1. Error detection/correction (parity)
    2. Connection quality transmission
    
    Args:
        data: Data to compute parity for
        quality: Connection quality (0-255)
    
    Returns:
        Tuple of (parity_byte, encoded_parity)
        - parity_byte: Standard parity
        - encoded_parity: Parity XOR quality (can recover both)
    """
    parity = compute_parity(data)[0]
    
    # Encode quality: parity XOR quality
    # At receiver: quality = encoded_parity XOR parity
    #              parity = encoded_parity XOR quality
    encoded_parity = parity ^ quality
    
    return bytes([parity]), bytes([encoded_parity])


def decode_quality_from_parity(encoded_parity: bytes, data: bytes) -> Tuple[int, bytes]:
    """
    Decode connection quality from parity byte.
    
    Args:
        encoded_parity: Encoded parity byte (parity XOR quality)
        data: Original data
    
    Returns:
        Tuple of (quality, parity)
        - quality: Recovered connection quality (0-255)
        - parity: Recovered parity byte
    """
    if not encoded_parity:
        return 255, b''  # Default quality if no parity
    
    encoded = encoded_parity[0]
    computed_parity = compute_parity(data)[0]
    
    # Recover quality: quality = encoded XOR parity
    quality = encoded ^ computed_parity
    
    # Recover parity: parity = encoded XOR quality
    parity = encoded ^ quality
    
    return quality & 0xFF, bytes([parity])


def apply_reed_solomon(data: bytes, ecc_bytes: int = 4) -> bytes:
    """
    Apply Reed-Solomon error correction.
    
    Args:
        data: Data to encode
        ecc_bytes: Number of ECC bytes to add
    
    Returns:
        Data with ECC bytes appended
    """
    if not REED_SOLOMON_AVAILABLE:
        # Fallback to parity
        parity = compute_parity(data)
        return data + parity
    
    try:
        rs = reedsolo.RSCodec(ecc_bytes)
        encoded = rs.encode(data)
        return encoded
    except Exception:
        # Fallback to parity
        parity = compute_parity(data)
        return data + parity


def decode_reed_solomon(encoded_data: bytes, ecc_bytes: int = 4) -> Tuple[bytes, bool]:
    """
    Decode Reed-Solomon error correction.
    
    Args:
        encoded_data: Data with ECC bytes
        ecc_bytes: Number of ECC bytes
    
    Returns:
        Tuple of (decoded_data, corrected)
        - decoded_data: Corrected data
        - corrected: True if errors were corrected
    """
    if not REED_SOLOMON_AVAILABLE:
        # Fallback: just remove parity byte
        if len(encoded_data) > 0:
            return encoded_data[:-1], False
        return encoded_data, False
    
    try:
        rs = reedsolo.RSCodec(ecc_bytes)
        decoded, corrected = rs.decode(encoded_data)
        return decoded, corrected
    except Exception:
        # Error correction failed
        if len(encoded_data) > ecc_bytes:
            return encoded_data[:-ecc_bytes], False
        return encoded_data, False


def encode_quality_in_ecc(data: bytes, quality: int, ecc_mode: int, ecc_bytes: int = 4) -> Tuple[bytes, bytes]:
    """
    Encode connection quality in ECC bytes efficiently.
    
    Uses ECC parity bytes to also carry quality information.
    
    Args:
        data: Data to encode
        quality: Connection quality (0-255)
        ecc_mode: ECC mode (1=parity, 2=reed-solomon)
        ecc_bytes: Number of ECC bytes for Reed-Solomon
    
    Returns:
        Tuple of (encoded_data, quality_info)
        - encoded_data: Data with ECC bytes (quality encoded in parity)
        - quality_info: Quality byte for verification
    """
    if ecc_mode == 1:  # Parity
        parity, encoded_parity = encode_quality_in_parity(data, quality)
        return data + encoded_parity, bytes([quality])
    
    elif ecc_mode == 2:  # Reed-Solomon
        # For RS, we encode quality in the first ECC byte
        # Create a quality marker byte
        quality_marker = bytes([quality])
        
        # Apply RS to data + quality marker
        data_with_marker = data + quality_marker
        encoded = apply_reed_solomon(data_with_marker, ecc_bytes)
        
        return encoded, quality_marker
    
    else:  # No ECC
        return data, bytes([quality])


def decode_quality_from_ecc(encoded_data: bytes, ecc_mode: int, ecc_bytes: int = 4) -> Tuple[bytes, int, bool]:
    """
    Decode connection quality from ECC bytes.
    
    Args:
        encoded_data: Data with ECC bytes
        ecc_mode: ECC mode (1=parity, 2=reed-solomon)
        ecc_bytes: Number of ECC bytes for Reed-Solomon
    
    Returns:
        Tuple of (decoded_data, quality, corrected)
        - decoded_data: Corrected data
        - quality: Recovered connection quality
        - corrected: True if errors were corrected
    """
    if ecc_mode == 1:  # Parity
        if len(encoded_data) < 1:
            return encoded_data, 255, False
        
        parity_byte = encoded_data[-1:]
        data = encoded_data[:-1]
        quality, parity = decode_quality_from_parity(parity_byte, data)
        
        # Verify parity
        computed_parity = compute_parity(data)[0]
        corrected = (parity[0] == computed_parity)
        
        return data, quality, corrected
    
    elif ecc_mode == 2:  # Reed-Solomon
        decoded, corrected = decode_reed_solomon(encoded_data, ecc_bytes)
        
        if len(decoded) > 0:
            # Last byte is quality marker
            quality = decoded[-1]
            data = decoded[:-1]
            return data, quality & 0xFF, corrected
        else:
            return decoded, 255, corrected
    
    else:  # No ECC
        return encoded_data, 255, False
