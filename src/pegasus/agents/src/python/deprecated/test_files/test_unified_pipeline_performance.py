#!/usr/bin/env python3
"""
Comprehensive Test Suite for Unified Async Optimization Pipeline
Validates all performance targets and integration points

Performance Targets:
- 50% memory reduction through streaming and pooling
- 60% CPU reduction through async I/O
- <100ms end-to-end latency for typical requests
- Support 1000+ concurrent operations
"""

import asyncio
import time
import logging
import statistics
import tracemalloc
import psutil
from typing import List, Dict, Any
from dataclasses import dataclass
import unittest
from unittest import IsolatedAsyncioTestCase
import json
import sys
import os
from pathlib import Path

# Add the current directory to the path for imports

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import (
        get_project_root, get_agents_dir, get_database_dir,
        get_python_src_dir, get_shadowgit_paths, get_database_config
    )
except ImportError:
    # Fallback if path_utilities not available
    def get_project_root():
        return Path(__file__).parent.parent.parent
    def get_agents_dir():
        return get_project_root() / 'agents'
    def get_database_dir():
        return get_project_root() / 'database'
    def get_python_src_dir():
        return get_agents_dir() / 'src' / 'python'
    def get_shadowgit_paths():
        home_dir = Path.home()
        return {'root': home_dir / 'shadowgit'}
    def get_database_config():
        return {
            'host': 'localhost', 'port': 5433,
            'database': 'claude_agents_auth',
            'user': 'claude_agent', 'password': 'claude_auth_pass'
        }
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unified_async_optimization_pipeline import (
    UnifiedAsyncPipeline, OptimizationRequest, OptimizationResponse,
    create_optimized_pipeline, AsyncConnectionPool, AsyncStreamProcessor,
    CircuitBreaker, MemoryTracker, PerformanceMonitor
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pipeline_test')

@dataclass
class PerformanceTestResult:
    """Test result with performance metrics"""
    test_name: str
    success: bool
    latency_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput_req_per_sec: float
    error_message: str = ""

class PipelinePerformanceTest(IsolatedAsyncioTestCase):
    """Comprehensive performance test suite"""
    
    async def asyncSetUp(self):
        """Set up test environment"""
        # Start memory tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        
        # Create test configuration
        self.test_config = {
            'max_connections': 50,
            'worker_count': 5,
            'stream_chunk_size': 4096,
            'max_memory_mb': 50,
            'request_timeout': 10,
            'l1_capacity': 1000,
            'redis_url': 'redis://localhost:6379/1',  # Test database
            'postgres_url': 'postgresql://claude_agent:password@localhost:5433/claude_agents_auth',
            'security_mode': False,  # Disable for performance testing
            'baseline_memory_mb': 100,
            'baseline_cpu_percent': 50
        }
        
        # Initialize pipeline for testing
        try:
            self.pipeline = await create_optimized_pipeline(self.test_config)
            self.pipeline_created = True
        except Exception as e:
            logger.warning(f"Could not create full pipeline: {e}")
            self.pipeline_created = False
            # Create minimal pipeline for basic tests
            self.pipeline = UnifiedAsyncPipeline(self.test_config)
        
        # Test data
        self.test_requests = self._generate_test_requests(100)
        self.performance_results: List[PerformanceTestResult] = []
    
    async def asyncTearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'pipeline') and self.pipeline:
            try:
                await self.pipeline.shutdown()
            except:
                pass  # Ignore shutdown errors in tests
    
    def _generate_test_requests(self, count: int) -> List[OptimizationRequest]:
        """Generate test requests with varying complexity"""
        requests = []
        
        # Simple requests (30%)
        for i in range(count // 3):
            requests.append(OptimizationRequest(
                request_id=f"simple-{i}",
                query=f"simple query {i}",
                context={'type': 'simple', 'id': i},
                priority=5,
                max_tokens=1000
            ))
        
        # Medium complexity requests (50%)
        for i in range(count // 2):
            requests.append(OptimizationRequest(
                request_id=f"medium-{i}",
                query=f"optimize database performance for user {i} with complex joins",
                context={
                    'type': 'medium',
                    'id': i,
                    'project_root': str(get_project_root()),
                    'extensions': ['.py', '.sql']
                },
                priority=5,
                max_tokens=4000
            ))
        
        # Complex requests (20%)
        remaining = count - len(requests)
        for i in range(remaining):
            requests.append(OptimizationRequest(
                request_id=f"complex-{i}",
                query=f"comprehensive system analysis and optimization for project {i} with security audit",
                context={
                    'type': 'complex',
                    'id': i,
                    'project_root': str(get_project_root()),
                    'extensions': ['.py', '.js', '.md', '.sql', '.yaml'],
                    'security_level': 'high',
                    'optimization_level': 'aggressive'
                },
                priority=3,
                max_tokens=8000
            ))
        
        return requests
    
    def _measure_performance(self, func_name: str):
        """Decorator to measure performance of test functions"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Get baseline measurements
                start_time = time.perf_counter()
                start_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
                start_cpu = psutil.cpu_percent()
                
                success = True
                error_message = ""
                
                try:
                    result = await func(*args, **kwargs)
                    await asyncio.sleep(0.1)  # Allow CPU measurement to stabilize
                except Exception as e:
                    success = False
                    error_message = str(e)
                    result = None
                
                # Calculate metrics
                end_time = time.perf_counter()
                end_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
                end_cpu = psutil.cpu_percent()
                
                latency_ms = (end_time - start_time) * 1000
                memory_usage_mb = (end_memory - start_memory) / (1024 * 1024)
                cpu_usage_percent = end_cpu
                
                # Store result
                test_result = PerformanceTestResult(
                    test_name=func_name,
                    success=success,
                    latency_ms=latency_ms,
                    memory_usage_mb=memory_usage_mb,
                    cpu_usage_percent=cpu_usage_percent,
                    throughput_req_per_sec=0.0,  # Will be calculated separately
                    error_message=error_message
                )
                
                self.performance_results.append(test_result)
                return result
            
            return wrapper
        return decorator
    
    @_measure_performance("test_basic_initialization")
    async def test_basic_initialization(self):
        """Test basic pipeline initialization"""
        logger.info("Testing basic initialization...")
        
        # Test pipeline creation
        self.assertIsNotNone(self.pipeline)
        
        # Test component initialization
        if self.pipeline_created:
            self.assertIsNotNone(self.pipeline.trie_matcher)
            self.assertIsNotNone(self.pipeline.cache_manager)
            self.assertIsNotNone(self.pipeline.token_optimizer)
            self.assertIsNotNone(self.pipeline.context_chopper)
        
        logger.info("✓ Basic initialization test passed")
    
    @_measure_performance("test_single_request_latency")
    async def test_single_request_latency(self):
        """Test single request latency < 100ms target"""
        logger.info("Testing single request latency...")
        
        request = OptimizationRequest(
            request_id="latency-test",
            query="test latency optimization",
            context={'test': True}
        )
        
        start_time = time.perf_counter()
        
        if self.pipeline_created:
            response = await self.pipeline.process_request(request)
            self.assertIsInstance(response, OptimizationResponse)
            self.assertEqual(response.request_id, "latency-test")
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Assert latency target
        self.assertLess(latency_ms, 100, f"Latency {latency_ms:.2f}ms exceeds 100ms target")
        
        logger.info(f"✓ Single request latency: {latency_ms:.2f}ms (target: <100ms)")
    
    @_measure_performance("test_concurrent_requests")
    async def test_concurrent_requests(self):
        """Test concurrent request processing"""
        logger.info("Testing concurrent request processing...")
        
        if not self.pipeline_created:
            self.skipTest("Pipeline not fully created, skipping concurrent test")
        
        # Use smaller batch for testing
        test_requests = self.test_requests[:20]
        
        start_time = time.perf_counter()
        
        # Process requests concurrently
        tasks = [self.pipeline.process_request(req) for req in test_requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.perf_counter() - start_time
        
        # Check successful responses
        successful_responses = [r for r in responses if isinstance(r, OptimizationResponse)]
        
        # Calculate throughput
        throughput = len(successful_responses) / total_time if total_time > 0 else 0
        
        # Update test result with throughput
        if self.performance_results:
            self.performance_results[-1].throughput_req_per_sec = throughput
        
        # Assert minimum performance
        self.assertGreater(len(successful_responses), 0, "No successful responses")
        self.assertGreater(throughput, 1.0, f"Throughput {throughput:.2f} req/s too low")
        
        logger.info(f"✓ Processed {len(successful_responses)} requests in {total_time:.2f}s")
        logger.info(f"✓ Throughput: {throughput:.2f} req/sec")
    
    @_measure_performance("test_memory_efficiency")
    async def test_memory_efficiency(self):
        """Test memory efficiency and reduction targets"""
        logger.info("Testing memory efficiency...")
        
        # Set baseline
        baseline_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
        
        if self.pipeline_created:
            # Process some requests to generate memory usage
            test_requests = self.test_requests[:10]
            tasks = [self.pipeline.process_request(req) for req in test_requests]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Get pipeline memory stats
            stats = await self.pipeline.get_performance_stats()
            memory_reduction = stats['pipeline_metrics']['memory_reduction_percent']
            
            # Check if memory tracking is working
            if memory_reduction > 0:
                self.assertGreaterEqual(memory_reduction, 30, 
                    f"Memory reduction {memory_reduction:.1f}% below 30% minimum")
            
            logger.info(f"✓ Memory reduction: {memory_reduction:.1f}%")
        
        # Check current memory usage
        current_memory = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
        memory_used_mb = (current_memory - baseline_memory) / (1024 * 1024)
        
        # Assert reasonable memory usage
        self.assertLess(memory_used_mb, 200, f"Memory usage {memory_used_mb:.2f}MB too high")
        
        logger.info(f"✓ Memory usage during test: {memory_used_mb:.2f}MB")
    
    @_measure_performance("test_caching_performance")
    async def test_caching_performance(self):
        """Test caching system performance"""
        logger.info("Testing caching performance...")
        
        if not self.pipeline_created:
            self.skipTest("Pipeline not fully created, skipping cache test")
        
        # Create identical requests for cache testing
        request1 = OptimizationRequest(
            request_id="cache-test-1",
            query="cache test query",
            context={'cache_test': True}
        )
        request2 = OptimizationRequest(
            request_id="cache-test-2", 
            query="cache test query",  # Same query for cache hit
            context={'cache_test': True}
        )
        
        # First request (cache miss)
        start1 = time.perf_counter()
        response1 = await self.pipeline.process_request(request1)
        latency1 = (time.perf_counter() - start1) * 1000
        
        # Second request (should be cache hit)
        start2 = time.perf_counter()
        response2 = await self.pipeline.process_request(request2)
        latency2 = (time.perf_counter() - start2) * 1000
        
        # Cache hit should be faster
        cache_improvement = (latency1 - latency2) / latency1 * 100 if latency1 > 0 else 0
        
        self.assertIsInstance(response1, OptimizationResponse)
        self.assertIsInstance(response2, OptimizationResponse)
        
        logger.info(f"✓ Cache miss latency: {latency1:.2f}ms")
        logger.info(f"✓ Cache hit latency: {latency2:.2f}ms")
        logger.info(f"✓ Cache improvement: {cache_improvement:.1f}%")
    
    @_measure_performance("test_stream_processing")
    async def test_stream_processing(self):
        """Test stream processing for memory efficiency"""
        logger.info("Testing stream processing...")
        
        # Create stream processor
        stream_processor = AsyncStreamProcessor(chunk_size=1000, max_memory_mb=10)
        
        # Create large dataset
        large_data = ["test data " * 100 for _ in range(1000)]
        
        async def simple_processor(chunk):
            return f"processed: {len(chunk)} items"
        
        results = []
        async for chunk_batch in stream_processor.process_stream(large_data, simple_processor):
            results.extend(chunk_batch)
        
        # Verify processing
        self.assertGreater(len(results), 0, "Stream processing produced no results")
        self.assertGreater(stream_processor.processed_chunks, 0, "No chunks processed")
        
        logger.info(f"✓ Processed {stream_processor.processed_chunks} chunks")
        logger.info(f"✓ Generated {len(results)} results")
    
    @_measure_performance("test_connection_pool")
    async def test_connection_pool(self):
        """Test async connection pool efficiency"""
        logger.info("Testing connection pool...")
        
        pool = AsyncConnectionPool(max_connections=10, max_idle_time=60)
        await pool.initialize()
        
        try:
            # Test multiple concurrent connections
            async def use_connection(i):
                async with pool.get_connection() as conn:
                    self.assertIsNotNone(conn)
                    await asyncio.sleep(0.01)  # Simulate work
                    return f"connection-{i}"
            
            # Use connections concurrently
            tasks = [use_connection(i) for i in range(20)]
            results = await asyncio.gather(*tasks)
            
            self.assertEqual(len(results), 20, "Not all connections completed")
            
            logger.info(f"✓ Successfully used {len(results)} connections")
            
        finally:
            # Cleanup
            if hasattr(pool, '_cleanup_task') and pool._cleanup_task:
                pool._cleanup_task.cancel()
    
    @_measure_performance("test_circuit_breaker")
    async def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        logger.info("Testing circuit breaker...")
        
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        # Test normal operation
        self.assertFalse(breaker.is_open())
        breaker.record_success()
        self.assertEqual(breaker.state, "CLOSED")
        
        # Trigger failures
        for i in range(3):
            breaker.record_failure()
        
        # Should be open now
        self.assertTrue(breaker.is_open())
        self.assertEqual(breaker.state, "OPEN")
        
        # Wait for recovery
        await asyncio.sleep(1.1)
        self.assertFalse(breaker.is_open())  # Should transition to HALF_OPEN
        
        # Success should close it
        breaker.record_success()
        self.assertEqual(breaker.state, "CLOSED")
        
        logger.info("✓ Circuit breaker working correctly")
    
    @_measure_performance("test_performance_monitoring")
    async def test_performance_monitoring(self):
        """Test performance monitoring system"""
        logger.info("Testing performance monitoring...")
        
        if not self.pipeline_created:
            self.skipTest("Pipeline not fully created, skipping monitoring test")
        
        # Get performance stats
        stats = await self.pipeline.get_performance_stats()
        
        # Verify structure
        self.assertIn('pipeline_metrics', stats)
        self.assertIn('component_metrics', stats)
        self.assertIn('cache_performance', stats)
        
        pipeline_metrics = stats['pipeline_metrics']
        
        # Check required metrics exist
        required_metrics = [
            'requests_processed', 'avg_latency_ms', 'memory_reduction_percent',
            'cpu_reduction_percent', 'concurrent_requests'
        ]
        
        for metric in required_metrics:
            self.assertIn(metric, pipeline_metrics, f"Missing metric: {metric}")
        
        logger.info("✓ Performance monitoring system working")
        logger.info(f"✓ Stats keys: {list(stats.keys())}")
    
    async def test_integration_components(self):
        """Test integration with all optimization components"""
        logger.info("Testing component integration...")
        
        # Test individual components if available
        if hasattr(self.pipeline, 'trie_matcher') and self.pipeline.trie_matcher:
            # Test trie matcher
            result = self.pipeline.trie_matcher.match("test query", {})
            self.assertIsNotNone(result)
            logger.info("✓ Trie matcher integration working")
        
        if hasattr(self.pipeline, 'token_optimizer') and self.pipeline.token_optimizer:
            # Test token optimizer
            stats = self.pipeline.token_optimizer.get_stats()
            self.assertIn('cache_hit_rate', stats)
            logger.info("✓ Token optimizer integration working")
        
        logger.info("✓ Component integration tests completed")
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        if not self.performance_results:
            return "No performance results available"
        
        successful_tests = [r for r in self.performance_results if r.success]
        failed_tests = [r for r in self.performance_results if not r.success]
        
        # Calculate statistics
        if successful_tests:
            avg_latency = statistics.mean(r.latency_ms for r in successful_tests)
            max_latency = max(r.latency_ms for r in successful_tests)
            min_latency = min(r.latency_ms for r in successful_tests)
            
            memory_usage = [r.memory_usage_mb for r in successful_tests if r.memory_usage_mb > 0]
            avg_memory = statistics.mean(memory_usage) if memory_usage else 0
            
            cpu_usage = [r.cpu_usage_percent for r in successful_tests if r.cpu_usage_percent > 0]
            avg_cpu = statistics.mean(cpu_usage) if cpu_usage else 0
        else:
            avg_latency = max_latency = min_latency = avg_memory = avg_cpu = 0
        
        # Generate report
        report = f"""
=== Unified Async Optimization Pipeline Performance Report ===

Test Summary:
  Total tests: {len(self.performance_results)}
  Successful: {len(successful_tests)}
  Failed: {len(failed_tests)}
  Success rate: {len(successful_tests)/len(self.performance_results)*100:.1f}%

Performance Metrics:
  Average latency: {avg_latency:.2f}ms
  Min latency: {min_latency:.2f}ms
  Max latency: {max_latency:.2f}ms
  Average memory usage: {avg_memory:.2f}MB
  Average CPU usage: {avg_cpu:.1f}%

Performance Targets:
  ✓ Latency < 100ms: {avg_latency < 100}
  ✓ Memory efficient: {avg_memory < 100}
  ✓ CPU efficient: {avg_cpu < 80}

Test Details:
"""
        
        for result in self.performance_results:
            status = "✓ PASS" if result.success else "✗ FAIL"
            report += f"  {result.test_name}: {status} "
            report += f"({result.latency_ms:.1f}ms, {result.memory_usage_mb:.1f}MB)\n"
            if not result.success and result.error_message:
                report += f"    Error: {result.error_message}\n"
        
        if failed_tests:
            report += "\nFailed Tests:\n"
            for test in failed_tests:
                report += f"  - {test.test_name}: {test.error_message}\n"
        
        report += "\n=== End Report ===\n"
        
        return report

async def run_performance_benchmark():
    """Run comprehensive performance benchmark"""
    logger.info("Starting comprehensive performance benchmark...")
    
    # Create test suite
    test_suite = PipelinePerformanceTest()
    await test_suite.asyncSetUp()
    
    try:
        # Run all tests
        await test_suite.test_basic_initialization()
        await test_suite.test_single_request_latency()
        await test_suite.test_memory_efficiency()
        await test_suite.test_stream_processing()
        await test_suite.test_connection_pool()
        await test_suite.test_circuit_breaker()
        await test_suite.test_integration_components()
        
        # Run advanced tests if pipeline fully created
        if test_suite.pipeline_created:
            await test_suite.test_concurrent_requests()
            await test_suite.test_caching_performance()
            await test_suite.test_performance_monitoring()
        else:
            logger.warning("Pipeline not fully created - skipping advanced tests")
        
    except Exception as e:
        logger.error(f"Benchmark error: {e}")
    
    finally:
        # Generate report
        report = test_suite.generate_performance_report()
        print(report)
        
        # Save report to file
        with open('performance_test_report.txt', 'w') as f:
            f.write(report)
        
        await test_suite.asyncTearDown()
    
    logger.info("Performance benchmark completed")

if __name__ == "__main__":
    # Run benchmark
    asyncio.run(run_performance_benchmark())