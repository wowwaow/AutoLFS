"""
Recovery Module

This module provides error recovery functionality for the
LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type, Any

from loguru import logger

from .error_types import (
    BuildError,
    ConfigError,
    EnvironmentError,
    ProcessError,
    ResourceError,
    ValidationError,
    WrapperError
)


@dataclass
class RecoveryAction:
    """Record of a recovery action taken."""
    timestamp: datetime
    action_type: str
    description: str
    success: bool = False
    details: Optional[Dict[str, Any]] = None


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    error: WrapperError
    success: bool
    recovery_attempted: bool
    actions: List[RecoveryAction]
    timestamp: datetime
    attempts: int = 0
    recovery_time: float = 0.0
    message: Optional[str] = None

    def __post_init__(self):
        """Initialize computed fields."""
        if not self.actions:
            self.actions = []
        if not self.timestamp:
            self.timestamp = datetime.now()

    @property
    def latest_action(self) -> Optional[RecoveryAction]:
        """Get most recent recovery action."""
        return self.actions[-1] if self.actions else None

    def add_action(self, action: RecoveryAction) -> None:
        """
        Add a recovery action.

        Args:
            action: Action to add
        """
        self.actions.append(action)
        self.attempts += 1

    def get_successful_actions(self) -> List[RecoveryAction]:
        """
        Get successful recovery actions.

        Returns:
            List of successful actions
        """
        return [
            action for action in self.actions
            if action.success
        ]

    def get_action_summary(self) -> str:
        """
        Get summary of recovery actions.

        Returns:
            Summary string
        """
        return "\n".join(
            f"[{action.timestamp}] {action.action_type}: {action.description}"
            for action in self.actions
        )


class RecoveryStrategy(ABC):
    """Base class for error recovery strategies."""

    def __init__(self, name: str, description: str):
        """
        Initialize recovery strategy.

        Args:
            name: Strategy name
            description: Strategy description
        """
        self.name = name
        self.description = description
        self.actions: List[RecoveryAction] = []

    @abstractmethod
    async def attempt_recovery(
        self,
        error: WrapperError,
        **kwargs
    ) -> List[RecoveryAction]:
        """
        Attempt to recover from an error.

        Args:
            error: Error to recover from
            **kwargs: Recovery options

        Returns:
            List of recovery actions taken
        """
        pass

    @abstractmethod
    async def verify_recovery(self, error: WrapperError) -> bool:
        """
        Verify recovery was successful.

        Args:
            error: Original error

        Returns:
            bool indicating success
        """
        pass

    def _record_action(
        self,
        action_type: str,
        description: str,
        success: bool = True,
        **details
    ) -> RecoveryAction:
        """
        Record a recovery action.

        Args:
            action_type: Type of action
            description: Action description
            success: Whether action succeeded
            **details: Additional details

        Returns:
            Recorded action
        """
        action = RecoveryAction(
            timestamp=datetime.now(),
            action_type=action_type,
            description=description,
            success=success,
            details=details
        )
        self.actions.append(action)
        return action


class RetryStrategy(RecoveryStrategy):
    """Simple retry strategy."""

    def __init__(self, max_attempts: int = 3, delay: float = 1.0):
        """
        Initialize retry strategy.

        Args:
            max_attempts: Maximum retry attempts
            delay: Delay between attempts
        """
        super().__init__(
            name="retry",
            description="Retry the failed operation"
        )
        self.max_attempts = max_attempts
        self.delay = delay

    async def attempt_recovery(
        self,
        error: WrapperError,
        **kwargs
    ) -> List[RecoveryAction]:
        """
        Attempt recovery by retrying.

        Args:
            error: Error to recover from
            **kwargs: Recovery options

        Returns:
            List of recovery actions
        """
        import asyncio

        for attempt in range(self.max_attempts):
            try:
                # Wait before retry
                await asyncio.sleep(self.delay)
                
                self._record_action(
                    "retry",
                    f"Retry attempt {attempt + 1}",
                    attempt=attempt + 1
                )
                
                # Attempt operation based on error type
                if isinstance(error, BuildError):
                    await self._retry_build(error)
                elif isinstance(error, ProcessError):
                    await self._retry_process(error)
                
                return self.actions

            except Exception as e:
                logger.warning(f"Retry attempt {attempt + 1} failed: {e}")
                self._record_action(
                    "retry_failed",
                    f"Retry attempt {attempt + 1} failed: {e}",
                    success=False,
                    error=str(e)
                )

        return self.actions

    async def verify_recovery(self, error: WrapperError) -> bool:
        """
        Verify recovery success.

        Args:
            error: Original error

        Returns:
            bool indicating success
        """
        return any(action.success for action in self.actions)

    async def _retry_build(self, error: BuildError) -> None:
        """Retry a failed build."""
        # Implementation would retry the build
        pass

    async def _retry_process(self, error: ProcessError) -> None:
        """Retry a failed process."""
        # Implementation would retry the process
        pass


class CleanupStrategy(RecoveryStrategy):
    """Recovery through cleanup and reset."""

    def __init__(self, cleanup_dirs: Optional[List[Path]] = None):
        """
        Initialize cleanup strategy.

        Args:
            cleanup_dirs: Directories to clean
        """
        super().__init__(
            name="cleanup",
            description="Clean up and reset state"
        )
        self.cleanup_dirs = cleanup_dirs or []

    async def attempt_recovery(
        self,
        error: WrapperError,
        **kwargs
    ) -> List[RecoveryAction]:
        """
        Attempt recovery through cleanup.

        Args:
            error: Error to recover from
            **kwargs: Recovery options

        Returns:
            List of recovery actions
        """
        try:
            if isinstance(error, BuildError):
                await self._cleanup_build(error)
            elif isinstance(error, ResourceError):
                await self._cleanup_resources(error)
            
            # Clean specified directories
            for directory in self.cleanup_dirs:
                if directory.exists():
                    shutil.rmtree(directory)
                    self._record_action(
                        "cleanup",
                        f"Cleaned directory: {directory}",
                        directory=str(directory)
                    )

            return self.actions

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            self._record_action(
                "cleanup_failed",
                f"Cleanup failed: {e}",
                success=False,
                error=str(e)
            )
            return self.actions

    async def verify_recovery(self, error: WrapperError) -> bool:
        """
        Verify cleanup success.

        Args:
            error: Original error

        Returns:
            bool indicating success
        """
        # Check if all specified directories are clean
        for directory in self.cleanup_dirs:
            if directory.exists() and any(directory.iterdir()):
                return False
        return True

    async def _cleanup_build(self, error: BuildError) -> None:
        """Clean up failed build artifacts."""
        # Implementation would clean build directory
        pass

    async def _cleanup_resources(self, error: ResourceError) -> None:
        """Clean up resource usage."""
        # Implementation would clean up resources
        pass


class EnvironmentResetStrategy(RecoveryStrategy):
    """Recovery by resetting environment."""

    def __init__(self, preserve_vars: Optional[List[str]] = None):
        """
        Initialize environment reset strategy.

        Args:
            preserve_vars: Variables to preserve
        """
        super().__init__(
            name="env_reset",
            description="Reset environment variables"
        )
        self.preserve_vars = preserve_vars or []

    async def attempt_recovery(
        self,
        error: WrapperError,
        **kwargs
    ) -> List[RecoveryAction]:
        """
        Attempt recovery by resetting environment.

        Args:
            error: Error to recover from
            **kwargs: Recovery options

        Returns:
            List of recovery actions
        """
        try:
            if isinstance(error, EnvironmentError):
                await self._reset_environment(error)
            return self.actions

        except Exception as e:
            logger.error(f"Environment reset failed: {e}")
            self._record_action(
                "reset_failed",
                f"Environment reset failed: {e}",
                success=False,
                error=str(e)
            )
            return self.actions

    async def verify_recovery(self, error: WrapperError) -> bool:
        """
        Verify environment reset.

        Args:
            error: Original error

        Returns:
            bool indicating success
        """
        if isinstance(error, EnvironmentError):
            return error.context.details.get('variable') not in os.environ
        return True

    async def _reset_environment(self, error: EnvironmentError) -> None:
        """Reset environment variables."""
        import os
        
        # Save preserved variables
        preserved = {}
        for var in self.preserve_vars:
            if var in os.environ:
                preserved[var] = os.environ[var]
        
        # Clear environment
        os.environ.clear()
        
        # Restore preserved variables
        os.environ.update(preserved)
        
        self._record_action(
            "env_reset",
            "Reset environment variables",
            preserved_vars=list(preserved.keys())
        )

