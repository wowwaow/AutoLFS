"""
Unit tests for the BenchmarkManager class.

Tests performance measurement, analysis, and reporting
functionality.
"""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

import psutil
import pytest

from lfs_wrapper.benchmark_manager import (
    BenchmarkManager,
    BenchmarkResult,
    MetricSample,
    MetricType,
    PerformanceReport
)
from lfs_wrapper.build_manager import BuildPhase
from lfs_wrapper.exceptions import BenchmarkError


@pytest.fixture
def test_config(tmp_path):
    """Provide test configuration."""
    return {
        'benchmark': {
            'history_file': str(tmp_path / "benchmark_history.json"),
            'collection_interval': 1,
            'max_history': 100
        }
    }


@pytest.fixture
def benchmark_manager(test_config):
    """Provide BenchmarkManager instance."""
    return BenchmarkManager(test_config)


@pytest.fixture
def test_metrics():
    """Provide test metric samples."""
    timestamp = time.time()
    return [
        MetricSample(
            metric_type=MetricType.CPU_USAGE,
            value=50.0,
            timestamp=timestamp,
            context={'per_cpu': [50.0, 50.0]}
        ),
        MetricSample(
            metric_type=MetricType.MEMORY_USAGE,
            value=75.0,
            timestamp=timestamp,
            context={'total': 16000, 'available': 4000}
        ),
        MetricSample(
            metric_type=MetricType.DISK_IO,
            value=1000000,
            timestamp=timestamp,
            context={'read_bytes': 500000, 'write_bytes': 500000}
        )
    ]


def test_benchmark_initialization(benchmark_manager):
    """Test benchmark manager initialization."""
    assert benchmark_manager.history_file.exists()
    history = benchmark_manager._load_history()
    assert isinstance(history, list)


def test_start_benchmark(benchmark_manager):
    """Test starting a benchmark."""
    benchmark_manager.start_benchmark(BuildPhase.TOOLCHAIN)
    assert hasattr(benchmark_manager, '_current_benchmark')
    assert benchmark_manager._current_benchmark['phase'] == BuildPhase.TOOLCHAIN


def test_stop_benchmark(benchmark_manager):
    """Test stopping a benchmark."""
    benchmark_manager.start_benchmark(BuildPhase.TOOLCHAIN)
    result = benchmark_manager.stop_benchmark()
    
    assert isinstance(result, BenchmarkResult)
    assert result.phase == BuildPhase.TOOLCHAIN
    assert not hasattr(benchmark_manager, '_current_benchmark')


def test_stop_benchmark_without_start(benchmark_manager):
    """Test stopping a benchmark that wasn't started."""
    with pytest.raises(BenchmarkError):
        benchmark_manager.stop_benchmark()


@patch('psutil.cpu_percent')
@patch('psutil.virtual_memory')
@patch('psutil.disk_io_counters')
def test_collect_sample(
    mock_io,
    mock_memory,
    mock_cpu,
    benchmark_manager
):
    """Test metric sample collection."""
    # Mock system metrics
    mock_cpu.return_value = 50.0
    mock_memory.return_value = Mock(
        percent=75.0,
        _asdict=lambda: {'total': 16000, 'available': 4000}
    )
    mock_io.return_value = Mock(
        read_bytes=500000,
        write_bytes=500000,
        _asdict=lambda: {'read_bytes': 500000, 'write_bytes': 500000}
    )
    
    benchmark_manager.start_benchmark(BuildPhase.TOOLCHAIN)
    benchmark_manager.collect_sample()
    
    metrics = benchmark_manager._current_benchmark['metrics']
    assert len(metrics) == 3  # CPU, Memory, Disk I/O
    assert any(m.metric_type == MetricType.CPU_USAGE for m in metrics)
    assert any(m.metric_type == MetricType.MEMORY_USAGE for m in metrics)
    assert any(m.metric_type == MetricType.DISK_IO for m in metrics)


def test_generate_report(benchmark_manager, test_metrics):
    """Test performance report generation."""
    # Create test benchmark result
    benchmark = BenchmarkResult(
        phase=BuildPhase.TOOLCHAIN,
        start_time=time.time() - 100,
        end_time=time.time(),
        metrics=test_metrics,
        summary=benchmark_manager._calculate_summary(test_metrics),
        system_info=benchmark_manager._collect_system_info()
    )
    
    report = benchmark_manager.generate_report(benchmark)
    assert isinstance(report, PerformanceReport)
    assert report.benchmark == benchmark
    assert isinstance(report.recommendations, list)


