"""
LFS/BLFS Build Scripts Wrapper System - QA Framework

This package provides the quality assurance framework for managing and executing
test suites, collecting metrics, and generating quality reports for the LFS/BLFS
build system wrapper.

Author: WARP System
Created: 2025-05-31
"""

from typing import Dict, List, Optional, Type

from .framework import QAFramework
from .orchestrator import TestOrchestrator
from .metrics import MetricsCollector

__version__ = "1.0.0"
__all__ = ["QAFramework", "TestOrchestrator", "MetricsCollector"]

