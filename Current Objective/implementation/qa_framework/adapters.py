"""
Test Adapter Module

This module provides adapters for integrating existing test files with the
QA framework, handling test discovery, dependency management, and result
conversion.

Author: WARP System
Created: 2025-05-31
"""

import asyncio
import importlib.util
import inspect
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from loguru import logger

from .orchestrator import TestResult


@dataclass
class TestMetadata:
    """Metadata for a discovered test."""
    id: str
    module: str
    name: str
    dependencies: List[str]
    async_test: bool
    setup_functions: List[str]
    teardown_functions: List[str]


class TestAdapter:
    """
    Adapts existing test files for use with the QA framework.

    This class is responsible for:
    - Discovering tests in existing files
    - Managing test dependencies
    - Converting test results
    - Handling test setup/teardown

    Attributes:
        test_modules: Dict mapping module names to their test collections
        discovered_tests: Dict mapping test IDs to their metadata
        dependency_graph: Dict tracking test dependencies
    """

    def __init__(self):
        """Initialize the TestAdapter."""
        self.test_modules: Dict[str, Any] = {}
        self.discovered_tests: Dict[str, TestMetadata] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}

    def discover_tests(self, test_dir: str) -> Dict[str, TestMetadata]:
        """
        Discover tests in the specified directory.

        Args:
            test_dir: Directory containing test files

        Returns:
            Dict mapping test IDs to their metadata
        """
        for root, _, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    self._process_test_file(os.path.join(root, file))

        # Build dependency graph after discovering all tests
        self._build_dependency_graph()
        return self.discovered_tests

    def _process_test_file(self, file_path: str) -> None:
        """
        Process a test file to extract test functions and metadata.

        Args:
            file_path: Path to the test file
        """
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.test_modules[module_name] = module

                # Process module for tests
                self._extract_tests_from_module(module, module_name)
        except Exception as e:
            logger.error(f"Error processing test file {file_path}: {e}")

    def _extract_tests_from_module(self, module: Any, module_name: str) -> None:
        """
        Extract test functions and their metadata from a module.

        Args:
            module: The imported test module
            module_name: Name of the module
        """
        for name, obj in inspect.getmembers(module):
            if name.startswith('test_') and (inspect.isfunction(obj) or inspect.iscoroutinefunction(obj)):
                test_id = f"{module_name}.{name}"
                
                # Extract test dependencies from docstring or markers
                dependencies = self._extract_dependencies(obj)
                
                # Determine if test is async
                is_async = inspect.iscoroutinefunction(obj)
                
                # Find setup/teardown functions
                setup_funcs = self._find_setup_functions(module, name)
                teardown_funcs = self._find_teardown_functions(module, name)
                
                # Create test metadata
                self.discovered_tests[test_id] = TestMetadata(
                    id=test_id,
                    module=module_name,
                    name=name,
                    dependencies=dependencies,
                    async_test=is_async,
                    setup_functions=setup_funcs,
                    teardown_functions=teardown_funcs
                )

    def _extract_dependencies(self, test_func: callable) -> List[str]:
        """
        Extract test dependencies from function metadata.

        Args:
            test_func: The test function to analyze

        Returns:
            List of test IDs that this test depends on
        """
        dependencies = []
        
        # Check docstring for dependencies
        if test_func.__doc__:
            for line in test_func.__doc__.split('\n'):
                if 'depends:' in line.lower():
                    deps = line.split(':', 1)[1].strip()
                    dependencies.extend(dep.strip() for dep in deps.split(','))

        # Check for dependency markers
        if hasattr(test_func, '_test_dependencies'):
            dependencies.extend(test_func._test_dependencies)

        return dependencies

    def _find_setup_functions(self, module: Any, test_name: str) -> List[str]:
        """
        Find setup functions for a test.

        Args:
            module: The test module
            test_name: Name of the test function

        Returns:
            List of setup function names
        """
        setup_funcs = []
        
        # Check for test-specific setup
        specific_setup = f"setup_{test_name[5:]}"  # Remove 'test_' prefix
        if hasattr(module, specific_setup):
            setup_funcs.append(specific_setup)
        
        # Check for module-level setup
        if hasattr(module, 'setup_module'):
            setup_funcs.append('setup_module')
        
        return setup_funcs

    def _find_teardown_functions(self, module: Any, test_name: str) -> List[str]:
        """
        Find teardown functions for a test.

        Args:
            module: The test module
            test_name: Name of the test function

        Returns:
            List of teardown function names
        """
        teardown_funcs = []
        
        # Check for test-specific teardown
        specific_teardown = f"teardown_{test_name[5:]}"  # Remove 'test_' prefix
        if hasattr(module, specific_teardown):
            teardown_funcs.append(specific_teardown)
        
        # Check for module-level teardown
        if hasattr(module, 'teardown_module'):
            teardown_funcs.append('teardown_module')
        
        return teardown_funcs

    def _build_dependency_graph(self) -> None:
        """Build the complete test dependency graph."""
        for test_id, metadata in self.discovered_tests.items():
            self.dependency_graph[test_id] = set(metadata.dependencies)

    async def run_test(self, test_id: str) -> TestResult:
        """
        Run a test with its setup and teardown functions.

        Args:
            test_id: ID of the test to run

        Returns:
            TestResult containing the test execution results
        """
        if test_id not in self.discovered_tests:
            raise ValueError(f"Unknown test ID: {test_id}")

        metadata = self.discovered_tests[test_id]
        module = self.test_modules[metadata.module]
        test_func = getattr(module, metadata.name)

        start_time = datetime.now()
        error_message = None
        status = "SUCCESS"

        try:
            # Run setup functions
            for setup_func in metadata.setup_functions:
                setup = getattr(module, setup_func)
                if inspect.iscoroutinefunction(setup):
                    await setup()
                else:
                    setup()

            # Run the test
            if metadata.async_test:
                await test_func()
            else:
                test_func()

        except Exception as e:
            status = "FAILURE"
            error_message = str(e)
            logger.error(f"Test {test_id} failed: {e}")

        finally:
            # Run teardown functions
            for teardown_func in metadata.teardown_functions:
                try:
                    teardown = getattr(module, teardown_func)
                    if inspect.iscoroutinefunction(teardown):
                        await teardown()
                    else:
                        teardown()
                except Exception as e:
                    logger.error(f"Teardown {teardown_func} failed for test {test_id}: {e}")

        end_time = datetime.now()

        return TestResult(
            test_id=test_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            error_message=error_message
        )

    def get_test_dependencies(self, test_id: str) -> Set[str]:
        """
        Get all dependencies for a test.

        Args:
            test_id: ID of the test to check

        Returns:
            Set of test IDs that this test depends on
        """
        return self.dependency_graph.get(test_id, set())

    def get_module_tests(self, module_name: str) -> List[str]:
        """
        Get all tests from a specific module.

        Args:
            module_name: Name of the module

        Returns:
            List of test IDs from the module
        """
        return [
            test_id for test_id, metadata in self.discovered_tests.items()
            if metadata.module == module_name
        ]

    def get_test_info(self, test_id: str) -> Optional[Dict]:
        """
        Get detailed information about a test.

        Args:
            test_id: ID of the test to get info for

        Returns:
            Dict containing test information if found, None otherwise
        """
        if test_id in self.discovered_tests:
            metadata = self.discovered_tests[test_id]
            return {
                'id': metadata.id,
                'module': metadata.module,
                'name': metadata.name,
                'dependencies': list(metadata.dependencies),
                'is_async': metadata.async_test,
                'setup': metadata.setup_functions,
                'teardown': metadata.teardown_functions
            }
        return None

