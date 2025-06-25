"""
Unit tests for Quote Aggregation Engine.
"""

import asyncio
import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.quote_aggregation_engine import (
    QuoteAggregationEngine,
    FailoverStatus,
    ContractSubscription,
    GatewayFailoverState,
    FailoverEvent
)


@pytest.fixture
def aggregation_engine():
    """Create a QuoteAggregationEngine instance for testing."""
    return QuoteAggregationEngine()


@pytest.fixture
def mock_database_service():
    """Mock database service."""
    with patch('app.services.quote_aggregation_engine.database_service') as mock:
        mock.is_available = AsyncMock(return_value=True)
        mock.get_all_accounts = AsyncMock(return_value=[
            MagicMock(id="ctp_main", gateway_type="ctp", priority=1),
            MagicMock(id="ctp_backup", gateway_type="ctp", priority=2),
            MagicMock(id="sopt_backup", gateway_type="sopt", priority=3)
        ])
        yield mock


@pytest.fixture
def mock_event_bus():
    """Mock event bus."""
    with patch('app.services.quote_aggregation_engine.event_bus') as mock:
        mock.subscribe = MagicMock()
        mock.unsubscribe = MagicMock()
        mock.publish = AsyncMock()
        yield mock


@pytest.fixture
def mock_gateway_manager():
    """Mock gateway manager."""
    with patch('app.services.quote_aggregation_engine.gateway_manager') as mock:
        mock.get_gateway_contracts.return_value = ["rb2501.SHFE", "au2502.SHFE"]
        mock.migrate_contracts = AsyncMock(return_value=True)
        yield mock


