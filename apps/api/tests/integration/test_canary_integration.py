"""
Integration tests for canary functionality across gateway manager and health monitor.
Tests the full flow from tick reception to health status determination.
"""

import pytest
import asyncio
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import json

from app.services.health_monitor import HealthMonitor
from app.services.gateway_manager import GatewayManager
from app.services.websocket_manager import WebSocketManager


class MockTickData:
    """Mock tick data for testing."""
    def __init__(self, symbol="rb2601.SHFE", last_price=3800.0):
        self.symbol = symbol
        self.datetime = datetime.now()
        self.last_price = last_price
        self.volume = 1000
        self.last_volume = 10
        self.bid_price_1 = last_price - 1.0
        self.ask_price_1 = last_price + 1.0
        self.bid_volume_1 = 50
        self.ask_volume_1 = 50


class MockEvent:
    """Mock vnpy event."""
    def __init__(self, event_type, data):
        self.type = event_type
        self.data = data


@pytest.fixture(autouse=True)
def setup_environment():
    """Setup test environment variables."""
    # Set canary configuration
    os.environ["CTP_CANARY_CONTRACTS"] = "rb2601,au2512"
    os.environ["SOPT_CANARY_CONTRACTS"] = "510050,159915"
    os.environ["CANARY_HEARTBEAT_TIMEOUT_SECONDS"] = "30"
    
    yield
    
    # Cleanup environment
    for key in ["CTP_CANARY_CONTRACTS", "SOPT_CANARY_CONTRACTS", "CANARY_HEARTBEAT_TIMEOUT_SECONDS"]:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
async def health_monitor():
    """Create a health monitor instance for testing."""
    with patch('app.services.event_bus.event_bus') as mock_event_bus, \
         patch('app.services.gateway_manager.gateway_manager') as mock_gm_instance:
        
        mock_event_bus.start = AsyncMock()
        mock_event_bus.stop = AsyncMock()
        mock_event_bus.publish_health_status_change = AsyncMock()
        
        # Mock gateway manager to return test accounts
        mock_gm_instance.get_account_status.return_value = {
            'accounts': [
                {'id': 'test_ctp_01', 'gateway_type': 'ctp', 'is_enabled': True},
                {'id': 'test_sopt_01', 'gateway_type': 'sopt', 'is_enabled': True}
            ]
        }
        
        monitor = HealthMonitor()
        yield monitor
        
        # Cleanup
        if monitor._running:
            await monitor.stop()


@pytest.fixture
def gateway_manager():
    """Create a gateway manager instance for testing."""
    return GatewayManager()


@pytest.fixture
async def websocket_manager():
    """Create a websocket manager instance for testing."""
    with patch('app.services.websocket_manager.WebSocketManager.get_instance') as mock_ws_instance:
        manager = WebSocketManager()
        manager.broadcast = AsyncMock()
        mock_ws_instance.return_value = manager
        yield manager


