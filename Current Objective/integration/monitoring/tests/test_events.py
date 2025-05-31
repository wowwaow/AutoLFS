"""
Test suite for monitoring system event handling.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from typing import Dict, Any
import threading
import time

from ..events import (
    EventDispatcher, EventType, EventPriority,
    MonitoringEvent, AlertHandler
)

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration."""
    return {
        "event_queue_size": 1000,
        "processing_threads": 1,
        "alert_retention": "24h"
    }

@pytest.fixture
def test_event() -> MonitoringEvent:
    """Create test monitoring event."""
    return MonitoringEvent.create(
        event_type=EventType.SYSTEM_ALERT,
        priority=EventPriority.HIGH,
        data={"message": "Test alert"},
        source="test_suite"
    )

class TestEventDispatcher:
    """Test cases for EventDispatcher functionality."""

    @pytest.fixture
    def event_dispatcher(self, test_config: Dict[str, Any]) -> EventDispatcher:
        """Create event dispatcher instance."""
        return EventDispatcher(test_config)

    def test_initialization(self, event_dispatcher: EventDispatcher):
        """Test event dispatcher initialization."""
        assert event_dispatcher.config is not None
        assert event_dispatcher.handlers == {}
        assert not event_dispatcher.running
        assert event_dispatcher.processing_thread is None

    def test_handler_registration(self, event_dispatcher: EventDispatcher):
        """Test event handler registration."""
        mock_handler = Mock()
        event_dispatcher.register_handler(EventType.SYSTEM_ALERT, mock_handler)
        
        assert EventType.SYSTEM_ALERT in event_dispatcher.handlers
        assert mock_handler in event_dispatcher.handlers[EventType.SYSTEM_ALERT]

        # Test unregistration
        event_dispatcher.unregister_handler(EventType.SYSTEM_ALERT, mock_handler)
        assert mock_handler not in event_dispatcher.handlers[EventType.SYSTEM_ALERT]

    def test_event_dispatch(self, event_dispatcher: EventDispatcher, test_event: MonitoringEvent):
        """Test event dispatching."""
        mock_handler = Mock()
        event_dispatcher.register_handler(test_event.type, mock_handler)
        
        event_dispatcher.start()
        event_dispatcher.dispatch_event(test_event)
        
        # Allow time for event processing
        time.sleep(0.1)
        
        mock_handler.assert_called_once_with(test_event)
        event_dispatcher.stop()

    def test_priority_handling(self, event_dispatcher: EventDispatcher):
        """Test event priority handling."""
        processed_events = []
        
        def handler(event: MonitoringEvent):
            processed_events.append(event)
        
        event_dispatcher.register_handler(EventType.SYSTEM_ALERT, handler)
        event_dispatcher.start()
        
        # Dispatch events with different priorities
        events = [
            MonitoringEvent.create(
                EventType.SYSTEM_ALERT,
                priority,
                {"message": f"Test {priority.name}"},
                "test"
            )
            for priority in [
                EventPriority.LOW,
                EventPriority.CRITICAL,
                EventPriority.HIGH
            ]
        ]
        
        for event in events:
            event_dispatcher.dispatch_event(event)
        
        # Allow time for processing
        time.sleep(0.1)
        event_dispatcher.stop()
        
        # Verify critical events processed first
        assert processed_events[0].priority == EventPriority.CRITICAL
        assert processed_events[1].priority == EventPriority.HIGH

    def test_concurrent_dispatch(self, event_dispatcher: EventDispatcher):
        """Test concurrent event dispatching."""
        processed_count = 0
        process_lock = threading.Lock()
        
        def handler(event: MonitoringEvent):
            nonlocal processed_count
            with process_lock:
                processed_count += 1
        
        event_dispatcher.register_handler(EventType.SYSTEM_ALERT, handler)
        event_dispatcher.start()
        
        # Dispatch multiple events concurrently
        event_count = 10
        threads = []
        
        for _ in range(event_count):
            thread = threading.Thread(
                target=event_dispatcher.dispatch_event,
                args=(test_event,)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Allow time for processing
        time.sleep(0.1)
        event_dispatcher.stop()
        
        assert processed_count == event_count

class TestAlertHandler:
    """Test cases for AlertHandler functionality."""

    @pytest.fixture
    def alert_handler(self, test_config: Dict[str, Any]) -> AlertHandler:
        """Create alert handler instance."""
        return AlertHandler(test_config)

    def test_alert_logging(self, alert_handler: AlertHandler, test_event: MonitoringEvent):
        """Test alert logging functionality."""
        alert_handler.handle_alert(test_event)
        
        assert len(alert_handler.alert_history) == 1
        logged_alert = alert_handler.alert_history[0]
        
        assert logged_alert["id"] == test_event.id
        assert logged_alert["type"] == test_event.type.name
        assert logged_alert["priority"] == test_event.priority.name

    def test_priority_handling(self, alert_handler: AlertHandler):
        """Test different priority alert handling."""
        for priority in EventPriority:
            event = MonitoringEvent.create(
                EventType.SYSTEM_ALERT,
                priority,
                {"message": f"Test {priority.name}"},
                "test"
            )
            
            with patch.object(alert_handler.logger, 'critical') as mock_critical, \
                 patch.object(alert_handler.logger, 'error') as mock_error, \
                 patch.object(alert_handler.logger, 'warning') as mock_warning, \
                 patch.object(alert_handler.logger, 'info') as mock_info:
                
                alert_handler.handle_alert(event)
                
                if priority == EventPriority.CRITICAL:
                    mock_critical.assert_called_once()
                elif priority == EventPriority.HIGH:
                    mock_error.assert_called_once()
                elif priority == EventPriority.MEDIUM:
                    mock_warning.assert_called_once()
                else:
                    mock_info.assert_called_once()

    def test_alert_history(self, alert_handler: AlertHandler):
        """Test alert history management."""
        # Generate multiple alerts
        for i in range(3):
            event = MonitoringEvent.create(
                EventType.SYSTEM_ALERT,
                EventPriority.HIGH,
                {"message": f"Test alert {i}"},
                "test"
            )
            alert_handler.handle_alert(event)
        
        assert len(alert_handler.alert_history) == 3
        assert all(isinstance(alert["timestamp"], datetime) 
                  for alert in alert_handler.alert_history)

    def test_error_handling(self, alert_handler: AlertHandler):
        """Test error handling in alert processing."""
        # Create invalid event
        invalid_event = Mock(spec=MonitoringEvent)
        invalid_event.data = None  # This should cause an error
        
        # Should not raise exception
        alert_handler.handle_alert(invalid_event)

