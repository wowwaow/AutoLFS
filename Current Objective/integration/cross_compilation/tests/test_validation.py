"""
Test suite for cross-compilation validation system.
"""
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any

from ..validation import (
    ValidationManager, ValidationLevel, ValidationResult,
    BuildPlatform, EnvironmentValidator, ResourceValidator,
    PlatformValidator
)
from ...monitoring.monitor import MonitoringManager

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration."""
    return {
        "toolchain_prefix": "x86_64-linux-gnu",
        "target_arch": "aarch64",
        "build_path": "/tmp/build",
        "required_paths": [
            "/usr/bin",
            "/usr/lib",
            "/usr/include"
        ],
        "cross_compile": True,
        "BUILD_ROOT": Path("/tmp/build"),
        "TARGET_SYSROOT": Path("/tmp/sysroot")
    }

@pytest.fixture
def test_platform() -> BuildPlatform:
    """Create test platform specification."""
    return BuildPlatform(
        architecture="x86_64",
        triple="x86_64-linux-gnu",
        features=["sse4.2", "avx2"],
        abi="gnu",
        requirements={
            "minimum_memory": 4,
            "minimum_cores": 2,
            "minimum_disk": 20
        }
    )

@pytest.fixture
def mock_monitoring_manager() -> Mock:
    """Create mock monitoring manager."""
    return Mock(spec=MonitoringManager)

class TestValidationManager:
    """Test cases for ValidationManager functionality."""

    @pytest.fixture
    def validation_manager(
        self, test_config: Dict[str, Any], mock_monitoring_manager: Mock
    ) -> ValidationManager:
        """Create validation manager instance."""
        return ValidationManager(test_config, mock_monitoring_manager)

    def test_initialization(self, validation_manager: ValidationManager):
        """Test validation manager initialization."""
        assert validation_manager.config is not None
        assert validation_manager.toolchain_validator is not None
        assert validation_manager.environment_validator is not None
        assert validation_manager.resource_validator is not None
        assert validation_manager.platform_validator is not None

    def test_basic_validation(
        self, validation_manager: ValidationManager, test_platform: BuildPlatform
    ):
        """Test basic (L1) validation."""
        result = validation_manager.validate(test_platform, ValidationLevel.L1_BASIC)
        
        assert result.level == ValidationLevel.L1_BASIC
        assert "platform" in result.details
        assert validation_manager.monitoring_manager.update_state.called

    def test_resource_validation(
        self, validation_manager: ValidationManager, test_platform: BuildPlatform
    ):
        """Test resource (L2) validation."""
        result = validation_manager.validate(test_platform, ValidationLevel.L2_RESOURCE)
        
        assert result.level == ValidationLevel.L2_RESOURCE
        assert "resources" in result.details
        assert "platform" in result.details

    def test_full_validation(
        self, validation_manager: ValidationManager, test_platform: BuildPlatform
    ):
        """Test full (L4) validation."""
        result = validation_manager.validate(test_platform, ValidationLevel.L4_FULL)
        
        assert result.level == ValidationLevel.L4_FULL
        assert all(key in result.details for key in [
            "platform", "resources", "toolchain", "environment"
        ])

    def test_error_handling(
        self, validation_manager: ValidationManager, test_platform: BuildPlatform
    ):
        """Test error handling in validation."""
        with patch.object(
            validation_manager.platform_validator,
            "validate_platform",
            side_effect=Exception("Test error")
        ):
            result = validation_manager.validate(test_platform, ValidationLevel.L1_BASIC)
            
            assert not result.success
            assert "error" in result.details
            assert "Test error" in result.messages[0]

class TestPlatformValidator:
    """Test cases for PlatformValidator functionality."""

    @pytest.fixture
    def platform_validator(self, test_config: Dict[str, Any]) -> PlatformValidator:
        """Create platform validator instance."""
        return PlatformValidator(test_config)

    def test_valid_platform(
        self, platform_validator: PlatformValidator, test_platform: BuildPlatform
    ):
        """Test validation of valid platform."""
        result = platform_validator.validate_platform(test_platform)
        assert result.success
        assert "architecture" in result.details
        assert "features" in result.details
        assert "abi" in result.details

    def test_invalid_architecture(
        self, platform_validator: PlatformValidator, test_platform: BuildPlatform
    ):
        """Test validation of invalid architecture."""
        test_platform.architecture = "invalid"
        result = platform_validator.validate_platform(test_platform)
        assert not result.success
        assert any("Unsupported host architecture" in msg for msg in result.messages)

    def test_missing_features(
        self, platform_validator: PlatformValidator, test_platform: BuildPlatform
    ):
        """Test validation of missing features."""
        test_platform.features = ["invalid_feature"]
        result = platform_validator.validate_platform(test_platform)
        assert not result.success
        assert any("Missing required features" in msg for msg in result.messages)

class TestEnvironmentValidator:
    """Test cases for EnvironmentValidator functionality."""

    @pytest.fixture
    def environment_validator(self, test_config: Dict[str, Any]) -> EnvironmentValidator:
        """Create environment validator instance."""
        return EnvironmentValidator(test_config)

    def test_valid_environment(self, environment_validator: EnvironmentValidator):
        """Test validation of valid environment."""
        result = environment_validator.validate_environment()
        assert result.success
        assert "variables" in result.details
        assert "paths" in result.details
        assert "permissions" in result.details

    def test_missing_variables(self, environment_validator: EnvironmentValidator):
        """Test validation of missing variables."""
        environment_validator.config = {}
        result = environment_validator.validate_environment()
        assert not result.success
        assert any("Missing required variable" in msg for msg in result.messages)

    @patch('os.access')
    def test_permission_validation(
        self, mock_access, environment_validator: EnvironmentValidator
    ):
        """Test validation of permissions."""
        mock_access.return_value = False
        result = environment_validator.validate_environment()
        assert not result.success
        assert any("permission" in msg.lower() for msg in result.messages)

class TestResourceValidator:
    """Test cases for ResourceValidator functionality."""

    @pytest.fixture
    def resource_validator(self, test_config: Dict[str, Any]) -> ResourceValidator:
        """Create resource validator instance."""
        return ResourceValidator(test_config)

    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_count')
    @patch('shutil.disk_usage')
    def test_sufficient_resources(
        self, mock_disk, mock_cpu, mock_memory,
        resource_validator: ResourceValidator,
        test_platform: BuildPlatform
    ):
        """Test validation of sufficient resources."""
        mock_memory.return_value.available = 8 * 1024**3  # 8GB
        mock_cpu.return_value = 4
        mock_disk.return_value.free = 50 * 1024**3  # 50GB
        
        result = resource_validator.validate_resources(test_platform)
        assert result.success
        assert all(key in result.details for key in ["memory", "cpu", "disk"])

    @patch('psutil.virtual_memory')
    def test_insufficient_memory(
        self, mock_memory,
        resource_validator: ResourceValidator,
        test_platform: BuildPlatform
    ):
        """Test validation of insufficient memory."""
        mock_memory.return_value.available = 2 * 1024**3  # 2GB
        result = resource_validator.validate_resources(test_platform)
        assert not result.success
        assert any("Insufficient memory" in msg for msg in result.messages)

    @patch('psutil.cpu_count')
    def test_insufficient_cpu(
        self, mock_cpu,
        resource_validator: ResourceValidator,
        test_platform: BuildPlatform
    ):
        """Test validation of insufficient CPU."""
        mock_cpu.return_value = 1
        result = resource_validator.validate_resources(test_platform)
        assert not result.success
        assert any("Insufficient CPU cores" in msg for msg in result.messages)

    @patch('shutil.disk_usage')
    def test_insufficient_disk(
        self, mock_disk,
        resource_validator: ResourceValidator,
        test_platform: BuildPlatform
    ):
        """Test validation of insufficient disk space."""
        mock_disk.return_value.free = 10 * 1024**3  # 10GB
        result = resource_validator.validate_resources(test_platform)
        assert not result.success
        assert any("Insufficient disk space" in msg for msg in result.messages)

