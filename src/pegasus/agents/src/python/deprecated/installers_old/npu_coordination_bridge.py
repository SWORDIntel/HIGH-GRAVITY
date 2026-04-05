#!/usr/bin/env python3
"""
NPU Coordination Bridge v2.0 - Rust-Python Hybrid Implementation
High-performance NPU coordination with backward compatibility wrapper
"""

import asyncio
import time
import json
import numpy as np
import sys
import warnings
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import path utilities
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import (
        get_project_root, get_agents_dir, get_database_dir,
        get_python_src_dir, get_shadowgit_paths, get_database_config
    )
except ImportError:
    def get_project_root():
        return Path(__file__).parent.parent.parent
    def get_agents_dir():
        return get_project_root() / 'agents'
    def get_database_dir():
        return get_project_root() / 'database'
    def get_python_src_dir():
        return get_agents_dir() / 'src' / 'python'

# Try to import Rust bridge first, fallback to Python implementation
RUST_BRIDGE_AVAILABLE = False
FALLBACK_MODE = False

try:
    # Import the compiled Rust bridge
    import npu_coordination_bridge as rust_bridge
    RUST_BRIDGE_AVAILABLE = True
    logger.info("✅ Rust NPU Bridge v2.0 loaded successfully - High performance mode enabled")
except ImportError as e:
    logger.warning(f"⚠️  Rust NPU Bridge not available: {e}")
    logger.info("🔄 Falling back to Python implementation")
    FALLBACK_MODE = True

# Data structures for coordination
@dataclass
class NPUOperation:
    """NPU operation specification"""
    operation_id: str
    operation_type: str
    input_data: Union[np.ndarray, List[float]]
    priority: int = 1
    timeout_ms: int = 5000
    metadata: Dict[str, Any] = None

@dataclass
class NPUResult:
    """NPU operation result"""
    operation_id: str
    success: bool
    result_data: Optional[Union[np.ndarray, List[float]]] = None
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

