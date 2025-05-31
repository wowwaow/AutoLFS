"""
Metrics Collection Module

This module provides functionality for collecting and analyzing various
metrics from the LFS/BLFS build system.

Author: WARP System
Created: 2025-05-31
"""

import asyncio
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

from loguru import logger

from ..process import ProcessStatus, ResourceUsage
from typing import Any
from .metrics_store import MetricsStore


from .types import BuildMetrics, PerformanceMetrics


@dataclass
class MetricsContext:
    """Context for a metrics collection session."""
    start_time: datetime = field(default_factory=datetime.now)
    metrics_collected: bool = False
    build_metrics: Optional[BuildMetrics] = None
    performance_metrics: Optional[PerformanceMetrics] = None


class MetricsCollector:
    """
    Collects and manages various system metrics.

    This class is responsible for:
    - Collecting build metrics
    - Tracking performance metrics
    - Monitoring resource usage
    - Persisting metrics data

    Attributes:
        store: Metrics storage backend
        active_collections: Currently active metric collections
        collection_history: Historical metrics data
    """

    def __init__(self, metrics_dir: Optional[Path] = None):
        """
        Initialize the metrics collector.

        Args:
            metrics_dir: Directory for metrics storage
        """
        self.store = MetricsStore(metrics_dir) if metrics_dir else None
        self.active_collections: Dict[str, MetricsContext] = {}
        self.collection_history: Dict[str, List[BuildMetrics]] = {}

    def start_collection(self, collection_id: str = "") -> MetricsContext:
        """
        Start collecting metrics.

        Args:
            collection_id: Optional identifier for this collection

        Returns:
            New metrics context
        """
        context = MetricsContext()
        self.active_collections[collection_id] = context
        return context

    def stop_collection(
        self,
        collection_id: str = "",
        success: bool = True
    ) -> Optional[BuildMetrics]:
        """
        Stop collecting metrics.

        Args:
            collection_id: Collection identifier
            success: Whether the operation was successful

        Returns:
            Collected build metrics or None
        """
        context = self.active_collections.get(collection_id)
        if not context:
            return None

        # Finalize metrics
        end_time = datetime.now()
        if context.build_metrics:
            context.build_metrics.end_time = end_time
            context.build_metrics.build_success = success
            context.build_metrics.build_duration = (
                end_time - context.build_metrics.start_time
            ).total_seconds()

        # Store metrics
        if self.store and context.build_metrics:
            self.store.save_build_metrics(context.build_metrics)

        # Update history
        if context.build_metrics:
            pkg = context.build_metrics.package_name
            if pkg not in self.collection_history:
                self.collection_history[pkg] = []
            self.collection_history[pkg].append(context.build_metrics)

        # Cleanup
        del self.active_collections[collection_id]
        return context.build_metrics

    @contextmanager
    def collect_metrics(self, package_name: str):
        """
        Context manager for metrics collection.

        Args:
            package_name: Name of package being built

        Yields:
            None
        """
        collection_id = f"{package_name}-{int(time.time())}"
        context = self.start_collection(collection_id)
        context.build_metrics = BuildMetrics(
            start_time=context.start_time,
            package_name=package_name
        )
        try:
            yield
            self.stop_collection(collection_id, success=True)
        except Exception as e:
            context.build_metrics.error_count += 1
            self.stop_collection(collection_id, success=False)
            raise

    def update_build_metrics(
        self,
        collection_id: str,
        status: ProcessStatus
    ) -> None:
        """
        Update build metrics with process status.

        Args:
            collection_id: Collection identifier
            status: Process status to record
        """
        context = self.active_collections.get(collection_id)
        if not context or not context.build_metrics:
            return

        metrics = context.build_metrics
        metrics.exit_code = status.exit_code
        metrics.build_success = status.exit_code == 0
        if status.peak_memory is not None:
            if not context.performance_metrics:
                context.performance_metrics = PerformanceMetrics()
            context.performance_metrics.peak_memory_usage = status.peak_memory
        if status.peak_cpu is not None:
            if not context.performance_metrics:
                context.performance_metrics = PerformanceMetrics()
            context.performance_metrics.peak_cpu_usage = status.peak_cpu

    def update_performance_metrics(
        self,
        collection_id: str,
        usage: ResourceUsage
    ) -> None:
        """
        Update performance metrics with resource usage.

        Args:
            collection_id: Collection identifier
            usage: Resource usage to record
        """
        context = self.active_collections.get(collection_id)
        if not context:
            return

        if not context.performance_metrics:
            context.performance_metrics = PerformanceMetrics()

        metrics = context.performance_metrics
        metrics.peak_memory_usage = max(metrics.peak_memory_usage, usage.memory_rss)
        metrics.peak_cpu_usage = max(metrics.peak_cpu_usage, usage.cpu_percent)
        metrics.total_io_reads = max(metrics.total_io_reads, usage.io_read_bytes)
        metrics.total_io_writes = max(metrics.total_io_writes, usage.io_write_bytes)
        metrics.peak_thread_count = max(metrics.peak_thread_count, usage.num_threads)
        metrics.peak_fd_count = max(metrics.peak_fd_count, usage.num_fds)

    def get_build_metrics(self, package_name: str = "") -> Dict[str, Any]:
        """
        Get build metrics summary.

        Args:
            package_name: Optional package name to filter by

        Returns:
            Dict containing build metrics
        """
        if package_name:
            history = self.collection_history.get(package_name, [])
        else:
            history = [
                metric for metrics in self.collection_history.values()
                for metric in metrics
            ]

        return {
            'builds_completed': len(history),
            'successful_builds': sum(1 for m in history if m.build_success),
            'failed_builds': sum(1 for m in history if not m.build_success),
            'total_errors': sum(m.error_count for m in history),
            'total_retries': sum(m.retry_count for m in history),
            'average_duration': sum(
                m.build_duration for m in history if m.build_duration
            ) / len(history) if history else 0
        }

    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Get performance metrics summary.

        Returns:
            Dict containing performance metrics
        """
        peak_memory = 0
        peak_cpu = 0.0
        total_io_reads = 0
        total_io_writes = 0

        for context in self.active_collections.values():
            if not context.performance_metrics:
                continue
            metrics = context.performance_metrics
            peak_memory = max(peak_memory, metrics.peak_memory_usage)
            peak_cpu = max(peak_cpu, metrics.peak_cpu_usage)
            total_io_reads = max(total_io_reads, metrics.total_io_reads)
            total_io_writes = max(total_io_writes, metrics.total_io_writes)

        return {
            'peak_memory_mb': peak_memory / (1024 * 1024),
            'peak_cpu_percent': peak_cpu,
            'total_io_reads_mb': total_io_reads / (1024 * 1024),
            'total_io_writes_mb': total_io_writes / (1024 * 1024)
        }

    async def cleanup(self) -> None:
        """Clean up metrics collection state."""
        # Stop all active collections
        for collection_id in list(self.active_collections.keys()):
            self.stop_collection(collection_id, success=False)

        # Clear history
        self.collection_history.clear()

        # Clean up store
        if self.store:
            await self.store.cleanup()

