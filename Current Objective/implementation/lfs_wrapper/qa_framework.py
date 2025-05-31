"""
Quality assurance framework for LFS/BLFS builds.

Provides comprehensive test management, quality metrics collection,
and validation capabilities.

Dependencies:
    - coverage>=7.2
    - pytest>=7.0
"""

import json
import logging
import shutil
import signal
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import coverage
import yaml

from .build_manager import BuildManager, BuildPhase, BuildStatus
from .build_scheduler import BuildScheduler
from .exceptions import QAError, TestError, ValidationError
from .validation_manager import ValidationManager


class TestStatus(Enum):
    """Test execution status."""
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    PASSED = auto()
    FAILED = auto()
    SKIPPED = auto()
    ERROR = auto()


class MetricType(Enum):
    """Types of quality metrics."""
    CODE_COVERAGE = auto()
    TEST_COVERAGE = auto()
    BUILD_SUCCESS = auto()
    BUILD_TIME = auto()
    ERROR_RATE = auto()
    RESOURCE_USAGE = auto()
    USER_FEEDBACK = auto()


@dataclass
class TestPlan:
    """Test plan definition."""
    name: str
    description: str
    test_suites: List[str]
    requirements: Dict[str, str]
    environment: Dict[str, str]
    coverage_targets: Dict[str, float]
    timeout: int = 3600


@dataclass
class TestResult:
    """Test execution result."""
    test_name: str
    status: TestStatus
    start_time: float
    end_time: float
    coverage: Dict[str, float]
    metrics: Dict[str, float]
    output: str
    error: Optional[str] = None


@dataclass
class QualityMetrics:
    """Quality assurance metrics."""
    code_coverage: float
    test_coverage: float
    build_success_rate: float
    avg_build_time: float
    error_rate: float
    resource_efficiency: float
    user_satisfaction: float
    timestamp: float = field(default_factory=time.time)


