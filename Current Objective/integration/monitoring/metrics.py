"""
Core metrics collection and management implementation.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import psutil
import logging

@dataclass
class ResourceMetrics:
    """System resource metrics."""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_bandwidth: float
    io_operations: int
    timestamp: datetime = None

    def __post_init__(self):
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
            "network_bandwidth": self.network_bandwidth,
            "io_operations": self.io_operations,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class BuildMetrics:
    """Build process metrics."""
    phase_progress: float
    overall_progress: float
    phase_duration: timedelta
    total_duration: timedelta
    step_count: int
    timestamp: datetime = None

    def __post_init__(self):
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "phase_progress": self.phase_progress,
            "overall_progress": self.overall_progress,
            "phase_duration": self.phase_duration.total_seconds(),
            "total_duration": self.total_duration.total_seconds(),
            "step_count": self.step_count,
            "timestamp": self.timestamp.isoformat()
        }

class MetricCollector:
    """Collects and manages system metrics."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.collectors = {}
        self._initialize_collectors()

    def _initialize_collectors(self):
        """Initialize metric collectors."""
        self.collectors = {
            "system": self._collect_system_metrics,
            "build": self._collect_build_metrics,
            "performance": self._collect_performance_metrics,
            "resource": self._collect_resource_metrics
        }

    def collect_metrics(self) -> Dict[str, Any]:
        """Collect all metrics."""
        metrics = {}
        for collector_name, collector_func in self.collectors.items():
            try:
                metrics[collector_name] = collector_func()
            except Exception as e:
                self.logger.error(f"Failed to collect {collector_name} metrics: {e}")
        return metrics

    def _collect_system_metrics(self) -> ResourceMetrics:
        """Collect system resource metrics."""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            net_io = psutil.net_io_counters()
            disk_io = psutil.disk_io_counters()

            return ResourceMetrics(
                cpu_usage=cpu,
                memory_usage=memory,
                disk_usage=disk,
                network_bandwidth=net_io.bytes_sent + net_io.bytes_recv,
                io_operations=disk_io.read_count + disk_io.write_count
            )
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            raise

    def _collect_build_metrics(self) -> Optional[BuildMetrics]:
        """Collect build process metrics."""
        # This will be populated with actual build data from the state manager
        return None

    def _collect_performance_metrics(self) -> Dict[str, float]:
        """Collect performance metrics."""
        return {
            "build_speed": 0.0,
            "resource_efficiency": 0.0,
            "error_rate": 0.0
        }

    def _collect_resource_metrics(self) -> Dict[str, Any]:
        """Collect detailed resource metrics."""
        return {
            "memory_detailed": self._get_detailed_memory_metrics(),
            "cpu_detailed": self._get_detailed_cpu_metrics(),
            "disk_detailed": self._get_detailed_disk_metrics()
        }

    def _get_detailed_memory_metrics(self) -> Dict[str, Any]:
        """Get detailed memory metrics."""
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "free": mem.free,
            "percent": mem.percent
        }

    def _get_detailed_cpu_metrics(self) -> Dict[str, Any]:
        """Get detailed CPU metrics."""
        return {
            "per_cpu": psutil.cpu_percent(interval=1, percpu=True),
            "load_avg": psutil.getloadavg(),
            "ctx_switches": psutil.cpu_stats().ctx_switches,
            "interrupts": psutil.cpu_stats().interrupts
        }

    def _get_detailed_disk_metrics(self) -> Dict[str, Any]:
        """Get detailed disk metrics."""
        disk = psutil.disk_usage('/')
        io = psutil.disk_io_counters()
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "read_bytes": io.read_bytes,
            "write_bytes": io.write_bytes
        }

class MetricAggregator:
    """Aggregates metrics over time."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.aggregation_windows = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1)
        }
        self.metric_history = {}

    def add_metrics(self, metrics: Dict[str, Any]):
        """Add metrics to history."""
        timestamp = datetime.utcnow()
        for metric_type, values in metrics.items():
            if metric_type not in self.metric_history:
                self.metric_history[metric_type] = []
            self.metric_history[metric_type].append((timestamp, values))
        self._cleanup_old_metrics()

    def get_aggregated_metrics(self, window: str) -> Dict[str, Any]:
        """Get aggregated metrics for time window."""
        if window not in self.aggregation_windows:
            raise ValueError(f"Invalid aggregation window: {window}")

        window_td = self.aggregation_windows[window]
        cutoff = datetime.utcnow() - window_td
        aggregated = {}

        for metric_type, history in self.metric_history.items():
            window_metrics = [m for t, m in history if t >= cutoff]
            if window_metrics:
                aggregated[metric_type] = self._aggregate_metrics(window_metrics)

        return aggregated

    def _aggregate_metrics(self, metrics: List[Any]) -> Dict[str, float]:
        """Aggregate metrics using configured rules."""
        if not metrics:
            return {}

        # Handle different metric types
        if isinstance(metrics[0], ResourceMetrics):
            return self._aggregate_resource_metrics(metrics)
        elif isinstance(metrics[0], BuildMetrics):
            return self._aggregate_build_metrics(metrics)
        elif isinstance(metrics[0], dict):
            return self._aggregate_dict_metrics(metrics)
        return {}

    def _cleanup_old_metrics(self):
        """Remove metrics older than the longest aggregation window."""
        max_age = max(self.aggregation_windows.values())
        cutoff = datetime.utcnow() - max_age

        for metric_type in self.metric_history:
            self.metric_history[metric_type] = [
                (t, m) for t, m in self.metric_history[metric_type]
                if t >= cutoff
            ]

