#!/usr/bin/env python3

import os
import pytest
from pathlib import Path
from click.testing import CliRunner
import yaml

# Add implementation directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
sys.path.append(str(Path(__file__).parent.parent / "lib"))

from lfs_wrapper import cli, LFSWrapper
from lfs_core import LFSCore, LFSError, BuildEnvironment

@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
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
        },
        'requirements': {
            'disk_space_gb': 30
        }
    }

@pytest.fixture
def config_file(tmp_path, test_config):
    """Create a temporary config file."""
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(test_config, f)
    return str(config_path)

@pytest.fixture
def cli_runner():
    """Provide Click CLI runner."""
    return CliRunner()

class TestLFSWrapper:
    """Test suite for LFS wrapper functionality."""

    def test_config_loading(self, config_file, test_config):
        """Test configuration loading."""
        wrapper = LFSWrapper(config_file)
        assert wrapper.config == test_config

    def test_environment_setup(self, config_file, monkeypatch, tmp_path):
        """Test environment setup."""
        # Update config paths to use temporary directory
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        config['paths']['sources'] = str(tmp_path / "sources")
        config['paths']['tools'] = str(tmp_path / "tools")
        config['paths']['scripts'] = str(tmp_path / "scripts")
        config['paths']['logs'] = str(tmp_path / "logs")
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        wrapper = LFSWrapper(config_file)
        
        # Mock environment variables
        monkeypatch.setenv("LFS", "/mnt/lfs")
        monkeypatch.setenv("LFS_TGT", "x86_64-lfs-linux-gnu")
        monkeypatch.setenv("PATH", "/tools/bin:/bin:/usr/bin")
        
        wrapper.setup_environment()
        
        # Verify directories were created
        assert Path(config['paths']['sources']).exists()
        assert Path(config['paths']['tools']).exists()
        assert Path(config['paths']['scripts']).exists()
        assert Path(config['paths']['logs']).exists()

    def test_invalid_config(self, tmp_path):
        """Test handling of invalid configuration."""
        invalid_config = tmp_path / "invalid.yaml"
        invalid_config.write_text("invalid: yaml: :")
        
        with pytest.raises(click.ClickException) as exc_info:
            LFSWrapper(str(invalid_config))
        assert "Configuration error" in str(exc_info.value)

    def test_missing_environment_vars(self, config_file, monkeypatch):
        """Test detection of missing environment variables."""
        wrapper = LFSWrapper(config_file)
        
        # Clear environment variables
        monkeypatch.delenv("LFS", raising=False)
        monkeypatch.delenv("LFS_TGT", raising=False)
        
        with pytest.raises(click.ClickException) as exc_info:
            wrapper.setup_environment()
        assert "not set" in str(exc_info.value)

class TestBuildEnvironment:
    """Test suite for BuildEnvironment class."""

    def test_environment_variables(self, test_config):
        """Test environment variable setup."""
        env = BuildEnvironment(test_config)
        env._setup_environment()
        
        assert os.environ["LFS"] == test_config['environment']['LFS']
        assert os.environ["LFS_TGT"] == test_config['environment']['LFS_TGT']
        assert os.environ["PATH"] == test_config['environment']['PATH']

    def test_directory_creation(self, test_config, tmp_path):
        """Test directory creation."""
        config = test_config.copy()
        config['paths'] = {
            k: str(tmp_path / k)
            for k in ['sources', 'tools', 'scripts', 'logs']
        }
        
        env = BuildEnvironment(config)
        env._create_directories()
        
        for path in config['paths'].values():
            assert Path(path).exists()

