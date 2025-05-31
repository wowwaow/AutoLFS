"""
Build Script Integration Tests for LFS Wrapper System

This module contains integration tests for the LFS wrapper system's
build script handling and execution capabilities.

Author: WARP System
Created: 2025-05-31
"""

import os
from typing import Dict, List

import pytest
from loguru import logger

from lfs_wrapper.core import LFSWrapper, WrapperConfig
from lfs_wrapper.build import BuildManager, BuildResult


@pytest.fixture
async def build_manager():
    """Fixture providing a configured BuildManager instance."""
    config = WrapperConfig(
        build_dir="/tmp/lfs_test_build",
        source_dir="/tmp/lfs_test_sources",
        log_dir="/tmp/lfs_test_logs",
        temp_dir="/tmp/lfs_test_temp"
    )
    wrapper = LFSWrapper(config)
    await wrapper.initialize()
    manager = BuildManager(wrapper)
    yield manager
    await wrapper.cleanup()


async def test_script_execution(build_manager):
    """
    Test basic build script execution.

    Verifies that the wrapper can execute build scripts and capture
    their output correctly.

    depends: test_wrapper_initialization
    """
    result = await build_manager.execute_script(
        "binutils-pass1",
        {"version": "2.39"}
    )
    assert result.success
    assert result.exit_code == 0
    assert os.path.exists(result.log_file)


async def test_dependency_resolution(build_manager):
    """
    Test build dependency resolution.

    Verifies that the wrapper correctly resolves and orders build
    dependencies.

    depends: test_script_execution
    """
    deps = await build_manager.resolve_dependencies("gcc-pass2")
    assert deps is not None
    assert "binutils-pass1" in deps
    assert "linux-headers" in deps


async def test_build_phase_execution(build_manager):
    """
    Test execution of a complete build phase.

    Verifies that the wrapper can execute a sequence of related
    build scripts correctly.

    depends: test_dependency_resolution
    """
    phase_result = await build_manager.execute_phase(
        "toolchain",
        {"gcc_version": "12.2.0", "binutils_version": "2.39"}
    )
    assert phase_result.success
    assert len(phase_result.completed_scripts) > 0
    assert phase_result.failed_scripts == []


async def test_build_state_tracking(build_manager):
    """
    Test build state tracking and persistence.

    Verifies that the wrapper correctly tracks and persists build
    state across executions.

    depends: test_build_phase_execution
    """
    # Execute partial build
    await build_manager.execute_script("binutils-pass1", {"version": "2.39"})
    
    # Save state
    state = await build_manager.save_state()
    assert state is not None
    
    # Create new manager and load state
    new_manager = BuildManager(build_manager.wrapper)
    await new_manager.load_state(state)
    
    # Verify state
    assert new_manager.completed_scripts == build_manager.completed_scripts
    assert new_manager.current_phase == build_manager.current_phase


async def test_error_recovery(build_manager):
    """
    Test build error recovery mechanisms.

    Verifies that the wrapper can handle and recover from build
    failures appropriately.

    depends: test_build_phase_execution
    """
    # Simulate failed build
    result = await build_manager.execute_script(
        "invalid-script",
        {"version": "1.0"}
    )
    assert not result.success
    
    # Verify error handling
    assert result.error_details is not None
    assert result.exit_code != 0
    
    # Test recovery
    recovery_result = await build_manager.recover_failed_build(result)
    assert recovery_result.recovery_attempted
    assert "recovery_actions" in recovery_result.details

