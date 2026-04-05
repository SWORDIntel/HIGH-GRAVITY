#!/usr/bin/env python3
"""
CRYPTD-Specific Analysis Automation Workflows
Enhanced Ghidra Integration with NPU/GPU/GNA Hardware Acceleration

This module provides comprehensive automation workflows for CRYPTD-specific
malware analysis with hardware acceleration and advanced pattern detection.
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from DISASSEMBLER_impl import DISASSEMBLERBinaryAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CRYPTDAutomationWorkflows:
    """Comprehensive automation workflows for CRYPTD analysis"""

    def __init__(self):
        self.analyzer = DISASSEMBLERBinaryAnalyzer(
            file_generation_enabled=False, user_consent_given=False
        )
        self.results_dir = Path.home() / ".claude" / "cryptd-analysis-results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def execute_comprehensive_cryptd_campaign(
        self, sample_directory: str
    ) -> Dict[str, Any]:
        """Execute comprehensive CRYPTD analysis campaign on sample directory"""
        campaign_start = time.time()
        campaign_id = f"cryptd_campaign_{int(campaign_start)}"

        logger.info(f"Starting CRYPTD analysis campaign: {campaign_id}")

        # Discover sample files
        sample_files = self._discover_samples(sample_directory)
        if not sample_files:
            return {
                "status": "error",
                "message": "No sample files found",
                "directory": sample_directory,
            }

        logger.info(f"Found {len(sample_files)} samples for analysis")

        # Execute parallel hardware-accelerated analysis
        batch_results = await self.analyzer.execute_parallel_batch_analysis(
            sample_files, "cryptd_focused"
        )

        # Generate comprehensive campaign report
        campaign_report = await self._generate_campaign_report(
            campaign_id, batch_results, sample_directory
        )

        # Save results
        report_path = self.results_dir / f"{campaign_id}_report.json"
        with open(report_path, "w") as f:
            json.dump(campaign_report, f, indent=2)

        campaign_duration = time.time() - campaign_start
        logger.info(f"Campaign completed in {campaign_duration:.2f}s")

        return {
            "status": "success",
            "campaign_id": campaign_id,
            "duration": campaign_duration,
            "samples_analyzed": len(sample_files),
            "report_path": str(report_path),
            "summary": campaign_report["executive_summary"],
        }

    async def execute_real_time_monitoring(
        self, watch_directory: str, duration: int = 3600
    ) -> Dict[str, Any]:
        """Execute real-time CRYPTD analysis monitoring"""
        monitor_start = time.time()
        monitor_id = f"cryptd_monitor_{int(monitor_start)}"

        logger.info(f"Starting real-time monitoring: {monitor_id} for {duration}s")

        processed_files = set()
        analysis_results = []

        # Monitor directory for new samples
        end_time = monitor_start + duration
        while time.time() < end_time:
            try:
                # Check for new files
                current_files = set(self._discover_samples(watch_directory))
                new_files = current_files - processed_files

                if new_files:
                    logger.info(f"Found {len(new_files)} new samples")

                    # Process new files with real-time threat scoring
                    for sample_path in new_files:
                        try:
                            threat_score = (
                                await self.analyzer.execute_real_time_threat_scoring(
                                    sample_path
                                )
                            )
                            analysis_results.append(
                                {
                                    "sample_path": sample_path,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "threat_score": threat_score,
                                }
                            )

                            # Immediate action for high-threat samples
                            if threat_score.get("threat_classification") in [
                                "CRITICAL",
                                "HIGH",
                            ]:
                                await self._handle_critical_threat(
                                    sample_path, threat_score
                                )

                        except Exception as e:
                            logger.error(f"Failed to analyze {sample_path}: {e}")

                    processed_files.update(new_files)

                # Sleep before next check
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(30)

        monitor_duration = time.time() - monitor_start

        # Generate monitoring report
        monitoring_report = {
            "monitor_id": monitor_id,
            "duration": monitor_duration,
            "samples_processed": len(processed_files),
            "critical_threats": len(
                [
                    r
                    for r in analysis_results
                    if r["threat_score"].get("threat_classification") == "CRITICAL"
                ]
            ),
            "high_threats": len(
                [
                    r
                    for r in analysis_results
                    if r["threat_score"].get("threat_classification") == "HIGH"
                ]
            ),
            "analysis_results": analysis_results,
        }

        # Save monitoring report
        report_path = self.results_dir / f"{monitor_id}_monitoring.json"
        with open(report_path, "w") as f:
            json.dump(monitoring_report, f, indent=2)

        return {
            "status": "success",
            "monitor_id": monitor_id,
            "duration": monitor_duration,
            "samples_processed": len(processed_files),
            "report_path": str(report_path),
        }

    async def execute_performance_benchmarking(
        self, test_samples: List[str]
    ) -> Dict[str, Any]:
        """Execute performance benchmarking of hardware acceleration"""
        benchmark_start = time.time()
        benchmark_id = f"cryptd_benchmark_{int(benchmark_start)}"

        logger.info(f"Starting performance benchmarking: {benchmark_id}")

        # Test different hardware configurations
        performance_results = {}

        # Benchmark CPU-only performance
        cpu_start = time.time()
        original_mode = self.analyzer.performance_mode
        self.analyzer.performance_mode = "cpu_only"

        cpu_results = []
        for sample_path in test_samples[:5]:  # Test with 5 samples
            try:
                result = await self.analyzer.execute_hardware_accelerated_analysis(
                    sample_path, "comprehensive"
                )
                cpu_results.append(result["analysis_duration"])
            except Exception as e:
                logger.error(f"CPU benchmark error: {e}")

        cpu_duration = time.time() - cpu_start
        performance_results["cpu_only"] = {
            "total_duration": cpu_duration,
            "average_per_sample": cpu_duration / len(cpu_results) if cpu_results else 0,
            "samples_per_second": (
                len(cpu_results) / cpu_duration if cpu_duration > 0 else 0
            ),
        }

        # Benchmark with hardware acceleration
        self.analyzer.performance_mode = "auto"
        hw_start = time.time()

        hw_results = []
        for sample_path in test_samples[:5]:
            try:
                result = await self.analyzer.execute_hardware_accelerated_analysis(
                    sample_path, "comprehensive"
                )
                hw_results.append(result["analysis_duration"])
            except Exception as e:
                logger.error(f"Hardware benchmark error: {e}")

        hw_duration = time.time() - hw_start
        performance_results["hardware_accelerated"] = {
            "total_duration": hw_duration,
            "average_per_sample": hw_duration / len(hw_results) if hw_results else 0,
            "samples_per_second": (
                len(hw_results) / hw_duration if hw_duration > 0 else 0
            ),
        }

        # Calculate performance improvements
        speedup = (cpu_duration / hw_duration) if hw_duration > 0 else 1.0
        efficiency_gain = (
            ((cpu_duration - hw_duration) / cpu_duration * 100)
            if cpu_duration > 0
            else 0
        )

        self.analyzer.performance_mode = original_mode

        benchmark_report = {
            "benchmark_id": benchmark_id,
            "hardware_capabilities": {
                "npu_available": self.analyzer.hardware_engine.npu_available,
                "gpu_available": self.analyzer.hardware_engine.gpu_available,
                "gna_available": self.analyzer.hardware_engine.gna_available,
                "cpu_cores": self.analyzer.hardware_engine.cpu_count,
            },
            "performance_results": performance_results,
            "improvements": {
                "speedup_factor": speedup,
                "efficiency_gain_percent": efficiency_gain,
                "throughput_multiplier": self.analyzer._calculate_throughput_multiplier(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Save benchmark report
        report_path = self.results_dir / f"{benchmark_id}_benchmark.json"
        with open(report_path, "w") as f:
            json.dump(benchmark_report, f, indent=2)

        logger.info(f"Benchmarking completed. Speedup: {speedup:.2f}x")

        return {
            "status": "success",
            "benchmark_id": benchmark_id,
            "speedup_factor": speedup,
            "efficiency_gain": efficiency_gain,
            "report_path": str(report_path),
        }

    async def execute_cryptd_hall_of_shame_analysis(
        self, sample_paths: List[str]
    ) -> Dict[str, Any]:
        """Execute analysis specifically looking for Hall of Shame candidates"""
        shame_start = time.time()
        shame_id = f"cryptd_shame_{int(shame_start)}"

        logger.info(f"Starting CRYPTD Hall of Shame analysis: {shame_id}")

        hall_of_shame_candidates = []
        total_meme_score = 0

        for sample_path in sample_paths:
            try:
                # Execute comprehensive CRYPTD analysis
                result = await self.analyzer.execute_hardware_accelerated_analysis(
                    sample_path, "cryptd_focused"
                )

                cryptd_analysis = result.get("cryptd_analysis", {})
                meme_score = cryptd_analysis.get("meme_score", 0)
                total_meme_score += meme_score

                # Check for Hall of Shame qualification
                if cryptd_analysis.get("hall_of_shame_qualification", False):
                    hall_of_shame_candidates.append(
                        {
                            "sample_path": sample_path,
                            "meme_score": meme_score,
                            "threat_actor_competence": cryptd_analysis.get(
                                "threat_actor_competence"
                            ),
                            "roast_level": cryptd_analysis.get("roast_level"),
                            "crypto_findings": cryptd_analysis.get(
                                "crypto_findings", []
                            ),
                            "analysis_details": cryptd_analysis,
                        }
                    )

            except Exception as e:
                logger.error(f"Hall of Shame analysis error for {sample_path}: {e}")

        # Sort candidates by meme score (highest first)
        hall_of_shame_candidates.sort(key=lambda x: x["meme_score"], reverse=True)

        shame_report = {
            "shame_id": shame_id,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_samples_analyzed": len(sample_paths),
            "hall_of_shame_candidates": len(hall_of_shame_candidates),
            "average_meme_score": (
                total_meme_score / len(sample_paths) if sample_paths else 0
            ),
            "top_candidates": hall_of_shame_candidates[:10],  # Top 10
            "competence_distribution": self._analyze_competence_distribution(
                hall_of_shame_candidates
            ),
            "roast_level_distribution": self._analyze_roast_distribution(
                hall_of_shame_candidates
            ),
        }

        # Save Hall of Shame report
        report_path = self.results_dir / f"{shame_id}_hall_of_shame.json"
        with open(report_path, "w") as f:
            json.dump(shame_report, f, indent=2)

        logger.info(
            f"Hall of Shame analysis completed. Found {len(hall_of_shame_candidates)} candidates"
        )

        return {
            "status": "success",
            "shame_id": shame_id,
            "candidates_found": len(hall_of_shame_candidates),
            "top_meme_score": (
                hall_of_shame_candidates[0]["meme_score"]
                if hall_of_shame_candidates
                else 0
            ),
            "report_path": str(report_path),
        }

    def _discover_samples(self, directory: str) -> List[str]:
        """Discover potential malware samples in directory"""
        sample_extensions = [
            ".exe",
            ".dll",
            ".bin",
            ".elf",
            ".so",
            ".dylib",
            ".scr",
            ".bat",
            ".ps1",
        ]
        sample_files = []

        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if any(file.lower().endswith(ext) for ext in sample_extensions):
                        sample_files.append(file_path)
                    elif (
                        os.path.getsize(file_path) > 1024
                    ):  # Files > 1KB without extension
                        sample_files.append(file_path)
        except Exception as e:
            logger.error(f"Error discovering samples: {e}")

        return sample_files

    async def _generate_campaign_report(
        self, campaign_id: str, batch_results: Dict[str, Any], sample_directory: str
    ) -> Dict[str, Any]:
        """Generate comprehensive campaign analysis report"""
        individual_results = batch_results.get("individual_results", {})

        # Aggregate statistics
        total_meme_score = 0
        threat_classifications = {}
        crypto_findings_summary = {}
        competence_levels = {}

        for sample_path, result in individual_results.items():
            if result.get("status") != "error":
                cryptd_analysis = result.get("cryptd_analysis", {})
                meme_score = cryptd_analysis.get("meme_score", 0)
                total_meme_score += meme_score

                # Aggregate threat classifications
                threat_class = cryptd_analysis.get("threat_actor_competence", "UNKNOWN")
                competence_levels[threat_class] = (
                    competence_levels.get(threat_class, 0) + 1
                )

                # Aggregate crypto findings
                for finding in cryptd_analysis.get("crypto_findings", []):
                    crypto_findings_summary[finding] = (
                        crypto_findings_summary.get(finding, 0) + 1
                    )

        # Executive summary
        total_samples = len(individual_results)
        average_meme_score = (
            total_meme_score / total_samples if total_samples > 0 else 0
        )

        hall_of_shame_count = len(
            [
                r
                for r in individual_results.values()
                if r.get("cryptd_analysis", {}).get(
                    "hall_of_shame_qualification", False
                )
            ]
        )

        executive_summary = {
            "campaign_overview": f"CRYPTD analysis campaign on {total_samples} samples",
            "average_meme_score": average_meme_score,
            "hall_of_shame_candidates": hall_of_shame_count,
            "most_common_failure": (
                max(crypto_findings_summary.items(), key=lambda x: x[1])
                if crypto_findings_summary
                else ("None", 0)
            ),
            "competence_assessment": self._assess_overall_competence(competence_levels),
            "hardware_utilization": batch_results.get("hardware_utilization", {}),
            "processing_efficiency": batch_results.get("success_rate", 0),
        }

        return {
            "campaign_id": campaign_id,
            "sample_directory": sample_directory,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "executive_summary": executive_summary,
            "batch_results": batch_results,
            "aggregated_statistics": {
                "total_meme_score": total_meme_score,
                "average_meme_score": average_meme_score,
                "competence_distribution": competence_levels,
                "crypto_findings_summary": crypto_findings_summary,
            },
        }

    async def _handle_critical_threat(
        self, sample_path: str, threat_score: Dict[str, Any]
    ):
        """Handle critical threat detection with immediate actions"""
        logger.warning(f"CRITICAL THREAT DETECTED: {sample_path}")
        logger.warning(f"Threat Score: {threat_score.get('threat_score', 'Unknown')}")
        logger.warning(
            f"Classification: {threat_score.get('threat_classification', 'Unknown')}"
        )

        # In a real environment, this would trigger:
        # - Immediate quarantine
        # - Alert security team
        # - Initiate incident response
        # - Update threat intelligence feeds

        alert = {
            "alert_type": "CRITICAL_THREAT_DETECTED",
            "sample_path": sample_path,
            "threat_score": threat_score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recommended_actions": [
                "IMMEDIATE_QUARANTINE",
                "SECURITY_TEAM_ALERT",
                "INCIDENT_RESPONSE_ACTIVATION",
                "THREAT_INTEL_UPDATE",
            ],
        }

        # Save alert
        alert_path = self.results_dir / f"critical_alert_{int(time.time())}.json"
        with open(alert_path, "w") as f:
            json.dump(alert, f, indent=2)

    def _analyze_competence_distribution(
        self, candidates: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze threat actor competence distribution"""
        distribution = {}
        for candidate in candidates:
            competence = candidate.get("threat_actor_competence", "UNKNOWN")
            distribution[competence] = distribution.get(competence, 0) + 1
        return distribution

    def _analyze_roast_distribution(
        self, candidates: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze roast level distribution"""
        distribution = {}
        for candidate in candidates:
            roast_level = candidate.get("roast_level", "UNKNOWN")
            distribution[roast_level] = distribution.get(roast_level, 0) + 1
        return distribution

    def _assess_overall_competence(self, competence_levels: Dict[str, int]) -> str:
        """Assess overall threat actor competence"""
        if not competence_levels:
            return "NO_DATA"

        total = sum(competence_levels.values())
        script_kiddies = competence_levels.get(
            "SCRIPT_KIDDIE_LEGENDARY", 0
        ) + competence_levels.get("AMATEUR_HOUR_CHAMPION", 0)

        if script_kiddies / total > 0.7:
            return "PREDOMINANTLY_AMATEUR"
        elif script_kiddies / total > 0.4:
            return "MIXED_SKILL_LEVELS"
        else:
            return "CONCERNING_COMPETENCE"


# Demonstration and testing functions
async def demo_cryptd_workflows():
    """Demonstrate CRYPTD analysis workflows"""
    print("=== CRYPTD Analysis Automation Workflows Demo ===")

    workflows = CRYPTDAutomationWorkflows()

    # Create test samples directory
    test_dir = tempfile.mkdtemp(prefix="cryptd_test_")
    print(f"Test directory: {test_dir}")

    # Create mock sample files for demonstration
    test_samples = []
    for i in range(5):
        sample_path = Path(test_dir) / f"test_sample_{i}.exe"
        with open(sample_path, "wb") as f:
            # Create sample data with some patterns
            f.write(b"MZ\x90\x00")  # PE header
            f.write(b"This is a test sample " * 50)
            f.write(b"\x42" * 100)  # Some XOR pattern
        test_samples.append(str(sample_path))

    try:
        # Demo 1: Performance benchmarking
        print("\n1. Running performance benchmarking...")
        benchmark_result = await workflows.execute_performance_benchmarking(
            test_samples
        )
        print(f"Speedup achieved: {benchmark_result.get('speedup_factor', 'N/A')}x")

        # Demo 2: Hall of Shame analysis
        print("\n2. Running Hall of Shame analysis...")
        shame_result = await workflows.execute_cryptd_hall_of_shame_analysis(
            test_samples
        )
        print(
            f"Hall of Shame candidates found: {shame_result.get('candidates_found', 0)}"
        )

        # Demo 3: Comprehensive campaign
        print("\n3. Running comprehensive campaign...")
        campaign_result = await workflows.execute_comprehensive_cryptd_campaign(
            test_dir
        )
        print(
            f"Campaign completed: {campaign_result.get('samples_analyzed', 0)} samples analyzed"
        )

        print(f"\nResults saved to: {workflows.results_dir}")

    except Exception as e:
        print(f"Demo error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Cleanup test files
        import shutil

        shutil.rmtree(test_dir)


if __name__ == "__main__":
    # Run demonstration
    asyncio.run(demo_cryptd_workflows())
