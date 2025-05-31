"""
Error Types Module

This module defines the error types and context classes for the
LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ErrorContext:
    """Context information for errors."""
    timestamp: datetime = datetime.now()
    location: Optional[str] = None
    operation: Optional[str] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.details is None:
            self.details = {}


class WrapperError(Exception):
    """Base class for all wrapper system errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs
    ):
        """
        Initialize wrapper error.

        Args:
            message: Error message
            code: Error code
            context: Error context
            **kwargs: Additional error details
        """
        super().__init__(message)
        self.code = code or "UNKNOWN"
        self.context = context or ErrorContext()
        self.context.details.update(kwargs)


class BuildError(WrapperError):
    """Error during build process execution."""

    def __init__(
        self,
        message: str,
        package: str,
        script: Optional[Path] = None,
        exit_code: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize build error.

        Args:
            message: Error message
            package: Package being built
            script: Build script path
            exit_code: Process exit code
            **kwargs: Additional error details
        """
        super().__init__(
            message,
            code="BUILD_ERROR",
            context=ErrorContext(
                operation="build",
                details={
                    'package': package,
                    'script': str(script) if script else None,
                    'exit_code': exit_code,
                    **kwargs
                }
            )
        )


class ConfigError(WrapperError):
    """Configuration-related error."""

    def __init__(
        self,
        message: str,
        config_file: Optional[Path] = None,
        section: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize config error.

        Args:
            message: Error message
            config_file: Configuration file path
            section: Configuration section
            **kwargs: Additional error details
        """
        super().__init__(
            message,
            code="CONFIG_ERROR",
            context=ErrorContext(
                operation="config",
                details={
                    'config_file': str(config_file) if config_file else None,
                    'section': section,
                    **kwargs
                }
            )
        )


class EnvironmentError(WrapperError):
    """Environment setup or validation error."""

    def __init__(
        self,
        message: str,
        variable: Optional[str] = None,
        expected: Optional[str] = None,
        actual: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize environment error.

        Args:
            message: Error message
            variable: Environment variable name
            expected: Expected value
            actual: Actual value
            **kwargs: Additional error details
        """
        super().__init__(
            message,
            code="ENV_ERROR",
            context=ErrorContext(
                operation="environment",
                details={
                    'variable': variable,
                    'expected': expected,
                    'actual': actual,
                    **kwargs
                }
            )
        )


class ProcessError(WrapperError):
    """Process execution or management error."""

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        pid: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize process error.

        Args:
            message: Error message
            command: Command being executed
            exit_code: Process exit code
            pid: Process ID
            **kwargs: Additional error details
        """
        super().__init__(
            message,
            code="PROCESS_ERROR",
            context=ErrorContext(
                operation="process",
                details={
                    'command': command,
                    'exit_code': exit_code,
                    'pid': pid,
                    **kwargs
                }
            )
        )


class ResourceError(WrapperError):
    """Resource limit or management error."""

    def __init__(
        self,
        message: str,
        resource: str,
        limit: Optional[int] = None,
        usage: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize resource error.

        Args:
            message: Error message
            resource: Resource type (memory, cpu, etc.)
            limit: Resource limit
            usage: Current usage
            **kwargs: Additional error details
        """
        super().__init__(
            message,
            code="RESOURCE_ERROR",
            context=ErrorContext(
                operation="resource",
                details={
                    'resource': resource,
                    'limit': limit,
                    'usage': usage,
                    **kwargs
                }
            )
        )


class ValidationError(WrapperError):
    """Input or state validation error."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[str] = None,
        constraint: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field being validated
            value: Invalid value
            constraint: Validation constraint
            **kwargs: Additional error details
        """
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            context=ErrorContext(
                operation="validation",
                details={
                    'field': field,
                    'value': value,
                    'constraint': constraint,
                    **kwargs
                }
            )
        )

