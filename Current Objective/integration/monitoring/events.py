"""
Event system implementation for the monitoring system.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Dict, Any, List, Callable, Optional
import logging
import queue
import threading
import uuid

class EventPriority(Enum):
    """Event priority levels."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

class EventType(Enum):
    """Event types."""
    METRIC_UPDATE = auto()
    THRESHOLD_EXCEEDED = auto()
    STATE_CHANGE = auto()
    RESOURCE_WARNING = auto()
    BUILD_PROGRESS = auto()
    SYSTEM_ALERT = auto()

@dataclass
class MonitoringEvent:
    """Monitoring system event."""
    id: str
    type: EventType
    priority: EventPriority
    timestamp: datetime
    data: Dict[str, Any]
    source: str

    @classmethod
    def create(cls, event_type: EventType, priority: EventPriority, 
               data: Dict[str, Any], source: str) -> 'MonitoringEvent':
        """Create a new event."""
        return cls(
            id=str(uuid.uuid4()),
            type=event_type,
            priority=priority,
            timestamp=datetime.utcnow(),
            data=data,
            source=source
        )

class EventDispatcher:
    """Handles event distribution and processing."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.event_queue = queue.PriorityQueue()
        self.running = False
        self.processing_thread: Optional[threading.Thread] = None

    def start(self):
        """Start event processing."""
        self.running = True
        self.processing_thread = threading.Thread(
            target=self._process_events,
            daemon=True
        )
        self.processing_thread.start()

    def stop(self):
        """Stop event processing."""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join()

    def dispatch_event(self, event: MonitoringEvent):
        """Dispatch an event to registered handlers."""
        try:
            # Add to queue with priority
            priority_value = self._get_priority_value(event.priority)
            self.event_queue.put((priority_value, event))
        except Exception as e:
            self.logger.error(f"Failed to dispatch event {event.id}: {e}")

    def register_handler(self, event_type: EventType, 
                        handler: Callable[[MonitoringEvent], None]):
        """Register an event handler."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def unregister_handler(self, event_type: EventType, 
                          handler: Callable[[MonitoringEvent], None]):
        """Unregister an event handler."""
        if event_type in self.handlers:
            self.handlers[event_type].remove(handler)

    def _process_events(self):
        """Process events from the queue."""
        while self.running:
            try:
                # Get event with timeout to allow checking running flag
                try:
                    _, event = self.event_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Process event
                self._handle_event(event)
                self.event_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")

    def _handle_event(self, event: MonitoringEvent):
        """Handle a single event."""
        if event.type in self.handlers:
            for handler in self.handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    self.logger.error(
                        f"Error in handler for event {event.id}: {e}"
                    )

    def _get_priority_value(self, priority: EventPriority) -> int:
        """Convert priority enum to numeric value for queue."""
        priority_values = {
            EventPriority.LOW: 30,
            EventPriority.MEDIUM: 20,
            EventPriority.HIGH: 10,
            EventPriority.CRITICAL: 0
        }
        return priority_values.get(priority, 100)

class AlertHandler:
    """Handles monitoring system alerts."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.alert_history: List[Dict[str, Any]] = []

    def handle_alert(self, alert: MonitoringEvent):
        """Process and handle an alert."""
        alert_data = {
            "id": alert.id,
            "timestamp": alert.timestamp,
            "type": alert.type.name,
            "priority": alert.priority.name,
            "data": alert.data
        }

        # Log alert
        self._log_alert(alert_data)

        # Take action based on priority
        if alert.priority == EventPriority.CRITICAL:
            self._handle_critical_alert(alert)
        elif alert.priority == EventPriority.HIGH:
            self._handle_high_priority_alert(alert)
        elif alert.priority == EventPriority.MEDIUM:
            self._handle_medium_priority_alert(alert)
        else:
            self._handle_low_priority_alert(alert)

    def _log_alert(self, alert_data: Dict[str, Any]):
        """Log alert details."""
        self.alert_history.append(alert_data)
        self.logger.warning(f"Alert: {alert_data}")

    def _handle_critical_alert(self, alert: MonitoringEvent):
        """Handle critical priority alert."""
        # Implement system pause/shutdown logic
        self.logger.critical(f"Critical alert: {alert.data}")
        # Trigger emergency procedures

    def _handle_high_priority_alert(self, alert: MonitoringEvent):
        """Handle high priority alert."""
        self.logger.error(f"High priority alert: {alert.data}")
        # Trigger immediate notification

    def _handle_medium_priority_alert(self, alert: MonitoringEvent):
        """Handle medium priority alert."""
        self.logger.warning(f"Medium priority alert: {alert.data}")
        # Add to notification queue

    def _handle_low_priority_alert(self, alert: MonitoringEvent):
        """Handle low priority alert."""
        self.logger.info(f"Low priority alert: {alert.data}")
        # Log for later analysis

