"""Comprehensive unit tests for WebSocket Manager.

This test suite covers all functionality of the WebSocketManager class including:
- Connection management (connect/disconnect)
- Message broadcasting and targeting
- Event handling and transformation
- Rate limiting and buffering
- Health monitoring and ping/pong
- Error handling and recovery
- Singleton pattern
- Event bus integration
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from collections import deque

from app.services.websocket_manager import WebSocketManager
from app.services.event_bus import event_bus


class MockWebSocket:
    """Enhanced mock WebSocket for comprehensive testing."""
    
    def __init__(self, should_fail: bool = False, fail_on_send: bool = False):
        self.send_json = AsyncMock()
        self.close = AsyncMock()
        self.messages_sent: List[Dict[str, Any]] = []
        self.closed = False
        self.should_fail = should_fail
        self.fail_on_send = fail_on_send
        
        # Configure behavior
        if fail_on_send:
            self.send_json.side_effect = Exception("Connection failed")
        else:
            self.send_json.side_effect = self._track_message
    
    def _track_message(self, message: Dict[str, Any]) -> None:
        """Track messages sent through this WebSocket."""
        if self.should_fail:
            raise Exception("WebSocket connection failed")
        self.messages_sent.append(message)
    
    async def mock_close(self):
        """Mock close method."""
        self.closed = True


@pytest.fixture
def websocket_manager():
    """Create a fresh WebSocket manager instance for each test."""
    # Reset singleton before creating new instance
    WebSocketManager.reset_instance()
    manager = WebSocketManager()
    yield manager
    # Reset singleton after test
    WebSocketManager.reset_instance()


@pytest.fixture
def mock_websocket():
    """Create a standard mock WebSocket connection."""
    return MockWebSocket()


@pytest.fixture
def failing_websocket():
    """Create a WebSocket that fails on operations."""
    return MockWebSocket(should_fail=True, fail_on_send=True)


class TestWebSocketManagerCore:
    """Test core WebSocket Manager functionality."""
    
    def test_singleton_pattern(self):
        """Test that WebSocketManager implements singleton pattern correctly."""
        # Reset to ensure clean state
        WebSocketManager.reset_instance()
        
        # Create multiple instances
        manager1 = WebSocketManager()
        manager2 = WebSocketManager()
        manager3 = WebSocketManager.get_instance()
        
        # All should be the same instance
        assert manager1 is manager2
        assert manager2 is manager3
        assert manager1 is manager3
        
        # Reset should clear instance
        WebSocketManager.reset_instance()
        manager4 = WebSocketManager()
        assert manager4 is not manager1
    
    def test_initialization(self, websocket_manager):
        """Test proper initialization of WebSocket manager."""
        assert isinstance(websocket_manager.active_connections, dict)
        assert isinstance(websocket_manager.connection_health, dict)
        assert len(websocket_manager.active_connections) == 0
        assert len(websocket_manager.connection_health) == 0
        assert websocket_manager._ping_interval == 30
        assert websocket_manager._ping_timeout == 10
        assert websocket_manager._rate_limit_max_events == 100
        assert isinstance(websocket_manager._event_buffer, deque)
        assert isinstance(websocket_manager._log_buffer, deque)


class TestConnectionManagement:
    """Test WebSocket connection management."""
    
    @pytest.mark.asyncio
    async def test_connect_single_client(self, websocket_manager, mock_websocket):
        """Test connecting a single client."""
        client_id = await websocket_manager.connect(mock_websocket)
        
        assert client_id is not None
        assert isinstance(client_id, str)
        assert client_id in websocket_manager.active_connections
        assert client_id in websocket_manager.connection_health
        assert websocket_manager.get_connection_count() == 1
        
        # Verify connection health tracking
        health_time = websocket_manager.connection_health[client_id]
        assert isinstance(health_time, datetime)
        assert health_time.tzinfo == timezone.utc
    
    @pytest.mark.asyncio
    async def test_connect_multiple_clients(self, websocket_manager):
        """Test connecting multiple clients."""
        websockets = [MockWebSocket() for _ in range(5)]
        client_ids = []
        
        # Connect all clients
        for ws in websockets:
            client_id = await websocket_manager.connect(ws)
            client_ids.append(client_id)
        
        assert len(client_ids) == 5
        assert len(set(client_ids)) == 5  # All unique
        assert websocket_manager.get_connection_count() == 5
        
        # Verify all are tracked
        for client_id in client_ids:
            assert client_id in websocket_manager.active_connections
            assert client_id in websocket_manager.connection_health
    
    @pytest.mark.asyncio
    async def test_disconnect_client(self, websocket_manager, mock_websocket):
        """Test disconnecting a client."""
        client_id = await websocket_manager.connect(mock_websocket)
        assert websocket_manager.get_connection_count() == 1
        
        await websocket_manager.disconnect(client_id)
        
        assert websocket_manager.get_connection_count() == 0
        assert client_id not in websocket_manager.active_connections
        assert client_id not in websocket_manager.connection_health
    
    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_client(self, websocket_manager):
        """Test disconnecting a client that doesn't exist."""
        fake_client_id = str(uuid.uuid4())
        
        # Should not raise exception
        await websocket_manager.disconnect(fake_client_id)
        assert websocket_manager.get_connection_count() == 0
    
    @pytest.mark.asyncio
    async def test_connection_info(self, websocket_manager):
        """Test getting connection information."""
        # No connections initially
        info = websocket_manager.get_connection_info()
        assert info == {}
        
        # Connect clients
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        client_id1 = await websocket_manager.connect(ws1)
        client_id2 = await websocket_manager.connect(ws2)
        
        # Get connection info
        info = websocket_manager.get_connection_info()
        assert len(info) == 2
        assert client_id1 in info
        assert client_id2 in info
        
        # Verify info structure
        for client_id, client_info in info.items():
            assert "connected_since" in client_info
            assert "last_seen" in client_info
            assert "seconds_since_last_seen" in client_info
            assert client_info["connected_since"] is not None
            assert client_info["last_seen"] is not None
            assert isinstance(client_info["seconds_since_last_seen"], float)


