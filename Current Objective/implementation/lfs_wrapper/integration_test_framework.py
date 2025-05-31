"""
Integration test framework for LFS/BLFS build system.

Provides test case management, automation, environment setup,
and result collection capabilities.

Dependencies:
    - PyYAML>=6.0
    - psutil>=5.8
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import psutil
import yaml

from .exceptions import (
    TestEnvironmentError,
    TestExecutionError,
    ValidationError
)
from .validation_manager import (
    ValidationManager,
    ValidationReport,
    ValidationSeverity
)


class TestCaseStatus(Enum):
    """Test case execution status."""
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    PASSED = auto()
    FAILED = auto()
    SKIPPED = auto()
    ERROR = auto()


class TestCategory(Enum):
    """Test case categories."""
    LFS = auto()
    BLFS = auto()
    GAMING = auto()
    CROSS_COMPONENT = auto()
    ERROR_HANDLING = auto()


@dataclass
class TestEnvironment:
    """Test environment configuration."""
    work_dir: Path
    lfs_root: Path
    blfs_root: Path
    config: Dict
    temp_dir: Path = field(default_factory=lambda: Path(tempfile.mkdtemp()))
    initialized: bool = False
    cleanup_required: bool = True


@dataclass
class TestCase:
    """Test case definition."""
    id: str
    name: str
    category: TestCategory
    description: str
    prerequisites: List[str]
    steps: List[Dict[str, str]]
    validation_steps: List[Dict[str, str]]
    cleanup_steps: List[Dict[str, str]]
    expected_results: Dict[str, str]
    timeout: int = 3600  # Default 1 hour timeout


@dataclass
class TestResult:
    """Test execution results."""
    test_case: TestCase
    status: TestCaseStatus
    start_time: float
    end_time: float
    output: str
    error: Optional[str] = None
    validation_report: Optional[ValidationReport] = None
    metrics: Dict = field(default_factory=dict)


@dataclass
class TestSuiteResult:
    """Complete test suite results."""
    results: List[TestResult]
    summary: Dict[TestCaseStatus, int]
    start_time: float
    end_time: float
    metrics: Dict


class IntegrationTestFramework:
    """
    Manages integration test execution.

    Handles test case management, environment setup, test execution,
    and result collection.

    Attributes:
        validation_manager (ValidationManager): Validation system
        config (Dict): Test framework configuration
        logger (logging.Logger): Logger instance
    """

    def __init__(self, validation_manager: ValidationManager, config: Dict):
        """Initialize test framework."""
        self.validation_manager = validation_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.environment: Optional[TestEnvironment] = None

    def setup_environment(self) -> None:
        """
        Set up test environment.

        Raises:
            TestEnvironmentError: If environment setup fails
        """
        try:
            # Create work directory structure
            work_dir = Path(self.config['test']['work_dir'])
            work_dir.mkdir(parents=True, exist_ok=True)
            
            # Set up LFS/BLFS roots
            lfs_root = work_dir / "lfs"
            blfs_root = work_dir / "blfs"
            lfs_root.mkdir(exist_ok=True)
            blfs_root.mkdir(exist_ok=True)
            
            # Initialize environment
            self.environment = TestEnvironment(
                work_dir=work_dir,
                lfs_root=lfs_root,
                blfs_root=blfs_root,
                config=self.config
            )
            
            # Set up required directory structure
            self._setup_directories()
            
            # Initialize environment state
            self._initialize_environment()
            
            self.environment.initialized = True
            
        except Exception as e:
            raise TestEnvironmentError(f"Environment setup failed: {e}")

    def load_test_cases(self, directory: Path) -> List[TestCase]:
        """
        Load test cases from directory.

        Args:
            directory: Directory containing test case YAML files

        Returns:
            List[TestCase]: Loaded test cases
        """
        test_cases = []
        
        for test_file in directory.glob("*.yaml"):
            try:
                with open(test_file) as f:
                    data = yaml.safe_load(f)
                    test_cases.append(TestCase(
                        id=data['id'],
                        name=data['name'],
                        category=TestCategory[data['category']],
                        description=data['description'],
                        prerequisites=data['prerequisites'],
                        steps=data['steps'],
                        validation_steps=data['validation_steps'],
                        cleanup_steps=data['cleanup_steps'],
                        expected_results=data['expected_results'],
                        timeout=data.get('timeout', 3600)
                    ))
            except Exception as e:
                self.logger.error(f"Failed to load test case {test_file}: {e}")
        
        return test_cases

    def run_test_suite(
        self,
        test_cases: List[TestCase],
        continue_on_error: bool = False
    ) -> TestSuiteResult:
        """
        Execute a test suite.

        Args:
            test_cases: Test cases to execute
            continue_on_error: Whether to continue after test failures

        Returns:
            TestSuiteResult: Test suite execution results

        Raises:
            TestExecutionError: If test execution fails
        """
        if not self.environment or not self.environment.initialized:
            raise TestEnvironmentError("Test environment not initialized")
        
        suite_start = time.time()
        results = []
        suite_metrics = {
            'total_tests': len(test_cases),
            'executed_tests': 0,
            'system_metrics': {}
        }
        
        try:
            for test_case in test_cases:
                try:
                    result = self.run_test_case(test_case)
                    results.append(result)
                    suite_metrics['executed_tests'] += 1
                    
                    if (result.status in [TestCaseStatus.FAILED, TestCaseStatus.ERROR]
                            and not continue_on_error):
                        break
                        
                except Exception as e:
                    self.logger.error(f"Test case {test_case.id} failed: {e}")
                    if not continue_on_error:
                        raise
            
            # Collect system metrics
            suite_metrics['system_metrics'] = self._collect_system_metrics()
            
            # Create summary
            summary = {
                status: len([r for r in results if r.status == status])
                for status in TestCaseStatus
            }
            
            return TestSuiteResult(
                results=results,
                summary=summary,
                start_time=suite_start,
                end_time=time.time(),
                metrics=suite_metrics
            )
            
        except Exception as e:
            raise TestExecutionError(f"Test suite execution failed: {e}")

    def run_test_case(self, test_case: TestCase) -> TestResult:
        """
        Execute a single test case.

        Args:
            test_case: Test case to execute

        Returns:
            TestResult: Test execution results

        Raises:
            TestExecutionError: If test execution fails
        """
        start_time = time.time()
        output = []
        
        try:
            # Check prerequisites
            for prereq in test_case.prerequisites:
                if not self._check_prerequisite(prereq):
                    return TestResult(
                        test_case=test_case,
                        status=TestCaseStatus.SKIPPED,
                        start_time=start_time,
                        end_time=time.time(),
                        output="Prerequisites not met",
                        metrics={'skipped_reason': 'prerequisites'}
                    )
            
            # Execute test steps
            for step in test_case.steps:
                step_output = self._execute_step(step)
                output.append(f"Step '{step['name']}': {step_output}")
            
            # Run validation steps
            validation_report = None
            for step in test_case.validation_steps:
                validation_result = self._execute_validation(step)
                if validation_result:
                    validation_report = validation_result
                    output.append(
                        f"Validation '{step['name']}': {validation_result}"
                    )
            
            # Check results
            success = self._verify_results(test_case.expected_results)
            status = TestCaseStatus.PASSED if success else TestCaseStatus.FAILED
            
            # Collect metrics
            metrics = self._collect_test_metrics(test_case)
            
            # Execute cleanup
            self._execute_cleanup(test_case.cleanup_steps)
            
            return TestResult(
                test_case=test_case,
                status=status,
                start_time=start_time,
                end_time=time.time(),
                output="\n".join(output),
                validation_report=validation_report,
                metrics=metrics
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                status=TestCaseStatus.ERROR,
                start_time=start_time,
                end_time=time.time(),
                output="\n".join(output),
                error=str(e),
                metrics={'error_type': type(e).__name__}
            )

    def cleanup_environment(self) -> None:
        """Clean up test environment."""
        if not self.environment:
            return
            
        try:
            if self.environment.cleanup_required:
                shutil.rmtree(self.environment.temp_dir)
                if self.environment.work_dir.exists():
                    shutil.rmtree(self.environment.work_dir)
        except Exception as e:
            self.logger.error(f"Environment cleanup failed: {e}")

    def _setup_directories(self) -> None:
        """Set up required directory structure."""
        if not self.environment:
            raise TestEnvironmentError("Environment not initialized")
            
        required_dirs = [
            self.environment.work_dir / "scripts",
            self.environment.work_dir / "logs",
            self.environment.work_dir / "results",
            self.environment.lfs_root / "sources",
            self.environment.lfs_root / "tools",
            self.environment.blfs_root / "packages",
            self.environment.blfs_root / "sources"
        ]
        
        for directory in required_dirs:
            directory.mkdir(parents=True, exist_ok=True)

    def _initialize_environment(self) -> None:
        """Initialize environment state."""
        if not self.environment:
            raise TestEnvironmentError("Environment not initialized")
            
        # Set up environment variables
        os.environ.update({
            'LFS': str(self.environment.lfs_root),
            'BLFS': str(self.environment.blfs_root),
            'TEST_WORK_DIR': str(self.environment.work_dir)
        })
        
        # Copy required files
        for src, dst in self.config['test']['required_files'].items():
            shutil.copy2(src, self.environment.work_dir / dst)

    def _check_prerequisite(self, prerequisite: str) -> bool:
        """Check if a prerequisite is met."""
        try:
            if prerequisite.startswith('file:'):
                return Path(prerequisite[5:]).exists()
            elif prerequisite.startswith('command:'):
                result = subprocess.run(
                    ['which', prerequisite[8:]],
                    capture_output=True
                )
                return result.returncode == 0
            elif prerequisite.startswith('env:'):
                return prerequisite[4:] in os.environ
            return False
        except Exception:
            return False

    def _execute_step(self, step: Dict[str, str]) -> str:
        """Execute a test step."""
        if 'command' in step:
            result = subprocess.run(
                step['command'],
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise TestExecutionError(
                    f"Step failed: {result.stderr or result.stdout}"
                )
            return result.stdout.strip()
        elif 'script' in step:
            script_path = self.environment.work_dir / "scripts" / step['script']
            if not script_path.exists():
                raise TestExecutionError(f"Script not found: {script_path}")
            result = subprocess.run(
                [str(script_path)],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise TestExecutionError(
                    f"Script failed: {result.stderr or result.stdout}"
                )
            return result.stdout.strip()
        return "No action specified"

    def _execute_validation(self, step: Dict[str, str]) -> Optional[ValidationReport]:
        """Execute a validation step."""
        validation_type = step.get('type')
        if not validation_type:
            return None
            
        try:
            if validation_type == 'build':
                return self.validation_manager.validate_build(step['phase'])
            elif validation_type == 'system':
                return self.validation_manager.validate_system_integrity()
            elif validation_type == 'performance':
                return self.validation_manager.validate_performance()
            elif validation_type == 'checkpoint':
                return self.validation_manager.validate_checkpoint(
                    step['checkpoint_id']
                )
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
        return None

    def _verify_results(self, expected: Dict[str, str]) -> bool:
        """Verify test results against expectations."""
        for check, value in expected.items():
            if check.startswith('file:'):
                file_path = Path(check[5:])
                if not file_path.exists():
                    return False
                if 'content' in value:
                    with open(file_path) as f:
                        if value['content'] not in f.read():
                            return False
            elif check.startswith('command:'):
                result = subprocess.run(
                    check[8:],
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if str(result.returncode) != value.get('exit_code', '0'):
                    return False
                if 'output' in value and value['output'] not in result.stdout:
                    return False
        return True

    def _execute_cleanup(self, steps: List[Dict[str, str]]) -> None:
        """Execute cleanup steps."""
        for step in steps:
            try:
                self._execute_step(step)
            except Exception as e:
                self.logger.error(f"Cleanup step failed: {e}")

    def _collect_test_metrics(self, test_case: TestCase) -> Dict:
        """Collect test-specific metrics."""
        metrics = {
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        }
        
        # Add test-specific metrics if available
        if hasattr(test_case, 'collect_metrics'):
            try:
                metrics.update(test_case.collect_metrics())
            except Exception as e:
                self.logger.error(f"Failed to collect test metrics: {e}")
        
        return metrics

    def _collect_system_metrics(self) -> Dict:
        """Collect system-wide metrics."""
        metrics = {
            'cpu': {
                'usage_percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count()
            },
            'memory': psutil.virtual_memory()._asdict(),
            'disk': {
                'usage': psutil.disk_usage('/')._asdict(),
                'io_counters': psutil.disk_io_counters()._asdict()
                if psutil.disk_io_counters() else None
            },
            'network': psutil.net_io_counters()._asdict()
        }
        return metrics

