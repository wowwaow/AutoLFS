"""
Error Handler Module

This module provides error handling and recovery coordination for the
LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Type, Union

from loguru import logger

from .error_types import WrapperError
from .recovery import RecoveryResult, RecoveryStrategy


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    error: WrapperError
    strategy: RecoveryStrategy
    actions: List[RecoveryAction]
    success: bool
    start_time: float
    end_time: float
    attempts: int


class ErrorHandler:
    """
    Manages error handling and recovery attempts.

    This class is responsible for:
    - Coordinating error recovery
    - Tracking recovery attempts
    - Managing recovery strategies
    - Logging error handling

    Attributes:
        strategies: Available recovery strategies
        max_attempts: Maximum recovery attempts
        recovery_history: History of recovery attempts
    """

    def __init__(
        self,
        max_attempts: int = 3,
        log_dir: Optional[Union[str, Path]] = None
    ):
        """
        Initialize the error handler.

        Args:
            max_attempts: Maximum recovery attempts per error
            log_dir: Directory for error logs (str or Path)
        """
        self.strategies: Dict[Type[WrapperError], List[RecoveryStrategy]] = {}
        self.max_attempts = max_attempts
        self.recovery_history: List[RecoveryResult] = []
        
        # Handle log directory path
        if log_dir is None:
            self.log_dir = Path.cwd() / "logs"
        elif isinstance(log_dir, str):
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = log_dir
            
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Set up error logging
        logger.add(
            self.log_dir / "error.log",
            rotation="100 MB",
            retention="1 week",
            level="ERROR"
        )

    def register_strategy(
        self,
        error_type: Type[WrapperError],
        strategy: RecoveryStrategy
    ) -> None:
        """
        Register a recovery strategy for an error type.

        Args:
            error_type: Type of error to handle
            strategy: Recovery strategy to apply
        """
        if error_type not in self.strategies:
            self.strategies[error_type] = []
        self.strategies[error_type].append(strategy)

    async def handle_error(
        self,
        error: WrapperError,
        context: Optional[ErrorContext] = None
    ) -> RecoveryResult:
        """
        Handle an error with appropriate recovery strategies.

        Args:
            error: Error to handle
            context: Optional error context

        Returns:
            Result of recovery attempt

        Raises:
            RuntimeError: If no recovery possible
        """
        if context:
            error.context = context

        # Log error occurrence
        logger.error(
            f"Error occurred: {type(error).__name__}\n"
            f"Message: {str(error)}\n"
            f"Context: {error.context}"
        )

        # Find applicable strategies
        strategies = self.strategies.get(type(error), [])
        if not strategies:
            logger.warning(f"No recovery strategies for {type(error).__name__}")
            raise RuntimeError("No recovery strategy available")

        # Try each strategy
        attempts = 0
        start_time = time.time()
        actions = []

        for strategy in strategies:
            if attempts >= self.max_attempts:
                break

            try:
                logger.info(f"Attempting recovery with strategy: {strategy.name}")
                recovery_actions = await strategy.attempt_recovery(error)
                actions.extend(recovery_actions)

                # Check if recovery was successful
                if await strategy.verify_recovery(error):
                    end_time = time.time()
                    result = RecoveryResult(
                        error=error,
                        strategy=strategy,
                        actions=actions,
                        success=True,
                        start_time=start_time,
                        end_time=end_time,
                        attempts=attempts + 1
                    )
                    self.recovery_history.append(result)
                    return result

            except Exception as e:
                logger.error(f"Recovery attempt failed: {e}")

            attempts += 1

        # All recovery attempts failed
        end_time = time.time()
        result = RecoveryResult(
            error=error,
            strategy=strategies[-1],
            actions=actions,
            success=False,
            start_time=start_time,
            end_time=end_time,
            attempts=attempts
        )
        self.recovery_history.append(result)
        return result

    def get_error_history(self) -> List[RecoveryResult]:
        """
        Get history of error recovery attempts.

        Returns:
            List of recovery results
        """
        return self.recovery_history.copy()

    def set_error_policy(
        self,
        error_type: Type[WrapperError],
        policy: str,
        **kwargs
    ) -> None:
        """
        Set error handling policy for an error type.

        Args:
            error_type: Type of error to configure
            policy: Policy name ('retry', 'ignore', etc.)
            **kwargs: Policy-specific configuration
        """
        if policy == "retry":
            self.max_attempts = kwargs.get("max_attempts", 3)
        elif policy == "ignore":
            self.strategies[error_type] = []
        else:
            raise ValueError(f"Unknown error policy: {policy}")

    def clear_history(self) -> None:
        """Clear error handling history."""
        self.recovery_history.clear()

