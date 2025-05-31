"""Core functionality for the LFS build system wrapper."""

import os
import logging
from pathlib import Path
from typing import List, Optional

from .exceptions import LFSConfigError, LFSEnvironmentError

class LFSCore:
    """Core class for managing LFS build operations."""

    def __init__(self):
        """Initialize the LFS Core system."""
        self.logger = logging.getLogger(__name__)
        self.config = None
        self.environment = {}
        self.initialized = False

    def initialize(self) -> None:
        """Initialize the LFS build environment."""
        try:
            self.validate_environment()
            self.setup_logging()
            self.load_config()
            self.initialized = True
        except Exception as e:
            self.handle_error(f"Initialization failed: {e}", raise_exception=True)

    def validate_environment(self) -> None:
        """Validate the LFS environment variables and settings."""
        required_vars = ['LFS', 'LFS_TGT', 'PATH']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise LFSEnvironmentError(f"Required environment variables not set: {', '.join(missing_vars)}")
        
        # Validate LFS directory
        lfs_path = os.getenv('LFS')
        if not lfs_path or not Path(lfs_path).exists():
            raise LFSEnvironmentError("LFS base directory is not properly set or doesn't exist")

    def validate_config(self) -> None:
        """Validate the LFS configuration."""
        if not self.config:
            raise LFSConfigError("Configuration is not initialized")
        
        required_keys = ['paths', 'environment', 'logging']
        for key in required_keys:
            if key not in self.config:
                raise LFSConfigError(f"Missing required configuration key: {key}")

    def resolve_path(self, path: str) -> str:
        """Resolve and validate a path in the LFS context."""
        if not path:
            raise ValueError("Path cannot be empty")
        
        # Convert to absolute path if relative
        if not path.startswith('/'):
            path = os.path.join(os.getenv('LFS', ''), path)
        
        return os.path.abspath(path)

    def validate_script(self, script_name: str) -> bool:
        """Validate an LFS build script."""
        if not script_name:
            raise LFSConfigError("Script name cannot be empty")
        
        script_path = self.resolve_path(f"scripts/{script_name}")
        if not os.path.exists(script_path):
            raise LFSConfigError(f"Script not found: {script_path}")
        
        if not os.access(script_path, os.X_OK):
            raise LFSConfigError(f"Script is not executable: {script_path}")
        
        return True

    def check_dependencies(self, dependencies: List[str]) -> None:
        """Check if required dependencies are available."""
        missing = []
        for dep in dependencies:
            if not self._check_dependency(dep):
                missing.append(dep)
        
        if missing:
            raise LFSEnvironmentError(f"Missing dependencies: {', '.join(missing)}")

    def setup_build_environment(self) -> None:
        """Set up the LFS build environment."""
        if not self.initialized:
            raise LFSEnvironmentError("Core system not initialized")
        
        required_dirs = ['sources', 'tools', 'scripts', 'logs']
        lfs_root = os.getenv('LFS')
        
        if not lfs_root:
            raise LFSEnvironmentError("LFS environment variable not set")
        
        for dir_name in required_dirs:
            dir_path = os.path.join(lfs_root, dir_name)
            if not os.path.exists(dir_path):
                raise LFSEnvironmentError(f"Required directory missing: {dir_path}")

    def cleanup(self) -> None:
        """Clean up temporary files and reset state."""
        try:
            # Clean up temporary files
            temp_dir = os.path.join(os.getenv('LFS', ''), 'temp')
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")

    def log_message(self, message: str, level: str = "INFO") -> None:
        """Log a message with the specified level."""
        if not self.logger:
            self.setup_logging()
        
        log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        self.logger.log(log_levels.get(level.upper(), logging.INFO), message)

    def handle_error(self, error_message: str, raise_exception: bool = False) -> None:
        """Handle an error condition."""
        self.log_message(error_message, level="ERROR")
        if raise_exception:
            raise LFSEnvironmentError(error_message)

    def _check_dependency(self, dependency: str) -> bool:
        """Check if a single dependency is available."""
        from shutil import which
        return which(dependency) is not None

    def setup_logging(self) -> None:
        """Set up logging configuration."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        log_dir = os.path.join(os.getenv('LFS', ''), 'logs')
        
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(os.path.join(log_dir, 'lfs_core.log'))
            ]
        )

    def load_config(self) -> None:
        """Load the LFS configuration."""
        config_path = os.path.join(os.getenv('LFS', ''), 'config', 'lfs_config.yaml')
        if not os.path.exists(config_path):
            raise LFSConfigError(f"Configuration file not found: {config_path}")
        
        try:
            import yaml
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            self.validate_config()
        except Exception as e:
            raise LFSConfigError(f"Failed to load configuration: {e}")

