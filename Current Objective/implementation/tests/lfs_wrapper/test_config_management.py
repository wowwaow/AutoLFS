"""
Configuration Management Tests for LFS Wrapper System

This module contains tests for the LFS wrapper system's configuration
management and validation capabilities.

Author: WARP System
Created: 2025-05-31
"""

import os
from pathlib import Path
from typing import Dict

import pytest
import yaml
from loguru import logger

from lfs_wrapper.core import WrapperConfig
from lfs_wrapper.config import ConfigManager, ConfigValidationError


@pytest.fixture
def config_manager():
    """Fixture providing a ConfigManager instance."""
    return ConfigManager()


@pytest.fixture
def sample_config():
    """Fixture providing a sample configuration."""
    return {
        "build": {
            "directory": "/tmp/lfs_build",
            "parallel_jobs": 4,
            "keep_work_files": False
        },
        "source": {
            "directory": "/tmp/lfs_sources",
            "verify_checksums": True
        },
        "logging": {
            "directory": "/tmp/lfs_logs",
            "level": "INFO",
            "rotate": True,
            "max_size": "100M"
        }
    }


def test_config_loading(config_manager, tmp_path):
    """
    Test configuration loading from different sources.

    Verifies that the configuration system can load and merge
    configurations from various sources correctly.
    """
    # Test file loading
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump({"build": {"directory": "/custom/build"}}, f)
    
    config = config_manager.load_file(config_file)
    assert config is not None
    assert config.build.directory == "/custom/build"

    # Test environment loading
    os.environ["LFS_BUILD_DIR"] = "/env/build"
    config = config_manager.load_environment()
    assert config.build.directory == "/env/build"

    # Test merge priority
    combined = config_manager.merge_configs([
        config_manager.load_file(config_file),
        config_manager.load_environment()
    ])
    assert combined.build.directory == "/env/build"


def test_config_validation(config_manager, sample_config):
    """
    Test configuration validation rules.

    Verifies that the configuration system properly validates
    configuration values and constraints.
    """
    # Test valid config
    assert config_manager.validate_config(sample_config)

    # Test invalid directory
    invalid_config = sample_config.copy()
    invalid_config["build"]["directory"] = "relative/path"
    with pytest.raises(ConfigValidationError):
        config_manager.validate_config(invalid_config)

    # Test invalid job count
    invalid_config = sample_config.copy()
    invalid_config["build"]["parallel_jobs"] = -1
    with pytest.raises(ConfigValidationError):
        config_manager.validate_config(invalid_config)


def test_config_resolution(config_manager, sample_config, tmp_path):
    """
    Test configuration value resolution.

    Verifies that the configuration system correctly resolves
    variables and references in configuration values.
    """
    # Create test environment
    os.environ["LFS_ROOT"] = str(tmp_path)
    
    # Test path resolution
    config = sample_config.copy()
    config["build"]["directory"] = "${LFS_ROOT}/build"
    resolved = config_manager.resolve_config(config)
    assert resolved.build.directory == str(tmp_path / "build")

    # Test variable references
    config["source"]["directory"] = "${build.directory}/sources"
    resolved = config_manager.resolve_config(config)
    assert resolved.source.directory == str(tmp_path / "build" / "sources")


def test_config_schema_validation(config_manager):
    """
    Test configuration schema validation.

    Verifies that the configuration system validates against
    the defined schema correctly.
    """
    # Test required fields
    minimal_config = {
        "build": {"directory": "/tmp/build"},
        "source": {"directory": "/tmp/sources"},
        "logging": {"directory": "/tmp/logs"}
    }
    assert config_manager.validate_schema(minimal_config)

    # Test missing required field
    invalid_config = {
        "build": {"directory": "/tmp/build"},
        "source": {"directory": "/tmp/sources"}
    }
    with pytest.raises(ConfigValidationError):
        config_manager.validate_schema(invalid_config)

    # Test invalid field type
    invalid_config = minimal_config.copy()
    invalid_config["build"]["parallel_jobs"] = "not_a_number"
    with pytest.raises(ConfigValidationError):
        config_manager.validate_schema(invalid_config)


def test_config_persistence(config_manager, sample_config, tmp_path):
    """
    Test configuration persistence and reloading.

    Verifies that the configuration system can save and reload
    configurations correctly.
    """
    # Save configuration
    config_file = tmp_path / "saved_config.yaml"
    config_manager.save_config(sample_config, config_file)
    
    # Verify file exists and is valid YAML
    assert config_file.exists()
    with open(config_file) as f:
        loaded_config = yaml.safe_load(f)
    assert loaded_config == sample_config
    
    # Test reload
    reloaded = config_manager.load_file(config_file)
    assert reloaded.build.directory == sample_config["build"]["directory"]
    assert reloaded.source.verify_checksums == sample_config["source"]["verify_checksums"]

