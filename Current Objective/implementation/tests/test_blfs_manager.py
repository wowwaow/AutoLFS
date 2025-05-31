"""
Unit tests for the BLFSManager class.

Tests BLFS package management, configuration, building,
and maintenance functionality.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from lfs_wrapper.blfs_manager import (
    BLFSManager,
    BLFSPackage,
    PackageStatus
)
from lfs_wrapper.build_scheduler import BuildPriority
from lfs_wrapper.exceptions import (
    BLFSError,
    ConfigurationError,
    ValidationError,
    VersionError
)


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        'blfs': {
            'package_db': 'packages.yaml',
            'build_dir': '/var/tmp/blfs/build',
            'install_dir': '/usr',
            'source_cache': '/var/cache/blfs',
            'config_dir': '/etc/blfs/config'
        }
    }


@pytest.fixture
def test_package_db(tmp_path):
    """Create test package database."""
    db_file = tmp_path / "packages.yaml"
    packages = {
        'packages': [
            {
                'name': 'test-pkg',
                'version': '1.0.0',
                'source_url': 'http://example.com/test-pkg-1.0.0.tar.gz',
                'dependencies': ['dep1', 'dep2'],
                'optional_dependencies': ['opt1'],
                'configure_options': ['--enable-feature'],
                'build_options': {'jobs': '4'},
                'install_options': {'prefix': '/usr'},
                'post_install': ['ldconfig'],
                'tests': ['make test']
            }
        ]
    }
    
    with open(db_file, 'w') as f:
        yaml.dump(packages, f)
    
    return db_file


@pytest.fixture
def mock_build_manager():
    """Provide mock BuildManager."""
    return Mock()


@pytest.fixture
def mock_dependency_resolver():
    """Provide mock DependencyResolver."""
    resolver = Mock()
    resolver.resolve_dependencies.return_value = ['dep1', 'dep2', 'test-pkg']
    return resolver


@pytest.fixture
def mock_build_scheduler():
    """Provide mock BuildScheduler."""
    return Mock()


@pytest.fixture
def blfs_manager(
    test_config,
    test_package_db,
    mock_build_manager,
    mock_dependency_resolver,
    mock_build_scheduler
):
    """Provide BLFSManager instance."""
    config = test_config.copy()
    config['blfs']['package_db'] = str(test_package_db)
    return BLFSManager(
        mock_build_manager,
        mock_dependency_resolver,
        mock_build_scheduler,
        config
    )


def test_load_package_database(blfs_manager):
    """Test package database loading."""
    assert 'test-pkg' in blfs_manager.packages
    pkg = blfs_manager.packages['test-pkg']
    assert pkg.version == '1.0.0'
    assert len(pkg.dependencies) == 2
    assert len(pkg.optional_dependencies) == 1


def test_invalid_package_db(test_config, mock_build_manager,
                          mock_dependency_resolver, mock_build_scheduler):
    """Test handling of invalid package database."""
    config = test_config.copy()
    config['blfs']['package_db'] = 'nonexistent.yaml'
    
    with pytest.raises(ConfigurationError):
        BLFSManager(
            mock_build_manager,
            mock_dependency_resolver,
            mock_build_scheduler,
            config
        )


def test_select_package(blfs_manager):
    """Test package selection."""
    pkg = blfs_manager.select_package('test-pkg')
    assert isinstance(pkg, BLFSPackage)
    assert pkg.name == 'test-pkg'
    assert pkg.version == '1.0.0'


def test_select_package_invalid(blfs_manager):
    """Test selection of non-existent package."""
    with pytest.raises(BLFSError):
        blfs_manager.select_package('nonexistent')


def test_select_package_version_mismatch(blfs_manager):
    """Test package selection with version mismatch."""
    with pytest.raises(VersionError):
        blfs_manager.select_package('test-pkg', version='2.0.0')


def test_resolve_dependencies(blfs_manager):
    """Test dependency resolution."""
    deps = blfs_manager.resolve_dependencies('test-pkg')
    assert len(deps) == 3  # dep1, dep2, test-pkg
    assert 'dep1' in deps
    assert 'dep2' in deps


def test_resolve_dependencies_with_optional(blfs_manager):
    """Test dependency resolution including optional deps."""
    deps = blfs_manager.resolve_dependencies('test-pkg', include_optional=True)
    assert 'opt1' in blfs_manager.packages['test-pkg'].optional_dependencies


def test_configure_package(blfs_manager):
    """Test package configuration."""
    options = {'with-feature': 'yes'}
    blfs_manager.configure_package('test-pkg', options)
    
    pkg = blfs_manager.packages['test-pkg']
    assert '--with-feature=yes' in pkg.configure_options


@patch('subprocess.run')
def test_build_package(mock_run, blfs_manager):
    """Test package building."""
    blfs_manager.build_package('test-pkg')
    
    # Verify build scheduler was called for deps and package
    assert blfs_manager.build_scheduler.schedule_build.call_count == 3


@patch('subprocess.run')
def test_test_package_success(mock_run, blfs_manager):
    """Test successful package testing."""
    mock_run.return_value.returncode = 0
    assert blfs_manager.test_package('test-pkg') is True


@patch('subprocess.run')
def test_test_package_failure(mock_run, blfs_manager):
    """Test failed package testing."""
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = "Test failed"
    assert blfs_manager.test_package('test-pkg') is False


def test_get_package_status(blfs_manager):
    """Test package status checking."""
    status = blfs_manager.get_package_status('test-pkg')
    assert status == PackageStatus.NOT_INSTALLED


@patch('subprocess.run')
def test_update_package(mock_run, blfs_manager):
    """Test package update."""
    # Mock current version check
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "0.9.0\n"
    
    blfs_manager.update_package('test-pkg')
    
    # Should schedule update with HIGH priority
    blfs_manager.build_scheduler.schedule_build.assert_called_with(
        'test-pkg',
        BuildPriority.HIGH
    )


@patch('subprocess.run')
def test_perform_maintenance(mock_run, blfs_manager):
    """Test system maintenance."""
    # Mock version checks
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "0.9.0\n"
    
    report = blfs_manager.perform_maintenance()
    
    assert 'needs_update' in report
    assert 'broken_packages' in report
    assert 'missing_dependencies' in report
    assert 'test-pkg' in report['needs_update']


def test_save_package_config(tmp_path, blfs_manager):
    """Test package configuration saving."""
    # Set up test config directory
    config_dir = tmp_path / "config"
    blfs_manager.config['blfs']['config_dir'] = str(config_dir)
    
    pkg = blfs_manager.packages['test-pkg']
    blfs_manager._save_package_config(pkg)
    
    config_file = config_dir / "test-pkg.yaml"
    assert config_file.exists()
    
    with open(config_file) as f:
        config = yaml.safe_load(f)
        assert config['name'] == 'test-pkg'
        assert config['version'] == '1.0.0'

