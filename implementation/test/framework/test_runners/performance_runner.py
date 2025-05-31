"""
Performance test runner for executing and analyzing performance tests.

Provides specialized test execution environment for performance testing
with metrics collection, analysis, and reporting capabilities.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
import statistics

from ....core.metrics import MetricsCollector
from ..base_runner import BaseTestRunner
from ..test_result import TestResult

@dataclass
class PerformanceThresholds:
    """Performance test pass/fail thresholds."""
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 80.0
    max_execution_time: float = 60.0
    custom_thresholds: Dict[str, float] = None

    def __post_init__(self):
        """Initialize custom thresholds if none provided."""
        if self.custom_thresholds is None:
            self.custom_thresholds = {}

@dataclass
class PerformanceMetrics:
    """Collected performance metrics and analysis."""
    execution_time: float
    cpu_stats: Dict[str, float]
    memory_stats: Dict[str, float]
    io_stats: Dict[str, float]
    custom_metrics: Dict[str, Dict[str, float]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format."""
        return {
            "execution_time": self.execution_time,
            "cpu_stats": self.cpu_stats,
            "memory_stats": self.memory_stats,
            "io_stats": self.io_stats,
            "custom_metrics": self.custom_metrics
        }

class PerformanceRunner(BaseTestRunner):
    """
    Specialized test runner for performance testing.
    
    Features:
    - Detailed performance metrics collection
    - Resource usage monitoring
    - Performance regression detection
    - Benchmark comparison
    - Performance report generation
    """
    
    def __init__(
        self,
        output_dir: Path,
        thresholds: Optional[PerformanceThresholds] = None,
        collection_interval: float = 0.1
    ):
        """
        Initialize performance test runner.
        
        Args:
            output_dir: Directory for test outputs and reports
            thresholds: Performance thresholds for pass/fail criteria
            collection_interval: Metrics collection interval in seconds
        """
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_dir = Path(output_dir)
        self.thresholds = thresholds or PerformanceThresholds()
        self.collection_interval = collection_interval
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics collector
        self.metrics_collector = MetricsCollector(
            collection_interval_seconds=collection_interval
        )
        
        # Historical results for regression analysis
        self.historical_results: List[Dict[str, Any]] = []
        self._load_historical_results()
    
    def _load_historical_results(self) -> None:
        """Load historical test results for regression analysis."""
        history_file = self.output_dir / "performance_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    self.historical_results = json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load historical results: {e}")
                self.historical_results = []
    
    def _save_historical_results(self) -> None:
        """Save current test results to history."""
        history_file = self.output_dir / "performance_history.json"
        try:
            with open(history_file, "w") as f:
                json.dump(self.historical_results, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save historical results: {e}")
    
    async def setup_test(self, test_case: Any) -> None:
        """
        Set up performance test environment.
        
        Args:
            test_case: Test case to be executed
        """
        await super().setup_test(test_case)
        
        # Register any custom metrics defined by the test
        if hasattr(test_case, "register_custom_metrics"):
            await test_case.register_custom_metrics(self.metrics_collector)
        
        # Start metrics collection
        await self.metrics_collector.start_collection()
    
    async def teardown_test(self, test_case: Any) -> None:
        """
        Clean up after test execution.
        
        Args:
            test_case: Executed test case
        """
        # Stop metrics collection
        await self.metrics_collector.stop_collection()
        await super().teardown_test(test_case)
    
    async def execute_test(self, test_case: Any) -> TestResult:
        """
        Execute performance test and collect metrics.
        
        Args:
            test_case: Test case to execute
            
        Returns:
            TestResult with performance metrics and analysis
        """
        start_time = time.time()
        
        # Execute test case
        result = await super().execute_test(test_case)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Collect and analyze metrics
        metrics = await self._analyze_metrics(execution_time)
        
        # Check performance thresholds
        passed, violations = self._check_thresholds(metrics)
        
        # Update test result with performance data
        result.metrics = metrics.to_dict()
        result.passed = result.passed and passed
        if not passed:
            result.failures.extend(violations)
        
        # Generate performance report
        report_path = await self._generate_report(test_case, metrics, violations)
        result.artifacts["performance_report"] = str(report_path)
        
        # Check for performance regression
        regression = await self._check_regression(test_case, metrics)
        if regression:
            result.warnings.extend(regression)
        
        # Update historical results
        self.historical_results.append({
            "timestamp": time.time(),
            "test_name": test_case.__class__.__name__,
            "metrics": metrics.to_dict(),
            "passed": result.passed
        })
        self._save_historical_results()
        
        return result
    
    async def _analyze_metrics(
        self,
        execution_time: float
    ) -> PerformanceMetrics:
        """
        Analyze collected metrics.
        
        Args:
            execution_time: Total test execution time
            
        Returns:
            PerformanceMetrics with statistical analysis
        """
        stats = await self.metrics_collector.get_statistics()
        
        return PerformanceMetrics(
            execution_time=execution_time,
            cpu_stats=stats.get("cpu_percent", {}),
            memory_stats=stats.get("memory_percent", {}),
            io_stats={
                "read": stats.get("disk_read_bytes", {}),
                "write": stats.get("disk_write_bytes", {})
            },
            custom_metrics={
                name: values for name, values in stats.items()
                if name not in {
                    "cpu_percent",
                    "memory_percent",
                    "disk_read_bytes",
                    "disk_write_bytes"
                }
            }
        )
    
    def _check_thresholds(
        self,
        metrics: PerformanceMetrics
    ) -> Tuple[bool, List[str]]:
        """
        Check if metrics exceed defined thresholds.
        
        Args:
            metrics: Collected performance metrics
            
        Returns:
            Tuple of (passed, list of violations)
        """
        violations = []
        
        # Check execution time
        if metrics.execution_time > self.thresholds.max_execution_time:
            violations.append(
                f"Execution time {metrics.execution_time:.2f}s exceeded "
                f"threshold {self.thresholds.max_execution_time:.2f}s"
            )
        
        # Check CPU usage
        if metrics.cpu_stats.get("max", 0) > self.thresholds.max_cpu_percent:
            violations.append(
                f"CPU usage {metrics.cpu_stats['max']:.2f}% exceeded "
                f"threshold {self.thresholds.max_cpu_percent:.2f}%"
            )
        
        # Check memory usage
        if metrics.memory_stats.get("max", 0) > self.thresholds.max_memory_percent:
            violations.append(
                f"Memory usage {metrics.memory_stats['max']:.2f}% exceeded "
                f"threshold {self.thresholds.max_memory_percent:.2f}%"
            )
        
        # Check custom metric thresholds
        for metric, threshold in self.thresholds.custom_thresholds.items():
            if metric in metrics.custom_metrics:
                max_value = metrics.custom_metrics[metric].get("max", 0)
                if max_value > threshold:
                    violations.append(
                        f"Custom metric {metric} value {max_value:.2f} "
                        f"exceeded threshold {threshold:.2f}"
                    )
        
        return len(violations) == 0, violations
    
    async def _check_regression(
        self,
        test_case: Any,
        current_metrics: PerformanceMetrics
    ) -> List[str]:
        """
        Check for performance regression against historical results.
        
        Args:
            test_case: Current test case
            current_metrics: Current test metrics
            
        Returns:
            List of regression warnings
        """
        warnings = []
        test_name = test_case.__class__.__name__
        
        # Get historical results for this test
        historical = [
            result for result in self.historical_results
            if result["test_name"] == test_name
        ]
        
        if not historical:
            return warnings
        
        # Calculate historical averages
        historical_avg = {
            "execution_time": statistics.mean(
                r["metrics"]["execution_time"] for r in historical
            ),
            "cpu_max": statistics.mean(
                r["metrics"]["cpu_stats"]["max"] for r in historical
            ),
            "memory_max": statistics.mean(
                r["metrics"]["memory_stats"]["max"] for r in historical
            )
        }
        
        # Check for significant regressions (>20% increase)
        if current_metrics.execution_time > historical_avg["execution_time"] * 1.2:
            warnings.append(
                f"Execution time increased by "
                f"{((current_metrics.execution_time / historical_avg['execution_time']) - 1) * 100:.1f}% "
                f"compared to historical average"
            )
        
        if current_metrics.cpu_stats["max"] > historical_avg["cpu_max"] * 1.2:
            warnings.append(
                f"Maximum CPU usage increased by "
                f"{((current_metrics.cpu_stats['max'] / historical_avg['cpu_max']) - 1) * 100:.1f}% "
                f"compared to historical average"
            )
        
        if current_metrics.memory_stats["max"] > historical_avg["memory_max"] * 1.2:
            warnings.append(
                f"Maximum memory usage increased by "
                f"{((current_metrics.memory_stats['max'] / historical_avg['memory_max']) - 1) * 100:.1f}% "
                f"compared to historical average"
            )
        
        return warnings
    
    async def _generate_report(
        self,
        test_case: Any,
        metrics: PerformanceMetrics,
        violations: List[str]
    ) -> Path:
        """
        Generate detailed performance report.
        
        Args:
            test_case: Executed test case
            metrics: Collected performance metrics
            violations: List of threshold violations
            
        Returns:
            Path to generated report file
        """
        report = {
            "test_name": test_case.__class__.__name__,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "execution_time": metrics.execution_time,
            "metrics": metrics.to_dict(),
            "violations": violations,
            "historical_comparison": await self._get_historical_comparison(test_case)
        }
        
        report_path = self.output_dir / f"performance_{int(time.time())}.json"
        try:
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to write performance report: {e}")
            return None
        
        return report_path
    
    async def _get_historical_comparison(
        self,
        test_case: Any
    ) -> Dict[str, Any]:
        """
        Generate historical performance comparison data.
        
        Args:
            test_case: Current test case
            
        Returns:
            Dictionary with historical comparison metrics
        """
        test_name = test_case.__class__.__name__
        historical = [
            result for result in self.historical_results
            if result["test_name"] == test_name
        ]
        
        if not historical:
            return {"available": False}
        
        # Calculate historical statistics
        exec_times = [r["metrics"]["execution_time"] for r in historical]
        cpu_max = [r["metrics"]["cpu_stats"]["max"] for r in historical]
        memory_max = [r["metrics"]["memory_stats"]["max"] for r in historical]
        
        return {
            "available": True,
            "total_runs": len(historical),
            "execution_time": {
                "min": min(exec_times),
                "max": max(exec_times),
                "mean": statistics.mean(exec_times),
                "stddev": statistics.stdev(exec_times) if len(exec_times) > 1 else 0
            },
            "cpu_usage": {
                "min": min(cpu_max),
                "max": max(cpu_max),
                "mean": statistics.mean(cpu_max),
                "stddev": statistics.stdev(cpu_max) if len(cpu_max) > 1 else 0
            },
            "memory_usage": {
                "min": min(memory_max),
                "max": max(memory_max),
                "mean": statistics.mean(memory_max),
                "stddev": statistics.stdev(memory_max) if len(memory_max) > 1 else 0
            }
        }

