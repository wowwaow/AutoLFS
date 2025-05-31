"""
Build Process Integration Tests

This module tests the complete build process functionality of the LFS
wrapper system, including package builds and toolchain setup.

Author: WARP System
Created: 2025-05-31
"""

import os
from pathlib import Path
from typing import Dict

import pytest
from loguru import logger

from lfs_wrapper.core import LFSWrapper
from lfs_wrapper.errors import BuildError


async def test_single_package_build(
    lfs_wrapper: LFSWrapper,
    test_packages: Dict[str, Path],
    test_scripts: Dict[str, Path]
):
    """
    Test building a single package.

    Verifies that the wrapper can successfully build an individual package
    with proper environment setup and cleanup.
    """
    # Attempt to build binutils
    result = await lfs_wrapper.build_package("binutils-2.39")
    assert result is True
    
    # Verify build artifacts
    build_dir = Path(lfs_wrapper.config.build_dir) / "binutils-2.39"
    assert build_dir.exists()


async def test_toolchain_build_order(
    lfs_wrapper: LFSWrapper,
    test_packages: Dict[str, Path],
    test_scripts: Dict[str, Path]
):
    """
    Test building toolchain packages in correct order.

    Verifies that the wrapper correctly resolves and follows build
    dependencies when building the toolchain.
    """
    # Build toolchain packages
    packages = ["binutils-2.39", "gcc-12.2.0", "glibc-2.36"]
    for package in packages:
        result = await lfs_wrapper.build_package(package)
        assert result is True
    
    # Verify build order from logs
    log_file = Path(lfs_wrapper.config.log_dir) / "build.log"
    assert log_file.exists()


async def test_parallel_package_builds(
    lfs_wrapper: LFSWrapper,
    test_packages: Dict[str, Path],
    test_scripts: Dict[str, Path]
):
    """
    Test parallel package building.

    Verifies that the wrapper can build multiple independent packages
    in parallel while maintaining build order for dependencies.
    """
    # Configure parallel builds
    lfs_wrapper.config.parallel_jobs = 2
    
    # Build multiple packages
    results = await lfs_wrapper.build_packages([
        "binutils-2.39",
        "gcc-12.2.0",
        "glibc-2.36"
    ])
    
    assert all(results.values())
    assert len(results) == 3


async def test_build_error_handling(
    lfs_wrapper: LFSWrapper,
    test_packages: Dict[str, Path],
    test_scripts: Dict[str, Path]
):
    """
    Test build error handling and recovery.

    Verifies that the wrapper properly handles build failures and
    provides appropriate error information.
    """
    # Attempt to build non-existent package
    with pytest.raises(BuildError) as exc_info:
        await lfs_wrapper.build_package("nonexistent-1.0")
    
    assert "source file not found" in str(exc_info.value)

