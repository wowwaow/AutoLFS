"""
Validation framework for LFS and BLFS builds.

Provides comprehensive validation capabilities for build processes,
system integrity, and performance metrics.

Dependencies:
    - psutil>=5.8
"""

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import psutil
import yaml

from .blfs_manager import BLFSManager, PackageStatus
from .build_manager import BuildManager, BuildPhase, BuildStatus
from .checkpoint_manager import CheckpointManager, CheckpointType
from .exceptions import ValidationError


class ValidationType(Enum):
    """Types of validation checks."""
    BUILD = auto()
    SYSTEM = auto()
    PERFORMANCE = auto()
    CHECKPOINT = auto()


class ValidationSeverity(Enum):
    """Validation result severity levels."""
    CRITICAL = auto()
    ERROR = auto()
    WARNING = auto()
    INFO = auto()


@dataclass
class ValidationResult:
    """Results of a validation check."""
    check_type: ValidationType
    severity: ValidationSeverity
    message: str
    details: Dict
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    results: List[ValidationResult]
    summary: Dict[ValidationSeverity, int]
    duration: float
    timestamp: float


class ValidationManager:
    """
    Manages build and system validation.

    Handles validation of build processes, system integrity,
    and performance metrics.

    Attributes:
        build_manager (BuildManager): Build process manager
        blfs_manager (BLFSManager): BLFS package manager
        checkpoint_manager (CheckpointManager): Checkpoint manager
        config (Dict): Validation configuration
        logger (logging.Logger): Logger instance
    """

    def __init__(
        self,
        build_manager: BuildManager,
        blfs_manager: BLFSManager,
        checkpoint_manager: CheckpointManager,
        config: Dict
    ):
        """Initialize validation manager."""
        self.build_manager = build_manager
        self.blfs_manager = blfs_manager
        self.checkpoint_manager = checkpoint_manager
        self.config = config
        self.logger = logging.getLogger(__name__)

    def validate_build(self, phase: BuildPhase) -> ValidationReport:
        """
        Validate build process for a specific phase.

        Args:
            phase: Build phase to validate

        Returns:
            ValidationReport: Validation results

        Raises:
            ValidationError: If validation fails
        """
        start_time = time.time()
        results = []
        
        try:
            # Check build state
            state = self.build_manager.state
            if state.phase != phase:
                results.append(ValidationResult(
                    check_type=ValidationType.BUILD,
                    severity=ValidationSeverity.ERROR,
                    message=f"Incorrect build phase: expected {phase}, got {state.phase}",
                    details={'current_state': state.__dict__}
                ))
            
            # Verify completed scripts
            for script in state.completed_scripts:
                if not self._verify_script_output(script):
                    results.append(ValidationResult(
                        check_type=ValidationType.BUILD,
                        severity=ValidationSeverity.ERROR,
                        message=f"Script validation failed: {script}",
                        details={'script': script}
                    ))
            
            # Check for critical build files
            for path in self.config['validation']['critical_files']:
                if not Path(path).exists():
                    results.append(ValidationResult(
                        check_type=ValidationType.BUILD,
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Critical file missing: {path}",
                        details={'path': path}
                    ))
            
            return self._create_report(results, start_time)
            
        except Exception as e:
            raise ValidationError(f"Build validation failed: {e}")

    def validate_system_integrity(self) -> ValidationReport:
        """
        Validate system integrity.

        Returns:
            ValidationReport: Validation results

        Raises:
            ValidationError: If validation fails
        """
        start_time = time.time()
        results = []
        
        try:
            # Check system resources
            memory = psutil.virtual_memory()
            if memory.percent > self.config['validation']['memory_threshold']:
                results.append(ValidationResult(
                    check_type=ValidationType.SYSTEM,
                    severity=ValidationSeverity.WARNING,
                    message="High memory usage detected",
                    details={'memory_usage': memory._asdict()}
                ))
            
            # Check disk space
            disk = psutil.disk_usage('/')
            if disk.percent > self.config['validation']['disk_threshold']:
                results.append(ValidationResult(
                    check_type=ValidationType.SYSTEM,
                    severity=ValidationSeverity.WARNING,
                    message="Low disk space detected",
                    details={'disk_usage': disk._asdict()}
                ))
            
            # Verify system files
            for path in self.config['validation']['system_files']:
                if not self._verify_file_integrity(path):
                    results.append(ValidationResult(
                        check_type=ValidationType.SYSTEM,
                        severity=ValidationSeverity.ERROR,
                        message=f"System file integrity check failed: {path}",
                        details={'path': path}
                    ))
            
            # Check installed packages
            for pkg in self.config['validation']['required_packages']:
                if not self._verify_package(pkg):
                    results.append(ValidationResult(
                        check_type=ValidationType.SYSTEM,
                        severity=ValidationSeverity.ERROR,
                        message=f"Required package verification failed: {pkg}",
                        details={'package': pkg}
                    ))
            
            return self._create_report(results, start_time)
            
        except Exception as e:
            raise ValidationError(f"System integrity validation failed: {e}")

    def validate_performance(self) -> ValidationReport:
        """
        Validate system performance metrics.

        Returns:
            ValidationReport: Validation results

        Raises:
            ValidationError: If validation fails
        """
        start_time = time.time()
        results = []
        
        try:
            # Check CPU performance
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.config['validation']['cpu_threshold']:
                results.append(ValidationResult(
                    check_type=ValidationType.PERFORMANCE,
                    severity=ValidationSeverity.WARNING,
                    message="High CPU usage detected",
                    details={'cpu_usage': cpu_percent}
                ))
            
            # Check I/O performance
            io_counters = psutil.disk_io_counters()
            if io_counters:
                read_speed = io_counters.read_bytes / io_counters.read_time
                write_speed = io_counters.write_bytes / io_counters.write_time
                
                if read_speed < self.config['validation']['io_read_threshold']:
                    results.append(ValidationResult(
                        check_type=ValidationType.PERFORMANCE,
                        severity=ValidationSeverity.WARNING,
                        message="Slow disk read performance",
                        details={'read_speed': read_speed}
                    ))
                
                if write_speed < self.config['validation']['io_write_threshold']:
                    results.append(ValidationResult(
                        check_type=ValidationType.PERFORMANCE,
                        severity=ValidationSeverity.WARNING,
                        message="Slow disk write performance",
                        details={'write_speed': write_speed}
                    ))
            
            return self._create_report(results, start_time)
            
        except Exception as e:
            raise ValidationError(f"Performance validation failed: {e}")

    def validate_checkpoint(self, checkpoint_id: str) -> ValidationReport:
        """
        Validate a checkpoint's integrity and restorability.

        Args:
            checkpoint_id: ID of checkpoint to validate

        Returns:
            ValidationReport: Validation results

        Raises:
            ValidationError: If validation fails
        """
        start_time = time.time()
        results = []
        
        try:
            # Verify checkpoint exists and is readable
            if not self.checkpoint_manager.verify_checkpoint(checkpoint_id):
                results.append(ValidationResult(
                    check_type=ValidationType.CHECKPOINT,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Checkpoint verification failed: {checkpoint_id}",
                    details={'checkpoint_id': checkpoint_id}
                ))
                return self._create_report(results, start_time)
            
            # Try to restore checkpoint
            try:
                snapshot = self.checkpoint_manager.restore_checkpoint(checkpoint_id)
                
                # Verify restored state
                if not self._verify_restored_state(snapshot):
                    results.append(ValidationResult(
                        check_type=ValidationType.CHECKPOINT,
                        severity=ValidationSeverity.ERROR,
                        message="Restored state validation failed",
                        details={'snapshot': snapshot.__dict__}
                    ))
            except Exception as e:
                results.append(ValidationResult(
                    check_type=ValidationType.CHECKPOINT,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Checkpoint restoration failed: {e}",
                    details={'checkpoint_id': checkpoint_id}
                ))
            
            return self._create_report(results, start_time)
            
        except Exception as e:
            raise ValidationError(f"Checkpoint validation failed: {e}")

    def _verify_script_output(self, script: str) -> bool:
        """Verify script output against expected results."""
        script_path = Path(script)
        if not script_path.exists():
            return False
            
        try:
            result = subprocess.run(
                [str(script_path), '--verify'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def _verify_file_integrity(self, path: str) -> bool:
        """Verify file integrity using checksums."""
        try:
            import hashlib
            path_obj = Path(path)
            if not path_obj.exists():
                return False
                
            with open(path_obj, 'rb') as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            
            expected_hash = self.config['validation']['file_checksums'].get(path)
            return expected_hash == actual_hash
            
        except Exception:
            return False

    def _verify_package(self, package: str) -> bool:
        """Verify package installation and functionality."""
        try:
            result = subprocess.run(
                ['pkg-config', '--exists', package],
                capture_output=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def _verify_restored_state(self, snapshot: 'BuildSnapshot') -> bool:
        """Verify restored build state."""
        try:
            # Verify environment variables
            for key, value in snapshot.environment_vars.items():
                if os.environ.get(key) != value:
                    return False
            
            # Verify file checksums
            for path, checksum in snapshot.file_checksums.items():
                if not self._verify_file_integrity(path):
                    return False
            
            # Verify installed packages
            for pkg in snapshot.installed_packages:
                if not self._verify_package(pkg):
                    return False
            
            return True
            
        except Exception:
            return False

    def _create_report(
        self,
        results: List[ValidationResult],
        start_time: float
    ) -> ValidationReport:
        """Create validation report from results."""
        end_time = time.time()
        
        # Count results by severity
        summary = {
            severity: len([r for r in results if r.severity == severity])
            for severity in ValidationSeverity
        }
        
        return ValidationReport(
            results=results,
            summary=summary,
            duration=end_time - start_time,
            timestamp=end_time
        )

