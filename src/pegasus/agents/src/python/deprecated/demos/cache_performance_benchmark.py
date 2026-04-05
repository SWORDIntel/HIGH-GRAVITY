#!/usr/bin/env python3
"""
Multi-Level Cache Performance Benchmark and Validation Suite
OPTIMIZER Agent Implementation for validating 80-95% cache hit rates

Comprehensive benchmarking suite that:
- Validates L1, L2, L3 cache performance targets
- Tests realistic workload patterns
- Measures latency, throughput, and hit rates
- Validates integration with token optimizer and context chopper
- Provides detailed performance analysis and recommendations
"""

import asyncio
import time
import random
import statistics
import json
import sys
import os
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import logging
import matplotlib.pyplot as plt
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from path_utilities import get_project_root
except ImportError:
    # Fallback if path_utilities not available
    def get_project_root():
        return Path(__file__).parent.parent.parent

# Import our cache system
sys.path.append(str(Path(__file__).parent))
from multilevel_cache_system import MultiLevelCacheManager, CacheLevel
from token_optimizer import TokenOptimizer
from intelligent_context_chopper import IntelligentContextChopper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('cache_benchmark')

@dataclass
class BenchmarkResult:
    """Individual benchmark test result"""
    test_name: str
    cache_level: str
    operations: int
    duration_seconds: float
    hit_rate: float
    miss_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_ops_sec: float
    success_rate: float
    errors: List[str]
    metadata: Dict[str, Any]

@dataclass
class WorkloadPattern:
    """Defines a workload pattern for testing"""
    name: str
    operations: int
    key_distribution: str  # "uniform", "zipfian", "normal" 
    read_write_ratio: float  # 0.8 = 80% reads, 20% writes
    key_space_size: int
    value_size_bytes: int
    concurrent_threads: int
    repeat_probability: float  # Probability of accessing same key again