class TestQuoteAggregationEngine:
    """Test cases for QuoteAggregationEngine."""
    
    def test_initialization(self, aggregation_engine):
        """Test proper initialization of QuoteAggregationEngine."""
        assert aggregation_engine.failover_enabled is True
        assert aggregation_engine.failover_timeout_seconds == 5
        assert aggregation_engine.failover_cooldown_seconds == 30
        assert aggregation_engine.max_consecutive_failures == 3
        assert aggregation_engine._running is False
        assert len(aggregation_engine.gateway_states) == 0
        assert len(aggregation_engine.contract_subscriptions) == 0
    
    def test_environment_variable_configuration(self):
        """Test configuration from environment variables."""
        with patch.dict(os.environ, {
            'FAILOVER_ENABLED': 'false',
            'FAILOVER_TIMEOUT_SECONDS': '10',
            'FAILOVER_COOLDOWN_SECONDS': '60',
            'MAX_CONSECUTIVE_FAILURES': '5'
        }):
            engine = QuoteAggregationEngine()
            assert engine.failover_enabled is False
            assert engine.failover_timeout_seconds == 10
            assert engine.failover_cooldown_seconds == 60
            assert engine.max_consecutive_failures == 5
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, aggregation_engine, mock_database_service, mock_event_bus):
        """Test starting and stopping the aggregation engine."""
        # Test start
        await aggregation_engine.start()
        
        assert aggregation_engine._running is True
        assert aggregation_engine._subscription_active is True
        mock_event_bus.subscribe.assert_called_once_with(
            "gateway_status_change", 
            aggregation_engine._handle_health_status_change
        )
        
        # Test stop
        await aggregation_engine.stop()
        
        assert aggregation_engine._running is False
        assert aggregation_engine._subscription_active is False
        mock_event_bus.unsubscribe.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_gateway_states(self, aggregation_engine, mock_database_service):
        """Test initialization of gateway states from database."""
        await aggregation_engine._initialize_gateway_states()
        
        assert len(aggregation_engine.gateway_states) == 3
        assert "ctp_main" in aggregation_engine.gateway_states
        assert "ctp_backup" in aggregation_engine.gateway_states
        assert "sopt_backup" in aggregation_engine.gateway_states
        
        # Check priority ordering
        ctp_main_state = aggregation_engine.gateway_states["ctp_main"]
        assert ctp_main_state.priority == 1
        assert ctp_main_state.gateway_type == "ctp"
        assert ctp_main_state.is_healthy is True
    
    @pytest.mark.asyncio
    async def test_handle_health_status_change_unhealthy(self, aggregation_engine, mock_database_service, mock_event_bus):
        """Test handling of unhealthy gateway status change."""
        await aggregation_engine.start()
        
        # Trigger health status change event
        event_data = {
            "gateway_id": "ctp_main",
            "current_status": "UNHEALTHY",
            "health_check_type": "canary_timeout"
        }
        
        with patch.object(aggregation_engine, '_trigger_failover') as mock_trigger_failover:
            await aggregation_engine._handle_health_status_change(event_data)
            
            # Check that gateway state was updated
            gateway_state = aggregation_engine.gateway_states["ctp_main"]
            assert gateway_state.is_healthy is False
            assert gateway_state.consecutive_failures == 1
            
            # Check that failover was triggered
            mock_trigger_failover.assert_called_once_with("ctp_main", event_data)
    
    @pytest.mark.asyncio
    async def test_select_backup_gateway_same_type(self, aggregation_engine, mock_database_service):
        """Test backup gateway selection preferring same type."""
        await aggregation_engine._initialize_gateway_states()
        
        # Mark primary as unhealthy
        aggregation_engine.gateway_states["ctp_main"].is_healthy = False
        
        backup_id = await aggregation_engine._select_backup_gateway("ctp_main")
        
        # Should select ctp_backup (priority 2) over sopt_backup (priority 3)
        assert backup_id == "ctp_backup"
    
    @pytest.mark.asyncio
    async def test_select_backup_gateway_different_type(self, aggregation_engine, mock_database_service):
        """Test backup gateway selection with different type."""
        await aggregation_engine._initialize_gateway_states()
        
        # Mark both CTP gateways as unhealthy
        aggregation_engine.gateway_states["ctp_main"].is_healthy = False
        aggregation_engine.gateway_states["ctp_backup"].is_healthy = False
        
        backup_id = await aggregation_engine._select_backup_gateway("ctp_main")
        
        # Should select sopt_backup as the only healthy option
        assert backup_id == "sopt_backup"
    
    @pytest.mark.asyncio
    async def test_select_backup_gateway_no_healthy(self, aggregation_engine, mock_database_service):
        """Test backup gateway selection with no healthy gateways."""
        await aggregation_engine._initialize_gateway_states()
        
        # Mark all gateways as unhealthy
        for state in aggregation_engine.gateway_states.values():
            state.is_healthy = False
        
        backup_id = await aggregation_engine._select_backup_gateway("ctp_main")
        
        # Should return None when no healthy gateways available
        assert backup_id is None
    
    @pytest.mark.asyncio
    async def test_execute_failover_success(self, aggregation_engine, mock_database_service, mock_gateway_manager, mock_event_bus):
        """Test successful failover execution."""
        await aggregation_engine.start()
        
        # Setup initial state
        trigger_event = {"health_check_type": "canary_timeout"}
        
        with patch.object(aggregation_engine, '_select_backup_gateway', return_value="ctp_backup"):
            with patch.object(aggregation_engine, '_get_contracts_for_gateway', return_value=["rb2501.SHFE"]):
                await aggregation_engine._execute_failover("ctp_main", trigger_event)
        
        # Check that failover event was published
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == "failover_executed"
        
        # Check failover event data
        event_data = call_args[0][1]
        assert event_data["failed_gateway_id"] == "ctp_main"
        assert event_data["backup_gateway_id"] == "ctp_backup"
        assert event_data["affected_contracts"] == ["rb2501.SHFE"]
        assert "failover_duration_ms" in event_data
        
        # Check performance tracking
        assert aggregation_engine.total_failovers_executed == 1
        assert aggregation_engine.last_failover_time is not None
        assert len(aggregation_engine.failover_execution_times) == 1
    
    @pytest.mark.asyncio
    async def test_contract_migration(self, aggregation_engine, mock_gateway_manager):
        """Test contract migration functionality."""
        contracts = ["rb2501.SHFE", "au2502.SHFE"]
        
        await aggregation_engine._migrate_contracts("ctp_main", "ctp_backup", contracts)
        
        # Check that gateway manager was called for migration
        assert mock_gateway_manager.migrate_contracts.call_count == 2
        
        # Check individual contract calls
        calls = mock_gateway_manager.migrate_contracts.call_args_list
        assert calls[0][0] == ("ctp_main", "ctp_backup", ["rb2501.SHFE"])
        assert calls[1][0] == ("ctp_main", "ctp_backup", ["au2502.SHFE"])
    
    @pytest.mark.asyncio
    async def test_failover_cooldown_period(self, aggregation_engine, mock_database_service):
        """Test failover cooldown period enforcement."""
        await aggregation_engine.start()
        
        # Setup gateway with recent cooldown
        future_time = datetime.now(timezone.utc) + timedelta(minutes=1)
        aggregation_engine.gateway_states["ctp_main"].failover_cooldown_until = future_time
        
        trigger_event = {"health_check_type": "canary_timeout"}
        
        with patch.object(aggregation_engine, '_execute_failover') as mock_execute:
            await aggregation_engine._trigger_failover("ctp_main", trigger_event)
            
            # Should not execute failover due to cooldown
            mock_execute.assert_not_called()
            assert "ctp_main" not in aggregation_engine.active_failovers
    
    @pytest.mark.asyncio
    async def test_active_failover_prevention(self, aggregation_engine, mock_database_service):
        """Test prevention of multiple simultaneous failovers for same gateway."""
        await aggregation_engine.start()
        
        # Mark a failover as already in progress
        aggregation_engine.active_failovers["ctp_main"] = FailoverStatus.IN_PROGRESS
        
        trigger_event = {"health_check_type": "canary_timeout"}
        
        with patch.object(aggregation_engine, '_execute_failover') as mock_execute:
            await aggregation_engine._trigger_failover("ctp_main", trigger_event)
            
            # Should not execute another failover
            mock_execute.assert_not_called()
    
    def test_get_status(self, aggregation_engine):
        """Test status reporting functionality."""
        # Setup some state
        aggregation_engine._running = True
        aggregation_engine.total_failovers_executed = 5
        aggregation_engine.failover_execution_times = [100, 150, 120, 90, 110]
        
        # Add some gateway states
        aggregation_engine.gateway_states["ctp_main"] = GatewayFailoverState(
            gateway_id="ctp_main",
            gateway_type="ctp", 
            priority=1,
            is_healthy=True,
            last_health_check=datetime.now(timezone.utc)
        )
        aggregation_engine.gateway_states["ctp_backup"] = GatewayFailoverState(
            gateway_id="ctp_backup",
            gateway_type="ctp",
            priority=2, 
            is_healthy=False,
            last_health_check=datetime.now(timezone.utc)
        )
        
        status = aggregation_engine.get_status()
        
        assert status["running"] is True
        assert status["total_gateways"] == 2
        assert status["healthy_gateways"] == 1
        assert status["total_failovers_executed"] == 5
        assert status["average_failover_time_ms"] == 114.0  # (100+150+120+90+110)/5
        assert status["configuration"]["timeout_seconds"] == 5
        assert status["configuration"]["cooldown_seconds"] == 30
    
    @pytest.mark.asyncio
    async def test_cleanup_old_subscriptions(self, aggregation_engine):
        """Test cleanup of old inactive subscription records."""
        current_time = datetime.now(timezone.utc)
        old_time = current_time - timedelta(hours=2)
        
        # Add some old and new subscriptions
        aggregation_engine.contract_subscriptions["old:rb2501"] = ContractSubscription(
            symbol="rb2501.SHFE",
            gateway_id="old_gateway",
            subscribed_at=old_time,
            is_active=False
        )
        aggregation_engine.contract_subscriptions["new:rb2501"] = ContractSubscription(
            symbol="rb2501.SHFE", 
            gateway_id="new_gateway",
            subscribed_at=current_time,
            is_active=True
        )
        
        await aggregation_engine._cleanup_old_subscriptions()
        
        # Old inactive subscription should be removed
        assert "old:rb2501" not in aggregation_engine.contract_subscriptions
        # New active subscription should remain
        assert "new:rb2501" in aggregation_engine.contract_subscriptions
    
    def test_failover_event_serialization(self):
        """Test FailoverEvent serialization to dictionary."""
        event = FailoverEvent(
            failed_gateway_id="ctp_main",
            backup_gateway_id="ctp_backup", 
            affected_contracts=["rb2501.SHFE", "au2502.SHFE"],
            failover_duration_ms=150,
            metadata={
                "primary_priority": 1,
                "backup_priority": 2,
                "contracts_migrated": 2
            }
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == "failover_executed"
        assert event_dict["failed_gateway_id"] == "ctp_main"
        assert event_dict["backup_gateway_id"] == "ctp_backup"
        assert event_dict["affected_contracts"] == ["rb2501.SHFE", "au2502.SHFE"]
        assert event_dict["failover_duration_ms"] == 150
        assert event_dict["metadata"]["contracts_migrated"] == 2
        assert "timestamp" in event_dict
    
    def test_trim_performance_data(self, aggregation_engine):
        """Test trimming of performance data to prevent memory growth."""
        # Add more than 100 execution times
        aggregation_engine.failover_execution_times = list(range(150))
        
        aggregation_engine._trim_performance_data()
        
        # Should keep only last 100 entries
        assert len(aggregation_engine.failover_execution_times) == 100
        assert aggregation_engine.failover_execution_times == list(range(50, 150))
    
    @pytest.mark.asyncio
    async def test_failover_disabled_via_config(self, aggregation_engine, mock_database_service):
        """Test that failover is skipped when disabled via configuration."""
        aggregation_engine.failover_enabled = False
        await aggregation_engine.start()
        
        event_data = {
            "gateway_id": "ctp_main",
            "current_status": "UNHEALTHY"
        }
        
        with patch.object(aggregation_engine, '_trigger_failover') as mock_trigger:
            await aggregation_engine._handle_health_status_change(event_data)
            
            # Should not trigger failover when disabled
            mock_trigger.assert_not_called()