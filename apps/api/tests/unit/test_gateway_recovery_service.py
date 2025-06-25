"""
Unit tests for Gateway Recovery Service.
Tests recovery logic, cooldown management, and process lifecycle.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.services.gateway_recovery_service import (
    GatewayRecoveryService, 
    GatewayRecoveryState, 
    RecoveryStatus
)


class TestGatewayRecoveryState:
    """Test GatewayRecoveryState functionality."""
    
    def test_recovery_state_initialization(self):
        """Test recovery state initialization."""
        state = GatewayRecoveryState("test_gateway", "ctp")
        
        assert state.gateway_id == "test_gateway"
        assert state.gateway_type == "ctp"
        assert state.status == RecoveryStatus.IDLE
        assert state.restart_attempt_count == 0
        assert state.last_restart_timestamp is None
        assert state.cooldown_start_time is None
        assert state.recovery_start_time is None
        assert state.last_error_message is None
        assert state.recovery_history == []
    
    def test_recovery_state_to_dict(self):
        """Test recovery state serialization."""
        state = GatewayRecoveryState("test_gateway", "ctp")
        state.status = RecoveryStatus.COOLING_DOWN
        state.restart_attempt_count = 2
        state.last_error_message = "Test error"
        
        state_dict = state.to_dict()
        
        assert state_dict["gateway_id"] == "test_gateway"
        assert state_dict["gateway_type"] == "ctp"
        assert state_dict["status"] == "cooling_down"
        assert state_dict["restart_attempt_count"] == 2
        assert state_dict["last_error_message"] == "Test error"


class TestGatewayRecoveryService:
    """Test GatewayRecoveryService functionality."""
    
    @pytest.fixture
    def recovery_service(self):
        """Create a recovery service instance with mocked dependencies."""
        with patch.dict('os.environ', {
            'RECOVERY_SERVICE_ENABLED': 'true',
            'RECOVERY_COOLDOWN_SECONDS': '10',
            'RECOVERY_TIMEOUT_SECONDS': '60',
            'RECOVERY_MAX_RETRY_ATTEMPTS': '3'
        }):
            service = GatewayRecoveryService()
            return service
    
    @pytest.fixture
    def mock_gateway_manager(self):
        """Mock gateway manager."""
        with patch('app.services.gateway_recovery_service.gateway_manager') as mock:
            mock.get_account_status.return_value = {
                'accounts': [
                    {'id': 'gateway1', 'gateway_type': 'ctp'},
                    {'id': 'gateway2', 'gateway_type': 'sopt'}
                ]
            }
            mock.terminate_gateway_process = AsyncMock(return_value=True)
            mock.restart_gateway_process = AsyncMock(return_value=True)
            yield mock
    
    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        with patch('app.services.gateway_recovery_service.event_bus') as mock:
            mock.subscribe = MagicMock()
            mock.unsubscribe = MagicMock()
            mock.publish = AsyncMock()
            yield mock
    
    @pytest.fixture
    def mock_health_monitor(self):
        """Mock health monitor."""
        with patch('app.services.gateway_recovery_service.health_monitor') as mock:
            mock.get_gateway_health.return_value = {"status": "HEALTHY"}
            yield mock
    
    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        with patch('app.services.gateway_recovery_service.database_service') as mock:
            mock_account = MagicMock()
            mock_account.settings = {"username": "test", "password": "test"}
            mock.get_account_by_id = AsyncMock(return_value=mock_account)
            yield mock
    
    @pytest.mark.asyncio
    async def test_service_initialization(
        self, 
        recovery_service, 
        mock_gateway_manager, 
        mock_event_bus
    ):
        """Test service initialization."""
        # Test start
        result = await recovery_service.start()
        
        assert result is True
        assert recovery_service._running is True
        assert len(recovery_service.recovery_states) == 2
        assert "gateway1" in recovery_service.recovery_states
        assert "gateway2" in recovery_service.recovery_states
        
        mock_event_bus.subscribe.assert_called_once()
        
        # Test stop
        await recovery_service.stop()
        
        assert recovery_service._running is False
        mock_event_bus.unsubscribe.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_service_disabled(self):
        """Test service when disabled via environment variable."""
        with patch.dict('os.environ', {'RECOVERY_SERVICE_ENABLED': 'false'}):
            service = GatewayRecoveryService()
            result = await service.start()
            
            assert result is False
            assert service._running is False
    
    @pytest.mark.asyncio
    async def test_health_status_change_handling(
        self, 
        recovery_service, 
        mock_gateway_manager, 
        mock_event_bus
    ):
        """Test health status change event handling."""
        await recovery_service.start()
        
        # Simulate UNHEALTHY status event
        event_data = {
            "gateway_id": "gateway1",
            "current_status": "UNHEALTHY",
            "previous_status": "HEALTHY"
        }
        
        # Mock the cooldown process
        with patch.object(recovery_service, '_start_cooldown_period') as mock_cooldown:
            await recovery_service._handle_health_status_change(event_data)
            mock_cooldown.assert_called_once_with("gateway1")
        
        await recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_recovery_trigger_logic(
        self, 
        recovery_service, 
        mock_gateway_manager, 
        mock_event_bus
    ):
        """Test recovery triggering logic."""
        await recovery_service.start()
        
        event_data = {
            "gateway_id": "gateway1",
            "current_status": "UNHEALTHY"
        }
        
        # Test normal trigger
        with patch.object(recovery_service, '_start_cooldown_period') as mock_cooldown:
            await recovery_service._trigger_recovery("gateway1", event_data)
            mock_cooldown.assert_called_once_with("gateway1")
        
        # Test max retry attempts exceeded
        recovery_state = recovery_service.recovery_states["gateway1"]
        recovery_state.restart_attempt_count = 5  # Exceeds max of 3
        
        with patch.object(recovery_service, '_start_cooldown_period') as mock_cooldown:
            await recovery_service._trigger_recovery("gateway1", event_data)
            mock_cooldown.assert_not_called()
            assert recovery_state.status == RecoveryStatus.PERMANENTLY_FAILED
        
        await recovery_service.stop()
    
    def test_cooldown_duration_calculation(self, recovery_service):
        """Test cooldown duration calculation with exponential backoff."""
        # Without exponential backoff
        recovery_service.exponential_backoff_enabled = False
        duration = recovery_service._get_cooldown_duration(0)
        assert duration == recovery_service.cooldown_duration_seconds
        
        duration = recovery_service._get_cooldown_duration(3)
        assert duration == recovery_service.cooldown_duration_seconds
        
        # With exponential backoff
        recovery_service.exponential_backoff_enabled = True
        recovery_service.exponential_backoff_factor = 2.0
        
        duration = recovery_service._get_cooldown_duration(0)
        assert duration == recovery_service.cooldown_duration_seconds
        
        duration = recovery_service._get_cooldown_duration(1)
        assert duration == recovery_service.cooldown_duration_seconds * 2
        
        duration = recovery_service._get_cooldown_duration(2)
        assert duration == recovery_service.cooldown_duration_seconds * 4
    
    @pytest.mark.asyncio
    async def test_recovery_process_execution(
        self, 
        recovery_service, 
        mock_gateway_manager, 
        mock_event_bus,
        mock_health_monitor,
        mock_database_service
    ):
        """Test complete recovery process execution."""
        await recovery_service.start()
        
        # Mock successful recovery
        mock_health_monitor.get_gateway_health.return_value = {"status": "HEALTHY"}
        
        # Test successful recovery
        await recovery_service._execute_recovery("gateway1")
        
        # Verify gateway manager calls
        mock_gateway_manager.terminate_gateway_process.assert_called_once_with("gateway1")
        mock_gateway_manager.restart_gateway_process.assert_called_once()
        
        # Verify state updates
        recovery_state = recovery_service.recovery_states["gateway1"]
        assert recovery_state.status == RecoveryStatus.IDLE  # Reset to idle after success
        assert recovery_state.restart_attempt_count == 0  # Reset after success
        assert len(recovery_state.recovery_history) == 1
        assert recovery_state.recovery_history[0]["result"] == "success"
        
        await recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_recovery_failure_handling(
        self, 
        recovery_service, 
        mock_gateway_manager, 
        mock_event_bus,
        mock_health_monitor,
        mock_database_service
    ):
        """Test recovery failure handling."""
        await recovery_service.start()
        
        # Mock gateway manager failure
        mock_gateway_manager.terminate_gateway_process.side_effect = Exception("Termination failed")
        
        # Start recovery process to increment attempt count
        await recovery_service._start_recovery_process("gateway1")
        
        # Wait for recovery task to complete
        if "gateway1" in recovery_service.recovery_tasks:
            await recovery_service.recovery_tasks["gateway1"]
        
        # Verify failure handling
        recovery_state = recovery_service.recovery_states["gateway1"]
        assert recovery_state.status == RecoveryStatus.IDLE  # Reset to idle after failure
        assert "Termination failed" in recovery_state.last_error_message
        assert len(recovery_state.recovery_history) == 1
        assert recovery_state.recovery_history[0]["result"] == "failed"
        assert recovery_state.restart_attempt_count == 1  # Attempt count should remain
        
        await recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_recovery_confirmation_timeout(
        self, 
        recovery_service, 
        mock_gateway_manager, 
        mock_event_bus,
        mock_health_monitor,
        mock_database_service
    ):
        """Test recovery confirmation timeout."""
        await recovery_service.start()
        
        # Mock unhealthy status (timeout scenario)
        mock_health_monitor.get_gateway_health.return_value = {"status": "UNHEALTHY"}
        
        # Reduce timeout for faster test
        recovery_service.recovery_timeout_seconds = 1
        
        result = await recovery_service._wait_for_recovery_confirmation("gateway1")
        
        assert result is False
        
        await recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_recovery_confirmation_success(
        self, 
        recovery_service, 
        mock_gateway_manager, 
        mock_event_bus,
        mock_health_monitor,
        mock_database_service
    ):
        """Test successful recovery confirmation."""
        await recovery_service.start()
        
        # Mock healthy status
        mock_health_monitor.get_gateway_health.return_value = {"status": "HEALTHY"}
        
        result = await recovery_service._wait_for_recovery_confirmation("gateway1")
        
        assert result is True
        
        await recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_event_publishing(
        self, 
        recovery_service, 
        mock_gateway_manager, 
        mock_event_bus
    ):
        """Test recovery event publishing."""
        await recovery_service.start()
        
        metadata = {"test": "data"}
        await recovery_service._publish_recovery_event("gateway1", "test_event", metadata)
        
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args[0]
        
        assert call_args[0] == "test_event"
        assert call_args[1]["gateway_id"] == "gateway1"
        assert call_args[1]["metadata"] == metadata
        
        await recovery_service.stop()
    
    def test_status_retrieval(self, recovery_service, mock_gateway_manager, mock_event_bus):
        """Test recovery status retrieval."""
        # Test overall status
        status = recovery_service.get_recovery_status()
        
        assert "service_running" in status
        assert "recovery_enabled" in status
        assert "total_gateways" in status
        assert "performance_metrics" in status
        assert "configuration" in status
        
        # Test gateway-specific status
        recovery_service.recovery_states["test_gateway"] = GatewayRecoveryState("test_gateway", "ctp")
        gateway_status = recovery_service.get_gateway_recovery_status("test_gateway")
        
        assert gateway_status is not None
        assert gateway_status["gateway_id"] == "test_gateway"
        assert gateway_status["gateway_type"] == "ctp"
        
        # Test non-existent gateway
        non_existent = recovery_service.get_gateway_recovery_status("non_existent")
        assert non_existent is None
    
    @pytest.mark.asyncio
    async def test_concurrent_recovery_operations(
        self, 
        recovery_service, 
        mock_gateway_manager, 
        mock_event_bus,
        mock_health_monitor,
        mock_database_service
    ):
        """Test concurrent recovery operations for multiple gateways."""
        await recovery_service.start()
        
        # Mock healthy status for both gateways
        mock_health_monitor.get_gateway_health.return_value = {"status": "HEALTHY"}
        
        # Start recovery for both gateways concurrently
        tasks = [
            recovery_service._execute_recovery("gateway1"),
            recovery_service._execute_recovery("gateway2")
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify both gateways were processed
        assert mock_gateway_manager.terminate_gateway_process.call_count == 2
        assert mock_gateway_manager.restart_gateway_process.call_count == 2
        
        # Verify both recovery states
        state1 = recovery_service.recovery_states["gateway1"]
        state2 = recovery_service.recovery_states["gateway2"]
        assert state1.status == RecoveryStatus.IDLE  # Reset to idle after success
        assert state2.status == RecoveryStatus.IDLE  # Reset to idle after success
        assert len(state1.recovery_history) == 1
        assert len(state2.recovery_history) == 1
        assert state1.recovery_history[0]["result"] == "success"
        assert state2.recovery_history[0]["result"] == "success"
        
        await recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_service_shutdown_during_recovery(
        self, 
        recovery_service, 
        mock_gateway_manager, 
        mock_event_bus
    ):
        """Test service shutdown while recovery is in progress."""
        await recovery_service.start()
        
        # Start a recovery task that will be cancelled
        recovery_task = asyncio.create_task(recovery_service._execute_recovery("gateway1"))
        recovery_service.recovery_tasks["gateway1"] = recovery_task
        
        # Stop the service (should cancel the task)
        await recovery_service.stop()
        
        # Verify task was cancelled
        assert recovery_task.cancelled()
        assert "gateway1" not in recovery_service.recovery_tasks
    
    @pytest.mark.asyncio
    async def test_gateway_settings_retrieval(
        self, 
        recovery_service, 
        mock_database_service
    ):
        """Test gateway settings retrieval from database."""
        # Test successful retrieval
        settings = await recovery_service._get_gateway_settings("gateway1")
        
        assert settings is not None
        assert "username" in settings
        assert "password" in settings
        
        # Test missing gateway
        mock_database_service.get_account_by_id.return_value = None
        settings = await recovery_service._get_gateway_settings("non_existent")
        
        assert settings is None
    
    @pytest.mark.asyncio
    async def test_recovery_history_tracking(
        self, 
        recovery_service, 
        mock_gateway_manager, 
        mock_event_bus,
        mock_health_monitor,
        mock_database_service
    ):
        """Test recovery history tracking."""
        await recovery_service.start()
        
        recovery_state = recovery_service.recovery_states["gateway1"]
        
        # Test successful recovery history
        mock_health_monitor.get_gateway_health.return_value = {"status": "HEALTHY"}
        await recovery_service._handle_recovery_success("gateway1")
        
        assert len(recovery_state.recovery_history) == 1
        assert recovery_state.recovery_history[0]["result"] == "success"
        assert "timestamp" in recovery_state.recovery_history[0]
        assert "duration_seconds" in recovery_state.recovery_history[0]
        
        # Test failed recovery history
        await recovery_service._handle_recovery_failure("gateway1", "Test failure")
        
        assert len(recovery_state.recovery_history) == 2
        assert recovery_state.recovery_history[1]["result"] == "failed"
        assert recovery_state.recovery_history[1]["error_message"] == "Test failure"
        
        await recovery_service.stop()


if __name__ == "__main__":
    pytest.main([__file__])