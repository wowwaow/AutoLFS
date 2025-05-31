"""
QA Framework Core

This module provides the main QA framework implementation that coordinates
all quality assurance activities for the LFS/BLFS build system wrapper.

Author: WARP System
Created: 2025-05-31
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional, Set, Type, Union

from loguru import logger

from .metrics import MetricsCollector
from .orchestrator import TestOrchestrator, TestResult
from .test_suite import TestCategory, TestSuite, TestSuiteManager


class QAFramework:
    """
    Main QA framework coordinator integrating all QA components.

    This class is responsible for:
    - Initializing and coordinating QA components
    - Managing test execution across categories
    - Collecting and reporting metrics
    - Integrating with existing test infrastructure
    - Coordinating test suite execution
    - Managing test resources and results

    Attributes:
        metrics_collector: MetricsCollector instance
        orchestrator: TestOrchestrator instance
        suite_manager: TestSuiteManager instance
        base_test_path: Base path for test directories
        initialized: Whether the framework has been initialized
    """

    def __init__(self, base_test_path: Optional[str] = None):
        """
        Initialize the QA framework and its components.

        Args:
            base_test_path: Optional base path for test directories. If not provided,
                          will use default path based on package location.
        """
        self.metrics_collector = MetricsCollector()
        self.orchestrator = TestOrchestrator(self.metrics_collector)
        self.suite_manager = TestSuiteManager(
            self.orchestrator,
            self.metrics_collector
        )
        
        # Set base test path
        self.base_test_path = base_test_path or os.path.join(
            os.path.dirname(__file__),
            '..',
            'tests'
        )
        
        self.initialized = False
        logger.info("QA Framework created successfully")

    async def initialize(self) -> None:
        """
        Initialize the QA framework and discover test suites.
        Must be called before running any tests.
        """
        if self.initialized:
            logger.warning("QA Framework already initialized")
            return

        try:
            # Initialize test suites
            await self.suite_manager.initialize_suites(self.base_test_path)
            self.initialized = True
            logger.info("QA Framework initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize QA Framework: {e}")
            raise

    def _check_initialized(self) -> None:
        """Check if framework is initialized before operations."""
        if not self.initialized:
            raise RuntimeError(
                "QA Framework not initialized. Call initialize() first."
            )

    async def run_tests(
        self,
        categories: Optional[Union[TestCategory, List[TestCategory]]] = None,
        parallel: bool = True
    ) -> Dict[TestCategory, Dict[str, TestResult]]:
        """
        Run tests from specified categories or all categories.

        Args:
            categories: Optional category or list of categories to run.
                      If None, runs all categories in proper order.
            parallel: Whether to run test suites in parallel where possible.

        Returns:
            Dict mapping categories to their test results
        """
        self._check_initialized()

        if categories is None:
            # Run all suites in proper order
            return await self.suite_manager.run_all_suites()
        
        # Convert single category to list
        if isinstance(categories, TestCategory):
            categories = [categories]

        results = {}
        if parallel:
            # Run specified categories in parallel
            tasks = [
                self.suite_manager.run_suite(category)
                for category in categories
            ]
            suite_results = await asyncio.gather(*tasks)
            for category, result in zip(categories, suite_results):
                results[category] = result
        else:
            # Run categories sequentially
            for category in categories:
                results[category] = await self.suite_manager.run_suite(category)

        return results

    def get_test_summary(self) -> Dict:
        """
        Get comprehensive test execution summary.

        Returns:
            Dict containing summary of all test execution results
        """
        self._check_initialized()
        
        summary = {
            'metrics': self.metrics_collector.get_summary_metrics(),
            'suites': {}
        }

        for category in TestCategory:
            suite_info = self.suite_manager.get_suite_info(category)
            if suite_info:
                summary['suites'][category.name] = suite_info

        return summary

    async def verify_test_environment(self) -> Dict[str, bool]:
        """
        Verify the test environment is properly configured.

        Returns:
            Dict mapping verification checks to their status
        """
        verifications = {
            'test_directory': os.path.exists(self.base_test_path),
            'unit_tests': os.path.exists(
                os.path.join(self.base_test_path, 'unit')
            ),
            'integration_tests': os.path.exists(
                os.path.join(self.base_test_path, 'integration')
            ),
            'validation_tests': os.path.exists(
                os.path.join(self.base_test_path, 'validation')
            )
        }
        
        return verifications

    async def run_category_tests(
        self,
        category: TestCategory,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, TestResult]:
        """
        Run tests from a specific category with optional filtering.

        Args:
            category: Category of tests to run
            include_patterns: Optional list of patterns to include
            exclude_patterns: Optional list of patterns to exclude

        Returns:
            Dict mapping test IDs to their results
        """
        self._check_initialized()
        
        suite = self.suite_manager.suites.get(category)
        if not suite:
            raise ValueError(f"No test suite found for category: {category}")

        # Filter tests based on patterns
        tests_to_run = set(suite.execution_order)
        if include_patterns:
            tests_to_run = {
                test_id for test_id in tests_to_run
                if any(pattern in test_id for pattern in include_patterns)
            }
        if exclude_patterns:
            tests_to_run = {
                test_id for test_id in tests_to_run
                if not any(pattern in test_id for pattern in exclude_patterns)
            }

        results = {}
        for test_id in tests_to_run:
            try:
                result = await suite.adapter.run_test(test_id)
                results[test_id] = result
            except Exception as e:
                logger.error(f"Failed to run test {test_id}: {e}")
                results[test_id] = TestResult(
                    test_id=test_id,
                    status="ERROR",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error_message=str(e)
                )

        return results

