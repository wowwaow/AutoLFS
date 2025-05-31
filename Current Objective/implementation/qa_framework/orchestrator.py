"""
Test Orchestrator Component

This module provides the TestOrchestrator class which coordinates test execution,
manages dependencies, and handles test scheduling across the QA framework.

Author: WARP System
Created: 2025-05-31
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set, Type

from loguru import logger

from .metrics import MetricsCollector


@dataclass
class TestResult:
    """Represents the result of a test execution."""
    test_id: str
    status: str
    start_time: datetime
    end_time: datetime
    error_message: Optional[str] = None
    metrics: Optional[Dict] = None


class TestOrchestrator:
    """
    Coordinates and manages test execution across the QA framework.

    This class is responsible for:
    - Scheduling and executing tests
    - Managing test dependencies
    - Coordinating parallel test execution
    - Collecting and aggregating test results

    Attributes:
        metrics_collector: MetricsCollector instance for gathering test metrics
        active_tests: Set of currently running tests
        completed_tests: Dict of completed test results
        test_dependencies: Dict mapping tests to their dependencies
    """

    def __init__(self, metrics_collector: MetricsCollector):
        """
        Initialize the TestOrchestrator.

        Args:
            metrics_collector: MetricsCollector instance for gathering metrics
        """
        self.metrics_collector = metrics_collector
        self.active_tests: Set[str] = set()
        self.completed_tests: Dict[str, TestResult] = {}
        self.test_dependencies: Dict[str, List[str]] = {}
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)

    async def schedule_test(self, test_id: str, test_func: callable,
                          dependencies: Optional[List[str]] = None) -> None:
        """
        Schedule a test for execution.

        Args:
            test_id: Unique identifier for the test
            test_func: The test function to execute
            dependencies: List of test IDs that must complete before this test
        """
        if dependencies:
            self.test_dependencies[test_id] = dependencies
            # Wait for dependencies to complete
            await self._wait_for_dependencies(test_id)

        # Start test execution
        self.active_tests.add(test_id)
        start_time = datetime.now()

        try:
            # Execute test and collect metrics
            with self.metrics_collector.collect_metrics(test_id):
                await test_func()
            
            status = "SUCCESS"
            error_message = None
        except Exception as e:
            status = "FAILURE"
            error_message = str(e)
            logger.error(f"Test {test_id} failed: {e}")
        finally:
            end_time = datetime.now()
            self.active_tests.remove(test_id)
            
            # Record test result
            self.completed_tests[test_id] = TestResult(
                test_id=test_id,
                status=status,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message,
                metrics=self.metrics_collector.get_metrics(test_id)
            )

    async def _wait_for_dependencies(self, test_id: str) -> None:
        """
        Wait for all dependencies of a test to complete.

        Args:
            test_id: ID of the test whose dependencies need to be checked
        """
        dependencies = self.test_dependencies.get(test_id, [])
        while dependencies:
            completed_deps = []
            for dep in dependencies:
                if dep in self.completed_tests:
                    if self.completed_tests[dep].status == "FAILURE":
                        raise RuntimeError(
                            f"Dependency {dep} failed, cannot run {test_id}"
                        )
                    completed_deps.append(dep)
            
            for dep in completed_deps:
                dependencies.remove(dep)
            
            if dependencies:
                await asyncio.sleep(1)

    def get_test_status(self, test_id: str) -> Optional[TestResult]:
        """
        Get the current status of a test.

        Args:
            test_id: ID of the test to check

        Returns:
            TestResult if test is completed, None if not found
        """
        return self.completed_tests.get(test_id)

    def get_active_tests(self) -> Set[str]:
        """
        Get the set of currently running tests.

        Returns:
            Set of test IDs currently being executed
        """
        return self.active_tests.copy()

    async def run_test_suite(self, test_suite: Dict[str, callable]) -> Dict[str, TestResult]:
        """
        Run a complete test suite with dependency management.

        Args:
            test_suite: Dict mapping test IDs to test functions

        Returns:
            Dict mapping test IDs to their TestResults
        """
        tasks = []
        for test_id, test_func in test_suite.items():
            task = self.event_loop.create_task(
                self.schedule_test(
                    test_id,
                    test_func,
                    self.test_dependencies.get(test_id)
                )
            )
            tasks.append(task)

        await asyncio.gather(*tasks)
        return self.completed_tests

