#!/usr/bin/env python3

import asyncio
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from unittest.mock import MagicMock

from ..test_suite import TestSuite, TestCase, TestResult, TestStatus, TestSeverity

class ComponentState(Enum):
    """Component lifecycle states"""
    INITIALIZED = "initialized"
    READY = "ready"
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class Component:
    """Integration test component definition"""
    name: str
    setup: Callable
    teardown: Callable
    dependencies: List[str] = field(default_factory=list)
    state: ComponentState = ComponentState.INITIALIZED
    instance: Any = None
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StateCheckpoint:
    """Component state checkpoint"""
    timestamp: datetime
    components: Dict[str, Any]
    resources: Dict[str, Any]
    metadata: Dict[str, Any]

@dataclass
class IntegrationTestCase(TestCase):
    """Extended test case for integration testing"""
    components: List[Component]
    required_state: Dict[str, ComponentState]
    state_validations: List[Callable]
    cleanup_order: List[str] = field(default_factory=list)
    persistence_path: Optional[str] = None

class IntegrationTestRunner(TestSuite):
    """Test runner for integration tests"""

    def __init__(
        self,
        name: str,
        config_path: Optional[str] = None,
        workspace_dir: Optional[str] = None
    ):
        super().__init__(name, config_path)
        self.components: Dict[str, Component] = {}
        self.state_history: List[StateCheckpoint] = []
        self.workspace_dir = workspace_dir or tempfile.mkdtemp()
        self.resources: Dict[str, Any] = {}

    def add_integration_test(
        self,
        test_func: Callable,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        severity: TestSeverity = TestSeverity.MEDIUM,
        timeout: int = 300,  # Longer default timeout for integration tests
        retries: int = 0,
        dependencies: List[str] = None,
        setup: Optional[Callable] = None,
        teardown: Optional[Callable] = None,
        tags: Set[str] = None,
        components: List[Component] = None,
        required_state: Dict[str, ComponentState] = None,
        state_validations: List[Callable] = None,
        cleanup_order: List[str] = None,
        persistence_path: Optional[str] = None
    ) -> str:
        """Add an integration test case"""
        test_id = name or test_func.__name__
        if test_id in self.test_cases:
            raise ValueError(f"Test with ID {test_id} already exists")

        test_case = IntegrationTestCase(
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
            components=components or [],
            required_state=required_state or {},
            state_validations=state_validations or [],
            cleanup_order=cleanup_order or [],
            persistence_path=persistence_path
        )

        self.test_cases[test_id] = test_case
        return test_id

    async def _setup_components(
        self,
        components: List[Component],
        required_state: Dict[str, ComponentState]
    ) -> bool:
        """Set up test components in dependency order"""
        # Build dependency graph
        graph = {comp.name: comp.dependencies for comp in components}
        seen = set()
        active = set()

        async def setup_component(comp: Component) -> bool:
            """Set up a single component with dependencies"""
            if comp.name in active:
                raise ValueError(
                    f"Circular dependency detected for component {comp.name}"
                )
            if comp.name in seen:
                return comp.state == required_state.get(
                    comp.name, ComponentState.READY
                )

            active.add(comp.name)

            # Set up dependencies first
            for dep in comp.dependencies:
                dep_comp = next(
                    (c for c in components if c.name == dep), None
                )
                if not dep_comp:
                    raise ValueError(
                        f"Dependency {dep} not found for component {comp.name}"
                    )
                if not await setup_component(dep_comp):
                    return False

            try:
                # Set up component
                self.logger.info(f"Setting up component {comp.name}")
                comp.instance = await comp.setup()
                comp.state = ComponentState.READY
                self.components[comp.name] = comp
                
                # Verify required state
                if comp.name in required_state:
                    if comp.state != required_state[comp.name]:
                        self.logger.error(
                            f"Component {comp.name} failed to reach required state"
                        )
                        return False

                seen.add(comp.name)
                active.remove(comp.name)
                return True

            except Exception as e:
                self.logger.error(
                    f"Failed to set up component {comp.name}: {e}"
                )
                comp.state = ComponentState.ERROR
                active.remove(comp.name)
                return False

        # Set up all components
        success = all(
            await setup_component(comp)
            for comp in components
        )

        return success

    async def _create_checkpoint(self) -> StateCheckpoint:
        """Create a checkpoint of current state"""
        checkpoint = StateCheckpoint(
            timestamp=datetime.utcnow(),
            components={
                name: {
                    "state": comp.state,
                    "config": comp.config.copy()
                }
                for name, comp in self.components.items()
            },
            resources=self.resources.copy(),
            metadata={"workspace": self.workspace_dir}
        )
        
        self.state_history.append(checkpoint)
        return checkpoint

    async def _restore_checkpoint(self, checkpoint: StateCheckpoint):
        """Restore state from a checkpoint"""
        # Restore component states
        for name, state in checkpoint.components.items():
            if name in self.components:
                comp = self.components[name]
                comp.state = state["state"]
                comp.config = state["config"].copy()

        # Restore resources
        self.resources = checkpoint.resources.copy()

        # Restore workspace if needed
        if checkpoint.metadata["workspace"] != self.workspace_dir:
            if os.path.exists(checkpoint.metadata["workspace"]):
                shutil.copytree(
                    checkpoint.metadata["workspace"],
                    self.workspace_dir,
                    dirs_exist_ok=True
                )

    async def _validate_state(
        self,
        validations: List[Callable]
    ) -> Tuple[bool, List[str]]:
        """Run state validations"""
        failures = []
        
        for validate in validations:
            try:
                if not await validate(self.components, self.resources):
                    failures.append(
                        f"Validation failed: {validate.__name__}"
                    )
            except Exception as e:
                failures.append(
                    f"Validation error in {validate.__name__}: {str(e)}"
                )

        return len(failures) == 0, failures

    async def _cleanup_components(
        self,
        components: List[Component],
        cleanup_order: List[str]
    ):
        """Clean up components in specified order"""
        # Use specified order or reverse dependency order
        if cleanup_order:
            ordered_components = [
                comp for name in cleanup_order
                for comp in components
                if comp.name == name
            ]
        else:
            ordered_components = list(reversed(components))

        for comp in ordered_components:
            try:
                self.logger.info(f"Cleaning up component {comp.name}")
                await comp.teardown()
                comp.state = ComponentState.STOPPED
            except Exception as e:
                self.logger.error(
                    f"Failed to clean up component {comp.name}: {e}"
                )
                comp.state = ComponentState.ERROR

    async def run_test(self, test_id: str) -> TestResult:
        """Run an integration test"""
        if not isinstance(self.test_cases[test_id], IntegrationTestCase):
            raise ValueError(f"Test {test_id} is not an integration test")

        test_case = self.test_cases[test_id]
        checkpoint = None

        try:
            # Set up components
            if not await self._setup_components(
                test_case.components,
                test_case.required_state
            ):
                return TestResult(
                    test_case=test_case,
                    status=TestStatus.ERROR,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    error=ValueError("Component setup failed")
                )

            # Create state checkpoint
            checkpoint = await self._create_checkpoint()

            # Run test
            result = await super().run_test(test_id)

            # Validate state if test passed
            if result.status == TestStatus.PASSED:
                valid, failures = await self._validate_state(
                    test_case.state_validations
                )
                if not valid:
                    result.status = TestStatus.FAILED
                    result.error = ValueError(
                        "State validation failed:\n" + "\n".join(failures)
                    )

            return result

        except Exception as e:
            return TestResult(
                test_case=test_case,
                status=TestStatus.ERROR,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                error=e
            )

        finally:
            # Restore checkpoint on failure if needed
            if (checkpoint and 
                result.status in [TestStatus.FAILED, TestStatus.ERROR]):
                await self._restore_checkpoint(checkpoint)

            # Clean up components
            await self._cleanup_components(
                test_case.components,
                test_case.cleanup_order
            )

    def get_component(self, name: str) -> Optional[Component]:
        """Get a component by name"""
        return self.components.get(name)

    def get_component_state(self, name: str) -> Optional[ComponentState]:
        """Get a component's current state"""
        component = self.components.get(name)
        return component.state if component else None

