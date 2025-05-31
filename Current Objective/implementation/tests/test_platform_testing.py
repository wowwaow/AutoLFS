"""
Unit tests for the PlatformManager class.

Tests platform detection, compatibility validation, and
configuration management functionality.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import distro
import pytest

from lfs_wrapper.platform_testing import (
    PlatformManager,
    PlatformInfo,
    PlatformType,
    CompatibilityReport
)
from lfs_wrapper.exceptions import PlatformError


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        'platform': {
            'base_config': {
                'build_dir': '/var/tmp/build',
                'log_dir': '/var/log/lfs'
            },
            'platforms': {
                'debian': {
                    'build_dir': '/tmp/build',
                    'package_format': 'deb'
                },
                'rhel': {
                    'build_dir': '/buildroot',
                    'package_format': 'rpm'
                }
            },
            'build_requirements': {
                'base': {
                    'gcc': '>=10.0.0',
                    'make': '>=4.3'
                },
                'debian': {
                    'build-essential': '>=12.0'
                },
                'rhel': {
                    'gcc-c++': '>=10.0.0'
                }
            },
            'dependencies': {
                'debian': [
                    'build-essential',
                    'python3-dev',
                    'libtool'
                ],
                'rhel': [
                    'gcc-c++',
                    'python3-devel',
                    'libtool'
                ]
            },
            'compatibility': {
                'debian': {
                    'gcc': {
                        'min_version': '10.0.0',
                        'requires': ['binutils'],
                        'conflicts': ['gcc-4.8'],
                        'fix': 'apt-get install gcc-10'
                    }
                }
            },
            'recommendations': {
                'debian': [
                    'Consider using ccache for faster rebuilds',
                    'Enable parallel build support'
                ]
            },
            'validation': {
                'debian': {
                    'compiler': 'gcc --version',
                    'linker': 'ld --version'
                }
            },
            'recommended_versions': {
                'gcc': '11.0.0',
                'make': '4.3'
            }
        }
    }


@pytest.fixture
def platform_manager(test_config):
    """Provide PlatformManager instance."""
    return PlatformManager(test_config)


@patch('distro.id')
@patch('platform.machine')
@patch('subprocess.run')
def test_platform_detection(
    mock_run,
    mock_machine,
    mock_distro_id,
    test_config
):
    """Test platform detection."""
    # Mock platform information
    mock_distro_id.return_value = 'debian'
    mock_machine.return_value = 'x86_64'
    mock_run.return_value = Mock(returncode=0, stdout='gcc 10.2.0')
    
    manager = PlatformManager(test_config)
    assert manager.platform_info.platform_type == PlatformType.DEBIAN
    assert manager.platform_info.architecture == 'x86_64'


def test_validate_platform_success(platform_manager):
    """Test successful platform validation."""
    with patch.object(platform_manager, '_check_dependencies', return_value=[]), \
         patch.object(platform_manager, '_check_package_compatibility', return_value=[]):
        report = platform_manager.validate_platform()
        
        assert isinstance(report, CompatibilityReport)
        assert not report.missing_dependencies
        assert not report.incompatible_packages


def test_validate_platform_with_issues(platform_manager):
    """Test platform validation with issues."""
    with patch.object(
        platform_manager,
        '_check_dependencies',
        return_value=['missing-pkg']
    ), patch.object(
        platform_manager,
        '_check_package_compatibility',
        return_value=['incompatible-pkg']
    ):
        report = platform_manager.validate_platform()
        
        assert len(report.missing_dependencies) == 1
        assert len(report.incompatible_packages) == 1
        assert len(report.required_fixes) > 0


def test_get_platform_config(platform_manager):
    """Test platform-specific configuration retrieval."""
    # Set platform type to Debian for test
    platform_manager.platform_info.platform_type = PlatformType.DEBIAN
    
    config = platform_manager.get_platform_config()
    assert config['build_dir'] == '/tmp/build'  # Platform-specific override
    assert 'log_dir' in config  # From base config


@patch('subprocess.run')
def test_install_platform_dependencies(mock_run, platform_manager):
    """Test platform dependency installation."""
    # Mock dependency check and installation
    with patch.object(
        platform_manager,
        '_check_dependencies',
        return_value=['pkg1', 'pkg2']
    ):
        mock_run.return_value = Mock(returncode=0)
        platform_manager.install_platform_dependencies()
        
        assert mock_run.call_count == 2  # Two packages to install


def test_get_build_requirements(platform_manager):
    """Test build requirements retrieval."""
    # Set platform type to Debian for test
    platform_manager.platform_info.platform_type = PlatformType.DEBIAN
    
    requirements = platform_manager.get_build_requirements()
    assert 'gcc' in requirements  # From base requirements
    assert 'build-essential' in requirements  # Platform-specific


@patch('subprocess.run')
def test_check_package_installed(mock_run, platform_manager):
    """Test package installation check."""
    mock_run.return_value = Mock(returncode=0)
    assert platform_manager._check_package_installed('test-pkg')
    
    mock_run.return_value = Mock(returncode=1)
    assert not platform_manager._check_package_installed('missing-pkg')


def test_check_compatibility_rules(platform_manager):
    """Test package compatibility rules checking."""
    rules = {
        'min_version': '10.0.0',
        'requires': ['dep1'],
        'conflicts': ['conflict1']
    }
    
    with patch.object(platform_manager, '_get_package_version', return_value='11.0.0'), \
         patch.object(platform_manager, '_check_package_installed', side_effect=[True, False]):
        assert platform_manager._check_compatibility_rules('test-pkg', rules)


def test_version_meets_constraint(platform_manager):
    """Test version constraint checking."""
    assert platform_manager._version_meets_constraint('11.0.0', '10.0.0', '>=')
    assert not platform_manager._version_meets_constraint('9.0.0', '10.0.0', '>=')
    assert platform_manager._version_meets_constraint('10.0.0', '10.0.0', '==')


@patch('subprocess.run')
def test_run_platform_validation(mock_run, platform_manager):
    """Test platform-specific validation checks."""
    mock_run.return_value = Mock(returncode=0)
    
    # Set platform type to Debian for test
    platform_manager.platform_info.platform_type = PlatformType.DEBIAN
    
    results = platform_manager._run_platform_validation()
    assert 'compiler' in results
    assert 'linker' in results
    assert results['compiler']  # Should be True since returncode is 0


def test_generate_fixes(platform_manager):
    """Test fix generation for issues."""
    missing_deps = ['pkg1', 'pkg2']
    incompatible = ['old-gcc']
    
    # Set platform type to Debian for test
    platform_manager.platform_info.platform_type = PlatformType.DEBIAN
    platform_manager.platform_info.package_manager = 'apt'
    
    fixes = platform_manager._generate_fixes(missing_deps, incompatible)
    assert any('apt-get install' in fix for fix in fixes)
    assert any('gcc' in fix for fix in fixes)


def test_generate_recommendations(platform_manager):
    """Test recommendation generation."""
    # Set platform type to Debian for test
    platform_manager.platform_info.platform_type = PlatformType.DEBIAN
    platform_manager.platform_info.build_tools = {'gcc': '10.0.0'}
    
    recommendations = platform_manager._generate_recommendations()
    assert any('ccache' in rec for rec in recommendations)  # Platform-specific
    assert any('gcc' in rec for rec in recommendations)  # Version-based

