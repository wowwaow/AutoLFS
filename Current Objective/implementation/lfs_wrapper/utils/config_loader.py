"""
Configuration Loading Utilities

This module provides utilities for loading and managing configuration files
for the LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from loguru import logger


def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Dict containing configuration data

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        if not isinstance(config, dict):
            raise ValueError("Invalid configuration format")
            
        return config
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in configuration file: {e}")


def save_config(config: Dict[str, Any], config_path: Union[str, Path]) -> None:
    """
    Save configuration to a YAML file.

    Args:
        config: Configuration data to save
        config_path: Path to save configuration to

    Raises:
        ValueError: If config is invalid
    """
    config_path = Path(config_path)
    
    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    except Exception as e:
        raise ValueError(f"Failed to save configuration: {e}")


def merge_configs(configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge multiple configurations.

    Later configs override values from earlier ones.

    Args:
        configs: List of configuration dictionaries

    Returns:
        Merged configuration dictionary
    """
    merged = {}
    
    for config in configs:
        _deep_merge(merged, config)
        
    return merged


def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> None:
    """
    Recursively merge two dictionaries.

    Args:
        base: Base dictionary to update
        update: Dictionary with updates
    """
    for key, value in update.items():
        if (
            key in base 
            and isinstance(base[key], dict) 
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def normalize_paths(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert relative paths in configuration to absolute paths.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with normalized paths
    """
    normalized = config.copy()
    
    for key, value in normalized.items():
        if isinstance(value, str) and key.endswith('_dir'):
            normalized[key] = str(Path(value).absolute())
        elif isinstance(value, dict):
            normalized[key] = normalize_paths(value)
            
    return normalized

