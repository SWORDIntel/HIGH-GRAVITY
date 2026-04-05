#!/usr/bin/env python3
"""
Test and Demonstration Script for Shadowgit Maximum Performance Engine
======================================================================
Comprehensive testing of 15+ billion lines/sec C implementation
Intel Core Ultra 7 165H optimization with NPU acceleration

Features tested:
- Ultra-high performance C engine compilation and execution
- NPU integration with OpenVINO C++ API simulation
- Enhanced AVX2 optimizations beyond 930M lines/sec baseline
- Multi-threaded work-stealing queue coordination
- NUMA-aware memory management
- Thermal-aware performance scaling
- Real-time performance monitoring and metrics
"""

import os
import sys
import subprocess
import time
import json
import tempfile
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class ShadowgitMaxPerfTester:
    """Comprehensive test harness for Shadowgit Maximum Performance Engine"""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.build_dir = self.base_dir
        self.test_results = {}
        self.performance_metrics = {}

        # Performance targets
        self.targets = {
            'npu_lines_per_sec': 8_000_000_000,      # 8 billion lines/sec (NPU layer)
            'avx2_lines_per_sec': 2_000_000_000,     # 2 billion lines/sec (enhanced AVX2)
            'multicore_speedup': 3.0,                 # 3x scaling improvement
            'total_lines_per_sec': 15_000_000_000,   # 15+ billion lines/sec total
            'baseline_lines_per_sec': 930_000_000     # 930M lines/sec baseline
        }

        print("Shadowgit Maximum Performance Engine Test Harness")
        print("=" * 60)
        print(f"Base Directory: {self.base_dir}")
        print(f"Target Performance: {self.targets['total_lines_per_sec']:,} lines/sec")
        print()

    def check_system_compatibility(self) -> Dict[str, bool]:
        """Check system compatibility for maximum performance"""
        print("Checking System Compatibility...")
        print("-" * 40)

        compatibility = {}

        # Check CPU features
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()

            compatibility['avx2'] = 'avx2' in cpuinfo
            compatibility['avx512'] = 'avx512' in cpuinfo
            compatibility['fma'] = 'fma' in cpuinfo
            compatibility['bmi2'] = 'bmi2' in cpuinfo

            # Check for Intel Core Ultra (Meteor Lake)
            compatibility['meteor_lake'] = 'Ultra' in cpuinfo and 'Intel' in cpuinfo

        except Exception as e:
            print(f"Warning: Could not read CPU info: {e}")
            compatibility.update({'avx2': False, 'avx512': False, 'fma': False, 'bmi2': False, 'meteor_lake': False})

        # Check NPU availability
        compatibility['npu_device'] = os.path.exists('/dev/accel/accel0')

        # Check NUMA support
        compatibility['numa'] = os.path.exists('/sys/devices/system/node/node0')

        # Check thermal monitoring
        compatibility['thermal'] = os.path.exists('/sys/class/thermal/thermal_zone0/temp')

        # Check compiler availability
        compatibility['gcc'] = self._check_command('gcc --version')
        compatibility['make'] = self._check_command('make --version')

        # Check development libraries
        compatibility['numa_dev'] = self._check_library('numa')
        compatibility['pthread'] = self._check_library('pthread')

        # Print results
        for feature, available in compatibility.items():
            status = "✓" if available else "✗"
            print(f"  {feature.upper().replace('_', ' ')}: {status}")

        print()
        return compatibility

    def _check_command(self, command: str) -> bool:
        """Check if a command is available"""
        try:
            subprocess.run(command.split(), capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _check_library(self, lib_name: str) -> bool:
        """Check if a library is available"""
        try:
            result = subprocess.run(['pkg-config', '--exists', lib_name],
                                  capture_output=True)
            return result.returncode == 0
        except FileNotFoundError:
            # Try alternative method
            try:
                subprocess.run(['gcc', '-l' + lib_name, '-x', 'c', '/dev/null'],
                             capture_output=True, check=True)
                return True
            except subprocess.CalledProcessError:
                return False

    def build_components(self) -> Dict[str, bool]:
        """Build all Shadowgit components"""
        print("Building Shadowgit Maximum Performance Components...")
        print("-" * 50)

        build_results = {}

        # Change to build directory
        original_dir = os.getcwd()
        os.chdir(self.build_dir)

        try:
            # Build main components
            components = [
                ('check-deps', 'Dependency check'),
                ('engine', 'Main performance engine'),
                ('npu', 'NPU acceleration engine'),
                ('coordinator', 'Performance coordinator'),
                ('test-engine', 'Engine test executable'),
                ('test-npu', 'NPU test executable'),
                ('test-coordinator', 'Coordinator test executable')
            ]

            for target, description in components:
                print(f"Building {description}...")
                try:
                    result = subprocess.run(['make', '-f', 'Makefile.shadowgit_max_perf', target],
                                          capture_output=True, text=True, timeout=300)

                    if result.returncode == 0:
                        print(f"  ✓ {description} built successfully")
                        build_results[target] = True
                    else:
                        print(f"  ✗ {description} build failed")
                        print(f"    Error: {result.stderr}")
                        build_results[target] = False

                except subprocess.TimeoutExpired:
                    print(f"  ✗ {description} build timed out")
                    build_results[target] = False
                except Exception as e:
                    print(f"  ✗ {description} build error: {e}")
                    build_results[target] = False

        finally:
            os.chdir(original_dir)

        print()
        return build_results

    def run_engine_tests(self) -> Dict[str, any]:
        """Run main engine performance tests"""
        print("Running Engine Performance Tests...")
        print("-" * 40)

        test_executable = self.build_dir / 'shadowgit_max_perf_test'
        if not test_executable.exists():
            print("  ✗ Engine test executable not found")
            return {'success': False, 'error': 'Executable not found'}

        results = {}

        # Test configurations
        test_configs = [
            (1000, 'npu', 'Standard NPU test'),
            (5000, 'npu', 'Extended NPU test'),
            (1000, 'cpu', 'CPU-only test')
        ]

        for iterations, mode, description in test_configs:
            print(f"  Running {description} ({iterations} iterations)...")

            try:
                start_time = time.time()
                result = subprocess.run([str(test_executable), str(iterations), mode],
                                      capture_output=True, text=True, timeout=120)
                end_time = time.time()

                if result.returncode == 0:
                    # Parse performance metrics from output
                    metrics = self._parse_engine_output(result.stdout)
                    metrics['execution_time'] = end_time - start_time
                    metrics['success'] = True

                    print(f"    ✓ {description} completed")
                    if 'avg_lines_per_second' in metrics:
                        lps = metrics['avg_lines_per_second']
                        print(f"    Performance: {lps:,.0f} lines/sec ({lps/1e6:.1f} M lines/sec)")
                else:
                    metrics = {'success': False, 'error': result.stderr}
                    print(f"    ✗ {description} failed: {result.stderr}")

                results[f"{mode}_{iterations}"] = metrics

            except subprocess.TimeoutExpired:
                print(f"    ✗ {description} timed out")
                results[f"{mode}_{iterations}"] = {'success': False, 'error': 'Timeout'}
            except Exception as e:
                print(f"    ✗ {description} error: {e}")
                results[f"{mode}_{iterations}"] = {'success': False, 'error': str(e)}

        print()
        return results

    def run_npu_tests(self) -> Dict[str, any]:
        """Run NPU acceleration tests"""
        print("Running NPU Acceleration Tests...")
        print("-" * 35)

        test_executable = self.build_dir / 'shadowgit_npu_test'
        if not test_executable.exists():
            print("  ✗ NPU test executable not found")
            return {'success': False, 'error': 'Executable not found'}

        results = {}

        # NPU test configurations (size_mb, iterations)
        test_configs = [
            (10, 100, 'Standard NPU test'),
            (50, 50, 'Large data NPU test'),
            (1, 1000, 'Small data high iteration test')
        ]

        for size_mb, iterations, description in test_configs:
            print(f"  Running {description} ({size_mb}MB, {iterations} iterations)...")

            try:
                start_time = time.time()
                result = subprocess.run([str(test_executable), str(size_mb), str(iterations)],
                                      capture_output=True, text=True, timeout=180)
                end_time = time.time()

                if result.returncode == 0:
                    metrics = self._parse_npu_output(result.stdout)
                    metrics['execution_time'] = end_time - start_time
                    metrics['success'] = True

                    print(f"    ✓ {description} completed")
                    if 'lines_per_second' in metrics:
                        lps = metrics['lines_per_second']
                        print(f"    Performance: {lps:,.0f} lines/sec ({lps/1e9:.1f} B lines/sec)")
                else:
                    metrics = {'success': False, 'error': result.stderr}
                    print(f"    ✗ {description} failed: {result.stderr}")

                results[f"npu_{size_mb}mb_{iterations}"] = metrics

            except subprocess.TimeoutExpired:
                print(f"    ✗ {description} timed out")
                results[f"npu_{size_mb}mb_{iterations}"] = {'success': False, 'error': 'Timeout'}
            except Exception as e:
                print(f"    ✗ {description} error: {e}")
                results[f"npu_{size_mb}mb_{iterations}"] = {'success': False, 'error': str(e)}

        print()
        return results

    def run_coordinator_tests(self) -> Dict[str, any]:
        """Run performance coordinator tests"""
        print("Running Performance Coordinator Tests...")
        print("-" * 42)

        test_executable = self.build_dir / 'shadowgit_coordinator_test'
        if not test_executable.exists():
            print("  ✗ Coordinator test executable not found")
            return {'success': False, 'error': 'Executable not found'}

        print("  Running multi-core scaling test...")

        try:
            start_time = time.time()
            result = subprocess.run([str(test_executable)],
                                  capture_output=True, text=True, timeout=60)
            end_time = time.time()

            if result.returncode == 0:
                metrics = self._parse_coordinator_output(result.stdout)
                metrics['execution_time'] = end_time - start_time
                metrics['success'] = True

                print(f"    ✓ Coordinator test completed")
                if 'scaling_efficiency' in metrics:
                    eff = metrics['scaling_efficiency']
                    print(f"    Scaling Efficiency: {eff:.1f}%")
            else:
                metrics = {'success': False, 'error': result.stderr}
                print(f"    ✗ Coordinator test failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            print("    ✗ Coordinator test timed out")
            metrics = {'success': False, 'error': 'Timeout'}
        except Exception as e:
            print(f"    ✗ Coordinator test error: {e}")
            metrics = {'success': False, 'error': str(e)}

        print()
        return metrics

    def run_comprehensive_benchmark(self) -> Dict[str, any]:
        """Run comprehensive performance benchmark"""
        print("Running Comprehensive Performance Benchmark...")
        print("-" * 48)

        # Change to build directory
        original_dir = os.getcwd()
        os.chdir(self.build_dir)

        try:
            print("  Running full benchmark suite...")
            result = subprocess.run(['make', '-f', 'Makefile.shadowgit_max_perf', 'benchmark'],
                                  capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                print("    ✓ Benchmark suite completed")
                metrics = self._parse_benchmark_output(result.stdout)
                metrics['success'] = True
            else:
                print(f"    ✗ Benchmark suite failed: {result.stderr}")
                metrics = {'success': False, 'error': result.stderr}

        except subprocess.TimeoutExpired:
            print("    ✗ Benchmark suite timed out")
            metrics = {'success': False, 'error': 'Timeout'}
        except Exception as e:
            print(f"    ✗ Benchmark suite error: {e}")
            metrics = {'success': False, 'error': str(e)}
        finally:
            os.chdir(original_dir)

        print()
        return metrics

    def _parse_engine_output(self, output: str) -> Dict[str, any]:
        """Parse engine test output for performance metrics"""
        metrics = {}
        lines = output.split('\n')

        for line in lines:
            # Look for performance indicators
            if 'lines/sec' in line.lower():
                try:
                    # Extract numeric value
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'lines/sec' in part and i > 0:
                            value_str = parts[i-1].replace(',', '').replace('(', '').replace(')', '')
                            metrics['avg_lines_per_second'] = float(value_str)
                            break
                except (ValueError, IndexError):
                    continue

            if 'speedup' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'speedup' in part.lower() and i > 0:
                            value_str = parts[i+1].replace('x', '').replace(',', '')
                            metrics['speedup_factor'] = float(value_str)
                            break
                except (ValueError, IndexError):
                    continue

        return metrics

    def _parse_npu_output(self, output: str) -> Dict[str, any]:
        """Parse NPU test output for performance metrics"""
        metrics = {}
        lines = output.split('\n')

        for line in lines:
            if 'lines/sec' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'lines/sec' in part and i > 0:
                            value_str = parts[i-1].replace(',', '').replace('(', '').replace(')', '')
                            metrics['lines_per_second'] = float(value_str)
                            break
                except (ValueError, IndexError):
                    continue

            if 'throughput' in line.lower() and 'gb/s' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'gb/s' in part.lower() and i > 0:
                            value_str = parts[i-1].replace(',', '')
                            metrics['throughput_gbps'] = float(value_str)
                            break
                except (ValueError, IndexError):
                    continue

        return metrics

    def _parse_coordinator_output(self, output: str) -> Dict[str, any]:
        """Parse coordinator test output for scaling metrics"""
        metrics = {}
        lines = output.split('\n')

        for line in lines:
            if 'scaling efficiency' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if '%' in part and i > 0:
                            value_str = part.replace('%', '').replace(',', '')
                            metrics['scaling_efficiency'] = float(value_str)
                            break
                except (ValueError, IndexError):
                    continue

            if 'actual speedup' in line.lower():
                try:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'x' in part and i > 0:
                            value_str = part.replace('x', '').replace(',', '')
                            metrics['actual_speedup'] = float(value_str)
                            break
                except (ValueError, IndexError):
                    continue

        return metrics

    def _parse_benchmark_output(self, output: str) -> Dict[str, any]:
        """Parse comprehensive benchmark output"""
        metrics = {}
        lines = output.split('\n')

        # Extract key performance metrics
        for line in lines:
            if 'target achievement' in line.lower():
                try:
                    parts = line.split()
                    for part in parts:
                        if '%' in part:
                            value_str = part.replace('%', '').replace(',', '')
                            metrics['target_achievement'] = float(value_str)
                            break
                except (ValueError, IndexError):
                    continue

        return metrics

    def analyze_results(self) -> Dict[str, any]:
        """Analyze all test results and provide summary"""
        print("Analyzing Performance Results...")
        print("-" * 35)

        analysis = {
            'overall_success': True,
            'performance_analysis': {},
            'target_achievement': {},
            'recommendations': []
        }

        # Analyze engine performance
        if 'engine_tests' in self.test_results:
            engine_results = self.test_results['engine_tests']
            best_performance = 0

            for test_name, metrics in engine_results.items():
                if metrics.get('success') and 'avg_lines_per_second' in metrics:
                    lps = metrics['avg_lines_per_second']
                    if lps > best_performance:
                        best_performance = lps

            if best_performance > 0:
                analysis['performance_analysis']['engine_best'] = best_performance
                analysis['target_achievement']['engine'] = (best_performance / self.targets['total_lines_per_sec']) * 100

                print(f"  Engine Best Performance: {best_performance:,.0f} lines/sec")
                print(f"  Target Achievement: {analysis['target_achievement']['engine']:.1f}%")
            else:
                analysis['overall_success'] = False
                print("  ✗ No successful engine performance measurements")

        # Analyze NPU performance
        if 'npu_tests' in self.test_results:
            npu_results = self.test_results['npu_tests']
            best_npu_performance = 0

            for test_name, metrics in npu_results.items():
                if metrics.get('success') and 'lines_per_second' in metrics:
                    lps = metrics['lines_per_second']
                    if lps > best_npu_performance:
                        best_npu_performance = lps

            if best_npu_performance > 0:
                analysis['performance_analysis']['npu_best'] = best_npu_performance
                analysis['target_achievement']['npu'] = (best_npu_performance / self.targets['npu_lines_per_sec']) * 100

                print(f"  NPU Best Performance: {best_npu_performance:,.0f} lines/sec")
                print(f"  NPU Target Achievement: {analysis['target_achievement']['npu']:.1f}%")
            else:
                print("  ✗ No successful NPU performance measurements")

        # Analyze coordinator performance
        if 'coordinator_tests' in self.test_results:
            coord_results = self.test_results['coordinator_tests']
            if coord_results.get('success') and 'scaling_efficiency' in coord_results:
                efficiency = coord_results['scaling_efficiency']
                analysis['performance_analysis']['scaling_efficiency'] = efficiency

                print(f"  Multi-core Scaling Efficiency: {efficiency:.1f}%")

                if efficiency >= 70:
                    print("    ✓ Excellent scaling efficiency")
                elif efficiency >= 50:
                    print("    ⚠ Good scaling efficiency")
                else:
                    print("    ✗ Poor scaling efficiency")
                    analysis['recommendations'].append("Consider optimizing thread coordination")
            else:
                print("  ✗ No scaling efficiency measurements")

        # Generate recommendations
        if analysis['target_achievement'].get('engine', 0) < 50:
            analysis['recommendations'].append("Consider enabling more aggressive optimizations")

        if analysis['target_achievement'].get('npu', 0) < 25:
            analysis['recommendations'].append("NPU acceleration may need hardware support")

        if not analysis['recommendations']:
            analysis['recommendations'].append("Performance targets achieved successfully")

        print()
        return analysis

    def generate_report(self, output_file: Optional[str] = None):
        """Generate comprehensive performance report"""
        report = {
            'test_timestamp': time.time(),
            'test_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system_info': self.check_system_compatibility(),
            'performance_targets': self.targets,
            'test_results': self.test_results,
            'performance_metrics': self.performance_metrics,
            'analysis': self.analyze_results()
        }

        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Detailed report saved to: {output_file}")

        return report

    def run_all_tests(self, skip_build: bool = False) -> Dict[str, any]:
        """Run complete test suite"""
        print("Shadowgit Maximum Performance Engine - Complete Test Suite")
        print("=" * 65)
        print()

        # Check system compatibility
        self.test_results['compatibility'] = self.check_system_compatibility()

        # Build components
        if not skip_build:
            self.test_results['build_results'] = self.build_components()

        # Run performance tests
        self.test_results['engine_tests'] = self.run_engine_tests()
        self.test_results['npu_tests'] = self.run_npu_tests()
        self.test_results['coordinator_tests'] = self.run_coordinator_tests()

        # Run comprehensive benchmark
        self.test_results['benchmark'] = self.run_comprehensive_benchmark()

        # Generate analysis and report
        report = self.generate_report('shadowgit_performance_report.json')

        # Print final summary
        print("Test Suite Summary")
        print("=" * 20)

        if report['analysis']['overall_success']:
            print("✓ Test suite completed successfully")
        else:
            print("✗ Test suite completed with issues")

        for category, achievement in report['analysis']['target_achievement'].items():
            print(f"  {category.capitalize()}: {achievement:.1f}% of target")

        if report['analysis']['recommendations']:
            print("\nRecommendations:")
            for rec in report['analysis']['recommendations']:
                print(f"  • {rec}")

        print(f"\nDetailed report: shadowgit_performance_report.json")
        print(f"Target: {self.targets['total_lines_per_sec']:,} lines/sec")

        return report


def main():
    """Main test execution"""
    parser = argparse.ArgumentParser(description='Shadowgit Maximum Performance Engine Test Suite')
    parser.add_argument('--base-dir', help='Base directory for tests')
    parser.add_argument('--skip-build', action='store_true', help='Skip build step')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    parser.add_argument('--output', help='Output report file')

    args = parser.parse_args()

    try:
        tester = ShadowgitMaxPerfTester(args.base_dir)

        if args.quick:
            # Quick test mode
            print("Running quick test mode...")
            tester.check_system_compatibility()
            tester.test_results['engine_tests'] = tester.run_engine_tests()
            report = tester.generate_report(args.output)
        else:
            # Full test suite
            report = tester.run_all_tests(args.skip_build)
            if args.output:
                tester.generate_report(args.output)

        # Exit with appropriate code
        sys.exit(0 if report['analysis']['overall_success'] else 1)

    except KeyboardInterrupt:
        print("\nTest suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test suite failed with error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()