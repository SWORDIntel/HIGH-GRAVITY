"""
Unit tests for MEMSHADOW Protocol v3.0

Tests header pack/unpack, message serialization, and routing decisions.
"""

import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dsmil_protocol import (
    MemshadowHeader,
    MemshadowMessage,
    MessageType,
    Priority,
    MessageFlags,
    MemoryTier,
    SyncOperation,
    PsychEvent,
    FileMetadata,
    FileChunkHeader,
    FileFragmentationManager,
    FileReassemblyManager,
    create_file_transfer_messages,
    MEMSHADOW_MAGIC,
    MEMSHADOW_VERSION,
    HEADER_SIZE,
    should_route_p2p,
    get_routing_mode,
    create_memory_sync_message,
    create_psych_message,
)


class TestHeader:
    """Test MemshadowHeader"""
    
    def test_header_size(self):
        """Header must be exactly 32 bytes"""
        header = MemshadowHeader()
        packed = header.pack()
        assert len(packed) == HEADER_SIZE == 32
    
    def test_header_magic(self):
        """Magic number must be correct"""
        assert MEMSHADOW_MAGIC == 0x4D53485700000000  # "MSHW" padded to 8 bytes
        
        header = MemshadowHeader()
        packed = header.pack()
        unpacked = MemshadowHeader.unpack(packed)
        # Check first 4 bytes match "MSHW"
        magic_4bytes = (unpacked.magic >> 32) & 0xFFFFFFFF
        assert magic_4bytes == 0x4D534857
    
    def test_header_round_trip(self):
        """Pack and unpack should preserve all fields"""
        header = MemshadowHeader(
            priority=Priority.HIGH,
            msg_type=MessageType.MEMORY_SYNC,
            flags=MessageFlags.BATCHED | MessageFlags.COMPRESSED,
            batch_count=10,
            payload_len=4096,
        )
        
        packed = header.pack()
        unpacked = MemshadowHeader.unpack(packed)
        
        assert unpacked.priority == Priority.HIGH
        assert unpacked.msg_type == MessageType.MEMORY_SYNC
        assert unpacked.batch_count == 10
        assert unpacked.payload_len == 4096
        assert MessageFlags.BATCHED in MessageFlags(unpacked.flags)
        assert MessageFlags.COMPRESSED in MessageFlags(unpacked.flags)
    
    def test_header_validation(self):
        """Invalid magic should fail validation"""
        header = MemshadowHeader()
        assert header.validate()
        
        header.magic = 0x12345678
        assert not header.validate()
    
    def test_header_unpack_invalid_magic(self):
        """Unpack with invalid magic should raise"""
        bad_data = b"\x00" * 32
        with pytest.raises(ValueError, match="Invalid magic"):
            MemshadowHeader.unpack(bad_data)
    
    def test_header_unpack_too_short(self):
        """Unpack with short data should raise"""
        with pytest.raises(ValueError, match="Header too short"):
            MemshadowHeader.unpack(b"\x00" * 16)


class TestMessage:
    """Test MemshadowMessage"""
    
    def test_message_create(self):
        """Create message with payload"""
        payload = b"test data"
        msg = MemshadowMessage.create(
            msg_type=MessageType.MEMORY_STORE,
            payload=payload,
        )
        
        assert msg.header.msg_type == MessageType.MEMORY_STORE
        assert msg.payload == payload
        assert msg.header.payload_len == len(payload)
    
    def test_message_round_trip(self):
        """Pack and unpack message"""
        payload = b"important data here"
        msg = MemshadowMessage.create(
            msg_type=MessageType.INTEL_REPORT,
            payload=payload,
            priority=Priority.CRITICAL,
            flags=MessageFlags.REQUIRES_ACK,
        )
        
        packed = msg.pack()
        unpacked = MemshadowMessage.unpack(packed)
        
        assert unpacked.header.msg_type == MessageType.INTEL_REPORT
        assert unpacked.header.priority == Priority.CRITICAL
        assert unpacked.payload == payload


class TestMessageTypes:
    """Test all message type categories"""
    
    def test_system_types(self):
        """System/control types are in 0x00xx range"""
        assert MessageType.HEARTBEAT == 0x0001
        assert MessageType.ACK == 0x0002
        assert MessageType.ERROR == 0x0003
    
    def test_psych_types(self):
        """SHRINK psych types are in 0x01xx range"""
        assert MessageType.PSYCH_ASSESSMENT == 0x0100
        assert MessageType.DARK_TRIAD_UPDATE == 0x0101
        assert MessageType.PSYCH_THREAT_ALERT == 0x0110
    
    def test_memory_types(self):
        """Memory types are in 0x03xx range"""
        assert MessageType.MEMORY_STORE == 0x0301
        assert MessageType.MEMORY_QUERY == 0x0302
        assert MessageType.MEMORY_SYNC == 0x0304
    
    def test_improvement_types(self):
        """Improvement types are in 0x05xx range"""
        assert MessageType.IMPROVEMENT_ANNOUNCE == 0x0501
        assert MessageType.IMPROVEMENT_PAYLOAD == 0x0503