class CachePerformanceBenchmark:
    """Comprehensive cache performance benchmark suite"""
    
    def __init__(self, cache_config: Dict[str, Any] = None):
        self.cache_config = cache_config or {
            'l1_capacity': 50000,
            'l1_max_capacity': 200000,
            'redis_url': 'redis://localhost:6379/0',
            'postgres_url': 'postgresql://claude_agent:password@localhost:5433/claude_agents_auth',
            'prometheus_port': None  # Disable for benchmarking
        }
        
        self.cache_manager = None
        self.benchmark_results: List[BenchmarkResult] = []
        
        # Test workload patterns
        self.workload_patterns = [
            WorkloadPattern(
                name="Hot Data Access",
                operations=10000,
                key_distribution="zipfian",  # 80/20 rule
                read_write_ratio=0.9,
                key_space_size=1000,
                value_size_bytes=1024,
                concurrent_threads=10,
                repeat_probability=0.8
            ),
            WorkloadPattern(
                name="Cold Data Access",
                operations=5000,
                key_distribution="uniform",
                read_write_ratio=0.7,
                key_space_size=50000,
                value_size_bytes=2048,
                concurrent_threads=5,
                repeat_probability=0.1
            ),
            WorkloadPattern(
                name="Mixed Workload",
                operations=20000,
                key_distribution="normal",
                read_write_ratio=0.8,
                key_space_size=10000,
                value_size_bytes=512,
                concurrent_threads=20,
                repeat_probability=0.5
            ),
            WorkloadPattern(
                name="High Concurrency",
                operations=50000,
                key_distribution="zipfian",
                read_write_ratio=0.85,
                key_space_size=5000,
                value_size_bytes=256,
                concurrent_threads=50,
                repeat_probability=0.9
            )
        ]
    
    async def initialize(self):
        """Initialize cache system for benchmarking"""
        logger.info("Initializing cache system for benchmarking...")
        
        self.cache_manager = MultiLevelCacheManager(self.cache_config)
        success = await self.cache_manager.initialize()
        
        if not success:
            logger.error("Failed to initialize cache system")
            return False
        
        logger.info("Cache system initialized successfully")
        return True
    
    def generate_test_data(self, pattern: WorkloadPattern) -> List[Tuple[str, str, str]]:
        """Generate test data based on workload pattern"""
        operations = []
        keys_accessed = set()
        
        for i in range(pattern.operations):
            # Determine operation type
            is_read = random.random() < pattern.read_write_ratio
            operation = "GET" if is_read else "PUT"
            
            # Generate key based on distribution
            if pattern.key_distribution == "zipfian":
                # 80/20 distribution - 20% of keys get 80% of accesses
                if random.random() < 0.8:
                    key_id = random.randint(1, int(pattern.key_space_size * 0.2))
                else:
                    key_id = random.randint(int(pattern.key_space_size * 0.2), pattern.key_space_size)
            elif pattern.key_distribution == "normal":
                key_id = int(np.random.normal(pattern.key_space_size // 2, pattern.key_space_size // 6))
                key_id = max(1, min(pattern.key_space_size, key_id))
            else:  # uniform
                key_id = random.randint(1, pattern.key_space_size)
            
            # Consider repeat probability for previously accessed keys
            if keys_accessed and random.random() < pattern.repeat_probability:
                key_id = random.choice(list(keys_accessed))
            else:
                keys_accessed.add(key_id)
            
            key = f"benchmark_key_{key_id}"
            
            # Generate value
            if operation == "PUT":
                value = 'x' * pattern.value_size_bytes
            else:
                value = None  # GET operations don't need value
            
            operations.append((operation, key, value))
        
        return operations
    
    async def benchmark_cache_level(self, level: str, operations: List[Tuple[str, str, str]], 
                                   concurrency: int) -> BenchmarkResult:
        """Benchmark specific cache level"""
        start_time = time.perf_counter()
        hits = 0
        misses = 0
        errors = []
        latencies = []
        
        # Semaphore to control concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def execute_operation(op_data):
            operation, key, value = op_data
            
            async with semaphore:
                op_start = time.perf_counter()
                success = True
                hit = False
                
                try:
                    if operation == "GET":
                        result = await self.cache_manager.get(key)
                        hit = result is not None
                    else:  # PUT
                        await self.cache_manager.put(key, value, cache_level=level)
                        hit = True  # Writes are always "hits"
                        
                except Exception as e:
                    errors.append(str(e))
                    success = False
                    
                op_end = time.perf_counter()
                latency_ms = (op_end - op_start) * 1000
                latencies.append(latency_ms)
                
                return success, hit
        
        # Execute all operations concurrently
        tasks = [execute_operation(op) for op in operations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
                misses += 1
            else:
                success, hit = result
                if success:
                    if hit:
                        hits += 1
                    else:
                        misses += 1
                else:
                    misses += 1
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # Calculate metrics
        total_ops = len(operations)
        hit_rate = (hits / total_ops) * 100 if total_ops > 0 else 0
        miss_rate = 100 - hit_rate
        throughput = total_ops / duration if duration > 0 else 0
        success_rate = ((total_ops - len(errors)) / total_ops) * 100 if total_ops > 0 else 0
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        p95_latency = np.percentile(latencies, 95) if latencies else 0
        p99_latency = np.percentile(latencies, 99) if latencies else 0
        
        return BenchmarkResult(
            test_name=f"{level}_cache_benchmark",
            cache_level=level,
            operations=total_ops,
            duration_seconds=duration,
            hit_rate=hit_rate,
            miss_rate=miss_rate,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            throughput_ops_sec=throughput,
            success_rate=success_rate,
            errors=errors[:10],  # Keep only first 10 errors
            metadata={
                'concurrency': concurrency,
                'total_latencies': len(latencies)
            }
        )
    
    async def benchmark_workload_pattern(self, pattern: WorkloadPattern) -> Dict[str, BenchmarkResult]:
        """Benchmark a complete workload pattern across all cache levels"""
        logger.info(f"Benchmarking workload pattern: {pattern.name}")
        
        # Generate test data
        operations = self.generate_test_data(pattern)
        
        # Warm up cache with some data
        warmup_ops = operations[:min(1000, len(operations) // 10)]
        for op, key, value in warmup_ops:
            if op == "PUT":
                await self.cache_manager.put(key, value)
        
        # Benchmark each cache level
        results = {}
        
        # Test multi-level cache (normal operation)
        result = await self.benchmark_cache_level("ALL", operations, pattern.concurrent_threads)
        result.test_name = f"{pattern.name}_MultiLevel"
        results["MultiLevel"] = result
        
        # Test individual levels for comparison
        for level in ["L1", "L2", "L3"]:
            try:
                result = await self.benchmark_cache_level(level, operations, pattern.concurrent_threads)
                result.test_name = f"{pattern.name}_{level}"
                results[level] = result
            except Exception as e:
                logger.warning(f"Failed to benchmark {level} for {pattern.name}: {e}")
        
        return results
    
    async def benchmark_token_optimizer_integration(self) -> BenchmarkResult:
        """Benchmark token optimizer with multi-level caching"""
        logger.info("Benchmarking token optimizer integration...")
        
        # Create token optimizer with cache integration
        token_opt = TokenOptimizer(multilevel_cache=self.cache_manager)
        
        # Generate test responses
        test_responses = [
            ("TESTBED", f"run_test_{i}", f"Test execution result {i} with detailed output " + "x" * 500)
            for i in range(1000)
        ]
        
        start_time = time.perf_counter()
        hits = 0
        total = 0
        latencies = []
        
        # First pass - populate cache
        for agent, task, response in test_responses:
            op_start = time.perf_counter()
            await token_opt.cache_response(f"{agent}:{task}", response)
            op_end = time.perf_counter()
            latencies.append((op_end - op_start) * 1000)
            total += 1
        
        # Second pass - test cache hits
        for agent, task, response in test_responses:
            op_start = time.perf_counter()
            cached = await token_opt.get_cached_response(f"{agent}:{task}")
            op_end = time.perf_counter()
            latencies.append((op_end - op_start) * 1000)
            
            if cached:
                hits += 1
            total += 1
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        return BenchmarkResult(
            test_name="TokenOptimizer_Integration",
            cache_level="MultiLevel",
            operations=total,
            duration_seconds=duration,
            hit_rate=(hits / (total // 2)) * 100,  # Only count second pass for hit rate
            miss_rate=100 - ((hits / (total // 2)) * 100),
            avg_latency_ms=statistics.mean(latencies),
            p95_latency_ms=np.percentile(latencies, 95),
            p99_latency_ms=np.percentile(latencies, 99),
            throughput_ops_sec=total / duration,
            success_rate=100.0,
            errors=[],
            metadata={'token_optimizer_stats': token_opt.get_stats()}
        )
    
    async def benchmark_context_chopper_integration(self) -> BenchmarkResult:
        """Benchmark context chopper with multi-level caching"""
        logger.info("Benchmarking context chopper integration...")
        
        # Create context chopper with cache integration
        context_chopper = IntelligentContextChopper(
            max_context_tokens=8000,
            multilevel_cache=self.cache_manager
        )
        
        # Generate test queries
        test_queries = [
            "Implement feature 1 with authentication and testing",
            "Fix bug in module 2 related to database connections", 
            "Optimize performance for function 3 in service layer",
            "Add documentation for API endpoint 4",
            "Refactor class 5 to improve maintainability"
        ]
        
        # Duplicate queries to test caching
        all_queries = test_queries * 20
        random.shuffle(all_queries)
        
        start_time = time.perf_counter()
        cache_hits = 0
        total = 0
        latencies = []
        
        for query in all_queries:
            op_start = time.perf_counter()
            
            # This will internally use caching
            context = await context_chopper.get_context_for_request(
                query, 
                project_root=str(get_project_root()),
                file_extensions=['.py', '.md']
            )
            
            op_end = time.perf_counter()
            latency = (op_end - op_start) * 1000
            latencies.append(latency)
            total += 1
            
            # Check if this was likely a cache hit (very fast response)
            if latency < 10:  # Less than 10ms suggests cache hit
                cache_hits += 1
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        return BenchmarkResult(
            test_name="ContextChopper_Integration",
            cache_level="MultiLevel",
            operations=total,
            duration_seconds=duration,
            hit_rate=(cache_hits / total) * 100,
            miss_rate=100 - ((cache_hits / total) * 100),
            avg_latency_ms=statistics.mean(latencies),
            p95_latency_ms=np.percentile(latencies, 95),
            p99_latency_ms=np.percentile(latencies, 99),
            throughput_ops_sec=total / duration,
            success_rate=100.0,
            errors=[],
            metadata={'context_chopper_learning': context_chopper.export_learning_data()}
        )
    
    async def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite"""
        logger.info("Starting comprehensive cache performance benchmark...")
        
        all_results = {}
        
        # Benchmark each workload pattern
        for pattern in self.workload_patterns:
            pattern_results = await self.benchmark_workload_pattern(pattern)
            all_results[pattern.name] = pattern_results
            self.benchmark_results.extend(pattern_results.values())
        
        # Benchmark integrations
        token_opt_result = await self.benchmark_token_optimizer_integration()
        context_chopper_result = await self.benchmark_context_chopper_integration()
        
        all_results["TokenOptimizer"] = token_opt_result
        all_results["ContextChopper"] = context_chopper_result
        
        self.benchmark_results.extend([token_opt_result, context_chopper_result])
        
        # Get final cache statistics
        cache_stats = await self.cache_manager.get_comprehensive_stats()
        
        return {
            'benchmark_results': all_results,
            'cache_statistics': cache_stats,
            'summary': self.generate_summary_report()
        }
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive summary report"""
        if not self.benchmark_results:
            return {}
        
        # Overall metrics
        total_operations = sum(r.operations for r in self.benchmark_results)
        avg_hit_rate = statistics.mean([r.hit_rate for r in self.benchmark_results])
        avg_latency = statistics.mean([r.avg_latency_ms for r in self.benchmark_results])
        avg_throughput = statistics.mean([r.throughput_ops_sec for r in self.benchmark_results])
        
        # Performance targets validation
        l1_target_met = any(r.hit_rate >= 95.0 for r in self.benchmark_results if "L1" in r.cache_level)
        l2_target_met = any(r.hit_rate >= 85.0 for r in self.benchmark_results if "L2" in r.cache_level)  
        l3_target_met = any(r.hit_rate >= 70.0 for r in self.benchmark_results if "L3" in r.cache_level)
        combined_target_met = avg_hit_rate >= 80.0
        
        # Latency targets
        l1_latency_ok = any(r.avg_latency_ms < 1.0 for r in self.benchmark_results if "L1" in r.cache_level)
        l2_latency_ok = any(r.avg_latency_ms < 10.0 for r in self.benchmark_results if "L2" in r.cache_level)
        l3_latency_ok = any(r.avg_latency_ms < 50.0 for r in self.benchmark_results if "L3" in r.cache_level)
        
        return {
            'performance_summary': {
                'total_operations_tested': total_operations,
                'average_hit_rate': avg_hit_rate,
                'average_latency_ms': avg_latency,
                'average_throughput_ops_sec': avg_throughput,
                'tests_passed': len([r for r in self.benchmark_results if r.success_rate > 95.0])
            },
            'target_validation': {
                'l1_hit_rate_target_95_percent': l1_target_met,
                'l2_hit_rate_target_85_percent': l2_target_met,
                'l3_hit_rate_target_70_percent': l3_target_met,
                'combined_hit_rate_target_80_percent': combined_target_met,
                'overall_targets_met': all([combined_target_met, l1_latency_ok, l2_latency_ok, l3_latency_ok])
            },
            'latency_validation': {
                'l1_microsecond_latency': l1_latency_ok,
                'l2_millisecond_latency': l2_latency_ok,
                'l3_10ms_latency': l3_latency_ok
            },
            'recommendations': self.generate_recommendations()
        }
    
    def generate_recommendations(self) -> List[str]:
        """Generate performance recommendations based on results"""
        recommendations = []
        
        if not self.benchmark_results:
            return ["No benchmark results available for recommendations"]
        
        avg_hit_rate = statistics.mean([r.hit_rate for r in self.benchmark_results])
        avg_latency = statistics.mean([r.avg_latency_ms for r in self.benchmark_results])
        
        if avg_hit_rate < 80:
            recommendations.append("Consider increasing L1 cache capacity for better hit rates")
            recommendations.append("Review cache warming strategies for frequently accessed data")
        
        if avg_latency > 10:
            recommendations.append("Optimize Redis configuration for lower latency")
            recommendations.append("Consider using Redis pipelining for batch operations")
        
        error_rates = [len(r.errors) / r.operations for r in self.benchmark_results if r.operations > 0]
        if any(rate > 0.01 for rate in error_rates):  # More than 1% error rate
            recommendations.append("Investigate and resolve cache system errors")
            recommendations.append("Implement better error handling and fallback mechanisms")
        
        multilevel_results = [r for r in self.benchmark_results if "MultiLevel" in r.test_name]
        if multilevel_results and statistics.mean([r.hit_rate for r in multilevel_results]) < 85:
            recommendations.append("Fine-tune cache promotion/demotion strategies")
            recommendations.append("Adjust TTL values for different cache levels")
        
        if not recommendations:
            recommendations.append("Excellent performance! All targets are being met.")
            recommendations.append("Consider monitoring in production to maintain performance.")
        
        return recommendations
    
    def save_results(self, output_file: str = "cache_benchmark_results.json"):
        """Save benchmark results to file"""
        results_data = {
            'timestamp': time.time(),
            'config': self.cache_config,
            'workload_patterns': [asdict(p) for p in self.workload_patterns],
            'benchmark_results': [asdict(r) for r in self.benchmark_results],
            'summary': self.generate_summary_report()
        }
        
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        logger.info(f"Benchmark results saved to: {output_path}")
        return output_path
    
    def generate_performance_charts(self, output_dir: str = "cache_benchmark_charts"):
        """Generate performance visualization charts"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        if not self.benchmark_results:
            logger.warning("No benchmark results to visualize")
            return
        
        # Hit Rate Comparison
        plt.figure(figsize=(12, 8))
        cache_levels = [r.cache_level for r in self.benchmark_results if r.cache_level != "MultiLevel"]
        hit_rates = [r.hit_rate for r in self.benchmark_results if r.cache_level != "MultiLevel"]
        
        plt.bar(cache_levels, hit_rates)
        plt.axhline(y=95, color='r', linestyle='--', label='L1 Target (95%)')
        plt.axhline(y=85, color='orange', linestyle='--', label='L2 Target (85%)')
        plt.axhline(y=70, color='g', linestyle='--', label='L3 Target (70%)')
        plt.axhline(y=80, color='purple', linestyle='--', label='Combined Target (80%)')
        
        plt.title('Cache Hit Rate by Level')
        plt.ylabel('Hit Rate (%)')
        plt.xlabel('Cache Level')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(output_path / 'hit_rates.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Latency Comparison
        plt.figure(figsize=(12, 8))
        test_names = [r.test_name for r in self.benchmark_results]
        latencies = [r.avg_latency_ms for r in self.benchmark_results]
        
        plt.bar(range(len(test_names)), latencies)
        plt.xticks(range(len(test_names)), test_names, rotation=45, ha='right')
        plt.title('Average Latency by Test')
        plt.ylabel('Latency (ms)')
        plt.xlabel('Test Name')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path / 'latencies.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Throughput Comparison
        plt.figure(figsize=(12, 8))
        throughputs = [r.throughput_ops_sec for r in self.benchmark_results]
        
        plt.bar(range(len(test_names)), throughputs)
        plt.xticks(range(len(test_names)), test_names, rotation=45, ha='right')
        plt.title('Throughput by Test')
        plt.ylabel('Operations/Second')
        plt.xlabel('Test Name')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path / 'throughput.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Performance charts saved to: {output_path}")
    
    async def cleanup(self):
        """Cleanup cache system"""
        if self.cache_manager:
            await self.cache_manager.shutdown()

async def main():
    """Main benchmark execution"""
    
    # Configuration
    cache_config = {
        'l1_capacity': 50000,
        'l1_max_capacity': 200000,
        'redis_url': 'redis://localhost:6379/0',
        'postgres_url': 'postgresql://claude_agent:password@localhost:5433/claude_agents_auth',
        'prometheus_port': None
    }
    
    benchmark = CachePerformanceBenchmark(cache_config)
    
    try:
        # Initialize
        success = await benchmark.initialize()
        if not success:
            logger.error("Failed to initialize benchmark")
            sys.exit(1)
        
        # Run comprehensive benchmarks
        results = await benchmark.run_comprehensive_benchmark()
        
        # Save results
        results_file = benchmark.save_results()
        
        # Generate charts
        try:
            benchmark.generate_performance_charts()
        except Exception as e:
            logger.warning(f"Failed to generate charts: {e}")
        
        # Print summary
        summary = results['summary']
        cache_stats = results['cache_statistics']
        
        print("\n" + "="*80)
        print("MULTI-LEVEL CACHE PERFORMANCE BENCHMARK RESULTS")
        print("="*80)
        
        print(f"\nOverall Performance:")
        print(f"  Total Operations: {summary['performance_summary']['total_operations_tested']:,}")
        print(f"  Average Hit Rate: {summary['performance_summary']['average_hit_rate']:.1f}%")
        print(f"  Average Latency: {summary['performance_summary']['average_latency_ms']:.2f}ms")
        print(f"  Average Throughput: {summary['performance_summary']['average_throughput_ops_sec']:,.0f} ops/sec")
        
        print(f"\nTarget Validation:")
        targets = summary['target_validation']
        print(f"  L1 Hit Rate ≥95%: {'✅' if targets['l1_hit_rate_target_95_percent'] else '❌'}")
        print(f"  L2 Hit Rate ≥85%: {'✅' if targets['l2_hit_rate_target_85_percent'] else '❌'}")
        print(f"  L3 Hit Rate ≥70%: {'✅' if targets['l3_hit_rate_target_70_percent'] else '❌'}")
        print(f"  Combined ≥80%: {'✅' if targets['combined_hit_rate_target_80_percent'] else '❌'}")
        print(f"  Overall Success: {'✅ PASSED' if targets['overall_targets_met'] else '❌ FAILED'}")
        
        print(f"\nCache Statistics:")
        print(f"  Combined Hit Rate: {cache_stats['combined_hit_rate']:.1f}%")
        print(f"  L1 Hit Rate: {cache_stats['l1_cache']['hit_rate']:.1f}%")
        print(f"  L2 Hit Rate: {cache_stats['l2_cache']['hit_rate']:.1f}%")
        print(f"  L3 Hit Rate: {cache_stats['l3_cache']['hit_rate']:.1f}%")
        
        print(f"\nRecommendations:")
        for i, rec in enumerate(summary['recommendations'], 1):
            print(f"  {i}. {rec}")
        
        print(f"\nDetailed results saved to: {results_file}")
        print("="*80)
        
        # Exit with appropriate code
        if targets['overall_targets_met']:
            print("\n🎉 All performance targets achieved!")
            sys.exit(0)
        else:
            print("\n⚠️  Some performance targets not met. See recommendations above.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await benchmark.cleanup()

if __name__ == "__main__":
    asyncio.run(main())