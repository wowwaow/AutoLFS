"""
Core monitoring system implementation.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
import threading
import time

from .metrics import MetricCollector, MetricAggregator
from .events import (
    EventDispatcher, MonitoringEvent, EventType, EventPriority, AlertHandler
)
from ..state_management.state_manager import StateManager, BuildPhase, BuildState

class ProgressTracker:
    """Tracks build progress and phase transitions."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.phase_weights = {
            BuildPhase.INIT: 0.05,
            BuildPhase.SETUP: 0.15,
            BuildPhase.BUILD: 0.40,
            BuildPhase.TEST: 0.30,
            BuildPhase.CLEANUP: 0.10
        }
        self.current_phase: Optional[BuildPhase] = None
        self.phase_start_time: Optional[datetime] = None
        self.build_start_time: Optional[datetime] = None
        self.completed_phases: List[BuildPhase] = []

    def start_phase(self, phase: BuildPhase):
        """Start tracking a new phase."""
        self.current_phase = phase
        self.phase_start_time = datetime.utcnow()
        if not self.build_start_time:
            self.build_start_time = self.phase_start_time

    def complete_phase(self, phase: BuildPhase):
        """Mark a phase as completed."""
        if phase not in self.completed_phases:
            self.completed_phases.append(phase)

    def calculate_progress(self) -> Dict[str, float]:
        """Calculate current progress metrics."""
        if not self.current_phase or not self.phase_start_time:
            return {"phase_progress": 0.0, "overall_progress": 0.0}

        # Calculate phase progress
        phase_progress = self._calculate_phase_progress()

        # Calculate overall progress
        completed_weight = sum(
            self.phase_weights[phase] for phase in self.completed_phases
        )
        current_weight = self.phase_weights[self.current_phase] * phase_progress
        overall_progress = completed_weight + current_weight

        return {
            "phase_progress": phase_progress * 100,
            "overall_progress": overall_progress * 100
        }

    def _calculate_phase_progress(self) -> float:
        """Calculate progress within current phase."""
        if not self.current_phase or not self.phase_start_time:
            return 0.0

        # Calculate based on typical phase duration
        typical_duration = self.config.get("phase_durations", {}).get(
            self.current_phase.name, 300
        )
        elapsed = (datetime.utcnow() - self.phase_start_time).total_seconds()
        return min(elapsed / typical_duration, 1.0)

class ResourceMonitor:
    """Monitors system resource usage."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.metric_collector = MetricCollector(config)
        self.thresholds = config.get("thresholds", {})
        self.last_check: Optional[datetime] = None
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None

    def start(self):
        """Start resource monitoring."""
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_resources,
            daemon=True
        )
        self.monitor_thread.start()

    def stop(self):
        """Stop resource monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()

    def _monitor_resources(self):
        """Monitor resources periodically."""
        while self.running:
            try:
                metrics = self.metric_collector.collect_metrics()
                self._check_thresholds(metrics)
                self.last_check = datetime.utcnow()
                time.sleep(self.config.get("check_interval", 5))
            except Exception as e:
                self.logger.error(f"Error monitoring resources: {e}")

    def _check_thresholds(self, metrics: Dict[str, Any]):
        """Check metrics against thresholds."""
        if "system" not in metrics:
            return

        system_metrics = metrics["system"]
        alerts = []

        # Check CPU usage
        if system_metrics.cpu_usage > self.thresholds.get("cpu_critical", 95):
            alerts.append(("CPU_CRITICAL", EventPriority.CRITICAL))
        elif system_metrics.cpu_usage > self.thresholds.get("cpu_warning", 80):
            alerts.append(("CPU_WARNING", EventPriority.HIGH))

        # Check memory usage
        if system_metrics.memory_usage > self.thresholds.get("memory_critical", 90):
            alerts.append(("MEMORY_CRITICAL", EventPriority.CRITICAL))
        elif system_metrics.memory_usage > self.thresholds.get("memory_warning", 75):
            alerts.append(("MEMORY_WARNING", EventPriority.HIGH))

        # Check disk usage
        if system_metrics.disk_usage > self.thresholds.get("disk_critical", 95):
            alerts.append(("DISK_CRITICAL", EventPriority.CRITICAL))
        elif system_metrics.disk_usage > self.thresholds.get("disk_warning", 85):
            alerts.append(("DISK_WARNING", EventPriority.HIGH))

        return alerts

class MonitoringManager:
    """Core monitoring system manager."""

    def __init__(self, config: Dict[str, Any], state_manager: StateManager):
        self.config = config
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.metric_collector = MetricCollector(config)
        self.metric_aggregator = MetricAggregator(config)
        self.progress_tracker = ProgressTracker(config)
        self.resource_monitor = ResourceMonitor(config)
        self.event_dispatcher = EventDispatcher(config)
        self.alert_handler = AlertHandler(config)

        # Register event handlers
        self._register_event_handlers()

    def start(self):
        """Start the monitoring system."""
        try:
            # Start components
            self.resource_monitor.start()
            self.event_dispatcher.start()

            # Register with state manager
            self._register_state_handlers()

            self.logger.info("Monitoring system started")
        except Exception as e:
            self.logger.error(f"Failed to start monitoring system: {e}")
            raise

    def stop(self):
        """Stop the monitoring system."""
        try:
            self.resource_monitor.stop()
            self.event_dispatcher.stop()
            self.logger.info("Monitoring system stopped")
        except Exception as e:
            self.logger.error(f"Error stopping monitoring system: {e}")

    def _register_event_handlers(self):
        """Register event handlers."""
        self.event_dispatcher.register_handler(
            EventType.THRESHOLD_EXCEEDED,
            self.alert_handler.handle_alert
        )
        self.event_dispatcher.register_handler(
            EventType.SYSTEM_ALERT,
            self.alert_handler.handle_alert
        )
        self.event_dispatcher.register_handler(
            EventType.STATE_CHANGE,
            self._handle_state_change
        )

    def _register_state_handlers(self):
        """Register handlers with state manager."""
        if hasattr(self.state_manager, 'register_state_handler'):
            self.state_manager.register_state_handler(
                self._handle_state_update
            )

    def _handle_state_change(self, event: MonitoringEvent):
        """Handle state change events."""
        if 'phase' in event.data:
            phase = BuildPhase[event.data['phase']]
            self.progress_tracker.start_phase(phase)

    def _handle_state_update(self, state: BuildState):
        """Handle state updates from state manager."""
        # Update progress tracking
        self.progress_tracker.start_phase(state.phase)
        
        # Collect and aggregate metrics
        metrics = self.metric_collector.collect_metrics()
        self.metric_aggregator.add_metrics(metrics)
        
        # Calculate progress
        progress = self.progress_tracker.calculate_progress()
        
        # Update state with monitoring data
        self.state_manager.update_state({
            "metadata": {
                "monitoring": {
                    "metrics": metrics,
                    "progress": progress,
                    "last_update": datetime.utcnow().isoformat()
                }
            }
        })

    def get_current_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "progress": self.progress_tracker.calculate_progress(),
            "metrics": self.metric_collector.collect_metrics(),
            "aggregated_metrics": self.metric_aggregator.get_aggregated_metrics("5m"),
            "resource_status": "healthy",  # TODO: Implement health check
            "last_update": datetime.utcnow().isoformat()
        }

