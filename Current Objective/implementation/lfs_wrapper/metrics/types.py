"""
Metrics Types Module

This module defines the data types used for metrics collection in the
LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class BuildMetrics:
    """Build-related metrics."""
    start_time: datetime
    end_time: Optional[datetime] = None
    package_name: str = ""
    exit_code: Optional[int] = None
    build_success: bool = False
    build_duration: Optional[float] = None
    error_count: int = 0
    retry_count: int = 0
    log_file: Optional[Path] = None
    script_path: Optional[Path] = None


@dataclass
class PerformanceMetrics:
    """Performance-related metrics."""
    peak_memory_usage: int = 0
    peak_cpu_usage: float = 0.0
    average_cpu_usage: float = 0.0
    total_io_reads: int = 0
    total_io_writes: int = 0
    peak_thread_count: int = 0
    peak_fd_count: int = 0

