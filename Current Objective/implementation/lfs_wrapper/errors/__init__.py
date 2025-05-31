"""
Error Handling Package

This package provides error handling and recovery functionality for
the LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

from .error_types import (
    BuildError,
    ConfigError,
    EnvironmentError,
    ProcessError,
    ResourceError,
    ValidationError,
    WrapperError,
    ErrorContext
)
from .error_handler import ErrorHandler
from .recovery import (
    RecoveryAction,
    RecoveryResult,
    RecoveryStrategy,
    RetryStrategy,
    CleanupStrategy,
    EnvironmentResetStrategy
)

__all__ = [
    # Error Types
    'BuildError',
    'ConfigError',
    'EnvironmentError',
    'ProcessError',
    'ResourceError',
    'ValidationError',
    'WrapperError',
    'ErrorContext',

    # Error Handler
    'ErrorHandler',

    # Recovery Components
    'RecoveryAction',
    'RecoveryResult',
    'RecoveryStrategy',
    'RetryStrategy',
    'CleanupStrategy',
    'EnvironmentResetStrategy'
]