def test_generate_report_with_baseline(benchmark_manager, test_metrics):
    """Test performance report generation with baseline comparison."""
    # Create baseline with better performance
    baseline_metrics = [
        MetricSample(
            metric_type=m.metric_type,
            value=m.value * 0.8,  # 20% better
            timestamp=time.time(),
            context=m.context
        )
        for m in test_metrics
    ]
    
    current = BenchmarkResult(
        phase=BuildPhase.TOOLCHAIN,
        start_time=time.time() - 100,
        end_time=time.time(),
        metrics=test_metrics,
        summary=benchmark_manager._calculate_summary(test_metrics),
        system_info=benchmark_manager._collect_system_info()
    )
    
    baseline = BenchmarkResult(
        phase=BuildPhase.TOOLCHAIN,
        start_time=time.time() - 300,
        end_time=time.time() - 200,
        metrics=baseline_metrics,
        summary=benchmark_manager._calculate_summary(baseline_metrics),
        system_info=benchmark_manager._collect_system_info()
    )
    
    report = benchmark_manager.generate_report(current, baseline)
    assert report.baseline == baseline
    assert report.comparison is not None
    assert len(report.recommendations) > 0


def test_get_baseline(benchmark_manager, test_metrics):
    """Test retrieving baseline benchmark."""
    # Create and save a test result
    result = BenchmarkResult(
        phase=BuildPhase.TOOLCHAIN,
        start_time=time.time() - 100,
        end_time=time.time(),
        metrics=test_metrics,
        summary=benchmark_manager._calculate_summary(test_metrics),
        system_info=benchmark_manager._collect_system_info()
    )
    benchmark_manager._save_result(result)
    
    baseline = benchmark_manager.get_baseline(BuildPhase.TOOLCHAIN)
    assert baseline is not None
    assert baseline.phase == BuildPhase.TOOLCHAIN


def test_calculate_summary(benchmark_manager, test_metrics):
    """Test metric summary calculation."""
    summary = benchmark_manager._calculate_summary(test_metrics)
    
    for metric_type in MetricType:
        type_metrics = [m for m in test_metrics if m.metric_type == metric_type]
        if type_metrics:
            assert metric_type in summary
            assert 'mean' in summary[metric_type]
            assert 'median' in summary[metric_type]
            assert 'min' in summary[metric_type]
            assert 'max' in summary[metric_type]


def test_compare_benchmarks(benchmark_manager, test_metrics):
    """Test benchmark comparison."""
    # Create two benchmark results with different metrics
    current = BenchmarkResult(
        phase=BuildPhase.TOOLCHAIN,
        start_time=time.time() - 100,
        end_time=time.time(),
        metrics=test_metrics,
        summary=benchmark_manager._calculate_summary(test_metrics),
        system_info=benchmark_manager._collect_system_info()
    )
    
    baseline_metrics = [
        MetricSample(
            metric_type=m.metric_type,
            value=m.value * 0.8,  # 20% better
            timestamp=time.time(),
            context=m.context
        )
        for m in test_metrics
    ]
    
    baseline = BenchmarkResult(
        phase=BuildPhase.TOOLCHAIN,
        start_time=time.time() - 300,
        end_time=time.time() - 200,
        metrics=baseline_metrics,
        summary=benchmark_manager._calculate_summary(baseline_metrics),
        system_info=benchmark_manager._collect_system_info()
    )
    
    comparison = benchmark_manager._compare_benchmarks(current, baseline)
    assert comparison[MetricType.CPU_USAGE] == pytest.approx(25.0)  # 25% worse
    assert comparison[MetricType.MEMORY_USAGE] == pytest.approx(25.0)


def test_generate_recommendations(benchmark_manager, test_metrics):
    """Test recommendation generation."""
    # Create benchmark with high resource usage
    high_usage_metrics = [
        MetricSample(
            metric_type=MetricType.CPU_USAGE,
            value=95.0,
            timestamp=time.time(),
            context={'per_cpu': [95.0, 95.0]}
        ),
        MetricSample(
            metric_type=MetricType.MEMORY_USAGE,
            value=92.0,
            timestamp=time.time(),
            context={'total': 16000, 'available': 1280}
        )
    ]
    
    result = BenchmarkResult(
        phase=BuildPhase.TOOLCHAIN,
        start_time=time.time() - 100,
        end_time=time.time(),
        metrics=high_usage_metrics,
        summary=benchmark_manager._calculate_summary(high_usage_metrics),
        system_info=benchmark_manager._collect_system_info()
    )
    
    recommendations = benchmark_manager._generate_recommendations(result)
    assert len(recommendations) >= 2
    assert any('CPU' in r for r in recommendations)
    assert any('memory' in r for r in recommendations)


def test_benchmark_history(benchmark_manager, test_metrics):
    """Test benchmark history management."""
    # Create and save multiple results
    for i in range(3):
        result = BenchmarkResult(
            phase=BuildPhase.TOOLCHAIN,
            start_time=time.time() - 100 * (i + 1),
            end_time=time.time() - 100 * i,
            metrics=test_metrics,
            summary=benchmark_manager._calculate_summary(test_metrics),
            system_info=benchmark_manager._collect_system_info()
        )
        benchmark_manager._save_result(result)
    
    history = benchmark_manager._load_history()
    assert len(history) == 3
    
    # Verify serialization/deserialization
    result = benchmark_manager._deserialize_result(history[0])
    assert isinstance(result, BenchmarkResult)
    assert result.phase == BuildPhase.TOOLCHAIN

