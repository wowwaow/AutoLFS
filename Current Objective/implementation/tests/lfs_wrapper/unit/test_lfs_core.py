"""Unit tests for the LFS Core functionality."""

import os
import pytest
from lfs_wrapper.lfs_core import LFSCore
from lfs_wrapper.exceptions import LFSConfigError, LFSEnvironmentError

def test_lfs_core_initialization():
    """Test basic initialization of LFSCore."""
    core = LFSCore()
    assert core is not None
    assert hasattr(core, 'initialize')
    assert callable(core.initialize)

def test_lfs_core_environment_validation(monkeypatch):
    """Test environment validation in LFSCore."""
    # Clear required environment variables
    monkeypatch.delenv('LFS', raising=False)
    monkeypatch.delenv('LFS_TGT', raising=False)
    
    core = LFSCore()
    with pytest.raises(LFSEnvironmentError):
        core.validate_environment()

def test_lfs_core_config_validation():
    """Test configuration validation in LFSCore."""
    core = LFSCore()
    with pytest.raises(LFSConfigError):
        core.validate_config()

def test_lfs_core_path_resolution():
    """Test path resolution functionality."""
    core = LFSCore()
    test_path = "/test/path"
    resolved_path = core.resolve_path(test_path)
    assert isinstance(resolved_path, str)
    assert resolved_path.startswith('/')

def test_lfs_core_script_validation():
    """Test script validation functionality."""
    core = LFSCore()
    test_script = "test_script.sh"
    with pytest.raises(LFSConfigError):
        core.validate_script(test_script)

def test_lfs_core_dependency_check():
    """Test dependency checking functionality."""
    core = LFSCore()
    dependencies = ["nonexistent_tool_12345"]
    with pytest.raises(LFSEnvironmentError):
        core.check_dependencies(dependencies)

def test_lfs_core_build_environment():
    """Test build environment setup."""
    core = LFSCore()
    with pytest.raises(LFSEnvironmentError):
        core.setup_build_environment()

def test_lfs_core_cleanup():
    """Test cleanup functionality."""
    core = LFSCore()
    try:
        core.cleanup()
    except Exception as e:
        pytest.fail(f"Cleanup failed: {e}")

def test_lfs_core_logging():
    """Test logging functionality."""
    core = LFSCore()
    test_message = "Test log message"
    try:
        core.log_message(test_message)
    except Exception as e:
        pytest.fail(f"Logging failed: {e}")

def test_lfs_core_error_handling():
    """Test error handling functionality."""
    core = LFSCore()
    with pytest.raises(LFSEnvironmentError):
        core.handle_error("test_error", raise_exception=True)
