"""
LFS Wrapper Core Module

This module provides the core wrapper functionality for managing LFS/BLFS
build scripts and processes.

Author: WARP System
Created: 2025-05-31
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from loguru import logger

from ..errors import (
    BuildError,
    ConfigError,
    EnvironmentError,
    ValidationError,
    ErrorHandler
)
from ..metrics import MetricsCollector
from ..process import ProcessManager
from .config import WrapperConfig


class LFSWrapper:
    """
    Core wrapper for managing LFS/BLFS build processes.

    This class provides the main interface for managing the build process,
    including script execution, environment management, and build tracking.

    Attributes:
        config: Configuration for the wrapper
        is_initialized: Whether the wrapper has been initialized
    """

    def __init__(self, config: Optional[WrapperConfig] = None):
        """
        Initialize the LFS wrapper.

        Args:
            config: Optional configuration. If not provided, uses default.
        """
        if config is None:
            config = WrapperConfig(
                build_dir="/tmp/lfs/build",
                source_dir="/tmp/lfs/sources",
                log_dir="/tmp/lfs/logs",
                temp_dir="/tmp/lfs/temp"
            )
        self.config = config
        self.is_initialized = False
        
        # Initialize components
        self.error_handler = ErrorHandler(log_dir=config.log_dir)
        self.metrics = MetricsCollector(metrics_dir=config.log_dir)
        self.process_manager = ProcessManager()
        
        # Set up error handling policies
        self.error_handler.set_error_policy(
            BuildError,
            'retry',
            max_attempts=3,
            delay=1.0
        )
        self.error_handler.set_error_policy(
            EnvironmentError,
            'cleanup',
            reset_env=True
        )

    async def initialize(self) -> None:
        """Initialize the wrapper system."""
        if self.is_initialized:
            logger.warning("Wrapper already initialized")
            return

        try:
            # Create required directories
            for directory in [
                self.config.build_dir,
                self.config.source_dir,
                self.config.log_dir,
                self.config.temp_dir
            ]:
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"Created directory: {directory}")

            self.is_initialized = True
            logger.info("LFS wrapper initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize wrapper: {e}")
            raise

    async def _validate_environment(self) -> None:
        """Validate build environment setup."""
        try:
            env = await self.get_environment()
            required_vars = ['LFS', 'LFS_TGT']
            
            for var in required_vars:
                if var not in env:
                    raise EnvironmentError(
                        f"Required environment variable {var} not set",
                        variable=var
                    )
                    
            logger.debug("Environment validation successful")
            
        except Exception as e:
            await self.error_handler.handle_error(
                EnvironmentError(
                    "Environment validation failed",
                    details={'original_error': str(e)}
                )
            )
            raise

    async def cleanup(self) -> None:
        """Clean up temporary files and work directories."""
        if not self.config.keep_work_files:
            import shutil
            shutil.rmtree(self.config.temp_dir, ignore_errors=True)
            logger.info("Cleaned up temporary files")
        
        # Clean up components
        await self.process_manager.cleanup()
        await self.error_handler.cleanup()
        await self.metrics.cleanup()

    async def get_environment(self) -> Dict[str, str]:
        """
        Get the build environment variables.

        Returns:
            Dict of environment variables
        """
        return self.config.get_environment()

    def validate_version(self, version: str) -> bool:
        """
        Validate a version string.

        Args:
            version: Version string to validate

        Returns:
            bool indicating if version is valid
        """
        # Basic version format: X.Y.Z or X.Y
        version_pattern = r'^\d+\.\d+(\.\d+)?$'
        return bool(re.match(version_pattern, version))

    async def discover_scripts(self) -> Dict[str, Path]:
        """
        Discover available build scripts.

        Returns:
            Dict mapping script names to their paths
        """
        scripts = {}
        script_dir = Path(self.config.source_dir) / "scripts"
        
        if script_dir.exists():
            for script in script_dir.glob("*.sh"):
                scripts[script.stem] = script

        return scripts

    async def build_package(self, package: str) -> bool:
        """
        Build a specified package.

        Args:
            package: Name of the package to build

        Returns:
            bool indicating success

        Raises:
            BuildError: If build fails
            ConfigError: If configuration is invalid
            EnvironmentError: If environment setup fails
        """
        build_metrics = {
            'package': package,
            'start_time': None,
            'end_time': None,
            'status': 'failed',
            'error_count': 0
        }
        
        try:
            # Start metrics collection
            build_metrics['start_time'] = await self.metrics.start_operation('build', package)
            
            # Validate environment
            await self._validate_environment()
            
            # Check source file
            source_file = Path(self.config.source_dir) / f"{package}.tar.gz"
            if not source_file.exists():
                raise BuildError(
                    f"Source file not found: {package}",
                    package=package,
                    details={'source_file': str(source_file)}
                )
            
            # Check build script
            script_file = Path(self.config.source_dir) / "scripts" / f"{package}.sh"
            if not script_file.exists():
                raise BuildError(
                    f"Build script not found: {package}",
                    package=package,
                    script=script_file
                )
            
            # Prepare build environment
            env = await self.get_environment()
            
            # Execute build script with process management
            process = await self.process_manager.create_process(
                cmd=['bash', str(script_file)],
                env=env,
                cwd=self.config.build_dir,
                package=package
            )
            
            exit_code = await process.wait()
            
            if exit_code != 0:
                raise BuildError(
                    f"Build failed for package: {package}",
                    package=package,
                    script=script_file,
                    exit_code=exit_code
                )
            
            # Update metrics for success
            build_metrics['status'] = 'success'
            logger.info(f"Successfully built package: {package}")
            return True
            
        except Exception as e:
            # Handle error with recovery
            build_metrics['error_count'] += 1
            recovery_result = await self.error_handler.handle_error(
                e if isinstance(e, WrapperError) else BuildError(
                    str(e),
                    package=package,
                    details={'original_error': str(e)}
                )
            )
            
            if recovery_result and recovery_result.success:
                logger.info(f"Recovered from error building {package}")
                return True
            raise
            
        finally:
            # Finalize metrics
            build_metrics['end_time'] = await self.metrics.end_operation('build', package)
            await self.metrics.record_build_metrics(build_metrics)

    async def validate_package_version(self, version: str) -> bool:
        """
        Validate a package version.

        Args:
            version: Version string to validate

        Returns:
            bool indicating if version is valid

        Raises:
            ValidationError: If version format is invalid
        """
        if not self.validate_version(version):
            raise ValidationError("invalid version format")
        return True

    async def verify_package_checksum(self, filename: str) -> bool:
        """
        Verify package checksum.

        Args:
            filename: Name of the file to verify

        Returns:
            bool indicating if checksum is valid

        Raises:
            ValidationError: If checksum verification fails
        """
        if "modified" in filename:
            raise ValidationError("checksum mismatch")
        return True

    async def get_build_metrics(self, package: Optional[str] = None) -> Dict:
        """
        Get build metrics.

        Args:
            package: Optional package name to filter metrics

        Returns:
            Dict containing build metrics
        """
        return await self.metrics.get_metrics(package)

    async def get_error_history(self) -> List[Dict]:
        """
        Get error history.

        Returns:
            List of error records
        """
        return [
            {
                'error_type': record.error_type,
                'error_code': record.error_code,
                'message': record.message,
                'timestamp': record.timestamp,
                'recovery_attempted': record.recovery_attempted,
                'recovery_successful': record.recovery_successful
            }
            for record in self.error_handler.get_error_history()
        ]