if __name__ == "__main__":
    # Example usage
    async def main():
        # Example components
        class DatabaseComponent:
            async def initialize(self):
                return "DB Connection"

            async def cleanup(self):
                pass

        class ApiComponent:
            async def initialize(self, db):
                return "API Server"

            async def cleanup(self):
                pass

        # Component setup functions
        async def setup_db():
            db = DatabaseComponent()
            return await db.initialize()

        async def setup_api():
            api = ApiComponent()
            return await api.initialize(
                get_component("database").instance
            )

        # Component definitions
        db_component = Component(
            name="database",
            setup=setup_db,
            teardown=lambda: None,
            config={"url": "test://db"}
        )

        api_component = Component(
            name="api",
            setup=setup_api,
            teardown=lambda: None,
            dependencies=["database"],
            config={"port": 8000}
        )

        # State validation
        async def validate_components(
            components: Dict[str, Component],
            resources: Dict[str, Any]
        ) -> bool:
            return all(
                comp.state == ComponentState.READY
                for comp in components.values()
            )

        # Create test runner
        runner = IntegrationTestRunner("example_integration_tests")

        # Example test
        async def test_api_with_db():
            api = get_component("api").instance
            db = get_component("database").instance
            assert api and db, "Components not initialized"

        # Add test
        runner.add_integration_test(
            test_api_with_db,
            name="test_api_db_integration",
            description="Test API with database integration",
            severity=TestSeverity.HIGH,
            components=[db_component, api_component],
            required_state={
                "database": ComponentState.READY,
                "api": ComponentState.READY
            },
            state_validations=[validate_components],
            cleanup_order=["api", "database"]
        )

        # Run tests
        await runner.run_suite()
        
        # Generate report
        report = runner.generate_report()
        print(f"Test Report: {json.dumps(report, indent=2)}")

    asyncio.run(main())

