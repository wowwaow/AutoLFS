#!/usr/bin/env python3

import asyncio
import inspect
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

class TestSeverity(Enum):
    """Test severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class TestCase:
    """Individual test case definition"""
    id: str
    name: str
    description: str
    severity: TestSeverity
    test_func: Callable
    timeout: int = 60
    retries: int = 0
    dependencies: List[str] = field(default_factory=list)
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    tags: Set[str] = field(default_factory=set)

@dataclass
class TestResult:
    """Result of a test execution"""
    test_case: TestCase
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[Exception] = None
    output: Optional[Any] = None
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

class TestSuite(ABC):
    """Base class for test suites"""

    def __init__(self, name: str, config_path: Optional[str] = None):
        self.name = name
        self.logger = logging.getLogger(name)
        self.test_cases: Dict[str, TestCase] = {}
        self.results: Dict[str, TestResult] = {}
        self.config = self._load_config(config_path)
        self.initialize_logging()

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load test suite configuration"""
        if not config_path:
            config_path = os.path.join(
                os.path.dirname(__file__),
                'config',
                'test_config.json'
            )

        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}

    def initialize_logging(self):
        """Initialize logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{self.name}.log'),
                logging.StreamHandler()
            ]
        )

    def add_test(
        self,
        test_func: Callable,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        severity: TestSeverity = TestSeverity.MEDIUM,
        timeout: int = 60,
        retries: int = 0,
        dependencies: List[str] = None,
        setup: Optional[Callable] = None,
        teardown: Optional[Callable] = None,
        tags: Set[str] = None
    ) -> str:
        """Add a test case to the suite"""
        # Generate test ID if not provided
        test_id = name or test_func.__name__
        if test_id in self.test_cases:
            raise ValueError(f"Test with ID {test_id} already exists")

        # Create test case
        test_case = TestCase(
            id=test_id,
            name=name or test_func.__name__,
            description=description or test_func.__doc__ or "",
            severity=severity,
            test_func=test_func,
            timeout=timeout,
            retries=retries,
            dependencies=dependencies or [],
            setup=setup,
            teardown=teardown,
            tags=tags or set()
        )

        self.test_cases[test_id] = test_case
        return test_id

    async def run_test(self, test_id: str) -> TestResult:
        """Run a single test case"""
        if test_id not in self.test_cases:
            raise ValueError(f"Test {test_id} not found")

        test_case = self.test_cases[test_id]
        start_time = datetime.utcnow()

        # Initialize result
        result = TestResult(
            test_case=test_case,
            status=TestStatus.RUNNING,
            start_time=start_time
        )
        self.results[test_id] = result

        try:
            # Run setup if provided
            if test_case.setup:
                await self._run_with_timeout(test_case.setup)

            # Run test with retries
            for attempt in range(test_case.retries + 1):
                try:
                    output = await self._run_with_timeout(
                        test_case.test_func,
                        timeout=test_case.timeout
                    )
                    result.status = TestStatus.PASSED
                    result.output = output
                    break
                except Exception as e:
                    if attempt < test_case.retries:
                        self.logger.warning(
                            f"Test {test_id} failed attempt {attempt + 1}, retrying..."
                        )
                        continue
                    result.status = TestStatus.FAILED
                    result.error = e

        except asyncio.TimeoutError:
            result.status = TestStatus.ERROR
            result.error = asyncio.TimeoutError(
                f"Test exceeded timeout of {test_case.timeout} seconds"
            )
        except Exception as e:
            result.status = TestStatus.ERROR
            result.error = e
        finally:
            # Run teardown if provided
            if test_case.teardown:
                try:
                    await self._run_with_timeout(test_case.teardown)
                except Exception as e:
                    self.logger.error(f"Teardown failed for test {test_id}: {e}")

            result.end_time = datetime.utcnow()
            self._log_test_result(test_id, result)

        return result

    async def _run_with_timeout(
        self,
        func: Callable,
        timeout: Optional[int] = None
    ) -> Any:
        """Run a function with timeout"""
        if asyncio.iscoroutinefunction(func):
            return await asyncio.wait_for(func(), timeout=timeout)
        else:
            return await asyncio.get_event_loop().run_in_executor(
                None, func
            )

    def _log_test_result(self, test_id: str, result: TestResult):
        """Log test execution result"""
        duration = (result.end_time - result.start_time).total_seconds()
        self.logger.info(
            f"Test {test_id} {result.status.value} "
            f"(duration: {duration:.2f}s)"
        )
        if result.error:
            self.logger.error(
                f"Test {test_id} error: {str(result.error)}"
            )

    async def run_suite(
        self,
        test_ids: Optional[List[str]] = None,
        tags: Optional[Set[str]] = None
    ) -> Dict[str, TestResult]:
        """Run multiple test cases"""
        if test_ids is None:
            # Run all tests if no specific IDs provided
            test_ids = list(self.test_cases.keys())

        # Filter by tags if provided
        if tags:
            test_ids = [
                test_id for test_id in test_ids
                if any(tag in self.test_cases[test_id].tags for tag in tags)
            ]

        # Sort tests by dependencies
        sorted_tests = self._sort_tests_by_dependencies(test_ids)

        # Run tests in order
        for test_id in sorted_tests:
            await self.run_test(test_id)

        return self.results

    def _sort_tests_by_dependencies(self, test_ids: List[str]) -> List[str]:
        """Sort tests based on their dependencies"""
        # Build dependency graph
        graph = {
            test_id: self.test_cases[test_id].dependencies
            for test_id in test_ids
        }

        # Detect cycles
        visited = set()
        temp = set()

        def has_cycle(node: str) -> bool:
            if node in temp:
                return True
            if node in visited:
                return False
            temp.add(node)
            for dep in graph.get(node, []):
                if has_cycle(dep):
                    return True
            temp.remove(node)
            visited.add(node)
            return False

        # Check for cycles
        for test_id in test_ids:
            if has_cycle(test_id):
                raise ValueError(f"Circular dependency detected in test {test_id}")

        # Topological sort
        sorted_tests = []
        visited = set()

        def visit(node: str):
            if node in visited:
                return
            for dep in graph.get(node, []):
                visit(dep)
            visited.add(node)
            sorted_tests.append(node)

        for test_id in test_ids:
            visit(test_id)

        return sorted_tests

    def get_suite_status(self) -> Dict[str, Any]:
        """Get current status of the test suite"""
        total_tests = len(self.test_cases)
        completed_tests = len(self.results)
        passed_tests = len([
            r for r in self.results.values()
            if r.status == TestStatus.PASSED
        ])

        status_counts = {
            status: len([
                r for r in self.results.values()
                if r.status == status
            ])
            for status in TestStatus
        }

        return {
            "total_tests": total_tests,
            "completed_tests": completed_tests,
            "passed_tests": passed_tests,
            "pass_rate": (passed_tests / completed_tests * 100) 
                        if completed_tests > 0 else 0,
            "status_counts": {
                status.value: count
                for status, count in status_counts.items()
            }
        }

    def generate_report(self) -> Dict[str, Any]:
        """Generate test execution report"""
        # Overall statistics
        stats = self.get_suite_status()

        # Detailed results by severity
        results_by_severity = {}
        for severity in TestSeverity:
            severity_results = [
                {
                    "id": test_id,
                    "name": result.test_case.name,
                    "status": result.status.value,
                    "duration": (
                        result.end_time - result.start_time
                    ).total_seconds() if result.end_time else None,
                    "error": str(result.error) if result.error else None
                }
                for test_id, result in self.results.items()
                if result.test_case.severity == severity
            ]
            if severity_results:
                results_by_severity[severity.value] = severity_results

        # Failed test details
        failed_tests = [
            {
                "id": test_id,
                "name": result.test_case.name,
                "severity": result.test_case.severity.value,
                "error": str(result.error),
                "duration": (
                    result.end_time - result.start_time
                ).total_seconds() if result.end_time else None
            }
            for test_id, result in self.results.items()
            if result.status in [TestStatus.FAILED, TestStatus.ERROR]
        ]

        return {
            "suite_name": self.name,
            "execution_time": datetime.utcnow().isoformat(),
            "statistics": stats,
            "results_by_severity": results_by_severity,
            "failed_tests": failed_tests
        }

if __name__ == "__main__":
    # Example usage
    class ExampleTestSuite(TestSuite):
        async def test_example(self):
            assert True, "This test should pass"

        async def test_with_error(self):
            raise ValueError("This test should fail")

    async def main():
        suite = ExampleTestSuite("example_suite")
        
        # Add test cases
        suite.add_test(
            suite.test_example,
            name="test_example",
            description="Example test case",
            severity=TestSeverity.LOW
        )
        suite.add_test(
            suite.test_with_error,
            name="test_with_error",
            description="Example failing test",
            severity=TestSeverity.HIGH
        )

        # Run suite
        await suite.run_suite()
        
        # Generate report
        report = suite.generate_report()
        print(f"Test Report: {json.dumps(report, indent=2)}")

    asyncio.run(main())

