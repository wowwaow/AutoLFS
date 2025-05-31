"""
Metrics Storage Module

This module provides persistent storage for metrics data in the LFS/BLFS
build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from .types import BuildMetrics, PerformanceMetrics


class MetricsStore:
    """
    Provides persistent storage for metrics data.

    This class is responsible for:
    - Storing build metrics
    - Storing performance metrics
    - Managing metrics history
    - Providing query capabilities

    Attributes:
        db_path: Path to SQLite database
        metrics_dir: Directory for metrics files
    """

    def __init__(self, metrics_dir: Optional[Path] = None):
        """
        Initialize the metrics store.

        Args:
            metrics_dir: Directory for metrics storage
        """
        self.metrics_dir = metrics_dir or Path.cwd() / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.metrics_dir / "metrics.db"

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS build_metrics (
                    id INTEGER PRIMARY KEY,
                    package_name TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    exit_code INTEGER,
                    build_success BOOLEAN,
                    build_duration REAL,
                    error_count INTEGER,
                    retry_count INTEGER,
                    log_file TEXT,
                    script_path TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY,
                    build_id INTEGER,
                    peak_memory_usage INTEGER,
                    peak_cpu_usage REAL,
                    average_cpu_usage REAL,
                    total_io_reads INTEGER,
                    total_io_writes INTEGER,
                    peak_thread_count INTEGER,
                    peak_fd_count INTEGER,
                    FOREIGN KEY(build_id) REFERENCES build_metrics(id)
                )
            """)
            conn.commit()

    def save_build_metrics(self, metrics: BuildMetrics) -> int:
        """
        Save build metrics to database.

        Args:
            metrics: Build metrics to save

        Returns:
            ID of saved metrics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO build_metrics (
                    package_name, start_time, end_time, exit_code,
                    build_success, build_duration, error_count,
                    retry_count, log_file, script_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metrics.package_name,
                    metrics.start_time.isoformat(),
                    metrics.end_time.isoformat() if metrics.end_time else None,
                    metrics.exit_code,
                    metrics.build_success,
                    metrics.build_duration,
                    metrics.error_count,
                    metrics.retry_count,
                    str(metrics.log_file) if metrics.log_file else None,
                    str(metrics.script_path) if metrics.script_path else None
                )
            )
            return cursor.lastrowid

    def save_performance_metrics(
        self,
        build_id: int,
        metrics: PerformanceMetrics
    ) -> None:
        """
        Save performance metrics to database.

        Args:
            build_id: ID of associated build metrics
            metrics: Performance metrics to save
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO performance_metrics (
                    build_id, peak_memory_usage, peak_cpu_usage,
                    average_cpu_usage, total_io_reads, total_io_writes,
                    peak_thread_count, peak_fd_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    build_id,
                    metrics.peak_memory_usage,
                    metrics.peak_cpu_usage,
                    metrics.average_cpu_usage,
                    metrics.total_io_reads,
                    metrics.total_io_writes,
                    metrics.peak_thread_count,
                    metrics.peak_fd_count
                )
            )
            conn.commit()

    def get_build_history(
        self,
        package_name: Optional[str] = None,
        days: int = 7
    ) -> List[Dict]:
        """
        Get build history from database.

        Args:
            package_name: Optional package name filter
            days: Number of days of history

        Returns:
            List of build metrics records
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                SELECT * FROM build_metrics
                WHERE start_time >= datetime('now', '-? days')
            """
            params = [days]

            if package_name:
                query += " AND package_name = ?"
                params.append(package_name)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_performance_history(
        self,
        build_id: Optional[int] = None,
        days: int = 7
    ) -> List[Dict]:
        """
        Get performance history from database.

        Args:
            build_id: Optional build ID filter
            days: Number of days of history

        Returns:
            List of performance metrics records
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                SELECT p.* FROM performance_metrics p
                JOIN build_metrics b ON p.build_id = b.id
                WHERE b.start_time >= datetime('now', '-? days')
            """
            params = [days]

            if build_id:
                query += " AND p.build_id = ?"
                params.append(build_id)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    async def cleanup(self) -> None:
        """Clean up old metrics data."""
        # Remove old database entries
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM performance_metrics
                WHERE build_id IN (
                    SELECT id FROM build_metrics
                    WHERE start_time < datetime('now', '-30 days')
                )
            """)
            conn.execute("""
                DELETE FROM build_metrics
                WHERE start_time < datetime('now', '-30 days')
            """)
            conn.commit()