class TestMessageHandling:
    """Test message broadcasting and sending."""
    
    @pytest.mark.asyncio
    async def test_broadcast_to_single_client(self, websocket_manager, mock_websocket):
        """Test broadcasting to a single connected client."""
        client_id = await websocket_manager.connect(mock_websocket)
        
        test_message = {
            "event_type": "test_event",
            "data": "test_data",
            "number": 42
        }
        
        await websocket_manager.broadcast(test_message)
        
        assert len(mock_websocket.messages_sent) == 1
        sent_message = mock_websocket.messages_sent[0]
        assert sent_message["event_type"] == "test_event"
        assert sent_message["data"] == "test_data"
        assert sent_message["number"] == 42
        assert "timestamp" in sent_message  # Should be added automatically
    
    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self, websocket_manager):
        """Test broadcasting to multiple clients."""
        websockets = [MockWebSocket() for _ in range(3)]
        client_ids = []
        
        # Connect all clients
        for ws in websockets:
            client_id = await websocket_manager.connect(ws)
            client_ids.append(client_id)
        
        test_message = {"event_type": "broadcast_test", "message": "hello_all"}
        await websocket_manager.broadcast(test_message)
        
        # Verify all clients received the message
        for ws in websockets:
            assert len(ws.messages_sent) == 1
            assert ws.messages_sent[0]["event_type"] == "broadcast_test"
            assert ws.messages_sent[0]["message"] == "hello_all"
    
    @pytest.mark.asyncio
    async def test_broadcast_no_clients(self, websocket_manager):
        """Test broadcasting when no clients are connected."""
        test_message = {"event_type": "no_clients"}
        
        # Should not raise exception
        await websocket_manager.broadcast(test_message)
    
    @pytest.mark.asyncio
    async def test_send_to_specific_client(self, websocket_manager):
        """Test sending message to specific client."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        client_id1 = await websocket_manager.connect(ws1)
        client_id2 = await websocket_manager.connect(ws2)
        
        test_message = {"event_type": "specific", "target": "client_1"}
        success = await websocket_manager.send_to_client(client_id1, test_message)
        
        assert success is True
        assert len(ws1.messages_sent) == 1
        assert len(ws2.messages_sent) == 0
        assert ws1.messages_sent[0]["event_type"] == "specific"
    
    @pytest.mark.asyncio
    async def test_send_to_nonexistent_client(self, websocket_manager):
        """Test sending message to non-existent client."""
        fake_client_id = str(uuid.uuid4())
        test_message = {"event_type": "test"}
        
        success = await websocket_manager.send_to_client(fake_client_id, test_message)
        assert success is False
    
    @pytest.mark.asyncio
    async def test_timestamp_addition(self, websocket_manager, mock_websocket):
        """Test that timestamps are added to messages."""
        await websocket_manager.connect(mock_websocket)
        
        # Message without timestamp
        message_without_timestamp = {"event_type": "test"}
        await websocket_manager.broadcast(message_without_timestamp)
        
        sent_message = mock_websocket.messages_sent[0]
        assert "timestamp" in sent_message
        
        # Message with timestamp (should not be overwritten)
        custom_timestamp = "2023-01-01T00:00:00Z"
        message_with_timestamp = {"event_type": "test", "timestamp": custom_timestamp}
        await websocket_manager.broadcast(message_with_timestamp)
        
        sent_message = mock_websocket.messages_sent[1]
        assert sent_message["timestamp"] == custom_timestamp


class TestErrorHandling:
    """Test error handling and connection recovery."""
    
    @pytest.mark.asyncio
    async def test_broadcast_with_failing_connection(self, websocket_manager):
        """Test broadcasting when one connection fails."""
        good_ws = MockWebSocket()
        bad_ws = MockWebSocket(fail_on_send=True)
        
        good_client = await websocket_manager.connect(good_ws)
        bad_client = await websocket_manager.connect(bad_ws)
        
        assert websocket_manager.get_connection_count() == 2
        
        # Attempt broadcast
        await websocket_manager.broadcast({"event_type": "test"})
        
        # Good client should have received message
        assert len(good_ws.messages_sent) == 1
        
        # Bad client should be disconnected
        assert websocket_manager.get_connection_count() == 1
        assert bad_client not in websocket_manager.active_connections
    
    @pytest.mark.asyncio
    async def test_send_to_failing_client(self, websocket_manager, failing_websocket):
        """Test sending to a client that fails."""
        client_id = await websocket_manager.connect(failing_websocket)
        
        success = await websocket_manager.send_to_client(client_id, {"test": "message"})
        
        assert success is False
        assert websocket_manager.get_connection_count() == 0  # Should be disconnected


class TestEventBusIntegration:
    """Test event bus integration and event handling."""
    
    @pytest.mark.asyncio
    async def test_gateway_event_handling(self, websocket_manager, mock_websocket):
        """Test handling gateway status change events."""
        client_id = await websocket_manager.connect(mock_websocket)
        
        # Simulate gateway event
        gateway_event = {
            "gateway_id": "test_gateway",
            "gateway_type": "ctp",
            "previous_status": "HEALTHY",
            "current_status": "UNHEALTHY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {"reason": "connection_timeout"}
        }
        
        # Handle event directly
        await websocket_manager._handle_gateway_event(gateway_event)
        
        # Force flush events to send immediately
        await websocket_manager.force_flush_events()
        
        # Verify client received transformed event
        assert len(mock_websocket.messages_sent) == 1
        sent_message = mock_websocket.messages_sent[0]
        assert sent_message["event_type"] == "gateway_status_change"
        assert sent_message["gateway_id"] == "test_gateway"
        assert sent_message["gateway_type"] == "ctp"
        assert sent_message["previous_status"] == "HEALTHY"
        assert sent_message["current_status"] == "UNHEALTHY"
        assert "metadata" in sent_message
    
    @pytest.mark.asyncio
    async def test_recovery_event_handling(self, websocket_manager, mock_websocket):
        """Test handling gateway recovery events."""
        client_id = await websocket_manager.connect(mock_websocket)
        
        # Simulate recovery event
        recovery_event = {
            "gateway_id": "test_gateway",
            "status": "recovering",
            "attempt": 2,
            "message": "Attempting reconnection",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {"delay": 5000}
        }
        
        # Handle event directly
        await websocket_manager._handle_recovery_event(recovery_event)
        
        # Force flush events
        await websocket_manager.force_flush_events()
        
        # Verify client received transformed event
        assert len(mock_websocket.messages_sent) == 1
        sent_message = mock_websocket.messages_sent[0]
        assert sent_message["event_type"] == "gateway_recovery_status"
        assert sent_message["gateway_id"] == "test_gateway"
        assert sent_message["recovery_status"] == "recovering"
        assert sent_message["attempt"] == 2
        assert sent_message["message"] == "Attempting reconnection"
    
    @pytest.mark.asyncio
    async def test_log_event_publishing(self, websocket_manager, mock_websocket):
        """Test publishing system log events."""
        client_id = await websocket_manager.connect(mock_websocket)
        
        # Publish log event
        await websocket_manager.publish_log_event(
            level="ERROR",
            message="Test error occurred",
            source="test_component",
            metadata={"error_code": 500, "details": "Test error details"}
        )
        
        # Force flush events
        await websocket_manager.force_flush_events()
        
        # Verify log event was sent
        assert len(mock_websocket.messages_sent) == 1
        sent_message = mock_websocket.messages_sent[0]
        assert sent_message["event_type"] == "system_log"
        assert sent_message["level"] == "ERROR"
        assert sent_message["message"] == "Test error occurred"
        assert sent_message["source"] == "test_component"
        assert sent_message["metadata"]["error_code"] == 500
        
        # Verify log was added to buffer
        assert len(websocket_manager._log_buffer) == 1
        assert websocket_manager._log_buffer[0]["level"] == "ERROR"
    
    @pytest.mark.asyncio
    async def test_log_level_filtering(self, websocket_manager, mock_websocket):
        """Test that log events are filtered by level."""
        client_id = await websocket_manager.connect(mock_websocket)
        
        # Publish DEBUG log (should be filtered out)
        await websocket_manager.publish_log_event(
            level="DEBUG",
            message="Debug message",
            source="test"
        )
        
        # Publish INFO log (should be sent)
        await websocket_manager.publish_log_event(
            level="INFO",
            message="Info message",
            source="test"
        )
        
        await websocket_manager.force_flush_events()
        
        # Only INFO message should be sent
        assert len(mock_websocket.messages_sent) == 1
        assert mock_websocket.messages_sent[0]["level"] == "INFO"


class TestRateLimiting:
    """Test rate limiting and event buffering."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_buffer(self, websocket_manager, mock_websocket):
        """Test that events are buffered for rate limiting."""
        client_id = await websocket_manager.connect(mock_websocket)
        
        # Send many events quickly
        num_events = 50
        for i in range(num_events):
            await websocket_manager.publish_log_event(
                level="INFO",
                message=f"Message {i}",
                source="test"
            )
        
        # Events should be in buffer, not immediately sent
        assert len(websocket_manager._event_buffer) > 0
        
        # Force flush to send events
        await websocket_manager.force_flush_events()
        
        # Now messages should be sent
        assert len(mock_websocket.messages_sent) == num_events
    
    @pytest.mark.asyncio
    async def test_rate_limit_max_events(self, websocket_manager, mock_websocket):
        """Test that rate limiting respects max events per window."""
        client_id = await websocket_manager.connect(mock_websocket)
        
        # Send more events than the rate limit allows
        num_events = 150  # More than _rate_limit_max_events (100)
        for i in range(num_events):
            await websocket_manager.publish_log_event(
                level="INFO",
                message=f"Message {i}",
                source="test"
            )
        
        # Should trigger automatic flush due to buffer size
        # Wait a moment for async processing
        await asyncio.sleep(0.1)
        
        # Should have sent at most the rate limit
        assert len(mock_websocket.messages_sent) <= websocket_manager._rate_limit_max_events
    
    @pytest.mark.asyncio
    async def test_event_buffer_deque_maxlen(self, websocket_manager):
        """Test that event buffer respects maximum length."""
        # Add more events than the buffer can hold
        for i in range(1200):  # More than maxlen=1000
            await websocket_manager._rate_limited_broadcast({
                "event_type": "test",
                "data": f"event_{i}"
            })
        
        # Buffer should not exceed maximum length
        assert len(websocket_manager._event_buffer) <= 1000


