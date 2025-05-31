"""
Error Handling Tests for LFS Wrapper System

This module contains tests for the LFS wrapper system's error handling
and recovery capabilities.

Author: WARP System
Created: 2025-05-31
"""

import os
from typing import Dict, Optional

import pytest
from loguru import logger

from lfs_wrapper.core import LFSWrapper, WrapperConfig
from lfs_wrapper.errors import (
    BuildError,
    ConfigError,
    EnvironmentError,
    ValidationError
)


@pytest.fixture
async def error_test_wrapper():
    """Fixture providing a wrapper instance for error testing."""
    config = WrapperConfig(
        build_dir="/tmp/lfs_error_test",
        source_dir="/tmp/lfs_error_sources",
        log_dir="/tmp/lfs_error_logs",
        temp_dir="/tmp/lfs_error_temp"
    )
    wrapper = LFSWrapper(config)
    await wrapper.initialize()
    yield wrapper
    await wrapper.cleanup()


async def test_configuration_errors():
    """
    Test configuration error handling.

    Verifies that the wrapper properly handles and reports
    configuration-related errors.
    """
    # Test invalid directory
    with pytest.raises(ConfigError) as exc_info:
        config = WrapperConfig(build_dir="invalid/relative/path")
        wrapper = LFSWrapper(config)
        await wrapper.initialize()
    assert "absolute path required" in str(exc_info.value)

    # Test invalid permissions
    with pytest.raises(ConfigError) as exc_info:
        config = WrapperConfig(build_dir="/root/no_permission")
        wrapper = LFSWrapper(config)
        await wrapper.initialize()
    assert "permission denied" in str(exc_info.value)


async def test_environment_errors(error_test_wrapper):
    """
    Test environment error handling.

    Verifies that the wrapper properly handles and reports
    environment-related errors.
    """
    # Test missing required tool
    os.environ["PATH"] = "/nonexistent"
    with pytest.raises(EnvironmentError) as exc_info:
        await error_test_wrapper.verify_environment()
    assert "required tool not found" in str(exc_info.value)

    # Test invalid environment variable
    os.environ["LFS"] = "invalid"
    with pytest.raises(EnvironmentError) as exc_info:
        await error_test_wrapper.verify_environment()
    assert "invalid LFS environment variable" in str(exc_info.value)


async def test_build_errors(error_test_wrapper):
    """
    Test build error handling.

    Verifies that the wrapper properly handles and reports
    build process errors.

    depends: test_environment_errors
    """
    # Test missing source file
    with pytest.raises(BuildError) as exc_info:
        await error_test_wrapper.build_package("nonexistent-1.0")
    assert "source file not found" in str(exc_info.value)

    # Test build script error
    with pytest.raises(BuildError) as exc_info:
        await error_test_wrapper.build_package("invalid-package-1.0")
    assert "build script failed" in str(exc_info.value)


async def test_validation_errors(error_test_wrapper):
    """
    Test validation error handling.

    Verifies that the wrapper properly handles and reports
    validation-related errors.
    """
    # Test invalid version format
    with pytest.raises(ValidationError) as exc_info:
        await error_test_wrapper.validate_package_version("invalid")
    assert "invalid version format" in str(exc_info.value)

    # Test checksum mismatch
    with pytest.raises(ValidationError) as exc_info:
        await error_test_wrapper.verify_package_checksum("modified-file")
    assert "checksum mismatch" in str(exc_info.value)


async def test_error_recovery(error_test_wrapper):
    """
    Test error recovery mechanisms.

    Verifies that the wrapper can properly recover from
    various error conditions.

    depends: test_build_errors
    """
    # Test build error recovery
    try:
        await error_test_wrapper.build_package("failing-package-1.0")
    except BuildError as e:
        recovery_result = await error_test_wrapper.attempt_recovery(e)
        assert recovery_result.recovered
        assert recovery_result.actions_taken

    # Test environment error recovery
    try:
        await error_test_wrapper.verify_environment()
    except EnvironmentError as e:
        recovery_result = await error_test_wrapper.attempt_recovery(e)
        assert recovery_result.recovered
        assert recovery_result.actions_taken


async def test_error_reporting(error_test_wrapper):
    """
    Test error reporting functionality.

    Verifies that the wrapper provides detailed and useful
    error reports.
    """
    # Test error details
    try:
        await error_test_wrapper.build_package("error-package-1.0")
    except BuildError as e:
        report = error_test_wrapper.generate_error_report(e)
        assert report.error_type == "BuildError"
        assert report.timestamp is not None
        assert report.context is not None
        assert report.log_file is not None


async def test_cleanup_after_error(error_test_wrapper):
    """
    Test cleanup after error conditions.

    Verifies that the wrapper properly cleans up resources
    after encountering errors.

    depends: test_error_recovery
    """
    temp_files = []
    try:
        await error_test_wrapper.build_package("cleanup-test-1.0")
    except BuildError:
        temp_files = list(Path(error_test_wrapper.config.temp_dir).glob("*"))
    
    # Verify cleanup
    await error_test_wrapper.cleanup()
    remaining_files = list(Path(error_test_wrapper.config.temp_dir).glob("*"))
    assert len(remaining_files) == 0

