"""
Unit tests for the ValidationManager class.

Tests validation functionality for builds, system integrity,
performance, and checkpoints.
"""

import json
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch

import psutil
import pytest

from lfs_wrapper.build_manager import BuildPhase, BuildState, BuildStatus
from lfs_wrapper.checkpoint_manager import BuildSnapshot, CheckpointType
from lfs_wrapper.validation_manager import (
    ValidationManager,
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
    ValidationType
)
from lfs_wrapper.exceptions import ValidationError


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        'validation': {
            'memory_threshold': 90,
            'disk_threshold': 90,
            'cpu_threshold': 80,
            'io_read_threshold': 10_000_000,  # 10 MB/s
            'io_write_threshold': 5_000_000,  # 5 MB/s
            'critical_files': [
                '/test/critical1',
                '/test/critical2'
            ],
            'system_files': [
                '/test/system1',
                '/test/system2'
            ],
            'required_packages': [
                'pkg1',
                'pkg2'
            ],
            'file_checksums': {
                '/test/system1': 'abc123',
                '/test/system2': 'def456'
            }
        }
    }


@pytest.fixture
def mock_build_manager():
    """Provide mock BuildManager."""
    manager = Mock()
    manager.state = BuildState(
        phase=BuildPhase.TOOLCHAIN,
        status=BuildStatus.IN_PROGRESS,
        current_script="current.sh",
        completed_scripts=["script1.sh", "script2.sh"],
        failed_scripts=[],
        start_time=time.time(),
        last_checkpoint=time.time(),
        error_count=0
    )
    return manager


@pytest.fixture
def mock_blfs_manager():
    """Provide mock BLFSManager."""
    return Mock()


@pytest.fixture
def mock_checkpoint_manager():
    """Provide mock CheckpointManager."""
    return Mock()


@pytest.fixture
def validation_manager(
    test_config,
    mock_build_manager,
    mock_blfs_manager,
    mock_checkpoint_manager
):
    """Provide ValidationManager instance."""
    return ValidationManager(
        mock_build_manager,
        mock_blfs_manager,
        mock_checkpoint_manager,
        test_config
    )


def test_validate_build_success(validation_manager):
    """Test successful build validation."""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        report = validation_manager.validate_build(BuildPhase.TOOLCHAIN)
        assert report.summary[ValidationSeverity.ERROR] == 0
        assert report.summary[ValidationSeverity.CRITICAL] == 0


def test_validate_build_wrong_phase(validation_manager):
    """Test build validation with wrong phase."""
    report = validation_manager.validate_build(BuildPhase.SYSTEM)
    
    assert report.summary[ValidationSeverity.ERROR] == 1
    assert any(
        r.message.startswith("Incorrect build phase")
        for r in report.results
    )


def test_validate_build_missing_files(validation_manager):
    """Test build validation with missing critical files."""
    with patch('pathlib.Path.exists', return_value=False):
        report = validation_manager.validate_build(BuildPhase.TOOLCHAIN)
        
        assert report.summary[ValidationSeverity.CRITICAL] == 2  # Two critical files
        assert all(
            r.check_type == ValidationType.BUILD
            for r in report.results
        )


@patch('psutil.virtual_memory')
@patch('psutil.disk_usage')
def test_validate_system_integrity(mock_disk, mock_memory, validation_manager):
    """Test system integrity validation."""
    # Mock memory usage below threshold
    mock_memory.return_value.percent = 50
    
    # Mock disk usage below threshold
    mock_disk.return_value.percent = 50
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        report = validation_manager.validate_system_integrity()
        assert report.summary[ValidationSeverity.WARNING] == 0
        assert report.summary[ValidationSeverity.ERROR] == 0


@patch('psutil.virtual_memory')
def test_validate_system_high_memory(mock_memory, validation_manager):
    """Test system validation with high memory usage."""
    mock_memory.return_value.percent = 95
    
    report = validation_manager.validate_system_integrity()
    assert report.summary[ValidationSeverity.WARNING] == 1
    assert any(
        r.message == "High memory usage detected"
        for r in report.results
    )


@patch('psutil.cpu_percent')
@patch('psutil.disk_io_counters')
def test_validate_performance(mock_io, mock_cpu, validation_manager):
    """Test performance validation."""
    # Mock CPU usage below threshold
    mock_cpu.return_value = 50
    
    # Mock I/O counters with good performance
    mock_io.return_value = Mock(
        read_bytes=1_000_000_000,  # 1 GB
        write_bytes=500_000_000,   # 500 MB
        read_time=10_000,          # 10 seconds
        write_time=10_000          # 10 seconds
    )
    
    report = validation_manager.validate_performance()
    assert report.summary[ValidationSeverity.WARNING] == 0


@patch('psutil.cpu_percent')
def test_validate_performance_high_cpu(mock_cpu, validation_manager):
    """Test performance validation with high CPU usage."""
    mock_cpu.return_value = 90
    
    report = validation_manager.validate_performance()
    assert report.summary[ValidationSeverity.WARNING] == 1
    assert any(
        r.message == "High CPU usage detected"
        for r in report.results
    )


def test_validate_checkpoint_success(validation_manager, mock_checkpoint_manager):
    """Test successful checkpoint validation."""
    mock_checkpoint_manager.verify_checkpoint.return_value = True
    mock_checkpoint_manager.restore_checkpoint.return_value = Mock(
        environment_vars={},
        file_checksums={},
        installed_packages=[]
    )
    
    with patch.object(
        validation_manager,
        '_verify_restored_state',
        return_value=True
    ):
        report = validation_manager.validate_checkpoint("test_checkpoint")
        assert report.summary[ValidationSeverity.ERROR] == 0
        assert report.summary[ValidationSeverity.CRITICAL] == 0


def test_validate_checkpoint_verification_failed(
    validation_manager,
    mock_checkpoint_manager
):
    """Test checkpoint validation with verification failure."""
    mock_checkpoint_manager.verify_checkpoint.return_value = False
    
    report = validation_manager.validate_checkpoint("test_checkpoint")
    assert report.summary[ValidationSeverity.CRITICAL] == 1
    assert any(
        r.message.startswith("Checkpoint verification failed")
        for r in report.results
    )


def test_validate_checkpoint_restoration_failed(
    validation_manager,
    mock_checkpoint_manager
):
    """Test checkpoint validation with restoration failure."""
    mock_checkpoint_manager.verify_checkpoint.return_value = True
    mock_checkpoint_manager.restore_checkpoint.side_effect = Exception("Restore failed")
    
    report = validation_manager.validate_checkpoint("test_checkpoint")
    assert report.summary[ValidationSeverity.CRITICAL] == 1
    assert any(
        r.message.startswith("Checkpoint restoration failed")
        for r in report.results
    )


def test_verify_script_output(validation_manager):
    """Test script output verification."""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        assert validation_manager._verify_script_output("test_script.sh")
        
        mock_run.return_value.returncode = 1
        assert not validation_manager._verify_script_output("test_script.sh")


def test_verify_file_integrity(validation_manager):
    """Test file integrity verification."""
    test_content = b"test content"
    test_hash = "abc123"
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data=test_content)), \
         patch.dict(validation_manager.config['validation']['file_checksums'],
                   {'/test/file': test_hash}):
        assert validation_manager._verify_file_integrity('/test/file')


def test_verify_package(validation_manager):
    """Test package verification."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        assert validation_manager._verify_package("test-pkg")
        
        mock_run.return_value.returncode = 1
        assert not validation_manager._verify_package("test-pkg")