class TestHealthMonitoring:
    """Test health monitoring and ping/pong functionality."""
    
    @pytest.mark.asyncio
    async def test_client_health_update(self, websocket_manager, mock_websocket):
        """Test updating client health timestamp."""
        client_id = await websocket_manager.connect(mock_websocket)
        original_health = websocket_manager.connection_health[client_id]
        
        # Wait a moment then update health
        await asyncio.sleep(0.01)
        websocket_manager.update_client_health(client_id)
        
        # Health timestamp should be updated
        updated_health = websocket_manager.connection_health[client_id]
        assert updated_health > original_health
    
    @pytest.mark.asyncio
    async def test_health_update_nonexistent_client(self, websocket_manager):
        """Test updating health for non-existent client."""
        fake_client_id = str(uuid.uuid4())
        
        # Should not raise exception
        websocket_manager.update_client_health(fake_client_id)


class TestEventFiltering:
    """Test event filtering functionality."""
    
    def test_gateway_event_filter(self, websocket_manager):
        """Test gateway event filtering."""
        # All gateway events should pass for now
        test_event = {"gateway_id": "test", "status": "HEALTHY"}
        assert websocket_manager._filter_gateway_event(test_event) is True
        
        empty_event = {}
        assert websocket_manager._filter_gateway_event(empty_event) is True
    
    def test_recovery_event_filter(self, websocket_manager):
        """Test recovery event filtering."""
        # All recovery events should pass for now
        test_event = {"gateway_id": "test", "status": "recovering"}
        assert websocket_manager._filter_recovery_event(test_event) is True
        
        empty_event = {}
        assert websocket_manager._filter_recovery_event(empty_event) is True
    
    def test_log_event_filter(self, websocket_manager):
        """Test log event filtering by level."""
        # Valid log levels should pass
        assert websocket_manager._filter_log_event({"level": "INFO"}) is True
        assert websocket_manager._filter_log_event({"level": "WARN"}) is True
        assert websocket_manager._filter_log_event({"level": "ERROR"}) is True
        
        # Invalid log levels should not pass
        assert websocket_manager._filter_log_event({"level": "DEBUG"}) is False
        assert websocket_manager._filter_log_event({"level": "TRACE"}) is False
        
        # Default level should pass
        assert websocket_manager._filter_log_event({}) is True  # Defaults to INFO


