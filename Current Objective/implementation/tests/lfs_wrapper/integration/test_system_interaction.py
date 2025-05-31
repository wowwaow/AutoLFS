"""
System Interaction Integration Tests

This module tests the system-level interactions of the LFS wrapper,
including environment management and resource handling.

Author: WARP System
Created: 2025-05-31
"""

import os
import resource
from pathlib import Path

import pytest
from loguru import logger

from lfs_wrapper.core import LFSWrapper


async def test_environment_setup(lfs_wrapper: LFSWrapper):
    """
    Test build environment setup and validation.

    Verifies that the wrapper correctly sets up and validates the
    build environment variables and paths.
    """
    env = await lfs_wrapper.get_environment()
    
    # Verify essential variables
    assert "LFS" in env
    assert "LFS_TGT" in env
    assert env["LFS"] == lfs_wrapper.config.build_dir
    
    # Verify PATH setup
    assert "PATH" in env
    assert f"{lfs_wrapper.config.build_dir}/tools/bin" in env["PATH"]


async def test_resource_management(lfs_wrapper: LFSWrapper):
    """
    Test system resource management.

    Verifies that the wrapper properly manages system resources
    during build operations.
    """
    # Configure resource limits
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))
    
    # Perform build operation
    result = await lfs_wrapper.build_package("binutils-2.39")
    assert result is True
    
    # Verify resource cleanup
    assert resource.getrlimit(resource.RLIMIT_NOFILE) == (soft, hard)


async def test_filesystem_interaction(
    lfs_wrapper: LFSWrapper,
    test_root: Path
):
    """
    Test filesystem operations and permissions.

    Verifies that the wrapper correctly handles filesystem operations
    and maintains proper permissions.
    """
    # Create test directories
    build_dir = test_root / "build_test"
    build_dir.mkdir()
    
    # Set custom build directory
    lfs_wrapper.config.build_dir = str(build_dir)
    await lfs_wrapper.initialize()
    
    # Verify directory permissions
    assert build_dir.exists()
    assert os.access(build_dir, os.R_OK | os.W_OK | os.X_OK)


async def test_process_management(lfs_wrapper: LFSWrapper):
    """
    Test build process management.

    Verifies that the wrapper properly manages build processes,
    including spawning, monitoring, and cleanup.
    """
    # Start build process
    process = await lfs_wrapper.start_build_process("binutils-2.39")
    assert process is not None
    
    # Monitor process
    status = await lfs_wrapper.monitor_build_process(process)
    assert status.exit_code == 0
    
    # Verify process cleanup
    assert not await lfs_wrapper.is_process_running(process)

