"""
Integration tests for service startup with database accounts.
Tests the complete database-to-gateway initialization flow.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, Mock
from fastapi.testclient import TestClient

from app.app import create_app
from app.services.gateway_manager import gateway_manager
from app.services.database_service import database_service
from app.models.market_data_account import MarketDataAccount


class TestServiceStartup:
    """Test suite for service startup behavior with various database states."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI app instance for testing."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_ctp_account(self):
        """Sample CTP account for testing."""
        return MarketDataAccount(
            id='integration_test_ctp',
            gateway_type='ctp',
            settings={
                'userID': 'test_user',
                'password': 'test_pass',
                'brokerID': 'test_broker',
                'mdAddress': 'tcp://test:10131',
                'tdAddress': 'tcp://test:10130'
            },
            priority=1,
            is_enabled=True,
            description='Integration Test CTP Account'
        )
    
    @pytest.fixture
    def sample_sopt_account(self):
        """Sample SOPT account for testing."""
        return MarketDataAccount(
            id='integration_test_sopt',
            gateway_type='sopt',
            settings={
                'username': 'test_user',
                'password': 'test_pass',
                'brokerID': 'test_broker',
                'tdAddress': 'tcp://test:20130',
                'mdAddress': 'tcp://test:20131'
            },
            priority=2,
            is_enabled=True,
            description='Integration Test SOPT Account'
        )
    
    @pytest.mark.asyncio
    async def test_startup_with_enabled_accounts(self, sample_ctp_account, sample_sopt_account):
        """Test service startup with enabled accounts in database."""
        with patch.object(database_service, 'is_available') as mock_db_available:
            with patch.object(database_service, 'get_all_accounts') as mock_get_accounts:
                with patch('app.services.gateway_manager.zmq_publisher.initialize') as mock_zmq_init:
                    with patch('app.services.gateway_manager.CTP_AVAILABLE', True):
                        with patch('app.services.gateway_manager.SOPT_AVAILABLE', True):
                            # Setup mocks
                            mock_db_available.return_value = True
                            mock_get_accounts.return_value = [sample_ctp_account, sample_sopt_account]
                            mock_zmq_init.return_value = True
                            
                            # Reset gateway manager state
                            gateway_manager.active_accounts = []
                            gateway_manager.main_engines = {}
                            gateway_manager.event_engines = {}
                            
                            # Mock the engine creation
                            with patch('app.services.gateway_manager.EventEngine') as mock_event_engine:
                                with patch('app.services.gateway_manager.MainEngine') as mock_main_engine:
                                    mock_event_instance = Mock()
                                    mock_main_instance = Mock()
                                    mock_event_engine.return_value = mock_event_instance
                                    mock_main_engine.return_value = mock_main_instance
                                    
                                    # Test initialization
                                    result = await gateway_manager.initialize()
                                    
                                    # Verify results
                                    assert result is True
                                    assert len(gateway_manager.active_accounts) == 2
                                    assert 'integration_test_ctp' in gateway_manager.main_engines
                                    assert 'integration_test_sopt' in gateway_manager.main_engines
                                    
                                    # Verify database was queried correctly
                                    mock_get_accounts.assert_called_once_with(enabled_only=True)
    
    @pytest.mark.asyncio
    async def test_startup_with_no_enabled_accounts(self):
        """Test service startup with no enabled accounts."""
        with patch.object(database_service, 'is_available') as mock_db_available:
            with patch.object(database_service, 'get_all_accounts') as mock_get_accounts:
                with patch('app.services.gateway_manager.zmq_publisher.initialize') as mock_zmq_init:
                    # Setup mocks
                    mock_db_available.return_value = True
                    mock_get_accounts.return_value = []
                    mock_zmq_init.return_value = True
                    
                    # Reset gateway manager state
                    gateway_manager.active_accounts = []
                    gateway_manager.main_engines = {}
                    gateway_manager.event_engines = {}
                    
                    # Test initialization
                    result = await gateway_manager.initialize()
                    
                    # Verify results
                    assert result is True  # Should succeed with no accounts
                    assert len(gateway_manager.active_accounts) == 0
                    assert len(gateway_manager.main_engines) == 0
    
    @pytest.mark.asyncio
    async def test_startup_with_database_unavailable(self):
        """Test service startup when database is unavailable."""
        with patch.object(database_service, 'is_available') as mock_db_available:
            with patch('app.services.gateway_manager.zmq_publisher.initialize') as mock_zmq_init:
                # Setup mocks
                mock_db_available.return_value = False
                mock_zmq_init.return_value = True
                
                # Reset gateway manager state
                gateway_manager.active_accounts = []
                gateway_manager.main_engines = {}
                gateway_manager.event_engines = {}
                
                # Test initialization
                result = await gateway_manager.initialize()
                
                # Verify results
                assert result is True  # Should succeed with no accounts loaded
                assert len(gateway_manager.active_accounts) == 0
    
    @pytest.mark.asyncio
    async def test_startup_with_database_error(self):
        """Test service startup with database connection errors."""
        with patch.object(database_service, 'is_available') as mock_db_available:
            with patch.object(database_service, 'get_all_accounts') as mock_get_accounts:
                with patch('app.services.gateway_manager.zmq_publisher.initialize') as mock_zmq_init:
                    # Setup mocks
                    mock_db_available.return_value = True
                    mock_get_accounts.side_effect = Exception("Database connection failed")
                    mock_zmq_init.return_value = True
                    
                    # Reset gateway manager state
                    gateway_manager.active_accounts = []
                    gateway_manager.main_engines = {}
                    gateway_manager.event_engines = {}
                    
                    # Test initialization
                    result = await gateway_manager.initialize()
                    
                    # Verify results - should succeed with no accounts loaded
                    assert result is True
                    assert len(gateway_manager.active_accounts) == 0
    
    @pytest.mark.asyncio
    async def test_startup_with_gateway_initialization_failures(self, sample_ctp_account):
        """Test service startup when individual gateway initialization fails."""
        with patch.object(database_service, 'is_available') as mock_db_available:
            with patch.object(database_service, 'get_all_accounts') as mock_get_accounts:
                with patch('app.services.gateway_manager.zmq_publisher.initialize') as mock_zmq_init:
                    with patch('app.services.gateway_manager.CTP_AVAILABLE', True):
                        # Setup mocks
                        mock_db_available.return_value = True
                        mock_get_accounts.return_value = [sample_ctp_account]
                        mock_zmq_init.return_value = True
                        
                        # Reset gateway manager state
                        gateway_manager.active_accounts = []
                        gateway_manager.main_engines = {}
                        gateway_manager.event_engines = {}
                        
                        # Mock engine creation to fail
                        with patch('app.services.gateway_manager.EventEngine') as mock_event_engine:
                            mock_event_engine.side_effect = Exception("Engine creation failed")
                            
                            # Test initialization
                            result = await gateway_manager.initialize()
                            
                            # Verify results - should handle failure gracefully
                            assert result is False  # No successful initializations
                            assert len(gateway_manager.active_accounts) == 1  # Accounts loaded
    
    @pytest.mark.asyncio
    async def test_startup_with_zmq_publisher_failure(self, sample_ctp_account):
        """Test service startup when ZMQ publisher initialization fails."""
        with patch.object(database_service, 'is_available') as mock_db_available:
            with patch.object(database_service, 'get_all_accounts') as mock_get_accounts:
                with patch('app.services.gateway_manager.zmq_publisher.initialize') as mock_zmq_init:
                    with patch('app.services.gateway_manager.CTP_AVAILABLE', True):
                        # Setup mocks
                        mock_db_available.return_value = True
                        mock_get_accounts.return_value = [sample_ctp_account]
                        mock_zmq_init.return_value = False  # ZMQ fails
                        
                        # Reset gateway manager state
                        gateway_manager.active_accounts = []
                        gateway_manager.main_engines = {}
                        gateway_manager.event_engines = {}
                        
                        # Mock the engine creation
                        with patch('app.services.gateway_manager.EventEngine') as mock_event_engine:
                            with patch('app.services.gateway_manager.MainEngine') as mock_main_engine:
                                mock_event_instance = Mock()
                                mock_main_instance = Mock()
                                mock_event_engine.return_value = mock_event_instance
                                mock_main_engine.return_value = mock_main_instance
                                
                                # Test initialization
                                result = await gateway_manager.initialize()
                                
                                # Verify results - should succeed despite ZMQ failure
                                assert result is True
                                assert len(gateway_manager.active_accounts) == 1
    
    @pytest.mark.asyncio
    async def test_startup_priority_ordering(self):
        """Test that accounts are loaded and initialized by priority order."""
        high_priority_account = MarketDataAccount(
            id='high_priority',
            gateway_type='ctp',
            settings={'userID': 'high'},
            priority=1,
            is_enabled=True
        )
        
        low_priority_account = MarketDataAccount(
            id='low_priority',
            gateway_type='ctp',
            settings={'userID': 'low'},
            priority=5,
            is_enabled=True
        )
        
        with patch.object(database_service, 'is_available') as mock_db_available:
            with patch.object(database_service, 'get_all_accounts') as mock_get_accounts:
                with patch('app.services.gateway_manager.zmq_publisher.initialize') as mock_zmq_init:
                    # Setup mocks - database returns accounts ordered by priority
                    mock_db_available.return_value = True
                    mock_get_accounts.return_value = [high_priority_account, low_priority_account]
                    mock_zmq_init.return_value = True
                    
                    # Reset gateway manager state
                    gateway_manager.active_accounts = []
                    
                    # Load accounts
                    accounts = await gateway_manager._load_accounts_from_database()
                    
                    # Verify priority ordering is maintained
                    assert len(accounts) == 2
                    assert accounts[0]['id'] == 'high_priority'
                    assert accounts[0]['priority'] == 1
                    assert accounts[1]['id'] == 'low_priority'
                    assert accounts[1]['priority'] == 5
    
    def test_health_endpoint_with_gateway_status(self, client):
        """Test health endpoint includes gateway manager status."""
        with patch.object(database_service, 'is_available') as mock_db_available:
            with patch.object(gateway_manager, 'get_account_status') as mock_gateway_status:
                # Setup mocks
                mock_db_available.return_value = True
                mock_gateway_status.return_value = {
                    'total_accounts': 2,
                    'connected_accounts': 1,
                    'accounts': [
                        {
                            'id': 'test_ctp',
                            'gateway_type': 'ctp',
                            'priority': 1,
                            'connected': True,
                            'connection_attempts': 1,
                            'connection_duration': 30.5
                        },
                        {
                            'id': 'test_sopt',
                            'gateway_type': 'sopt',
                            'priority': 2,
                            'connected': False,
                            'connection_attempts': 2,
                            'connection_duration': 0.0
                        }
                    ]
                }
                
                # Test health endpoint
                response = client.get("/health")
                
                assert response.status_code == 200
                data = response.json()
                
                assert data['status'] == 'ok'
                assert data['database_available'] is True
                assert data['gateway_manager'] is not None
                assert data['gateway_manager']['total_accounts'] == 2
                assert data['gateway_manager']['connected_accounts'] == 1
                assert len(data['gateway_manager']['accounts']) == 2
    
    @pytest.mark.asyncio
    async def test_startup_error_handling_continues_with_partial_failures(self):
        """Test that startup continues even if some account initializations fail."""
        good_account = MarketDataAccount(
            id='good_account',
            gateway_type='ctp',
            settings={'userID': 'good'},
            priority=1,
            is_enabled=True
        )
        
        bad_account = MarketDataAccount(
            id='bad_account',
            gateway_type='ctp',
            settings={'userID': 'bad'},
            priority=2,
            is_enabled=True
        )
        
        with patch.object(database_service, 'is_available') as mock_db_available:
            with patch.object(database_service, 'get_all_accounts') as mock_get_accounts:
                with patch('app.services.gateway_manager.zmq_publisher.initialize') as mock_zmq_init:
                    with patch('app.services.gateway_manager.CTP_AVAILABLE', True):
                        # Setup mocks
                        mock_db_available.return_value = True
                        mock_get_accounts.return_value = [good_account, bad_account]
                        mock_zmq_init.return_value = True
                        
                        # Reset gateway manager state
                        gateway_manager.active_accounts = []
                        gateway_manager.main_engines = {}
                        gateway_manager.event_engines = {}
                        
                        call_count = 0
                        def side_effect_engine(*args, **kwargs):
                            nonlocal call_count
                            call_count += 1
                            if call_count == 1:
                                return Mock()  # First call succeeds
                            else:
                                raise Exception("Second engine fails")  # Second call fails
                        
                        # Mock engine creation with partial failure
                        with patch('app.services.gateway_manager.EventEngine') as mock_event_engine:
                            with patch('app.services.gateway_manager.MainEngine') as mock_main_engine:
                                mock_event_engine.side_effect = side_effect_engine
                                mock_main_engine.return_value = Mock()
                                
                                # Test initialization
                                result = await gateway_manager.initialize()
                                
                                # Verify results - should succeed with partial initialization
                                assert result is True  # At least one successful initialization
                                assert len(gateway_manager.active_accounts) == 2  # Both accounts loaded