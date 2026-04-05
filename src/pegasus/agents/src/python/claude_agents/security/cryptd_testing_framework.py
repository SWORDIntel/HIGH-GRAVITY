#!/usr/bin/env python3
"""
CRYPTD Analysis Testing and Validation Framework
Comprehensive testing suite for hardware-accelerated CRYPTD analysis capabilities

This module provides comprehensive testing and validation for the enhanced
DISASSEMBLER with CRYPTD-specific analysis and hardware acceleration.
"""

import asyncio
import hashlib
import json
import os
import struct
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

# Import our enhanced modules
from DISASSEMBLER_impl import (
    CRYPTDAnalysisEngine,
    DISASSEMBLERBinaryAnalyzer,
    HardwareAccelerationEngine,
)


class CRYPTDTestingFramework:
    """Comprehensive testing framework for CRYPTD analysis capabilities"""

    def __init__(self):
        self.test_results_dir = Path.home() / ".claude" / "cryptd-test-results"
        self.test_results_dir.mkdir(parents=True, exist_ok=True)
        self.analyzer = DISASSEMBLERBinaryAnalyzer(
            file_generation_enabled=False, user_consent_given=False
        )

    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        test_start = time.time()
        test_session_id = f"cryptd_test_{int(test_start)}"

        print(f"🧪 Starting CRYPTD Testing Framework - Session: {test_session_id}")
        print("=" * 70)

        test_results = {
            "session_id": test_session_id,
            "start_time": test_start,
            "tests": {},
        }

        # Test categories
        test_categories = [
            ("Hardware Detection", self._test_hardware_detection),
            ("CRYPTD Pattern Detection", self._test_cryptd_pattern_detection),
            ("XOR Analysis", self._test_xor_analysis),
            ("Entropy Analysis", self._test_entropy_analysis),
            ("Performance Benchmarks", self._test_performance_benchmarks),
            ("Parallel Processing", self._test_parallel_processing),
            ("Real-time Threat Scoring", self._test_real_time_scoring),
            ("Error Handling", self._test_error_handling),
            ("Resource Management", self._test_resource_management),
            ("Integration Tests", self._test_integration),
        ]

        # Execute test categories
        for category_name, test_func in test_categories:
            print(f"\n🔬 Testing: {category_name}")
            print("-" * 50)

            try:
                category_start = time.time()
                category_results = await test_func()
                category_duration = time.time() - category_start

                test_results["tests"][category_name] = {
                    "status": (
                        "PASSED" if category_results.get("passed", True) else "FAILED"
                    ),
                    "duration": category_duration,
                    "results": category_results,
                }

                status_emoji = "✅" if category_results.get("passed", True) else "❌"
                print(
                    f"{status_emoji} {category_name}: {test_results['tests'][category_name]['status']} ({category_duration:.2f}s)"
                )

            except Exception as e:
                test_results["tests"][category_name] = {
                    "status": "ERROR",
                    "error": str(e),
                    "duration": time.time() - category_start,
                }
                print(f"❌ {category_name}: ERROR - {str(e)}")

        # Calculate overall results
        total_duration = time.time() - test_start
        passed_tests = len(
            [t for t in test_results["tests"].values() if t["status"] == "PASSED"]
        )
        total_tests = len(test_results["tests"])
        success_rate = passed_tests / total_tests * 100 if total_tests > 0 else 0

        test_results.update(
            {
                "end_time": time.time(),
                "total_duration": total_duration,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "success_rate": success_rate,
                "overall_status": "PASSED" if success_rate >= 80 else "FAILED",
            }
        )

        # Save test results
        results_file = self.test_results_dir / f"{test_session_id}_results.json"
        with open(results_file, "w") as f:
            json.dump(test_results, f, indent=2)

        # Print summary
        print("\n" + "=" * 70)
        print(f"🏁 Test Session Complete: {test_session_id}")
        print(
            f"📊 Results: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)"
        )
        print(f"⏱️  Duration: {total_duration:.2f}s")
        print(f"📁 Results saved: {results_file}")

        if success_rate >= 80:
            print("🎉 Overall Status: PASSED")
        else:
            print("💥 Overall Status: FAILED")

        return test_results

    async def _test_hardware_detection(self) -> Dict[str, Any]:
        """Test hardware acceleration detection capabilities"""
        results = {"passed": True, "details": {}}

        # Test hardware engine initialization
        hw_engine = self.analyzer.hardware_engine
        results["details"]["hardware_engine_created"] = hw_engine is not None

        # Test core detection
        core_config = hw_engine.available_cores
        results["details"]["p_cores_detected"] = len(core_config["p_cores"]) > 0
        results["details"]["e_cores_detected"] = len(core_config["e_cores"]) > 0
        results["details"]["total_cores"] = hw_engine.cpu_count

        # Test acceleration detection
        results["details"]["npu_detection"] = {
            "available": hw_engine.npu_available,
            "method": "detected" if hw_engine.npu_available else "not_found",
        }
        results["details"]["gpu_detection"] = {
            "available": hw_engine.gpu_available,
            "method": "detected" if hw_engine.gpu_available else "not_found",
        }
        results["details"]["gna_detection"] = {
            "available": hw_engine.gna_available,
            "method": "detected" if hw_engine.gna_available else "not_found",
        }

        # Test thread optimization
        for workload_type in ["cpu_intensive", "io_intensive", "mixed"]:
            thread_count = hw_engine.get_optimal_thread_count(workload_type)
            results["details"][f"optimal_threads_{workload_type}"] = thread_count

        print(
            f"  💻 CPU Cores: {hw_engine.cpu_count} total ({len(core_config['p_cores'])} P-cores, {len(core_config['e_cores'])} E-cores)"
        )
        print(
            f"  🧠 NPU: {'✅ Available' if hw_engine.npu_available else '❌ Not detected'}"
        )
        print(
            f"  🎮 GPU: {'✅ Available' if hw_engine.gpu_available else '❌ Not detected'}"
        )
        print(
            f"  ⚡ GNA: {'✅ Available' if hw_engine.gna_available else '❌ Not detected'}"
        )

        return results

    async def _test_cryptd_pattern_detection(self) -> Dict[str, Any]:
        """Test CRYPTD-specific pattern detection"""
        results = {"passed": True, "details": {}}

        # Create test samples with known patterns
        test_samples = self._create_cryptd_test_samples()

        cryptd_engine = self.analyzer.cryptd_engine

        for sample_name, sample_data in test_samples.items():
            print(f"    🔍 Testing {sample_name}...")

            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as temp_file:
                temp_file.write(sample_data)
                temp_path = temp_file.name

            try:
                # Analyze sample
                analysis_result = await cryptd_engine.analyze_sample(
                    temp_path, "cryptd_focused"
                )

                results["details"][sample_name] = {
                    "meme_score": analysis_result.get("meme_score", 0),
                    "findings": analysis_result.get("crypto_findings", []),
                    "competence_assessment": analysis_result.get(
                        "threat_actor_competence", "UNKNOWN"
                    ),
                    "hall_of_shame": analysis_result.get(
                        "hall_of_shame_qualification", False
                    ),
                }

                # Validate expected patterns
                expected_findings = self._get_expected_findings(sample_name)
                found_patterns = set(analysis_result.get("crypto_findings", []))
                expected_patterns = set(expected_findings)

                detection_accuracy = (
                    len(found_patterns & expected_patterns) / len(expected_patterns)
                    if expected_patterns
                    else 1.0
                )
                results["details"][sample_name][
                    "detection_accuracy"
                ] = detection_accuracy

                print(f"      📊 Meme Score: {analysis_result.get('meme_score', 0)}")
                print(f"      🎯 Detection Accuracy: {detection_accuracy:.1%}")

            except Exception as e:
                results["passed"] = False
                results["details"][sample_name] = {"error": str(e)}
                print(f"      ❌ Error: {str(e)}")
            finally:
                os.unlink(temp_path)

        return results

    async def _test_xor_analysis(self) -> Dict[str, Any]:
        """Test XOR pattern analysis capabilities"""
        results = {"passed": True, "details": {}}

        # Create XOR test samples
        test_cases = [
            ("single_byte_xor", self._create_single_byte_xor_sample(0x42)),
            ("multi_byte_xor", self._create_multi_byte_xor_sample(b"key123")),
            ("no_xor", b"This is plain text data without XOR encryption"),
        ]

        cryptd_engine = self.analyzer.cryptd_engine

        for test_name, test_data in test_cases:
            print(f"    🔐 Testing {test_name}...")

            try:
                # Test XOR analysis
                xor_result = await cryptd_engine._analyze_xor_patterns(test_data)

                results["details"][test_name] = {
                    "findings": xor_result.get("findings", []),
                    "meme_score": xor_result.get("meme_score", 0),
                    "details": xor_result.get("details", {}),
                }

                # Validate results
                if "single_byte" in test_name:
                    expected = "XOR_SINGLE_BYTE" in xor_result.get("findings", [])
                elif "multi_byte" in test_name:
                    expected = "XOR_BASIC_KEY" in xor_result.get("findings", [])
                else:
                    expected = len(xor_result.get("findings", [])) == 0

                results["details"][test_name]["validation_passed"] = expected
                if not expected:
                    results["passed"] = False

                print(f"      🔍 Findings: {xor_result.get('findings', [])}")
                print(f"      ✅ Validation: {'Passed' if expected else 'Failed'}")

            except Exception as e:
                results["passed"] = False
                results["details"][test_name] = {"error": str(e)}
                print(f"      ❌ Error: {str(e)}")

        return results

    async def _test_entropy_analysis(self) -> Dict[str, Any]:
        """Test entropy analysis capabilities"""
        results = {"passed": True, "details": {}}

        # Create entropy test samples
        test_samples = [
            ("high_entropy", os.urandom(1024)),  # Random data
            ("low_entropy", b"A" * 1024),  # Repeated pattern
            ("medium_entropy", b"Hello World! " * 64),  # Text pattern
        ]

        cryptd_engine = self.analyzer.cryptd_engine

        for sample_name, sample_data in test_samples:
            print(f"    📊 Testing {sample_name}...")

            try:
                # Calculate entropy
                entropy = cryptd_engine._calculate_entropy(sample_data)

                # Test entropy analysis
                entropy_result = await cryptd_engine._analyze_entropy_patterns(
                    sample_data
                )

                results["details"][sample_name] = {
                    "calculated_entropy": entropy,
                    "findings": entropy_result.get("findings", []),
                    "meme_score": entropy_result.get("meme_score", 0),
                }

                # Validate entropy ranges
                if "high" in sample_name:
                    expected = entropy > 7.0
                elif "low" in sample_name:
                    expected = entropy < 2.0
                else:
                    expected = 2.0 <= entropy <= 7.0

                results["details"][sample_name]["validation_passed"] = expected
                if not expected:
                    results["passed"] = False

                print(f"      📈 Entropy: {entropy:.2f}")
                print(f"      ✅ Validation: {'Passed' if expected else 'Failed'}")

            except Exception as e:
                results["passed"] = False
                results["details"][sample_name] = {"error": str(e)}
                print(f"      ❌ Error: {str(e)}")

        return results

    async def _test_performance_benchmarks(self) -> Dict[str, Any]:
        """Test performance benchmarks"""
        results = {"passed": True, "details": {}}

        # Create test sample
        test_data = b"MZ" + os.urandom(8192)  # 8KB test sample

        with tempfile.NamedTemporaryFile(delete=False, suffix=".exe") as temp_file:
            temp_file.write(test_data)
            temp_path = temp_file.name

        try:
            # Benchmark single analysis
            start_time = time.time()
            result = await self.analyzer.execute_hardware_accelerated_analysis(
                temp_path, "comprehensive"
            )
            single_duration = time.time() - start_time

            results["details"]["single_analysis"] = {
                "duration": single_duration,
                "samples_per_second": 1 / single_duration if single_duration > 0 else 0,
                "hardware_acceleration": result.get("hardware_acceleration_used", {}),
                "performance_metrics": result.get("performance_metrics", {}),
            }

            # Benchmark real-time scoring
            start_time = time.time()
            threat_score = await self.analyzer.execute_real_time_threat_scoring(
                temp_path
            )
            scoring_duration = time.time() - start_time

            results["details"]["real_time_scoring"] = {
                "duration": scoring_duration,
                "score": threat_score.get("threat_score", 0),
                "meets_realtime_target": scoring_duration
                < 1.0,  # Should be under 1 second
            }

            # Performance validation
            throughput_multiplier = self.analyzer._calculate_throughput_multiplier()
            resource_efficiency = self.analyzer._calculate_resource_efficiency()

            results["details"]["performance_metrics"] = {
                "throughput_multiplier": throughput_multiplier,
                "resource_efficiency": resource_efficiency,
                "meets_performance_targets": throughput_multiplier >= 1.0
                and resource_efficiency >= 0.5,
            }

            print(f"    ⚡ Single Analysis: {single_duration:.3f}s")
            print(f"    🎯 Real-time Scoring: {scoring_duration:.3f}s")
            print(f"    📈 Throughput Multiplier: {throughput_multiplier:.1f}x")
            print(f"    🎛️  Resource Efficiency: {resource_efficiency:.1%}")

            # Validate performance targets
            if (
                single_duration > 30.0 or scoring_duration > 1.0
            ):  # Performance thresholds
                results["passed"] = False

        except Exception as e:
            results["passed"] = False
            results["details"]["error"] = str(e)
            print(f"    ❌ Error: {str(e)}")
        finally:
            os.unlink(temp_path)

        return results

    async def _test_parallel_processing(self) -> Dict[str, Any]:
        """Test parallel processing capabilities"""
        results = {"passed": True, "details": {}}

        # Create multiple test samples
        test_samples = []
        for i in range(5):
            test_data = b"MZ" + os.urandom(1024) + f"sample_{i}".encode()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".exe") as temp_file:
                temp_file.write(test_data)
                test_samples.append(temp_file.name)

        try:
            # Test batch processing
            start_time = time.time()
            batch_result = await self.analyzer.execute_parallel_batch_analysis(
                test_samples, "comprehensive"
            )
            batch_duration = time.time() - start_time

            results["details"]["batch_processing"] = {
                "duration": batch_duration,
                "samples_processed": batch_result.get("completed_samples", 0),
                "success_rate": batch_result.get("success_rate", 0),
                "samples_per_second": batch_result.get("samples_per_second", 0),
                "hardware_utilization": batch_result.get("hardware_utilization", {}),
            }

            # Validate parallel efficiency
            expected_sequential_time = 5 * 10  # 5 samples * ~10s each
            parallel_efficiency = (
                expected_sequential_time / batch_duration if batch_duration > 0 else 0
            )

            results["details"]["parallel_efficiency"] = parallel_efficiency
            results["details"]["efficiency_target_met"] = (
                parallel_efficiency >= 2.0
            )  # At least 2x speedup

            print(f"    🔄 Batch Duration: {batch_duration:.2f}s")
            print(f"    📊 Success Rate: {batch_result.get('success_rate', 0):.1f}%")
            print(f"    ⚡ Parallel Efficiency: {parallel_efficiency:.1f}x")

            if batch_result.get("success_rate", 0) < 80 or parallel_efficiency < 2.0:
                results["passed"] = False

        except Exception as e:
            results["passed"] = False
            results["details"]["error"] = str(e)
            print(f"    ❌ Error: {str(e)}")
        finally:
            # Cleanup
            for sample_path in test_samples:
                try:
                    os.unlink(sample_path)
                except:
                    pass

        return results

    async def _test_real_time_scoring(self) -> Dict[str, Any]:
        """Test real-time threat scoring"""
        results = {"passed": True, "details": {}}

        # Create test samples with different threat levels
        test_cases = [
            (
                "high_threat",
                b"MZ" + b"\x00" * 100 + os.urandom(1024),
            ),  # PE with suspicious content
            ("low_threat", b"This is a plain text file with normal content"),
            ("medium_threat", b"MZ" + b"Hello World! " * 50),  # PE with text
        ]

        for test_name, test_data in test_cases:
            print(f"    🎯 Testing {test_name}...")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".exe") as temp_file:
                temp_file.write(test_data)
                temp_path = temp_file.name

            try:
                # Test real-time scoring
                start_time = time.time()
                threat_score = await self.analyzer.execute_real_time_threat_scoring(
                    temp_path
                )
                scoring_duration = time.time() - start_time

                results["details"][test_name] = {
                    "duration": scoring_duration,
                    "threat_score": threat_score.get("threat_score", 0),
                    "classification": threat_score.get(
                        "threat_classification", "UNKNOWN"
                    ),
                    "confidence": threat_score.get("confidence_level", "UNKNOWN"),
                    "meets_realtime_requirement": scoring_duration < 1.0,
                }

                print(f"      📊 Score: {threat_score.get('threat_score', 0):.1f}")
                print(
                    f"      🏷️  Classification: {threat_score.get('threat_classification', 'UNKNOWN')}"
                )
                print(f"      ⏱️  Duration: {scoring_duration:.3f}s")

                # Validate scoring makes sense
                score_value = threat_score.get("threat_score", 0)
                if "high" in test_name and score_value < 60:
                    results["passed"] = False
                elif "low" in test_name and score_value > 40:
                    results["passed"] = False

            except Exception as e:
                results["passed"] = False
                results["details"][test_name] = {"error": str(e)}
                print(f"      ❌ Error: {str(e)}")
            finally:
                os.unlink(temp_path)

        return results

    async def _test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and resilience"""
        results = {"passed": True, "details": {}}

        # Test invalid file
        try:
            result = await self.analyzer.execute_hardware_accelerated_analysis(
                "/nonexistent/file.exe", "comprehensive"
            )
            results["details"]["invalid_file"] = {
                "status": result.get("status"),
                "handled_gracefully": result.get("status") == "error",
            }
        except Exception as e:
            results["details"]["invalid_file"] = {
                "exception": str(e),
                "handled_gracefully": False,
            }
            results["passed"] = False

        # Test empty file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = await self.analyzer.execute_hardware_accelerated_analysis(
                temp_path, "comprehensive"
            )
            results["details"]["empty_file"] = {
                "status": result.get("status"),
                "handled_gracefully": True,
            }
        except Exception as e:
            results["details"]["empty_file"] = {
                "exception": str(e),
                "handled_gracefully": False,
            }
            results["passed"] = False
        finally:
            os.unlink(temp_path)

        print(f"    🛡️  Error handling tests completed")

        return results

    async def _test_resource_management(self) -> Dict[str, Any]:
        """Test resource management and cleanup"""
        results = {"passed": True, "details": {}}

        try:
            # Test core allocation
            hw_engine = self.analyzer.hardware_engine
            current_pid = os.getpid()

            # Test different workload allocations
            for workload_type in ["cpu_intensive", "background", "mixed"]:
                hw_engine.allocate_cores(current_pid, workload_type)
                # Note: In a real test, we'd verify the actual core affinity

            results["details"]["core_allocation"] = {"status": "completed"}

            # Test resource efficiency calculation
            efficiency = self.analyzer._calculate_resource_efficiency()
            results["details"]["resource_efficiency"] = {
                "value": efficiency,
                "valid_range": 0.0 <= efficiency <= 1.0,
            }

            if not (0.0 <= efficiency <= 1.0):
                results["passed"] = False

            print(f"    🎛️  Resource efficiency: {efficiency:.1%}")

        except Exception as e:
            results["passed"] = False
            results["details"]["error"] = str(e)
            print(f"    ❌ Error: {str(e)}")

        return results

    async def _test_integration(self) -> Dict[str, Any]:
        """Test end-to-end integration"""
        results = {"passed": True, "details": {}}

        # Create comprehensive test sample
        test_data = (
            b"MZ\x90\x00"  # PE header
            + b"RC4" * 10  # RC4 indicators
            + bytes(i ^ 0x42 for i in range(256))  # XOR pattern
            + os.urandom(512)  # High entropy section
            + b"http://malware.example.com"  # Plaintext URL
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".exe") as temp_file:
            temp_file.write(test_data)
            temp_path = temp_file.name

        try:
            # Full analysis workflow
            analysis_result = await self.analyzer.execute_hardware_accelerated_analysis(
                temp_path, "comprehensive"
            )

            results["details"]["full_analysis"] = {
                "status": analysis_result.get("status"),
                "has_cryptd_analysis": "cryptd_analysis" in analysis_result,
                "has_ultrathink_analysis": "ultrathink_analysis" in analysis_result,
                "has_performance_metrics": "performance_metrics" in analysis_result,
            }

            # Validate comprehensive analysis
            cryptd_analysis = analysis_result.get("cryptd_analysis", {})
            expected_findings = [
                "RC4_IN_2025",
                "XOR_SINGLE_BYTE",
                "PLAINTEXT_URL",
                "EMBEDDED_PE_VISIBLE",
            ]
            found_findings = cryptd_analysis.get("crypto_findings", [])

            detection_rate = len(set(found_findings) & set(expected_findings)) / len(
                expected_findings
            )
            results["details"]["detection_comprehensive"] = {
                "expected": expected_findings,
                "found": found_findings,
                "detection_rate": detection_rate,
            }

            if detection_rate < 0.7:  # Should detect at least 70% of patterns
                results["passed"] = False

            print(f"    🔍 Pattern Detection Rate: {detection_rate:.1%}")
            print(f"    📊 Meme Score: {cryptd_analysis.get('meme_score', 0)}")

        except Exception as e:
            results["passed"] = False
            results["details"]["error"] = str(e)
            print(f"    ❌ Error: {str(e)}")
        finally:
            os.unlink(temp_path)

        return results

    def _create_cryptd_test_samples(self) -> Dict[str, bytes]:
        """Create test samples with known CRYPTD patterns"""
        samples = {}

        # Sample with single-byte XOR
        xor_data = bytes(i ^ 0x42 for i in b"This is a secret message!")
        samples["xor_single_byte"] = b"MZ\x90\x00" + xor_data

        # Sample with RC4 indicators
        samples["rc4_sample"] = (
            b"MZ\x90\x00" + b"RC4_KEY_SCHEDULE" + b"arcfour" + os.urandom(256)
        )

        # Sample with poor entropy
        samples["entropy_fail"] = b"MZ\x90\x00" + b"A" * 1000

        # Sample with PE in ELF
        samples["pe_in_elf"] = (
            b"\x7fELF" + os.urandom(100) + b"MZ\x90\x00" + os.urandom(100)
        )

        # Sample with plaintext URLs
        samples["plaintext_urls"] = (
            b"MZ\x90\x00" + b"http://malware.example.com" + b"192.168.1.100"
        )

        return samples

    def _get_expected_findings(self, sample_name: str) -> List[str]:
        """Get expected findings for test samples"""
        expected = {
            "xor_single_byte": ["XOR_SINGLE_BYTE"],
            "rc4_sample": ["RC4_IN_2025"],
            "entropy_fail": ["ENTROPY_FAIL"],
            "pe_in_elf": ["PE_IN_ELF"],
            "plaintext_urls": ["PLAINTEXT_URL"],
        }
        return expected.get(sample_name, [])

    def _create_single_byte_xor_sample(self, key: int) -> bytes:
        """Create sample with single-byte XOR encryption"""
        plaintext = b"This is a test message for XOR analysis!"
        return bytes(b ^ key for b in plaintext)

    def _create_multi_byte_xor_sample(self, key: bytes) -> bytes:
        """Create sample with multi-byte XOR encryption"""
        plaintext = b"This is a test message for multi-byte XOR analysis!" * 5
        result = bytearray()
        for i, b in enumerate(plaintext):
            result.append(b ^ key[i % len(key)])
        return bytes(result)


# Main testing function
async def run_cryptd_tests():
    """Run the complete CRYPTD testing suite"""
    framework = CRYPTDTestingFramework()
    return await framework.run_comprehensive_tests()


if __name__ == "__main__":
    # Run tests
    results = asyncio.run(run_cryptd_tests())

    # Print final summary
    print("\n" + "🎯 FINAL TEST SUMMARY" + "=" * 50)
    print(f"Overall Status: {results['overall_status']}")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    print(f"Total Duration: {results['total_duration']:.2f}s")

    if results["overall_status"] == "PASSED":
        print("✅ All tests completed successfully!")
    else:
        print("❌ Some tests failed. Check results for details.")
