"""
Performance benchmarking system for LFS/BLFS builds.

Provides functionality for measuring, tracking, and analyzing
build performance metrics.

Dependencies:
    - psutil>=5.8
    - numpy>=1.20
"""

import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import psutil

from .build_manager import BuildPhase
from .exceptions import BenchmarkError


class MetricType(Enum):
    """Types of performance metrics."""
    CPU_USAGE = auto()
    MEMORY_USAGE = auto()
    DISK_IO = auto()
    BUILD_TIME = auto()
    SCRIPT_TIME = auto()


@dataclass
class MetricSample:
    """Single performance metric sample."""
    metric_type: MetricType
    value: float
    timestamp: float
    context: Dict


@dataclass
class BenchmarkResult:
    """Results of a performance benchmark run."""
    phase: BuildPhase
    start_time: float
    end_time: float
    metrics: List[MetricSample]
    summary: Dict[MetricType, Dict[str, float]]
    system_info: Dict


@dataclass
class PerformanceReport:
    """Comprehensive performance analysis report."""
    benchmark: BenchmarkResult
    baseline: Optional[BenchmarkResult]
    comparison: Optional[Dict[MetricType, float]]
    recommendations: List[str]
    timestamp: float = field(default_factory=time.time)


class BenchmarkManager:
    """
    Manages performance benchmarking.

    Handles performance measurement, analysis, and reporting
    for build processes.

    Attributes:
        config (Dict): Benchmark configuration
        history_file (Path): Performance history storage
        logger (logging.Logger): Logger instance
    """

    def __init__(self, config: Dict):
        """Initialize benchmark manager."""
        self.config = config
        self.history_file = Path(config['benchmark']['history_file'])
        self.logger = logging.getLogger(__name__)
        
        # Ensure history file exists
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._save_history([])

    def start_benchmark(self, phase: BuildPhase) -> None:
        """
        Start benchmarking for a build phase.

        Args:
            phase: Build phase to benchmark

        Raises:
            BenchmarkError: If benchmark start fails
        """
        try:
            self._current_benchmark = {
                'phase': phase,
                'start_time': time.time(),
                'metrics': [],
                'system_info': self._collect_system_info()
            }
            
            # Start metric collection
            self._start_collection()
            
        except Exception as e:
            raise BenchmarkError(f"Failed to start benchmark: {e}")

    def stop_benchmark(self) -> BenchmarkResult:
        """
        Stop current benchmark and return results.

        Returns:
            BenchmarkResult: Benchmark results

        Raises:
            BenchmarkError: If benchmark stop fails
        """
        try:
            if not hasattr(self, '_current_benchmark'):
                raise BenchmarkError("No benchmark in progress")
            
            # Stop metric collection
            self._stop_collection()
            
            # Create benchmark result
            result = BenchmarkResult(
                phase=self._current_benchmark['phase'],
                start_time=self._current_benchmark['start_time'],
                end_time=time.time(),
                metrics=self._current_benchmark['metrics'],
                summary=self._calculate_summary(self._current_benchmark['metrics']),
                system_info=self._current_benchmark['system_info']
            )
            
            # Save to history
            self._save_result(result)
            
            return result
            
        except Exception as e:
            raise BenchmarkError(f"Failed to stop benchmark: {e}")
        finally:
            if hasattr(self, '_current_benchmark'):
                delattr(self, '_current_benchmark')

    def collect_sample(self) -> None:
        """Collect current performance metrics."""
        if not hasattr(self, '_current_benchmark'):
            return
            
        try:
            timestamp = time.time()
            
            # Collect CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self._current_benchmark['metrics'].append(MetricSample(
                metric_type=MetricType.CPU_USAGE,
                value=cpu_percent,
                timestamp=timestamp,
                context={'per_cpu': psutil.cpu_percent(percpu=True)}
            ))
            
            # Collect memory metrics
            memory = psutil.virtual_memory()
            self._current_benchmark['metrics'].append(MetricSample(
                metric_type=MetricType.MEMORY_USAGE,
                value=memory.percent,
                timestamp=timestamp,
                context=memory._asdict()
            ))
            
            # Collect disk I/O metrics
            io_counters = psutil.disk_io_counters()
            if io_counters:
                self._current_benchmark['metrics'].append(MetricSample(
                    metric_type=MetricType.DISK_IO,
                    value=io_counters.read_bytes + io_counters.write_bytes,
                    timestamp=timestamp,
                    context=io_counters._asdict()
                ))
                
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")

    def generate_report(
        self,
        benchmark: BenchmarkResult,
        baseline: Optional[BenchmarkResult] = None
    ) -> PerformanceReport:
        """
        Generate performance analysis report.

        Args:
            benchmark: Benchmark result to analyze
            baseline: Optional baseline for comparison

        Returns:
            PerformanceReport: Performance analysis report
        """
        try:
            # Compare with baseline if provided
            comparison = None
            if baseline:
                comparison = self._compare_benchmarks(benchmark, baseline)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                benchmark,
                comparison
            )
            
            return PerformanceReport(
                benchmark=benchmark,
                baseline=baseline,
                comparison=comparison,
                recommendations=recommendations
            )
            
        except Exception as e:
            raise BenchmarkError(f"Failed to generate report: {e}")

    def get_baseline(self, phase: BuildPhase) -> Optional[BenchmarkResult]:
        """
        Get baseline benchmark for a phase.

        Args:
            phase: Build phase

        Returns:
            Optional[BenchmarkResult]: Baseline benchmark or None
        """
        try:
            history = self._load_history()
            if not history:
                return None
            
            # Find most recent successful benchmark for phase
            phase_results = [
                r for r in history
                if r['phase'] == phase.name
                and r['summary'][MetricType.BUILD_TIME.name]['success']
            ]
            
            if not phase_results:
                return None
            
            latest = max(phase_results, key=lambda x: x['timestamp'])
            return self._deserialize_result(latest)
            
        except Exception as e:
            self.logger.error(f"Failed to get baseline: {e}")
            return None

    def _start_collection(self) -> None:
        """Start metric collection."""
        # Collection is handled by external monitoring
        pass

    def _stop_collection(self) -> None:
        """Stop metric collection."""
        # Collection is handled by external monitoring
        pass

    def _calculate_summary(self, metrics: List[MetricSample]) -> Dict[MetricType, Dict[str, float]]:
        """Calculate summary statistics for metrics."""
        summary = {}
        
        for metric_type in MetricType:
            type_metrics = [m.value for m in metrics if m.metric_type == metric_type]
            if type_metrics:
                summary[metric_type] = {
                    'min': min(type_metrics),
                    'max': max(type_metrics),
                    'mean': statistics.mean(type_metrics),
                    'median': statistics.median(type_metrics),
                    'stddev': statistics.stdev(type_metrics) if len(type_metrics) > 1 else 0
                }
        
        return summary

    def _compare_benchmarks(
        self,
        current: BenchmarkResult,
        baseline: BenchmarkResult
    ) -> Dict[MetricType, float]:
        """Compare benchmark results against baseline."""
        comparison = {}
        
        for metric_type in MetricType:
            if (metric_type in current.summary 
                    and metric_type in baseline.summary):
                current_mean = current.summary[metric_type]['mean']
                baseline_mean = baseline.summary[metric_type]['mean']
                
                # Calculate percentage difference
                comparison[metric_type] = (
                    (current_mean - baseline_mean) / baseline_mean * 100
                )
        
        return comparison

    def _generate_recommendations(
        self,
        benchmark: BenchmarkResult,
        comparison: Optional[Dict[MetricType, float]] = None
    ) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Check CPU usage
        cpu_metrics = [
            m for m in benchmark.metrics
            if m.metric_type == MetricType.CPU_USAGE
        ]
        if cpu_metrics:
            avg_cpu = statistics.mean(m.value for m in cpu_metrics)
            if avg_cpu > 90:
                recommendations.append(
                    "High CPU usage detected. Consider reducing parallel builds."
                )
            elif avg_cpu < 50:
                recommendations.append(
                    "Low CPU utilization. Consider increasing parallel builds."
                )
        
        # Check memory usage
        mem_metrics = [
            m for m in benchmark.metrics
            if m.metric_type == MetricType.MEMORY_USAGE
        ]
        if mem_metrics:
            avg_mem = statistics.mean(m.value for m in mem_metrics)
            if avg_mem > 90:
                recommendations.append(
                    "High memory usage. Consider reducing concurrent builds."
                )
        
        # Check comparison metrics
        if comparison:
            for metric_type, diff in comparison.items():
                if abs(diff) > 10:  # More than 10% difference
                    worse = diff > 0
                    recommendations.append(
                        f"{metric_type.name} performance is "
                        f"{'worse' if worse else 'better'} than baseline "
                        f"by {abs(diff):.1f}%"
                    )
        
        return recommendations

    def _collect_system_info(self) -> Dict:
        """Collect system information."""
        return {
            'cpu': {
                'count': psutil.cpu_count(),
                'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'swap': psutil.swap_memory()._asdict()
            },
            'disk': {
                'partitions': [p._asdict() for p in psutil.disk_partitions()],
                'usage': {
                    str(p.mountpoint): psutil.disk_usage(p.mountpoint)._asdict()
                    for p in psutil.disk_partitions()
                }
            }
        }

    def _save_result(self, result: BenchmarkResult) -> None:
        """Save benchmark result to history."""
        try:
            history = self._load_history()
            history.append(self._serialize_result(result))
            self._save_history(history)
        except Exception as e:
            self.logger.error(f"Failed to save benchmark result: {e}")

    def _load_history(self) -> List[Dict]:
        """Load benchmark history from disk."""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except Exception:
            return []

    def _save_history(self, history: List[Dict]) -> None:
        """Save benchmark history to disk."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save benchmark history: {e}")

    def _serialize_result(self, result: BenchmarkResult) -> Dict:
        """Serialize benchmark result for storage."""
        return {
            'phase': result.phase.name,
            'start_time': result.start_time,
            'end_time': result.end_time,
            'metrics': [
                {
                    'type': m.metric_type.name,
                    'value': m.value,
                    'timestamp': m.timestamp,
                    'context': m.context
                }
                for m in result.metrics
            ],
            'summary': {
                k.name: v for k, v in result.summary.items()
            },
            'system_info': result.system_info,
            'timestamp': time.time()
        }

    def _deserialize_result(self, data: Dict) -> BenchmarkResult:
        """Deserialize benchmark result from storage."""
        return BenchmarkResult(
            phase=BuildPhase[data['phase']],
            start_time=data['start_time'],
            end_time=data['end_time'],
            metrics=[
                MetricSample(
                    metric_type=MetricType[m['type']],
                    value=m['value'],
                    timestamp=m['timestamp'],
                    context=m['context']
                )
                for m in data['metrics']
            ],
            summary={
                MetricType[k]: v
                for k, v in data['summary'].items()
            },
            system_info=data['system_info']
        )

