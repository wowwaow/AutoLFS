"""
Test suite for toolchain validation functionality.
"""
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any

from ..toolchain import ToolchainValidator, ToolchainComponent
from ..validation import BuildPlatform, ValidationLevel

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration."""
    return {
        "toolchain_prefix": "x86_64-linux-gnu",
        "build_path": "/tmp/build",
        "required_versions": {
            "gcc": "11.2.0",
            "binutils": "2.37",
            "glibc": "2.34"
        }
    }

@pytest.fixture
def test_platform() -> BuildPlatform:
    """Create test platform specification."""
    return BuildPlatform(
        architecture="x86_64",
        triple="x86_64-linux-gnu",
        features=["sse4.2", "avx2"],
        abi="gnu",
        requirements={}
    )

@pytest.fixture
def toolchain_validator(test_config: Dict[str, Any]) -> ToolchainValidator:
    """Create toolchain validator instance."""
    return ToolchainValidator(test_config)

class TestToolchainValidator:
    """Test cases for ToolchainValidator functionality."""

    def test_initialization(self, toolchain_validator: ToolchainValidator):
        """Test toolchain validator initialization."""
        assert toolchain_validator.config is not None
        assert toolchain_validator.required_versions is not None
        assert "gcc" in toolchain_validator.required_versions

    @patch('subprocess.run')
    def test_version_validation(
        self,
        mock_run,
        toolchain_validator: ToolchainValidator,
        test_platform: BuildPlatform
    ):
        """Test toolchain version validation."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="gcc version 11.2.0"
        )
        
        result = toolchain_validator._validate_versions()
        assert result.success
        assert result.level == ValidationLevel.L3_TOOLCHAIN
        assert "versions" in result.details

    @patch('subprocess.run')
    def test_outdated_version(
        self,
        mock_run,
        toolchain_validator: ToolchainValidator,
        test_platform: BuildPlatform
    ):
        """Test validation of outdated toolchain version."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="gcc version 9.3.0"
        )
        
        result = toolchain_validator._validate_versions()
        assert not result.success
        assert any("below minimum required version" in msg for msg in result.messages)

    def test_version_comparison(self, toolchain_validator: ToolchainValidator):
        """Test version comparison logic."""
        assert toolchain_validator._compare_versions("11.2.0", "10.2.0") > 0
        assert toolchain_validator._compare_versions("10.2.0", "11.2.0") < 0
        assert toolchain_validator._compare_versions("11.2.0", "11.2.0") == 0
        assert toolchain_validator._compare_versions("11.2.0", "11.2") == 0
        assert toolchain_validator._compare_versions("11.2.1", "11.2.0") > 0

    @patch('subprocess.run')
    def test_feature_validation(
        self,
        mock_run,
        toolchain_validator: ToolchainValidator,
        test_platform: BuildPlatform
    ):
        """Test toolchain feature validation."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        with patch.object(
            toolchain_validator,
            '_test_lto_support',
            return_value=True
        ), patch.object(
            toolchain_validator,
            '_test_pic_support',
            return_value=True
        ):
            result = toolchain_validator._validate_features()
            assert result.success
            assert result.level == ValidationLevel.L3_TOOLCHAIN
            assert "features" in result.details

    @patch('subprocess.run')
    def test_target_validation(
        self,
        mock_run,
        toolchain_validator: ToolchainValidator,
        test_platform: BuildPlatform
    ):
        """Test target platform validation."""
        mock_run.side_effect = [
            Mock(returncode=0, stdout=test_platform.triple),  # Triple check
            Mock(returncode=0, stdout="sse4.2\navx2\n"),     # Features check
            Mock(returncode=0, stdout=f"gnu")                # ABI check
        ]
        
        result = toolchain_validator._validate_target_support(test_platform)
        assert result.success
        assert result.level == ValidationLevel.L3_TOOLCHAIN
        assert all(key in result.details for key in ["triple", "features", "abi"])

    def test_compilation_tests(
        self,
        toolchain_validator: ToolchainValidator,
        test_platform: BuildPlatform
    ):
        """Test compilation test execution."""
        with patch.object(
            toolchain_validator,
            '_compile_test',
            return_value=True
        ):
            result = toolchain_validator._run_compilation_tests(test_platform)
            assert result.success
            assert result.level == ValidationLevel.L3_TOOLCHAIN
            assert "tests" in result.details

    @patch('tempfile.NamedTemporaryFile')
    @patch('subprocess.run')
    def test_individual_feature_tests(
        self,
        mock_run,
        mock_temp_file,
        toolchain_validator: ToolchainValidator
    ):
        """Test individual feature test execution."""
        mock_run.return_value = Mock(returncode=0)
        mock_temp_file.return_value.__enter__.return_value = Mock(
            name="/tmp/test.c"
        )

        assert toolchain_validator._test_lto_support()
        assert toolchain_validator._test_pic_support()
        assert toolchain_validator._test_relro_support()
        assert toolchain_validator._test_stack_protection()

    @patch('subprocess.run')
    def test_abi_compatibility(
        self,
        mock_run,
        toolchain_validator: ToolchainValidator,
        test_platform: BuildPlatform
    ):
        """Test ABI compatibility checking."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=f"{test_platform.triple}"
        )
        
        result = toolchain_validator._check_abi_compatibility(test_platform.abi)
        assert result.success
        assert result.level == ValidationLevel.L3_TOOLCHAIN
        assert "actual" in result.details
        assert "expected" in result.details

    def test_error_handling(
        self,
        toolchain_validator: ToolchainValidator,
        test_platform: BuildPlatform
    ):
        """Test error handling in validation."""
        with patch.object(
            toolchain_validator,
            '_validate_versions',
            side_effect=Exception("Test error")
        ):
            result = toolchain_validator.validate_toolchain(test_platform)
            assert not result.success
            assert any("Failed to validate" in msg for msg in result.messages)

    def test_test_source_generation(self, toolchain_validator: ToolchainValidator):
        """Test test source code generation."""
        hello_source = toolchain_validator._get_test_source("hello.c")
        assert "main" in hello_source
        assert "printf" in hello_source
        
        feature_source = toolchain_validator._get_test_source("features.cpp")
        assert "noinline" in feature_source
        assert "volatile" in feature_source

