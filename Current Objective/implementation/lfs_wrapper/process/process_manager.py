"""
Process Management Module

This module provides functionality for managing build processes and system
resources in the LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import asyncio
import os
import resource
import signal
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import psutil
from loguru import logger

from .resource_monitor import ResourceLimits, ResourceMonitor


@dataclass
class ResourceUsage:
    """Resource usage information for a process."""
    memory_rss: int = 0
    memory_vms: int = 0
    cpu_percent: float = 0.0
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    num_threads: int = 0
    num_fds: int = 0


@dataclass
class ProcessStatus:
    """Status information for a managed process."""
    pid: int
    exit_code: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    peak_memory: Optional[int] = None
    peak_cpu: Optional[float] = None
    error_message: Optional[str] = None


class ProcessManager:
    """
    Manages build processes and system resources.

    This class is responsible for:
    - Spawning and monitoring build processes
    - Managing system resources and limits
    - Tracking process status and performance
    - Cleaning up processes and resources

    Attributes:
        active_processes: Currently running processes
        resource_monitor: System resource monitor
        process_statuses: Status information for processes
    """

    def __init__(self):
        """Initialize the process manager."""
        self.active_processes: Set[int] = set()
        self.resource_monitor = ResourceMonitor()
        self.process_statuses: Dict[int, ProcessStatus] = {}

    async def start_process(
        self,
        command: str,
        work_dir: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        limits: Optional[ResourceLimits] = None
    ) -> ProcessStatus:
        """
        Start a new process with resource management.

        Args:
            command: Command to execute
            work_dir: Working directory for process
            env: Environment variables
            limits: Resource limits to apply

        Returns:
            ProcessStatus for the new process

        Raises:
            OSError: If process creation fails
        """
        try:
            # Set up resource limits
            if limits:
                self._apply_resource_limits(limits)

            # Create process
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=env
            )

            # Initialize monitoring
            status = ProcessStatus(
                pid=process.pid,
                start_time=datetime.now()
            )
            self.process_statuses[process.pid] = status
            self.active_processes.add(process.pid)

            # Start resource monitoring
            await self.resource_monitor.start_monitoring(process.pid)

            return status

        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            raise OSError(f"Process creation failed: {e}")

    async def monitor_process(self, pid: int) -> ProcessStatus:
        """
        Monitor a running process.

        Args:
            pid: Process ID to monitor

        Returns:
            Updated ProcessStatus

        Raises:
            ValueError: If process not found
        """
        if pid not in self.active_processes:
            raise ValueError(f"Process {pid} not found")

        try:
            process = psutil.Process(pid)
            status = self.process_statuses[pid]

            # Monitor process state
            while process.is_running():
                # Update resource usage
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()

                # Update peak values
                if status.peak_cpu is None or cpu_percent > status.peak_cpu:
                    status.peak_cpu = cpu_percent
                if status.peak_memory is None or memory_info.rss > status.peak_memory:
                    status.peak_memory = memory_info.rss

                await asyncio.sleep(1)

            # Process completed
            status.end_time = datetime.now()
            status.exit_code = process.wait()
            self.active_processes.remove(pid)

            return status

        except psutil.NoSuchProcess:
            logger.error(f"Process {pid} no longer exists")
            self.active_processes.remove(pid)
            raise ValueError(f"Process {pid} not found")

    def _apply_resource_limits(self, limits: ResourceLimits) -> None:
        """
        Apply resource limits to the current process.

        Args:
            limits: Resource limits to apply
        """
        if limits.max_memory:
            resource.setrlimit(
                resource.RLIMIT_AS,
                (limits.max_memory, limits.max_memory)
            )
        if limits.max_files:
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (limits.max_files, limits.max_files)
            )
        if limits.max_processes:
            resource.setrlimit(
                resource.RLIMIT_NPROC,
                (limits.max_processes, limits.max_processes)
            )

    async def terminate_process(
        self,
        pid: int,
        timeout: float = 5.0
    ) -> ProcessStatus:
        """
        Terminate a process with cleanup.

        Args:
            pid: Process ID to terminate
            timeout: Seconds to wait for graceful termination

        Returns:
            Final ProcessStatus

        Raises:
            ValueError: If process not found
        """
        if pid not in self.active_processes:
            raise ValueError(f"Process {pid} not found")

        try:
            process = psutil.Process(pid)
            status = self.process_statuses[pid]

            # Try graceful termination
            process.terminate()
            try:
                process.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                # Force kill if timeout
                process.kill()
                status.error_message = "Process killed after timeout"

            status.end_time = datetime.now()
            status.exit_code = process.wait()
            self.active_processes.remove(pid)

            # Stop monitoring
            await self.resource_monitor.stop_monitoring(pid)

            return status

        except psutil.NoSuchProcess:
            logger.error(f"Process {pid} no longer exists")
            self.active_processes.remove(pid)
            raise ValueError(f"Process {pid} not found")

    async def cleanup(self) -> None:
        """Clean up all managed processes and resources."""
        # Terminate all active processes
        for pid in list(self.active_processes):
            try:
                await self.terminate_process(pid)
            except ValueError:
                continue

        # Stop all monitoring
        await self.resource_monitor.cleanup()

        # Clear internal state
        self.active_processes.clear()
        self.process_statuses.clear()

    def is_process_running(self, pid: int) -> bool:
        """
        Check if a process is still running.

        Args:
            pid: Process ID to check

        Returns:
            bool indicating if process is running
        """
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except psutil.NoSuchProcess:
            return False

    def get_resource_usage(self, pid: int) -> Optional[Dict[str, float]]:
        """
        Get current resource usage for a process.

        Args:
            pid: Process ID to check

        Returns:
            Dict with resource usage or None if process not found
        """
        try:
            process = psutil.Process(pid)
            mem_info = process.memory_info()
            io_info = process.io_counters()
            return ResourceUsage(
                memory_rss=mem_info.rss,
                memory_vms=mem_info.vms,
                cpu_percent=process.cpu_percent(),
                io_read_bytes=io_info.read_bytes,
                io_write_bytes=io_info.write_bytes,
                num_threads=process.num_threads(),
                num_fds=process.num_fds()
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

