"""
Configuration Loading and Management

This module provides utilities for loading and validating configuration files
for the Linux From Scratch (LFS) build system wrapper.

Author: WARP System
Created: 2025-05-31
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from loguru import logger

from ..errors.error_types import ConfigError

# Default configuration values
DEFAULT_CONFIG = {
    'build': {
        'parallel_jobs': 1,
        'keep_work_files': False,
        'verify_checksums': True,
        'fail_fast': False,
        'retry_failed': True,
        'max_retries': 3
    },
    'directories': {
        'build_dir': '/tmp/lfs/build',
        'source_dir': '/tmp/lfs/sources',
        'log_dir': '/tmp/lfs/logs',
        'temp_dir': '/tmp/lfs/temp',
        'tools_dir': '/tmp/lfs/tools'
    },
    'logging': {
        'level': 'INFO',
        'format': '{time} | {level} | {message}',
        'file': None
    },
    'metrics': {
        'enabled': True,
        'collect_interval': 60,
        'retention_days': 30
    },
    'process': {
        'max_concurrent': 4,
        'idle_timeout': 300,
        'kill_timeout': 10,
        'shell': '/bin/bash'
    },
    'resources': {
        'max_memory_mb': 1024,
        'max_cpu_percent': 80,
        'max_disk_gb': 10,
        'min_free_space_gb': 5
    },
    'environment': {
        'LFS': '/mnt/lfs',
        'LFS_TGT': 'x86_64-lfs-linux-gnu',
        'PATH': '/tools/bin:/bin:/usr/bin'
    }
}

# Configuration schema for validation
CONFIG_SCHEMA = {
    'build': {
        'parallel_jobs': int,
        'keep_work_files': bool,
        'verify_checksums': bool,
        'fail_fast': bool,
        'retry_failed': bool,
        'max_retries': int
    },
    'directories': {
        'build_dir': str,
        'source_dir': str,
        'log_dir': str,
        'temp_dir': str,
        'tools_dir': str
    },
    'logging': {
        'level': str,
        'format': str,
        'file': (str, type(None))
    },
    'metrics': {
        'enabled': bool,
        'collect_interval': int,
        'retention_days': int
    },
    'process': {
        'max_concurrent': int,
        'idle_timeout': int,
        'kill_timeout': int,
        'shell': str
    },
    'resources': {
        'max_memory_mb': int,
        'max_cpu_percent': (int, float),
        'max_disk_gb': (int, float),
        'min_free_space_gb': (int, float)
    },
    'environment': {
        'LFS': str,
        'LFS_TGT': str,
        'PATH': str
    }
}


def validate_config(config: Dict[str, Any], schema: Dict[str, Any], path: str = '') -> None:
    """
    Validate configuration against schema.

    Args:
        config: Configuration dictionary to validate
        schema: Schema to validate against
        path: Current path in configuration (for nested validation)

    Raises:
        ConfigError: If validation fails
    """
    for key, expected_type in schema.items():
        current_path = f"{path}.{key}" if path else key

        if key not in config:
            raise ConfigError(
                f"Missing required configuration key: {current_path}",
                field=current_path
            )

        if isinstance(expected_type, dict):
            if not isinstance(config[key], dict):
                raise ConfigError(
                    f"Invalid type for {current_path}. Expected dict, got {type(config[key]).__name__}",
                    field=current_path,
                    expected='dict',
                    actual=type(config[key]).__name__
                )
            validate_config(config[key], expected_type, current_path)
        else:
            expected_types = expected_type if isinstance(expected_type, tuple) else (expected_type,)
            if not isinstance(config[key], expected_types):
                type_names = ' or '.join(t.__name__ for t in expected_types)
                raise ConfigError(
                    f"Invalid type for {current_path}. Expected {type_names}, got {type(config[key]).__name__}",
                    field=current_path,
                    expected=type_names,
                    actual=type(config[key]).__name__
                )


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two configuration dictionaries.

    Args:
        base: Base configuration
        override: Override configuration

    Returns:
        Merged configuration dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if (
            key in result and
            isinstance(result[key], dict) and
            isinstance(value, dict)
        ):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result


def load_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file with validation.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Configuration dictionary

    Raises:
        ConfigError: If configuration is invalid
    """
    config = DEFAULT_CONFIG.copy()

    if config_path:
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                logger.warning(f"Configuration file not found: {config_path}")
                return config

            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)

            if not isinstance(file_config, dict):
                raise ConfigError(
                    "Invalid configuration format. Expected dictionary.",
                    config_file=str(config_path)
                )

            config = merge_configs(config, file_config)

        except yaml.YAMLError as e:
            raise ConfigError(
                f"Failed to parse configuration file: {e}",
                config_file=str(config_path)
            )
        except Exception as e:
            raise ConfigError(
                f"Error loading configuration: {e}",
                config_file=str(config_path)
            )

    # Apply environment variable overrides
    # Apply environment variable overrides using standard LFS naming conventions
    for key in os.environ:
        if key.startswith('LFS_'):
            if key in ['LFS', 'LFS_TGT']:
                # Special handling for core LFS environment variables
                config['environment'][key] = os.environ[key]
            else:
                # Handle other LFS_* configuration variables
                config_key = key[4:].lower()
                if '.' in config_key:
                    section, option = config_key.split('.', 1)
                    if section in config and option in config[section]:
                        value_type = type(config[section][option])
                        try:
                            config[section][option] = value_type(os.environ[key])
                        except ValueError as e:
                            logger.warning(f"Invalid environment variable value: {key}={os.environ[key]}")
                            
        elif key == 'PATH':
            # Special handling for PATH to ensure tools directory is included
            config['environment']['PATH'] = os.environ[key]

    # Validate final configuration
    try:
        validate_config(config, CONFIG_SCHEMA)
    except ConfigError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    return config

