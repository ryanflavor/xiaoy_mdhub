"""
Unit tests for Gateway Manager service with database integration.
Tests the new database-driven gateway initialization functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timezone

from app.services.gateway_manager import GatewayManager
from app.models.market_data_account import MarketDataAccount


class TestGatewayManager:
    """Test suite for Gateway Manager database integration."""
    
    @pytest.fixture
    def gateway_manager(self):
        """Create a fresh gateway manager instance for testing."""
        return GatewayManager()
    
    @pytest.fixture
    def mock_ctp_account(self):
        """Mock CTP account for testing."""
        return {
            'id': 'test_ctp_account',
            'gateway_type': 'ctp',
            'settings': {
                'userID': 'test_user',
                'password': 'test_pass',
                'brokerID': 'test_broker',
                'mdAddress': 'tcp://test:10131',
                'tdAddress': 'tcp://test:10130'
            },
            'priority': 1,
            'description': 'Test CTP Account'
        }
    
    @pytest.fixture
    def mock_sopt_account(self):
        """Mock SOPT account for testing."""
        return {
            'id': 'test_sopt_account',
            'gateway_type': 'sopt',
            'settings': {
                'username': 'test_user',
                'password': 'test_pass',
                'brokerID': 'test_broker',
                'tdAddress': 'tcp://test:20130',
                'mdAddress': 'tcp://test:20131'
            },
            'priority': 2,
            'description': 'Test SOPT Account'
        }
    
    @pytest.mark.asyncio
    async def test_load_accounts_from_database_success(self, gateway_manager, mock_ctp_account):
        """Test successful loading of accounts from database."""
        # Mock database service
        mock_db_account = MarketDataAccount(
            id=mock_ctp_account['id'],
            gateway_type=mock_ctp_account['gateway_type'],
            settings=mock_ctp_account['settings'],
            priority=mock_ctp_account['priority'],
            is_enabled=True,
            description=mock_ctp_account['description']
        )
        
        with patch('app.services.gateway_manager.database_service') as mock_db_service:
            mock_db_service.is_available = AsyncMock(return_value=True)
            mock_db_service.get_all_accounts = AsyncMock(return_value=[mock_db_account])
            
            accounts = await gateway_manager._load_accounts_from_database()
            
            assert len(accounts) == 1
            assert accounts[0]['id'] == mock_ctp_account['id']
            assert accounts[0]['gateway_type'] == 'ctp'
            assert gateway_manager.active_accounts == accounts
            mock_db_service.get_all_accounts.assert_called_once_with(enabled_only=True)
    
    @pytest.mark.asyncio
    async def test_load_accounts_database_unavailable(self, gateway_manager):
        """Test handling of database unavailable scenario."""
        with patch('app.services.gateway_manager.database_service') as mock_db_service:
            mock_db_service.is_available = AsyncMock(return_value=False)
            
            accounts = await gateway_manager._load_accounts_from_database()
            
            assert accounts == []
            assert gateway_manager.active_accounts == []
    
    @pytest.mark.asyncio
    async def test_load_accounts_database_error(self, gateway_manager):
        """Test handling of database error during account loading."""
        with patch('app.services.gateway_manager.database_service') as mock_db_service:
            mock_db_service.is_available = AsyncMock(return_value=True)
            mock_db_service.get_all_accounts = AsyncMock(side_effect=Exception("Database error"))
            
            accounts = await gateway_manager._load_accounts_from_database()
            
            assert accounts == []
            assert gateway_manager.active_accounts == []
    
    @pytest.mark.asyncio
    async def test_initialize_gateway_disabled(self, gateway_manager):
        """Test initialization when gateway is disabled via environment variable."""
        with patch.dict('os.environ', {'ENABLE_CTP_GATEWAY': 'false'}):
            gateway_manager._enable_gateway = False
            
            result = await gateway_manager.initialize()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_initialize_no_accounts(self, gateway_manager):
        """Test initialization when no enabled accounts are found."""
        with patch('app.services.gateway_manager.database_service') as mock_db_service:
            with patch('app.services.gateway_manager.zmq_publisher') as mock_zmq:
                mock_db_service.is_available = AsyncMock(return_value=True)
                mock_db_service.get_all_accounts = AsyncMock(return_value=[])
                mock_zmq.initialize = AsyncMock(return_value=True)
                
                result = await gateway_manager.initialize()
                
                assert result is True  # Not an error, just no accounts
    
    @pytest.mark.asyncio
    async def test_initialize_account_gateway_ctp_success(self, gateway_manager, mock_ctp_account):
        """Test successful CTP account gateway initialization."""
        with patch('app.services.gateway_manager.CTP_AVAILABLE', True):
            with patch('app.services.gateway_manager.EventEngine') as mock_event_engine:
                with patch('app.services.gateway_manager.MainEngine') as mock_main_engine:
                    mock_event_instance = Mock()
                    mock_main_instance = Mock()
                    mock_event_engine.return_value = mock_event_instance
                    mock_main_engine.return_value = mock_main_instance
                    
                    result = await gateway_manager._initialize_account_gateway(mock_ctp_account)
                    
                    assert result is True
                    assert mock_ctp_account['id'] in gateway_manager.event_engines
                    assert mock_ctp_account['id'] in gateway_manager.main_engines
                    assert mock_ctp_account['id'] in gateway_manager.connection_attempts
    
    @pytest.mark.asyncio
    async def test_initialize_account_gateway_sopt_success(self, gateway_manager, mock_sopt_account):
        """Test successful SOPT account gateway initialization."""
        with patch('app.services.gateway_manager.SOPT_AVAILABLE', True):
            with patch('app.services.gateway_manager.EventEngine') as mock_event_engine:
                with patch('app.services.gateway_manager.MainEngine') as mock_main_engine:
                    mock_event_instance = Mock()
                    mock_main_instance = Mock()
                    mock_event_engine.return_value = mock_event_instance
                    mock_main_engine.return_value = mock_main_instance
                    
                    result = await gateway_manager._initialize_account_gateway(mock_sopt_account)
                    
                    assert result is True
                    assert mock_sopt_account['id'] in gateway_manager.event_engines
                    assert mock_sopt_account['id'] in gateway_manager.main_engines
    
    @pytest.mark.asyncio
    async def test_initialize_account_gateway_mock_mode(self, gateway_manager, mock_ctp_account):
        """Test account gateway initialization in mock mode."""
        with patch('app.services.gateway_manager.CTP_AVAILABLE', False):
            with patch.dict('os.environ', {'ENABLE_CTP_MOCK': 'true'}):
                with patch.object(gateway_manager, '_initialize_mock_gateway') as mock_init:
                    mock_init.return_value = True
                    
                    result = await gateway_manager._initialize_account_gateway(mock_ctp_account)
                    
                    assert result is True
                    mock_init.assert_called_once_with(mock_ctp_account)
    
    @pytest.mark.asyncio
    async def test_initialize_account_gateway_unsupported_type(self, gateway_manager):
        """Test handling of unsupported gateway type."""
        unsupported_account = {
            'id': 'test_unsupported',
            'gateway_type': 'unsupported',
            'settings': {},
            'priority': 1,
            'description': 'Unsupported Gateway'
        }
        
        with patch('app.services.gateway_manager.CTP_AVAILABLE', True):
            result = await gateway_manager._initialize_account_gateway(unsupported_account)
            
            assert result is False
    
    def test_convert_to_sopt_settings(self, gateway_manager):
        """Test conversion of database settings to SOPT format."""
        db_settings = {
            'username': 'test_user',
            'password': 'test_pass',
            'brokerID': 'test_broker',
            'tdAddress': 'tcp://test:20130',
            'mdAddress': 'tcp://test:20131',
            'appID': 'test_app',
            'authCode': 'test_auth'
        }
        
        result = gateway_manager._convert_to_sopt_settings(db_settings)
        
        expected = {
            '用户名': 'test_user',
            '密码': 'test_pass',
            '经纪商代码': 'test_broker',
            '交易服务器': 'tcp://test:20130',
            '行情服务器': 'tcp://test:20131',
            '产品名称': 'test_app',
            '授权编码': 'test_auth'
        }
        
        assert result == expected
    
    def test_get_account_status(self, gateway_manager, mock_ctp_account, mock_sopt_account):
        """Test getting account status information."""
        gateway_manager.active_accounts = [mock_ctp_account, mock_sopt_account]
        gateway_manager.gateway_connections = {
            'test_ctp_account': True,
            'test_sopt_account': False
        }
        gateway_manager.connection_attempts = {
            'test_ctp_account': 1,
            'test_sopt_account': 2
        }
        gateway_manager.connection_start_times = {
            'test_ctp_account': datetime.now(timezone.utc),
            'test_sopt_account': datetime.now(timezone.utc)
        }
        
        status = gateway_manager.get_account_status()
        
        assert status['total_accounts'] == 2
        assert status['connected_accounts'] == 1
        assert len(status['accounts']) == 2
        
        ctp_status = next(acc for acc in status['accounts'] if acc['id'] == 'test_ctp_account')
        assert ctp_status['connected'] is True
        assert ctp_status['gateway_type'] == 'ctp'
        assert ctp_status['priority'] == 1
    
    def test_handle_connection_status_change(self, gateway_manager):
        """Test handling of connection status changes."""
        account_id = 'test_account'
        gateway_manager.gateway_connections[account_id] = False
        gateway_manager.connection_start_times[account_id] = datetime.now(timezone.utc)
        
        # Test successful connection
        gateway_manager._handle_connection_status_change('connected', account_id)
        assert gateway_manager.gateway_connections[account_id] is True
        
        # Test disconnection
        gateway_manager._handle_connection_status_change('disconnected', account_id)
        assert gateway_manager.gateway_connections[account_id] is False
    
    @pytest.mark.asyncio
    async def test_shutdown_graceful(self, gateway_manager):
        """Test graceful shutdown of gateway manager."""
        # Setup some mock engines
        mock_main_engine = Mock()
        mock_event_engine = Mock()
        
        gateway_manager.main_engines['test_account'] = mock_main_engine
        gateway_manager.event_engines['test_account'] = mock_event_engine
        gateway_manager.active_accounts = [{'id': 'test_account'}]
        
        with patch('app.services.gateway_manager.zmq_publisher') as mock_zmq:
            mock_zmq.shutdown = AsyncMock()
            
            await gateway_manager.shutdown()
            
            mock_main_engine.close.assert_called_once()
            mock_event_engine.stop.assert_called_once()
            mock_zmq.shutdown.assert_called_once()