"""
Metrics Collection Module

This module provides metrics collection and analysis functionality for
the LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from ..errors import ConfigError
from ..process import ProcessStatus, ResourceUsage


@dataclass
class BuildMetrics:
    """Build process metrics."""
    package: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    status: str = "started"
    exit_code: Optional[int] = None
    error_count: int = 0
    retry_count: int = 0
    build_script: Optional[str] = None
    script_args: Optional[List[str]] = None
    process_metrics: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_usage: float = 0.0
    memory_usage: int = 0
    disk_read: int = 0
    disk_write: int = 0
    process_count: int = 0
    io_wait: float = 0.0


class MetricsCollector:
    """
    Collects and manages build and performance metrics.

    This class is responsible for:
    - Collecting build metrics
    - Tracking performance metrics
    - Storing metrics data
    - Generating reports
    """

    def __init__(self, metrics_dir: Optional[Union[str, Path]] = None):
        """
        Initialize metrics collector.

        Args:
            metrics_dir: Directory for metrics storage
        """
        self.metrics_dir = Path(metrics_dir) if metrics_dir else Path.cwd() / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        # Setup metrics files
        self.build_metrics_file = self.metrics_dir / "build_metrics.json"
        self.performance_metrics_file = self.metrics_dir / "performance_metrics.json"

        # Initialize metrics storage
        self.build_metrics: Dict[str, Dict[str, BuildMetrics]] = {}
        self.performance_metrics: List[PerformanceMetrics] = []

        # Load existing metrics
        self._load_metrics()

    async def start_operation(
        self,
        operation: str,
        package: str,
        **kwargs
    ) -> datetime:
        """
        Start tracking an operation.

        Args:
            operation: Operation type
            package: Package name
            **kwargs: Additional operation details

        Returns:
            Start timestamp
        """
        start_time = datetime.now()

        if operation == "build":
            metrics = BuildMetrics(
                package=package,
                start_time=start_time,
                build_script=kwargs.get('script'),
                script_args=kwargs.get('args'),
                process_metrics={}
            )
            self._store_build_metrics(package, metrics)

        return start_time

    async def end_operation(
        self,
        operation: str,
        package: str,
        **kwargs
    ) -> datetime:
        """
        End tracking an operation.

        Args:
            operation: Operation type
            package: Package name
            **kwargs: Additional operation details

        Returns:
            End timestamp
        """
        end_time = datetime.now()

        if operation == "build":
            if package in self.build_metrics:
                metrics = self.build_metrics[package]
                latest_build = max(
                    metrics.values(),
                    key=lambda m: m.start_time
                )
                latest_build.end_time = end_time
                latest_build.duration = (
                    end_time - latest_build.start_time
                ).total_seconds()
                self._store_build_metrics(package, latest_build)

        return end_time

    async def record_build_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Record build metrics.

        Args:
            metrics: Build metrics data
        """
        package = metrics.get('package')
        if not package:
            raise ValueError("Package name required for build metrics")

        # Create build metrics record
        build_metrics = BuildMetrics(
            package=package,
            start_time=metrics.get('start_time', datetime.now()),
            end_time=metrics.get('end_time'),
            status=metrics.get('status', 'unknown'),
            error_count=metrics.get('error_count', 0),
            retry_count=metrics.get('retry_count', 0),
            process_metrics=metrics.get('process_metrics', {})
        )

        # Calculate duration if both timestamps present
        if build_metrics.start_time and build_metrics.end_time:
            build_metrics.duration = (
                build_metrics.end_time - build_metrics.start_time
            ).total_seconds()

        self._store_build_metrics(package, build_metrics)

    async def record_performance_metrics(
        self,
        metrics: Union[ProcessStatus, ResourceUsage]
    ) -> None:
        """
        Record performance metrics.

        Args:
            metrics: Performance metrics data
        """
        perf_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_usage=getattr(metrics, 'cpu_usage', 0.0),
            memory_usage=getattr(metrics, 'memory_usage', 0),
            disk_read=getattr(metrics, 'io_read', 0),
            disk_write=getattr(metrics, 'io_write', 0),
            process_count=getattr(metrics, 'num_processes', 1)
        )

        self.performance_metrics.append(perf_metrics)
        self._save_performance_metrics()

    async def get_metrics(
        self,
        package: Optional[str] = None,
        metric_type: str = "build"
    ) -> Dict[str, Any]:
        """
        Get collected metrics.

        Args:
            package: Optional package filter
            metric_type: Type of metrics to retrieve

        Returns:
            Dict of metrics data
        """
        if metric_type == "build":
            if package:
                if package in self.build_metrics:
                    # Get latest build metrics
                    metrics = self.build_metrics[package]
                    latest = max(
                        metrics.values(),
                        key=lambda m: m.start_time
                    )
                    return asdict(latest)
                return {}
            return {
                pkg: asdict(max(metrics.values(), key=lambda m: m.start_time))
                for pkg, metrics in self.build_metrics.items()
            }
        elif metric_type == "performance":
            # Get performance metrics for last hour
            cutoff = datetime.now() - timedelta(hours=1)
            metrics = [
                asdict(m) for m in self.performance_metrics
                if m.timestamp >= cutoff
            ]
            return {'metrics': metrics}
        else:
            raise ValueError(f"Unknown metric type: {metric_type}")

    def _store_build_metrics(
        self,
        package: str,
        metrics: BuildMetrics
    ) -> None:
        """
        Store build metrics.

        Args:
            package: Package name
            metrics: Build metrics to store
        """
        if package not in self.build_metrics:
            self.build_metrics[package] = {}

        # Use timestamp as key
        key = metrics.start_time.isoformat()
        self.build_metrics[package][key] = metrics
        self._save_build_metrics()

    def _load_metrics(self) -> None:
        """Load metrics from storage."""
        try:
            if self.build_metrics_file.exists():
                with open(self.build_metrics_file) as f:
                    data = json.load(f)
                    self.build_metrics = {
                        pkg: {
                            ts: BuildMetrics(**metrics)
                            for ts, metrics in builds.items()
                        }
                        for pkg, builds in data.items()
                    }

            if self.performance_metrics_file.exists():
                with open(self.performance_metrics_file) as f:
                    data = json.load(f)
                    self.performance_metrics = [
                        PerformanceMetrics(**metrics)
                        for metrics in data
                    ]

        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
            raise ConfigError(
                "Failed to load metrics",
                details={'error': str(e)}
            )

    def _save_build_metrics(self) -> None:
        """Save build metrics to storage."""
        try:
            with open(self.build_metrics_file, 'w') as f:
                json.dump(
                    {
                        pkg: {
                            ts: asdict(metrics)
                            for ts, metrics in builds.items()
                        }
                        for pkg, builds in self.build_metrics.items()
                    },
                    f,
                    default=str,
                    indent=2
                )
        except Exception as e:
            logger.error(f"Failed to save build metrics: {e}")

    def _save_performance_metrics(self) -> None:
        """Save performance metrics to storage."""
        try:
            with open(self.performance_metrics_file, 'w') as f:
                json.dump(
                    [asdict(m) for m in self.performance_metrics],
                    f,
                    default=str,
                    indent=2
                )
        except Exception as e:
            logger.error(f"Failed to save performance metrics: {e}")

    async def cleanup(self) -> None:
        """Clean up metrics storage."""
        try:
            # Save final metrics
            self._save_build_metrics()
            self._save_performance_metrics()

            # Clear memory
            self.build_metrics.clear()
            self.performance_metrics.clear()

        except Exception as e:
            logger.error(f"Metrics cleanup failed: {e}")
            raise

