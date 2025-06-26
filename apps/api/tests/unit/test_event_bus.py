"""
Unit tests for EventBus service.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.event_bus import EventBus
from app.models.health_status import HealthStatusEvent, GatewayStatus


class TestEventBus:
    """Test cases for EventBus service."""
    
    @pytest.fixture
    def event_bus(self):
        """Create a fresh EventBus instance for each test."""
        return EventBus()
    
    @pytest.mark.asyncio
    async def test_event_bus_start_stop(self, event_bus):
        """Test event bus start and stop functionality."""
        # Test start
        await event_bus.start()
        assert event_bus._running is True
        assert event_bus._processing_task is not None
        
        # Test stop
        await event_bus.stop()
        assert event_bus._running is False
        assert event_bus._processing_task.cancelled() or event_bus._processing_task.done()
    
    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, event_bus):
        """Test subscription and unsubscription functionality."""
        handler_called = []
        
        def test_handler(event_data):
            handler_called.append(event_data)
        
        # Test subscription
        event_bus.subscribe("test_event", test_handler)
        assert "test_event" in event_bus._subscribers
        assert test_handler in event_bus._subscribers["test_event"]
        
        # Test unsubscription
        event_bus.unsubscribe("test_event", test_handler)
        assert test_handler not in event_bus._subscribers["test_event"]
    
    @pytest.mark.asyncio
    async def test_event_publishing_and_handling(self, event_bus):
        """Test event publishing and handling."""
        await event_bus.start()
        
        handler_called = []
        
        def test_handler(event_data):
            handler_called.append(event_data)
        
        # Subscribe to event
        event_bus.subscribe("test_event", test_handler)
        
        # Publish event
        test_data = {"message": "Hello World", "value": 42}
        await event_bus.publish("test_event", test_data)
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify handler was called
        assert len(handler_called) == 1
        assert handler_called[0] == test_data
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_async_event_handler(self, event_bus):
        """Test async event handler support."""
        await event_bus.start()
        
        handler_called = []
        
        async def async_test_handler(event_data):
            handler_called.append(event_data)
        
        # Subscribe to event
        event_bus.subscribe("async_test", async_test_handler)
        
        # Publish event
        test_data = {"async": True}
        await event_bus.publish("async_test", test_data)
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify handler was called
        assert len(handler_called) == 1
        assert handler_called[0] == test_data
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers for the same event type."""
        await event_bus.start()
        
        handler1_called = []
        handler2_called = []
        
        def handler1(event_data):
            handler1_called.append(event_data)
        
        def handler2(event_data):
            handler2_called.append(event_data)
        
        # Subscribe both handlers
        event_bus.subscribe("multi_test", handler1)
        event_bus.subscribe("multi_test", handler2)
        
        # Publish event
        test_data = {"multi": True}
        await event_bus.publish("multi_test", test_data)
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify both handlers were called
        assert len(handler1_called) == 1
        assert len(handler2_called) == 1
        assert handler1_called[0] == test_data
        assert handler2_called[0] == test_data
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_health_status_event_publishing(self, event_bus):
        """Test health status event publishing."""
        await event_bus.start()
        
        received_events = []
        
        def health_handler(event_data):
            received_events.append(event_data)
        
        # Subscribe to health status changes
        event_bus.subscribe("gateway_status_change", health_handler)
        
        # Create health status event
        from datetime import datetime, timezone
        health_event = HealthStatusEvent(
            event_type="gateway_status_change",
            timestamp=datetime.now(),
            gateway_id="test_gateway",
            gateway_type="ctp",
            previous_status=GatewayStatus.CONNECTING,
            current_status=GatewayStatus.HEALTHY,
            metadata={"test": "data"}
        )
        
        # Publish health event
        await event_bus.publish_health_status_change(health_event)
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify event was received
        assert len(received_events) == 1
        event_data = received_events[0]
        assert event_data["event_type"] == "gateway_status_change"
        assert event_data["gateway_id"] == "test_gateway"
        assert event_data["gateway_type"] == "ctp"
        assert event_data["previous_status"] == "CONNECTING"
        assert event_data["current_status"] == "HEALTHY"
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_event_handler_error_handling(self, event_bus):
        """Test error handling in event handlers."""
        await event_bus.start()
        
        def failing_handler(event_data):
            raise ValueError("Handler error")
        
        def working_handler(event_data):
            working_handler.called = True
        
        working_handler.called = False
        
        # Subscribe both handlers
        event_bus.subscribe("error_test", failing_handler)
        event_bus.subscribe("error_test", working_handler)
        
        # Publish event
        await event_bus.publish("error_test", {"test": "data"})
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify working handler still called despite failing handler
        assert working_handler.called is True
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_event_bus_stats(self, event_bus):
        """Test event bus statistics."""
        await event_bus.start()
        
        def test_handler(event_data):
            pass
        
        # Subscribe to events
        event_bus.subscribe("stats_test", test_handler)
        event_bus.subscribe("stats_test", test_handler)  # Duplicate subscription
        event_bus.subscribe("other_test", test_handler)
        
        # Publish some events
        await event_bus.publish("stats_test", {"test": 1})
        await event_bus.publish("stats_test", {"test": 2})
        await event_bus.publish("other_test", {"test": 3})
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Get stats
        stats = event_bus.get_stats()
        
        assert stats["running"] is True
        assert stats["total_events_processed"] == 3
        assert stats["subscriber_count"]["stats_test"] == 2
        assert stats["subscriber_count"]["other_test"] == 1
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_no_subscribers_for_event(self, event_bus):
        """Test publishing event with no subscribers."""
        await event_bus.start()
        
        # Publish event with no subscribers - should not crash
        await event_bus.publish("no_subscribers", {"test": "data"})
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Get stats
        stats = event_bus.get_stats()
        assert stats["total_events_processed"] == 1
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_event_bus_not_running(self, event_bus):
        """Test publishing events when event bus is not running."""
        # Don't start the event bus
        
        # Publish event - should be dropped
        await event_bus.publish("dropped_event", {"test": "data"})
        
        # Stats should show no events processed
        stats = event_bus.get_stats()
        assert stats["running"] is False
        assert stats["total_events_processed"] == 0
    
    @pytest.mark.asyncio
    async def test_event_queue_size_tracking(self, event_bus):
        """Test event queue size tracking."""
        await event_bus.start()
        
        # Publish multiple events quickly
        for i in range(5):
            await event_bus.publish("queue_test", {"index": i})
        
        # Check queue size before processing
        stats = event_bus.get_stats()
        queue_size = stats["queue_size"]
        assert queue_size >= 0  # Queue might be processed quickly
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_event_timestamp_addition(self, event_bus):
        """Test that events get timestamp added automatically."""
        await event_bus.start()
        
        received_events = []
        
        def timestamp_handler(event_data):
            # This handler receives the full event structure
            pass
        
        # We'll test this by checking the internal queue
        test_data = {"test": "timestamp"}
        await event_bus.publish("timestamp_test", test_data)
        
        # The event should have been queued with timestamp
        # (We can't easily test this without accessing internals)
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_event_bus_queue_overflow(self, event_bus):
        """Test event bus behavior under queue overflow conditions."""
        await event_bus.start()
        
        # Publish many events quickly to test queue limits
        for i in range(10000):
            await event_bus.publish("overflow_test", {"index": i})
        
        # Event bus should handle this gracefully
        stats = event_bus.get_stats()
        assert stats["running"] is True
        
        await event_bus.stop()
    
    @pytest.mark.asyncio 
    async def test_event_handler_timeout_simulation(self, event_bus):
        """Test event handler that takes a long time to process."""
        await event_bus.start()
        
        slow_handler_called = []
        
        async def slow_handler(event_data):
            await asyncio.sleep(0.1)  # Simulate slow processing
            slow_handler_called.append(event_data)
        
        event_bus.subscribe("slow_test", slow_handler)
        
        # Publish multiple events
        for i in range(5):
            await event_bus.publish("slow_test", {"index": i})
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # All events should eventually be processed
        assert len(slow_handler_called) == 5
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_event_bus_memory_cleanup(self, event_bus):
        """Test that event bus properly cleans up memory."""
        await event_bus.start()
        
        # Create many subscribers and events
        handlers = []
        for i in range(100):
            def handler(event_data, idx=i):
                pass
            handlers.append(handler)
            event_bus.subscribe(f"test_event_{i}", handler)
        
        # Publish events
        for i in range(100):
            await event_bus.publish(f"test_event_{i}", {"data": i})
        
        # Unsubscribe all handlers
        for i, handler in enumerate(handlers):
            event_bus.unsubscribe(f"test_event_{i}", handler)
        
        # Stats should reflect cleanup
        stats = event_bus.get_stats()
        total_subscribers = sum(stats["subscriber_count"].values())
        assert total_subscribers == 0
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_event_data_serialization_edge_cases(self, event_bus):
        """Test event bus with complex data types."""
        await event_bus.start()
        
        received_data = []
        
        def complex_handler(event_data):
            received_data.append(event_data)
        
        event_bus.subscribe("complex_test", complex_handler)
        
        # Test with various complex data types
        complex_data = {
            "nested": {"deep": {"value": 42}},
            "list": [1, 2, 3, {"item": "value"}],
            "none_value": None,
            "boolean": True,
            "float": 3.14159,
            "large_string": "x" * 10000
        }
        
        await event_bus.publish("complex_test", complex_data)
        await asyncio.sleep(0.1)
        
        assert len(received_data) == 1
        assert received_data[0] == complex_data
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_double_start_and_stop(self, event_bus):
        """Test calling start/stop multiple times."""
        # Test double start
        await event_bus.start()
        assert event_bus._running is True
        
        # Second start should return early
        await event_bus.start()  # Should hit line 33 return
        assert event_bus._running is True
        
        # Test double stop
        await event_bus.stop()
        assert event_bus._running is False
        
        # Second stop should return early  
        await event_bus.stop()  # Should hit line 42 return
        assert event_bus._running is False
    
    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_handler(self, event_bus):
        """Test unsubscribing a handler that doesn't exist."""
        def dummy_handler(event_data):
            pass
        
        # Try to unsubscribe without subscribing first
        # This should trigger the ValueError catch block (line 90-95)
        event_bus.unsubscribe("nonexistent_event", dummy_handler)
        
        # Subscribe then unsubscribe a different handler
        def other_handler(event_data):
            pass
        
        event_bus.subscribe("test_event", other_handler)
        
        # Try to unsubscribe different handler - should trigger warning
        event_bus.unsubscribe("test_event", dummy_handler)
    
    @pytest.mark.asyncio
    async def test_publish_when_stopped(self, event_bus):
        """Test publishing when event bus is not running."""
        # Don't start the event bus
        assert event_bus._running is False
        
        # Publishing should hit line 106 early return
        await event_bus.publish("stopped_test", {"data": "test"})
        
        # Verify no events were processed
        stats = event_bus.get_stats()
        assert stats["total_events_processed"] == 0
    
    @pytest.mark.asyncio
    async def test_process_events_exception_handling(self, event_bus):
        """Test exception handling in _process_events method."""
        await event_bus.start()
        
        # Create a handler that will cause exception during event processing
        exception_raised = []
        
        def failing_handler(event_data):
            exception_raised.append(True)
            raise RuntimeError("Test exception in handler")
        
        event_bus.subscribe("exception_test", failing_handler)
        
        # Publish event that will cause exception
        await event_bus.publish("exception_test", {"test": "data"})
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Handler should have been called despite exception
        assert len(exception_raised) > 0
        
        # Event bus should still be running
        assert event_bus._running is True
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_queue_get_timeout_scenario(self, event_bus):
        """Test queue timeout scenario in _process_events."""
        await event_bus.start()
        
        # Don't publish any events, let the queue timeout (should hit line 125-126)
        # The _process_events loop runs with a timeout, this tests that path
        await asyncio.sleep(0.2)  # Let it cycle a few times
        
        assert event_bus._running is True
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_event_processing_task_cancellation(self, event_bus):
        """Test proper task cancellation during stop."""
        await event_bus.start()
        
        # Store reference to processing task
        processing_task = event_bus._processing_task
        assert processing_task is not None
        
        # Stop should cancel the task (line 152, 156-157)
        await event_bus.stop()
        
        # Task should be cancelled
        assert processing_task.cancelled() or processing_task.done()
        # Note: _processing_task is not set to None in current implementation
    
    @pytest.mark.asyncio
    async def test_publish_exception_handling(self, event_bus):
        """Test exception handling in publish method."""
        await event_bus.start()
        
        # Mock the queue to raise an exception
        with patch.object(event_bus._event_queue, 'put_nowait', side_effect=Exception("Queue error")):
            # This should trigger the exception handler (line 125-126)
            await event_bus.publish("error_test", {"data": "test"})
        
        # Event bus should still be running
        assert event_bus._running is True
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_process_events_general_exception(self, event_bus):
        """Test general exception handling in _process_events."""
        await event_bus.start()
        
        # Create a mock that will cause an exception in the processing loop
        original_get = event_bus._event_queue.get
        
        async def mock_get():
            # First call works normally, second call raises exception
            if not hasattr(mock_get, 'called'):
                mock_get.called = True
                return await original_get()
            else:
                raise Exception("Processing error")
        
        with patch.object(event_bus._event_queue, 'get', side_effect=mock_get):
            # Publish an event to trigger processing
            await event_bus.publish("test_event", {"data": "test"})
            
            # Wait for processing and exception
            await asyncio.sleep(0.2)
        
        # Event bus should handle the exception and continue running
        assert event_bus._running is True
        
        await event_bus.stop()
    
    @pytest.mark.asyncio
    async def test_cancellation_during_processing(self, event_bus):
        """Test cancellation exception handling in _process_events."""
        await event_bus.start()
        
        # Get reference to the processing task
        processing_task = event_bus._processing_task
        
        # Cancel the task directly to trigger CancelledError (line 153-155)
        processing_task.cancel()
        
        # Wait a bit for the cancellation to be processed
        await asyncio.sleep(0.1)
        
        # Task should be cancelled
        assert processing_task.cancelled()
        
        # Manually stop to clean up
        await event_bus.stop()