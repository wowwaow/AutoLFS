"""
Resource Monitoring Module

This module provides system resource monitoring and management functionality
for the LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, Optional, Set

import psutil
from loguru import logger


@dataclass
class ResourceLimits:
    """System resource limits configuration."""
    max_memory: Optional[int] = None  # bytes
    max_cpu: Optional[float] = None   # percentage
    max_files: Optional[int] = None   # file descriptors
    max_processes: Optional[int] = None  # child processes


@dataclass
class ResourceUsage:
    """Resource usage information."""
    cpu_percent: float = 0.0
    memory_rss: int = 0
    memory_vms: int = 0
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    num_threads: int = 0
    num_fds: int = 0


class ResourceMonitor:
    """
    Monitors and tracks system resource usage.

    This class is responsible for:
    - Monitoring process resource usage
    - Tracking system-wide resources
    - Detecting resource limits
    - Collecting usage statistics

    Attributes:
        monitored_processes: Set of monitored process IDs
        usage_history: Historical resource usage data
    """

    def __init__(self):
        """Initialize the resource monitor."""
        self.monitored_processes: Set[int] = set()
        self.usage_history: Dict[int, List[ResourceUsage]] = {}
        self._monitoring_tasks: Dict[int, asyncio.Task] = {}

    async def start_monitoring(
        self,
        pid: int,
        interval: float = 1.0
    ) -> None:
        """
        Start monitoring a process.

        Args:
            pid: Process ID to monitor
            interval: Monitoring interval in seconds
        """
        if pid in self.monitored_processes:
            return

        self.monitored_processes.add(pid)
        self.usage_history[pid] = []

        # Start monitoring task
        task = asyncio.create_task(
            self._monitor_process(pid, interval)
        )
        self._monitoring_tasks[pid] = task

    async def stop_monitoring(self, pid: int) -> None:
        """
        Stop monitoring a process.

        Args:
            pid: Process ID to stop monitoring
        """
        if pid not in self.monitored_processes:
            return

        # Cancel monitoring task
        if pid in self._monitoring_tasks:
            task = self._monitoring_tasks.pop(pid)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.monitored_processes.remove(pid)

    async def _monitor_process(
        self,
        pid: int,
        interval: float
    ) -> None:
        """
        Monitor a single process's resource usage.

        Args:
            pid: Process ID to monitor
            interval: Monitoring interval in seconds
        """
        try:
            process = psutil.Process(pid)
            while True:
                usage = ResourceUsage(
                    cpu_percent=process.cpu_percent(),
                    memory_rss=process.memory_info().rss,
                    memory_vms=process.memory_info().vms,
                    io_read_bytes=process.io_counters().read_bytes,
                    io_write_bytes=process.io_counters().write_bytes,
                    num_threads=process.num_threads(),
                    num_fds=process.num_fds()
                )
                self.usage_history[pid].append(usage)
                await asyncio.sleep(interval)

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"Failed to monitor process {pid}: {e}")
            await self.stop_monitoring(pid)

    def get_current_usage(self, pid: int) -> Optional[ResourceUsage]:
        """
        Get current resource usage for a process.

        Args:
            pid: Process ID to check

        Returns:
            Current ResourceUsage or None if not monitored
        """
        if pid not in self.monitored_processes:
            return None

        history = self.usage_history.get(pid, [])
        return history[-1] if history else None

    def get_peak_usage(self, pid: int) -> Optional[ResourceUsage]:
        """
        Get peak resource usage for a process.

        Args:
            pid: Process ID to check

        Returns:
            Peak ResourceUsage or None if not monitored
        """
        if pid not in self.monitored_processes:
            return None

        history = self.usage_history.get(pid, [])
        if not history:
            return None

        return ResourceUsage(
            cpu_percent=max(u.cpu_percent for u in history),
            memory_rss=max(u.memory_rss for u in history),
            memory_vms=max(u.memory_vms for u in history),
            io_read_bytes=max(u.io_read_bytes for u in history),
            io_write_bytes=max(u.io_write_bytes for u in history),
            num_threads=max(u.num_threads for u in history),
            num_fds=max(u.num_fds for u in history)
        )

    async def cleanup(self) -> None:
        """Clean up all monitoring tasks and data."""
        # Stop all monitoring tasks
        for pid in list(self.monitored_processes):
            await self.stop_monitoring(pid)

        # Clear data
        self.usage_history.clear()
        self._monitoring_tasks.clear()

    def is_monitoring(self, pid: int) -> bool:
        """
        Check if a process is being monitored.

        Args:
            pid: Process ID to check

        Returns:
            bool indicating if process is monitored
        """
        return pid in self.monitored_processes

