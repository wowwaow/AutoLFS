"""
Unit tests for the command line interface.

Tests the CLI functionality including command execution,
error handling, and output formatting.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import click
import pytest
import yaml

from lfs_wrapper.cli import cli
from lfs_wrapper.build_manager import BuildPhase, BuildStatus


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration file."""
    config = {
        'build': {
            'script_timeout': 3600,
            'checkpoint_interval': 300
        },
        'phases': {
            'toolchain': {
                'scripts': ['*.sh'],
                'timeout': 7200
            },
            'temp_system': {
                'scripts': ['*.sh'],
                'timeout': 7200
            },
            'system': {
                'scripts': ['*.sh'],
                'timeout': 14400
            }
        },
        'checkpoints': {
            'enabled': True,
            'directory': 'checkpoints'
        },
        'recovery': {
            'max_retries': 3,
            'retry_delay': 60
        },
        'environment': {
            'LFS': '/mnt/lfs',
            'LFS_TGT': 'x86_64-lfs-linux-gnu',
            'PATH': '/tools/bin:/bin:/usr/bin'
        },
        'paths': {
            'sources': '/mnt/lfs/sources',
            'tools': '/tools',
            'scripts': '/mnt/lfs/scripts',
            'logs': '/mnt/lfs/logs'
        },
        'logging': {
            'directory': 'logs',
            'level': 'INFO'
        }
    }
    
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    
    return config_file


@pytest.fixture
def test_build_root(tmp_path):
    """Create a test build root directory."""
    build_root = tmp_path / "build"
    build_root.mkdir()
    
    # Create script directories
    scripts_dir = build_root / "scripts"
    scripts_dir.mkdir()
    
    for phase in BuildPhase:
        phase_dir = scripts_dir / phase.name.lower()
        phase_dir.mkdir()
        
        # Create test scripts
        script = phase_dir / f"test_{phase.name.lower()}.sh"
        script.write_text("#!/bin/bash\necho test")
        script.chmod(0o755)
    
    return build_root


def test_cli_setup(test_config, test_build_root):
    """Test setup command execution."""
    runner = click.testing.CliRunner()
    with patch('lfs_wrapper.build_manager.BuildManager.execute_phase') as mock_execute:
        result = runner.invoke(
            cli,
            ['--config', str(test_config), 'setup', str(test_build_root)]
        )
        
        assert result.exit_code == 0
        assert "Setting up build environment..." in result.output
        mock_execute.assert_called_once_with(BuildPhase.TOOLCHAIN)


def test_cli_build_specific_phase(test_config, test_build_root):
    """Test build command with specific phase."""
    runner = click.testing.CliRunner()
    with patch('lfs_wrapper.build_manager.BuildManager.execute_phase') as mock_execute:
        result = runner.invoke(
            cli,
            [
                '--config', str(test_config),
                'build',
                '--phase', 'toolchain',
                str(test_build_root)
            ]
        )
        
        assert result.exit_code == 0
        assert "Executing build phase: toolchain" in result.output
        mock_execute.assert_called_once_with(BuildPhase.TOOLCHAIN)


def test_cli_build_all_phases(test_config, test_build_root):
    """Test build command execution for all phases."""
    runner = click.testing.CliRunner()
    with patch('lfs_wrapper.build_manager.BuildManager.execute_phase') as mock_execute:
        result = runner.invoke(
            cli,
            ['--config', str(test_config), 'build', str(test_build_root)]
        )
        
        assert result.exit_code == 0
        assert "Build process completed successfully" in result.output
        # Should be called for all phases except CONFIGURATION
        assert mock_execute.call_count == len(BuildPhase) - 1


def test_cli_configure(test_config, test_build_root):
    """Test configure command execution."""
    runner = click.testing.CliRunner()
    with patch('lfs_wrapper.build_manager.BuildManager.execute_phase') as mock_execute:
        result = runner.invoke(
            cli,
            ['--config', str(test_config), 'configure', str(test_build_root)]
        )
        
        assert result.exit_code == 0
        assert "Configuring system..." in result.output
        mock_execute.assert_called_once_with(BuildPhase.CONFIGURATION)


def test_cli_status(test_config, test_build_root):
    """Test status command output."""
    runner = click.testing.CliRunner()
    
    mock_progress = {
        'phase': 'TOOLCHAIN',
        'status': 'IN_PROGRESS',
        'current_script': 'test_script.sh',
        'completed_scripts': 2,
        'failed_scripts': 0,
        'error_count': 0,
        'runtime': 123.45
    }
    
    with patch('lfs_wrapper.build_manager.BuildManager.get_build_progress') as mock_get_progress:
        mock_get_progress.return_value = mock_progress
        result = runner.invoke(
            cli,
            ['--config', str(test_config), 'status', str(test_build_root)]
        )
        
        assert result.exit_code == 0
        assert "Build Status:" in result.output
        assert "Phase: TOOLCHAIN" in result.output
        assert "Status: IN_PROGRESS" in result.output


def test_cli_cleanup(test_config, test_build_root):
    """Test cleanup command execution."""
    runner = click.testing.CliRunner()
    with patch('lfs_wrapper.build_manager.BuildManager.cleanup') as mock_cleanup:
        result = runner.invoke(
            cli,
            ['--config', str(test_config), 'cleanup', str(test_build_root)]
        )
        
        assert result.exit_code == 0
        assert "Cleaning up build artifacts..." in result.output
        mock_cleanup.assert_called_once()


def test_cli_invalid_config():
    """Test CLI behavior with invalid configuration file."""
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem():
        # Create invalid config file
        with open('invalid.yaml', 'w') as f:
            f.write('invalid: yaml: content}')
        
        result = runner.invoke(cli, ['--config', 'invalid.yaml', 'status', '.'])
        assert result.exit_code == 2
        assert "Invalid configuration file" in result.output


def test_cli_build_error(test_config, test_build_root):
    """Test CLI error handling during build."""
    runner = click.testing.CliRunner()
    with patch('lfs_wrapper.build_manager.BuildManager.execute_phase') as mock_execute:
        mock_execute.side_effect = Exception("Build failed")
        result = runner.invoke(
            cli,
            ['--config', str(test_config), 'build', str(test_build_root)]
        )
        
        assert result.exit_code == 1
        assert "Build failed" in result.output


def test_cli_verbose_output(test_config, test_build_root):
    """Test verbose output option."""
    runner = click.testing.CliRunner()
    with patch('logging.basicConfig') as mock_logging:
        runner.invoke(
            cli,
            [
                '--config', str(test_config),
                '--verbose',
                'status',
                str(test_build_root)
            ]
        )
        
        # Verify debug level was set
        mock_logging.assert_called_once()
        assert mock_logging.call_args[1]['level'] == logging.DEBUG

