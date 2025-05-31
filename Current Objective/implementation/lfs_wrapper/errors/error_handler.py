"""
Error Handler Module

This module provides error handling and recovery coordination for the
LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type

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
from .recovery import (
    RecoveryAction,
    RecoveryResult,
    RecoveryStrategy,
    RetryStrategy,
    CleanupStrategy
)


class ErrorHandler:
    """
    Manages error handling and recovery strategies.

    This class is responsible for:
    - Coordinating error recovery
    - Managing recovery strategies
    - Tracking recovery attempts
    - Logging error handling
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        max_attempts: int = 3
    ):
        """
        Initialize error handler.

        Args:
            log_dir: Directory for error logs
            max_attempts: Maximum recovery attempts
        """
        self.log_dir = Path(log_dir) if log_dir else Path.cwd() / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configure error logging
        logger.add(
            self.log_dir / "error.log",
            rotation="100 MB",
            retention="1 week",
            level="ERROR"
        )

        # Initialize recovery tracking
        self.max_attempts = max_attempts
        self.recovery_history: List[RecoveryResult] = []
        self.strategies: Dict[Type[WrapperError], List[RecoveryStrategy]] = {}

        # Set up default strategies
        self._setup_default_strategies()

    def set_error_policy(
        self,
        error_type: Type[WrapperError],
        policy: str,
        **options
    ) -> None:
        """
        Set error handling policy.

        Args:
            error_type: Type of error
            policy: Policy name
            **options: Policy options
        """
        if policy == "retry":
            strategy = RetryStrategy(
                max_attempts=options.get('max_attempts', self.max_attempts),
                delay=options.get('delay', 1.0)
            )
        elif policy == "cleanup":
            strategy = CleanupStrategy(
                cleanup_dirs=options.get('cleanup_dirs', [])
            )
        else:
            raise ValueError(f"Unknown policy: {policy}")

        self.strategies[error_type] = [strategy]

    async def handle_error(
        self,
        error: WrapperError,
        **kwargs
    ) -> RecoveryResult:
        """
        Handle an error with recovery attempts.

        Args:
            error: Error to handle
            **kwargs: Recovery options

        Returns:
            Recovery result

        Raises:
            RuntimeError: If no recovery possible
        """
        start_time = time.time()
        recovery_actions = []

        # Log error occurrence
        logger.error(
            f"Error occurred: {type(error).__name__}\n"
            f"Message: {str(error)}\n"
            f"Context: {error.context.details}"
        )

        # Get applicable strategies
        strategies = self.strategies.get(type(error), [])
        if not strategies:
            logger.warning(f"No recovery strategies for {type(error).__name__}")
            return RecoveryResult(
                error=error,
                success=False,
                recovery_attempted=False,
                actions=[],
                timestamp=datetime.now()
            )

        # Try each strategy
        for strategy in strategies:
            try:
                logger.info(f"Attempting recovery with strategy: {strategy.__class__.__name__}")
                actions = await strategy.attempt_recovery(error, **kwargs)
                recovery_actions.extend(actions)

                if await strategy.verify_recovery(error):
                    result = RecoveryResult(
                        error=error,
                        success=True,
                        recovery_attempted=True,
                        actions=recovery_actions,
                        timestamp=datetime.now()
                    )
                    self.recovery_history.append(result)
                    return result

            except Exception as e:
                logger.error(f"Recovery attempt failed: {e}")
                recovery_actions.append(
                    RecoveryAction(
                        timestamp=datetime.now(),
                        action_type="recovery_failed",
                        description=str(e),
                        success=False
                    )
                )

        # All recovery attempts failed
        result = RecoveryResult(
            error=error,
            success=False,
            recovery_attempted=True,
            actions=recovery_actions,
            timestamp=datetime.now()
        )
        self.recovery_history.append(result)
        return result

    def get_error_history(self) -> List[RecoveryResult]:
        """
        Get error handling history.

        Returns:
            List of recovery results
        """
        return self.recovery_history.copy()

    def _setup_default_strategies(self) -> None:
        """Set up default recovery strategies."""
        # Build errors: retry and cleanup
        self.strategies[BuildError] = [
            RetryStrategy(max_attempts=self.max_attempts),
            CleanupStrategy()
        ]

        # Process errors: retry
        self.strategies[ProcessError] = [
            RetryStrategy(max_attempts=self.max_attempts)
        ]

        # Resource errors: cleanup
        self.strategies[ResourceError] = [
            CleanupStrategy()
        ]

    async def cleanup(self) -> None:
        """Clean up error handling resources."""
        try:
            # Clear history
            self.recovery_history.clear()
            self.strategies.clear()

        except Exception as e:
            logger.error(f"Error handler cleanup failed: {e}")
            raise

