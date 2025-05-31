"""
Unit tests for the ScriptManager class.

Tests the functionality of the LFS build script management system.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from lfs_wrapper.script_manager import ScriptManager
from lfs_wrapper.exceptions import (
    ScriptNotFoundError,
    EnvironmentError,
    ValidationError,
    ExecutionError
)


@pytest.fixture
def test_config():
    """Provide a valid test configuration."""
    return {
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
def temp_script_root(tmp_path):
    """Create a temporary script root directory with test scripts."""
    script_root = tmp_path / "scripts"
    script_root.mkdir()
    
    # Create a valid test script
    test_script = script_root / "test_script.sh"
    test_script.write_text("""#!/bin/bash
# DESCRIPTION: Test build script
# DEPENDENCIES: gcc, make
echo "Test script"
""")
    test_script.chmod(0o755)
    
    # Create an invalid script (no execute permission)
    invalid_script = script_root / "invalid_script.sh"
    invalid_script.write_text("#!/bin/bash\necho invalid")
    invalid_script.chmod(0o644)
    
    return script_root

def test_script_manager_initialization(temp_script_root, test_config):
    """Test ScriptManager initialization with valid inputs."""
    manager = ScriptManager(temp_script_root, test_config)
    assert manager.script_root == temp_script_root
    assert manager.config == test_config
    assert isinstance(manager.env, dict)

def test_script_manager_invalid_root(tmp_path, test_config):
    """Test ScriptManager initialization with invalid root directory."""
    invalid_root = tmp_path / "nonexistent"
    with pytest.raises(EnvironmentError):
        ScriptManager(invalid_root, test_config)

def test_script_manager_invalid_config(temp_script_root):
    """Test ScriptManager initialization with invalid config."""
    invalid_config = {}
    with pytest.raises(ValidationError):
        ScriptManager(temp_script_root, invalid_config)

def test_discover_scripts(temp_script_root, test_config):
    """Test script discovery functionality."""
    manager = ScriptManager(temp_script_root, test_config)
    scripts = manager.discover_scripts()
    assert len(scripts) == 1
    assert scripts[0].name == "test_script.sh"

def test_validate_script_success(temp_script_root, test_config):
    """Test script validation with valid script."""
    manager = ScriptManager(temp_script_root, test_config)
    script_path = temp_script_root / "test_script.sh"
    assert manager.validate_script(script_path) is True

def test_validate_script_nonexistent(temp_script_root, test_config):
    """Test script validation with nonexistent script."""
    manager = ScriptManager(temp_script_root, test_config)
    script_path = temp_script_root / "nonexistent.sh"
    with pytest.raises(ScriptNotFoundError):
        manager.validate_script(script_path)

def test_validate_script_not_executable(temp_script_root, test_config):
    """Test script validation with non-executable script."""
    manager = ScriptManager(temp_script_root, test_config)
    script_path = temp_script_root / "invalid_script.sh"
    with pytest.raises(ValidationError):
        manager.validate_script(script_path)

@patch('subprocess.run')
def test_execute_script_success(mock_run, temp_script_root, test_config):
    """Test successful script execution."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "Test output"
    mock_result.stderr = ""
    mock_run.return_value = mock_result
    
    manager = ScriptManager(temp_script_root, test_config)
    script_path = temp_script_root / "test_script.sh"
    
    returncode, stdout, stderr = manager.execute_script(script_path)
    assert returncode == 0
    assert stdout == "Test output"
    assert stderr == ""

@patch('subprocess.run')
def test_execute_script_failure(mock_run, temp_script_root, test_config):
    """Test script execution failure."""
    mock_run.side_effect = subprocess.SubprocessError("Test error")
    
    manager = ScriptManager(temp_script_root, test_config)
    script_path = temp_script_root / "test_script.sh"
    
    with pytest.raises(ExecutionError):
        manager.execute_script(script_path)

def test_get_script_metadata(temp_script_root, test_config):
    """Test script metadata extraction."""
    manager = ScriptManager(temp_script_root, test_config)
    script_path = temp_script_root / "test_script.sh"
    
    metadata = manager.get_script_metadata(script_path)
    assert metadata['name'] == "test_script.sh"
    assert metadata['description'] == "Test build script"
    assert metadata['dependencies'] == ['gcc', 'make']
    assert metadata['executable'] is True

