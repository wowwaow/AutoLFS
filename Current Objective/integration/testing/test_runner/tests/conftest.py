import os
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any

@pytest.fixture(scope="session")
def test_resources_dir(tmp_path_factory) -> Path:
    """Create a temporary directory for test resources."""
    temp_dir = tmp_path_factory.mktemp("test_resources")
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="function")
def mock_config() -> Dict[str, Any]:
    """Provide mock configuration for test runner."""
    return {
        "build": {
            "parallel_jobs": 4,
            "timeout": 3600,
            "retry_count": 3
        },
        "paths": {
            "build_scripts": "${TEST_ROOT}/scripts",
            "logs": "${TEST_ROOT}/logs",
            "output": "${TEST_ROOT}/output"
        },
        "resources": {
            "memory_limit": "4G",
            "cpu_limit": 2,
            "disk_space": "10G"
        }
    }

@pytest.fixture(scope="function")
def test_environment(test_resources_dir) -> Generator[Dict[str, str], None, None]:
    """Set up test environment with required paths and variables."""
    env = os.environ.copy()
    env.update({
        "TEST_ROOT": str(test_resources_dir),
        "BUILD_MODE": "test",
        "LOG_LEVEL": "DEBUG"
    })
    
    # Create required directories
    for dir_name in ["scripts", "logs", "output"]:
        path = test_resources_dir / dir_name
        path.mkdir(exist_ok=True)
    
    yield env

@pytest.fixture(scope="function")
def mock_build_script(test_resources_dir) -> Path:
    """Create a mock build script for testing."""
    script_content = """#!/bin/bash
echo "Starting mock build"
sleep 1
echo "Build completed successfully"
exit 0
"""
    script_path = test_resources_dir / "scripts" / "mock_build.sh"
    script_path.write_text(script_content)
    script_path.chmod(0o755)
    return script_path

@pytest.fixture(scope="function")
def failed_build_script(test_resources_dir) -> Path:
    """Create a mock build script that fails for testing error handling."""
    script_content = """#!/bin/bash
echo "Starting mock build"
echo "Error: Build failed" >&2
exit 1
"""
    script_path = test_resources_dir / "scripts" / "failed_build.sh"
    script_path.write_text(script_content)
    script_path.chmod(0o755)
    return script_path

