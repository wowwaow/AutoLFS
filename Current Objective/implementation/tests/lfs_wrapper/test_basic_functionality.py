"""
Basic Functionality Tests for LFS Wrapper System

This module contains basic functionality tests for the LFS wrapper system,
verifying core operations and basic integrations.

Author: WARP System
Created: 2025-05-31
"""

import os
from typing import Dict, Optional

import pytest
from loguru import logger

from lfs_wrapper.core import WrapperConfig, LFSWrapper
from lfs_wrapper.utils import config_loader


@pytest.fixture
async def lfs_wrapper():
    """Fixture providing a configured LFS wrapper instance."""
    config = WrapperConfig(
        build_dir="/tmp/lfs_test_build",
        source_dir="/tmp/lfs_test_sources",
        log_dir="/tmp/lfs_test_logs",
        temp_dir="/tmp/lfs_test_temp"
    )
    wrapper = LFSWrapper(config)
    await wrapper.initialize()
    yield wrapper
    await wrapper.cleanup()


async def test_wrapper_initialization(lfs_wrapper):
    """
    Test basic wrapper initialization.

    Verifies that the wrapper initializes correctly with proper directory
    structure and configuration.
    """
    assert lfs_wrapper.is_initialized
    assert os.path.exists(lfs_wrapper.config.build_dir)
    assert os.path.exists(lfs_wrapper.config.source_dir)
    assert os.path.exists(lfs_wrapper.config.log_dir)


async def test_wrapper_configuration():
    """
    Test wrapper configuration loading and validation.

    Verifies that the wrapper properly loads and validates configuration
    from different sources.
    """
    # Test default configuration
    wrapper = LFSWrapper()
    assert wrapper.config is not None
    assert wrapper.config.build_dir is not None

    # Test custom configuration
    custom_config = WrapperConfig(
        build_dir="/custom/build",
        source_dir="/custom/sources",
        log_dir="/custom/logs",
        temp_dir="/custom/temp"
    )
    wrapper = LFSWrapper(custom_config)
    assert wrapper.config.build_dir == "/custom/build"
    assert wrapper.config.source_dir == "/custom/sources"


async def test_environment_setup(lfs_wrapper):
    """
    Test environment setup and validation.

    Verifies that the wrapper correctly sets up and validates the
    build environment.
    """
    env_vars = await lfs_wrapper.get_environment()
    assert "LFS" in env_vars
    assert "LFS_TGT" in env_vars
    assert env_vars["LFS"] == lfs_wrapper.config.build_dir


async def test_script_discovery(lfs_wrapper):
    """
    Test build script discovery functionality.

    Verifies that the wrapper can discover and validate build scripts
    in the source directory.
    """
    scripts = await lfs_wrapper.discover_scripts()
    assert scripts is not None
    assert isinstance(scripts, dict)
    assert len(scripts) > 0


def test_version_validation(lfs_wrapper):
    """
    Test version string validation.

    Verifies that the wrapper correctly validates version strings
    for tools and packages.
    """
    assert lfs_wrapper.validate_version("1.2.3")
    assert lfs_wrapper.validate_version("11.2")
    assert not lfs_wrapper.validate_version("invalid")
    assert not lfs_wrapper.validate_version("1.2.3.4.5")

