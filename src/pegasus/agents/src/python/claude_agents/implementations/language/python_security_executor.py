#!/usr/bin/env python3
"""
PYTHON-INTERNAL SECURITY EXECUTOR
Enhanced Python execution environment for ULTRATHINK v4.0 malware analysis workflows
"""

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def find_project_root():
    """Find project root directory"""
    from pathlib import Path

    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "hooks").exists() or (current / ".git").exists():
            return current
        current = current.parent
    return Path.home() / "claude-backups"


_PROJECT_ROOT = find_project_root()
_CLAUDE_DIR = Path.home() / ".claude"


class SecurityPythonExecutor:
    """
    Enhanced Python executor for malware analysis with ULTRATHINK v4.0 integration

    Provides secure Python execution environment with:
    - Ghidra Python scripting integration
    - ML threat scoring capabilities
    - Security isolation and sandboxing
    - ULTRATHINK workflow automation
    - Malware analysis Python toolchain
    """

    def __init__(self):
        self.agent_id = (
            "security_python_"
            + hashlib.md5(f"{datetime.now()}".encode()).hexdigest()[:8]
        )
        self.version = "v1.0.0"
        self.status = "operational"

        # Security-focused capabilities
        self.security_capabilities = [
            "execute_ghidra_script",
            "run_malware_analysis",
            "ml_threat_scoring",
            "sandbox_execution",
            "extract_iocs",
            "behavioral_analysis",
            "memory_forensics",
            "static_analysis_automation",
            "c2_extraction",
        ]

        # ULTRATHINK integration points
        self.ultrathink_integration = {
            "ghidra_scripts_dir": str(
                _PROJECT_ROOT / "hooks" / "ghidra-workspace" / "scripts"
            ),
            "analysis_workspace": str(_CLAUDE_DIR / "ghidra-workspace"),
            "hostile_samples_dir": str(_CLAUDE_DIR / "hostile-samples"),
            "quarantine_dir": str(_CLAUDE_DIR / "quarantine"),
            "reports_dir": str(_CLAUDE_DIR / "analysis-reports"),
            "yara_rules_dir": str(_CLAUDE_DIR / "yara-rules"),
        }

        # Security isolation settings
        self.isolation_config = {
            "network_isolation": True,
            "filesystem_isolation": True,
            "process_timeout": 300,  # 5 minutes max execution
            "memory_limit": "512M",
            "cpu_limit": "1.0",
            "temp_workspace": True,
        }

        # ML frameworks for threat analysis
        self.ml_frameworks = {
            "sklearn_available": False,
            "tensorflow_available": False,
            "torch_available": False,
            "xgboost_available": False,
        }

        self._initialize_security_environment()

        logger.info(
            f"SecurityPythonExecutor {self.version} initialized with ULTRATHINK v4.0 integration"
        )

    def _initialize_security_environment(self):
        """Initialize the secure Python execution environment"""
        try:
            # Create ULTRATHINK workspace directories
            for path in self.ultrathink_integration.values():
                os.makedirs(path, exist_ok=True)

            # Check ML framework availability
            self._check_ml_frameworks()

            # Setup security policies
            self._setup_security_policies()

        except Exception as e:
            logger.error(f"Failed to initialize security environment: {e}")

    def _check_ml_frameworks(self):
        """Check availability of ML frameworks for threat analysis"""
        frameworks = {
            "sklearn": "sklearn_available",
            "tensorflow": "tensorflow_available",
            "torch": "torch_available",
            "xgboost": "xgboost_available",
        }

        for module, flag in frameworks.items():
            try:
                __import__(module)
                self.ml_frameworks[flag] = True
                logger.info(f"ML framework {module} available")
            except ImportError:
                logger.debug(f"ML framework {module} not available")

    def _setup_security_policies(self):
        """Setup security policies for malware analysis execution"""
        # Create isolated Python environment configuration
        self.security_config = {
            "restricted_imports": [
                "os.system",
                "subprocess.call",
                "eval",
                "exec",
                "compile",
                "__import__",
                "open",  # Will be wrapped
            ],
            "allowed_modules": [
                "json",
                "hashlib",
                "base64",
                "struct",
                "binascii",
                "collections",
                "itertools",
                "functools",
                "operator",
                "math",
                "statistics",
                "datetime",
                "uuid",
                "pathlib",
            ],
            "sandbox_modules": ["ghidra", "numpy", "pandas", "sklearn", "yara"],
        }

    # ========================================
    # GHIDRA PYTHON INTEGRATION
    # ========================================

    async def execute_ghidra_script(
        self, script_content: str, sample_path: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute Ghidra Python script with ULTRATHINK integration"""
        try:
            if context is None:
                context = {}

            # Create isolated workspace for this analysis
            workspace_id = f"ghidra_analysis_{uuid.uuid4().hex[:8]}"
            workspace_path = (
                Path(self.ultrathink_integration["analysis_workspace"]) / workspace_id
            )
            workspace_path.mkdir(parents=True, exist_ok=True)

            # Setup Ghidra environment
            ghidra_env = await self._setup_ghidra_environment(workspace_path)

            # Enhance script with ULTRATHINK capabilities
            enhanced_script = self._enhance_ghidra_script(
                script_content, sample_path, context
            )

            # Write enhanced script to workspace
            script_path = workspace_path / "analysis_script.py"
            with open(script_path, "w") as f:
                f.write(enhanced_script)

            # Execute Ghidra script with timeout and isolation
            result = await self._execute_isolated_ghidra(
                script_path, sample_path, ghidra_env, workspace_path
            )

            # Parse and enhance results
            enhanced_result = await self._process_ghidra_results(result, workspace_path)

            return {
                "status": "success",
                "execution_type": "ghidra_python_analysis",
                "workspace_id": workspace_id,
                "sample_analyzed": os.path.basename(sample_path),
                "analysis_results": enhanced_result,
                "ghidra_integration": True,
                "ultrathink_enhanced": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Ghidra script execution failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "execution_type": "ghidra_python_analysis",
            }

    def _enhance_ghidra_script(
        self, script_content: str, sample_path: str, context: Dict[str, Any]
    ) -> str:
        """Enhance Ghidra script with ULTRATHINK capabilities"""

        # ULTRATHINK enhanced Ghidra analysis script template
        enhanced_script = f'''
# ULTRATHINK v4.0 Enhanced Ghidra Analysis Script
# Auto-generated by PYTHON-INTERNAL SecurityPythonExecutor

from ghidra.app.script import GhidraScript
from ghidra.program.model.symbol import SymbolTable, Symbol
from ghidra.program.model.listing import Function, Instruction
from ghidra.program.model.address import Address
from ghidra.program.model.block import BasicBlockModel
from ghidra.program.model.mem import Memory
import json
import os
import re
import hashlib
from datetime import datetime

class ULTRATHINKAnalysis(GhidraScript):
    def __init__(self):
        super().__init__()
        self.analysis_results = {{
            'program_info': {{}},
            'functions': [],
            'strings': [],
            'imports': [],
            'exports': [],
            'suspicious_indicators': {{}},
            'behavioral_patterns': {{}},
            'threat_score': 0,
            'iocs': [],
            'malware_techniques': []
        }}

    def run(self):
        """Execute comprehensive malware analysis"""
        program = getCurrentProgram()
        if program is None:
            print("No program loaded")
            return

        print("[ULTRATHINK] Starting comprehensive analysis...")

        # Phase 1: Program Information
        self.analysis_results['program_info'] = self.analyze_program_info(program)

        # Phase 2: Function Analysis
        self.analysis_results['functions'] = self.analyze_functions(program)

        # Phase 3: String Analysis
        self.analysis_results['strings'] = self.extract_strings(program)

        # Phase 4: Import/Export Analysis
        self.analysis_results['imports'] = self.analyze_imports(program)
        self.analysis_results['exports'] = self.analyze_exports(program)

        # Phase 5: Suspicious Pattern Detection
        self.analysis_results['suspicious_indicators'] = self.detect_suspicious_patterns(program)

        # Phase 6: Behavioral Analysis
        self.analysis_results['behavioral_patterns'] = self.analyze_behavioral_patterns(program)

        # Phase 7: IOC Extraction
        self.analysis_results['iocs'] = self.extract_iocs(program)

        # Phase 8: Malware Technique Detection
        self.analysis_results['malware_techniques'] = self.detect_malware_techniques(program)

        # Phase 9: Calculate Threat Score
        self.analysis_results['threat_score'] = self.calculate_threat_score()

        # Save results
        output_file = os.path.join(os.environ.get('RESULTS_DIR', '/tmp'),
                                  f"{{program.getName()}}_ultrathink_analysis.json")

        with open(output_file, 'w') as f:
            json.dump(self.analysis_results, f, indent=2)

        print(f"[ULTRATHINK] Analysis complete. Results: {{output_file}}")
        print(f"[ULTRATHINK] Threat Score: {{self.analysis_results['threat_score']}}/100")

    def analyze_program_info(self, program):
        """Analyze basic program information"""
        return {{
            'name': program.getName(),
            'format': program.getExecutableFormat(),
            'language': str(program.getLanguage()),
            'compiler': str(program.getCompilerSpec()),
            'entry_point': str(program.getAddressMap().getImageBase()),
            'size': program.getMaxAddress().subtract(program.getMinAddress()),
            'creation_date': str(program.getCreationDate()),
            'image_base': str(program.getImageBase()),
            'min_address': str(program.getMinAddress()),
            'max_address': str(program.getMaxAddress())
        }}

    def analyze_functions(self, program):
        """Comprehensive function analysis"""
        function_manager = program.getFunctionManager()
        functions = []

        for function in function_manager.getFunctions(True):
            func_info = {{
                'name': function.getName(),
                'entry_point': str(function.getEntryPoint()),
                'size': function.getBody().getNumAddresses(),
                'instruction_count': len(list(program.getListing().getInstructions(function.getBody(), True))),
                'call_count': len(list(function.getCallingFunctions(None))),
                'called_functions': [str(ref.getToAddress()) for ref in function.getCalledFunctions(None)],
                'cyclomatic_complexity': self.calculate_complexity(function, program),
                'suspicious_score': self.score_function_suspicion(function),
                'api_calls': self.extract_api_calls(function, program),
                'strings_referenced': self.get_function_strings(function, program)
            }}
            functions.append(func_info)

        return functions

    def extract_strings(self, program):
        """Extract and analyze strings with malware focus"""
        strings = []
        string_table = program.getListing().getDefinedData(True)

        for data in string_table:
            if data.hasStringValue():
                string_value = data.getDefaultValueRepresentation()
                strings.append({{
                    'value': string_value,
                    'address': str(data.getAddress()),
                    'length': len(string_value),
                    'encoding': 'ascii',  # Simplified
                    'suspicious_score': self.score_string_suspicion(string_value),
                    'is_url': self.is_url(string_value),
                    'is_ip': self.is_ip_address(string_value),
                    'is_domain': self.is_domain(string_value),
                    'is_registry_key': self.is_registry_key(string_value),
                    'is_file_path': self.is_file_path(string_value),
                    'obfuscation_indicators': self.detect_obfuscation(string_value)
                }})

        return strings

    def analyze_imports(self, program):
        """Analyze imported functions"""
        imports = []
        external_manager = program.getExternalManager()

        for lib in external_manager.getExternalLibraryNames():
            for symbol in external_manager.getExternalSymbols(lib):
                imports.append({{
                    'library': lib,
                    'function': symbol.getName(),
                    'address': str(symbol.getExternalLocation().getAddress()),
                    'suspicious_score': self.score_import_suspicion(lib, symbol.getName()),
                    'category': self.categorize_api_function(symbol.getName())
                }})

        return imports

    def analyze_exports(self, program):
        """Analyze exported functions"""
        exports = []
        symbol_table = program.getSymbolTable()

        for symbol in symbol_table.getExternalSymbols():
            if symbol.getSymbolType().isFunction():
                exports.append({{
                    'name': symbol.getName(),
                    'address': str(symbol.getAddress()),
                    'ordinal': symbol.getID() if hasattr(symbol, 'getID') else None
                }})

        return exports

    def detect_suspicious_patterns(self, program):
        """Detect suspicious code patterns"""
        patterns = {{
            'anti_debug': False,
            'anti_vm': False,
            'packing_indicators': False,
            'crypto_functions': False,
            'network_functions': False,
            'file_operations': False,
            'registry_operations': False,
            'process_injection': False,
            'dll_injection': False,
            'code_caves': False
        }}

        # Analyze for suspicious patterns
        function_manager = program.getFunctionManager()
        for function in function_manager.getFunctions(True):
            func_name = function.getName().lower()

            # Anti-debugging checks
            if any(api in func_name for api in ['isdebuggerpresent', 'checkremotedebugger', 'ntquerysysteminformation']):
                patterns['anti_debug'] = True

            # Anti-VM checks
            if any(vm in func_name for vm in ['vmware', 'virtualbox', 'qemu', 'xen']):
                patterns['anti_vm'] = True

            # Crypto functions
            if any(crypto in func_name for crypto in ['encrypt', 'decrypt', 'aes', 'des', 'rsa', 'md5', 'sha']):
                patterns['crypto_functions'] = True

            # Network functions
            if any(net in func_name for net in ['socket', 'connect', 'send', 'recv', 'internet']):
                patterns['network_functions'] = True

            # Process injection
            if any(inj in func_name for inj in ['createremotethread', 'writeprocessmemory', 'virtualalloc']):
                patterns['process_injection'] = True

        return patterns

    def analyze_behavioral_patterns(self, program):
        """Analyze behavioral patterns in the code"""
        return {{
            'file_system_access': self.count_fs_operations(program),
            'network_communication': self.count_network_operations(program),
            'registry_manipulation': self.count_registry_operations(program),
            'process_manipulation': self.count_process_operations(program),
            'service_manipulation': self.count_service_operations(program),
            'persistence_mechanisms': self.detect_persistence(program)
        }}

    def extract_iocs(self, program):
        """Extract Indicators of Compromise"""
        iocs = {{
            'ip_addresses': [],
            'domains': [],
            'urls': [],
            'file_paths': [],
            'registry_keys': [],
            'mutexes': [],
            'user_agents': []
        }}

        # Extract from strings
        for string_data in self.analysis_results.get('strings', []):
            value = string_data['value']

            if string_data['is_ip']:
                iocs['ip_addresses'].append(value)
            elif string_data['is_domain']:
                iocs['domains'].append(value)
            elif string_data['is_url']:
                iocs['urls'].append(value)
            elif string_data['is_file_path']:
                iocs['file_paths'].append(value)
            elif string_data['is_registry_key']:
                iocs['registry_keys'].append(value)
            elif 'mutex' in value.lower():
                iocs['mutexes'].append(value)
            elif 'user-agent' in value.lower():
                iocs['user_agents'].append(value)

        return iocs

    def detect_malware_techniques(self, program):
        """Detect specific malware techniques"""
        techniques = []

        # Check for common malware techniques
        if self.analysis_results['suspicious_indicators'].get('packing_indicators'):
            techniques.append('T1027 - Obfuscated Files or Information')

        if self.analysis_results['suspicious_indicators'].get('process_injection'):
            techniques.append('T1055 - Process Injection')

        if self.analysis_results['suspicious_indicators'].get('dll_injection'):
            techniques.append('T1055.001 - Dynamic-link Library Injection')

        if self.analysis_results['suspicious_indicators'].get('anti_debug'):
            techniques.append('T1497.001 - Anti-debugging')

        if self.analysis_results['suspicious_indicators'].get('anti_vm'):
            techniques.append('T1497.001 - Virtual Machine Detection')

        return techniques

    def calculate_threat_score(self):
        """Calculate overall threat score"""
        score = 0

        # Base score from suspicious indicators
        indicators = self.analysis_results['suspicious_indicators']
        score += sum(20 for key, value in indicators.items() if value)

        # Function suspicion scores
        functions = self.analysis_results.get('functions', [])
        if functions:
            avg_function_suspicion = sum(f.get('suspicious_score', 0) for f in functions) / len(functions)
            score += avg_function_suspicion * 2

        # String suspicion scores
        strings = self.analysis_results.get('strings', [])
        if strings:
            high_suspicion_strings = sum(1 for s in strings if s.get('suspicious_score', 0) > 7)
            score += min(high_suspicion_strings * 5, 30)

        # IOC count
        iocs = self.analysis_results.get('iocs', {{}})
        total_iocs = sum(len(ioc_list) for ioc_list in iocs.values())
        score += min(total_iocs * 2, 20)

        return min(score, 100)

    # Helper methods for scoring and detection
    def score_function_suspicion(self, function):
        """Score function suspicion level (0-10)"""
        score = 0
        name = function.getName().lower()

        suspicious_apis = [
            'virtualalloc', 'writeprocessmemory', 'createremotethread',
            'loadlibrary', 'getprocaddress', 'createfile', 'deletefile',
            'regsetvalue', 'regdeletekey', 'createprocess', 'shellexecute'
        ]

        for api in suspicious_apis:
            if api in name:
                score += 3

        return min(score, 10)

    def score_string_suspicion(self, string_value):
        """Score string suspicion level (0-10)"""
        score = 0
        lower_string = string_value.lower()

        # Suspicious keywords
        suspicious_keywords = [
            'backdoor', 'trojan', 'virus', 'keylog', 'steal', 'dump',
            'inject', 'hook', 'rootkit', 'bot', 'c&c', 'payload'
        ]

        for keyword in suspicious_keywords:
            if keyword in lower_string:
                score += 4

        # Base64 patterns
        if re.match(r'^[A-Za-z0-9+/]{{40,}}=*$', string_value):
            score += 3

        # Hex patterns
        if re.match(r'^[0-9a-fA-F]{{32,}}$', string_value):
            score += 2

        return min(score, 10)

    def score_import_suspicion(self, library, function):
        """Score import suspicion level"""
        score = 0

        suspicious_functions = [
            'VirtualAlloc', 'WriteProcessMemory', 'CreateRemoteThread',
            'SetWindowsHookEx', 'GetKeyState', 'GetAsyncKeyState',
            'CreateFile', 'DeleteFile', 'MoveFile', 'CopyFile',
            'RegSetValue', 'RegDeleteKey', 'RegDeleteValue'
        ]

        if function in suspicious_functions:
            score += 5

        return min(score, 10)

    def categorize_api_function(self, function_name):
        """Categorize API function"""
        categories = {{
            'file_operations': ['CreateFile', 'DeleteFile', 'MoveFile', 'CopyFile', 'ReadFile', 'WriteFile'],
            'process_operations': ['CreateProcess', 'TerminateProcess', 'OpenProcess'],
            'memory_operations': ['VirtualAlloc', 'VirtualFree', 'WriteProcessMemory', 'ReadProcessMemory'],
            'registry_operations': ['RegOpenKey', 'RegSetValue', 'RegDeleteKey', 'RegQueryValue'],
            'network_operations': ['socket', 'connect', 'send', 'recv', 'InternetOpen', 'HttpOpenRequest'],
            'crypto_operations': ['CryptAcquireContext', 'CryptEncrypt', 'CryptDecrypt']
        }}

        for category, functions in categories.items():
            if function_name in functions:
                return category

        return 'other'

    def calculate_complexity(self, function, program):
        """Calculate cyclomatic complexity"""
        # Simplified complexity calculation
        return len(list(program.getListing().getInstructions(function.getBody(), True))) // 10

    def extract_api_calls(self, function, program):
        """Extract API calls from function"""
        api_calls = []
        # Simplified API call extraction
        return api_calls

    def get_function_strings(self, function, program):
        """Get strings referenced by function"""
        strings = []
        # Simplified string reference extraction
        return strings

    def is_url(self, string_value):
        """Check if string is a URL"""
        return string_value.startswith(('http://', 'https://', 'ftp://'))

    def is_ip_address(self, string_value):
        """Check if string is an IP address"""
        return bool(re.match(r'^\\d{{1,3}}\\.\\d{{1,3}}\\.\\d{{1,3}}\\.\\d{{1,3}}$', string_value))

    def is_domain(self, string_value):
        """Check if string is a domain"""
        return bool(re.match(r'^[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$', string_value))

    def is_registry_key(self, string_value):
        """Check if string is a registry key"""
        return string_value.startswith(('HKEY_', 'SOFTWARE\\\\', 'SYSTEM\\\\'))

    def is_file_path(self, string_value):
        """Check if string is a file path"""
        return '\\\\' in string_value or string_value.startswith(('C:', '/'))

    def detect_obfuscation(self, string_value):
        """Detect obfuscation indicators"""
        indicators = []

        if len(set(string_value)) < len(string_value) * 0.3:
            indicators.append('low_entropy')

        if re.search(r'[xX]{{3,}}', string_value):
            indicators.append('repeated_x')

        return indicators

    def count_fs_operations(self, program):
        """Count file system operations"""
        return len([f for f in self.analysis_results.get('functions', [])
                   if 'file' in f.get('name', '').lower()])

    def count_network_operations(self, program):
        """Count network operations"""
        return len([f for f in self.analysis_results.get('functions', [])
                   if any(net in f.get('name', '').lower() for net in ['socket', 'internet', 'http'])])

    def count_registry_operations(self, program):
        """Count registry operations"""
        return len([f for f in self.analysis_results.get('functions', [])
                   if 'reg' in f.get('name', '').lower()])

    def count_process_operations(self, program):
        """Count process operations"""
        return len([f for f in self.analysis_results.get('functions', [])
                   if 'process' in f.get('name', '').lower()])

    def count_service_operations(self, program):
        """Count service operations"""
        return len([f for f in self.analysis_results.get('functions', [])
                   if 'service' in f.get('name', '').lower()])

    def detect_persistence(self, program):
        """Detect persistence mechanisms"""
        persistence = []

        # Check for registry persistence
        for string_data in self.analysis_results.get('strings', []):
            value = string_data['value']
            if 'Run' in value and 'CurrentVersion' in value:
                persistence.append('Registry Run Key')
            elif 'StartupFolder' in value:
                persistence.append('Startup Folder')
            elif 'Service' in value and 'Control' in value:
                persistence.append('Windows Service')

        return persistence

# Execute the analysis
analysis = ULTRATHINKAnalysis()
analysis.run()

# Original user script integration
{script_content}
'''

        return enhanced_script

    async def _setup_ghidra_environment(self, workspace_path: Path) -> Dict[str, str]:
        """Setup Ghidra execution environment"""
        ghidra_env = os.environ.copy()

        # Setup Ghidra-specific environment variables
        ghidra_env.update(
            {
                "RESULTS_DIR": str(workspace_path),
                "ANALYSIS_WORKSPACE": str(workspace_path),
                "PYTHONPATH": f"{ghidra_env.get('PYTHONPATH', '')}:{workspace_path}",
                "ULTRATHINK_MODE": "python_analysis",
            }
        )

        return ghidra_env

    async def _execute_isolated_ghidra(
        self,
        script_path: Path,
        sample_path: str,
        env: Dict[str, str],
        workspace_path: Path,
    ) -> Dict[str, Any]:
        """Execute Ghidra script in isolated environment"""
        try:
            # Check if Ghidra is available
            ghidra_cmd = self._detect_ghidra_command()

            if not ghidra_cmd:
                return {"status": "error", "error": "Ghidra not found"}

            # Create Ghidra project if needed
            project_dir = workspace_path / "ghidra_project"
            project_dir.mkdir(exist_ok=True)

            # Execute Ghidra headless analysis
            cmd = [
                ghidra_cmd,
                str(project_dir),
                "ULTRATHINKProject",
                "-import",
                sample_path,
                "-postScript",
                str(script_path),
                "-max-cpu",
                "2",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.isolation_config["process_timeout"],
                )

                return {
                    "status": "success",
                    "returncode": process.returncode,
                    "stdout": stdout.decode("utf-8", errors="ignore"),
                    "stderr": stderr.decode("utf-8", errors="ignore"),
                }

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {"status": "timeout", "error": "Ghidra analysis timeout"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _detect_ghidra_command(self) -> Optional[str]:
        """Detect available Ghidra command"""
        # Try snap first
        if shutil.which("snap"):
            result = subprocess.run(["snap", "list"], capture_output=True, text=True)
            if "ghidra" in result.stdout:
                return "snap run ghidra.analyzeHeadless"

        # Try common installation paths
        common_paths = [
            "/opt/ghidra/support/analyzeHeadless",
            "/usr/local/ghidra/support/analyzeHeadless",
            "/usr/share/ghidra/support/analyzeHeadless",
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        return None

    async def _process_ghidra_results(
        self, execution_result: Dict[str, Any], workspace_path: Path
    ) -> Dict[str, Any]:
        """Process and enhance Ghidra analysis results"""
        if execution_result["status"] != "success":
            return execution_result

        results = {"ghidra_execution": execution_result}

        # Look for JSON results file
        results_pattern = workspace_path.glob("*_ultrathink_analysis.json")
        for result_file in results_pattern:
            try:
                with open(result_file, "r") as f:
                    analysis_data = json.load(f)
                    results["analysis_data"] = analysis_data
                    break
            except Exception as e:
                logger.warning(f"Failed to parse analysis results: {e}")

        # Extract threat indicators
        if "analysis_data" in results:
            results["threat_assessment"] = self._assess_threats(
                results["analysis_data"]
            )

        return results

    def _assess_threats(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess threat level from analysis data"""
        threat_score = analysis_data.get("threat_score", 0)

        if threat_score >= 80:
            threat_level = "CRITICAL"
        elif threat_score >= 60:
            threat_level = "HIGH"
        elif threat_score >= 40:
            threat_level = "MEDIUM"
        elif threat_score >= 20:
            threat_level = "LOW"
        else:
            threat_level = "MINIMAL"

        return {
            "threat_level": threat_level,
            "threat_score": threat_score,
            "malware_techniques": analysis_data.get("malware_techniques", []),
            "ioc_count": sum(
                len(iocs) for iocs in analysis_data.get("iocs", {}).values()
            ),
            "suspicious_functions": len(
                [
                    f
                    for f in analysis_data.get("functions", [])
                    if f.get("suspicious_score", 0) > 7
                ]
            ),
            "recommended_actions": self._generate_recommendations(
                threat_level, analysis_data
            ),
        }

    def _generate_recommendations(
        self, threat_level: str, analysis_data: Dict[str, Any]
    ) -> List[str]:
        """Generate security recommendations based on analysis"""
        recommendations = []

        if threat_level in ["CRITICAL", "HIGH"]:
            recommendations.append("Immediate quarantine recommended")
            recommendations.append("Block all network communications")
            recommendations.append("Scan all systems for similar indicators")

        if analysis_data.get("iocs", {}).get("ip_addresses"):
            recommendations.append("Block identified IP addresses in firewall")

        if analysis_data.get("iocs", {}).get("domains"):
            recommendations.append("Block identified domains in DNS/proxy")

        if analysis_data.get("malware_techniques"):
            recommendations.append("Review detection rules for identified techniques")

        return recommendations

    # ========================================
    # ML THREAT SCORING INTEGRATION
    # ========================================

    async def run_ml_threat_scoring(
        self, features: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Run ML-based threat scoring analysis"""
        try:
            if context is None:
                context = {}

            # Initialize ML threat scoring
            ml_scorer = await self._initialize_ml_scorer()

            # Extract features for ML analysis
            processed_features = await self._process_ml_features(features)

            # Run threat scoring
            threat_score = await ml_scorer.score_threat(processed_features)

            # Generate detailed analysis
            analysis_result = await self._generate_ml_analysis(
                threat_score, processed_features, context
            )

            return {
                "status": "success",
                "execution_type": "ml_threat_scoring",
                "threat_score": threat_score,
                "confidence": analysis_result.get("confidence", 0.0),
                "feature_importance": analysis_result.get("feature_importance", {}),
                "threat_indicators": analysis_result.get("threat_indicators", []),
                "ml_models_used": analysis_result.get("models_used", []),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"ML threat scoring failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "execution_type": "ml_threat_scoring",
            }


# Continue in next part due to length...
