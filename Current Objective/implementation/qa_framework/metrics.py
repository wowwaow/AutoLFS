"""
Metrics Collection Component

This module provides the MetricsCollector interface and implementation for
gathering and analyzing quality metrics across the QA framework.

Author: WARP System
Created: 2025-05-31
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Generator, List, Optional

import psutil
from loguru import logger


class MetricsCollector:
    """
    Collects and manages quality metrics during test execution.

    This class is responsible for:
    - Gathering performance metrics
    - Tracking resource usage
    - Collecting test coverage data
    - Storing and analyzing metrics

    Attributes:
        metrics: Dict storing collected metrics by test ID
        current_test: Currently active test ID
    """

    def __init__(self):
        """Initialize the MetricsCollector."""
        self.metrics: Dict[str, Dict] = {}
        self.current_test: Optional[str] = None

    @contextmanager
    def collect_metrics(self, test_id: str) -> Generator[None, None, None]:
        """
        Context manager for collecting metrics during test execution.

        Args:
            test_id: Unique identifier for the test

        Yields:
            None
        """
        try:
            self.current_test = test_id
            self.metrics[test_id] = {
                'start_time': datetime.now(),
                'cpu_usage': [],
                'memory_usage': [],
                'disk_io': [],
                'coverage': None
            }
            
            # Start performance monitoring
            self._start_monitoring(test_id)
            yield
            
        finally:
            # Stop monitoring and finalize metrics
            self._stop_monitoring(test_id)
            self.metrics[test_id]['end_time'] = datetime.now()
            self.current_test = None

    def get_metrics(self, test_id: str) -> Optional[Dict]:
        """
        Get collected metrics for a specific test.

        Args:
            test_id: ID of the test to get metrics for

        Returns:
            Dict of metrics if test exists, None otherwise
        """
        return self.metrics.get(test_id)

    def _start_monitoring(self, test_id: str) -> None:
        """
        Start monitoring system resources for a test.

        Args:
            test_id: ID of the test to monitor
        """
        process = psutil.Process()
        self.metrics[test_id]['initial_cpu'] = process.cpu_percent()
        self.metrics[test_id]['initial_memory'] = process.memory_info().rss
        self.metrics[test_id]['initial_disk'] = psutil.disk_io_counters()

    def _stop_monitoring(self, test_id: str) -> None:
        """
        Stop monitoring and calculate final metrics.

        Args:
            test_id: ID of the test to stop monitoring
        """
        process = psutil.Process()
        metrics = self.metrics[test_id]
        
        # Calculate CPU usage
        final_cpu = process.cpu_percent()
        metrics['cpu_usage'].append({
            'final': final_cpu,
            'average': sum(metrics['cpu_usage']) / len(metrics['cpu_usage'])
            if metrics['cpu_usage'] else 0
        })

        # Calculate memory usage
        final_memory = process.memory_info().rss
        metrics['memory_usage'].append({
            'final': final_memory,
            'peak': max(metrics['memory_usage']) if metrics['memory_usage'] else 0
        })

        # Calculate disk I/O
        final_disk = psutil.disk_io_counters()
        metrics['disk_io'].append({
            'read_bytes': final_disk.read_bytes - metrics['initial_disk'].read_bytes,
            'write_bytes': final_disk.write_bytes - metrics['initial_disk'].write_bytes
        })

    def record_coverage(self, test_id: str, coverage_data: Dict) -> None:
        """
        Record test coverage data.

        Args:
            test_id: ID of the test
            coverage_data: Dictionary containing coverage information
        """
        if test_id in self.metrics:
            self.metrics[test_id]['coverage'] = coverage_data
        else:
            logger.warning(f"Attempting to record coverage for unknown test: {test_id}")

    def get_summary_metrics(self) -> Dict:
        """
        Get summary metrics across all tests.

        Returns:
            Dict containing aggregated metrics
        """
        return {
            'total_tests': len(self.metrics),
            'average_cpu': sum(
                m['cpu_usage'][-1]['average'] for m in self.metrics.values()
                if m['cpu_usage']
            ) / len(self.metrics) if self.metrics else 0,
            'peak_memory': max(
                m['memory_usage'][-1]['peak'] for m in self.metrics.values()
                if m['memory_usage']
            ) if self.metrics else 0,
            'total_duration': sum(
                (m['end_time'] - m['start_time']).total_seconds()
                for m in self.metrics.values()
                if 'end_time' in m and 'start_time' in m
            )
        }

