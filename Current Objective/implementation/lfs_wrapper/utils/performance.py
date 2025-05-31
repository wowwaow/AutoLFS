"""
Performance Measurement Module

This module provides performance measurement utilities for
the LFS/BLFS build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

import asyncio
import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, TypeVar, Union

import psutil
from loguru import logger

T = TypeVar('T')


def measure_time(
    func: Optional[Callable[..., T]] = None,
    *,
    name: Optional[str] = None
) -> Union[Callable[..., T], float]:
    """
    Measure execution time of a function.

    Can be used as a decorator or context manager:

    @measure_time
    async def my_func():
        ...

    with measure_time("operation"):
        ...

    Args:
        func: Function to measure
        name: Optional operation name

    Returns:
        Wrapped function or elapsed time
    """
    if func is not None:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            start_time = time.monotonic()
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.monotonic() - start_time
                logger.debug(
                    f"Function {func.__name__} took {elapsed:.3f} seconds"
                )

        return wrapper

    @contextmanager
    def timer():
        start_time = time.monotonic()
        try:
            yield
        finally:
            elapsed = time.monotonic() - start_time
            if name:
                logger.debug(
                    f"Operation {name} took {elapsed:.3f} seconds"
                )
            else:
                logger.debug(f"Operation took {elapsed:.3f} seconds")

    return timer()


def measure_memory(
    func: Optional[Callable[..., T]] = None,
    *,
    name: Optional[str] = None
) -> Union[Callable[..., T], Dict[str, int]]:
    """
    Measure memory usage of a function.

    Can be used as a decorator or context manager:

    @measure_memory
    async def my_func():
        ...

    with measure_memory("operation") as stats:
        ...
        print(stats['peak_rss'])

    Args:
        func: Function to measure
        name: Optional operation name

    Returns:
        Wrapped function or memory statistics
    """
    if func is not None:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            process = psutil.Process()
            start_mem = process.memory_info().rss
            peak_mem = start_mem

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
            finally:
                end_mem = process.memory_info().rss
                peak_mem = max(peak_mem, end_mem)
                logger.debug(
                    f"Function {func.__name__} memory usage: "
                    f"start={start_mem/1024/1024:.1f}MB, "
                    f"end={end_mem/1024/1024:.1f}MB, "
                    f"peak={peak_mem/1024/1024:.1f}MB"
                )

        return wrapper

    class MemoryStats:
        def __init__(self):
            self.process = psutil.Process()
            self.start_mem = self.process.memory_info().rss
            self.peak_mem = self.start_mem
            self.end_mem = self.start_mem

        def update(self):
            current = self.process.memory_info().rss
            self.peak_mem = max(self.peak_mem, current)
            return current

        def get_stats(self) -> Dict[str, int]:
            return {
                'start_rss': self.start_mem,
                'end_rss': self.end_mem,
                'peak_rss': self.peak_mem
            }

    @contextmanager
    def memory_tracker():
        stats = MemoryStats()
        try:
            yield stats.get_stats()
        finally:
            stats.end_mem = stats.update()
            if name:
                logger.debug(
                    f"Operation {name} memory usage: "
                    f"start={stats.start_mem/1024/1024:.1f}MB, "
                    f"end={stats.end_mem/1024/1024:.1f}MB, "
                    f"peak={stats.peak_mem/1024/1024:.1f}MB"
                )
            else:
                logger.debug(
                    f"Operation memory usage: "
                    f"start={stats.start_mem/1024/1024:.1f}MB, "
                    f"end={stats.end_mem/1024/1024:.1f}MB, "
                    f"peak={stats.peak_mem/1024/1024:.1f}MB"
                )

    return memory_tracker()

