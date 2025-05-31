"""
Core Package

This package provides the core functionality for the LFS/BLFS
build scripts wrapper system.

Author: WARP System
Created: 2025-05-31
"""

from .config import WrapperConfig
from .wrapper import LFSWrapper

__all__ = [
    'WrapperConfig',
    'LFSWrapper'
]

