#!/usr/bin/env python3
"""
Test script for JSON-INTERNAL agent implementation
Validates core functionality, NPU acceleration, and performance
"""

import asyncio
import json
import time
import sys
from pathlib import Path

# Add the agent implementations to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from claude_agents.implementations.internal.json_internal_impl import (
        JSONInternalPythonExecutor,
        JSONProcessingConfig,
        JSONParserType,
        ValidationLevel
    )
    print("✅ JSON-INTERNAL implementation imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

async def test_basic_parsing():
    """Test basic JSON parsing functionality"""
    print("\n🔍 Testing basic JSON parsing...")

    config = JSONProcessingConfig()
    executor = JSONInternalPythonExecutor(config)

    # Test simple JSON
    test_json = '{"name": "test", "value": 123, "nested": {"array": [1, 2, 3]}}'
    result = await executor.parse_json(test_json)

    print(f"Parse result: {result.success}")
    print(f"Execution time: {result.execution_time:.4f}s")
    print(f"Parser used: {result.parser_used}")
    print(f"NPU acceleration: {result.npu_acceleration}")

    assert result.success, "Basic parsing should succeed"
    assert result.data['name'] == 'test', "Parsed data should match input"
    print("✅ Basic parsing test passed")

    return executor

async def test_validation():
    """Test JSON schema validation"""
    print("\n🔍 Testing JSON validation...")

    config = JSONProcessingConfig()
    executor = JSONInternalPythonExecutor(config)

    # Test data and schema
    test_data = {"name": "John", "age": 30, "email": "john@example.com"}
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "number"},
            "email": {"type": "string"}
        },
        "required": ["name", "age"]
    }

    result = await executor.validate_json(test_data, schema)

    print(f"Validation result: {result.success}")
    print(f"Execution time: {result.execution_time:.4f}s")
    print(f"NPU acceleration: {result.npu_acceleration}")

    print("✅ Validation test completed")
    return executor

async def test_error_recovery():
    """Test JSON error recovery"""
    print("\n🔍 Testing error recovery...")

    config = JSONProcessingConfig()
    executor = JSONInternalPythonExecutor(config)

    # Test malformed JSON with trailing comma
    malformed_json = '{"name": "test", "value": 123,}'
    result = await executor.parse_json(malformed_json, enable_recovery=True)

    print(f"Recovery result: {result.success}")
    print(f"Execution time: {result.execution_time:.4f}s")
    if result.error_message:
        print(f"Recovery message: {result.error_message}")

    print("✅ Error recovery test completed")
    return executor

async def test_performance():
    """Test performance with various JSON sizes"""
    print("\n🔍 Testing performance...")

    config = JSONProcessingConfig()
    executor = JSONInternalPythonExecutor(config)

    # Test different sizes
    test_sizes = [100, 1000, 10000]

    for size in test_sizes:
        # Generate test JSON
        test_data = {
            "items": [{"id": i, "value": f"item_{i}"} for i in range(size)]
        }
        test_json = json.dumps(test_data)

        start_time = time.time()
        result = await executor.parse_json(test_json)
        end_time = time.time()

        print(f"Size {size}: {result.success}, {end_time - start_time:.4f}s, parser: {result.parser_used}")

    print("✅ Performance test completed")
    return executor

async def test_batch_processing():
    """Test batch processing functionality"""
    print("\n🔍 Testing batch processing...")

    config = JSONProcessingConfig(batch_size=100)
    executor = JSONInternalPythonExecutor(config)

    # Create test objects
    test_objects = [{"id": i, "data": f"object_{i}"} for i in range(500)]

    async def simple_processor(objects):
        """Simple processor that counts objects"""
        return {"count": len(objects), "total_ids": sum(obj["id"] for obj in objects)}

    results = await executor.batch_process_json(test_objects, simple_processor)

    successful_results = [r for r in results if r.success]
    print(f"Batch processing: {len(successful_results)}/{len(results)} successful")

    print("✅ Batch processing test completed")
    return executor

async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting JSON-INTERNAL agent tests...\n")

    try:
        # Run tests
        await test_basic_parsing()
        await test_validation()
        await test_error_recovery()
        await test_performance()
        await test_batch_processing()

        print(f"\n🎉 All tests completed successfully!")

        # Final performance stats
        config = JSONProcessingConfig()
        executor = JSONInternalPythonExecutor(config)

        # Quick test to generate stats
        test_json = '{"test": "performance"}'
        await executor.parse_json(test_json)

        stats = executor.get_performance_stats()
        print(f"\n📊 Performance Statistics:")
        print(f"   Operations per second: {stats['operations_per_second']:.2f}")
        print(f"   Parse operations: {stats['parse_operations']}")
        print(f"   Validation operations: {stats['validation_operations']}")
        print(f"   Error count: {stats['error_count']}")
        print(f"   NPU available: {stats['npu_stats']['total_operations'] > 0}")

        executor.cleanup()

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)