"""
Error Handling Package

This package provides error handling and recovery functionality for the
LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

from .exceptions import (
    BuildError,
    ConfigError,
    EnvironmentError,
    ResourceError,
    ValidationError,
)
from .error_handler import ErrorHandler, RecoveryResult
from .error_manager import ErrorManager
from .recovery_strategies import RecoveryStrategy, RecoveryAction

__all__ = [
    'BuildError',
    'ConfigError',
    'EnvironmentError',
    'ResourceError',
    'ValidationError',
    'ErrorHandler',
    'RecoveryResult',
    'ErrorManager',
    'RecoveryStrategy',
    'RecoveryAction',
]

