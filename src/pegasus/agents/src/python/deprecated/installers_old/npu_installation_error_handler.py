#!/usr/bin/env python3
"""
NPU Installation Error Handler
Comprehensive error handling and recovery system for NPU binary distribution
Provides detailed diagnostics, recovery options, and graceful degradation
"""

import os
import sys
import json
import logging
import traceback
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = "critical"     # Installation must abort
    HIGH = "high"            # Major functionality affected
    MEDIUM = "medium"        # Minor functionality affected
    LOW = "low"              # Cosmetic or performance issues
    INFO = "info"            # Informational messages

class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"                    # Download/connectivity issues
    HARDWARE = "hardware"                  # Hardware detection problems
    PERMISSIONS = "permissions"            # File/directory access issues
    DEPENDENCIES = "dependencies"          # Missing system dependencies
    COMPILATION = "compilation"            # Build/compilation failures
    VALIDATION = "validation"              # Security/integrity validation
    CONFIGURATION = "configuration"       # Configuration errors
    SYSTEM = "system"                     # System-level issues
    USER_INPUT = "user_input"             # Invalid user input
    INTEGRATION = "integration"           # Integration failures
    UNKNOWN = "unknown"                   # Unclassified errors

@dataclass
class ErrorDetails:
    """Comprehensive error information"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    title: str
    description: str
    technical_details: str
    user_message: str
    recovery_actions: List[str]
    context: Dict[str, Any]
    timestamp: float
    system_info: Dict[str, str]
    stack_trace: Optional[str] = None

@dataclass
class RecoveryResult:
    """Recovery attempt result"""
    success: bool
    action_taken: str
    details: str
    time_taken: float
    additional_errors: List[str]

class NPUInstallationErrorHandler:
    """
    Comprehensive error handling system for NPU installation
    Provides diagnostics, recovery, and graceful degradation
    """

    def __init__(self, log_file: Optional[str] = None):
        self.error_history: List[ErrorDetails] = []
        self.recovery_attempts: List[RecoveryResult] = []
        self.system_context = self._gather_system_context()

        # Setup logging
        if log_file:
            self._setup_file_logging(log_file)

        logger.info("NPU Installation Error Handler initialized")

    def _gather_system_context(self) -> Dict[str, str]:
        """Gather comprehensive system context for error diagnosis"""
        context = {
            "platform": sys.platform,
            "python_version": sys.version,
            "working_directory": os.getcwd(),
            "user": os.environ.get("USER", "unknown"),
            "path": os.environ.get("PATH", ""),
            "home": os.environ.get("HOME", ""),
        }

        # Add system-specific information
        try:
            import platform
            context.update({
                "platform_system": platform.system(),
                "platform_release": platform.release(),
                "platform_machine": platform.machine(),
                "platform_processor": platform.processor(),
            })
        except ImportError:
            pass

        # Check for common tools
        tools = ["curl", "wget", "git", "rustc", "cargo", "gcc", "clang", "python3"]
        for tool in tools:
            try:
                result = subprocess.run([tool, "--version"],
                                      capture_output=True, text=True, timeout=5)
                context[f"tool_{tool}"] = "available" if result.returncode == 0 else "unavailable"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                context[f"tool_{tool}"] = "not_found"

        return context

    def _setup_file_logging(self, log_file: str) -> None:
        """Setup file logging for error tracking"""
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.info(f"File logging enabled: {log_file}")
        except (OSError, IOError) as e:
            logger.warning(f"Failed to setup file logging: {e}")

    def handle_error(self,
                    exception: Exception,
                    category: ErrorCategory,
                    severity: ErrorSeverity,
                    context: Optional[Dict[str, Any]] = None,
                    recovery_actions: Optional[List[str]] = None) -> ErrorDetails:
        """
        Comprehensive error handling with classification and recovery
        """
        error_id = f"NPU_{category.value}_{int(time.time())}"

        # Generate user-friendly messages
        title, description, user_message = self._generate_error_messages(
            exception, category, severity
        )

        # Create error details
        error_details = ErrorDetails(
            error_id=error_id,
            category=category,
            severity=severity,
            title=title,
            description=description,
            technical_details=str(exception),
            user_message=user_message,
            recovery_actions=recovery_actions or self._suggest_recovery_actions(category, exception),
            context=context or {},
            timestamp=time.time(),
            system_info=self.system_context,
            stack_trace=traceback.format_exc()
        )

        # Log error appropriately
        self._log_error(error_details)

        # Store error for analysis
        self.error_history.append(error_details)

        # Attempt automatic recovery for non-critical errors
        if severity != ErrorSeverity.CRITICAL:
            self._attempt_automatic_recovery(error_details)

        return error_details

    def _generate_error_messages(self,
                                exception: Exception,
                                category: ErrorCategory,
                                severity: ErrorSeverity) -> tuple[str, str, str]:
        """Generate user-friendly error messages"""

        # Category-specific message templates
        message_templates = {
            ErrorCategory.NETWORK: {
                "title": "Network Connection Problem",
                "description": "Failed to download NPU bridge components",
                "user_message": "Please check your internet connection and try again. "
                              "If behind a firewall, ensure access to GitHub releases."
            },
            ErrorCategory.HARDWARE: {
                "title": "Hardware Detection Issue",
                "description": "Could not detect Intel NPU hardware",
                "user_message": "NPU hardware was not detected. Installation will continue "
                              "without NPU-specific optimizations."
            },
            ErrorCategory.PERMISSIONS: {
                "title": "Permission Denied",
                "description": "Insufficient permissions for installation",
                "user_message": "Please ensure you have write permissions to the installation "
                              "directory, or run with elevated privileges."
            },
            ErrorCategory.DEPENDENCIES: {
                "title": "Missing Dependencies",
                "description": "Required system dependencies are missing",
                "user_message": "Please install required system packages. Check the "
                              "documentation for your platform's specific requirements."
            },
            ErrorCategory.COMPILATION: {
                "title": "Compilation Failed",
                "description": "Failed to compile NPU bridge from source",
                "user_message": "Source compilation failed. This may be due to missing "
                              "development tools or incompatible system configuration."
            },
            ErrorCategory.VALIDATION: {
                "title": "Security Validation Failed",
                "description": "Downloaded files failed security validation",
                "user_message": "Security validation failed. This may indicate a corrupted "
                              "download or potential security issue."
            },
        }

        template = message_templates.get(category, {
            "title": "Installation Error",
            "description": "An unexpected error occurred during installation",
            "user_message": "An unexpected error occurred. Please check the logs for details."
        })

        # Customize based on specific exception
        title = template["title"]
        description = f"{template['description']}: {str(exception)}"
        user_message = template["user_message"]

        # Add severity-specific modifications
        if severity == ErrorSeverity.CRITICAL:
            user_message += " Installation cannot continue."
        elif severity == ErrorSeverity.HIGH:
            user_message += " Some features may not work correctly."

        return title, description, user_message

    def _suggest_recovery_actions(self,
                                 category: ErrorCategory,
                                 exception: Exception) -> List[str]:
        """Suggest recovery actions based on error category"""

        recovery_suggestions = {
            ErrorCategory.NETWORK: [
                "Check internet connection",
                "Retry download with exponential backoff",
                "Try alternative download mirrors",
                "Use manual download and local installation"
            ],
            ErrorCategory.HARDWARE: [
                "Continue without NPU-specific optimizations",
                "Use generic binary distribution",
                "Verify system hardware configuration"
            ],
            ErrorCategory.PERMISSIONS: [
                "Change installation directory to user-writable location",
                "Run installer with elevated privileges",
                "Fix directory permissions"
            ],
            ErrorCategory.DEPENDENCIES: [
                "Install missing system packages",
                "Update package manager repositories",
                "Use containerized installation",
                "Switch to static binary distribution"
            ],
            ErrorCategory.COMPILATION: [
                "Use pre-compiled binary instead",
                "Install additional development tools",
                "Update Rust toolchain",
                "Use fallback compilation options"
            ],
            ErrorCategory.VALIDATION: [
                "Re-download from official source",
                "Verify download integrity manually",
                "Use alternative installation method",
                "Skip validation if trusted source (not recommended)"
            ],
        }

        return recovery_suggestions.get(category, [
            "Restart installation process",
            "Check system requirements",
            "Consult documentation",
            "Contact support"
        ])

    def _log_error(self, error_details: ErrorDetails) -> None:
        """Log error with appropriate level"""

        message = f"[{error_details.error_id}] {error_details.title}: {error_details.description}"

        if error_details.severity == ErrorSeverity.CRITICAL:
            logger.critical(message)
        elif error_details.severity == ErrorSeverity.HIGH:
            logger.error(message)
        elif error_details.severity == ErrorSeverity.MEDIUM:
            logger.warning(message)
        else:
            logger.info(message)

        # Log technical details at debug level
        logger.debug(f"Technical details: {error_details.technical_details}")
        if error_details.stack_trace:
            logger.debug(f"Stack trace: {error_details.stack_trace}")

    def _attempt_automatic_recovery(self, error_details: ErrorDetails) -> Optional[RecoveryResult]:
        """Attempt automatic recovery based on error type"""

        start_time = time.time()
        recovery_actions = {
            ErrorCategory.NETWORK: self._recover_network_error,
            ErrorCategory.PERMISSIONS: self._recover_permission_error,
            ErrorCategory.DEPENDENCIES: self._recover_dependency_error,
        }

        recovery_func = recovery_actions.get(error_details.category)
        if not recovery_func:
            return None

        try:
            logger.info(f"Attempting automatic recovery for {error_details.error_id}")
            result = recovery_func(error_details)
            result.time_taken = time.time() - start_time

            self.recovery_attempts.append(result)

            if result.success:
                logger.info(f"Recovery successful: {result.action_taken}")
            else:
                logger.warning(f"Recovery failed: {result.details}")

            return result

        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            return RecoveryResult(
                success=False,
                action_taken="automatic_recovery",
                details=f"Recovery attempt raised exception: {e}",
                time_taken=time.time() - start_time,
                additional_errors=[str(e)]
            )

    def _recover_network_error(self, error_details: ErrorDetails) -> RecoveryResult:
        """Attempt to recover from network errors"""

        # Simple connectivity test
        try:
            import urllib.request

            # Test connectivity to GitHub
            urllib.request.urlopen("https://api.github.com", timeout=10)

            return RecoveryResult(
                success=True,
                action_taken="network_connectivity_verified",
                details="Network connectivity restored",
                time_taken=0,
                additional_errors=[]
            )

        except Exception as e:
            return RecoveryResult(
                success=False,
                action_taken="network_connectivity_test",
                details=f"Network still unavailable: {e}",
                time_taken=0,
                additional_errors=[str(e)]
            )

    def _recover_permission_error(self, error_details: ErrorDetails) -> RecoveryResult:
        """Attempt to recover from permission errors"""

        # Try to find alternative installation directory
        try:
            alternative_dirs = [
                os.path.expanduser("~/.local"),
                os.path.expanduser("~/bin"),
                "/tmp/npu-bridge-install"
            ]

            for alt_dir in alternative_dirs:
                try:
                    Path(alt_dir).mkdir(parents=True, exist_ok=True)
                    test_file = Path(alt_dir) / "test_write"
                    test_file.write_text("test")
                    test_file.unlink()

                    return RecoveryResult(
                        success=True,
                        action_taken=f"alternative_directory_found",
                        details=f"Found writable directory: {alt_dir}",
                        time_taken=0,
                        additional_errors=[]
                    )

                except (OSError, IOError):
                    continue

            return RecoveryResult(
                success=False,
                action_taken="find_alternative_directory",
                details="No writable directories found",
                time_taken=0,
                additional_errors=[]
            )

        except Exception as e:
            return RecoveryResult(
                success=False,
                action_taken="permission_recovery",
                details=f"Permission recovery failed: {e}",
                time_taken=0,
                additional_errors=[str(e)]
            )

    def _recover_dependency_error(self, error_details: ErrorDetails) -> RecoveryResult:
        """Attempt to recover from missing dependencies"""

        try:
            # Check if we can install dependencies automatically
            if self._can_install_packages():
                missing_packages = self._detect_missing_packages()

                if missing_packages:
                    return RecoveryResult(
                        success=False,
                        action_taken="dependency_detection",
                        details=f"Missing packages detected: {', '.join(missing_packages)}",
                        time_taken=0,
                        additional_errors=[]
                    )
                else:
                    return RecoveryResult(
                        success=True,
                        action_taken="dependency_check",
                        details="All required dependencies are available",
                        time_taken=0,
                        additional_errors=[]
                    )
            else:
                return RecoveryResult(
                    success=False,
                    action_taken="dependency_recovery",
                    details="Cannot install packages automatically",
                    time_taken=0,
                    additional_errors=[]
                )

        except Exception as e:
            return RecoveryResult(
                success=False,
                action_taken="dependency_recovery",
                details=f"Dependency recovery failed: {e}",
                time_taken=0,
                additional_errors=[str(e)]
            )

    def _can_install_packages(self) -> bool:
        """Check if we can install packages automatically"""
        package_managers = ["apt-get", "yum", "dnf", "pacman", "brew"]

        for pm in package_managers:
            try:
                result = subprocess.run([pm, "--version"],
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        return False

    def _detect_missing_packages(self) -> List[str]:
        """Detect missing system packages"""
        required_packages = {
            "build-essential": ["gcc", "g++", "make"],
            "pkg-config": ["pkg-config"],
            "libssl-dev": ["openssl"],
            "curl": ["curl"],
        }

        missing = []

        for package, commands in required_packages.items():
            for cmd in commands:
                try:
                    result = subprocess.run([cmd, "--version"],
                                          capture_output=True, timeout=5)
                    if result.returncode == 0:
                        break
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            else:
                missing.append(package)

        return missing

    def get_diagnostic_report(self) -> Dict[str, Any]:
        """Generate comprehensive diagnostic report"""

        error_summary = {}
        for category in ErrorCategory:
            category_errors = [e for e in self.error_history if e.category == category]
            error_summary[category.value] = {
                "count": len(category_errors),
                "severities": [e.severity.value for e in category_errors]
            }

        recovery_summary = {
            "total_attempts": len(self.recovery_attempts),
            "successful_recoveries": len([r for r in self.recovery_attempts if r.success]),
            "failed_recoveries": len([r for r in self.recovery_attempts if not r.success])
        }

        return {
            "system_context": self.system_context,
            "error_summary": error_summary,
            "recovery_summary": recovery_summary,
            "total_errors": len(self.error_history),
            "critical_errors": len([e for e in self.error_history if e.severity == ErrorSeverity.CRITICAL]),
            "recent_errors": [asdict(e) for e in self.error_history[-5:]],  # Last 5 errors
            "recovery_attempts": [asdict(r) for r in self.recovery_attempts[-3:]]  # Last 3 recovery attempts
        }

    def export_error_log(self, file_path: str) -> bool:
        """Export comprehensive error log to file"""
        try:
            report = {
                "diagnostic_report": self.get_diagnostic_report(),
                "full_error_history": [asdict(e) for e in self.error_history],
                "full_recovery_history": [asdict(r) for r in self.recovery_attempts],
                "export_timestamp": time.time()
            }

            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"Error log exported to: {file_path}")
            return True

        except (OSError, IOError) as e:
            logger.error(f"Failed to export error log: {e}")
            return False

    def should_abort_installation(self) -> bool:
        """Determine if installation should be aborted based on error history"""

        # Abort if we have critical errors
        critical_errors = [e for e in self.error_history if e.severity == ErrorSeverity.CRITICAL]
        if critical_errors:
            return True

        # Abort if too many high-severity errors
        high_errors = [e for e in self.error_history if e.severity == ErrorSeverity.HIGH]
        if len(high_errors) >= 3:
            return True

        # Abort if recovery keeps failing
        recent_recoveries = self.recovery_attempts[-5:]  # Last 5 attempts
        if len(recent_recoveries) >= 3 and all(not r.success for r in recent_recoveries):
            return True

        return False

    def get_user_guidance(self) -> str:
        """Generate user guidance based on error patterns"""

        if not self.error_history:
            return "Installation proceeding normally."

        # Analyze error patterns
        categories = [e.category for e in self.error_history]

        if categories.count(ErrorCategory.NETWORK) > 2:
            return ("Multiple network errors detected. Please check your internet "
                   "connection and consider using offline installation method.")

        if categories.count(ErrorCategory.PERMISSIONS) > 1:
            return ("Permission errors detected. Consider changing installation directory "
                   "or running with appropriate privileges.")

        if categories.count(ErrorCategory.DEPENDENCIES) > 1:
            return ("Missing dependencies detected. Please install required system "
                   "packages for your platform.")

        if any(e.severity == ErrorSeverity.CRITICAL for e in self.error_history):
            return ("Critical error encountered. Installation cannot continue. "
                   "Please check the error log for details.")

        return ("Some issues encountered during installation. Check logs for details, "
               "but installation may still succeed.")


def main():
    """Test the error handler"""
    handler = NPUInstallationErrorHandler("npu_installation_errors.log")

    # Test different error scenarios
    try:
        raise FileNotFoundError("Test file not found")
    except Exception as e:
        handler.handle_error(
            e,
            ErrorCategory.DEPENDENCIES,
            ErrorSeverity.MEDIUM,
            context={"test": True}
        )

    # Generate diagnostic report
    report = handler.get_diagnostic_report()
    print("Diagnostic Report:")
    print(json.dumps(report, indent=2, default=str))

    # Export full log
    handler.export_error_log("npu_error_report.json")


if __name__ == "__main__":
    main()