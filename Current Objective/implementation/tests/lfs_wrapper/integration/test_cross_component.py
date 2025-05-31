"""
Cross-Component Integration Tests

This module tests interactions between different components of the LFS
wrapper system, ensuring proper coordination and data flow.

Author: WARP System
Created: 2025-05-31
"""

from pathlib import Path
from typing import Dict

import pytest
from loguru import logger

from lfs_wrapper.core import LFSWrapper
from lfs_wrapper.build import BuildManager
from lfs_wrapper.config import ConfigManager


async def test_config_build_integration(
    lfs_wrapper: LFSWrapper,
    test_root: Path
):
    """
    Test configuration and build system integration.

    Verifies that configuration changes properly affect build behavior
    and environment setup.
    """
    # Modify configuration
    config_manager = ConfigManager()
    config = config_manager.load_environment()
    config.build.parallel_jobs = 4
    
    # Apply to build system
    build_manager = BuildManager(lfs_wrapper)
    await build_manager.apply_config(config)
    
    # Verify build behavior
    result = await build_manager.build_package("binutils-2.39")
    assert result.parallel_jobs == 4


async def test_logging_metrics_integration(
    lfs_wrapper: LFSWrapper,
    test_packages: Dict[str, Path]
):
    """
    Test logging and metrics system integration.

    Verifies that build operations properly generate logs and metrics,
    and that these can be collected and analyzed.
    """
    # Configure metrics collection
    metrics = lfs_wrapper.metrics_collector
    metrics.start_collection()
    
    # Perform build operation
    await lfs_wrapper.build_package("gcc-12.2.0")
    
    # Verify metrics and logs
    build_metrics = metrics.get_build_metrics()
    assert build_metrics["builds_completed"] > 0
    
    log_file = Path(lfs_wrapper.config.log_dir) / "build.log"
    assert log_file.exists()
    assert log_file.stat().st_size > 0


async def test_dependency_resolution_integration(
    lfs_wrapper: LFSWrapper,
    test_packages: Dict[str, Path]
):
    """
    Test dependency resolution across components.

    Verifies that dependency information is properly shared and
    utilized across different system components.
    """
    # Configure dependency resolver
    resolver = lfs_wrapper.dependency_resolver
    resolver.add_package("glibc-2.36", ["binutils-2.39", "gcc-12.2.0"])
    
    # Attempt package build
    result = await lfs_wrapper.build_package("glibc-2.36")
    assert result is True
    
    # Verify dependency handling
    deps = resolver.get_package_dependencies("glibc-2.36")
    assert len(deps) == 2
    assert "binutils-2.39" in deps
    assert "gcc-12.2.0" in deps


async def test_error_handling_integration(
    lfs_wrapper: LFSWrapper,
    test_root: Path
):
    """
    Test error handling across components.

    Verifies that errors are properly propagated and handled
    across system components.
    """
    # Configure error handling
    error_handler = lfs_wrapper.error_handler
    error_handler.set_error_policy("retry", max_attempts=2)
    
    # Trigger build error
    build_manager = BuildManager(lfs_wrapper)
    await build_manager.build_package("nonexistent-1.0")
    
    # Verify error handling
    error_log = Path(lfs_wrapper.config.log_dir) / "error.log"
    assert error_log.exists()
    
    errors = error_handler.get_error_history()
    assert len(errors) > 0
    assert errors[-1].attempts == 2

