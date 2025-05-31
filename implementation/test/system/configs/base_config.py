"""
Base configuration for system tests.

This module defines the base configuration parameters and management functionality
for system test execution.
"""

import logging.config
import os
from pathlib import Path
from typing import Dict, Optional

class SystemTestConfig:
    """Base configuration for system test execution."""
    
    # Environment defaults
    DEFAULT_ROOT_DIR = Path("/mnt/host/WARP_CURRENT")
    DEFAULT_TEMP_DIR = Path("/tmp/system_tests")
    DEFAULT_LOG_DIR = Path("/mnt/host/WARP_CURRENT/logs/system_tests")
    
    # Resource configurations
    RESOURCE_LIMITS = {
        "memory_mb": 2048,  # 2GB default memory limit
        "cpu_count": 2,     # 2 CPU cores
        "disk_gb": 10,      # 10GB disk space
        "network": True,    # Network access allowed
    }
    
    # Logging configuration
    LOG_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": str(DEFAULT_LOG_DIR / "system_test.log"),
                "mode": "a"
            }
        },
        "loggers": {
            "": {
                "handlers": ["console", "file"],
                "level": "DEBUG",
                "propagate": True
            }
        }
    }
    
    # Test suite configuration
    SUITE_CONFIG = {
        "parallel_execution": True,
        "max_parallel_tests": 4,
        "max_retries": 3,
        "retry_delay_seconds": 5,
    }
    
    # Timeouts (in seconds)
    TIMEOUTS = {
        "setup": 300,       # 5 minutes for environment setup
        "teardown": 180,    # 3 minutes for cleanup
        "test_execution": 1800,  # 30 minutes max per test
        "validation": 300,  # 5 minutes for result validation
    }
    
    # Metric thresholds
    METRIC_THRESHOLDS = {
        "cpu_usage_percent": 80.0,
        "memory_usage_percent": 75.0,
        "disk_usage_percent": 90.0,
        "network_latency_ms": 100,
        "error_rate_percent": 1.0,
    }
    
    # Environment variables required for system tests
    REQUIRED_ENV_VARS = {
        "TEST_MODE": "system",
        "TEST_ROOT": str(DEFAULT_ROOT_DIR),
        "TEST_TEMP": str(DEFAULT_TEMP_DIR),
        "TEST_LOGS": str(DEFAULT_LOG_DIR),
    }
    
    def __init__(
        self,
        root_dir: Optional[Path] = None,
        resource_limits: Optional[Dict] = None,
        timeouts: Optional[Dict] = None,
        environment: Optional[Dict] = None
    ):
        """
        Initialize system test configuration.
        
        Args:
            root_dir: Optional override for root directory
            resource_limits: Optional override for resource limits
            timeouts: Optional override for timeouts
            environment: Optional environment variable overrides
        """
        self.root_dir = root_dir or self.DEFAULT_ROOT_DIR
        self.resource_limits = {**self.RESOURCE_LIMITS, **(resource_limits or {})}
        self.timeouts = {**self.TIMEOUTS, **(timeouts or {})}
        self.environment = {**self.REQUIRED_ENV_VARS, **(environment or {})}
        
        # Initialize required directories with targeted permissions
        self._initialize_directories()
        
        # Initialize logging with targeted permissions
        self._initialize_logging()
    
    def _initialize_directories(self):
        """Initialize required directories with proper permissions."""
        for path in [self.DEFAULT_ROOT_DIR, self.DEFAULT_TEMP_DIR, self.DEFAULT_LOG_DIR]:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                # Set targeted permissions
                os.chmod(path, 0o755)
                if os.getuid() == os.stat(path).st_uid:
                    os.chown(path, os.getuid(), os.getgid())
    
    def _initialize_logging(self):
        """Initialize logging with proper file permissions."""
        log_file = Path(self.LOG_CONFIG["handlers"]["file"]["filename"])
        
        # Ensure log directory exists with proper permissions
        log_dir = log_file.parent
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(log_dir, 0o755)
        
        # Create log file if it doesn't exist
        if not log_file.exists():
            log_file.touch()
            os.chmod(log_file, 0o644)
        
        logging.config.dictConfig(self.LOG_CONFIG)
    
    def get_test_path(self, test_name: str, path_type: str = "temp") -> Path:
        """
        Get test-specific path with proper permissions.
        
        Args:
            test_name: Name of the test
            path_type: Type of path (temp, log, data)
            
        Returns:
            Path object for requested directory
        """
        if path_type == "temp":
            base_dir = self.DEFAULT_TEMP_DIR
        elif path_type == "log":
            base_dir = self.DEFAULT_LOG_DIR
        else:
            base_dir = self.DEFAULT_ROOT_DIR / "test_data"
        
        test_dir = base_dir / test_name
        if not test_dir.exists():
            test_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(test_dir, 0o755)
        
        return test_dir
    
    def get_resource_limit(self, resource: str) -> any:
        """
        Get specific resource limit.
        
        Args:
            resource: Resource identifier
            
        Returns:
            Resource limit value
        """
        return self.resource_limits.get(resource)
    
    def get_timeout(self, operation: str) -> int:
        """
        Get timeout for specific operation.
        
        Args:
            operation: Operation identifier
            
        Returns:
            Timeout in seconds
        """
        return self.timeouts.get(operation, self.TIMEOUTS["test_execution"])
    
    def get_metric_threshold(self, metric: str) -> float:
        """
        Get threshold for specific metric.
        
        Args:
            metric: Metric identifier
            
        Returns:
            Threshold value
        """
        return self.METRIC_THRESHOLDS.get(metric, float('inf'))
    
    def update_environment(self, env_vars: Dict[str, str]):
        """
        Update environment variables.
        
        Args:
            env_vars: Dictionary of environment variables to update
        """
        self.environment.update(env_vars)
        # Apply environment variables
        os.environ.update(self.environment)
    
    def validate_config(self) -> bool:
        """
        Validate configuration.
        
        Returns:
            True if configuration is valid
        """
        # Check required directories with proper permissions
        for path in [self.DEFAULT_ROOT_DIR, self.DEFAULT_TEMP_DIR, self.DEFAULT_LOG_DIR]:
            if not path.exists():
                return False
            stats = os.stat(path)
            if stats.st_mode & 0o777 != 0o755:
                return False
        
        # Check environment variables
        for var in self.REQUIRED_ENV_VARS:
            if var not in os.environ:
                return False
        
        return True

