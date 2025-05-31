"""
Configuration Management Package

This package provides configuration management functionality for the LFS/BLFS
build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from ..utils.config_loader import load_config, save_config, merge_configs


@dataclass
class BuildConfig:
    """Build configuration section."""
    directory: str = "/tmp/lfs/build"
    parallel_jobs: int = 4
    keep_work_files: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "directory": self.directory,
            "parallel_jobs": self.parallel_jobs,
            "keep_work_files": self.keep_work_files
        }


@dataclass
class SourceConfig:
    """Source configuration section."""
    directory: str = "/tmp/lfs/sources"
    verify_checksums: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "directory": self.directory,
            "verify_checksums": self.verify_checksums
        }


@dataclass
class LoggingConfig:
    """Logging configuration section."""
    directory: str = "/tmp/lfs/logs"
    level: str = "INFO"
    rotate: bool = True
    max_size: str = "100M"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "directory": self.directory,
            "level": self.level,
            "rotate": self.rotate,
            "max_size": self.max_size
        }


@dataclass
class Configuration:
    """Complete configuration object."""
    build: BuildConfig
    source: SourceConfig
    logging: LoggingConfig

    def __init__(
        self,
        build: Optional[Union[BuildConfig, Dict]] = None,
        source: Optional[Union[SourceConfig, Dict]] = None,
        logging: Optional[Union[LoggingConfig, Dict]] = None
    ):
        """
        Initialize configuration with flexible input types.

        Args:
            build: Build configuration or dict
            source: Source configuration or dict
            logging: Logging configuration or dict
        """
        self.build = (
            build if isinstance(build, BuildConfig)
            else BuildConfig(**(build or {}))
        )
        self.source = (
            source if isinstance(source, SourceConfig)
            else SourceConfig(**(source or {}))
        )
        self.logging = (
            logging if isinstance(logging, LoggingConfig)
            else LoggingConfig(**(logging or {}))
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Configuration":
        """Create from dictionary."""
        return cls(
            build=data.get("build"),
            source=data.get("source"),
            logging=data.get("logging")
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "build": self.build.to_dict(),
            "source": self.source.to_dict(),
            "logging": self.logging.to_dict()
        }


class ConfigValidationError(Exception):
    """Exception raised for configuration validation errors."""
    pass


class ConfigManager:
    """
    Manages configuration loading, validation, and persistence.

    This class is responsible for:
    - Loading configurations from various sources
    - Validating configuration values
    - Merging multiple configurations
    - Persisting configurations
    """

    def __init__(self):
        """Initialize the ConfigManager."""
        self.default_config = Configuration(
            build=BuildConfig(
                directory="/tmp/lfs/build",
                parallel_jobs=4,
                keep_work_files=False
            ),
            source=SourceConfig(
                directory="/tmp/lfs/sources",
                verify_checksums=True
            ),
            logging=LoggingConfig(
                directory="/tmp/lfs/logs",
                level="INFO",
                rotate=True,
                max_size="100M"
            )
        )

    def load_file(self, config_file: Union[str, Path]) -> Configuration:
        """
        Load configuration from a file.

        Args:
            config_file: Path to configuration file

        Returns:
            Configuration object

        Raises:
            ConfigValidationError: If configuration is invalid
        """
        try:
            config_dict = load_config(config_file)
            self.validate_config(config_dict)
            return Configuration.from_dict(config_dict)
        except (FileNotFoundError, ValueError) as e:
            raise ConfigValidationError(f"Failed to load config: {e}")

    def load_environment(self) -> Configuration:
        """
        Load configuration from environment variables.

        Returns:
            Configuration object
        """
        build_config = BuildConfig(directory="/tmp/lfs/build")
        source_config = SourceConfig(directory="/tmp/lfs/sources")
        logging_config = LoggingConfig(directory="/tmp/lfs/logs")
        
        # Update from environment variables
        if "LFS_BUILD_DIR" in os.environ:
            build_config.directory = os.environ["LFS_BUILD_DIR"]
            
        if "LFS_PARALLEL_JOBS" in os.environ:
            try:
                build_config.parallel_jobs = int(os.environ["LFS_PARALLEL_JOBS"])
            except ValueError:
                logger.warning("Invalid LFS_PARALLEL_JOBS value, using default")
                
        return Configuration(
            build=build_config,
            source=source_config,
            logging=logging_config
        )

    def merge_configs(self, configs: List[Union[Configuration, Dict[str, Any]]]) -> Configuration:
        """
        Merge multiple configurations.

        Args:
            configs: List of Configuration objects or dictionaries

        Returns:
            Merged Configuration object
        """
        # Convert all configs to dicts for merging
        config_dicts = [self.default_config.to_dict()]
        for config in configs:
            if isinstance(config, Configuration):
                config_dicts.append(config.to_dict())
            else:
                config_dicts.append(config.copy())
        
        # Merge dictionaries
        merged = merge_configs(config_dicts)
        
        # Convert back to Configuration object
        return Configuration.from_dict(merged)

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration values.

        Args:
            config: Configuration to validate

        Returns:
            True if configuration is valid

        Raises:
            ConfigValidationError: If configuration is invalid
        """
        try:
            # Validate build section
            if "build" in config:
                build = config["build"]
                if "directory" in build and not os.path.isabs(build["directory"]):
                    raise ConfigValidationError("Build directory must be absolute path")
                if "parallel_jobs" in build and build["parallel_jobs"] < 1:
                    raise ConfigValidationError("parallel_jobs must be >= 1")
                    
            # Validate source section
            if "source" in config:
                source = config["source"]
                if "directory" in source and not os.path.isabs(source["directory"]):
                    raise ConfigValidationError("Source directory must be absolute path")
                    
            # Validate logging section
            if "logging" in config:
                logging = config["logging"]
                if "directory" in logging and not os.path.isabs(logging["directory"]):
                    raise ConfigValidationError("Log directory must be absolute path")
                    
            return True
            
        except Exception as e:
            raise ConfigValidationError(f"Configuration validation failed: {e}")

    def save_config(self, config: Union[Configuration, Dict[str, Any]], config_file: Union[str, Path]) -> None:
        """
        Save configuration to a file.

        Args:
            config: Configuration object or dictionary to save
            config_file: Path to save configuration to

        Raises:
            ConfigValidationError: If configuration is invalid or save fails
        """
        try:
            # Convert input to dict if needed
            config_dict = config.to_dict() if isinstance(config, Configuration) else config.copy()
            self.validate_config(config_dict)
            save_config(config_dict, config_file)
        except Exception as e:
            raise ConfigValidationError(f"Failed to save config: {e}")

    def resolve_config(self, config: Union[Configuration, Dict[str, Any]]) -> Configuration:
        """
        Resolve configuration variables and references.

        Args:
            config: Configuration object or dictionary to resolve

        Returns:
            Resolved Configuration object

        Raises:
            ConfigValidationError: If resolution fails
        """
        try:
            # Convert input to dict if needed
            config_dict = config.to_dict() if isinstance(config, Configuration) else config.copy()
            
            # Deep copy sections to avoid modifying the input
            resolved_dict = {
                section: dict(values) if isinstance(values, dict) else values
                for section, values in config_dict.items()
            }
            
            # Resolve environment variables and references
            for section_name, section in resolved_dict.items():
                if not isinstance(section, dict):
                    continue
                    
                for key, value in section.items():
                    if not isinstance(value, str):
                        continue
                        
                    # Handle environment variable substitution
                    while "${" in value and "}" in value:
                        start = value.find("${")
                        end = value.find("}", start)
                        if end == -1:
                            break
                            
                        var_name = value[start+2:end]
                        if var_name in os.environ:
                            # Replace the variable with its value
                            value = value[:start] + os.environ[var_name] + value[end+1:]
                        elif "." in var_name:
                            # Handle reference to other config value
                            ref_section, ref_key = var_name.split(".")
                            if (
                                ref_section in resolved_dict
                                and isinstance(resolved_dict[ref_section], dict)
                                and ref_key in resolved_dict[ref_section]
                            ):
                                replacement = str(resolved_dict[ref_section][ref_key])
                                value = value[:start] + replacement + value[end+1:]
                            else:
                                break
                        else:
                            break
                            
                    section[key] = value
                    
            return Configuration.from_dict(resolved_dict)
            
        except Exception as e:
            raise ConfigValidationError(f"Failed to resolve config: {e}")

    def validate_schema(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration against schema.

        Args:
            config: Configuration to validate

        Returns:
            True if configuration matches schema

        Raises:
            ConfigValidationError: If schema validation fails
        """
        required_sections = {"build", "source", "logging"}
        
        # Check required sections
        missing = required_sections - set(config.keys())
        if missing:
            raise ConfigValidationError(f"Missing required sections: {missing}")
            
        # Validate types
        if "build" in config:
            build = config["build"]
            if not isinstance(build.get("parallel_jobs", 4), int):
                raise ConfigValidationError("parallel_jobs must be an integer")
                
        return True

