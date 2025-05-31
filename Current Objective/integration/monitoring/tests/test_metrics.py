"""
Test suite for metrics collection and aggregation.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from typing import Dict, Any

from ..metrics import (
    MetricCollector, MetricAggregator,
    ResourceMetrics, BuildMetrics
)

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration."""
    return {
        "collection_interval": 5,
        "aggregation_windows": ["1m", "5m", "15m", "1h"],
        "retention_period": "1h"
    }

class TestMetricCollector:
    """Test cases for MetricCollector functionality."""

    @pytest.fixture
    def metric_collector(self, test_config: Dict[str, Any]) -> MetricCollector:
        """Create metric collector instance."""
        return MetricCollector(test_config)

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    @patch('psutil.disk_io_counters')
    def test_system_metrics_collection(
        self, mock_disk_io, mock_net_io, mock_disk,
        mock_memory, mock_cpu, metric_collector: MetricCollector
    ):
        """Test system metrics collection."""
        # Setup mocks
        mock_cpu.return_value = 45.0
        mock_memory.return_value.percent = 60.0
        mock_disk.return_value.percent = 55.0
        mock_net_io.return_value = Mock(
            bytes_sent=1000,
            bytes_recv=2000
        )
        mock_disk_io.return_value = Mock(
            read_count=100,
            write_count=200
        )

        # Collect metrics
        metrics = metric_collector.collect_metrics()
        system_metrics = metrics["system"]

        # Verify metrics
        assert isinstance(system_metrics, ResourceMetrics)
        assert system_metrics.cpu_usage == 45.0
        assert system_metrics.memory_usage == 60.0
        assert system_metrics.disk_usage == 55.0
        assert system_metrics.network_bandwidth == 3000
        assert system_metrics.io_operations == 300

    def test_build_metrics_collection(self, metric_collector: MetricCollector):
        """Test build metrics collection."""
        metrics = metric_collector.collect_metrics()
        assert "build" in metrics
        assert metrics["build"] is None  # Should be None until integrated with state

    def test_performance_metrics_collection(self, metric_collector: MetricCollector):
        """Test performance metrics collection."""
        metrics = metric_collector.collect_metrics()
        performance = metrics["performance"]

        assert "build_speed" in performance
        assert "resource_efficiency" in performance
        assert "error_rate" in performance

    def test_detailed_resource_metrics(self, metric_collector: MetricCollector):
        """Test detailed resource metrics collection."""
        metrics = metric_collector.collect_metrics()
        detailed = metrics["resource"]

        assert "memory_detailed" in detailed
        assert "cpu_detailed" in detailed
        assert "disk_detailed" in detailed

    @patch('psutil.cpu_percent', side_effect=Exception("Test error"))
    def test_error_handling(self, mock_cpu, metric_collector: MetricCollector):
        """Test error handling in metric collection."""
        metrics = metric_collector.collect_metrics()
        assert "system" not in metrics  # Should skip failed collector

class TestMetricAggregator:
    """Test cases for MetricAggregator functionality."""

    @pytest.fixture
    def metric_aggregator(self, test_config: Dict[str, Any]) -> MetricAggregator:
        """Create metric aggregator instance."""
        return MetricAggregator(test_config)

    def test_metric_addition(self, metric_aggregator: MetricAggregator):
        """Test adding metrics to history."""
        metrics = {
            "system": ResourceMetrics(
                cpu_usage=50.0,
                memory_usage=60.0,
                disk_usage=70.0,
                network_bandwidth=1000,
                io_operations=100
            )
        }
        
        metric_aggregator.add_metrics(metrics)
        assert "system" in metric_aggregator.metric_history
        assert len(metric_aggregator.metric_history["system"]) == 1

    def test_aggregation_windows(self, metric_aggregator: MetricAggregator):
        """Test different aggregation windows."""
        # Add metrics with different timestamps
        now = datetime.utcnow()
        
        for minutes in range(10):
            timestamp = now - timedelta(minutes=minutes)
            metrics = {
                "system": ResourceMetrics(
                    cpu_usage=50.0 + minutes,
                    memory_usage=60.0,
                    disk_usage=70.0,
                    network_bandwidth=1000,
                    io_operations=100
                )
            }
            metric_aggregator.add_metrics(metrics)

        # Test different windows
        for window in ["1m", "5m"]:
            aggregated = metric_aggregator.get_aggregated_metrics(window)
            assert "system" in aggregated

    def test_old_metric_cleanup(self, metric_aggregator: MetricAggregator):
        """Test cleanup of old metrics."""
        # Add old metrics
        old_time = datetime.utcnow() - timedelta(hours=2)
        metrics = {
            "system": ResourceMetrics(
                cpu_usage=50.0,
                memory_usage=60.0,
                disk_usage=70.0,
                network_bandwidth=1000,
                io_operations=100
            )
        }
        
        metric_aggregator.metric_history["system"] = [(old_time, metrics["system"])]
        
        # Trigger cleanup
        metric_aggregator._cleanup_old_metrics()
        assert len(metric_aggregator.metric_history["system"]) == 0

    def test_invalid_window(self, metric_aggregator: MetricAggregator):
        """Test handling of invalid aggregation window."""
        with pytest.raises(ValueError):
            metric_aggregator.get_aggregated_metrics("invalid")

    def test_mixed_metric_types(self, metric_aggregator: MetricAggregator):
        """Test aggregation of different metric types."""
        metrics = {
            "system": ResourceMetrics(
                cpu_usage=50.0,
                memory_usage=60.0,
                disk_usage=70.0,
                network_bandwidth=1000,
                io_operations=100
            ),
            "build": BuildMetrics(
                phase_progress=75.0,
                overall_progress=50.0,
                phase_duration=timedelta(minutes=30),
                total_duration=timedelta(hours=1),
                step_count=100
            )
        }
        
        metric_aggregator.add_metrics(metrics)
        aggregated = metric_aggregator.get_aggregated_metrics("5m")
        
        assert "system" in aggregated
        assert "build" in aggregated

