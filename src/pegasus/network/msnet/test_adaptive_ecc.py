#!/usr/bin/env python3
"""
Test adaptive ECC functionality
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.pegasus.network.msnet.adaptive_ecc import AdaptiveECCManager, ConnectionQualityTracker, ECC_NONE, ECC_PARITY, ECC_REED_SOLOMON

def test_adaptive_ecc():
    """Test adaptive ECC adjustment"""
    print("[1] Testing adaptive ECC...")
    
    manager = AdaptiveECCManager(window_size=10, min_samples=3)
    
    # Simulate excellent connection
    print("    Simulating excellent connection...")
    for i in range(5):
        manager.record_quality(250, errors_corrected=False, ecc_mode_used=ECC_NONE)
    
    mode, bytes_val = manager.get_recommended_ecc()
    print(f"    Recommended ECC: mode={mode}, bytes={bytes_val}")
    assert mode == ECC_NONE or mode == ECC_PARITY, "Should use minimal ECC for excellent quality"
    
    # Simulate degrading connection
    print("    Simulating degrading connection...")
    manager.reset()  # Reset for clean test
    import time
    for quality in [200, 150, 100, 80, 60]:
        manager.record_quality(quality, errors_corrected=True, ecc_mode_used=ECC_PARITY)
        time.sleep(0.1)  # Small delay to allow adaptation
    
    # Force adaptation
    manager._adapt_ecc()
    
    mode, bytes_val = manager.get_recommended_ecc()
    print(f"    Recommended ECC: mode={mode}, bytes={bytes_val}")
    assert mode == ECC_REED_SOLOMON, f"Should use Reed-Solomon for poor quality, got mode={mode}"
    
    # Check stats
    stats = manager.get_stats()
    print(f"    Average quality: {stats.average_quality:.1f}")
    print(f"    Trend: {stats.trend}")
    print(f"    Error rate: {stats.error_rate:.2%}")
    
    print("    ✓ Adaptive ECC test passed")

def test_connection_tracker():
    """Test connection quality tracker"""
    print("[2] Testing connection tracker...")
    
    tracker = ConnectionQualityTracker()
    
    # Track multiple connections
    tracker.record_quality("conn1", 200, False, ECC_PARITY)
    tracker.record_quality("conn2", 100, True, ECC_REED_SOLOMON)
    
    mode1, bytes1 = tracker.get_recommended_ecc("conn1")
    mode2, bytes2 = tracker.get_recommended_ecc("conn2")
    
    print(f"    Connection 1 ECC: mode={mode1}, bytes={bytes1}")
    print(f"    Connection 2 ECC: mode={mode2}, bytes={bytes2}")
    
    stats1 = tracker.get_stats("conn1")
    stats2 = tracker.get_stats("conn2")
    
    assert stats1 is not None
    assert stats2 is not None
    print(f"    Connection 1 quality: {stats1.current_quality}")
    print(f"    Connection 2 quality: {stats2.current_quality}")
    
    print("    ✓ Connection tracker test passed")

def test_quality_trends():
    """Test quality trend detection"""
    print("[3] Testing quality trends...")
    
    manager = AdaptiveECCManager()
    
    # Improving trend
    for quality in [100, 120, 140, 160, 180]:
        manager.record_quality(quality)
    
    stats = manager.get_stats()
    print(f"    Trend: {stats.trend}")
    assert stats.trend in ["improving", "stable"], "Should detect improving trend"
    
    # Degrading trend
    manager.reset()
    for quality in [200, 180, 160, 140, 120]:
        manager.record_quality(quality)
    
    stats = manager.get_stats()
    print(f"    Trend: {stats.trend}")
    assert stats.trend in ["degrading", "stable"], "Should detect degrading trend"
    
    print("    ✓ Quality trends test passed")

if __name__ == "__main__":
    print("=" * 60)
    print("Adaptive ECC Test")
    print("=" * 60)
    
    try:
        test_adaptive_ecc()
        test_connection_tracker()
        test_quality_trends()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
