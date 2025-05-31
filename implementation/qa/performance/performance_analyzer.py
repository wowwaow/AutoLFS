#!/usr/bin/env python3

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np
import psutil
import resource
from pympler import summary, muppy

class MetricType(Enum):
    """Types of performance metrics"""
    TIME = "time"
    MEMORY = "memory"
    CPU = "cpu"
    IO = "io"
    THROUGHPUT = "throughput"
    LATENCY = "latency"

class MetricUnit(Enum):
    """Units for performance metrics"""
    SECONDS = "seconds"
    MILLISECONDS = "ms"
    BYTES = "bytes"
    MEGABYTES = "MB"
    PERCENT = "percent"
    OPERATIONS = "ops"
    REQUESTS = "requests"

@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    type: MetricType
    value: float
    unit: MetricUnit
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceBaseline:
    """Performance baseline definition"""
    metric_name: str
    expected_value: float
    acceptable_deviation: float
    unit: MetricUnit
    valid_from: datetime
    valid_to: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceThreshold:
    """Performance threshold definition"""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    unit: MetricUnit
    comparison: str  # 'greater_than' or 'less_than'
    enabled: bool = True

@dataclass
class AnalysisResult:
    """Results of performance analysis"""
    metrics: List[PerformanceMetric]
    baseline_comparisons: Dict[str, Dict[str, Any]]
    threshold_violations: List[Dict[str, Any]]
    bottlenecks: List[Dict[str, Any]]
    recommendations: List[str]
    trends: Dict[str, Any]

