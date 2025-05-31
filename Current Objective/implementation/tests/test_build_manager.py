"""
Unit tests for the BuildManager class.

Tests the build process management functionality including state
management, checkpointing, and error recovery.
"""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from lfs_wrapper.build_manager import (
    BuildManager,
    BuildPhase,
    BuildStatus,
    BuildState
)
from lfs_wrapper.exceptions import (
    BuildError,
    ConfigurationError,
    ExecutionError,
    ValidationError
)


@pytest.fixture
def test_config():
    """Provide a valid test configuration."""
    return {
        'build': {
            'script_timeout': 3600,
            'checkpoint_interval': 300
        },
        'phases': {
            'toolchain': {
                'scripts': ['*.sh'],
                'timeout': 7200
            },
            'temp_system': {
                'scripts': ['*.sh'],
                'timeout': 7200
            },
            'system': {
                'scripts': ['*.sh'],
                'timeout': 14400
            }
        },
        'checkpoints': {
            'enabled': True,
            'directory': 'checkpoints'
        },
        'recovery': {
            'max_retries': 3,
            'retry_delay': 60
        },
        'environment': {
            'LFS': '/mnt/lfs',
            'LFS_TGT': 'x86_64-lfs-linux-gnu',
            'PATH': '/tools/bin:/bin:/usr/bin'
        },
        'paths': {
            'sources': '/mnt/lfs/sources',
            'tools': '/tools',
            'scripts': '/mnt/lfs/scripts',
            'logs': '/mnt/lfs/logs'
        },
        'logging': {
            'directory': 'logs',
            'level': 'INFO'
        }
    }


@pytest.fixture
def build_root(tmp_path):
    """Create a temporary build root directory."""
    build_root = tmp_path / "build"
    build_root.mkdir()
    
    # Create script directories
    scripts_dir = build_root / "scripts"
    scripts_dir.mkdir()
    
    for phase in BuildPhase:
        phase_dir = scripts_dir / phase.name.lower()
        phase_dir.mkdir()
        
        # Create test scripts for each phase
        script = phase_dir / f"test_{phase.name.lower()}.sh"
        script.write_text("""#!/bin/bash
# DESCRIPTION: Test script
echo "Executing test script"
""")
        script.chmod(0o755)
    
    # Create cleanup script
    cleanup_script = scripts_dir / "cleanup.sh"
    cleanup_script.write_text("""#!/bin/bash
echo "Cleaning up"
""")
    cleanup_script.chmod(0o755)
    
    return build_root


def test_build_manager_initialization(build_root, test_config):
    """Test BuildManager initialization with valid inputs."""
    manager = BuildManager(build_root, test_config)
    assert manager.build_root == build_root
    assert manager.config == test_config
    assert manager.state is not None
    assert manager.state.status == BuildStatus.NOT_STARTED


def test_build_manager_invalid_root(tmp_path, test_config):
    """Test BuildManager initialization with invalid root directory."""
    invalid_root = tmp_path / "nonexistent"
    with pytest.raises(ValidationError):
        BuildManager(invalid_root, test_config)


def test_build_manager_invalid_config(build_root):
    """Test BuildManager initialization with invalid config."""
    invalid_config = {}
    with pytest.raises(ConfigurationError):
        BuildManager(build_root, invalid_config)


def test_get_build_scripts(build_root, test_config):
    """Test retrieving build scripts for a phase."""
    manager = BuildManager(build_root, test_config)
    scripts = manager.get_build_scripts(BuildPhase.TOOLCHAIN)
    assert len(scripts) == 1
    assert scripts[0].name == "test_toolchain.sh"


@patch('lfs_wrapper.script_manager.ScriptManager.execute_script')
def test_execute_phase_success(mock_execute, build_root, test_config):
    """Test successful phase execution."""
    mock_execute.return_value = (0, "Success", "")
    
    manager = BuildManager(build_root, test_config)
    result = manager.execute_phase(BuildPhase.TOOLCHAIN)
    
    assert result is True
    assert manager.state.status == BuildStatus.COMPLETED
    assert len(manager.state.completed_scripts) == 1
    assert len(manager.state.failed_scripts) == 0


@patch('lfs_wrapper.script_manager.ScriptManager.execute_script')
def test_execute_phase_failure(mock_execute, build_root, test_config):
    """Test phase execution with script failure."""
    mock_execute.side_effect = ExecutionError("Script failed")
    
    manager = BuildManager(build_root, test_config)
    with pytest.raises(BuildError):
        manager.execute_phase(BuildPhase.TOOLCHAIN)
    
    assert manager.state.status == BuildStatus.FAILED
    assert len(manager.state.failed_scripts) == 1


def test_build_state_persistence(build_root, test_config):
    """Test build state saving and loading."""
    manager = BuildManager(build_root, test_config)
    manager.state.phase = BuildPhase.TOOLCHAIN
    manager.state.status = BuildStatus.IN_PROGRESS
    manager._save_state()
    
    # Create new manager instance to test state loading
    new_manager = BuildManager(build_root, test_config)
    assert new_manager.state.phase == BuildPhase.TOOLCHAIN
    assert new_manager.state.status == BuildStatus.IN_PROGRESS


@patch('lfs_wrapper.script_manager.ScriptManager.execute_script')
def test_error_recovery(mock_execute, build_root, test_config):
    """Test error recovery mechanism."""
    # First call fails, second call succeeds
    mock_execute.side_effect = [
        ExecutionError("Script failed"),
        (0, "Success", "")
    ]
    
    manager = BuildManager(build_root, test_config)
    manager.state.error_count = 1  # Simulate first failure
    
    # This should trigger recovery and succeed
    assert manager._handle_error(ExecutionError("Test error")) is True
    assert manager.state.status == BuildStatus.RECOVERING


def test_get_build_progress(build_root, test_config):
    """Test build progress reporting."""
    manager = BuildManager(build_root, test_config)
    manager.state.current_script = "test_script.sh"
    manager.state.completed_scripts = ["script1.sh", "script2.sh"]
    
    progress = manager.get_build_progress()
    assert progress['phase'] == BuildPhase.TOOLCHAIN.name
    assert progress['status'] == BuildStatus.NOT_STARTED.name
    assert progress['completed_scripts'] == 2
    assert progress['current_script'] == "test_script.sh"


@patch('lfs_wrapper.script_manager.ScriptManager.execute_script')
def test_cleanup(mock_execute, build_root, test_config):
    """Test build cleanup functionality."""
    manager = BuildManager(build_root, test_config)
    manager.cleanup()
    
    mock_execute.assert_called_once()
    assert mock_execute.call_args[0][0] == build_root / "scripts" / "cleanup.sh"


def test_checkpoint_timing(build_root, test_config):
    """Test checkpoint creation timing."""
    manager = BuildManager(build_root, test_config)
    initial_checkpoint = manager.state.last_checkpoint
    
    # Simulate some time passing
    time.sleep(1)
    manager._save_state()
    
    assert manager.state.last_checkpoint > initial_checkpoint