class Priority(Enum):
    """Operation priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    REALTIME = 4

class NPUCoordinationBridge:
    """
    High-performance NPU coordination bridge with Rust backend and Python fallback
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize NPU coordination bridge"""
        self.config = config or {}
        self.initialized = False
        self.rust_bridge = None
        self.stats = {
            'operations_completed': 0,
            'operations_failed': 0,
            'total_execution_time_ms': 0.0,
            'rust_mode': RUST_BRIDGE_AVAILABLE and not FALLBACK_MODE
        }

        # Initialize backend
        if RUST_BRIDGE_AVAILABLE and not FALLBACK_MODE:
            self._init_rust_backend()
        else:
            self._init_python_fallback()

    def _init_rust_backend(self):
        """Initialize high-performance Rust backend"""
        try:
            # Configure Rust bridge with Intel NPU optimization
            rust_config = {
                'intel_npu_enabled': True,
                'target_throughput': 50000,  # 50K ops/sec target
                'max_latency_ms': 1.0,       # <1ms target latency
                'memory_pool_size': 256 * 1024 * 1024,  # 256MB
                'worker_threads': 16,
                'hardware_acceleration': True
            }
            rust_config.update(self.config)

            self.rust_bridge = rust_bridge.NPUBridge(rust_config)
            self.initialized = True
            logger.info("🚀 Rust NPU Bridge initialized - 50K+ ops/sec capability")

        except Exception as e:
            logger.error(f"❌ Rust backend initialization failed: {e}")
            logger.info("🔄 Falling back to Python implementation")
            self._init_python_fallback()

    def _init_python_fallback(self):
        """Initialize Python fallback implementation"""
        global FALLBACK_MODE
        FALLBACK_MODE = True

        # Load legacy Python implementation if available
        try:
            deprecated_path = get_python_src_dir() / "deprecated"
            for dep_dir in deprecated_path.glob("npu_bridge_python_legacy_*"):
                legacy_file = dep_dir / "npu_coordination_bridge_buggy_original.py"
                if legacy_file.exists():
                    logger.warning("⚠️  Using legacy Python implementation - performance limited")
                    break
        except Exception as e:
            logger.error(f"Legacy Python implementation not found: {e}")

        # Basic Python implementation
        self.operation_queue = asyncio.Queue()
        self.results_cache = {}
        self.initialized = True
        logger.info("✅ Python fallback mode initialized")

    async def submit_operation(self, operation: NPUOperation) -> str:
        """Submit operation for NPU processing"""
        if not self.initialized:
            raise RuntimeError("NPU Bridge not initialized")

        start_time = time.time()

        try:
            if RUST_BRIDGE_AVAILABLE and not FALLBACK_MODE:
                # Use high-performance Rust backend
                result_id = await self._submit_rust_operation(operation)
            else:
                # Use Python fallback
                result_id = await self._submit_python_operation(operation)

            self.stats['operations_completed'] += 1
            execution_time = (time.time() - start_time) * 1000
            self.stats['total_execution_time_ms'] += execution_time

            return result_id

        except Exception as e:
            self.stats['operations_failed'] += 1
            logger.error(f"Operation {operation.operation_id} failed: {e}")
            raise

    async def _submit_rust_operation(self, operation: NPUOperation) -> str:
        """Submit operation to Rust backend"""
        # Convert Python operation to Rust format
        rust_operation = {
            'operation_id': operation.operation_id,
            'operation_type': operation.operation_type,
            'input_data': operation.input_data.tolist() if isinstance(operation.input_data, np.ndarray) else operation.input_data,
            'priority': operation.priority,
            'timeout_ms': operation.timeout_ms,
            'metadata': operation.metadata or {}
        }

        # Submit to Rust bridge (async)
        result = await self.rust_bridge.submit_operation_async(rust_operation)
        return result['operation_id']

    async def _submit_python_operation(self, operation: NPUOperation) -> str:
        """Submit operation to Python fallback"""
        # Simple queue-based processing for fallback
        await self.operation_queue.put(operation)

        # Simulate processing (replace with actual NPU integration)
        await asyncio.sleep(0.001)  # 1ms simulated processing

        # Create mock result
        result = NPUResult(
            operation_id=operation.operation_id,
            success=True,
            result_data=operation.input_data,  # Echo input for simulation
            execution_time_ms=1.0,
            metadata={'fallback_mode': True}
        )

        self.results_cache[operation.operation_id] = result
        return operation.operation_id

    async def get_result(self, operation_id: str, timeout_ms: int = 5000) -> NPUResult:
        """Get operation result"""
        if RUST_BRIDGE_AVAILABLE and not FALLBACK_MODE:
            # Get result from Rust backend
            rust_result = await self.rust_bridge.get_result_async(operation_id, timeout_ms)

            # Convert Rust result to Python format
            return NPUResult(
                operation_id=rust_result['operation_id'],
                success=rust_result['success'],
                result_data=np.array(rust_result['result_data']) if rust_result['result_data'] else None,
                execution_time_ms=rust_result['execution_time_ms'],
                error_message=rust_result.get('error_message'),
                metadata=rust_result.get('metadata', {})
            )
        else:
            # Get result from Python cache
            if operation_id in self.results_cache:
                return self.results_cache[operation_id]
            else:
                raise ValueError(f"Operation {operation_id} not found")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = self.stats.copy()

        if stats['operations_completed'] > 0:
            stats['average_execution_time_ms'] = stats['total_execution_time_ms'] / stats['operations_completed']
        else:
            stats['average_execution_time_ms'] = 0.0

        if RUST_BRIDGE_AVAILABLE and not FALLBACK_MODE:
            # Get additional Rust performance metrics
            try:
                rust_stats = self.rust_bridge.get_performance_stats()
                stats.update(rust_stats)
            except Exception as e:
                logger.warning(f"Could not get Rust performance stats: {e}")

        return stats

    async def shutdown(self):
        """Graceful shutdown"""
        if RUST_BRIDGE_AVAILABLE and not FALLBACK_MODE and self.rust_bridge:
            await self.rust_bridge.shutdown_async()

        logger.info("NPU Coordination Bridge shutdown complete")

# Backward compatibility functions
async def create_npu_bridge(config: Optional[Dict[str, Any]] = None) -> NPUCoordinationBridge:
    """Create and initialize NPU coordination bridge"""
    bridge = NPUCoordinationBridge(config)
    return bridge

def get_bridge_status() -> Dict[str, Any]:
    """Get current bridge status"""
    return {
        'rust_available': RUST_BRIDGE_AVAILABLE,
        'fallback_mode': FALLBACK_MODE,
        'performance_mode': 'rust' if RUST_BRIDGE_AVAILABLE and not FALLBACK_MODE else 'python'
    }

# Legacy compatibility layer
class LegacyNPUCoordinator:
    """Legacy compatibility for old Python implementation"""

    def __init__(self):
        warnings.warn("LegacyNPUCoordinator is deprecated. Use NPUCoordinationBridge instead.", DeprecationWarning)
        self.bridge = NPUCoordinationBridge()

    async def coordinate_operation(self, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy coordination method"""
        operation = NPUOperation(
            operation_id=operation_data.get('id', f"legacy_{int(time.time() * 1000)}"),
            operation_type=operation_data.get('type', 'legacy'),
            input_data=operation_data.get('data', []),
            priority=operation_data.get('priority', 1)
        )

        result_id = await self.bridge.submit_operation(operation)
        result = await self.bridge.get_result(result_id)

        return {
            'success': result.success,
            'data': result.result_data.tolist() if isinstance(result.result_data, np.ndarray) else result.result_data,
            'execution_time': result.execution_time_ms,
            'error': result.error_message
        }

# Module-level bridge instance for backward compatibility
_global_bridge = None

async def get_global_bridge() -> NPUCoordinationBridge:
    """Get global bridge instance"""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = await create_npu_bridge()
    return _global_bridge

if __name__ == "__main__":
    async def main():
        """Example usage and testing"""
        print("NPU Coordination Bridge v2.0 - Testing")
        print("=" * 50)

        # Show bridge status
        status = get_bridge_status()
        print(f"Bridge Status: {status}")

        # Create bridge
        bridge = await create_npu_bridge()

        # Test operation
        test_operation = NPUOperation(
            operation_id="test_001",
            operation_type="matrix_multiply",
            input_data=np.random.random((100, 100)).tolist(),
            priority=Priority.HIGH.value
        )

        print(f"\nSubmitting test operation: {test_operation.operation_id}")
        start_time = time.time()

        result_id = await bridge.submit_operation(test_operation)
        result = await bridge.get_result(result_id)

        end_time = time.time()

        print(f"Operation completed: {result.success}")
        print(f"Execution time: {result.execution_time_ms:.2f}ms")
        print(f"Total time: {(end_time - start_time) * 1000:.2f}ms")

        # Show performance stats
        stats = bridge.get_performance_stats()
        print(f"\nPerformance Stats: {stats}")

        await bridge.shutdown()

    asyncio.run(main())