"""
Integration Test Configuration

This module provides fixtures and configuration for integration tests.

Author: WARP System
Created: 2025-05-31
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Generator, Optional

import pytest
from loguru import logger

from lfs_wrapper.core import LFSWrapper, WrapperConfig


@pytest.fixture
def test_root(tmp_path) -> Path:
    """Provide root directory for integration tests."""
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture
def test_config(test_root: Path) -> WrapperConfig:
    """Provide test configuration."""
    return WrapperConfig(
        build_dir=str(test_root / "build"),
        source_dir=str(test_root / "sources"),
        log_dir=str(test_root / "logs"),
        temp_dir=str(test_root / "temp"),
        parallel_jobs=2,
        keep_work_files=True
    )


@pytest.fixture
async def lfs_wrapper(test_config: WrapperConfig) -> LFSWrapper:
    """Provide initialized LFS wrapper instance."""
    wrapper = LFSWrapper(test_config)
    await wrapper.initialize()
    yield wrapper
    await wrapper.cleanup()


@pytest.fixture
def test_packages(test_root: Path) -> Dict[str, Path]:
    """Set up test package files."""
    packages_dir = test_root / "sources" / "packages"
    packages_dir.mkdir(parents=True)
    
    # Create test package files
    packages = {
        "binutils": packages_dir / "binutils-2.39.tar.gz",
        "gcc": packages_dir / "gcc-12.2.0.tar.gz",
        "glibc": packages_dir / "glibc-2.36.tar.gz"
    }
    
    for pkg_file in packages.values():
        pkg_file.parent.mkdir(parents=True, exist_ok=True)
        pkg_file.touch()
        
    return packages


@pytest.fixture
def test_scripts(test_root: Path) -> Dict[str, Path]:
    """Set up test build scripts."""
    scripts_dir = test_root / "sources" / "scripts"
    scripts_dir.mkdir(parents=True)
    
    # Create test build scripts
    scripts = {
        "binutils": scripts_dir / "build-binutils.sh",
        "gcc": scripts_dir / "build-gcc.sh",
        "glibc": scripts_dir / "build-glibc.sh"
    }
    
    for script_name, script_path in scripts.items():
        with open(script_path, 'w') as f:
            f.write(f"""#!/bin/bash
echo "Building {script_name}..."
exit 0
""")
        script_path.chmod(0o755)
        
    return scripts

