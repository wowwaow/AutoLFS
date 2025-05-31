"""
Performance Integration Tests

These tests verify the performance characteristics and resource
management of the LFS wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import asyncio
import pytest
from pathlib import Path

from lfs_wrapper.core import LFSWrapper, WrapperConfig
from lfs_wrapper.errors import ResourceError
from lfs_wrapper.utils import measure_time, measure_memory


@pytest.mark.asyncio
async def test_build_performance(lfs_wrapper: LFSWrapper, test_packages):
    """Test build process performance metrics."""
    # Arrange
    package = "binutils"
    
    # Act
    with measure_time() as build_time:
        with measure_memory() as memory_stats:
            await lfs_wrapper.build_package(package)
    
    # Assert
    metrics = await lfs_wrapper.get_build_metrics(package)
    assert metrics["status"] == "success"
    assert build_time < 60  # Build should complete within 60 seconds
    assert memory_stats["peak_rss"] < 1024 * 1024 * 1024  # Under 1GB


@pytest.mark.asyncio
async def test_parallel_build_scaling(lfs_wrapper: LFSWrapper, test_packages):
    """Test build system scaling with parallel builds."""
    # Arrange
    packages = ["binutils", "gcc", "glibc"]
    parallel_configs = [1, 2, 4]
    timing_results = {}
    
    # Act
    for num_jobs in parallel_configs:
        lfs_wrapper.config.parallel_jobs = num_jobs
        with measure_time() as build_time:
            results = await asyncio.gather(*[
                lfs_wrapper.build_package(pkg)
                for pkg in packages
            ])
        timing_results[num_jobs] = build_time
    
    # Assert
    assert all(timing_results[n] > 0 for n in parallel_configs)
    # Verify some speedup with parallelization
    assert timing_results[4] < timing_results[1]


@pytest.mark.asyncio
async def test_memory_usage(lfs_wrapper: LFSWrapper, test_packages):
    """Test memory usage tracking and limits."""
    # Arrange
    package = "gcc"
    
    # Act
    with measure_memory() as memory_stats:
        await lfs_wrapper.build_package(package)
    
    # Assert
    metrics = await lfs_wrapper.get_build_metrics(package)
    assert metrics["status"] == "success"
    assert memory_stats["peak_rss"] > 0
    assert memory_stats["peak_rss"] < 2 * 1024 * 1024 * 1024  # Under 2GB


@pytest.mark.asyncio
async def test_resource_limits(lfs_wrapper: LFSWrapper, test_packages):
    """Test resource limit enforcement."""
    # Arrange
    package = "gcc"
    original_limit = lfs_wrapper.config.memory_limit
    
    try:
        # Set very low memory limit
        lfs_wrapper.config.memory_limit = 1024 * 1024  # 1MB
        
        # Act & Assert
        with pytest.raises(ResourceError) as exc:
            await lfs_wrapper.build_package(package)
        
        assert "memory limit exceeded" in str(exc.value)
        
        # Verify error handling
        error_history = await lfs_wrapper.get_error_history()
        assert len(error_history) > 0
        assert error_history[-1]["error_type"] == "ResourceError"
        
    finally:
        # Restore original limit
        lfs_wrapper.config.memory_limit = original_limit