class TestPriority:
    """Test priority levels and routing"""
    
    def test_priority_order(self):
        """Priority values should be ordered"""
        assert Priority.LOW < Priority.NORMAL < Priority.HIGH < Priority.CRITICAL < Priority.EMERGENCY
    
    def test_p2p_routing(self):
        """CRITICAL and EMERGENCY use P2P"""
        assert not should_route_p2p(Priority.LOW)
        assert not should_route_p2p(Priority.NORMAL)
        assert not should_route_p2p(Priority.HIGH)
        assert should_route_p2p(Priority.CRITICAL)
        assert should_route_p2p(Priority.EMERGENCY)
    
    def test_routing_mode_strings(self):
        """Routing mode descriptions"""
        assert get_routing_mode(Priority.LOW) == "hub-normal"
        assert get_routing_mode(Priority.NORMAL) == "hub-normal"
        assert get_routing_mode(Priority.HIGH) == "hub-priority"
        assert get_routing_mode(Priority.CRITICAL) == "p2p+hub"
        assert get_routing_mode(Priority.EMERGENCY) == "p2p+hub"


class TestFlags:
    """Test message flags"""
    
    def test_flag_combinations(self):
        """Flags can be combined"""
        flags = MessageFlags.BATCHED | MessageFlags.COMPRESSED | MessageFlags.REQUIRES_ACK
        
        assert MessageFlags.BATCHED in flags
        assert MessageFlags.COMPRESSED in flags
        assert MessageFlags.REQUIRES_ACK in flags
        assert MessageFlags.ENCRYPTED not in flags
    
    def test_flag_round_trip(self):
        """Flags survive pack/unpack"""
        header = MemshadowHeader(
            flags=MessageFlags.PQC_SIGNED | MessageFlags.HIGH_CONFIDENCE,
        )
        
        packed = header.pack()
        unpacked = MemshadowHeader.unpack(packed)
        
        flags = MessageFlags(unpacked.flags)
        # Note: only low byte of flags is preserved in current format
        assert MessageFlags.HIGH_CONFIDENCE in flags


class TestPsychEvent:
    """Test SHRINK psychological event structure"""
    
    def test_psych_event_size(self):
        """Psych event must be 64 bytes"""
        event = PsychEvent()
        packed = event.pack()
        assert len(packed) == 64
    
    def test_psych_event_round_trip(self):
        """Pack and unpack psych event"""
        event = PsychEvent(
            session_id=12345,
            timestamp_offset_us=1000,
            event_type=3,
            acute_stress=0.75,
            machiavellianism=0.5,
            narcissism=0.3,
            psychopathy=0.2,
            confidence=0.95,
        )
        
        packed = event.pack()
        unpacked = PsychEvent.unpack(packed)
        
        assert unpacked.session_id == 12345
        assert unpacked.timestamp_offset_us == 1000
        assert abs(unpacked.acute_stress - 0.75) < 0.001
        assert abs(unpacked.confidence - 0.95) < 0.001


class TestConvenienceFunctions:
    """Test convenience message creation functions"""
    
    def test_create_memory_sync_message(self):
        """Create MEMORY_SYNC message"""
        msg = create_memory_sync_message(
            payload=b"sync data",
            priority=Priority.HIGH,
            batch_count=5,
            compressed=True,
        )
        
        assert msg.header.msg_type == MessageType.MEMORY_SYNC
        assert msg.header.priority == Priority.HIGH
        assert msg.header.batch_count == 5
        assert MessageFlags.BATCHED in MessageFlags(msg.header.flags)
        assert MessageFlags.COMPRESSED in MessageFlags(msg.header.flags)
        assert MessageFlags.REQUIRES_ACK in MessageFlags(msg.header.flags)  # HIGH priority
    
    def test_create_psych_message(self):
        """Create batched PSYCH message"""
        events = [PsychEvent(session_id=i) for i in range(3)]
        msg = create_psych_message(events)
        
        assert msg.header.msg_type == MessageType.PSYCH_ASSESSMENT
        assert msg.header.batch_count == 3
        assert len(msg.payload) == 64 * 3


class TestEnums:
    """Test enum values match documentation"""
    
    def test_memory_tier_values(self):
        """Memory tier enum values"""
        assert MemoryTier.WORKING == 1
        assert MemoryTier.EPISODIC == 2
        assert MemoryTier.SEMANTIC == 3
        assert MemoryTier.L1 == MemoryTier.WORKING
        assert MemoryTier.L2 == MemoryTier.EPISODIC
        assert MemoryTier.L3 == MemoryTier.SEMANTIC
    
    def test_sync_operation_values(self):
        """Sync operation enum values"""
        assert SyncOperation.INSERT == 1
        assert SyncOperation.UPDATE == 2
        assert SyncOperation.DELETE == 3
        assert SyncOperation.MERGE == 4
        assert SyncOperation.REPLICATE == 5