class TestLFSCore:
    """Test suite for LFSCore class."""

    def test_script_execution(self, test_config, tmp_path):
        """Test script execution."""
        # Create a test script
        script_dir = tmp_path / "scripts"
        script_dir.mkdir(parents=True)
        test_script = script_dir / "test.sh"
        test_script.write_text("#!/bin/sh\necho 'Test successful'\n")
        test_script.chmod(0o755)
        
        # Update config to use test script directory
        config = test_config.copy()
        config['paths']['scripts'] = str(script_dir)
        
        core = LFSCore(config)
        core.execute_script("test.sh")

    def test_nonexistent_script(self, test_config):
        """Test handling of non-existent script."""
        core = LFSCore(test_config)
        with pytest.raises(LFSError) as exc_info:
            core.execute_script("nonexistent.sh")
        assert "Script not found" in str(exc_info.value)

    def test_non_executable_script(self, test_config, tmp_path):
        """Test handling of non-executable script."""
        script_dir = tmp_path / "scripts"
        script_dir.mkdir(parents=True)
        test_script = script_dir / "non_executable.sh"
        test_script.write_text("#!/bin/sh\necho 'Test'\n")
        
        config = test_config.copy()
        config['paths']['scripts'] = str(script_dir)
        
        core = LFSCore(config)
        with pytest.raises(LFSError) as exc_info:
            core.execute_script("non_executable.sh")
        assert "not executable" in str(exc_info.value)

class TestCLICommands:
    """Test suite for CLI commands."""

    def test_setup_command(self, cli_runner, config_file, monkeypatch, tmp_path):
        """Test the setup command."""
        # Update config to use temporary directory
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        config['paths']['sources'] = str(tmp_path / "sources")
        config['paths']['tools'] = str(tmp_path / "tools")
        config['paths']['scripts'] = str(tmp_path / "scripts")
        config['paths']['logs'] = str(tmp_path / "logs")
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Set required environment variables
        monkeypatch.setenv("LFS", "/mnt/lfs")
        monkeypatch.setenv("LFS_TGT", "x86_64-lfs-linux-gnu")
        monkeypatch.setenv("PATH", "/tools/bin:/bin:/usr/bin")
        
        result = cli_runner.invoke(cli, ['--config', config_file, 'setup'])
        assert result.exit_code == 0
        assert "Environment setup complete" in result.output

    def test_status_command(self, cli_runner, config_file, monkeypatch):
        """Test the status command."""
        monkeypatch.setenv("LFS", "/mnt/lfs")
        monkeypatch.setenv("LFS_TGT", "x86_64-lfs-linux-gnu")
        
        result = cli_runner.invoke(cli, ['--config', config_file, 'status'])
        assert result.exit_code == 0
        assert "LFS: /mnt/lfs" in result.output
        assert "LFS_TGT: x86_64-lfs-linux-gnu" in result.output

    def test_run_command(self, cli_runner, config_file, tmp_path):
        """Test the run command."""
        # Create a test script
        script_dir = tmp_path / "scripts"
        script_dir.mkdir(parents=True)
        test_script = script_dir / "test.sh"
        test_script.write_text("#!/bin/sh\necho 'Test successful'\n")
        test_script.chmod(0o755)
        
        # Update config to use test script directory
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        config['paths']['scripts'] = str(script_dir)
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        result = cli_runner.invoke(cli, ['--config', config_file, 'run', 'test.sh'])
        assert result.exit_code == 0
        assert "Successfully executed test.sh" in result.output

    def test_run_command_with_args(self, cli_runner, config_file, tmp_path):
        """Test the run command with arguments."""
        # Create a test script
        script_dir = tmp_path / "scripts"
        script_dir.mkdir(parents=True)
        test_script = script_dir / "test.sh"
        test_script.write_text("#!/bin/sh\necho \"Args: $@\"\n")
        test_script.chmod(0o755)
        
        # Update config to use test script directory
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        config['paths']['scripts'] = str(script_dir)
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        result = cli_runner.invoke(cli, ['--config', config_file, 'run', 'test.sh', 'arg1', 'arg2'])
        assert result.exit_code == 0
        assert "Successfully executed test.sh" in result.output

