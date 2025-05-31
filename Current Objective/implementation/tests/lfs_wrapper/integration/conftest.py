"""
Integration Test Configuration

This module provides fixtures and configuration for integration tests.

Author: WARP System
Created: 2025-05-31
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Generator

import pytest
from pytest_mock import MockFixture

from lfs_wrapper.core import LFSWrapper, WrapperConfig


@pytest.fixture
def test_root(tmp_path: Path) -> Path:
    """Provide temporary test directory."""
    yield tmp_path
    if tmp_path.exists():
        shutil.rmtree(tmp_path)


@pytest.fixture
def test_config(test_root: Path) -> WrapperConfig:
    """Provide test configuration."""
    return WrapperConfig(
        build_dir=str(test_root / "build"),
        source_dir=str(test_root / "sources"),
        log_dir=str(test_root / "logs"),
        temp_dir=str(test_root / "temp"),
        parallel_jobs=2,
        keep_work_files=True,
        verify_checksums=True
    )


@pytest.fixture
async def lfs_wrapper(test_config: WrapperConfig) -> Generator[LFSWrapper, None, None]:
    """Provide initialized LFS wrapper instance."""
    wrapper = LFSWrapper(test_config)
    await wrapper.initialize()
    yield wrapper
    await wrapper.cleanup()


@pytest.fixture
def test_packages(test_root: Path) -> Dict[str, Path]:
    """Set up test package files."""
    packages_dir = test_root / "sources"
    packages_dir.mkdir(parents=True, exist_ok=True)
    
    packages = {
        "binutils": packages_dir / "binutils-2.39.tar.gz",
        "gcc": packages_dir / "gcc-12.2.0.tar.gz",
        "glibc": packages_dir / "glibc-2.36.tar.gz"
    }
    
    for pkg_path in packages.values():
        pkg_path.parent.mkdir(parents=True, exist_ok=True)
        pkg_path.touch()
    
    return packages


@pytest.fixture
def test_scripts(test_root: Path) -> Dict[str, Path]:
    """Set up test build scripts."""
    scripts_dir = test_root / "sources" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    
    scripts = {
        "binutils": scripts_dir / "build-binutils.sh",
        "gcc": scripts_dir / "build-gcc.sh",
        "glibc": scripts_dir / "build-glibc.sh"
    }
    
    for script_name, script_path in scripts.items():
        script_path.write_text(f"""#!/bin/bash
echo "Building {script_name}..."
exit 0
""")
        script_path.chmod(0o755)
    
    return scripts

