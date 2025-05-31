"""
Recovery Strategies Module

This module provides recovery strategies for various error conditions in
the LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from loguru import logger

from .exceptions import WrapperError


@dataclass
class RecoveryAction:
    """Record of a recovery action taken."""
    action_type: str
    description: str
    success: bool
    details: Optional[str] = None


class RecoveryStrategy(ABC):
    """
    Base class for recovery strategies.

    This class defines the interface for implementing recovery strategies
    for different types of errors.
    """

    def __init__(self, name: str):
        """
        Initialize recovery strategy.

        Args:
            name: Strategy name
        """
        self.name = name
        self.actions: List[RecoveryAction] = []

    @abstractmethod
    async def attempt_recovery(
        self,
        error: WrapperError
    ) -> List[RecoveryAction]:
        """
        Attempt to recover from an error.

        Args:
            error: Error to recover from

        Returns:
            List of recovery actions taken

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    async def verify_recovery(self, error: WrapperError) -> bool:
        """
        Verify recovery was successful.

        Args:
            error: Error that was recovered from

        Returns:
            bool indicating if recovery was successful

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError


class BuildDirectoryRecovery(RecoveryStrategy):
    """Recovery strategy for build directory issues."""

    def __init__(self):
        """Initialize build directory recovery strategy."""
        super().__init__("BuildDirectoryRecovery")

    async def attempt_recovery(
        self,
        error: WrapperError
    ) -> List[RecoveryAction]:
        """
        Attempt to recover build directory.

        Args:
            error: Error to recover from

        Returns:
            List of recovery actions taken
        """
        if not error.context or "build_dir" not in error.context.details:
            return []

        build_dir = Path(error.context.details["build_dir"])
        actions = []

        # Clean build directory
        try:
            shutil.rmtree(build_dir)
            actions.append(RecoveryAction(
                action_type="cleanup",
                description=f"Removed build directory: {build_dir}",
                success=True
            ))
        except Exception as e:
            actions.append(RecoveryAction(
                action_type="cleanup",
                description=f"Failed to remove build directory: {build_dir}",
                success=False,
                details=str(e)
            ))
            return actions

        # Recreate build directory
        try:
            build_dir.mkdir(parents=True)
            actions.append(RecoveryAction(
                action_type="create",
                description=f"Created new build directory: {build_dir}",
                success=True
            ))
        except Exception as e:
            actions.append(RecoveryAction(
                action_type="create",
                description=f"Failed to create build directory: {build_dir}",
                success=False,
                details=str(e)
            ))

        return actions

    async def verify_recovery(self, error: WrapperError) -> bool:
        """
        Verify build directory recovery.

        Args:
            error: Error that was recovered from

        Returns:
            bool indicating if recovery was successful
        """
        if not error.context or "build_dir" not in error.context.details:
            return False

        build_dir = Path(error.context.details["build_dir"])
        return (
            build_dir.exists() and
            build_dir.is_dir() and
            os.access(build_dir, os.R_OK | os.W_OK | os.X_OK)
        )


class EnvironmentRecovery(RecoveryStrategy):
    """Recovery strategy for environment issues."""

    def __init__(self):
        """Initialize environment recovery strategy."""
        super().__init__("EnvironmentRecovery")

    async def attempt_recovery(
        self,
        error: WrapperError
    ) -> List[RecoveryAction]:
        """
        Attempt to recover environment.

        Args:
            error: Error to recover from

        Returns:
            List of recovery actions taken
        """
        if not error.context:
            return []

        actions = []

        # Reset environment variables
        try:
            os.environ.clear()
            os.environ.update({
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "HOME": os.path.expanduser("~"),
                "USER": os.getlogin(),
                "LANG": "C.UTF-8"
            })
            actions.append(RecoveryAction(
                action_type="reset",
                description="Reset environment variables",
                success=True
            ))
        except Exception as e:
            actions.append(RecoveryAction(
                action_type="reset",
                description="Failed to reset environment",
                success=False,
                details=str(e)
            ))

        return actions

    async def verify_recovery(self, error: WrapperError) -> bool:
        """
        Verify environment recovery.

        Args:
            error: Error that was recovered from

        Returns:
            bool indicating if recovery was successful
        """
        required_vars = {"PATH", "HOME", "USER", "LANG"}
        return all(var in os.environ for var in required_vars)

