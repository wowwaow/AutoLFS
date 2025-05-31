"""
Configuration Module

This module provides configuration management for the LFS/BLFS
build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class WrapperConfig:
    """Configuration for the LFS wrapper system."""

    # Directory paths
    build_dir: str = "/tmp/lfs/build"
    source_dir: str = "/tmp/lfs/sources"
    log_dir: str = "/tmp/lfs/logs"
    temp_dir: str = "/tmp/lfs/temp"

    # Build options
    parallel_jobs: int = 1
    keep_work_files: bool = False
    verify_checksums: bool = True

    # Resource limits
    memory_limit: Optional[int] = None
    process_limit: Optional[int] = None
    disk_space_limit: Optional[int] = None

    # Environment configuration
    environment_vars: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize configuration."""
        # Ensure paths are absolute
        self.build_dir = str(Path(self.build_dir).absolute())
        self.source_dir = str(Path(self.source_dir).absolute())
        self.log_dir = str(Path(self.log_dir).absolute())
        self.temp_dir = str(Path(self.temp_dir).absolute())

        # Validate numeric values
        if self.parallel_jobs < 1:
            self.parallel_jobs = 1

        # Set default environment variables
        if 'LFS' not in self.environment_vars:
            self.environment_vars['LFS'] = self.build_dir

    def get_environment(self) -> Dict[str, str]:
        """
        Get build environment variables.

        Returns:
            Dict of environment variables
        """
        env = self.environment_vars.copy()

        # Add standard variables if not set
        if 'LFS' not in env:
            env['LFS'] = self.build_dir
        if 'LFS_TGT' not in env:
            env['LFS_TGT'] = "x86_64-lfs-linux-gnu"

        return env

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            bool indicating if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Check paths
        if not Path(self.source_dir).exists():
            raise ValueError(f"Source directory does not exist: {self.source_dir}")

        # Check resource limits
        if self.memory_limit is not None and self.memory_limit < 0:
            raise ValueError("Memory limit cannot be negative")
        if self.process_limit is not None and self.process_limit < 1:
            raise ValueError("Process limit must be positive")
        if self.disk_space_limit is not None and self.disk_space_limit < 0:
            raise ValueError("Disk space limit cannot be negative")

        return True