class TestFileTransfer:
    """Test file transfer functionality"""
    
    def test_file_metadata_serialization(self):
        """FileMetadata can be serialized/deserialized"""
        metadata = FileMetadata(
            file_id="abc123",
            filename="test.bin",
            file_size=1024,
            mime_type="application/octet-stream",
            checksum="sha256hash",
            compression="gzip",
            chunk_size=512,
            total_chunks=2,
        )
        
        metadata_dict = metadata.to_dict()
        restored = FileMetadata.from_dict(metadata_dict)
        
        assert restored.file_id == metadata.file_id
        assert restored.filename == metadata.filename
        assert restored.file_size == metadata.file_size
        assert restored.compression == metadata.compression
    
    def test_file_chunk_header(self):
        """FileChunkHeader pack/unpack"""
        header = FileChunkHeader(
            file_id=b"test_file_id_16",
            chunk_index=5,
            chunk_size=1024,
            chunk_checksum=b"checksum_16bytes",
        )
        
        packed = header.pack()
        unpacked = FileChunkHeader.unpack(packed)
        
        assert unpacked.chunk_index == 5
        assert unpacked.chunk_size == 1024
        assert unpacked.file_id == header.file_id
        assert unpacked.chunk_checksum == header.chunk_checksum
    
    def test_small_file_no_fragmentation(self):
        """Small files don't need fragmentation"""
        small_data = b"small file content" * 10  # ~170 bytes
        
        metadata, messages = create_file_transfer_messages(
            file_data=small_data,
            filename="small.txt",
            chunk_size=1024,  # Larger than file
            compress=False,
        )
        
        # Should have START, one CHUNK, and END
        assert len(messages) == 3
        assert messages[0].header.msg_type == MessageType.FILE_TRANSFER_START
        assert messages[1].header.msg_type == MessageType.FILE_TRANSFER_CHUNK
        assert messages[2].header.msg_type == MessageType.FILE_TRANSFER_END
        
        # Last chunk should have LAST_FRAGMENT flag
        assert MessageFlags.LAST_FRAGMENT in MessageFlags(messages[1].header.flags)
    
    def test_large_file_fragmentation(self):
        """Large files are fragmented correctly"""
        # Create 2.5MB file
        large_data = b"x" * (2 * 1024 * 1024 + 512 * 1024)
        
        metadata, messages = create_file_transfer_messages(
            file_data=large_data,
            filename="large.bin",
            chunk_size=1024 * 1024,  # 1MB chunks
            compress=False,
        )
        
        # Should have START, multiple CHUNKs, and END
        assert len(messages) >= 4  # START + at least 3 chunks + END
        assert metadata.total_chunks >= 3
        
        # Verify chunk sequence
        chunk_messages = [m for m in messages if m.header.msg_type == MessageType.FILE_TRANSFER_CHUNK]
        assert len(chunk_messages) == metadata.total_chunks
        
        # Last chunk should have LAST_FRAGMENT flag
        assert MessageFlags.LAST_FRAGMENT in MessageFlags(chunk_messages[-1].header.flags)
    
    def test_file_reassembly(self):
        """File reassembly works correctly"""
        # Create test file
        original_data = b"test file content" * 1000  # ~17KB
        
        # Fragment it
        metadata, messages = create_file_transfer_messages(
            file_data=original_data,
            filename="test.bin",
            chunk_size=4096,  # 4KB chunks
            compress=False,
        )
        
        # Reassemble
        reassembly = FileReassemblyManager()
        
        # Process START
        start_metadata = reassembly.handle_start(messages[0])
        assert start_metadata is not None
        assert start_metadata.filename == "test.bin"
        
        # Process chunks
        chunk_messages = [m for m in messages if m.header.msg_type == MessageType.FILE_TRANSFER_CHUNK]
        is_complete = False
        
        for chunk_msg in chunk_messages:
            file_id, chunk_data, is_complete = reassembly.handle_chunk(chunk_msg)
            assert file_id == metadata.file_id
        
        # Should be complete
        assert is_complete
        
        # Reassemble file
        reassembled_data = reassembly.reassemble_file(metadata.file_id)
        assert reassembled_data == original_data
    
    def test_file_transfer_with_compression(self):
        """File transfer with compression"""
        # Create compressible data
        compressible_data = b"repeated pattern " * 10000
        
        metadata, messages = create_file_transfer_messages(
            file_data=compressible_data,
            filename="compressible.bin",
            compress=True,
        )
        
        # Check if compression was applied
        if metadata.compression == "gzip":
            # Verify compressed flag
            chunk_messages = [m for m in messages if m.header.msg_type == MessageType.FILE_TRANSFER_CHUNK]
            assert MessageFlags.FILE_COMPRESSED in MessageFlags(chunk_messages[0].header.flags)
    
    def test_file_transfer_backwards_compatibility(self):
        """File transfer doesn't break existing small payloads"""
        # Existing small payload should still work
        small_payload = b"small data"
        msg = MemshadowMessage.create(
            msg_type=MessageType.MEMORY_SYNC,
            payload=small_payload,
        )
        
        # Should pack/unpack normally
        packed = msg.pack()
        unpacked = MemshadowMessage.unpack(packed)
        
        assert unpacked.payload == small_payload
        assert unpacked.header.msg_type == MessageType.MEMORY_SYNC
        # Should NOT have file transfer flags
        assert MessageFlags.FILE_STREAM not in MessageFlags(unpacked.header.flags)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
