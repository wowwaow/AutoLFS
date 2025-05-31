"""
System Interaction Integration Tests

These tests verify the interaction between the LFS wrapper system
and the underlying operating system.

Author: WARP System
Created: 2025-05-31
"""

import os
import pytest
from pathlib import Path

from lfs_wrapper.core import LFSWrapper, WrapperConfig
from lfs_wrapper.errors import EnvironmentError, ProcessError


@pytest.mark.asyncio
async def test_environment_setup(lfs_wrapper: LFSWrapper):
    """Test environment variable management."""
    # Arrange
    test_vars = {
        "LFS": "/mnt/lfs",
        "LFS_TGT": "x86_64-lfs-linux-gnu"
    }
    
    # Act
    for var, value in test_vars.items():
        os.environ[var] = value
    
    # Assert
    env = await lfs_wrapper.get_environment()
    assert all(var in env for var in test_vars)
    assert all(env[var] == value for var, value in test_vars.items())


@pytest.mark.asyncio
async def test_resource_management(lfs_wrapper: LFSWrapper, test_packages):
    """Test system resource management."""
    # Arrange
    package = "gcc"
    process_limit = 10
    
    # Act
    lfs_wrapper.config.process_limit = process_limit
    await lfs_wrapper.build_package(package)
    
    # Assert
    metrics = await lfs_wrapper.get_build_metrics(package)
    assert metrics["status"] == "success"
    
    # Verify process count stayed within limits
    process_metrics = metrics.get("process_metrics", {})
    assert process_metrics.get("max_processes", 0) <= process_limit


@pytest.mark.asyncio
async def test_filesystem_interaction(lfs_wrapper: LFSWrapper, test_packages):
    """Test filesystem operations and permissions."""
    # Arrange
    build_dir = Path(lfs_wrapper.config.build_dir)
    
    # Act
    await lfs_wrapper.build_package("binutils")
    
    # Assert
    assert build_dir.exists()
    assert (build_dir / "binutils").exists()
    assert os.access(str(build_dir), os.W_OK)
    
    # Verify cleanup
    await lfs_wrapper.cleanup()
    assert not (build_dir / "binutils").exists()


@pytest.mark.asyncio
async def test_process_management(lfs_wrapper: LFSWrapper, test_packages):
    """Test process creation and monitoring."""
    # Arrange
    package = "gcc"
    
    # Act
    with mock.patch.object(
        lfs_wrapper.process_manager,
        'monitor_process'
    ) as mock_monitor:
        await lfs_wrapper.build_package(package)
    
    # Assert
    assert mock_monitor.called
    
    # Verify process tracking
    metrics = await lfs_wrapper.get_build_metrics(package)
    process_metrics = metrics.get("process_metrics", {})
    assert "cpu_usage" in process_metrics
    assert "memory_usage" in process_metrics

