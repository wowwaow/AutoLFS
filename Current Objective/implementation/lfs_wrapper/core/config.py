"""
LFS Wrapper Configuration Module

This module provides configuration management for the LFS/BLFS build scripts
wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import yaml


@dataclass
class WrapperConfig:
    """
    Configuration for the LFS wrapper system.

    Attributes:
        build_dir: Directory for build operations
        source_dir: Directory for source files
        log_dir: Directory for log files
        temp_dir: Directory for temporary files
        parallel_jobs: Number of parallel build jobs
        keep_work_files: Whether to keep work files after build
        verify_checksums: Whether to verify package checksums
        environment_vars: Additional environment variables
    """
    build_dir: str
    source_dir: str
    log_dir: str
    temp_dir: str
    parallel_jobs: int = 4
    keep_work_files: bool = False
    verify_checksums: bool = True
    environment_vars: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize configuration after initialization."""
        # Convert paths to absolute paths
        self.build_dir = str(Path(self.build_dir).absolute())
        self.source_dir = str(Path(self.source_dir).absolute())
        self.log_dir = str(Path(self.log_dir).absolute())
        self.temp_dir = str(Path(self.temp_dir).absolute())

        # Validate configuration
        self.validate()

    def validate(self) -> None:
        """
        Validate the configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate paths are absolute
        for path in [self.build_dir, self.source_dir, self.log_dir, self.temp_dir]:
            if not os.path.isabs(path):
                raise ValueError(f"Path must be absolute: {path}")

        # Validate parallel jobs
        if self.parallel_jobs < 1:
            raise ValueError("parallel_jobs must be >= 1")

    @classmethod
    def from_file(cls, config_file: str) -> "WrapperConfig":
        """
        Create configuration from a YAML file.

        Args:
            config_file: Path to configuration file

        Returns:
            WrapperConfig instance
        """
        with open(config_file) as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)

    def to_dict(self) -> Dict:
        """
        Convert configuration to dictionary.

        Returns:
            Dict representation of configuration
        """
        return {
            "build_dir": self.build_dir,
            "source_dir": self.source_dir,
            "log_dir": self.log_dir,
            "temp_dir": self.temp_dir,
            "parallel_jobs": self.parallel_jobs,
            "keep_work_files": self.keep_work_files,
            "verify_checksums": self.verify_checksums,
            "environment_vars": self.environment_vars.copy()
        }

    def save(self, config_file: str) -> None:
        """
        Save configuration to a YAML file.

        Args:
            config_file: Path to save configuration to
        """
        with open(config_file, 'w') as f:
            yaml.dump(self.to_dict(), f)

    def get_environment(self) -> Dict[str, str]:
        """
        Get environment variables for build process.

        Returns:
            Dict of environment variables
        """
        env = self.environment_vars.copy()
        env.update({
            "LFS": self.build_dir,
            "LFS_TGT": "x86_64-lfs-linux-gnu",
            "LFS_TOOLS": os.path.join(self.build_dir, "tools"),
            "LFS_SOURCES": self.source_dir,
            "LFS_LOG": self.log_dir
        })
        return env

