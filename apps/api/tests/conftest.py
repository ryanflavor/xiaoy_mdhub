"""
Pytest configuration and shared fixtures for Market Data Hub tests.
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path

# Add the app directory to Python path for imports
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

# Use pytest-asyncio event loop
pytest_plugins = ['pytest_asyncio']

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy."""
    import asyncio
    return asyncio.get_event_loop_policy()

@pytest.fixture(scope="session")
def test_database_url():
    """Create a temporary database URL for testing."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    db_url = f"sqlite:///{db_path}"
    
    yield db_url
    
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass

@pytest.fixture(scope="session")
def test_environment(test_database_url):
    """Set up test environment variables."""
    test_env = {
        'DATABASE_URL': test_database_url,
        'ENABLE_DATABASE': 'true',
        'ENABLE_ZMQ_PUBLISHER': 'true',
        'ZMQ_PORT': '5560',
        'ZMQ_PERFORMANCE_MODE': 'development',
        'ENABLE_PERFORMANCE_MONITORING': 'true'
    }
    
    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield test_env
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value

@pytest.fixture
def sample_ctp_account():
    """Sample CTP account data for testing."""
    return {
        "id": "test_ctp_account",
        "gateway_type": "ctp",
        "settings": {
            "userID": "test123",
            "password": "test456",
            "brokerID": "9999",
            "mdAddress": "tcp://180.168.146.187:10131",
            "tdAddress": "tcp://180.168.146.187:10130"
        },
        "priority": 1,
        "is_enabled": True,
        "description": "Test CTP Account"
    }

@pytest.fixture
def sample_sopt_account():
    """Sample SOPT account data for testing."""
    return {
        "id": "test_sopt_account",
        "gateway_type": "sopt",
        "settings": {
            "username": "sopt_user",
            "token": "sopt_token_123",
            "serverAddress": "tcp://192.168.1.100:8080"
        },
        "priority": 2,
        "is_enabled": True,
        "description": "Test SOPT Account"
    }

@pytest.fixture
def mock_tick_data():
    """Generate mock tick data for testing."""
    from datetime import datetime, timezone
    
    class MockTickData:
        def __init__(self, symbol="TEST", price=100.0):
            self.symbol = symbol
            self.vt_symbol = f"{symbol}.MOCK"
            self.datetime = datetime.now(timezone.utc)
            self.last_price = price
            self.volume = 1000
            self.last_volume = 10
            self.bid_price_1 = price - 0.05
            self.ask_price_1 = price + 0.05
            self.bid_volume_1 = 50
            self.ask_volume_1 = 50
    
    return MockTickData

@pytest.fixture
def performance_thresholds():
    """Provide performance threshold configuration for testing."""
    return {
        'max_serialization_latency_p95_ms': 1.0,
        'min_publication_rate_per_sec': 100.0,
        'max_memory_overhead_mb': 50.0,
        'min_success_rate_percent': 95.0
    }

def pytest_configure(config):
    """Pytest configuration hook."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "load: mark test as load test")
    config.addinivalue_line("markers", "slow: mark test as slow running")

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "load" in str(item.fspath):
            item.add_marker(pytest.mark.load)
            item.add_marker(pytest.mark.slow)