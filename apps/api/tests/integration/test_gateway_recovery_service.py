"""
Integration tests for Gateway Recovery Service.
Tests full recovery workflow with real service integration.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.services.gateway_recovery_service import gateway_recovery_service, RecoveryStatus
from app.services.event_bus import event_bus
from app.services.gateway_manager import gateway_manager
from app.services.health_monitor import health_monitor
from app.services.database_service import database_service


class TestGatewayRecoveryServiceIntegration:
    """Integration tests for Gateway Recovery Service."""
    
    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Ensure service is stopped before each test
        await gateway_recovery_service.stop()
        
        # Reset service state
        gateway_recovery_service.recovery_states.clear()
        gateway_recovery_service.recovery_tasks.clear()
        gateway_recovery_service.cooldown_tasks.clear()
        gateway_recovery_service._running = False
        gateway_recovery_service._event_subscription_active = False
        
        yield
        
        # Cleanup after each test
        await gateway_recovery_service.stop()
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        patches = [
            patch('app.services.gateway_recovery_service.gateway_manager'),
            patch('app.services.gateway_recovery_service.health_monitor'),
            patch('app.services.gateway_recovery_service.database_service'),
            patch('app.services.gateway_recovery_service.event_bus')
        ]
        
        mocks = {}
        for patch_obj in patches:
            mock_obj = patch_obj.start()
            module_name = patch_obj.attribute
            mocks[module_name] = mock_obj
        
        # Configure gateway manager mock
        mocks['gateway_manager'].get_account_status.return_value = {
            'accounts': [
                {'id': 'test_gateway_1', 'gateway_type': 'ctp'},
                {'id': 'test_gateway_2', 'gateway_type': 'sopt'}
            ]
        }
        mocks['gateway_manager'].terminate_gateway_process = AsyncMock(return_value=True)
        mocks['gateway_manager'].restart_gateway_process = AsyncMock(return_value=True)
        
        # Configure health monitor mock
        mocks['health_monitor'].get_gateway_health.return_value = {"status": "HEALTHY"}
        
        # Configure database service mock
        mock_account = MagicMock()
        mock_account.settings = {"username": "test", "password": "test"}
        mocks['database_service'].get_account_by_id = AsyncMock(return_value=mock_account)
        
        # Configure event bus mock
        mocks['event_bus'].subscribe = MagicMock()
        mocks['event_bus'].unsubscribe = MagicMock()
        mocks['event_bus'].publish = AsyncMock()
        
        yield mocks
        
        # Stop all patches
        for patch_obj in patches:
            patch_obj.stop()
    
    @pytest.mark.asyncio
    async def test_service_startup_and_shutdown(self, mock_dependencies):
        """Test complete service startup and shutdown cycle."""
        # Test startup
        with patch.dict('os.environ', {'RECOVERY_SERVICE_ENABLED': 'true'}):
            result = await gateway_recovery_service.start()
            
            assert result is True
            assert gateway_recovery_service._running is True
            assert len(gateway_recovery_service.recovery_states) == 2
            
            # Verify event subscription
            mock_dependencies['event_bus'].subscribe.assert_called_once()
            
            # Test shutdown
            await gateway_recovery_service.stop()
            
            assert gateway_recovery_service._running is False
            mock_dependencies['event_bus'].unsubscribe.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_service_disabled_by_environment(self):
        """Test service behavior when disabled via environment variable."""
        with patch.dict('os.environ', {'RECOVERY_SERVICE_ENABLED': 'false'}):
            result = await gateway_recovery_service.start()
            
            assert result is False
            assert gateway_recovery_service._running is False
    
    @pytest.mark.asyncio
    async def test_end_to_end_recovery_workflow(self, mock_dependencies):
        """Test complete end-to-end recovery workflow."""
        with patch.dict('os.environ', {
            'RECOVERY_SERVICE_ENABLED': 'true',
            'RECOVERY_COOLDOWN_SECONDS': '1',  # Short cooldown for test
            'RECOVERY_TIMEOUT_SECONDS': '5'   # Short timeout for test
        }):
            await gateway_recovery_service.start()
            
            # Simulate UNHEALTHY event
            event_data = {
                "gateway_id": "test_gateway_1",
                "current_status": "UNHEALTHY",
                "previous_status": "HEALTHY"
            }
            
            # Trigger recovery
            await gateway_recovery_service._handle_health_status_change(event_data)
            
            # Wait for cooldown to complete and recovery to start
            await asyncio.sleep(5)  # Wait for cooldown + processing + termination sleep
            
            # Verify recovery process was executed
            gateway_manager = mock_dependencies['gateway_manager']
            gateway_manager.terminate_gateway_process.assert_called_with("test_gateway_1")
            gateway_manager.restart_gateway_process.assert_called()
            
            # Verify recovery state
            recovery_state = gateway_recovery_service.recovery_states["test_gateway_1"]
            assert recovery_state.status == RecoveryStatus.IDLE  # Should be reset after successful recovery
            assert len(recovery_state.recovery_history) == 1  # Should have one successful recovery
            assert recovery_state.recovery_history[0]["result"] == "success"
            
            await gateway_recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_recovery_with_process_termination_failure(self, mock_dependencies):
        """Test recovery workflow when process termination fails."""
        with patch.dict('os.environ', {
            'RECOVERY_SERVICE_ENABLED': 'true',
            'RECOVERY_COOLDOWN_SECONDS': '1'
        }):
            await gateway_recovery_service.start()
            
            # Mock termination failure
            mock_dependencies['gateway_manager'].terminate_gateway_process.side_effect = Exception("Termination failed")
            
            # Execute recovery directly (bypass cooldown for test)
            await gateway_recovery_service._start_recovery_process("test_gateway_1")
            
            # Wait for the recovery task to complete
            await asyncio.sleep(1)  # Give the task time to fail and handle the error
            
            # Verify failure handling
            recovery_state = gateway_recovery_service.recovery_states["test_gateway_1"]
            assert recovery_state.status == RecoveryStatus.IDLE  # Status is reset to IDLE after failure for retry
            assert "Termination failed" in recovery_state.last_error_message
            assert len(recovery_state.recovery_history) == 1
            assert recovery_state.recovery_history[0]["result"] == "failed"
            assert "Termination failed" in recovery_state.recovery_history[0]["error_message"]
            
            await gateway_recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_recovery_with_restart_failure(self, mock_dependencies):
        """Test recovery workflow when process restart fails."""
        with patch.dict('os.environ', {
            'RECOVERY_SERVICE_ENABLED': 'true',
            'RECOVERY_COOLDOWN_SECONDS': '1'
        }):
            await gateway_recovery_service.start()
            
            # Mock restart failure
            mock_dependencies['gateway_manager'].restart_gateway_process.side_effect = Exception("Restart failed")
            
            # Execute recovery directly
            await gateway_recovery_service._start_recovery_process("test_gateway_1")
            
            # Wait for the recovery task to complete
            await asyncio.sleep(3)  # Give time for termination sleep + restart failure
            
            # Verify failure handling
            recovery_state = gateway_recovery_service.recovery_states["test_gateway_1"]
            assert recovery_state.status == RecoveryStatus.IDLE  # Status is reset to IDLE after failure for retry
            assert "Restart failed" in recovery_state.last_error_message
            assert len(recovery_state.recovery_history) == 1
            assert recovery_state.recovery_history[0]["result"] == "failed"
            assert "Restart failed" in recovery_state.recovery_history[0]["error_message"]
            
            await gateway_recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_recovery_with_health_confirmation_timeout(self, mock_dependencies):
        """Test recovery workflow when health confirmation times out."""
        with patch.dict('os.environ', {
            'RECOVERY_SERVICE_ENABLED': 'true',
            'RECOVERY_COOLDOWN_SECONDS': '1',
            'RECOVERY_TIMEOUT_SECONDS': '2'
        }):
            await gateway_recovery_service.start()
            
            # Mock unhealthy status (no recovery confirmation)
            mock_dependencies['health_monitor'].get_gateway_health.return_value = {"status": "UNHEALTHY"}
            
            # Execute recovery directly
            await gateway_recovery_service._start_recovery_process("test_gateway_1")
            
            # Wait for recovery task to complete (timeout is 2 seconds, plus termination sleep)
            await asyncio.sleep(8)  # Give time for termination (2s) + restart + timeout (2s) + failure handling
            
            # Verify timeout handling
            recovery_state = gateway_recovery_service.recovery_states["test_gateway_1"]
            assert recovery_state.status == RecoveryStatus.IDLE  # Status is reset to IDLE after failure for retry
            assert "Health confirmation timeout" in recovery_state.last_error_message
            assert len(recovery_state.recovery_history) == 1
            assert recovery_state.recovery_history[0]["result"] == "failed"
            assert "Health confirmation timeout" in recovery_state.recovery_history[0]["error_message"]
            
            await gateway_recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_recoveries(self, mock_dependencies):
        """Test multiple concurrent recovery operations."""
        with patch.dict('os.environ', {
            'RECOVERY_SERVICE_ENABLED': 'true',
            'RECOVERY_COOLDOWN_SECONDS': '1'
        }):
            await gateway_recovery_service.start()
            
            # Start concurrent recoveries
            await gateway_recovery_service._start_recovery_process("test_gateway_1")
            await gateway_recovery_service._start_recovery_process("test_gateway_2")
            
            # Wait for both recovery tasks to complete
            await asyncio.sleep(4)  # Give time for both recoveries to complete
            
            # Verify both gateways were processed
            gateway_manager = mock_dependencies['gateway_manager']
            assert gateway_manager.terminate_gateway_process.call_count == 2
            assert gateway_manager.restart_gateway_process.call_count == 2
            
            # Verify both recovery states
            state1 = gateway_recovery_service.recovery_states["test_gateway_1"]
            state2 = gateway_recovery_service.recovery_states["test_gateway_2"]
            
            # Status should be IDLE after successful recovery (reset for potential future recoveries)
            assert state1.status == RecoveryStatus.IDLE
            assert state2.status == RecoveryStatus.IDLE
            
            # Verify successful recovery in history
            assert len(state1.recovery_history) >= 1
            assert len(state2.recovery_history) >= 1
            
            # Check that the latest recovery was successful
            assert state1.recovery_history[-1]["result"] == "success"
            assert state2.recovery_history[-1]["result"] == "success"
            
            await gateway_recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_maximum_retry_attempts_enforcement(self, mock_dependencies):
        """Test maximum retry attempts enforcement."""
        with patch.dict('os.environ', {
            'RECOVERY_SERVICE_ENABLED': 'true',
            'RECOVERY_MAX_RETRY_ATTEMPTS': '2'
        }):
            await gateway_recovery_service.start()
            
            # Set gateway to have reached max attempts
            recovery_state = gateway_recovery_service.recovery_states["test_gateway_1"]
            recovery_state.restart_attempt_count = 2  # At max
            
            # Try to trigger recovery again
            event_data = {
                "gateway_id": "test_gateway_1",
                "current_status": "UNHEALTHY"
            }
            
            await gateway_recovery_service._trigger_recovery("test_gateway_1", event_data)
            
            # Verify permanently failed status
            assert recovery_state.status == RecoveryStatus.PERMANENTLY_FAILED
            assert "Maximum retry attempts exceeded" in recovery_state.last_error_message
            
            await gateway_recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_cooldown(self, mock_dependencies):
        """Test exponential backoff cooldown calculation."""
        with patch.dict('os.environ', {
            'RECOVERY_SERVICE_ENABLED': 'true',
            'RECOVERY_COOLDOWN_SECONDS': '5',
            'RECOVERY_EXPONENTIAL_BACKOFF': 'true',
            'RECOVERY_EXPONENTIAL_BACKOFF_FACTOR': '2.0'
        }):
            await gateway_recovery_service.start()
            
            # Test cooldown durations for different attempt counts
            duration_0 = gateway_recovery_service._get_cooldown_duration(0)
            duration_1 = gateway_recovery_service._get_cooldown_duration(1)
            duration_2 = gateway_recovery_service._get_cooldown_duration(2)
            
            assert duration_0 == 5  # Base duration
            assert duration_1 == 10  # 5 * 2^1
            assert duration_2 == 20  # 5 * 2^2
            
            await gateway_recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_event_publishing_integration(self, mock_dependencies):
        """Test event publishing during recovery workflow."""
        with patch.dict('os.environ', {
            'RECOVERY_SERVICE_ENABLED': 'true',
            'RECOVERY_COOLDOWN_SECONDS': '1'
        }):
            await gateway_recovery_service.start()
            
            # Execute recovery and verify events are published
            await gateway_recovery_service._start_recovery_process("test_gateway_1")
            await gateway_recovery_service._execute_recovery("test_gateway_1")
            
            # Verify event bus publish calls
            event_bus_mock = mock_dependencies['event_bus']
            assert event_bus_mock.publish.call_count >= 2  # At least started and completed events
            
            # Check event types
            call_args_list = event_bus_mock.publish.call_args_list
            event_types = [call[0][0] for call in call_args_list]
            
            assert "gateway_recovery_started" in event_types
            assert "gateway_recovery_completed" in event_types
            
            await gateway_recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_database_settings_retrieval_integration(self, mock_dependencies):
        """Test database settings retrieval during recovery."""
        with patch.dict('os.environ', {'RECOVERY_SERVICE_ENABLED': 'true'}):
            await gateway_recovery_service.start()
            
            # Test settings retrieval
            settings = await gateway_recovery_service._get_gateway_settings("test_gateway_1")
            
            assert settings is not None
            assert "username" in settings
            assert "password" in settings
            
            # Verify database service was called
            database_service_mock = mock_dependencies['database_service']
            database_service_mock.get_account_by_id.assert_called_with("test_gateway_1")
            
            await gateway_recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_recovery_status_reporting(self, mock_dependencies):
        """Test recovery status reporting functionality."""
        with patch.dict('os.environ', {'RECOVERY_SERVICE_ENABLED': 'true'}):
            await gateway_recovery_service.start()
            
            # Get overall status
            overall_status = gateway_recovery_service.get_recovery_status()
            
            assert overall_status["service_running"] is True
            assert overall_status["recovery_enabled"] is True
            assert overall_status["total_gateways"] == 2
            assert "performance_metrics" in overall_status
            assert "configuration" in overall_status
            assert "gateway_states" in overall_status
            
            # Get gateway-specific status
            gateway_status = gateway_recovery_service.get_gateway_recovery_status("test_gateway_1")
            
            assert gateway_status is not None
            assert gateway_status["gateway_id"] == "test_gateway_1"
            assert gateway_status["gateway_type"] == "ctp"
            assert gateway_status["status"] == "idle"
            
            await gateway_recovery_service.stop()
    
    @pytest.mark.asyncio
    async def test_service_graceful_shutdown_during_recovery(self, mock_dependencies):
        """Test graceful service shutdown while recovery is in progress."""
        with patch.dict('os.environ', {
            'RECOVERY_SERVICE_ENABLED': 'true',
            'RECOVERY_COOLDOWN_SECONDS': '10'  # Long cooldown to test shutdown
        }):
            await gateway_recovery_service.start()
            
            # Start a cooldown that won't complete before shutdown
            await gateway_recovery_service._start_cooldown_period("test_gateway_1")
            
            # Verify task is running
            assert "test_gateway_1" in gateway_recovery_service.cooldown_tasks
            
            # Shutdown service
            await gateway_recovery_service.stop()
            
            # Verify tasks were cancelled and cleaned up
            assert len(gateway_recovery_service.cooldown_tasks) == 0
            assert len(gateway_recovery_service.recovery_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_recovery_history_tracking_integration(self, mock_dependencies):
        """Test recovery history tracking through complete workflow."""
        with patch.dict('os.environ', {
            'RECOVERY_SERVICE_ENABLED': 'true',
            'RECOVERY_COOLDOWN_SECONDS': '1'
        }):
            await gateway_recovery_service.start()
            
            # Execute successful recovery
            await gateway_recovery_service._start_recovery_process("test_gateway_1")
            await gateway_recovery_service._execute_recovery("test_gateway_1")
            
            # Check recovery history
            recovery_state = gateway_recovery_service.recovery_states["test_gateway_1"]
            assert len(recovery_state.recovery_history) == 1
            
            history_entry = recovery_state.recovery_history[0]
            assert history_entry["result"] == "success"
            assert history_entry["attempt"] == 1
            assert "timestamp" in history_entry
            assert "duration_seconds" in history_entry
            
            # Simulate a failure
            mock_dependencies['gateway_manager'].terminate_gateway_process.side_effect = Exception("Test failure")
            
            await gateway_recovery_service._start_recovery_process("test_gateway_1")
            await gateway_recovery_service._execute_recovery("test_gateway_1")
            
            # Check updated history
            assert len(recovery_state.recovery_history) == 2
            
            failure_entry = recovery_state.recovery_history[1]
            assert failure_entry["result"] == "failed"
            assert failure_entry["error_message"] == "Test failure"
            
            await gateway_recovery_service.stop()


if __name__ == "__main__":
    pytest.main([__file__])