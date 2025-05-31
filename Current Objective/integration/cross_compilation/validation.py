"""
Core validation system implementation for cross-compilation.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import shutil
import psutil

from .toolchain import ToolchainValidator
from ..monitoring.monitor import MonitoringManager

class ValidationLevel(Enum):
    """Validation level enumeration."""
    L1_BASIC = auto()  # Basic compatibility
    L2_RESOURCE = auto()  # Resource validation
    L3_TOOLCHAIN = auto()  # Toolchain verification
    L4_FULL = auto()  # Full integration

@dataclass
class ValidationResult:
    """Validation result container."""
    success: bool
    level: ValidationLevel
    messages: List[str]
    timestamp: datetime
    details: Dict[str, Any]

@dataclass
class BuildPlatform:
    """Platform specification."""
    architecture: str
    triple: str
    features: List[str]
    abi: str
    requirements: Dict[str, Any]

class EnvironmentValidator:
    """Validates build environment configuration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.required_vars = {
            "CROSS_COMPILE": str,
            "TARGET_ARCH": str,
            "TOOLCHAIN_PREFIX": str,
            "BUILD_ROOT": Path,
            "TARGET_SYSROOT": Path
        }

    def validate_environment(self) -> ValidationResult:
        """Validate build environment."""
        messages = []
        details = {}

        # Validate environment variables
        env_result = self._validate_variables()
        messages.extend(env_result.messages)
        details["variables"] = env_result.details

        # Validate paths
        path_result = self._validate_paths()
        messages.extend(path_result.messages)
        details["paths"] = path_result.details

        # Validate permissions
        perm_result = self._validate_permissions()
        messages.extend(perm_result.messages)
        details["permissions"] = perm_result.details

        success = all(r.success for r in [env_result, path_result, perm_result])
        return ValidationResult(
            success=success,
            level=ValidationLevel.L1_BASIC,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_variables(self) -> ValidationResult:
        """Validate environment variables."""
        messages = []
        success = True
        details = {}

        for var_name, var_type in self.required_vars.items():
            if var_name not in self.config:
                messages.append(f"Missing required variable: {var_name}")
                success = False
                continue

            value = self.config[var_name]
            if not isinstance(value, var_type):
                messages.append(
                    f"Invalid type for {var_name}: expected {var_type}, got {type(value)}"
                )
                success = False
            details[var_name] = str(value)

        return ValidationResult(
            success=success,
            level=ValidationLevel.L1_BASIC,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_paths(self) -> ValidationResult:
        """Validate required paths."""
        messages = []
        success = True
        details = {}

        for path_str in self.config.get("required_paths", []):
            path = Path(path_str)
            if not path.exists():
                messages.append(f"Missing required path: {path}")
                success = False
            details[str(path)] = {"exists": path.exists()}

        return ValidationResult(
            success=success,
            level=ValidationLevel.L1_BASIC,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_permissions(self) -> ValidationResult:
        """Validate path permissions."""
        messages = []
        success = True
        details = {}

        for path_str in self.config.get("required_paths", []):
            path = Path(path_str)
            if path.exists():
                try:
                    if not os.access(path, os.R_OK):
                        messages.append(f"No read permission: {path}")
                        success = False
                    if path.is_dir() and not os.access(path, os.X_OK):
                        messages.append(f"No execute permission: {path}")
                        success = False
                    details[str(path)] = {
                        "readable": os.access(path, os.R_OK),
                        "executable": os.access(path, os.X_OK)
                    }
                except Exception as e:
                    messages.append(f"Permission check failed for {path}: {e}")
                    success = False

        return ValidationResult(
            success=success,
            level=ValidationLevel.L1_BASIC,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

class ResourceValidator:
    """Validates resource requirements and availability."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def validate_resources(self, platform: BuildPlatform) -> ValidationResult:
        """Validate resource requirements for platform."""
        messages = []
        details = {}

        # Validate memory
        mem_result = self._validate_memory(platform)
        messages.extend(mem_result.messages)
        details["memory"] = mem_result.details

        # Validate CPU
        cpu_result = self._validate_cpu(platform)
        messages.extend(cpu_result.messages)
        details["cpu"] = cpu_result.details

        # Validate disk
        disk_result = self._validate_disk(platform)
        messages.extend(disk_result.messages)
        details["disk"] = disk_result.details

        success = all(r.success for r in [mem_result, cpu_result, disk_result])
        return ValidationResult(
            success=success,
            level=ValidationLevel.L2_RESOURCE,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_memory(self, platform: BuildPlatform) -> ValidationResult:
        """Validate memory requirements."""
        messages = []
        details = {}
        success = True

        required_memory = platform.requirements.get("minimum_memory", 4) * 1024**3  # GB to bytes
        available_memory = psutil.virtual_memory().available

        details["required"] = required_memory
        details["available"] = available_memory

        if available_memory < required_memory:
            messages.append(
                f"Insufficient memory: required {required_memory/1024**3:.1f}GB, "
                f"available {available_memory/1024**3:.1f}GB"
            )
            success = False

        return ValidationResult(
            success=success,
            level=ValidationLevel.L2_RESOURCE,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_cpu(self, platform: BuildPlatform) -> ValidationResult:
        """Validate CPU requirements."""
        messages = []
        details = {}
        success = True

        required_cores = platform.requirements.get("minimum_cores", 2)
        available_cores = psutil.cpu_count()

        details["required_cores"] = required_cores
        details["available_cores"] = available_cores

        if available_cores < required_cores:
            messages.append(
                f"Insufficient CPU cores: required {required_cores}, "
                f"available {available_cores}"
            )
            success = False

        return ValidationResult(
            success=success,
            level=ValidationLevel.L2_RESOURCE,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_disk(self, platform: BuildPlatform) -> ValidationResult:
        """Validate disk space requirements."""
        messages = []
        details = {}
        success = True

        required_space = platform.requirements.get("minimum_disk", 20) * 1024**3  # GB to bytes
        available_space = shutil.disk_usage(self.config["build_path"]).free

        details["required"] = required_space
        details["available"] = available_space

        if available_space < required_space:
            messages.append(
                f"Insufficient disk space: required {required_space/1024**3:.1f}GB, "
                f"available {available_space/1024**3:.1f}GB"
            )
            success = False

        return ValidationResult(
            success=success,
            level=ValidationLevel.L2_RESOURCE,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

class PlatformValidator:
    """Validates platform compatibility and requirements."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def validate_platform(self, platform: BuildPlatform) -> ValidationResult:
        """Validate platform requirements."""
        messages = []
        details = {}

        # Validate architecture compatibility
        arch_result = self._validate_architecture(platform)
        messages.extend(arch_result.messages)
        details["architecture"] = arch_result.details

        # Validate features
        feature_result = self._validate_features(platform)
        messages.extend(feature_result.messages)
        details["features"] = feature_result.details

        # Validate ABI compatibility
        abi_result = self._validate_abi(platform)
        messages.extend(abi_result.messages)
        details["abi"] = abi_result.details

        success = all(r.success for r in [arch_result, feature_result, abi_result])
        return ValidationResult(
            success=success,
            level=ValidationLevel.L1_BASIC,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_architecture(self, platform: BuildPlatform) -> ValidationResult:
        """Validate architecture compatibility."""
        messages = []
        details = {}
        success = True

        host_arch = platform.architecture
        target_arch = self.config["target_arch"]

        details["host"] = host_arch
        details["target"] = target_arch

        # Check supported combinations
        valid_combinations = {
            "x86_64": ["x86_64", "aarch64", "arm"],
            "aarch64": ["aarch64", "arm"]
        }

        if host_arch not in valid_combinations:
            messages.append(f"Unsupported host architecture: {host_arch}")
            success = False
        elif target_arch not in valid_combinations[host_arch]:
            messages.append(
                f"Unsupported target architecture {target_arch} "
                f"for host {host_arch}"
            )
            success = False

        return ValidationResult(
            success=success,
            level=ValidationLevel.L1_BASIC,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_features(self, platform: BuildPlatform) -> ValidationResult:
        """Validate required features."""
        messages = []
        details = {}
        success = True

        required_features = platform.features
        supported_features = self._get_supported_features()

        details["required"] = required_features
        details["supported"] = supported_features

        missing_features = set(required_features) - set(supported_features)
        if missing_features:
            messages.append(f"Missing required features: {missing_features}")
            success = False

        return ValidationResult(
            success=success,
            level=ValidationLevel.L1_BASIC,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _validate_abi(self, platform: BuildPlatform) -> ValidationResult:
        """Validate ABI compatibility."""
        messages = []
        details = {}
        success = True

        required_abi = platform.abi
        supported_abis = self._get_supported_abis()

        details["required"] = required_abi
        details["supported"] = supported_abis

        if required_abi not in supported_abis:
            messages.append(f"Unsupported ABI: {required_abi}")
            success = False

        return ValidationResult(
            success=success,
            level=ValidationLevel.L1_BASIC,
            messages=messages,
            timestamp=datetime.utcnow(),
            details=details
        )

    def _get_supported_features(self) -> List[str]:
        """Get supported CPU features."""
        # Implementation would use platform-specific feature detection
        return ["sse4.2", "avx2", "neon", "crypto"]

    def _get_supported_abis(self) -> List[str]:
        """Get supported ABIs."""
        return ["gnu", "gnueabi", "gnueabihf", "musl"]

class ValidationManager:
    """Core validation system manager."""

    def __init__(self, config: Dict[str, Any], monitoring_manager: MonitoringManager):
        self.config = config
        self.monitoring_manager = monitoring_manager
        self.logger = logging.getLogger(__name__)

        # Initialize validators
        self.toolchain_validator = ToolchainValidator(config)
        self.environment_validator = EnvironmentValidator(config)
        self.resource_validator = ResourceValidator(config)
        self.platform_validator = PlatformValidator(config)

    def validate(self, platform: BuildPlatform, level: ValidationLevel) -> ValidationResult:
        """Run validation at specified level."""
        messages = []
        details = {}
        success = True

        try:
            # Basic platform validation (L1)
            platform_result = self.platform_validator.validate_platform(platform)
            messages.extend(platform_result.messages)
            details["platform"] = platform_result.details
            success = success and platform_result.success

            if level.value >= ValidationLevel.L2_RESOURCE.value:
                # Resource validation (L2)
                resource_result = self.resource_validator.validate_resources(platform)
                messages.extend(resource_result.messages)
                details["resources"] = resource_result.details
                success = success and resource_result.success

            if level.value >= ValidationLevel.L3_TOOLCHAIN.value:
                # Toolchain validation (L3)
                toolchain_result = self.toolchain_validator.validate_toolchain(platform)
                messages.extend(toolchain_result.messages)
                details["toolchain"] = toolchain_result.details
                success = success and toolchain_result.success

            if level.value >= ValidationLevel.L4_FULL.value:
                # Environment validation (L4)
                env_result = self.environment_validator.validate_environment()
                messages.extend(env_result.messages)
                details["environment"] = env_result.details
                success = success and env_result.success

            # Report validation status
            self._report_validation_status(level, success, details)

            return ValidationResult(
                success=success,
                level=level,
                messages=messages,
                timestamp=datetime.utcnow(),
                details=details
            )

        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return ValidationResult(
                success=False,
                level=level,
                messages=[f"Validation error: {e}"],
                timestamp=datetime.utcnow(),
                details={"error": str(e)}
            )

    def _report_validation_status(
        self,
        level: ValidationLevel,
        success: bool,
        details: Dict[str, Any]
    ):
        """Report validation status to monitoring system."""
        try:
            self.monitoring_manager.update_state({
                "metadata": {
                    "validation": {
                        "level": level.name,
                        "success": success,
                        "timestamp": datetime.utcnow().isoformat(),
                        "details": details
                    }
                }
            })
        except Exception as e:
            self.logger.error(f"Failed to report validation status: {e}")

