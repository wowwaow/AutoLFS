#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import shutil
import signal
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import psutil

from ..test_suite import TestSuite, TestCase, TestResult, TestStatus, TestSeverity

class SystemState(Enum):
    """System state enumeration"""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    SHUTDOWN = "shutdown"

class ResourceType(Enum):
    """System resource types"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESS = "process"
    PORT = "port"

@dataclass
class SystemResource:
    """System resource definition"""
    type: ResourceType
    identifier: str
    requirements: Dict[str, Any]
    allocated: bool = False
    handle: Any = None

@dataclass
class EnvironmentConfig:
    """System environment configuration"""
    base_dir: str
    temp_dir: str
    data_dir: str
    log_dir: str
    resources: List[SystemResource]
    env_vars: Dict[str, str] = field(default_factory=dict)
    cleanup_enabled: bool = True
    persist_logs: bool = True

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_usage: float
    memory_usage: float
    disk_io: Dict[str, int]
    network_io: Dict[str, int]
    process_count: int
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class SystemTestCase(TestCase):
    """Extended test case for system testing"""
    environment: EnvironmentConfig
    setup_timeout: int = 300
    teardown_timeout: int = 300
    required_state: SystemState = SystemState.READY
    validation_checks: List[Callable] = field(default_factory=list)
    metric_thresholds: Dict[str, float] = field(default_factory=dict)

class SystemTestRunner(TestSuite):
    """Test runner for system/end-to-end tests"""

    def __init__(
        self,
        name: str,
        config_path: Optional[str] = None,
        base_dir: Optional[str] = None
    ):
        super().__init__(name, config_path)
        self.base_dir = base_dir or os.path.join(
            tempfile.gettempdir(),
            f"system_test_{name}"
        )
        self.state = SystemState.UNKNOWN
        self.resources: Dict[str, SystemResource] = {}
        self.metrics_history: List[SystemMetrics] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self.initialize_logging()

    def add_system_test(
        self,
        test_func: Callable,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        severity: TestSeverity = TestSeverity.HIGH,
        timeout: int = 600,  # Longer default timeout for system tests
        retries: int = 0,
        dependencies: List[str] = None,
        setup: Optional[Callable] = None,
        teardown: Optional[Callable] = None,
        tags: Set[str] = None,
        environment: EnvironmentConfig,
        setup_timeout: int = 300,
        teardown_timeout: int = 300,
        required_state: SystemState = SystemState.READY,
        validation_checks: List[Callable] = None,
        metric_thresholds: Dict[str, float] = None
    ) -> str:
        """Add a system test case"""
        test_id = name or test_func.__name__
        if test_id in self.test_cases:
            raise ValueError(f"Test with ID {test_id} already exists")

        test_case = SystemTestCase(
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
            environment=environment,
            setup_timeout=setup_timeout,
            teardown_timeout=teardown_timeout,
            required_state=required_state,
            validation_checks=validation_checks or [],
            metric_thresholds=metric_thresholds or {}
        )

        self.test_cases[test_id] = test_case
        return test_id

    async def _setup_environment(
        self,
        config: EnvironmentConfig,
        timeout: int
    ) -> bool:
        """Set up test environment"""
        try:
            self.state = SystemState.INITIALIZING
            self.logger.info("Setting up test environment")

            # Create directories
            os.makedirs(config.base_dir, exist_ok=True)
            os.makedirs(config.temp_dir, exist_ok=True)
            os.makedirs(config.data_dir, exist_ok=True)
            os.makedirs(config.log_dir, exist_ok=True)

            # Set environment variables
            os.environ.update(config.env_vars)

            # Allocate resources
            async with asyncio.timeout(timeout):
                for resource in config.resources:
                    if not await self._allocate_resource(resource):
                        self.state = SystemState.ERROR
                        return False

            self.state = SystemState.READY
            return True

        except asyncio.TimeoutError:
            self.logger.error(f"Environment setup timed out after {timeout}s")
            self.state = SystemState.ERROR
            return False
        except Exception as e:
            self.logger.error(f"Environment setup failed: {e}")
            self.state = SystemState.ERROR
            return False

    async def _allocate_resource(self, resource: SystemResource) -> bool:
        """Allocate a system resource"""
        try:
            if resource.type == ResourceType.CPU:
                # CPU allocation logic
                cpu_count = psutil.cpu_count()
                requested = resource.requirements.get('cores', 1)
                if requested > cpu_count:
                    return False
                resource.allocated = True

            elif resource.type == ResourceType.MEMORY:
                # Memory allocation logic
                total_memory = psutil.virtual_memory().total
                requested = resource.requirements.get('bytes', 0)
                if requested > total_memory:
                    return False
                resource.allocated = True

            elif resource.type == ResourceType.PORT:
                # Port allocation logic
                port = resource.requirements.get('number')
                if await self._is_port_available(port):
                    resource.allocated = True
                    resource.handle = port

            self.resources[resource.identifier] = resource
            return resource.allocated

        except Exception as e:
            self.logger.error(
                f"Failed to allocate resource {resource.identifier}: {e}"
            )
            return False

    async def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        try:
            # Try to bind to the port
            server = await asyncio.start_server(
                lambda: None,
                'localhost',
                port
            )
            server.close()
            await server.wait_closed()
            return True
        except:
            return False

    async def _start_monitoring(self):
        """Start system monitoring"""
        async def monitor():
            while self.state not in [SystemState.ERROR, SystemState.SHUTDOWN]:
                try:
                    metrics = SystemMetrics(
                        cpu_usage=psutil.cpu_percent(),
                        memory_usage=psutil.virtual_memory().percent,
                        disk_io={
                            "read_bytes": psutil.disk_io_counters().read_bytes,
                            "write_bytes": psutil.disk_io_counters().write_bytes
                        },
                        network_io={
                            "bytes_sent": psutil.net_io_counters().bytes_sent,
                            "bytes_recv": psutil.net_io_counters().bytes_recv
                        },
                        process_count=len(psutil.pids())
                    )
                    self.metrics_history.append(metrics)
                except Exception as e:
                    self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(1)

        self._monitoring_task = asyncio.create_task(monitor())

    async def _stop_monitoring(self):
        """Stop system monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

    async def _validate_system_state(
        self,
        checks: List[Callable]
    ) -> Tuple[bool, List[str]]:
        """Run system state validation checks"""
        failures = []
        
        for check in checks:
            try:
                if not await check(self.state, self.resources):
                    failures.append(
                        f"Validation check failed: {check.__name__}"
                    )
            except Exception as e:
                failures.append(
                    f"Validation error in {check.__name__}: {str(e)}"
                )

        return len(failures) == 0, failures

    async def _check_metric_thresholds(
        self,
        thresholds: Dict[str, float]
    ) -> Tuple[bool, List[str]]:
        """Check system metrics against thresholds"""
        if not self.metrics_history:
            return True, []

        violations = []
        latest_metrics = self.metrics_history[-1]

        if "cpu" in thresholds and latest_metrics.cpu_usage > thresholds["cpu"]:
            violations.append(
                f"CPU usage {latest_metrics.cpu_usage}% exceeds threshold "
                f"{thresholds['cpu']}%"
            )

        if "memory" in thresholds and latest_metrics.memory_usage > thresholds["memory"]:
            violations.append(
                f"Memory usage {latest_metrics.memory_usage}% exceeds threshold "
                f"{thresholds['memory']}%"
            )

        return len(violations) == 0, violations

    async def _cleanup_environment(
        self,
        config: EnvironmentConfig,
        timeout: int
    ):
        """Clean up test environment"""
        try:
            self.logger.info("Cleaning up test environment")
            async with asyncio.timeout(timeout):
                # Release resources
                for resource in self.resources.values():
                    await self._release_resource(resource)

                # Clean up directories
                if config.cleanup_enabled:
                    if config.persist_logs:
                        # Move logs to permanent storage
                        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        log_archive = os.path.join(
                            self.base_dir,
                            f"logs_{timestamp}"
                        )
                        shutil.move(config.log_dir, log_archive)

                    # Remove temporary directories
                    shutil.rmtree(config.temp_dir, ignore_errors=True)
                    shutil.rmtree(config.data_dir, ignore_errors=True)

                # Clear environment variables
                for var in config.env_vars:
                    os.environ.pop(var, None)

        except asyncio.TimeoutError:
            self.logger.error(f"Environment cleanup timed out after {timeout}s")
        except Exception as e:
            self.logger.error(f"Environment cleanup failed: {e}")
        finally:
            self.state = SystemState.SHUTDOWN

    async def _release_resource(self, resource: SystemResource):
        """Release a system resource"""
        try:
            if resource.type == ResourceType.PORT and resource.handle:
                # Ensure port is released
                server = await asyncio.start_server(
                    lambda: None,
                    'localhost',
                    resource.handle
                )
                server.close()
                await server.wait_closed()

            resource.allocated = False
            resource.handle = None

        except Exception as e:
            self.logger.error(
                f"Failed to release resource {resource.identifier}: {e}"
            )

    async def run_test(self, test_id: str) -> TestResult:
        """Run a system test"""
        if not isinstance(self.test_cases[test_id], SystemTestCase):
            raise ValueError(f"Test {test_id} is not a system test")

        test_case = self.test_cases[test_id]

        try:
            # Set up environment
            if not await self._setup_environment(
                test_case.environment,
                test_case.setup_timeout
            ):
                return TestResult(
                    test_case=test_case,
                    status=TestStatus.ERROR,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    error=ValueError("Environment setup failed")
                )

            # Start monitoring
            await self._start_monitoring()

            # Run test
            result = await super().run_test(test_id)

            # Validate system state
            if result.status == TestStatus.PASSED:
                # Check validation rules
                valid, failures = await self._validate_system_state(
                    test_case.validation_checks
                )
                if not valid:
                    result.status = TestStatus.FAILED
                    result.error = ValueError(
                        "System validation failed:\n" + "\n".join(failures)
                    )

                # Check metric thresholds
                valid, violations = await self._check_metric_thresholds(
                    test_case.metric_thresholds
                )
                if not valid:
                    result.status = TestStatus.FAILED
                    result.error = ValueError(
                        "Metric thresholds exceeded:\n" + "\n".join(violations)
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
            # Stop monitoring
            await self._stop_monitoring()

            # Clean up environment
            await self._cleanup_environment(
                test_case.environment,
                test_case.teardown_timeout
            )

    def get_metrics(
        self,
        time_window: Optional[timedelta] = None
    ) -> List[SystemMetrics]:
        """Get system metrics within time window"""
        if not time_window:
            return self.metrics_history

        cutoff = datetime.utcnow() - time_window
        return [
            m for m in self.metrics_history
            if m.timestamp >= cutoff
        ]

    def get_resource_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all resources"""
        return {
            resource.identifier: {
                "type": resource.type.value,
                "allocated": resource.allocated,
                "requirements": resource.requirements
            }
            for resource in self.resources.values()
        }

if __name__ == "__main__":
    # Example usage
    async def main():
        # Example environment configuration
        env_config = EnvironmentConfig(
            base_dir="/tmp/system_test",
            temp_dir="/tmp/system_test/temp",
            data_dir="/tmp/system_test/data",
            log_dir="/tmp/system_test/logs",
            resources=[
                SystemResource(
                    type=ResourceType.CPU,
                    identifier="test_cpu",
                    requirements={"cores": 2}
                ),
                SystemResource(
                    type=ResourceType.MEMORY,
                    identifier="test_memory",
                    requirements={"bytes": 1024 * 1024 * 1024}
                ),
                SystemResource(
                    type=ResourceType.PORT,
                    identifier="test_port",
                    requirements={"number": 8080}
                )
            ],
            env_vars={
                "TEST_MODE": "system",
                "LOG_LEVEL": "debug"
            }
        )

        # System validation
        async def validate_system_state(
            state: SystemState,
            resources: Dict[str, SystemResource]
        ) -> bool:
            return state == SystemState.READY and all(
                r.allocated for r in resources.values()
            )

        # Create test runner
        runner = SystemTestRunner("example_system_tests")

        # Example test
        async def test_system():
            assert runner.state == SystemState.READY, "System not ready"
            assert runner.get_resource_status()["test_port"]["allocated"], \
                "Port not allocated"

        # Add test
        runner.add_system_test(
            test_system,
            name="test_system_resources",
            description="Test system resource allocation",
            severity=TestSeverity.CRITICAL,
            environment=env_config,
            validation_checks=[validate_system_state],
            metric_thresholds={
                "cpu": 80.0,
                "memory": 90.0
            }
        )

        # Run tests
        await runner.run_suite()
        
        # Generate report
        report = runner.generate_report()
        print(f"Test Report: {json.dumps(report, indent=2)}")

    asyncio.run(main())

