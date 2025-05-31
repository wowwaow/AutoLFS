"""
Error Exception Classes

This module defines the custom exception classes used in the LFS/BLFS
build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ErrorContext:
    """Context information for an error."""
    location: str
    operation: str
    details: Dict[str, Any]
    timestamp: float
    recoverable: bool = True


class WrapperError(Exception):
    """Base class for all wrapper system errors."""

    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None
    ):
        """
        Initialize error with optional context.

        Args:
            message: Error message
            context: Optional error context
        """
        super().__init__(message)
        self.context = context
        self.recovery_attempted = False
        self.recovery_successful = False


class BuildError(WrapperError):
    """Error occurring during build process."""
    pass


class ConfigError(WrapperError):
    """Error in configuration handling."""
    pass


class EnvironmentError(WrapperError):
    """Error in environment setup or validation."""
    pass


class ResourceError(WrapperError):
    """Error related to system resources."""
    pass


class ValidationError(WrapperError):
    """Error in data validation."""
    pass

