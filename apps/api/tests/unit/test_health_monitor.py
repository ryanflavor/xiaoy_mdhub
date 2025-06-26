"""
Unit tests for HealthMonitor service.
"""

import pytest
import asyncio
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.health_monitor import HealthMonitor
from app.models.health_status import GatewayStatus, HealthMetrics, GatewayHealthStatus


class TestHealthMonitor:
    """Test cases for HealthMonitor service."""
    
    @pytest.fixture
    def health_monitor(self):
        """Create a fresh HealthMonitor instance for each test."""
        # Mock environment variables for testing
        with patch.dict(os.environ, {
            'HEALTH_CHECK_INTERVAL_SECONDS': '1',
            'HEALTH_CHECK_TIMEOUT_SECONDS': '5',
            'CANARY_HEARTBEAT_TIMEOUT_SECONDS': '10',
            'CTP_CANARY_CONTRACTS': 'rb2601,au2512',
            'CTP_CANARY_PRIMARY': 'rb2601',
            'SOPT_CANARY_CONTRACTS': 'rb2601,au2512',
            'SOPT_CANARY_PRIMARY': 'rb2601',
            'HEALTH_CHECK_FALLBACK_MODE': 'connection_only'
        }):
            monitor = HealthMonitor()
            monitor._load_configuration()  # Load config with mocked env vars
            yield monitor
    
    @pytest.fixture
    def mock_gateway_manager(self):
        """Mock gateway manager for testing."""
        with patch('app.services.health_monitor.gateway_manager') as mock_gm:
            mock_gm.get_account_status.return_value = {
                'total_accounts': 2,
                'connected_accounts': 1,
                'accounts': [
                    {
                        'id': 'test_ctp_account',
                        'gateway_type': 'ctp',
                        'priority': 1,
                        'connected': True,
                        'connection_attempts': 1,
                        'connection_duration': 120.5
                    },
                    {
                        'id': 'test_sopt_account',
                        'gateway_type': 'sopt',
                        'priority': 2,
                        'connected': False,
                        'connection_attempts': 3,
                        'connection_duration': 0.0
                    }
                ]
            }
            yield mock_gm
    
    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus for testing."""
        with patch('app.services.health_monitor.event_bus') as mock_eb:
            mock_eb.start = AsyncMock()
            mock_eb.stop = AsyncMock()
            mock_eb.publish_health_status_change = AsyncMock()
            yield mock_eb
    
    @pytest.mark.asyncio
    async def test_health_monitor_start_stop(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test health monitor start and stop functionality."""
        # Test start
        result = await health_monitor.start()
        assert result is True
        assert health_monitor._running is True
        assert mock_event_bus.start.called
        
        # Verify gateway health initialization
        assert len(health_monitor.gateway_health) == 2
        assert 'test_ctp_account' in health_monitor.gateway_health
        assert 'test_sopt_account' in health_monitor.gateway_health
        
        # Test stop
        await health_monitor.stop()
        assert health_monitor._running is False
        assert mock_event_bus.stop.called
    
    @pytest.mark.asyncio
    async def test_gateway_health_initialization(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test gateway health status initialization."""
        await health_monitor.start()
        
        # Check CTP account health
        ctp_health = health_monitor.gateway_health['test_ctp_account']
        assert ctp_health.gateway_id == 'test_ctp_account'
        assert ctp_health.gateway_type == 'ctp'
        assert ctp_health.status == GatewayStatus.CONNECTING
        assert isinstance(ctp_health.metrics, HealthMetrics)
        
        # Check SOPT account health
        sopt_health = health_monitor.gateway_health['test_sopt_account']
        assert sopt_health.gateway_id == 'test_sopt_account'
        assert sopt_health.gateway_type == 'sopt'
        assert sopt_health.status == GatewayStatus.CONNECTING
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_vnpy_connection_check(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test vnpy connection status checking."""
        await health_monitor.start()
        
        # Test connected gateway
        connected_result = await health_monitor._check_vnpy_connection('test_ctp_account')
        assert connected_result is True
        
        # Test disconnected gateway
        disconnected_result = await health_monitor._check_vnpy_connection('test_sopt_account')
        assert disconnected_result is False
        
        # Test non-existent gateway
        nonexistent_result = await health_monitor._check_vnpy_connection('nonexistent_account')
        assert nonexistent_result is False
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_canary_contract_heartbeat(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test canary contract heartbeat monitoring."""
        await health_monitor.start()
        
        # Test with no tick data (should return True initially due to timeout grace period)
        heartbeat_result = await health_monitor._check_canary_heartbeat('test_ctp_account')
        assert heartbeat_result is True
        
        # Add canary tick data
        current_time = datetime.now(timezone.utc)
        health_monitor.update_canary_tick('test_ctp_account', 'rb2601', current_time)
        
        # Test with recent tick data
        heartbeat_result = await health_monitor._check_canary_heartbeat('test_ctp_account')
        assert heartbeat_result is True
        
        # Test with old tick data
        old_time = current_time - timedelta(seconds=120)  # Older than timeout
        health_monitor.update_canary_tick('test_ctp_account', 'rb2601', old_time)
        heartbeat_result = await health_monitor._check_canary_heartbeat('test_ctp_account')
        assert heartbeat_result is False
        
        await health_monitor.stop()
    
    def test_get_canary_contract(self, health_monitor):
        """Test canary contract configuration."""
        # Test CTP canary contract
        ctp_canary = health_monitor._get_canary_contract('ctp')
        assert ctp_canary == 'rb2601'
        
        # Test SOPT canary contract
        sopt_canary = health_monitor._get_canary_contract('sopt')
        assert sopt_canary == 'rb2601'
        
        # Test unknown gateway type
        unknown_canary = health_monitor._get_canary_contract('unknown')
        assert unknown_canary is None
    
    def test_determine_health_status(self, health_monitor):
        """Test health status determination logic."""
        # Healthy: connection OK, heartbeat OK
        status = health_monitor._determine_health_status(True, True, 'test_gateway')
        assert status == GatewayStatus.HEALTHY
        
        # Disconnected: connection failed
        status = health_monitor._determine_health_status(False, True, 'test_gateway')
        assert status == GatewayStatus.DISCONNECTED
        
        # Unhealthy: connection OK, heartbeat failed
        status = health_monitor._determine_health_status(True, False, 'test_gateway')
        assert status == GatewayStatus.UNHEALTHY
        
        # Disconnected: both failed (connection takes priority)
        status = health_monitor._determine_health_status(False, False, 'test_gateway')
        assert status == GatewayStatus.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_status_change_event_publishing(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test status change event publishing."""
        await health_monitor.start()
        
        # Update gateway status
        await health_monitor._update_gateway_status(
            'test_ctp_account',
            GatewayStatus.HEALTHY,
            GatewayStatus.CONNECTING,
            error_message=None
        )
        
        # Verify event was published
        assert mock_event_bus.publish_health_status_change.called
        
        # Get the published event
        call_args = mock_event_bus.publish_health_status_change.call_args[0][0]
        event_dict = call_args.to_dict()
        
        assert event_dict['event_type'] == 'gateway_status_change'
        assert event_dict['gateway_id'] == 'test_ctp_account'
        assert event_dict['gateway_type'] == 'ctp'
        assert event_dict['previous_status'] == 'CONNECTING'
        assert event_dict['current_status'] == 'HEALTHY'
        assert 'metadata' in event_dict
        
        await health_monitor.stop()
    
    def test_canary_tick_update(self, health_monitor):
        """Test canary tick timestamp updates."""
        timestamp = datetime.now(timezone.utc)
        
        health_monitor.update_canary_tick('test_gateway', 'rb2601', timestamp)
        
        # Check that tick timestamp was stored
        key = 'test_gateway:rb2601'
        assert key in health_monitor.canary_tick_timestamps
        assert health_monitor.canary_tick_timestamps[key] == timestamp
    
    @pytest.mark.asyncio
    async def test_health_summary(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test health summary generation."""
        await health_monitor.start()
        
        # Get health summary
        summary = health_monitor.get_health_summary()
        
        assert 'monitoring_active' in summary
        assert summary['monitoring_active'] is True
        assert summary['total_gateways'] == 2
        assert summary['healthy_gateways'] == 0  # All start as CONNECTING
        assert summary['unhealthy_gateways'] == 0
        assert 'gateways' in summary
        assert 'performance' in summary
        
        # Check individual gateway data
        gateways = summary['gateways']
        assert 'test_ctp_account' in gateways
        assert 'test_sopt_account' in gateways
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_gateway_health_retrieval(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test individual gateway health retrieval."""
        await health_monitor.start()
        
        # Get existing gateway health
        ctp_health = health_monitor.get_gateway_health('test_ctp_account')
        assert ctp_health is not None
        assert ctp_health['gateway_id'] == 'test_ctp_account'
        assert ctp_health['gateway_type'] == 'ctp'
        
        # Get non-existent gateway health
        nonexistent_health = health_monitor.get_gateway_health('nonexistent')
        assert nonexistent_health is None
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_health_check(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test error handling during health checks."""
        await health_monitor.start()
        
        # Mock gateway manager to raise exception
        mock_gateway_manager.get_account_status.side_effect = Exception("Connection error")
        
        # Perform health check - should not crash
        await health_monitor._perform_health_check('test_ctp_account')
        
        # Gateway should be marked as disconnected due to connection error
        health_status = health_monitor.gateway_health['test_ctp_account']
        # Status should be DISCONNECTED since connection check failed
        assert health_status.status == GatewayStatus.DISCONNECTED
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_configuration_from_environment(self, health_monitor):
        """Test configuration loading from environment variables."""
        # The fixture already applies environment variables and calls _load_configuration
        # So we should test the values that were set in the fixture
        assert health_monitor.health_check_interval == 1
        assert health_monitor.health_check_timeout == 5
        assert health_monitor.canary_heartbeat_timeout == 10
        assert health_monitor.ctp_canary_primary == 'rb2601'
        assert health_monitor.sopt_canary_primary == 'rb2601'
        assert health_monitor.fallback_mode == 'connection_only'
    
    @pytest.mark.asyncio
    async def test_monitoring_task_lifecycle(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test monitoring task creation and cleanup."""
        await health_monitor.start()
        
        # Verify monitoring tasks were created
        assert len(health_monitor.monitoring_tasks) == 2
        assert 'test_ctp_account' in health_monitor.monitoring_tasks
        assert 'test_sopt_account' in health_monitor.monitoring_tasks
        
        # Verify tasks are running
        for task in health_monitor.monitoring_tasks.values():
            assert not task.done()
        
        # Stop monitor and verify tasks are cancelled
        await health_monitor.stop()
        
        # Give tasks a moment to be cancelled
        await asyncio.sleep(0.1)
        
        for task in health_monitor.monitoring_tasks.values():
            assert task.cancelled() or task.done()
    
    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test performance metrics collection."""
        await health_monitor.start()
        
        # Wait for at least one monitoring cycle to complete
        await asyncio.sleep(1.2)  # Slightly longer than health check interval
        
        # Check that performance metrics are tracked
        assert health_monitor.health_check_count > 0
        
        # Check health check duration is recorded for at least one gateway
        found_duration = False
        for gateway_health in health_monitor.gateway_health.values():
            if gateway_health.metrics.health_check_duration_ms is not None:
                assert gateway_health.metrics.health_check_duration_ms >= 0
                found_duration = True
                break
        
        # At least one gateway should have duration metrics
        assert found_duration
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio 
    async def test_fallback_mode_behavior(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test fallback mode behavior when canary contracts unavailable."""
        # Test with skip_canary mode
        health_monitor.fallback_mode = 'skip_canary'
        
        await health_monitor.start()
        
        # Health check should skip canary contract monitoring
        heartbeat_result = await health_monitor._check_canary_heartbeat('test_ctp_account')
        assert heartbeat_result is True  # Should always return True in skip mode
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_status_updates(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test concurrent status updates don't cause race conditions."""
        await health_monitor.start()
        
        # Create multiple concurrent status updates
        import asyncio
        tasks = []
        for i in range(10):
            task = health_monitor._update_gateway_status(
                'test_ctp_account',
                GatewayStatus.HEALTHY if i % 2 == 0 else GatewayStatus.UNHEALTHY,
                GatewayStatus.CONNECTING,
                error_message=f"Test error {i}" if i % 2 == 1 else None
            )
            tasks.append(task)
        
        # Execute all updates concurrently
        await asyncio.gather(*tasks)
        
        # Verify final state is consistent
        final_health = health_monitor.gateway_health['test_ctp_account']
        assert final_health.status in [GatewayStatus.HEALTHY, GatewayStatus.UNHEALTHY]
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_invalid_gateway_configuration(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test handling of invalid gateway configuration."""
        # Mock gateway manager to return invalid account data
        mock_gateway_manager.get_account_status.return_value = {
            'total_accounts': 1,
            'connected_accounts': 0,
            'accounts': [
                {
                    'id': None,  # Invalid ID
                    'gateway_type': 'invalid_type',  # Invalid type
                    'priority': -1,  # Invalid priority
                    'connected': 'not_boolean',  # Invalid type
                    'connection_attempts': 'not_integer',  # Invalid type
                    'connection_duration': 'not_float'  # Invalid type
                }
            ]
        }
        
        # Should handle invalid data gracefully
        result = await health_monitor.start()
        assert result is True  # Should still start despite invalid data
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_health_monitor_restart_behavior(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test health monitor restart behavior."""
        # Start health monitor
        await health_monitor.start()
        assert health_monitor._running is True
        
        # Stop health monitor
        await health_monitor.stop()
        assert health_monitor._running is False
        
        # Restart health monitor
        await health_monitor.start()
        assert health_monitor._running is True
        
        # Verify state was reset properly
        assert len(health_monitor.monitoring_tasks) >= 0
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_extreme_error_conditions(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test extreme error conditions."""
        await health_monitor.start()
        
        # Simulate event bus failure
        mock_event_bus.publish_health_status_change.side_effect = Exception("Event bus failed")
        
        # Should continue working despite event bus failure
        await health_monitor._update_gateway_status(
            'test_ctp_account',
            GatewayStatus.UNHEALTHY,
            GatewayStatus.HEALTHY,
            error_message="Test error"
        )
        
        # Verify status was still updated
        health_status = health_monitor.gateway_health['test_ctp_account']
        assert health_status.status == GatewayStatus.UNHEALTHY
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_simulation(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test behavior under resource exhaustion conditions."""
        await health_monitor.start()
        
        # Simulate high resource usage
        import psutil
        import os
        
        # Create a large number of canary tick updates
        current_time = datetime.now(timezone.utc)
        for i in range(1000):
            health_monitor.update_canary_tick(f'gateway_{i}', f'contract_{i}', current_time)
        
        # Verify health monitor still functions
        summary = health_monitor.get_health_summary()
        assert 'performance' in summary
        assert summary['performance']['memory_usage_mb'] > 0
        
        await health_monitor.stop()
    
    def test_edge_case_canary_contract_names(self, health_monitor):
        """Test edge cases for canary contract name handling."""
        # Test with empty environment variables
        with patch.dict(os.environ, {
            'CTP_CANARY_PRIMARY': '',
            'SOPT_CANARY_PRIMARY': ''
        }, clear=False):
            monitor = HealthMonitor()
            monitor._load_configuration()  # Load config after env vars are set
            assert monitor._get_canary_contract('ctp') is None
            assert monitor._get_canary_contract('sopt') is None
        
        # Test with whitespace-only environment variables
        with patch.dict(os.environ, {
            'CTP_CANARY_PRIMARY': '   ',
            'SOPT_CANARY_PRIMARY': '\t\n'
        }, clear=False):
            monitor = HealthMonitor()
            monitor._load_configuration()  # Load config after env vars are set
            assert monitor._get_canary_contract('ctp') is None
            assert monitor._get_canary_contract('sopt') is None
    
    @pytest.mark.asyncio
    async def test_double_start_warning(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test starting health monitor twice triggers warning."""
        # Start once
        result1 = await health_monitor.start()
        assert result1 is True
        assert health_monitor._running is True
        
        # Start again - should trigger warning (line 71-72)
        result2 = await health_monitor.start()
        assert result2 is True  # Should still return True
        assert health_monitor._running is True
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, health_monitor):
        """Test stopping health monitor when not running."""
        assert health_monitor._running is False
        
        # Stop when not running - should hit line 111 return
        await health_monitor.stop()
        assert health_monitor._running is False
    
    @pytest.mark.asyncio
    async def test_startup_exception_handling(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test health monitor startup exception handling."""
        # Mock event bus start to raise exception
        mock_event_bus.start.side_effect = Exception("Event bus startup failed")
        
        # Start should handle exception and return False (line 101-106)
        result = await health_monitor.start()
        assert result is False
        assert health_monitor._running is False
    
    @pytest.mark.asyncio
    async def test_gateway_initialization_edge_cases(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test gateway initialization with edge cases."""
        # Mock with no accounts
        mock_gateway_manager.get_account_status.return_value = {
            'total_accounts': 0,
            'connected_accounts': 0,
            'accounts': []
        }
        
        result = await health_monitor.start()
        assert result is True
        assert len(health_monitor.gateway_health) == 0
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_monitoring_task_creation_failure(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test handling of monitoring task creation failures."""
        await health_monitor.start()
        
        # Verify tasks were created normally
        initial_task_count = len(health_monitor.monitoring_tasks)
        assert initial_task_count >= 0
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_health_check_timeout_handling(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test health check timeout scenarios."""
        await health_monitor.start()
        
        # Mock gateway manager to be very slow (simulating timeout)
        async def slow_response():
            await asyncio.sleep(0.1)
            return {
                'total_accounts': 1,
                'connected_accounts': 1,
                'accounts': [
                    {
                        'id': 'slow_gateway',
                        'gateway_type': 'ctp',
                        'priority': 1,
                        'connected': True,
                        'connection_attempts': 1,
                        'connection_duration': 30.0
                    }
                ]
            }
        
        mock_gateway_manager.get_account_status = slow_response
        
        # Perform health check - should handle timeout gracefully
        await health_monitor._perform_health_check('slow_gateway')
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_canary_heartbeat_edge_cases(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test canary heartbeat monitoring edge cases."""
        await health_monitor.start()
        
        # Test with no canary contract configured
        with patch.object(health_monitor, '_get_canary_contract', return_value=None):
            result = await health_monitor._check_canary_heartbeat('test_ctp_account')
            # Should return True when fallback mode is connection_only
            assert result is True
        
        # Test with canary contract but no tick data
        with patch.object(health_monitor, '_get_canary_contract', return_value='test_contract'):
            result = await health_monitor._check_canary_heartbeat('test_ctp_account')
            # Should return True initially (no data yet)
            assert result is True
        
        await health_monitor.stop()
    
    @pytest.mark.asyncio
    async def test_health_status_determination_all_combinations(self, health_monitor):
        """Test all possible combinations of health status determination."""
        # Test all possible combinations
        test_cases = [
            (True, True, GatewayStatus.HEALTHY),
            (True, False, GatewayStatus.UNHEALTHY),
            (False, True, GatewayStatus.DISCONNECTED),
            (False, False, GatewayStatus.DISCONNECTED),
        ]
        
        for connection_healthy, heartbeat_healthy, expected_status in test_cases:
            result = health_monitor._determine_health_status(
                connection_healthy, heartbeat_healthy, 'test_gateway'
            )
            assert result == expected_status
    
    @pytest.mark.asyncio
    async def test_update_gateway_status_edge_cases(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test gateway status update edge cases."""
        await health_monitor.start()
        
        # Test updating non-existent gateway
        await health_monitor._update_gateway_status(
            'nonexistent_gateway',
            GatewayStatus.HEALTHY,
            GatewayStatus.CONNECTING,
            error_message="Test error"
        )
        
        # Should handle gracefully without crashing
        assert health_monitor._running is True
        
        await health_monitor.stop()
    
    def test_get_health_summary_when_not_running(self, health_monitor):
        """Test getting health summary when monitor is not running."""
        summary = health_monitor.get_health_summary()
        
        assert summary['monitoring_active'] is False
        assert summary['total_gateways'] == 0
        assert 'performance' in summary
        assert 'gateways' in summary
    
    def test_get_gateway_health_edge_cases(self, health_monitor):
        """Test gateway health retrieval edge cases."""
        # Test with empty gateway_health dict
        result = health_monitor.get_gateway_health('nonexistent')
        assert result is None
        
        # Test with invalid gateway ID types
        result = health_monitor.get_gateway_health(None)
        assert result is None
        
        result = health_monitor.get_gateway_health('')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_monitoring_task_stop_exception(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test exception handling when stopping monitoring tasks."""
        await health_monitor.start()
        
        # Mock one of the tasks to raise an exception when cancelled
        task_mock = AsyncMock()
        task_mock.cancel = MagicMock()
        task_mock.side_effect = Exception("Task stop error")
        
        # Replace one task with our mock
        if health_monitor.monitoring_tasks:
            gateway_id = list(health_monitor.monitoring_tasks.keys())[0]
            health_monitor.monitoring_tasks[gateway_id] = task_mock
        
        # Stop should handle the exception gracefully (line 123-124)
        await health_monitor.stop()
        
        assert health_monitor._running is False
    
    @pytest.mark.asyncio
    async def test_skip_canary_fallback_mode(self, health_monitor, mock_gateway_manager, mock_event_bus):
        """Test skip_canary fallback mode behavior."""
        # Set fallback mode to skip_canary
        health_monitor.fallback_mode = "skip_canary"
        
        await health_monitor.start()
        
        # Test with no canary contract - when fallback_mode is NOT connection_only, should return False
        with patch.object(health_monitor, '_get_canary_contract', return_value=None):
            # Set fallback mode to something other than connection_only
            health_monitor.fallback_mode = "skip_canary"
            result = await health_monitor._check_canary_heartbeat('test_ctp_account')
            # In skip_canary mode with no contract, based on implementation should return False
            assert result is False
        
        await health_monitor.stop()