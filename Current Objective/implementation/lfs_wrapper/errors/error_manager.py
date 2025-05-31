"""
Error Management Module

This module provides centralized error management and tracking for the
LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Type

from loguru import logger

from .error_handler import ErrorHandler, RecoveryResult
from .exceptions import ErrorContext, WrapperError


class ErrorManager:
    """
    Manages system-wide error handling and tracking.

    This class is responsible for:
    - Tracking active errors
    - Managing error handlers
    - Coordinating recovery attempts
    - Generating error reports

    Attributes:
        handlers: Active error handlers
        active_errors: Currently active errors
        error_history: Historical error data
    """

    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize the error manager.

        Args:
            log_dir: Directory for error logs
        """
        self.handlers: Dict[Type[WrapperError], ErrorHandler] = {}
        self.active_errors: Set[WrapperError] = set()
        self.error_history: List[RecoveryResult] = []
        self.log_dir = log_dir

    def register_handler(
        self,
        error_type: Type[WrapperError],
        handler: ErrorHandler
    ) -> None:
        """
        Register an error handler.

        Args:
            error_type: Type of error to handle
            handler: Handler to register
        """
        self.handlers[error_type] = handler

    async def handle_error(
        self,
        error: WrapperError,
        context: Optional[ErrorContext] = None
    ) -> RecoveryResult:
        """
        Handle an error with appropriate handler.

        Args:
            error: Error to handle
            context: Optional error context

        Returns:
            Result of recovery attempt

        Raises:
            RuntimeError: If no handler available
        """
        # Find appropriate handler
        handler = None
        for error_type, h in self.handlers.items():
            if isinstance(error, error_type):
                handler = h
                break

        if not handler:
            raise RuntimeError(f"No handler for {type(error).__name__}")

        # Track error
        self.active_errors.add(error)

        try:
            # Attempt recovery
            result = await handler.handle_error(error, context)
            self.error_history.append(result)
            return result

        finally:
            # Remove from active errors
            self.active_errors.remove(error)

    def generate_error_report(self, error: WrapperError) -> Dict:
        """
        Generate detailed error report.

        Args:
            error: Error to report

        Returns:
            Dict containing error details
        """
        # Get error context
        context = error.context or ErrorContext(
            location="unknown",
            operation="unknown",
            details={},
            timestamp=datetime.now().timestamp()
        )

        # Get recovery attempts
        recovery_attempts = [
            result for result in self.error_history
            if result.error == error
        ]

        return {
            'error_type': type(error).__name__,
            'message': str(error),
            'location': context.location,
            'operation': context.operation,
            'details': context.details,
            'timestamp': datetime.fromtimestamp(context.timestamp).isoformat(),
            'recoverable': context.recoverable,
            'recovery_attempted': bool(recovery_attempts),
            'recovery_successful': any(r.success for r in recovery_attempts),
            'recovery_attempts': len(recovery_attempts),
            'recovery_duration': sum(
                (r.end_time - r.start_time)
                for r in recovery_attempts
            ) if recovery_attempts else 0
        }

    def get_active_errors(self) -> Set[WrapperError]:
        """
        Get currently active errors.

        Returns:
            Set of active errors
        """
        return self.active_errors.copy()

    def get_error_statistics(
        self,
        days: int = 7
    ) -> Dict:
        """
        Get error statistics for a time period.

        Args:
            days: Number of days to analyze

        Returns:
            Dict containing error statistics
        """
        cutoff = datetime.now() - timedelta(days=days)
        recent_errors = [
            result for result in self.error_history
            if datetime.fromtimestamp(result.start_time) > cutoff
        ]

        return {
            'total_errors': len(recent_errors),
            'successful_recoveries': sum(1 for r in recent_errors if r.success),
            'failed_recoveries': sum(1 for r in recent_errors if not r.success),
            'average_attempts': sum(r.attempts for r in recent_errors) / len(recent_errors) if recent_errors else 0,
            'average_recovery_time': sum(
                (r.end_time - r.start_time)
                for r in recent_errors if r.success
            ) / sum(1 for r in recent_errors if r.success) if any(r.success for r in recent_errors) else 0
        }

    async def cleanup(self) -> None:
        """Clean up error management state."""
        # Clear active errors
        self.active_errors.clear()

        # Clear history
        self.error_history.clear()

        # Clean up handlers
        for handler in self.handlers.values():
            handler.clear_history()

