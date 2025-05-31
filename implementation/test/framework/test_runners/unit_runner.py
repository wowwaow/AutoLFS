#!/usr/bin/env python3

import asyncio
import inspect
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Type
from unittest.mock import MagicMock, patch

from ..test_suite import TestSuite, TestCase, TestResult, TestStatus, TestSeverity

@dataclass
class MockConfig:
    """Mock configuration for a test"""
    target: str
    return_value: Any = None
    side_effect: Optional[Callable] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UnitTestCase(TestCase):
    """Extended test case for unit testing"""
    mocks: List[MockConfig] = field(default_factory=list)
    component_path: Optional[str] = None
    isolation_level: str = "function"  # "function", "module", or "class"

class UnitTestRunner(TestSuite):
    """Test runner for unit tests"""

    def __init__(
        self,
        name: str,
        config_path: Optional[str] = None,
        mock_factory: Optional[Callable] = None
    ):
        super().__init__(name, config_path)
        self.mock_factory = mock_factory or MagicMock
        self.active_mocks: Dict[str, Any] = {}
        self.isolation_stack: List[Dict[str, Any]] = []

    def add_unit_test(
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
        tags: Set[str] = None,
        mocks: List[MockConfig] = None,
        component_path: Optional[str] = None,
        isolation_level: str = "function"
    ) -> str:
        """Add a unit test case"""
        test_id = name or test_func.__name__
        if test_id in self.test_cases:
            raise ValueError(f"Test with ID {test_id} already exists")

        test_case = UnitTestCase(
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
            tags=tags or set(),
            mocks=mocks or [],
            component_path=component_path,
            isolation_level=isolation_level
        )

        self.test_cases[test_id] = test_case
        return test_id

    async def _setup_mocks(self, test_case: UnitTestCase) -> List[Any]:
        """Set up mocks for a test case"""
        active_patches = []
        
        for mock_config in test_case.mocks:
            # Create mock object
            mock = self.mock_factory()
            
            # Configure mock
            if mock_config.return_value is not None:
                mock.return_value = mock_config.return_value
            if mock_config.side_effect is not None:
                mock.side_effect = mock_config.side_effect
            for attr, value in mock_config.attributes.items():
                setattr(mock, attr, value)

            # Apply patch
            patcher = patch(mock_config.target, mock)
            active_patches.append(patcher)
            
            # Start patch
            mock = patcher.start()
            self.active_mocks[mock_config.target] = mock

        return active_patches

    async def _teardown_mocks(self, patches: List[Any]):
        """Clean up mocks after test execution"""
        for patcher in patches:
            patcher.stop()
        self.active_mocks.clear()

    async def _setup_isolation(self, test_case: UnitTestCase):
        """Set up test isolation"""
        state = {}
        
        if test_case.isolation_level == "module":
            # Save module state
            if test_case.component_path:
                module = sys.modules.get(test_case.component_path)
                if module:
                    state['module'] = {
                        name: getattr(module, name)
                        for name in dir(module)
                        if not name.startswith('_')
                    }

        elif test_case.isolation_level == "class":
            # Save class state
            if test_case.component_path:
                module_path, class_name = test_case.component_path.rsplit('.', 1)
                module = sys.modules.get(module_path)
                if module and hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    state['class'] = {
                        name: getattr(cls, name)
                        for name in dir(cls)
                        if not name.startswith('_')
                    }

        self.isolation_stack.append(state)

    async def _restore_isolation(self, test_case: UnitTestCase):
        """Restore state after test execution"""
        if not self.isolation_stack:
            return

        state = self.isolation_stack.pop()
        
        if test_case.isolation_level == "module":
            # Restore module state
            if test_case.component_path and 'module' in state:
                module = sys.modules.get(test_case.component_path)
                if module:
                    for name, value in state['module'].items():
                        setattr(module, name, value)

        elif test_case.isolation_level == "class":
            # Restore class state
            if test_case.component_path and 'class' in state:
                module_path, class_name = test_case.component_path.rsplit('.', 1)
                module = sys.modules.get(module_path)
                if module and hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    for name, value in state['class'].items():
                        setattr(cls, name, value)

    async def run_test(self, test_id: str) -> TestResult:
        """Run a unit test with mocking and isolation"""
        if not isinstance(self.test_cases[test_id], UnitTestCase):
            raise ValueError(f"Test {test_id} is not a unit test")

        test_case = self.test_cases[test_id]
        patches = []

        try:
            # Setup isolation
            await self._setup_isolation(test_case)
            
            # Setup mocks
            patches = await self._setup_mocks(test_case)
            
            # Run test
            result = await super().run_test(test_id)
            
            # Verify mocks
            await self._verify_mocks(test_case, result)
            
            return result

        finally:
            # Cleanup
            await self._teardown_mocks(patches)
            await self._restore_isolation(test_case)

    async def _verify_mocks(self, test_case: UnitTestCase, result: TestResult):
        """Verify mock interactions"""
        mock_errors = []

        for mock_config in test_case.mocks:
            mock = self.active_mocks.get(mock_config.target)
            if mock and not mock.called:
                mock_errors.append(
                    f"Mock '{mock_config.target}' was never called"
                )

        if mock_errors:
            if result.status == TestStatus.PASSED:
                result.status = TestStatus.FAILED
                result.error = ValueError(
                    "Mock verification failed:\n" + "\n".join(mock_errors)
                )

    def get_mock(self, target: str) -> Optional[Any]:
        """Get active mock by target"""
        return self.active_mocks.get(target)

    def reset_mocks(self):
        """Reset all active mocks"""
        for mock in self.active_mocks.values():
            mock.reset_mock()

if __name__ == "__main__":
    # Example usage
    async def main():
        runner = UnitTestRunner("example_unit_tests")

        # Example component to test
        class Calculator:
            def add(self, a: int, b: int) -> int:
                return a + b

        # Example test with mock
        async def test_calculator():
            calc = Calculator()
            assert calc.add(2, 3) == 5, "Addition failed"

        # Add test with mock
        runner.add_unit_test(
            test_calculator,
            name="test_calculator_add",
            description="Test calculator addition",
            severity=TestSeverity.HIGH,
            mocks=[
                MockConfig(
                    target="calculator.external_service",
                    return_value={"status": "ok"}
                )
            ],
            component_path="calculator.Calculator",
            isolation_level="class"
        )

        # Run tests
        await runner.run_suite()
        
        # Generate report
        report = runner.generate_report()
        print(f"Test Report: {report}")

    asyncio.run(main())

