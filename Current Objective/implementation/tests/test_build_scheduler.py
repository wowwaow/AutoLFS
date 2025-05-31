"""
Unit tests for the BuildScheduler class.

Tests build scheduling, parallel execution, resource management,
and build status monitoring functionality.
"""

import time
from queue import PriorityQueue
from unittest.mock import Mock, patch

import pytest

from lfs_wrapper.build_scheduler import (
    BuildPriority,
    BuildScheduler,
    BuildTask,
    ResourceAllocation,
    SchedulerError
)
from lfs_wrapper.build_manager import BuildPhase


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        'build': {
            'parallel_builds': 2,
            'max_memory_percent': 80,
            'min_free_memory_mb': 1024
        }
    }


@pytest.fixture
def mock_build_manager():
    """Provide a mock BuildManager."""
    manager = Mock()
    manager.execute_phase.return_value = True
    return manager


@pytest.fixture
def mock_dependency_resolver():
    """Provide a mock DependencyResolver."""
    resolver = Mock()
    resolver.resolve_dependencies.return_value = ["pkg1"]
    return resolver


@pytest.fixture
def scheduler(test_config, mock_build_manager, mock_dependency_resolver):
    """Provide a BuildScheduler instance."""
    return BuildScheduler(
        mock_build_manager,
        mock_dependency_resolver,
        test_config
    )


def test_resource_allocation_init(test_config):
    """Test ResourceAllocation initialization."""
    resource_mgr = ResourceAllocation(test_config)
    assert resource_mgr.max_cpu > 0
    assert resource_mgr.max_memory > 0
    assert resource_mgr.allocated_cpu == 0
    assert resource_mgr.allocated_memory == 0


def test_resource_allocation(test_config):
    """Test resource allocation and release."""
    resource_mgr = ResourceAllocation(test_config)
    requirements = {'cpu_count': 2, 'memory_mb': 1024}
    
    assert resource_mgr.can_allocate(requirements)
    assert resource_mgr.allocate(requirements)
    assert resource_mgr.allocated_cpu == 2
    assert resource_mgr.allocated_memory == 1024 * 1024 * 1024
    
    resource_mgr.release(requirements)
    assert resource_mgr.allocated_cpu == 0
    assert resource_mgr.allocated_memory == 0


def test_build_task_priority_ordering():
    """Test BuildTask priority ordering."""
    high_priority = BuildTask(BuildPriority.HIGH, "pkg1")
    normal_priority = BuildTask(BuildPriority.NORMAL, "pkg2")
    low_priority = BuildTask(BuildPriority.LOW, "pkg3")
    
    assert high_priority < normal_priority < low_priority


def test_schedule_build(scheduler):
    """Test build task scheduling."""
    scheduler.schedule_build("test_pkg", BuildPriority.HIGH)
    assert not scheduler.build_queue.empty()
    task = scheduler.build_queue.get()
    assert task.package == "test_pkg"
    assert task.priority == BuildPriority.HIGH


def test_schedule_build_with_dependencies(scheduler, mock_dependency_resolver):
    """Test build scheduling with dependencies."""
    mock_dependency_resolver.resolve_dependencies.return_value = ["dep1", "test_pkg"]
    
    scheduler.schedule_build("test_pkg")
    task = scheduler.build_queue.get()
    assert "dep1" in task.dependencies


def test_scheduler_start_stop(scheduler):
    """Test scheduler thread start/stop."""
    scheduler.start_scheduler()
    assert scheduler.scheduler_thread.is_alive()
    
    scheduler.stop_scheduler()
    assert not scheduler.is_running
    assert not scheduler.scheduler_thread.is_alive()


@patch('time.sleep', return_value=None)
def test_process_queue(mock_sleep, scheduler):
    """Test build queue processing."""
    # Add a task without dependencies
    task = BuildTask(BuildPriority.NORMAL, "test_pkg")
    scheduler.build_queue.put(task)
    
    # Process queue
    scheduler._process_queue()
    
    # Task should be started
    assert "test_pkg" in scheduler.active_builds


def test_build_execution(scheduler):
    """Test build task execution."""
    task = BuildTask(
        priority=BuildPriority.NORMAL,
        package="test_pkg",
        phase=BuildPhase.SYSTEM
    )
    
    scheduler._execute_build(task)
    
    # Verify build manager was called
    scheduler.build_manager.execute_phase.assert_called_once_with(BuildPhase.SYSTEM)
    assert "test_pkg" in scheduler.completed_builds


def test_build_status(scheduler):
    """Test build status reporting."""
    # Add some builds in different states
    scheduler.build_queue.put(BuildTask(BuildPriority.NORMAL, "queued_pkg"))
    scheduler.active_builds["active_pkg"] = BuildTask(
        BuildPriority.HIGH,
        "active_pkg",
        start_time=time.time()
    )
    scheduler.completed_builds.add("completed_pkg")
    
    status = scheduler.get_build_status()
    assert status['queued_builds'] == 1
    assert len(status['active_builds']) == 1
    assert status['completed_builds'] == 1


def test_estimate_completion_time(scheduler):
    """Test build completion time estimation."""
    # Add completed build
    scheduler.completed_builds.add("completed_pkg")
    assert scheduler.estimate_completion_time("completed_pkg") == 0.0
    
    # Add active build
    task = BuildTask(
        priority=BuildPriority.NORMAL,
        package="active_pkg",
        estimated_duration=100.0,
        start_time=time.time() - 50
    )
    scheduler.active_builds["active_pkg"] = task
    estimate = scheduler.estimate_completion_time("active_pkg")
    assert 45 <= estimate <= 50
    
    # Add queued build
    scheduler.build_queue.put(BuildTask(
        priority=BuildPriority.NORMAL,
        package="queued_pkg",
        estimated_duration=200.0
    ))
    assert scheduler.estimate_completion_time("queued_pkg") == 200.0


def test_parallel_build_limits(scheduler):
    """Test parallel build limit enforcement."""
    # Configure for max 2 parallel builds
    scheduler.config = {'build': {'parallel_builds': 2}}
    
    # Add three build tasks
    for i in range(3):
        task = BuildTask(BuildPriority.NORMAL, f"pkg{i}")
        scheduler.build_queue.put(task)
    
    # Process queue multiple times
    for _ in range(3):
        scheduler._process_queue()
    
    # Should only have started 2 builds
    assert len(scheduler.active_builds) <= 2


def test_resource_constraints(scheduler):
    """Test resource constraint enforcement."""
    # Add task with high resource requirements
    requirements = {
        'cpu_count': 999,  # More than available
        'memory_mb': 999999
    }
    
    task = BuildTask(
        priority=BuildPriority.HIGH,
        package="resource_heavy_pkg",
        resource_requirements=requirements
    )
    
    scheduler.build_queue.put(task)
    scheduler._process_queue()
    
    # Build should not have started
    assert "resource_heavy_pkg" not in scheduler.active_builds


def test_build_failure_handling(scheduler):
    """Test handling of build failures."""
    scheduler.build_manager.execute_phase.side_effect = Exception("Build failed")
    
    task = BuildTask(BuildPriority.NORMAL, "failing_pkg")
    scheduler._execute_build(task)
    
    # Should not be in completed builds
    assert "failing_pkg" not in scheduler.completed_builds
    # Should have released resources
    assert task.package not in scheduler.active_builds

