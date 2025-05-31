"""
Process Management Module

This module provides process management functionality for the
LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import asyncio
import os
import signal
from asyncio import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import psutil
from loguru import logger

from ..errors import ProcessError, ResourceError


@dataclass
class ProcessStatus:
    """Process status information."""
    pid: int
    start_time: datetime
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    cpu_usage: float = 0.0
    memory_usage: int = 0
    io_read: int = 0
    io_write: int = 0
    package: Optional[str] = None


class ManagedProcess:
    """
    Wrapper for a managed subprocess.

    This class provides a high-level interface for process management,
    including resource tracking and limit enforcement.
    """

    def __init__(
        self,
        process: subprocess.Process,
        package: Optional[str] = None,
        limits: Optional[Dict[str, int]] = None
    ):
        """
        Initialize managed process.

        Args:
            process: Subprocess instance
            package: Associated package name
            limits: Resource limits
        """
        self.process = process
        self.package = package
        self.limits = limits or {}
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.exit_code: Optional[int] = None
        self._monitor_task: Optional[asyncio.Task] = None

    @property
    def pid(self) -> int:
        """Get process ID."""
        return self.process.pid

    async def wait(self) -> int:
        """
        Wait for process completion.

        Returns:
            Process exit code
        """
        try:
            self.exit_code = await self.process.wait()
            self.end_time = datetime.now()
            return self.exit_code

        finally:
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

    async def terminate(self, timeout: float = 5.0) -> None:
        """
        Terminate the process.

        Args:
            timeout: Seconds to wait before force kill
        """
        if self.process.returncode is not None:
            return

        try:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout)
                return
            except asyncio.TimeoutError:
                pass

            # Force kill if still running
            self.process.kill()
            await self.process.wait()

        finally:
            self.end_time = datetime.now()
            if self._monitor_task:
                self._monitor_task.cancel()

    def get_status(self) -> ProcessStatus:
        """
        Get process status.

        Returns:
            ProcessStatus object
        """
        return ProcessStatus(
            pid=self.pid,
            start_time=self.start_time,
            end_time=self.end_time,
            exit_code=self.exit_code,
            package=self.package
        )


class ProcessManager:
    """
    Manages build process execution and monitoring.

    This class is responsible for:
    - Process creation and cleanup
    - Resource monitoring
    - Limit enforcement
    - Process status tracking
    """

    def __init__(self):
        """Initialize process manager."""
        self.active_processes: Dict[int, ManagedProcess] = {}
        self._monitor_task: Optional[asyncio.Task] = None

    async def create_process(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        package: Optional[str] = None,
        limits: Optional[Dict[str, int]] = None
    ) -> ManagedProcess:
        """
        Create and start a new managed process.

        Args:
            cmd: Command and arguments
            cwd: Working directory
            env: Environment variables
            package: Associated package name
            limits: Resource limits

        Returns:
            ManagedProcess instance

        Raises:
            ProcessError: If process creation fails
        """
        try:
            # Create process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Create managed wrapper
            managed = ManagedProcess(process, package, limits)
            self.active_processes[process.pid] = managed

            # Start monitoring
            managed._monitor_task = asyncio.create_task(
                self._monitor_process(managed)
            )

            logger.debug(
                f"Started process {process.pid} "
                f"for package: {package}"
            )
            return managed

        except Exception as e:
            raise ProcessError(
                f"Failed to create process: {e}",
                command=cmd[0],
                details={'error': str(e)}
            )

    async def cleanup_process(self, package: str) -> None:
        """
        Clean up processes for a package.

        Args:
            package: Package name
        """
        processes = [
            p for p in self.active_processes.values()
            if p.package == package
        ]

        for process in processes:
            try:
                await process.terminate()
                self.active_processes.pop(process.pid, None)
            except Exception as e:
                logger.error(
                    f"Failed to cleanup process {process.pid}: {e}"
                )

    async def cleanup(self) -> None:
        """Clean up all managed processes."""
        for process in list(self.active_processes.values()):
            try:
                await process.terminate()
            except Exception as e:
                logger.error(
                    f"Failed to cleanup process {process.pid}: {e}"
                )

        self.active_processes.clear()

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_process(self, process: ManagedProcess) -> None:
        """
        Monitor process resource usage.

        Args:
            process: Process to monitor
        """
        try:
            ps_process = psutil.Process(process.pid)
            
            while process.process.returncode is None:
                try:
                    with ps_process.oneshot():
                        cpu_percent = ps_process.cpu_percent()
                        memory_info = ps_process.memory_info()
                        io_counters = ps_process.io_counters()

                        # Check resource limits
                        if process.limits:
                            if (
                                'memory' in process.limits and
                                memory_info.rss > process.limits['memory']
                            ):
                                raise ResourceError(
                                    "Process exceeded memory limit",
                                    resource="memory",
                                    limit=process.limits['memory'],
                                    usage=memory_info.rss
                                )

                        # Update process metrics
                        status = process.get_status()
                        status.cpu_usage = cpu_percent
                        status.memory_usage = memory_info.rss
                        status.io_read = io_counters.read_bytes
                        status.io_write = io_counters.write_bytes

                await asyncio.sleep(1.0)

        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            logger.error(f"Process monitoring failed: {e}")
            await process.terminate()

    def get_process_status(self, pid: int) -> Optional[ProcessStatus]:
        """
        Get status of a managed process.

        Args:
            pid: Process ID

        Returns:
            ProcessStatus if found, None otherwise
        """
        if pid in self.active_processes:
            return self.active_processes[pid].get_status()
        return None