class TestCanaryIntegration:
    """Integration tests for canary functionality."""
    
    @pytest.mark.asyncio
    async def test_canary_tick_processing_flow(self, health_monitor, gateway_manager, websocket_manager):
        """Test complete flow from tick reception to health status update."""
        
        # Start health monitor
        await health_monitor.start()
        
        # Setup gateway manager with test account
        gateway_manager.active_accounts = [
            {'id': 'test_ctp_01', 'gateway_type': 'ctp', 'is_enabled': True}
        ]
        
        # Simulate tick event for canary contract
        tick_data = MockTickData(symbol="rb2601.SHFE", last_price=3850.0)
        event = MockEvent("eTick", tick_data)
        
        # Process tick through gateway manager
        gateway_manager._on_tick_event(event, "test_ctp_01")
        
        # Verify health monitor was updated
        canary_status = health_monitor.get_canary_monitor_data()
        assert len(canary_status) > 0
        
        # Find rb2601 status
        rb2601_status = next((status for status in canary_status if status['contract_symbol'] == 'rb2601'), None)
        assert rb2601_status is not None
        assert rb2601_status['status'] == 'ACTIVE'
        assert rb2601_status['tick_count_1min'] >= 1
        
        # Verify WebSocket broadcast was called
        assert websocket_manager.broadcast.called
    
    @pytest.mark.asyncio
    async def test_canary_status_transitions(self, health_monitor, websocket_manager):
        """Test canary status transitions from ACTIVE to STALE to INACTIVE."""
        
        await health_monitor.start()
        
        current_time = datetime.now()
        
        # 1. Test ACTIVE status (recent tick)
        health_monitor.update_canary_tick("test_ctp_01", "rb2601", current_time)
        canary_data = health_monitor.get_canary_monitor_data()
        rb2601_data = next((d for d in canary_data if d['contract_symbol'] == 'rb2601'), None)
        assert rb2601_data['status'] == 'ACTIVE'
        
        # 2. Test STALE status (31 seconds old, within 2x timeout)
        stale_time = current_time - timedelta(seconds=31)
        health_monitor.update_canary_tick("test_ctp_01", "rb2601", stale_time)
        canary_data = health_monitor.get_canary_monitor_data()
        rb2601_data = next((d for d in canary_data if d['contract_symbol'] == 'rb2601'), None)
        assert rb2601_data['status'] == 'STALE'
        
        # 3. Test INACTIVE status (61 seconds old, beyond 2x timeout)
        inactive_time = current_time - timedelta(seconds=61)
        health_monitor.update_canary_tick("test_ctp_01", "rb2601", inactive_time)
        canary_data = health_monitor.get_canary_monitor_data()
        rb2601_data = next((d for d in canary_data if d['contract_symbol'] == 'rb2601'), None)
        assert rb2601_data['status'] == 'INACTIVE'
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_gateway_canary_aggregation(self, canary_test_setup):
        """Test canary data aggregation across multiple gateways."""
        setup = canary_test_setup
        health_monitor = setup['health_monitor']
        
        await health_monitor.start()
        
        current_time = datetime.now()
        
        # Update canary ticks from multiple gateways for same contract
        health_monitor.update_canary_tick("test_ctp_01", "rb2601", current_time)
        health_monitor.update_canary_tick("test_ctp_02", "rb2601", current_time - timedelta(seconds=5))
        
        canary_data = health_monitor.get_canary_monitor_data()
        rb2601_data = next((d for d in canary_data if d['contract_symbol'] == 'rb2601'), None)
        
        # Should use the latest timestamp and aggregate tick counts
        assert rb2601_data['status'] == 'ACTIVE'  # Latest tick is recent
        assert rb2601_data['tick_count_1min'] >= 2  # Counts from both gateways
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_canary_websocket_integration(self, canary_test_setup):
        """Test WebSocket broadcasting of canary updates."""
        setup = canary_test_setup
        health_monitor = setup['health_monitor']
        websocket_manager = setup['websocket_manager']
        
        await health_monitor.start()
        
        # Update canary tick
        current_time = datetime.now()
        health_monitor.update_canary_tick("test_ctp_01", "rb2601", current_time)
        
        # Give async task time to complete
        await asyncio.sleep(0.1)
        
        # Verify WebSocket broadcast was called
        assert websocket_manager.broadcast.called
        
        # Check the message format
        call_args = websocket_manager.broadcast.call_args[0][0]
        assert call_args['event_type'] == 'canary_tick_update'
        assert call_args['gateway_id'] == 'test_ctp_01'
        assert call_args['contract_symbol'] == 'rb2601'
        assert call_args['status'] == 'ACTIVE'
        assert 'tick_count_1min' in call_args
        assert 'threshold_seconds' in call_args
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_canary_contract_configuration(self, canary_test_setup):
        """Test canary contract configuration from environment variables."""
        setup = canary_test_setup
        health_monitor = setup['health_monitor']
        
        await health_monitor.start()
        
        # Verify CTP canary contracts
        assert 'rb2601' in health_monitor.ctp_canary_contracts
        assert 'au2512' in health_monitor.ctp_canary_contracts
        
        # Verify SOPT canary contracts
        assert '510050' in health_monitor.sopt_canary_contracts
        assert '159915' in health_monitor.sopt_canary_contracts
        
        # Verify timeout configuration
        assert health_monitor.canary_heartbeat_timeout == 30
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_canary_health_check_integration(self, canary_test_setup):
        """Test integration between canary monitoring and health check."""
        setup = canary_test_setup
        health_monitor = setup['health_monitor']
        
        await health_monitor.start()
        
        # No canary data initially - should return True (grace period)
        heartbeat_result = await health_monitor._check_canary_heartbeat('test_ctp_01')
        assert heartbeat_result is True
        
        # Add recent canary tick
        current_time = datetime.now()
        health_monitor.update_canary_tick("test_ctp_01", "rb2601", current_time)
        
        # Should still be healthy
        heartbeat_result = await health_monitor._check_canary_heartbeat('test_ctp_01')
        assert heartbeat_result is True
        
        # Add old canary tick
        old_time = current_time - timedelta(seconds=60)  # Beyond timeout
        health_monitor.update_canary_tick("test_ctp_01", "rb2601", old_time)
        
        # Should now be unhealthy
        heartbeat_result = await health_monitor._check_canary_heartbeat('test_ctp_01')
        assert heartbeat_result is False
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_canary_tick_validation_integration(self, canary_test_setup):
        """Test tick data validation in canary processing."""
        setup = canary_test_setup
        health_monitor = setup['health_monitor']
        
        await health_monitor.start()
        
        current_time = datetime.now()
        
        # Test valid tick data
        valid_tick = MockTickData(symbol="rb2601.SHFE", last_price=3800.0)
        health_monitor.update_canary_tick("test_ctp_01", "rb2601", current_time, valid_tick)
        
        canary_data = health_monitor.get_canary_monitor_data()
        rb2601_data = next((d for d in canary_data if d['contract_symbol'] == 'rb2601'), None)
        assert rb2601_data is not None
        assert rb2601_data['tick_count_1min'] >= 1
        
        # Test invalid tick data (zero price)
        invalid_tick = MockTickData(symbol="rb2601.SHFE", last_price=0.0)
        initial_count = rb2601_data['tick_count_1min']
        
        health_monitor.update_canary_tick("test_ctp_01", "rb2601", current_time + timedelta(seconds=1), invalid_tick)
        
        # Should not have increased tick count due to validation failure
        canary_data = health_monitor.get_canary_monitor_data()
        rb2601_data = next((d for d in canary_data if d['contract_symbol'] == 'rb2601'), None)
        assert rb2601_data['tick_count_1min'] == initial_count
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_canary_performance_under_load(self, canary_test_setup):
        """Test canary processing performance under load."""
        setup = canary_test_setup
        health_monitor = setup['health_monitor']
        
        await health_monitor.start()
        
        import time
        start_time = time.time()
        current_time = datetime.now()
        
        # Process 1000 canary ticks
        for i in range(1000):
            tick_time = current_time + timedelta(milliseconds=i)
            health_monitor.update_canary_tick("test_ctp_01", "rb2601", tick_time)
        
        processing_time = time.time() - start_time
        
        # Should process quickly (less than 1 second for 1000 ticks)
        assert processing_time < 1.0
        
        # Verify data consistency
        canary_data = health_monitor.get_canary_monitor_data()
        rb2601_data = next((d for d in canary_data if d['contract_symbol'] == 'rb2601'), None)
        assert rb2601_data is not None
        assert rb2601_data['status'] == 'ACTIVE'
        
        await health_monitor.stop()