"""
Unit tests for the BLFSAnalyzer class.

Tests BLFS package analysis, dependency resolution, validation,
and configuration management functionality.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import networkx as nx
import pytest
import yaml

from lfs_wrapper.blfs_analyzer import (
    BLFSAnalyzer,
    DependencyInfo,
    DependencyType,
    PackageInfo
)
from lfs_wrapper.exceptions import (
    BLFSAnalysisError,
    BLFSConfigError,
    BLFSValidationError
)


@pytest.fixture
def test_config(tmp_path):
    """Provide test configuration."""
    package_db = tmp_path / "packages.yaml"
    schema_db = tmp_path / "schema.yaml"
    config_map = tmp_path / "config_map.yaml"
    
    # Create test package database
    packages = {
        'packages': {
            'test-pkg': {
                'version': '1.0.0',
                'description': 'Test package',
                'required_dependencies': [
                    'dep1>=1.0.0',
                    'dep2'
                ],
                'optional_dependencies': [
                    'opt1'
                ],
                'build_commands': [
                    './configure',
                    'make'
                ],
                'test_commands': [
                    'make test'
                ],
                'post_install': [
                    'ldconfig'
                ],
                'configuration': {
                    'enable-feature': 'yes'
                }
            }
        }
    }
    
    with open(package_db, 'w') as f:
        yaml.dump(packages, f)
    
    # Create test schema database
    schema = {
        'packages': {
            'test-pkg': {
                'config': {
                    'enable-feature': {
                        'type': 'string',
                        'pattern': '^(yes|no)$'
                    }
                }
            }
        }
    }
    
    with open(schema_db, 'w') as f:
        yaml.dump(schema, f)
    
    # Create test config map
    config_map = {
        'packages': {
            'test-pkg': {
                'config_files': {
                    'enable-feature': '/etc/test-pkg/config'
                }
            }
        }
    }
    
    with open(config_map, 'w') as f:
        yaml.dump(config_map, f)
    
    return {
        'blfs': {
            'package_db': str(package_db),
            'schema_db': str(schema_db),
            'config_map': str(config_map)
        }
    }


@pytest.fixture
def analyzer(test_config):
    """Provide BLFSAnalyzer instance."""
    return BLFSAnalyzer(test_config)


def test_analyze_package(analyzer):
    """Test package analysis."""
    pkg = analyzer.analyze_package('test-pkg')
    
    assert isinstance(pkg, PackageInfo)
    assert pkg.name == 'test-pkg'
    assert pkg.version == '1.0.0'
    assert len(pkg.dependencies) == 3


def test_analyze_missing_package(analyzer):
    """Test analysis of non-existent package."""
    with pytest.raises(BLFSAnalysisError):
        analyzer.analyze_package('nonexistent')


def test_dependency_analysis(analyzer):
    """Test dependency analysis."""
    pkg = analyzer.analyze_package('test-pkg')
    
    # Check required dependencies
    required = [d for d in pkg.dependencies if d.type == DependencyType.REQUIRED]
    assert len(required) == 2
    assert required[0].name == 'dep1'
    assert required[0].version == '>=1.0.0'
    
    # Check optional dependencies
    optional = [d for d in pkg.dependencies if d.type == DependencyType.OPTIONAL]
    assert len(optional) == 1
    assert optional[0].name == 'opt1'


def test_build_order_optimization(analyzer):
    """Test build order optimization."""
    # Create test dependency chain
    analyzer.analyze_package('test-pkg')
    analyzer.dependency_graph.add_edge('test-pkg', 'dep1')
    analyzer.dependency_graph.add_edge('dep1', 'dep2')
    
    order = analyzer.optimize_build_order(['test-pkg'])
    assert order == ['dep2', 'dep1', 'test-pkg']


def test_circular_dependency_detection(analyzer):
    """Test circular dependency detection."""
    # Create circular dependency
    analyzer.dependency_graph.add_edge('pkg1', 'pkg2')
    analyzer.dependency_graph.add_edge('pkg2', 'pkg3')
    analyzer.dependency_graph.add_edge('pkg3', 'pkg1')
    
    with pytest.raises(BLFSAnalysisError):
        analyzer.optimize_build_order(['pkg1'])


@patch('subprocess.run')
def test_package_validation(mock_run, analyzer):
    """Test package validation."""
    # Mock package installation checks
    mock_run.return_value = Mock(
        returncode=0,
        stdout='1.0.0\n'
    )
    
    pkg = analyzer.analyze_package('test-pkg')
    assert analyzer.validate_package('test-pkg')
    assert pkg.validated


@patch('subprocess.run')
def test_validation_failure(mock_run, analyzer):
    """Test validation failure handling."""
    # Mock failed package check
    mock_run.return_value = Mock(returncode=1)
    
    with pytest.raises(BLFSValidationError):
        analyzer.validate_package('test-pkg')


def test_configuration_management(analyzer, tmp_path):
    """Test package configuration management."""
    # Create test config file
    config_file = tmp_path / "config"
    config_file.write_text("enable-feature=no\n")
    
    with patch('pathlib.Path.exists', return_value=True), \
         patch('builtins.open') as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = \
            "enable-feature=no\n"
        
        analyzer.manage_configuration('test-pkg', {
            'enable-feature': 'yes'
        })


def test_invalid_configuration(analyzer):
    """Test invalid configuration handling."""
    with pytest.raises(BLFSConfigError):
        analyzer.manage_configuration('test-pkg', {
            'enable-feature': 'invalid'
        })


def test_update_checking(analyzer):
    """Test package update checking."""
    # Analyze package first
    analyzer.analyze_package('test-pkg')
    
    # Mock available version check
    with patch.object(
        analyzer,
        '_check_available_version',
        return_value='2.0.0'
    ):
        updates = analyzer.check_updates()
        assert 'test-pkg' in updates
        assert updates['test-pkg'] == ('1.0.0', '2.0.0')


def test_dependency_graph_update(analyzer):
    """Test dependency graph updating."""
    pkg = analyzer.analyze_package('test-pkg')
    
    assert 'test-pkg' in analyzer.dependency_graph
    assert analyzer.dependency_graph.has_edge('test-pkg', 'dep1')
    assert analyzer.dependency_graph.has_edge('test-pkg', 'dep2')


def test_config_schema_validation(analyzer):
    """Test configuration schema validation."""
    schema = analyzer._load_config_schema('test-pkg')
    
    assert schema['enable-feature']['type'] == 'string'
    assert schema['enable-feature']['pattern'] == '^(yes|no)$'
    
    # Test valid value
    assert analyzer._validate_config_value('yes', schema['enable-feature'])
    
    # Test invalid value
    assert not analyzer._validate_config_value('maybe', schema['enable-feature'])


@patch('subprocess.run')
def test_dependency_installation_check(mock_run, analyzer):
    """Test dependency installation checking."""
    # Create test dependency
    dep = DependencyInfo(
        name='dep1',
        type=DependencyType.REQUIRED,
        version='>=1.0.0',
        build_order=None,
        description='Test dependency',
        alternatives=[]
    )
    
    # Mock version check
    mock_run.return_value = Mock(
        returncode=0,
        stdout='2.0.0\n'
    )
    
    assert analyzer._check_dependency_installed(dep)


def test_config_file_management(analyzer, tmp_path):
    """Test configuration file management."""
    # Create test config file
    config_file = tmp_path / "test.conf"
    config_file.write_text("key=old_value\n")
    
    # Test config update
    assert analyzer._update_config_file(config_file, 'key', 'new_value')
    assert config_file.read_text() == "key=new_value\n"

