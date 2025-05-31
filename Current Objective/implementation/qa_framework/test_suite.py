"""
Test Suite Initialization Module

This module provides test suite management and initialization, coordinating
test discovery, organization, and execution for the QA framework.

Author: WARP System
Created: 2025-05-31
"""

import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Type

from loguru import logger

from .adapters import TestAdapter, TestMetadata
from .metrics import MetricsCollector
from .orchestrator import TestOrchestrator, TestResult


class TestCategory(Enum):
    """Enumeration of test categories."""
    UNIT = auto()
    INTEGRATION = auto()
    VALIDATION = auto()
    PERFORMANCE = auto()
    SECURITY = auto()


@dataclass
class TestSuiteConfig:
    """Configuration for a test suite."""
    category: TestCategory
    base_path: str
    patterns: List[str]
    parallel_execution: bool = True
    timeout_seconds: int = 300
    retry_count: int = 0
    required_coverage: float = 0.0


class TestSuite:
    """
    Manages a collection of related tests.

    This class is responsible for:
    - Managing tests within a category
    - Handling test dependencies
    - Coordinating test execution
    - Collecting test results

    Attributes:
        category: The category of tests in this suite
        config: Configuration for this test suite
        tests: Dict mapping test IDs to their metadata
        execution_order: List of tests in dependency order
    """

    def __init__(self, config: TestSuiteConfig):
        """
        Initialize a test suite.

        Args:
            config: Configuration for this test suite
        """
        self.category = config.category
        self.config = config
        self.tests: Dict[str, TestMetadata] = {}
        self.execution_order: List[str] = []
        self.adapter = TestAdapter()

    async def initialize(self) -> None:
        """Initialize the test suite by discovering and organizing tests."""
        # Discover tests
        self.tests = self.adapter.discover_tests(self.config.base_path)
        
        # Calculate execution order
        self.execution_order = self._calculate_execution_order()
        
        logger.info(
            f"Initialized {self.category.name} test suite with "
            f"{len(self.tests)} tests"
        )

    def _calculate_execution_order(self) -> List[str]:
        """
        Calculate test execution order based on dependencies.

        Returns:
            List of test IDs in execution order
        """
        visited: Set[str] = set()
        execution_order: List[str] = []

        def visit(test_id: str) -> None:
            """Depth-first traversal of test dependencies."""
            if test_id in visited:
                return
            
            visited.add(test_id)
            for dep in self.adapter.get_test_dependencies(test_id):
                visit(dep)
            
            execution_order.append(test_id)

        # Visit all tests to build execution order
        for test_id in self.tests:
            visit(test_id)

        return execution_order

    async def run_tests(self, orchestrator: TestOrchestrator) -> Dict[str, TestResult]:
        """
        Run all tests in this suite.

        Args:
            orchestrator: TestOrchestrator instance to manage test execution

        Returns:
            Dict mapping test IDs to their results
        """
        results: Dict[str, TestResult] = {}
        
        for test_id in self.execution_order:
            try:
                # Schedule test with its dependencies
                test_result = await orchestrator.schedule_test(
                    test_id,
                    lambda: self.adapter.run_test(test_id),
                    list(self.adapter.get_test_dependencies(test_id))
                )
                results[test_id] = test_result
                
            except Exception as e:
                logger.error(f"Failed to run test {test_id}: {e}")
                # Create failure result
                results[test_id] = TestResult(
                    test_id=test_id,
                    status="ERROR",
                    start_time=None,
                    end_time=None,
                    error_message=str(e)
                )

        return results


class TestSuiteManager:
    """
    Manages all test suites in the QA framework.

    This class is responsible for:
    - Initializing test suites
    - Coordinating test execution across suites
    - Managing test resources
    - Collecting and aggregating results

    Attributes:
        suites: Dict mapping categories to their test suites
        orchestrator: TestOrchestrator instance
        metrics_collector: MetricsCollector instance
    """

    def __init__(
        self,
        orchestrator: TestOrchestrator,
        metrics_collector: MetricsCollector
    ):
        """
        Initialize the TestSuiteManager.

        Args:
            orchestrator: TestOrchestrator instance
            metrics_collector: MetricsCollector instance
        """
        self.suites: Dict[TestCategory, TestSuite] = {}
        self.orchestrator = orchestrator
        self.metrics_collector = metrics_collector

    async def initialize_suites(self, base_test_path: str) -> None:
        """
        Initialize all test suites.

        Args:
            base_test_path: Base path containing test directories
        """
        # Configure test suites
        suite_configs = {
            TestCategory.UNIT: TestSuiteConfig(
                category=TestCategory.UNIT,
                base_path=os.path.join(base_test_path, 'unit'),
                patterns=['test_*.py'],
                parallel_execution=True,
                required_coverage=90.0
            ),
            TestCategory.INTEGRATION: TestSuiteConfig(
                category=TestCategory.INTEGRATION,
                base_path=os.path.join(base_test_path, 'integration'),
                patterns=['test_*.py'],
                parallel_execution=False,
                timeout_seconds=600
            ),
            TestCategory.VALIDATION: TestSuiteConfig(
                category=TestCategory.VALIDATION,
                base_path=os.path.join(base_test_path, 'validation'),
                patterns=['test_*.py'],
                parallel_execution=False,
                timeout_seconds=1200
            ),
        }

        # Initialize each suite
        for category, config in suite_configs.items():
            suite = TestSuite(config)
            await suite.initialize()
            self.suites[category] = suite

    async def run_suite(self, category: TestCategory) -> Dict[str, TestResult]:
        """
        Run tests in a specific suite.

        Args:
            category: Category of tests to run

        Returns:
            Dict mapping test IDs to their results
        """
        if category not in self.suites:
            raise ValueError(f"Unknown test category: {category}")

        suite = self.suites[category]
        return await suite.run_tests(self.orchestrator)

    async def run_all_suites(self) -> Dict[TestCategory, Dict[str, TestResult]]:
        """
        Run all test suites in the correct order.

        Returns:
            Dict mapping categories to their test results
        """
        results = {}
        
        # Run suites in order: unit -> integration -> validation
        execution_order = [
            TestCategory.UNIT,
            TestCategory.INTEGRATION,
            TestCategory.VALIDATION
        ]

        for category in execution_order:
            if category in self.suites:
                suite_results = await self.run_suite(category)
                results[category] = suite_results

                # Check if we should continue based on results
                failed_tests = [
                    test_id for test_id, result in suite_results.items()
                    if result.status != "SUCCESS"
                ]
                if failed_tests and category != TestCategory.VALIDATION:
                    logger.error(
                        f"Stopping test execution due to failures in {category.name} "
                        f"suite: {failed_tests}"
                    )
                    break

        return results

    def get_suite_info(self, category: TestCategory) -> Optional[Dict]:
        """
        Get information about a specific test suite.

        Args:
            category: Category of the test suite

        Returns:
            Dict containing suite information if found, None otherwise
        """
        if category in self.suites:
            suite = self.suites[category]
            return {
                'category': category.name,
                'test_count': len(suite.tests),
                'execution_order': suite.execution_order.copy(),
                'config': {
                    'parallel_execution': suite.config.parallel_execution,
                    'timeout_seconds': suite.config.timeout_seconds,
                    'retry_count': suite.config.retry_count,
                    'required_coverage': suite.config.required_coverage
                }
            }
        return None