class TestShutdown:
    """Test graceful shutdown functionality."""
    
    @pytest.mark.asyncio
    async def test_shutdown_no_connections(self, websocket_manager):
        """Test shutdown with no active connections."""
        await websocket_manager.shutdown()
        assert websocket_manager.get_connection_count() == 0
    
    @pytest.mark.asyncio
    async def test_shutdown_with_connections(self, websocket_manager):
        """Test graceful shutdown with active connections."""
        # Connect multiple clients
        websockets = [MockWebSocket() for _ in range(3)]
        client_ids = []
        
        for ws in websockets:
            client_id = await websocket_manager.connect(ws)
            client_ids.append(client_id)
        
        assert websocket_manager.get_connection_count() == 3
        
        # Shutdown
        await websocket_manager.shutdown()
        
        # Verify shutdown messages were sent
        for ws in websockets:
            shutdown_messages = [
                msg for msg in ws.messages_sent 
                if msg.get("event_type") == "shutdown"
            ]
            assert len(shutdown_messages) == 1
            assert shutdown_messages[0]["message"] == "Server is shutting down"
        
        # Verify all connections are closed
        assert websocket_manager.get_connection_count() == 0
    
    @pytest.mark.asyncio
    async def test_shutdown_with_failing_connections(self, websocket_manager):
        """Test shutdown when some connections fail to close."""
        good_ws = MockWebSocket()
        bad_ws = MockWebSocket(fail_on_send=True)
        
        await websocket_manager.connect(good_ws)
        await websocket_manager.connect(bad_ws)
        
        # Shutdown should complete even with failing connections
        await websocket_manager.shutdown()
        
        assert websocket_manager.get_connection_count() == 0


