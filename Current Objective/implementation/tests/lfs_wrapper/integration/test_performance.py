"""
Performance Integration Tests

This module tests the performance characteristics of the LFS wrapper
system under various conditions and loads.

Author: WARP System
Created: 2025-05-31
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, List

import pytest
from loguru import logger

from lfs_wrapper.core import LFSWrapper
from lfs_wrapper.utils import measure_time, measure_memory


async def test_build_performance(
    lfs_wrapper: LFSWrapper,
    test_packages: Dict[str, Path]
):
    """
    Test build performance metrics.

    Verifies that the build system maintains acceptable performance
    levels under normal operation.
    """
    with measure_time() as timer:
        result = await lfs_wrapper.build_package("binutils-2.39")
        
    assert result is True
    assert timer.duration < 300  # Build should complete within 5 minutes


async def test_parallel_build_scaling(
    lfs_wrapper: LFSWrapper,
    test_packages: Dict[str, Path]
):
    """
    Test build system scaling with parallel builds.

    Verifies that the system properly scales with parallel build
    operations and manages resources effectively.
    """
    packages = ["binutils-2.39", "gcc-12.2.0", "glibc-2.36"]
    
    # Test different parallel job counts
    results: Dict[int, float] = {}
    for jobs in [1, 2, 4]:
        lfs_wrapper.config.parallel_jobs = jobs
        
        with measure_time() as timer:
            await lfs_wrapper.build_packages(packages)
            results[jobs] = timer.duration
            
    # Verify scaling efficiency
    assert results[2] < results[1] * 0.9  # At least 10% faster with 2 jobs
    assert results[4] < results[2] * 0.9  # At least 10% faster with 4 jobs


async def test_memory_usage(
    lfs_wrapper: LFSWrapper,
    test_packages: Dict[str, Path]
):
    """
    Test memory usage during builds.

    Verifies that the system maintains acceptable memory usage
    patterns during build operations.
    """
    with measure_memory() as memory:
        await lfs_wrapper.build_package("gcc-12.2.0")
        
    # Verify memory usage
    assert memory.peak < 2 * 1024 * 1024 * 1024  # Peak under 2GB
    assert memory.leaked == 0  # No memory leaks


async def test_resource_limits(
    lfs_wrapper: LFSWrapper,
    test_packages: Dict[str, Path]
):
    """
    Test system behavior under resource constraints.

    Verifies that the system handles resource limitations gracefully
    and maintains stability.
    """
    # Configure resource limits
    lfs_wrapper.config.parallel_jobs = 8  # Stress test
    
    # Run multiple builds simultaneously
    packages = ["binutils-2.39", "gcc-12.2.0", "glibc-2.36"] * 3
    
    with measure_memory() as memory:
        results = await asyncio.gather(*[
            lfs_wrapper.build_package(pkg)
            for pkg in packages
        ])
        
    # Verify system stability
    assert all(results)
    assert memory.peak < 4 * 1024 * 1024 * 1024  # Peak under 4GB