class PerformanceAnalyzer:
    """Main performance analyzer implementation"""

    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self.initialize_logging()
        self.baselines = self._load_baselines()
        self.thresholds = self._load_thresholds()
        self.metrics_history: Dict[str, List[PerformanceMetric]] = {}

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load analyzer configuration"""
        if not config_path:
            config_path = os.path.join(
                os.path.dirname(__file__),
                'config',
                'performance_config.json'
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
                logging.FileHandler('performance_analyzer.log'),
                logging.StreamHandler()
            ]
        )

    def _load_baselines(self) -> Dict[str, PerformanceBaseline]:
        """Load performance baselines"""
        baselines = {}
        
        # Load built-in baselines
        default_baselines = {
            "request_latency": PerformanceBaseline(
                metric_name="request_latency",
                expected_value=100.0,
                acceptable_deviation=20.0,
                unit=MetricUnit.MILLISECONDS,
                valid_from=datetime.utcnow()
            ),
            "memory_usage": PerformanceBaseline(
                metric_name="memory_usage",
                expected_value=512.0,
                acceptable_deviation=128.0,
                unit=MetricUnit.MEGABYTES,
                valid_from=datetime.utcnow()
            )
        }
        baselines.update(default_baselines)

        # Load custom baselines from config
        custom_baselines = self.config.get('baselines', {})
        for name, data in custom_baselines.items():
            try:
                baselines[name] = PerformanceBaseline(
                    metric_name=name,
                    expected_value=data['expected_value'],
                    acceptable_deviation=data['acceptable_deviation'],
                    unit=MetricUnit[data['unit'].upper()],
                    valid_from=datetime.fromisoformat(data['valid_from']),
                    valid_to=datetime.fromisoformat(data['valid_to'])
                    if 'valid_to' in data else None
                )
            except Exception as e:
                self.logger.error(f"Failed to load baseline {name}: {e}")

        return baselines

    def _load_thresholds(self) -> Dict[str, PerformanceThreshold]:
        """Load performance thresholds"""
        thresholds = {}
        
        # Load built-in thresholds
        default_thresholds = {
            "cpu_usage": PerformanceThreshold(
                metric_name="cpu_usage",
                warning_threshold=80.0,
                critical_threshold=90.0,
                unit=MetricUnit.PERCENT,
                comparison="greater_than"
            ),
            "memory_usage": PerformanceThreshold(
                metric_name="memory_usage",
                warning_threshold=2048.0,
                critical_threshold=3072.0,
                unit=MetricUnit.MEGABYTES,
                comparison="greater_than"
            )
        }
        thresholds.update(default_thresholds)

        # Load custom thresholds from config
        custom_thresholds = self.config.get('thresholds', {})
        for name, data in custom_thresholds.items():
            try:
                thresholds[name] = PerformanceThreshold(**data)
            except Exception as e:
                self.logger.error(f"Failed to load threshold {name}: {e}")

        return thresholds

    async def collect_metrics(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> List[PerformanceMetric]:
        """Collect current performance metrics"""
        metrics = []
        timestamp = datetime.utcnow()

        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(PerformanceMetric(
                name="cpu_usage",
                type=MetricType.CPU,
                value=cpu_percent,
                unit=MetricUnit.PERCENT,
                timestamp=timestamp,
                context=context or {}
            ))

            memory = psutil.Process().memory_info()
            metrics.append(PerformanceMetric(
                name="memory_usage",
                type=MetricType.MEMORY,
                value=memory.rss / 1024 / 1024,  # Convert to MB
                unit=MetricUnit.MEGABYTES,
                timestamp=timestamp,
                context=context or {}
            ))

            # IO metrics
            io_counters = psutil.Process().io_counters()
            metrics.append(PerformanceMetric(
                name="io_read_bytes",
                type=MetricType.IO,
                value=io_counters.read_bytes,
                unit=MetricUnit.BYTES,
                timestamp=timestamp,
                context=context or {}
            ))

            # Store metrics in history
            for metric in metrics:
                if metric.name not in self.metrics_history:
                    self.metrics_history[metric.name] = []
                self.metrics_history[metric.name].append(metric)

            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return []

    async def compare_to_baseline(
        self,
        metrics: List[PerformanceMetric]
    ) -> Dict[str, Dict[str, Any]]:
        """Compare metrics to baselines"""
        comparisons = {}

        for metric in metrics:
            if metric.name in self.baselines:
                baseline = self.baselines[metric.name]
                
                # Check if baseline is valid
                if (baseline.valid_to and 
                    baseline.valid_to < datetime.utcnow()):
                    continue

                deviation = abs(metric.value - baseline.expected_value)
                deviation_percent = (
                    (deviation / baseline.expected_value) * 100
                    if baseline.expected_value != 0 else float('inf')
                )

                comparisons[metric.name] = {
                    "current_value": metric.value,
                    "baseline_value": baseline.expected_value,
                    "deviation": deviation,
                    "deviation_percent": deviation_percent,
                    "acceptable_deviation": baseline.acceptable_deviation,
                    "within_baseline": (
                        deviation_percent <= baseline.acceptable_deviation
                    )
                }

        return comparisons

    async def check_thresholds(
        self,
        metrics: List[PerformanceMetric]
    ) -> List[Dict[str, Any]]:
        """Check metrics against thresholds"""
        violations = []

        for metric in metrics:
            if metric.name in self.thresholds:
                threshold = self.thresholds[metric.name]
                if not threshold.enabled:
                    continue

                if threshold.comparison == "greater_than":
                    if metric.value >= threshold.critical_threshold:
                        violations.append({
                            "metric": metric.name,
                            "value": metric.value,
                            "threshold": threshold.critical_threshold,
                            "severity": "critical",
                            "timestamp": metric.timestamp.isoformat()
                        })
                    elif metric.value >= threshold.warning_threshold:
                        violations.append({
                            "metric": metric.name,
                            "value": metric.value,
                            "threshold": threshold.warning_threshold,
                            "severity": "warning",
                            "timestamp": metric.timestamp.isoformat()
                        })
                elif threshold.comparison == "less_than":
                    if metric.value <= threshold.critical_threshold:
                        violations.append({
                            "metric": metric.name,
                            "value": metric.value,
                            "threshold": threshold.critical_threshold,
                            "severity": "critical",
                            "timestamp": metric.timestamp.isoformat()
                        })
                    elif metric.value <= threshold.warning_threshold:
                        violations.append({
                            "metric": metric.name,
                            "value": metric.value,
                            "threshold": threshold.warning_threshold,
                            "severity": "warning",
                            "timestamp": metric.timestamp.isoformat()
                        })

        return violations

    async def detect_bottlenecks(
        self,
        metrics: List[PerformanceMetric]
    ) -> List[Dict[str, Any]]:
        """Detect performance bottlenecks"""
        bottlenecks = []

        # CPU bottleneck detection
        cpu_metrics = [m for m in metrics if m.name == "cpu_usage"]
        if cpu_metrics and cpu_metrics[0].value > 80:
            bottlenecks.append({
                "type": "cpu",
                "severity": "high" if cpu_metrics[0].value > 90 else "medium",
                "value": cpu_metrics[0].value,
                "description": "High CPU usage detected"
            })

        # Memory bottleneck detection
        memory_metrics = [m for m in metrics if m.name == "memory_usage"]
        if memory_metrics and memory_metrics[0].value > 2048:  # 2GB
            bottlenecks.append({
                "type": "memory",
                "severity": "high" if memory_metrics[0].value > 3072 else "medium",
                "value": memory_metrics[0].value,
                "description": "High memory usage detected"
            })

        return bottlenecks

    async def analyze_trends(
        self,
        metric_name: str,
        time_window: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """Analyze metric trends"""
        if metric_name not in self.metrics_history:
            return {}

        cutoff_time = datetime.utcnow() - time_window
        relevant_metrics = [
            m for m in self.metrics_history[metric_name]
            if m.timestamp >= cutoff_time
        ]

        if not relevant_metrics:
            return {}

        values = [m.value for m in relevant_metrics]
        timestamps = [m.timestamp for m in relevant_metrics]

        return {
            "metric": metric_name,
            "min": min(values),
            "max": max(values),
            "mean": np.mean(values),
            "std_dev": np.std(values),
            "trend": self._calculate_trend(values),
            "time_window": str(time_window),
            "data_points": len(values)
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from series of values"""
        if len(values) < 2:
            return "stable"

        # Simple linear regression
        x = np.arange(len(values))
        z = np.polyfit(x, values, 1)
        slope = z[0]

        if abs(slope) < 0.1:
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"

    async def generate_recommendations(
        self,
        analysis_result: AnalysisResult
    ) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []

        # Threshold-based recommendations
        for violation in analysis_result.threshold_violations:
            if violation['severity'] == 'critical':
                recommendations.append(
                    f"CRITICAL: {violation['metric']} exceeds critical threshold. "
                    f"Current value: {violation['value']}, "
                    f"Threshold: {violation['threshold']}"
                )

        # Bottleneck-based recommendations
        for bottleneck in analysis_result.bottlenecks:
            if bottleneck['severity'] == 'high':
                recommendations.append(
                    f"HIGH: {bottleneck['type']} bottleneck detected. "
                    f"{bottleneck['description']}"
                )

        # Trend-based recommendations
        for metric_name, trend_data in analysis_result.trends.items():
            if trend_data.get('trend') == 'increasing':
                recommendations.append(
                    f"TREND: {metric_name} shows increasing trend. "
                    f"Consider optimization if trend continues."
                )

        return recommendations

    async def analyze_performance(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """Perform comprehensive performance analysis"""
        try:
            # Collect current metrics
            metrics = await self.collect_metrics(context)

            # Compare to baselines
            baseline_comparisons = await self.compare_to_baseline(metrics)

            # Check thresholds
            threshold_violations = await self.check_thresholds(metrics)

            # Detect bottlenecks
            bottlenecks = await self.detect_bottlenecks(metrics)

            # Analyze trends
            trends = {}
            for metric in metrics:
                trend_data = await self.analyze_trends(metric.name)
                if trend_data:
                    trends[metric.name] = trend_data

            # Create analysis result
            result = AnalysisResult(
                metrics=metrics,
                baseline_comparisons=baseline_comparisons,
                threshold_violations=threshold_violations,
                bottlenecks=bottlenecks,
                recommendations=[],
                trends=trends
            )

            # Generate recommendations
            result.recommendations = await self.generate_recommendations(result)

            return result

        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}")
            return AnalysisResult(
                metrics=[],
                baseline_comparisons={},
                threshold_violations=[],
                bottlenecks=[],
                recommendations=[
                    f"Analysis failed: {str(e)}"
                ],
                trends={}
            )

if __name__ == "__main__":
    # Example usage
    async def main():
        analyzer = PerformanceAnalyzer()
        result = await analyzer.analyze_performance()
        print("Performance Analysis Results:")
        print(f"Metrics collected: {len(result.metrics)}")
        print(f"Threshold violations: {len(result.threshold_violations)}")
        print("Recommendations:")
        for rec in result.recommendations:
            print(f"- {rec}")

    import asyncio
    asyncio.run(main())

