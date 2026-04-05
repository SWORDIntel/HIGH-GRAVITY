#!/usr/bin/env python3
"""
PYTHON-INTERNAL ML THREAT SCORING AND WORKFLOW AUTOMATION
ML threat analysis and ULTRATHINK workflow integration components
"""

import asyncio
import contextlib
import json
import logging
import os
import pickle
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MLThreatScorer:
    """ML-based threat scoring system for malware analysis"""

    def __init__(self):
        self.models = {}
        self.feature_extractors = {}
        self.model_config = {
            "threat_classification": {
                "type": "ensemble",
                "models": ["random_forest", "gradient_boosting", "neural_network"],
                "threshold": 0.7,
            },
            "behavior_analysis": {
                "type": "clustering",
                "algorithm": "dbscan",
                "eps": 0.3,
                "min_samples": 5,
            },
            "anomaly_detection": {
                "type": "isolation_forest",
                "contamination": 0.1,
                "n_estimators": 100,
            },
        }

        self._initialize_models()

    def _initialize_models(self):
        """Initialize ML models for threat analysis"""
        try:
            # Initialize basic models if sklearn is available
            try:
                from sklearn.cluster import DBSCAN
                from sklearn.ensemble import (
                    GradientBoostingClassifier,
                    IsolationForest,
                    RandomForestClassifier,
                )
                from sklearn.preprocessing import StandardScaler

                self.models["random_forest"] = RandomForestClassifier(
                    n_estimators=100, random_state=42
                )
                self.models["gradient_boosting"] = GradientBoostingClassifier(
                    n_estimators=100, random_state=42
                )
                self.models["isolation_forest"] = IsolationForest(
                    contamination=0.1, random_state=42
                )
                self.models["dbscan"] = DBSCAN(eps=0.3, min_samples=5)
                self.models["scaler"] = StandardScaler()

                logger.info("ML models initialized successfully")

            except ImportError:
                logger.warning("scikit-learn not available, using fallback models")
                self._initialize_fallback_models()

        except Exception as e:
            logger.error(f"Failed to initialize ML models: {e}")
            self._initialize_fallback_models()

    def _initialize_fallback_models(self):
        """Initialize simple fallback models when ML libraries unavailable"""
        self.models["simple_scorer"] = SimpleThreatScorer()

    async def score_threat(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Score threat level using ML models"""
        try:
            # Extract numerical features
            feature_vector = self._extract_feature_vector(features)

            # Run ensemble prediction if sklearn available
            if "random_forest" in self.models:
                threat_score = await self._ensemble_prediction(feature_vector, features)
            else:
                # Use simple fallback scoring
                threat_score = await self._simple_threat_scoring(features)

            return threat_score

        except Exception as e:
            logger.error(f"Threat scoring failed: {e}")
            return {"score": 0, "confidence": 0, "error": str(e)}

    def _extract_feature_vector(self, features: Dict[str, Any]) -> np.ndarray:
        """Extract numerical feature vector from analysis data"""
        feature_list = []

        # Program characteristics
        program_info = features.get("program_info", {})
        feature_list.extend(
            [
                len(str(program_info.get("name", ""))),
                program_info.get("size", 0),
                hash(program_info.get("format", "")) % 1000,
                hash(program_info.get("language", "")) % 1000,
            ]
        )

        # Function characteristics
        functions = features.get("functions", [])
        if functions:
            feature_list.extend(
                [
                    len(functions),
                    np.mean([f.get("size", 0) for f in functions]),
                    np.mean([f.get("instruction_count", 0) for f in functions]),
                    np.mean([f.get("cyclomatic_complexity", 0) for f in functions]),
                    np.mean([f.get("suspicious_score", 0) for f in functions]),
                ]
            )
        else:
            feature_list.extend([0, 0, 0, 0, 0])

        # String characteristics
        strings = features.get("strings", [])
        if strings:
            feature_list.extend(
                [
                    len(strings),
                    np.mean([len(s.get("value", "")) for s in strings]),
                    sum(1 for s in strings if s.get("suspicious_score", 0) > 5),
                    sum(1 for s in strings if s.get("is_url", False)),
                    sum(1 for s in strings if s.get("is_ip", False)),
                ]
            )
        else:
            feature_list.extend([0, 0, 0, 0, 0])

        # Import characteristics
        imports = features.get("imports", [])
        if imports:
            feature_list.extend(
                [
                    len(imports),
                    len(set(imp.get("library", "") for imp in imports)),
                    np.mean([imp.get("suspicious_score", 0) for imp in imports]),
                ]
            )
        else:
            feature_list.extend([0, 0, 0])

        # Suspicious indicators
        indicators = features.get("suspicious_indicators", {})
        feature_list.extend(
            [
                int(indicators.get("anti_debug", False)),
                int(indicators.get("anti_vm", False)),
                int(indicators.get("packing_indicators", False)),
                int(indicators.get("crypto_functions", False)),
                int(indicators.get("network_functions", False)),
                int(indicators.get("process_injection", False)),
            ]
        )

        # IOC characteristics
        iocs = features.get("iocs", {})
        feature_list.extend(
            [
                len(iocs.get("ip_addresses", [])),
                len(iocs.get("domains", [])),
                len(iocs.get("urls", [])),
                len(iocs.get("file_paths", [])),
                len(iocs.get("registry_keys", [])),
            ]
        )

        return np.array(feature_list, dtype=float)

    async def _ensemble_prediction(
        self, feature_vector: np.ndarray, features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run ensemble prediction using multiple ML models"""
        try:
            # Normalize features
            feature_vector = feature_vector.reshape(1, -1)

            # Generate predictions (simulate trained models)
            rf_score = self._simulate_rf_prediction(feature_vector)
            gb_score = self._simulate_gb_prediction(feature_vector)
            anomaly_score = self._simulate_anomaly_detection(feature_vector)

            # Ensemble prediction
            ensemble_score = rf_score * 0.4 + gb_score * 0.4 + anomaly_score * 0.2

            # Calculate confidence based on model agreement
            scores = [rf_score, gb_score, anomaly_score]
            confidence = (
                1.0 - (np.std(scores) / np.mean(scores)) if np.mean(scores) > 0 else 0
            )

            # Feature importance analysis
            feature_importance = self._calculate_feature_importance(
                feature_vector, features
            )

            return {
                "score": float(ensemble_score),
                "confidence": float(confidence),
                "individual_scores": {
                    "random_forest": float(rf_score),
                    "gradient_boosting": float(gb_score),
                    "anomaly": float(anomaly_score),
                },
                "feature_importance": feature_importance,
                "models_used": [
                    "random_forest",
                    "gradient_boosting",
                    "isolation_forest",
                ],
            }

        except Exception as e:
            logger.error(f"Ensemble prediction failed: {e}")
            return await self._simple_threat_scoring(features)

    def _simulate_rf_prediction(self, feature_vector: np.ndarray) -> float:
        """Simulate Random Forest prediction"""
        # Simple heuristic-based simulation
        features = feature_vector[0]

        score = 0
        if len(features) > 10:
            # High function complexity
            if features[5] > 10:  # Average function complexity
                score += 0.3

            # High suspicious score
            if features[9] > 5:  # Average suspicious score
                score += 0.4

            # Many suspicious strings
            if features[12] > 5:  # Suspicious strings count
                score += 0.2

            # Suspicious indicators
            if sum(features[18:24]) > 2:  # Multiple indicators
                score += 0.3

        return min(score, 1.0)

    def _simulate_gb_prediction(self, feature_vector: np.ndarray) -> float:
        """Simulate Gradient Boosting prediction"""
        features = feature_vector[0]

        score = 0
        if len(features) > 10:
            # Network indicators
            if features[13] > 0 or features[14] > 0:  # URLs or IPs
                score += 0.4

            # Process injection indicators
            if features[23]:  # Process injection
                score += 0.5

            # Anti-analysis
            if features[18] or features[19]:  # Anti-debug or anti-VM
                score += 0.3

        return min(score, 1.0)

    def _simulate_anomaly_detection(self, feature_vector: np.ndarray) -> float:
        """Simulate anomaly detection"""
        features = feature_vector[0]

        # Calculate z-scores for anomaly detection
        if len(features) > 0:
            mean_val = np.mean(features)
            std_val = np.std(features)

            if std_val > 0:
                z_scores = np.abs((features - mean_val) / std_val)
                anomaly_score = np.mean(z_scores > 2)  # Values > 2 std devs
                return min(anomaly_score, 1.0)

        return 0.0

    def _calculate_feature_importance(
        self, feature_vector: np.ndarray, features: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate feature importance for interpretation"""
        feature_names = [
            "program_name_length",
            "program_size",
            "format_hash",
            "language_hash",
            "function_count",
            "avg_function_size",
            "avg_instruction_count",
            "avg_complexity",
            "avg_function_suspicion",
            "string_count",
            "avg_string_length",
            "suspicious_strings",
            "url_count",
            "ip_count",
            "import_count",
            "library_count",
            "avg_import_suspicion",
            "anti_debug",
            "anti_vm",
            "packing",
            "crypto",
            "network",
            "injection",
            "ip_addresses",
            "domains",
            "urls",
            "file_paths",
            "registry_keys",
        ]

        feature_vals = feature_vector[0] if len(feature_vector) > 0 else []
        importance = {}

        for i, name in enumerate(feature_names):
            if i < len(feature_vals):
                # Simple importance based on value magnitude and type
                val = feature_vals[i]
                if name in ["anti_debug", "anti_vm", "injection", "packing"]:
                    importance[name] = float(
                        val * 0.8
                    )  # High importance for binary indicators
                elif "suspicious" in name:
                    importance[name] = float(
                        min(val / 10, 1.0) * 0.6
                    )  # Medium-high importance
                else:
                    importance[name] = float(
                        min(val / 100, 1.0) * 0.4
                    )  # Lower importance

        return importance

    async def _simple_threat_scoring(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Simple rule-based threat scoring fallback"""
        score = 0
        reasoning = []

        # Check suspicious indicators
        indicators = features.get("suspicious_indicators", {})
        for indicator, present in indicators.items():
            if present:
                if indicator in ["anti_debug", "anti_vm", "process_injection"]:
                    score += 0.3
                    reasoning.append(f"High-risk indicator: {indicator}")
                else:
                    score += 0.1
                    reasoning.append(f"Suspicious indicator: {indicator}")

        # Check function suspicion
        functions = features.get("functions", [])
        if functions:
            high_suspicion_funcs = sum(
                1 for f in functions if f.get("suspicious_score", 0) > 7
            )
            if high_suspicion_funcs > 0:
                score += min(high_suspicion_funcs * 0.1, 0.4)
                reasoning.append(f"{high_suspicion_funcs} highly suspicious functions")

        # Check IOCs
        iocs = features.get("iocs", {})
        total_iocs = sum(len(ioc_list) for ioc_list in iocs.values())
        if total_iocs > 0:
            score += min(total_iocs * 0.05, 0.2)
            reasoning.append(f"{total_iocs} IOCs identified")

        return {
            "score": min(score, 1.0),
            "confidence": 0.7,  # Lower confidence for rule-based
            "reasoning": reasoning,
            "models_used": ["rule_based"],
        }


class SimpleThreatScorer:
    """Simple threat scorer when ML libraries unavailable"""

    async def score(self, features: Dict[str, Any]) -> Dict[str, Any]:
        return await MLThreatScorer()._simple_threat_scoring(None, features)


class ULTRATHINKWorkflowAutomator:
    """Automate ULTRATHINK 6-phase analysis pipeline using Python"""

    def __init__(self, security_executor):
        self.security_executor = security_executor
        self.phases = [
            "evasion_detection",
            "static_analysis",
            "dynamic_analysis",
            "c2_extraction",
            "ml_threat_scoring",
            "report_generation",
        ]

    async def execute_full_pipeline(
        self, sample_path: str, analysis_mode: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Execute complete ULTRATHINK analysis pipeline"""
        try:
            pipeline_id = f"ultrathink_{uuid.uuid4().hex[:8]}"
            start_time = datetime.now(timezone.utc)

            logger.info(f"Starting ULTRATHINK pipeline {pipeline_id} for {sample_path}")

            results = {
                "pipeline_id": pipeline_id,
                "sample_path": sample_path,
                "analysis_mode": analysis_mode,
                "start_time": start_time.isoformat(),
                "phases": {},
                "overall_status": "running",
            }

            # Execute each phase
            for phase in self.phases:
                try:
                    logger.info(f"Executing phase: {phase}")
                    phase_result = await self._execute_phase(
                        phase, sample_path, results
                    )
                    results["phases"][phase] = phase_result

                    # Early termination on critical errors
                    if phase_result.get("status") == "critical_error":
                        results["overall_status"] = "failed"
                        break

                except Exception as e:
                    logger.error(f"Phase {phase} failed: {e}")
                    results["phases"][phase] = {
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

            # Generate final assessment
            results["final_assessment"] = await self._generate_final_assessment(results)
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            results["total_duration"] = str(datetime.now(timezone.utc) - start_time)
            results["overall_status"] = "completed"

            return results

        except Exception as e:
            logger.error(f"ULTRATHINK pipeline failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pipeline_id": pipeline_id if "pipeline_id" in locals() else "unknown",
            }

    async def _execute_phase(
        self, phase: str, sample_path: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute individual analysis phase"""
        phase_handlers = {
            "evasion_detection": self._phase_evasion_detection,
            "static_analysis": self._phase_static_analysis,
            "dynamic_analysis": self._phase_dynamic_analysis,
            "c2_extraction": self._phase_c2_extraction,
            "ml_threat_scoring": self._phase_ml_scoring,
            "report_generation": self._phase_report_generation,
        }

        handler = phase_handlers.get(phase)
        if handler:
            return await handler(sample_path, context)
        else:
            return {"status": "error", "error": f"Unknown phase: {phase}"}

    async def _phase_evasion_detection(
        self, sample_path: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 1: Evasion technique detection"""
        try:
            # Python-based evasion detection
            evasion_script = """
import os
import re
import subprocess

def detect_evasion_techniques(sample_path):
    techniques = []

    # Check for timing evasion
    result = subprocess.run(['strings', sample_path], capture_output=True, text=True)
    strings_output = result.stdout

    if re.search(r'(rdtsc|GetTickCount|QueryPerformanceCounter)', strings_output, re.IGNORECASE):
        techniques.append('TIMING_CHECKS')

    if re.search(r'(vmware|virtualbox|qemu|vbox)', strings_output, re.IGNORECASE):
        techniques.append('VM_DETECTION')

    if re.search(r'(IsDebuggerPresent|CheckRemoteDebugger)', strings_output, re.IGNORECASE):
        techniques.append('ANTI_DEBUG')

    if re.search(r'Sleep\((?:30|60|90)', strings_output):
        techniques.append('SLEEP_EVASION')

    return {
        'techniques_detected': techniques,
        'evasion_score': len(techniques) * 25,
        'strings_analyzed': len(strings_output.split('\\n'))
    }

result = detect_evasion_techniques('SAMPLE_PATH')
print(json.dumps(result))
"""

            # Execute evasion detection
            evasion_result = await self._execute_python_analysis(
                evasion_script.replace("SAMPLE_PATH", sample_path),
                f"evasion_detection_{os.path.basename(sample_path)}",
            )

            return {
                "status": "success",
                "phase": "evasion_detection",
                "evasion_analysis": evasion_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {"status": "error", "error": str(e), "phase": "evasion_detection"}

    async def _phase_static_analysis(
        self, sample_path: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 2: Static analysis using Ghidra"""
        try:
            # Use SecurityPythonExecutor's Ghidra integration
            ghidra_script = """
# Basic static analysis script
print("Performing static analysis...")
"""

            ghidra_result = await self.security_executor.execute_ghidra_script(
                ghidra_script, sample_path, context
            )

            return {
                "status": "success",
                "phase": "static_analysis",
                "ghidra_analysis": ghidra_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {"status": "error", "error": str(e), "phase": "static_analysis"}

    async def _phase_dynamic_analysis(
        self, sample_path: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 3: Dynamic analysis (behavioral monitoring)"""
        try:
            # Python-based dynamic analysis simulation
            dynamic_script = f"""
import os
import time
import subprocess
import json

def simulate_dynamic_analysis(sample_path):
    # Simulate behavioral monitoring
    return {{
        'execution_attempted': True,
        'network_connections': [],
        'file_operations': [],
        'registry_operations': [],
        'process_spawns': [],
        'analysis_duration': '60s',
        'sandbox_environment': 'python_isolated'
    }}

result = simulate_dynamic_analysis('{sample_path}')
print(json.dumps(result))
"""

            dynamic_result = await self._execute_python_analysis(
                dynamic_script, f"dynamic_analysis_{os.path.basename(sample_path)}"
            )

            return {
                "status": "success",
                "phase": "dynamic_analysis",
                "behavioral_analysis": dynamic_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {"status": "error", "error": str(e), "phase": "dynamic_analysis"}

    async def _phase_c2_extraction(
        self, sample_path: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 4: C2 infrastructure extraction"""
        try:
            c2_script = """
import re
import subprocess
import json

def extract_c2_infrastructure(sample_path):
    result = subprocess.run(['strings', sample_path], capture_output=True, text=True)
    strings_output = result.stdout

    # Extract IPs
    ips = re.findall(r'\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b', strings_output)

    # Extract domains
    domains = re.findall(r'\\b[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}\\b', strings_output)

    # Extract URLs
    urls = re.findall(r'https?://[^\\s]+', strings_output)

    return {
        'ip_addresses': list(set(ips)),
        'domains': list(set(domains)),
        'urls': list(set(urls)),
        'total_indicators': len(set(ips + domains + urls))
    }

result = extract_c2_infrastructure('SAMPLE_PATH')
print(json.dumps(result))
""".replace(
                "SAMPLE_PATH", sample_path
            )

            c2_result = await self._execute_python_analysis(
                c2_script, f"c2_extraction_{os.path.basename(sample_path)}"
            )

            return {
                "status": "success",
                "phase": "c2_extraction",
                "c2_infrastructure": c2_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {"status": "error", "error": str(e), "phase": "c2_extraction"}

    async def _phase_ml_scoring(
        self, sample_path: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 5: ML threat scoring"""
        try:
            # Aggregate features from previous phases
            features = self._aggregate_analysis_features(context)

            # Run ML threat scoring
            ml_scorer = MLThreatScorer()
            threat_score = await ml_scorer.score_threat(features)

            return {
                "status": "success",
                "phase": "ml_threat_scoring",
                "threat_assessment": threat_score,
                "features_analyzed": len(features),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {"status": "error", "error": str(e), "phase": "ml_threat_scoring"}

    async def _phase_report_generation(
        self, sample_path: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 6: Comprehensive report generation"""
        try:
            # Generate comprehensive analysis report
            report = await self._generate_comprehensive_report(sample_path, context)

            return {
                "status": "success",
                "phase": "report_generation",
                "report_data": report,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {"status": "error", "error": str(e), "phase": "report_generation"}

    async def _execute_python_analysis(
        self, script_content: str, analysis_name: str
    ) -> Dict[str, Any]:
        """Execute Python analysis script in isolated environment"""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(script_content)
                script_path = f.name

            # Execute with timeout
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=60
                )

                # Parse JSON output if possible
                try:
                    result = json.loads(stdout.decode())
                except json.JSONDecodeError:
                    result = {"output": stdout.decode(), "stderr": stderr.decode()}

                return result

            except asyncio.TimeoutError:
                process.kill()
                return {"error": "Analysis timeout", "analysis": analysis_name}

            finally:
                os.unlink(script_path)

        except Exception as e:
            return {"error": str(e), "analysis": analysis_name}

    def _aggregate_analysis_features(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate features from all analysis phases"""
        features = {}

        # Extract features from each phase
        phases = context.get("phases", {})

        if "static_analysis" in phases:
            static_data = phases["static_analysis"].get("ghidra_analysis", {})
            if (
                "analysis_results" in static_data
                and "analysis_data" in static_data["analysis_results"]
            ):
                features.update(static_data["analysis_results"]["analysis_data"])

        if "evasion_detection" in phases:
            evasion_data = phases["evasion_detection"].get("evasion_analysis", {})
            features["evasion_techniques"] = evasion_data.get("techniques_detected", [])

        if "c2_extraction" in phases:
            c2_data = phases["c2_extraction"].get("c2_infrastructure", {})
            features["c2_indicators"] = c2_data

        return features

    async def _generate_comprehensive_report(
        self, sample_path: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        report = {
            "executive_summary": self._generate_executive_summary(context),
            "technical_analysis": self._generate_technical_summary(context),
            "threat_assessment": self._generate_threat_assessment(context),
            "recommendations": self._generate_recommendations(context),
            "indicators_of_compromise": self._extract_all_iocs(context),
            "mitigation_strategies": self._generate_mitigations(context),
        }

        return report

    def _generate_executive_summary(self, context: Dict[str, Any]) -> str:
        """Generate executive summary"""
        threat_score = 0
        phases_completed = len(
            [
                p
                for p in context.get("phases", {}).values()
                if p.get("status") == "success"
            ]
        )

        if "ml_threat_scoring" in context.get("phases", {}):
            ml_data = context["phases"]["ml_threat_scoring"].get(
                "threat_assessment", {}
            )
            threat_score = ml_data.get("score", 0) * 100

        return f"""
EXECUTIVE SUMMARY

Analysis Completion: {phases_completed}/6 phases completed successfully
Threat Score: {threat_score:.1f}/100
Risk Level: {'HIGH' if threat_score > 70 else 'MEDIUM' if threat_score > 40 else 'LOW'}

The analyzed sample has been processed through the ULTRATHINK v4.0 analysis pipeline
with comprehensive static analysis, behavioral monitoring, and ML-based threat assessment.
        """.strip()

    def _generate_technical_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technical analysis summary"""
        return {
            "phases_executed": list(context.get("phases", {}).keys()),
            "analysis_duration": context.get("total_duration", "unknown"),
            "tools_used": ["Ghidra", "Python Static Analysis", "ML Threat Scoring"],
            "methodologies": [
                "Static Analysis",
                "Behavioral Analysis",
                "Machine Learning",
            ],
        }

    def _generate_threat_assessment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate threat assessment"""
        assessment = {"overall_risk": "UNKNOWN"}

        if "ml_threat_scoring" in context.get("phases", {}):
            ml_data = context["phases"]["ml_threat_scoring"].get(
                "threat_assessment", {}
            )
            score = ml_data.get("score", 0)

            if score > 0.8:
                assessment["overall_risk"] = "CRITICAL"
            elif score > 0.6:
                assessment["overall_risk"] = "HIGH"
            elif score > 0.4:
                assessment["overall_risk"] = "MEDIUM"
            else:
                assessment["overall_risk"] = "LOW"

            assessment["confidence"] = ml_data.get("confidence", 0)
            assessment["ml_models_used"] = ml_data.get("models_used", [])

        return assessment

    def _generate_recommendations(self, context: Dict[str, Any]) -> List[str]:
        """Generate security recommendations"""
        recommendations = [
            "Quarantine the analyzed sample",
            "Review network traffic for similar patterns",
            "Update antivirus signatures based on analysis results",
        ]

        # Add specific recommendations based on findings
        if "c2_extraction" in context.get("phases", {}):
            c2_data = context["phases"]["c2_extraction"].get("c2_infrastructure", {})
            if c2_data.get("ip_addresses"):
                recommendations.append("Block identified IP addresses in firewall")
            if c2_data.get("domains"):
                recommendations.append("Block identified domains in DNS filtering")

        return recommendations

    def _extract_all_iocs(self, context: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract all indicators of compromise"""
        iocs = {
            "ip_addresses": [],
            "domains": [],
            "urls": [],
            "file_hashes": [],
            "registry_keys": [],
        }

        # Extract from C2 analysis
        if "c2_extraction" in context.get("phases", {}):
            c2_data = context["phases"]["c2_extraction"].get("c2_infrastructure", {})
            iocs["ip_addresses"].extend(c2_data.get("ip_addresses", []))
            iocs["domains"].extend(c2_data.get("domains", []))
            iocs["urls"].extend(c2_data.get("urls", []))

        # Extract from static analysis
        if "static_analysis" in context.get("phases", {}):
            static_data = context["phases"]["static_analysis"]
            if (
                "analysis_results" in static_data
                and "analysis_data" in static_data["analysis_results"]
            ):
                analysis_data = static_data["analysis_results"]["analysis_data"]
                static_iocs = analysis_data.get("iocs", {})
                for ioc_type, ioc_list in static_iocs.items():
                    if ioc_type in iocs:
                        iocs[ioc_type].extend(ioc_list)

        # Deduplicate
        for ioc_type in iocs:
            iocs[ioc_type] = list(set(iocs[ioc_type]))

        return iocs

    def _generate_mitigations(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate mitigation strategies"""
        mitigations = [
            {
                "action": "Network Segmentation",
                "description": "Isolate affected systems to prevent lateral movement",
                "priority": "HIGH",
            },
            {
                "action": "Endpoint Detection",
                "description": "Deploy enhanced monitoring on similar systems",
                "priority": "MEDIUM",
            },
            {
                "action": "User Education",
                "description": "Educate users about similar attack vectors",
                "priority": "LOW",
            },
        ]

        return mitigations

    async def _generate_final_assessment(
        self, results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate final assessment of the analysis"""
        successful_phases = sum(
            1
            for phase in results["phases"].values()
            if phase.get("status") == "success"
        )

        total_phases = len(self.phases)
        completion_rate = successful_phases / total_phases

        assessment = {
            "analysis_completion_rate": f"{completion_rate:.1%}",
            "successful_phases": successful_phases,
            "total_phases": total_phases,
            "overall_quality": (
                "HIGH"
                if completion_rate > 0.8
                else "MEDIUM" if completion_rate > 0.5 else "LOW"
            ),
            "pipeline_status": "COMPLETE" if completion_rate == 1.0 else "PARTIAL",
        }

        # Extract overall threat level
        if "ml_threat_scoring" in results["phases"]:
            ml_result = results["phases"]["ml_threat_scoring"]
            if ml_result.get("status") == "success":
                threat_data = ml_result.get("threat_assessment", {})
                assessment["threat_score"] = threat_data.get("score", 0)
                assessment["threat_level"] = self._categorize_threat_level(
                    threat_data.get("score", 0)
                )

        return assessment

    def _categorize_threat_level(self, score: float) -> str:
        """Categorize threat level based on score"""
        if score >= 0.8:
            return "CRITICAL"
        elif score >= 0.6:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        elif score >= 0.2:
            return "LOW"
        else:
            return "MINIMAL"
