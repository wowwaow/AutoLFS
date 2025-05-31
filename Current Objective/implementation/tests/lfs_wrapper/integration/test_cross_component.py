"""
Cross-Component Integration Tests

These tests verify the integration between different components
of the LFS wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import pytest
from pathlib import Path

from lfs_wrapper.core import LFSWrapper, WrapperConfig
from lfs_wrapper.errors import (
    BuildError,
    ConfigError,
    EnvironmentError
)


@pytest.mark.asyncio
async def test_config_build_integration(lfs_wrapper: LFSWrapper, test_config):
    """Test configuration and build system integration."""
    # Arrange
    custom_config = WrapperConfig(
        build_dir=test_config.build_dir,
        source_dir=test_config.source_dir,
        parallel_jobs=4
    )
    
    # Act
    wrapper = LFSWrapper(custom_config)
    await wrapper.initialize()
    
    # Assert
    assert wrapper.config.parallel_jobs == 4
    assert wrapper.is_initialized


@pytest.mark.asyncio
async def test_logging_metrics_integration(lfs_wrapper: LFSWrapper, test_packages):
    """Test logging system and metrics collection integration."""
    # Arrange
    package = "binutils"
    
    # Act
    await lfs_wrapper.build_package(package)
    
    # Assert
    metrics = await lfs_wrapper.get_build_metrics(package)
    assert metrics is not None
    assert "start_time" in metrics
    assert "end_time" in metrics
    assert metrics["package"] == package


@pytest.mark.asyncio
async def test_dependency_resolution_integration(lfs_wrapper: LFSWrapper, test_packages):
    """Test dependency resolution and build process integration."""
    # Arrange
    packages = {
        "gcc": ["binutils"],
        "glibc": ["gcc"]
    }
    
    # Act & Assert
    for package, deps in packages.items():
        # Verify dependencies are built first
        for dep in deps:
            metrics = await lfs_wrapper.get_build_metrics(dep)
            assert metrics is not None
            assert metrics["status"] == "success"
        
        # Build package
        result = await lfs_wrapper.build_package(package)
        assert result is True


@pytest.mark.asyncio
async def test_error_handling_integration(lfs_wrapper: LFSWrapper, test_packages):
    """Test error handling integration across components."""
    # Arrange
    package = "gcc"
    
    # Simulate cascading errors
    def trigger_errors(*args, **kwargs):
        raise BuildError(
            "Build failed",
            package=package,
            exit_code=1
        )
    
    with mock.patch.object(
        lfs_wrapper.process_manager,
        'create_process',
        side_effect=trigger_errors
    ):
        # Act & Assert
        with pytest.raises(BuildError):
            await lfs_wrapper.build_package(package)
        
        # Verify error propagation
        error_history = await lfs_wrapper.get_error_history()
        assert len(error_history) > 0
        
        # Verify metrics captured error
        metrics = await lfs_wrapper.get_build_metrics(package)
        assert metrics["status"] == "failed"
        assert metrics["error_count"] > 0

