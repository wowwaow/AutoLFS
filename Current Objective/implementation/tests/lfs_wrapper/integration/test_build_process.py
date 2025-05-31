"""
Build Process Integration Tests

These tests verify the integration between build process management,
error handling, and resource monitoring components.

Author: WARP System
Created: 2025-05-31
"""

import pytest
from pathlib import Path

from lfs_wrapper.core import LFSWrapper, WrapperConfig
from lfs_wrapper.errors import BuildError, ProcessError


@pytest.mark.asyncio
async def test_single_package_build(lfs_wrapper: LFSWrapper, test_packages):
    """Test single package build with error handling."""
    # Arrange
    package = "binutils"
    
    # Act
    result = await lfs_wrapper.build_package(package)
    
    # Assert
    assert result is True
    metrics = await lfs_wrapper.get_build_metrics(package)
    assert metrics["status"] == "success"
    assert metrics["error_count"] == 0


@pytest.mark.asyncio
async def test_toolchain_build_order(lfs_wrapper: LFSWrapper, test_packages):
    """Test toolchain build order with dependencies."""
    # Arrange
    packages = ["binutils", "gcc", "glibc"]
    
    # Act & Assert
    for package in packages:
        result = await lfs_wrapper.build_package(package)
        assert result is True


@pytest.mark.asyncio
async def test_parallel_package_builds(lfs_wrapper: LFSWrapper, test_packages):
    """Test parallel package builds with resource management."""
    # Arrange
    packages = ["binutils", "gcc", "glibc"]
    
    # Act
    results = await asyncio.gather(*[
        lfs_wrapper.build_package(pkg)
        for pkg in packages
    ])
    
    # Assert
    assert all(results)
    for package in packages:
        metrics = await lfs_wrapper.get_build_metrics(package)
        assert metrics["status"] == "success"


@pytest.mark.asyncio
async def test_build_error_handling(lfs_wrapper: LFSWrapper, test_packages):
    """Test build error handling and recovery."""
    # Arrange
    package = "gcc"
    
    # Simulate build failure
    def fail_build(*args, **kwargs):
        raise BuildError(
            "Build failed",
            package=package,
            exit_code=1
        )
    
    with mock.patch.object(
        lfs_wrapper.process_manager,
        'create_process',
        side_effect=fail_build
    ):
        # Act & Assert
        with pytest.raises(BuildError) as exc:
            await lfs_wrapper.build_package(package)
        
        # Verify error handling
        error_history = await lfs_wrapper.get_error_history()
        assert len(error_history) > 0
        assert error_history[0]["error_type"] == "BuildError"
        assert error_history[0]["recovery_attempted"] is True