class QAFramework:
    """
    Manages quality assurance processes.

    Provides test management, quality metrics collection,
    and validation capabilities.

    Attributes:
        config (Dict): QA configuration
        build_manager (BuildManager): Build process manager
        validation_manager (ValidationManager): Validation system
        build_scheduler (BuildScheduler): Build scheduling
        db_path (Path): Metrics database path
        logger (logging.Logger): Logger instance
    """

    def __init__(
        self,
        config: Dict,
        build_manager: BuildManager,
        validation_manager: ValidationManager,
        build_scheduler: BuildScheduler
    ):
        """Initialize QA framework."""
        self.config = config
        self.build_manager = build_manager
        self.validation_manager = validation_manager
        self.build_scheduler = build_scheduler
        self.db_path = Path(config['qa']['metrics_db'])
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_database()

    def execute_test_plan(self, plan: TestPlan) -> List[TestResult]:
        """
        Execute a test plan.

        Args:
            plan: Test plan to execute

        Returns:
            List[TestResult]: Test results

        Raises:
            TestError: If test execution fails
        """
        try:
            # Set up test environment
            self._setup_test_environment(plan)
            
            results = []
            for suite in plan.test_suites:
                # Execute test suite
                suite_results = self._execute_test_suite(suite, plan)
                results.extend(suite_results)
                
                # Check coverage requirements
                if not self._verify_coverage(suite_results, plan.coverage_targets):
                    raise TestError(f"Coverage targets not met for {suite}")
            
            # Save metrics
            self._save_test_metrics(results)
            
            return results
            
        except Exception as e:
            raise TestError(f"Test plan execution failed: {e}")
        finally:
            self._cleanup_test_environment()

    def collect_metrics(self) -> QualityMetrics:
        """
        Collect current quality metrics.

        Returns:
            QualityMetrics: Current quality metrics
        """
        try:
            return QualityMetrics(
                code_coverage=self._measure_code_coverage(),
                test_coverage=self._measure_test_coverage(),
                build_success_rate=self._calculate_build_success_rate(),
                avg_build_time=self._calculate_avg_build_time(),
                error_rate=self._calculate_error_rate(),
                resource_efficiency=self._measure_resource_efficiency(),
                user_satisfaction=self._measure_user_satisfaction()
            )
        except Exception as e:
            raise QAError(f"Failed to collect metrics: {e}")

    def validate_environment(self) -> bool:
        """
        Validate test environment.

        Returns:
            bool: True if environment is valid
        """
        try:
            # Check system requirements
            self._check_system_requirements()
            
            # Verify tool installation
            self._verify_tools()
            
            # Validate configurations
            self._validate_configurations()
            
            # Check resource availability
            self._check_resources()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Environment validation failed: {e}")
            return False

    def simulate_errors(
        self,
        error_types: List[str]
    ) -> Dict[str, TestResult]:
        """
        Simulate error conditions.

        Args:
            error_types: Types of errors to simulate

        Returns:
            Dict[str, TestResult]: Error simulation results
        """
        results = {}
        
        for error_type in error_types:
            try:
                # Set up error simulation
                self._setup_error_simulation(error_type)
                
                # Execute test with error condition
                result = self._execute_with_error(error_type)
                
                # Verify error handling
                self._verify_error_handling(error_type, result)
                
                results[error_type] = result
                
            except Exception as e:
                self.logger.error(f"Error simulation failed for {error_type}: {e}")
                results[error_type] = TestResult(
                    test_name=f"error_sim_{error_type}",
                    status=TestStatus.ERROR,
                    start_time=time.time(),
                    end_time=time.time(),
                    coverage={},
                    metrics={},
                    output="",
                    error=str(e)
                )
            finally:
                self._cleanup_error_simulation(error_type)
        
        return results

    def collect_user_feedback(self) -> Dict[str, float]:
        """
        Collect and analyze user feedback.

        Returns:
            Dict[str, float]: Feedback metrics
        """
        try:
            # Query feedback database
            feedback = self._query_feedback()
            
            # Calculate metrics
            metrics = self._analyze_feedback(feedback)
            
            # Save metrics
            self._save_feedback_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            raise QAError(f"Failed to collect user feedback: {e}")

    def track_build_state(self) -> Dict[str, str]:
        """
        Track current build state.

        Returns:
            Dict[str, str]: Build state information
        """
        try:
            return {
                'phase': self.build_manager.state.phase.name,
                'status': self.build_manager.state.status.name,
                'current_script': self.build_manager.state.current_script or "None",
                'completed': len(self.build_manager.state.completed_scripts),
                'failed': len(self.build_manager.state.failed_scripts),
                'errors': self.build_manager.state.error_count
            }
        except Exception as e:
            raise QAError(f"Failed to track build state: {e}")

    def _init_database(self) -> None:
        """Initialize metrics database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY,
                    timestamp REAL,
                    metric_type TEXT,
                    value REAL,
                    context TEXT
                )
            """)
            
            # Create feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY,
                    timestamp REAL,
                    user_id TEXT,
                    category TEXT,
                    rating INTEGER,
                    comments TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            raise QAError(f"Failed to initialize database: {e}")

    def _setup_test_environment(self, plan: TestPlan) -> None:
        """Set up test environment."""
        try:
            # Create test directory
            test_dir = Path(self.config['qa']['test_dir'])
            test_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy test files
            for suite in plan.test_suites:
                suite_path = Path(self.config['qa']['test_suites']) / suite
                if suite_path.exists():
                    shutil.copytree(
                        suite_path,
                        test_dir / suite,
                        dirs_exist_ok=True
                    )
            
            # Set up environment variables
            os.environ.update(plan.environment)
            
            # Install requirements
            for package, version in plan.requirements.items():
                subprocess.run(
                    ['pip', 'install', f"{package}=={version}"],
                    check=True
                )
                
        except Exception as e:
            raise TestError(f"Failed to set up test environment: {e}")

    def _execute_test_suite(
        self,
        suite: str,
        plan: TestPlan
    ) -> List[TestResult]:
        """Execute a test suite."""
        results = []
        suite_path = Path(self.config['qa']['test_dir']) / suite
        
        try:
            # Start coverage measurement
            cov = coverage.Coverage()
            cov.start()
            
            # Execute tests
            start_time = time.time()
            process = subprocess.run(
                ['pytest', str(suite_path), '-v'],
                capture_output=True,
                text=True,
                timeout=plan.timeout
            )
            end_time = time.time()
            
            # Stop coverage measurement
            cov.stop()
            cov.save()
            
            # Parse results
            results.extend(
                self._parse_test_results(process.stdout, start_time, end_time)
            )
            
            # Add coverage data
            coverage_data = cov.get_data()
            for result in results:
                result.coverage = self._calculate_coverage(coverage_data)
            
        except Exception as e:
            self.logger.error(f"Test suite execution failed: {e}")
            results.append(TestResult(
                test_name=suite,
                status=TestStatus.ERROR,
                start_time=time.time(),
                end_time=time.time(),
                coverage={},
                metrics={},
                output="",
                error=str(e)
            ))
        
        return results

    def _verify_coverage(
        self,
        results: List[TestResult],
        targets: Dict[str, float]
    ) -> bool:
        """Verify coverage meets targets."""
        # Calculate actual coverage
        actual = {}
        for result in results:
            for coverage_type, value in result.coverage.items():
                actual[coverage_type] = actual.get(coverage_type, 0) + value
        
        # Average coverage values
        for coverage_type in actual:
            actual[coverage_type] /= len(results)
        
        # Check against targets
        for coverage_type, target in targets.items():
            if actual.get(coverage_type, 0) < target:
                return False
        
        return True

    def _save_test_metrics(self, results: List[TestResult]) -> None:
        """Save test execution metrics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for result in results:
                # Save coverage metrics
                for coverage_type, value in result.coverage.items():
                    cursor.execute(
                        "INSERT INTO metrics VALUES (NULL, ?, ?, ?, ?)",
                        (
                            result.end_time,
                            f"coverage_{coverage_type}",
                            value,
                            result.test_name
                        )
                    )
                
                # Save test metrics
                for metric_type, value in result.metrics.items():
                    cursor.execute(
                        "INSERT INTO metrics VALUES (NULL, ?, ?, ?, ?)",
                        (
                            result.end_time,
                            metric_type,
                            value,
                            result.test_name
                        )
                    )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            raise QAError(f"Failed to save metrics: {e}")

    def _measure_code_coverage(self) -> float:
        """Measure code coverage."""
        try:
            cov = coverage.Coverage()
            cov.load()
            return cov.report()
        except Exception:
            return 0.0

    def _measure_test_coverage(self) -> float:
        """Measure test coverage."""
        try:
            test_files = len(list(Path('tests').glob('test_*.py')))
            source_files = len(list(Path('src').glob('*.py')))
            return test_files / source_files * 100
        except Exception:
            return 0.0

    def _calculate_build_success_rate(self) -> float:
        """Calculate build success rate."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN value = 1 THEN 1 ELSE 0 END) as success
                FROM metrics
                WHERE metric_type = 'build_success'
                AND timestamp > ?
            """, (time.time() - 86400,))  # Last 24 hours
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                return (row[1] / row[0]) * 100
            return 0.0
            
        except Exception:
            return 0.0

    def _calculate_avg_build_time(self) -> float:
        """Calculate average build time."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT AVG(value)
                FROM metrics
                WHERE metric_type = 'build_time'
                AND timestamp > ?
            """, (time.time() - 86400,))  # Last 24 hours
            
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row and row[0] else 0.0
            
        except Exception:
            return 0.0

    def _calculate_error_rate(self) -> float:
        """Calculate error rate."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN value = 1 THEN 1 ELSE 0 END) as errors
                FROM metrics
                WHERE metric_type = 'error_occurred'
                AND timestamp > ?
            """, (time.time() - 86400,))  # Last 24 hours
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                return (row[1] / row[0]) * 100
            return 0.0
            
        except Exception:
            return 0.0

    def _measure_resource_efficiency(self) -> float:
        """Measure resource utilization efficiency."""
        try:
            # Get resource metrics
            cpu_usage = self._get_cpu_efficiency()
            memory_usage = self._get_memory_efficiency()
            io_usage = self._get_io_efficiency()
            
            # Calculate weighted average
            weights = {
                'cpu': 0.4,
                'memory': 0.4,
                'io': 0.2
            }
            
            return (
                cpu_usage * weights['cpu'] +
                memory_usage * weights['memory'] +
                io_usage * weights['io']
            )
            
        except Exception:
            return 0.0

    def _measure_user_satisfaction(self) -> float:
        """Measure user satisfaction from feedback."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT AVG(rating)
                FROM feedback
                WHERE timestamp > ?
            """, (time.time() - 7 * 86400,))  # Last 7 days
            
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row and row[0] else 0.0
            
        except Exception:
            return 0.0

    def _query_feedback(self) -> List[Dict]:
        """Query user feedback from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, user_id, category, rating, comments
                FROM feedback
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (time.time() - 7 * 86400,))
            
            feedback = []
            for row in cursor.fetchall():
                feedback.append({
                    'timestamp': row[0],
                    'user_id': row[1],
                    'category': row[2],
                    'rating': row[3],
                    'comments': row[4]
                })
            
            conn.close()
            return feedback
            
        except Exception as e:
            raise QAError(f"Failed to query feedback: {e}")

    def _analyze_feedback(self, feedback: List[Dict]) -> Dict[str, float]:
        """Analyze user feedback data."""
        if not feedback:
            return {}
        
        metrics = {
            'overall_satisfaction': 0.0,
            'usability_score': 0.0,
            'reliability_score': 0.0,
            'performance_score': 0.0
        }
        
        counts = {k: 0 for k in metrics}
        
        for entry in feedback:
            category = entry['category']
            rating = entry['rating']
            
            if category == 'overall':
                metrics['overall_satisfaction'] += rating
                counts['overall_satisfaction'] += 1
            elif category == 'usability':
                metrics['usability_score'] += rating
                counts['usability_score'] += 1
            elif category == 'reliability':
                metrics['reliability_score'] += rating
                counts['reliability_score'] += 1
            elif category == 'performance':
                metrics['performance_score'] += rating
                counts['performance_score'] += 1
        
        # Calculate averages
        for metric in metrics:
            if counts[metric] > 0:
                metrics[metric] /= counts[metric]
        
        return metrics

    def _save_feedback_metrics(self, metrics: Dict[str, float]) -> None:
        """Save analyzed feedback metrics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = time.time()
            for metric_type, value in metrics.items():
                cursor.execute(
                    "INSERT INTO metrics VALUES (NULL, ?, ?, ?, ?)",
                    (timestamp, f"feedback_{metric_type}", value, "user_feedback")
                )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            raise QAError(f"Failed to save feedback metrics: {e}")

    def _check_system_requirements(self) -> None:
        """Check system requirements."""
        for requirement, value in self.config['qa']['system_requirements'].items():
            if requirement == 'memory':
                if self._get_available_memory() < value:
                    raise ValidationError(f"Insufficient memory: {requirement}")
            elif requirement == 'disk_space':
                if self._get_available_disk_space() < value:
                    raise ValidationError(f"Insufficient disk space: {requirement}")
            elif requirement == 'python_version':
                if not self._check_python_version(value):
                    raise ValidationError(f"Python version requirement not met: {value}")

    def _verify_tools(self) -> None:
        """Verify required tools are installed."""
        for tool in self.config['qa']['required_tools']:
            result = subprocess.run(
                ['which', tool],
                capture_output=True
            )
            if result.returncode != 0:
                raise ValidationError(f"Required tool not found: {tool}")

    def _validate_configurations(self) -> None:
        """Validate configuration files."""
        for config_file in self.config['qa']['config_files']:
            path = Path(config_file)
            if not path.exists():
                raise ValidationError(f"Configuration file missing: {config_file}")
            
            try:
                with open(path) as f:
                    yaml.safe_load(f)
            except Exception as e:
                raise ValidationError(
                    f"Invalid configuration file {config_file}: {e}"
                )

    def _check_resources(self) -> None:
        """Check resource availability."""
        # Check CPU load
        if self._get_cpu_load() > self.config['qa']['max_cpu_load']:
            raise ValidationError("CPU load too high")
        
        # Check memory usage
        if self._get_memory_usage() > self.config['qa']['max_memory_usage']:
            raise ValidationError("Memory usage too high")
        
        # Check disk I/O
        if self._get_io_usage() > self.config['qa']['max_io_usage']:
            raise ValidationError("Disk I/O too high")

    def _setup_error_simulation(self, error_type: str) -> None:
        """Set up error simulation environment."""
        if error_type == 'disk_full':
            self._simulate_disk_full()
        elif error_type == 'memory_pressure':
            self._simulate_memory_pressure()
        elif error_type == 'network_failure':
            self._simulate_network_failure()
        elif error_type == 'process_crash':
            self._simulate_process_crash()

    def _execute_with_error(self, error_type: str) -> TestResult:
        """Execute test with simulated error."""
        start_time = time.time()
        
        try:
            if error_type == 'disk_full':
                self._test_disk_full_handling()
            elif error_type == 'memory_pressure':
                self._test_memory_pressure_handling()
            elif error_type == 'network_failure':
                self._test_network_failure_handling()
            elif error_type == 'process_crash':
                self._test_process_crash_handling()
            
            status = TestStatus.PASSED
            error = None
            
        except Exception as e:
            status = TestStatus.FAILED
            error = str(e)
        
        end_time = time.time()
        
        return TestResult(
            test_name=f"error_sim_{error_type}",
            status=status,
            start_time=start_time,
            end_time=end_time,
            coverage={},
            metrics={
                'duration': end_time - start_time,
                'error_detected': 1 if error else 0
            },
            output="",
            error=error
        )

    def _verify_error_handling(
        self,
        error_type: str,
        result: TestResult
    ) -> None:
        """Verify error handling behavior."""
        if error_type == 'disk_full':
            self._verify_disk_full_handling(result)
        elif error_type == 'memory_pressure':
            self._verify_memory_pressure_handling(result)
        elif error_type == 'network_failure':
            self._verify_network_failure_handling(result)
        elif error_type == 'process_crash':
            self._verify_process_crash_handling(result)

    def _cleanup_error_simulation(self, error_type: str) -> None:
        """Clean up after error simulation."""
        if error_type == 'disk_full':
            self._cleanup_disk_full()
        elif error_type == 'memory_pressure':
            self._cleanup_memory_pressure()
        elif error_type == 'network_failure':
            self._cleanup_network_failure()
        elif error_type == 'process_crash':
            self._cleanup_process_crash()

    def _simulate_disk_full(self) -> None:
        """Simulate disk full condition."""
        test_file = Path(self.config['qa']['test_dir']) / "disk_full_test"
        test_file.write_bytes(b'\0' * (1024 * 1024 * 100))  # 100MB file

    def _simulate_memory_pressure(self) -> None:
        """Simulate memory pressure."""
        subprocess.run(
            ['stress-ng', '--vm', '1', '--vm-bytes', '50%', '-t', '10s'],
            check=True
        )

    def _simulate_network_failure(self) -> None:
        """Simulate network failure."""
        subprocess.run(
            ['tc', 'qdisc', 'add', 'dev', 'lo', 'root', 'netem', 'loss', '100%'],
            check=True
        )

    def _simulate_process_crash(self) -> None:
        """Simulate process crash."""
        os.kill(os.getpid(), signal.SIGUSR1)

    def _test_disk_full_handling(self) -> None:
        """Test disk full error handling."""
        test_file = Path(self.config['qa']['test_dir']) / "test_output"
        test_file.write_bytes(b'\0' * (1024 * 1024 * 200))  # Should fail

    def _test_memory_pressure_handling(self) -> None:
        """Test memory pressure handling."""
        data = [0] * (1024 * 1024 * 100)  # Allocate 100MB
        while True:
            data.extend(data)  # Double size until OOM

    def _test_network_failure_handling(self) -> None:
        """Test network failure handling."""
        subprocess.run(['wget', 'http://localhost:8080'], check=True)

    def _test_process_crash_handling(self) -> None:
        """Test process crash handling."""
        os.kill(os.getpid(), signal.SIGSEGV)

    def _verify_disk_full_handling(self, result: TestResult) -> None:
        """Verify disk full error handling."""
        assert result.status == TestStatus.FAILED
        assert "No space left on device" in (result.error or "")

    def _verify_memory_pressure_handling(self, result: TestResult) -> None:
        """Verify memory pressure handling."""
        assert result.status == TestStatus.FAILED
        assert "MemoryError" in (result.error or "")

    def _verify_network_failure_handling(self, result: TestResult) -> None:
        """Verify network failure handling."""
        assert result.status == TestStatus.FAILED
        assert "Connection failed" in (result.error or "")

    def _verify_process_crash_handling(self, result: TestResult) -> None:
        """Verify process crash handling."""
        assert result.status == TestStatus.FAILED
        assert "Segmentation fault" in (result.error or "")

    def _cleanup_disk_full(self) -> None:
        """Clean up disk full simulation."""
        test_file = Path(self.config['qa']['test_dir']) / "disk_full_test"
        test_file.unlink(missing_ok=True)

    def _cleanup_memory_pressure(self) -> None:
        """Clean up memory pressure simulation."""
        subprocess.run(['killall', 'stress-ng'], check=False)

    def _cleanup_network_failure(self) -> None:
        """Clean up network failure simulation."""
        subprocess.run(
            ['tc', 'qdisc', 'del', 'dev', 'lo', 'root'],
            check=False
        )

    def _cleanup_process_crash(self) -> None:
        """Clean up process crash simulation."""
        # Nothing to clean up for process crash

    def _get_cpu_load(self) -> float:
        """Get current CPU load."""
        return os.getloadavg()[0]

    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        return psutil.virtual_memory().percent

    def _get_io_usage(self) -> float:
        """Get current I/O usage percentage."""
        io = psutil.disk_io_counters()
        return (io.read_bytes + io.write_bytes) / 1024 / 1024  # MB/s

    def _get_available_memory(self) -> int:
        """Get available memory in MB."""
        return psutil.virtual_memory().available // (1024 * 1024)

    def _get_available_disk_space(self) -> int:
        """Get available disk space in MB."""
        return shutil.disk_usage('/').free // (1024 * 1024)

    def _check_python_version(self, required: str) -> bool:
        """Check Python version meets requirement."""
        import sys
        current = '.'.join(map(str, sys.version_info[:3]))
        return parse_version(current) >= parse_version(required)

    def _get_cpu_efficiency(self) -> float:
        """Calculate CPU efficiency score."""
        try:
            load = os.getloadavg()[0]
            cpu_count = os.cpu_count() or 1
            return max(0, 100 - (load / cpu_count * 100))
        except Exception:
            return 0.0

    def _get_memory_efficiency(self) -> float:
        """Calculate memory efficiency score."""
        try:
            memory = psutil.virtual_memory()
            return 100 - memory.percent
        except Exception:
            return 0.0

    def _get_io_efficiency(self) -> float:
        """Calculate I/O efficiency score."""
        try:
            io = psutil.disk_io_counters()
            total_io = io.read_bytes + io.write_bytes
            return max(0, 100 - (total_io / (1024 * 1024 * 1024) * 10))
        except Exception:
            return 0.0

    def _parse_test_results(
        self,
        output: str,
        start_time: float,
        end_time: float
    ) -> List[TestResult]:
        """Parse pytest output into test results."""
        results = []
        current_test = None
        
        for line in output.splitlines():
            if line.startswith('test_'):
                # New test case
                if current_test:
                    results.append(current_test)
                
                test_name = line.split()[0]