class TestConcurrency:
    """Test concurrent operations and thread safety."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, websocket_manager):
        """Test connecting multiple clients concurrently."""
        websockets = [MockWebSocket() for _ in range(10)]
        
        # Connect all clients concurrently
        tasks = [websocket_manager.connect(ws) for ws in websockets]
        client_ids = await asyncio.gather(*tasks)
        
        assert len(client_ids) == 10
        assert len(set(client_ids)) == 10  # All unique
        assert websocket_manager.get_connection_count() == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_broadcasts(self, websocket_manager):
        """Test concurrent broadcasting."""
        # Connect multiple clients
        websockets = [MockWebSocket() for _ in range(5)]
        for ws in websockets:
            await websocket_manager.connect(ws)
        
        # Send multiple broadcasts concurrently
        tasks = [
            websocket_manager.broadcast({"event_type": "test", "id": i})
            for i in range(10)
        ]
        await asyncio.gather(*tasks)
        
        # Each client should have received all messages
        for ws in websockets:
            assert len(ws.messages_sent) == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_disconnect(self, websocket_manager):
        """Test concurrent disconnections."""
        # Connect multiple clients
        websockets = [MockWebSocket() for _ in range(10)]
        client_ids = []
        for ws in websockets:
            client_id = await websocket_manager.connect(ws)
            client_ids.append(client_id)
        
        # Disconnect all concurrently
        tasks = [websocket_manager.disconnect(client_id) for client_id in client_ids]
        await asyncio.gather(*tasks)
        
        assert websocket_manager.get_connection_count() == 0


@pytest.mark.asyncio
async def test_full_integration_scenario():
    """Integration test simulating real-world usage."""
    WebSocketManager.reset_instance()
    manager = WebSocketManager()
    
    try:
        # Simulate multiple clients connecting
        clients = [MockWebSocket() for _ in range(3)]
        client_ids = []
        
        for client in clients:
            client_id = await manager.connect(client)
            client_ids.append(client_id)
        
        # Simulate various events
        await manager.publish_log_event("INFO", "System started", "main")
        
        gateway_event = {
            "gateway_id": "main_ctp",
            "gateway_type": "ctp",
            "previous_status": "STARTING",
            "current_status": "HEALTHY"
        }
        await manager._handle_gateway_event(gateway_event)
        
        recovery_event = {
            "gateway_id": "backup_ctp",
            "status": "recovered",
            "attempt": 1,
            "message": "Recovery successful"
        }
        await manager._handle_recovery_event(recovery_event)
        
        # Force flush all events
        await manager.force_flush_events()
        
        # Verify all clients received events
        for client in clients:
            assert len(client.messages_sent) >= 3  # At least 3 events
        
        # Test client health updates
        for client_id in client_ids:
            manager.update_client_health(client_id)
        
        # Test connection info
        info = manager.get_connection_info()
        assert len(info) == 3
        
        # Test graceful shutdown
        await manager.shutdown()
        assert manager.get_connection_count() == 0
        
    finally:
        WebSocketManager.reset_instance()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])