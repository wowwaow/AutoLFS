import pytest
import os
from pathlib import Path
from typing import Dict, Any

from test_runner.core import TestRunner
from test_runner.exceptions import ConfigurationError, ResourceError
from test_runner.utils import ResourceManager

class TestTestRunnerIntegration:
    """Integration tests for the TestRunner implementation."""
    
    def test_runner_initialization(self, mock_config: Dict[str, Any], test_environment: Dict[str, str]):
        """Test that the TestRunner initializes correctly with valid configuration."""
        runner = TestRunner(config=mock_config, env=test_environment)
        assert runner is not None
        assert runner.config == mock_config
        assert runner.env == test_environment

    def test_invalid_configuration(self, test_environment: Dict[str, str]):
        """Test that invalid configuration raises appropriate errors."""
        invalid_config = {"invalid": "config"}
        with pytest.raises(ConfigurationError):
            TestRunner(config=invalid_config, env=test_environment)

    def test_successful_build_execution(
        self, 
        mock_config: Dict[str, Any], 
        test_environment: Dict[str, str],
        mock_build_script: Path
    ):
        """Test execution of a successful build script."""
        runner = TestRunner(config=mock_config, env=test_environment)
        result = runner.run_test(mock_build_script)
        
        assert result.success is True
        assert result.exit_code == 0
        assert "Build completed successfully" in result.output
        assert result.duration > 0

    def test_failed_build_execution(
        self, 
        mock_config: Dict[str, Any], 
        test_environment: Dict[str, str],
        failed_build_script: Path
    ):
        """Test execution of a failing build script."""
        runner = TestRunner(config=mock_config, env=test_environment)
        result = runner.run_test(failed_build_script)
        
        assert result.success is False
        assert result.exit_code == 1
        assert "Error: Build failed" in result.error_output

    def test_resource_management(
        self, 
        mock_config: Dict[str, Any], 
        test_environment: Dict[str, str],
        test_resources_dir: Path
    ):
        """Test resource allocation and management during test execution."""
        resource_manager = ResourceManager(mock_config["resources"])
        
        with resource_manager:
            assert resource_manager.check_memory_usage() <= float(mock_config["resources"]["memory_limit"][:-1])
            assert resource_manager.check_cpu_usage() <= mock_config["resources"]["cpu_limit"]
            
            # Verify disk space management
            output_dir = test_resources_dir / "output"
            assert output_dir.exists()
            assert resource_manager.check_disk_space(output_dir) <= float(mock_config["resources"]["disk_space"][:-1])

    def test_parallel_execution(
        self, 
        mock_config: Dict[str, Any], 
        test_environment: Dict[str, str],
        mock_build_script: Path
    ):
        """Test parallel execution of multiple build scripts."""
        runner = TestRunner(config=mock_config, env=test_environment)
        scripts = [mock_build_script] * 3  # Run same script multiple times
        
        results = runner.run_parallel_tests(scripts)
        assert len(results) == 3
        assert all(result.success for result in results)
        assert all(result.exit_code == 0 for result in results)

    def test_retry_mechanism(
        self, 
        mock_config: Dict[str, Any], 
        test_environment: Dict[str, str],
        failed_build_script: Path
    ):
        """Test the retry mechanism for failed builds."""
        runner = TestRunner(config=mock_config, env=test_environment)
        result = runner.run_test_with_retry(failed_build_script)
        
        assert result.success is False
        assert result.retry_count == mock_config["build"]["retry_count"]
        assert len(result.retry_history) == mock_config["build"]["retry_count"]

    def test_log_collection(
        self, 
        mock_config: Dict[str, Any], 
        test_environment: Dict[str, str],
        mock_build_script: Path,
        test_resources_dir: Path
    ):
        """Test that logs are properly collected and stored."""
        runner = TestRunner(config=mock_config, env=test_environment)
        result = runner.run_test(mock_build_script)
        
        log_dir = test_resources_dir / "logs"
        assert log_dir.exists()
        
        # Verify log files exist and contain expected content
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) > 0
        
        log_content = log_files[0].read_text()
        assert "Starting mock build" in log_content
        assert "Build completed successfully" in log_content

    def test_environment_integration(
        self, 
        mock_config: Dict[str, Any], 
        test_environment: Dict[str, str]
    ):
        """Test integration with environment variables and paths."""
        runner = TestRunner(config=mock_config, env=test_environment)
        
        # Verify environment variables are properly set
        assert runner.env["TEST_ROOT"] == str(Path(test_environment["TEST_ROOT"]))
        assert runner.env["BUILD_MODE"] == "test"
        
        # Verify path resolution
        resolved_paths = runner.resolve_paths()
        assert resolved_paths["build_scripts"].exists()
        assert resolved_paths["logs"].exists()
        assert resolved_paths["output"].exists()

    def test_resource_limits(
        self, 
        mock_config: Dict[str, Any], 
        test_environment: Dict[str, str]
    ):
        """Test enforcement of resource limits."""
        resource_config = mock_config["resources"]
        resource_manager = ResourceManager(resource_config)
        
        with pytest.raises(ResourceError):
            # Attempt to allocate more resources than allowed
            resource_manager.allocate_memory(float(resource_config["memory_limit"][:-1]) * 2)

