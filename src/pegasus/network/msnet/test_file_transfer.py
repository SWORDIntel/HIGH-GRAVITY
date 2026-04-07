#!/usr/bin/env python3
"""
Quick test of file transfer functionality
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pegasus.network.msnet.dsmil_protocol import (
    create_file_transfer_messages,
    FileReassemblyManager,
    MemshadowMessage,
    MessageType,
    Priority,
    MessageFlags,
)

def test_small_file():
    """Test small file transfer"""
    print("[1] Testing small file transfer...")
    small_data = b"small file content" * 10
    
    metadata, messages = create_file_transfer_messages(
        file_data=small_data,
        filename="small.txt",
        chunk_size=1024,
        compress=False,
    )
    
    print(f"    File: {metadata.filename}, Size: {metadata.file_size} bytes")
    print(f"    Chunks: {metadata.total_chunks}, Messages: {len(messages)}")
    assert len(messages) == 3  # START + CHUNK + END
    assert messages[0].header.msg_type == MessageType.FILE_TRANSFER_START
    assert messages[1].header.msg_type == MessageType.FILE_TRANSFER_CHUNK
    assert messages[2].header.msg_type == MessageType.FILE_TRANSFER_END
    print("    ✓ Small file test passed")

def test_large_file():
    """Test large file fragmentation"""
    print("[2] Testing large file fragmentation...")
    large_data = b"x" * (2 * 1024 * 1024)  # 2MB
    
    metadata, messages = create_file_transfer_messages(
        file_data=large_data,
        filename="large.bin",
        chunk_size=512 * 1024,  # 512KB chunks
        compress=False,
    )
    
    print(f"    File: {metadata.filename}, Size: {metadata.file_size} bytes")
    print(f"    Chunks: {metadata.total_chunks}, Messages: {len(messages)}")
    assert metadata.total_chunks >= 4  # At least 4 chunks
    assert len(messages) == metadata.total_chunks + 2  # START + chunks + END
    
    chunk_messages = [m for m in messages if m.header.msg_type == MessageType.FILE_TRANSFER_CHUNK]
    assert MessageFlags.LAST_FRAGMENT in MessageFlags(chunk_messages[-1].header.flags)
    print("    ✓ Large file test passed")

def test_reassembly():
    """Test file reassembly"""
    print("[3] Testing file reassembly...")
    original_data = b"test content " * 1000
    
    metadata, messages = create_file_transfer_messages(
        file_data=original_data,
        filename="test.bin",
        chunk_size=4096,
        compress=False,
    )
    
    reassembly = FileReassemblyManager()
    
    # Process START
    start_metadata = reassembly.handle_start(messages[0])
    assert start_metadata is not None
    
    # Process chunks
    chunk_messages = [m for m in messages if m.header.msg_type == MessageType.FILE_TRANSFER_CHUNK]
    is_complete = False
    
    for chunk_msg in chunk_messages:
        file_id, chunk_data, is_complete = reassembly.handle_chunk(chunk_msg)
        assert file_id == metadata.file_id
    
    assert is_complete
    
    # Reassemble
    reassembled = reassembly.reassemble_file(metadata.file_id)
    assert reassembled == original_data
    print(f"    ✓ Reassembly test passed ({len(reassembled)} bytes)")

def test_backwards_compatibility():
    """Test backwards compatibility"""
    print("[4] Testing backwards compatibility...")
    small_payload = b"small data"
    msg = MemshadowMessage.create(
        msg_type=MessageType.MEMORY_SYNC,
        payload=small_payload,
    )
    
    packed = msg.pack()
    unpacked = MemshadowMessage.unpack(packed)
    
    assert unpacked.payload == small_payload
    # Verify no extension header for simple messages
    assert unpacked.extension is None
    print("    ✓ Backwards compatibility test passed")

if __name__ == "__main__":
    print("=" * 60)
    print("File Transfer Protocol Test")
    print("=" * 60)
    
    try:
        test_small_file()
        test_large_file()
        test_reassembly()
        test_backwards_compatibility()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
