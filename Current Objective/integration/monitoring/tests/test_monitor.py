"""
Test suite for the monitoring system manager and progress tracking.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import Dict, Any

from ..monitor import MonitoringManager, ProgressTracker, ResourceMonitor
from ..events import EventType, EventPriority, MonitoringEvent
from ...state_management.state_manager import StateManager, BuildPhase, BuildState

@pytest.fixture
def mock_state_manager() -> Mock:
    """Create mock state manager."""
    state_manager = Mock(spec=StateManager)
    state_manager.current_state = BuildState(
        phase=BuildPhase.INIT,
        status="PENDING"
    )
    return state_manager

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration."""
    return {
        "storage_path": "/tmp/test_monitoring",
        "phase_durations": {
            "INIT": 60,
            "SETUP": 300,
            "BUILD": 1800,
            "TEST": 900,
            "CLEANUP": 120
        },
        "thresholds": {
            "cpu_warning": 80,
            "cpu_critical": 95,
            "memory_warning": 75,
            "memory_critical": 90,
            "disk_warning": 85,
            "disk_critical": 95
        }
    }

@pytest.fixture
def monitoring_manager(test_config: Dict[str, Any], mock_state_manager: Mock) -> MonitoringManager:
    """Create monitoring manager instance."""
    return MonitoringManager(test_config, mock_state_manager)

class TestMonitoringManager:
    """Test cases for MonitoringManager functionality."""

    def test_initialization(self, monitoring_manager: MonitoringManager):
        """Test monitoring manager initialization."""
        assert monitoring_manager.config is not None
        assert monitoring_manager.metric_collector is not None
        assert monitoring_manager.progress_tracker is not None
        assert monitoring_manager.resource_monitor is not None
        assert monitoring_manager.event_dispatcher is not None

    def test_start_stop(self, monitoring_manager: MonitoringManager):
        """Test monitoring system start/stop."""
        monitoring_manager.start()
        assert monitoring_manager.resource_monitor.running
        assert monitoring_manager.event_dispatcher.running

        monitoring_manager.stop()
        assert not monitoring_manager.resource_monitor.running
        assert not monitoring_manager.event_dispatcher.running

    def test_state_update_handling(self, monitoring_manager: MonitoringManager):
        """Test state update handling."""
        state = BuildState(phase=BuildPhase.BUILD, status="RUNNING")
        monitoring_manager._handle_state_update(state)
        
        assert monitoring_manager.progress_tracker.current_phase == BuildPhase.BUILD
        monitoring_manager.state_manager.update_state.assert_called_once()

    def test_status_reporting(self, monitoring_manager: MonitoringManager):
        """Test status reporting."""
        status = monitoring_manager.get_current_status()
        
        assert "progress" in status
        assert "metrics" in status
        assert "aggregated_metrics" in status
        assert "last_update" in status

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_resource_monitoring(self, mock_memory, mock_cpu, monitoring_manager: MonitoringManager):
        """Test resource monitoring integration."""
        mock_cpu.return_value = 75.0
        mock_memory.return_value.percent = 80.0
        
        monitoring_manager.start()
        metrics = monitoring_manager.metric_collector.collect_metrics()
        
        assert "system" in metrics
        assert metrics["system"].cpu_usage == 75.0
        assert metrics["system"].memory_usage == 80.0

    def test_event_handling(self, monitoring_manager: MonitoringManager):
        """Test event handling."""
        test_event = MonitoringEvent.create(
            event_type=EventType.STATE_CHANGE,
            priority=EventPriority.HIGH,
            data={"phase": "BUILD"},
            source="test"
        )
        
        monitoring_manager._handle_state_change(test_event)
        assert monitoring_manager.progress_tracker.current_phase == BuildPhase.BUILD

class TestProgressTracker:
    """Test cases for ProgressTracker functionality."""

    @pytest.fixture
    def progress_tracker(self, test_config: Dict[str, Any]) -> ProgressTracker:
        """Create progress tracker instance."""
        return ProgressTracker(test_config)

    def test_phase_progress_calculation(self, progress_tracker: ProgressTracker):
        """Test phase progress calculation."""
        progress_tracker.start_phase(BuildPhase.BUILD)
        progress = progress_tracker.calculate_progress()
        
        assert "phase_progress" in progress
        assert "overall_progress" in progress
        assert 0 <= progress["phase_progress"] <= 100
        assert 0 <= progress["overall_progress"] <= 100

    def test_phase_completion(self, progress_tracker: ProgressTracker):
        """Test phase completion tracking."""
        # Complete INIT phase
        progress_tracker.start_phase(BuildPhase.INIT)
        progress_tracker.complete_phase(BuildPhase.INIT)
        
        # Start SETUP phase
        progress_tracker.start_phase(BuildPhase.SETUP)
        progress = progress_tracker.calculate_progress()
        
        assert progress["overall_progress"] >= 5.0  # INIT weight is 5%
        assert BuildPhase.INIT in progress_tracker.completed_phases

    def test_progress_weights(self, progress_tracker: ProgressTracker):
        """Test progress weight calculations."""
        # Complete multiple phases
        phases = [BuildPhase.INIT, BuildPhase.SETUP, BuildPhase.BUILD]
        for phase in phases:
            progress_tracker.start_phase(phase)
            progress_tracker.complete_phase(phase)
        
        progress = progress_tracker.calculate_progress()
        expected_progress = sum(progress_tracker.phase_weights[p] for p in phases) * 100
        assert progress["overall_progress"] == expected_progress

class TestResourceMonitor:
    """Test cases for ResourceMonitor functionality."""

    @pytest.fixture
    def resource_monitor(self, test_config: Dict[str, Any]) -> ResourceMonitor:
        """Create resource monitor instance."""
        return ResourceMonitor(test_config)

    @patch('psutil.cpu_percent')
    def test_threshold_checking(self, mock_cpu, resource_monitor: ResourceMonitor):
        """Test resource threshold checking."""
        mock_cpu.return_value = 96.0  # Above critical threshold
        
        metrics = resource_monitor.metric_collector.collect_metrics()
        alerts = resource_monitor._check_thresholds(metrics)
        
        assert alerts is not None
        assert ("CPU_CRITICAL", EventPriority.CRITICAL) in alerts

    def test_monitoring_cycle(self, resource_monitor: ResourceMonitor):
        """Test monitoring cycle execution."""
        resource_monitor.start()
        assert resource_monitor.running
        assert resource_monitor.monitor_thread is not None
        
        # Let monitor run briefly
        time.sleep(2)
        
        resource_monitor.stop()
        assert not resource_monitor.running
        assert resource_monitor.last_check is not None

