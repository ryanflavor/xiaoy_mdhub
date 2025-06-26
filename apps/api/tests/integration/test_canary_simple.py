"""
Simple canary integration tests to verify basic functionality.
"""

import pytest
import asyncio
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.services.health_monitor import HealthMonitor


@pytest.fixture(autouse=True)
def setup_environment():
    """Setup test environment variables."""
    os.environ["CTP_CANARY_CONTRACTS"] = "rb2601,au2512"
    os.environ["SOPT_CANARY_CONTRACTS"] = "510050,159915"
    os.environ["CANARY_HEARTBEAT_TIMEOUT_SECONDS"] = "30"
    
    yield
    
    # Cleanup environment
    for key in ["CTP_CANARY_CONTRACTS", "SOPT_CANARY_CONTRACTS", "CANARY_HEARTBEAT_TIMEOUT_SECONDS"]:
        if key in os.environ:
            del os.environ[key]


class TestCanarySimpleIntegration:
    """Simple integration tests for canary functionality."""
    
    @pytest.mark.asyncio
    async def test_canary_basic_functionality(self):
        """Test basic canary functionality without complex setup."""
        
        with patch('app.services.event_bus.event_bus') as mock_event_bus, \
             patch('app.services.gateway_manager.gateway_manager') as mock_gm_instance:
            
            mock_event_bus.start = AsyncMock()
            mock_event_bus.stop = AsyncMock()
            mock_event_bus.publish_health_status_change = AsyncMock()
            
            # Mock gateway manager to return test accounts
            mock_gm_instance.get_account_status.return_value = {
                'accounts': [
                    {'id': 'test_ctp_01', 'gateway_type': 'ctp', 'is_enabled': True}
                ]
            }
            
            health_monitor = HealthMonitor()
            
            try:
                # Start health monitor
                await health_monitor.start()
                
                # Verify configuration loaded correctly
                assert 'rb2601' in health_monitor.ctp_canary_contracts
                assert 'au2512' in health_monitor.ctp_canary_contracts
                assert health_monitor.canary_heartbeat_timeout == 30
                
                # Test canary tick update
                current_time = datetime.now()
                health_monitor.update_canary_tick("test_ctp_01", "rb2601", current_time)
                
                # Verify canary data
                canary_data = health_monitor.get_canary_monitor_data()
                assert len(canary_data) > 0
                
                rb2601_data = next((d for d in canary_data if d['contract_symbol'] == 'rb2601'), None)
                assert rb2601_data is not None
                assert rb2601_data['status'] == 'ACTIVE'
                assert rb2601_data['tick_count_1min'] >= 1
                
                # Test status transitions
                old_time = current_time - timedelta(seconds=60)  # Beyond timeout
                health_monitor.update_canary_tick("test_ctp_01", "rb2601", old_time)
                
                canary_data = health_monitor.get_canary_monitor_data()
                rb2601_data = next((d for d in canary_data if d['contract_symbol'] == 'rb2601'), None)
                assert rb2601_data['status'] == 'INACTIVE'
                
            finally:
                # Cleanup
                if health_monitor._running:
                    await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_canary_health_check_integration(self):
        """Test canary integration with health check logic."""
        
        with patch('app.services.event_bus.event_bus') as mock_event_bus, \
             patch('app.services.gateway_manager.gateway_manager') as mock_gm_instance:
            
            mock_event_bus.start = AsyncMock()
            mock_event_bus.stop = AsyncMock()
            mock_event_bus.publish_health_status_change = AsyncMock()
            
            mock_gm_instance.get_account_status.return_value = {
                'accounts': [
                    {'id': 'test_ctp_01', 'gateway_type': 'ctp', 'is_enabled': True}
                ]
            }
            
            health_monitor = HealthMonitor()
            
            try:
                await health_monitor.start()
                
                # Manually initialize gateway health for test (since mock doesn't trigger it)
                from app.models.health_status import GatewayHealthStatus, HealthMetrics, GatewayStatus
                health_monitor.gateway_health['test_ctp_01'] = GatewayHealthStatus(
                    gateway_id='test_ctp_01',
                    gateway_type='ctp',
                    status=GatewayStatus.HEALTHY,
                    metrics=HealthMetrics(),
                    last_updated=datetime.now()
                )
                
                # Test healthy canary check
                current_time = datetime.now()
                health_monitor.update_canary_tick("test_ctp_01", "rb2601", current_time)
                
                heartbeat_result = await health_monitor._check_canary_heartbeat('test_ctp_01')
                assert heartbeat_result is True
                
                # Test unhealthy canary check
                old_time = current_time - timedelta(seconds=60)  # Beyond timeout
                health_monitor.update_canary_tick("test_ctp_01", "rb2601", old_time)
                
                heartbeat_result = await health_monitor._check_canary_heartbeat('test_ctp_01')
                assert heartbeat_result is False
                
            finally:
                if health_monitor._running:
                    await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_canary_websocket_publishing(self):
        """Test WebSocket publishing integration."""
        
        with patch('app.services.event_bus.event_bus') as mock_event_bus, \
             patch('app.services.gateway_manager.gateway_manager') as mock_gm_instance, \
             patch('app.services.websocket_manager.WebSocketManager.get_instance') as mock_ws_instance:
            
            mock_event_bus.start = AsyncMock()
            mock_event_bus.stop = AsyncMock()
            mock_event_bus.publish_health_status_change = AsyncMock()
            
            mock_gm_instance.get_account_status.return_value = {
                'accounts': [
                    {'id': 'test_ctp_01', 'gateway_type': 'ctp', 'is_enabled': True}
                ]
            }
            
            # Mock WebSocket manager
            mock_websocket_manager = Mock()
            mock_websocket_manager.publish_canary_tick_update = AsyncMock()
            mock_ws_instance.return_value = mock_websocket_manager
            
            health_monitor = HealthMonitor()
            
            try:
                await health_monitor.start()
                
                # Update canary tick - should trigger WebSocket publish
                current_time = datetime.now()
                health_monitor.update_canary_tick("test_ctp_01", "rb2601", current_time)
                
                # Give async task time to complete
                await asyncio.sleep(0.1)
                
                # Verify WebSocket publish was called
                assert mock_websocket_manager.publish_canary_tick_update.called
                
                # Check call arguments
                call_args = mock_websocket_manager.publish_canary_tick_update.call_args
                assert call_args[1]['gateway_id'] == 'test_ctp_01'
                assert call_args[1]['contract_symbol'] == 'rb2601'
                assert call_args[1]['status'] == 'ACTIVE'
                
            finally:
                if health_monitor._running:
                    await health_monitor.stop()