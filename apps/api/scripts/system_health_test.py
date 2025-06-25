#!/usr/bin/env python3
"""
Market Data Hub System Health Test Script
Comprehensive testing of all system components in development environment
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.database_service import DatabaseService
from app.services.gateway_manager import GatewayManager
from app.services.health_monitor import HealthMonitor
from app.services.websocket_manager import WebSocketManager
from app.services.zmq_publisher import ZMQPublisher
from app.services.event_bus import event_bus


async def test_database_service():
    """Test database service functionality"""
    print("\n🗄️  Testing Database Service...")
    
    try:
        db = DatabaseService()
        print("   ✅ Database Service initialized")
        
        # Test database operations
        accounts = await db.get_all_accounts()
        print(f"   ✅ Database query successful: {len(accounts)} accounts found")
        
        if accounts:
            print("   📊 Account Details:")
            for account in accounts:
                print(f"     - {account.gateway_name}: {account.status} ({account.account_id})")
        else:
            print("   ℹ️  No accounts found in database")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Database Service Error: {e}")
        return False


def test_gateway_manager():
    """Test gateway manager functionality"""
    print("\n🌐 Testing Gateway Manager...")
    
    try:
        gateway_mgr = GatewayManager()
        print("   ✅ Gateway Manager initialized")
        
        # Test gateway operations
        account_status = gateway_mgr.get_account_status()
        print(f"   ✅ Account status query successful")
        print(f"   📊 Total accounts: {account_status.get('total_accounts', 0)}")
        print(f"   📊 Connected accounts: {account_status.get('connected_accounts', 0)}")
        
        accounts = account_status.get('accounts', [])
        if accounts:
            print("   📊 Account Details:")
            for account in accounts:
                print(f"     - {account.get('gateway_name', 'Unknown')}: {account.get('status', 'Unknown')}")
        else:
            print("   ℹ️  No active accounts found")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Gateway Manager Error: {e}")
        return False


def test_health_monitor():
    """Test health monitor functionality"""
    print("\n💓 Testing Health Monitor...")
    
    try:
        health_monitor = HealthMonitor()
        print("   ✅ Health Monitor initialized")
        print(f"   ⏱️  Check Interval: {health_monitor.health_check_interval}s")
        print(f"   🎯 CTP Canary Contracts: {health_monitor.ctp_canary_contracts}")
        print(f"   🎯 SOPT Canary Contracts: {health_monitor.sopt_canary_contracts}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Health Monitor Error: {e}")
        return False


def test_websocket_manager():
    """Test WebSocket manager functionality"""
    print("\n🔌 Testing WebSocket Manager...")
    
    try:
        ws_manager = WebSocketManager()
        print("   ✅ WebSocket Manager initialized")
        print(f"   👤 Active connections: {len(ws_manager.active_connections)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ WebSocket Manager Error: {e}")
        return False


def test_zmq_publisher():
    """Test ZMQ publisher functionality"""
    print("\n📡 Testing ZMQ Publisher...")
    
    try:
        zmq_pub = ZMQPublisher()
        print("   ✅ ZMQ Publisher initialized")
        
        return True
        
    except Exception as e:
        print(f"   ❌ ZMQ Publisher Error: {e}")
        return False


def test_environment_config():
    """Test environment configuration"""
    print("\n⚙️  Testing Environment Configuration...")
    
    # Load environment variables from .env file
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print(f"   ✅ Environment file found: {env_file}")
        
        # Read and display key configuration
        with open(env_file, 'r') as f:
            lines = f.readlines()
            
        config = {}
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key] = value
        
        print("   📋 Key Configuration:")
        important_keys = [
            'ENVIRONMENT', 'ENABLE_CTP_GATEWAY', 'ENABLE_CTP_MOCK',
            'ENABLE_DATABASE', 'DATABASE_URL', 'ENABLE_ZMQ_PUBLISHER'
        ]
        
        for key in important_keys:
            value = config.get(key, 'Not set')
            print(f"     - {key}: {value}")
            
        return True
    else:
        print(f"   ❌ Environment file not found: {env_file}")
        return False


def test_event_bus():
    """Test event bus functionality"""
    print("\n🚌 Testing Event Bus...")
    
    try:
        # Test event bus operations
        print("   ✅ Event Bus accessible")
        print(f"   📊 Event Bus type: {type(event_bus)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Event Bus Error: {e}")
        return False


async def main():
    """Run comprehensive system health test"""
    print("🚀 Market Data Hub System Health Test")
    print("=" * 50)
    
    test_results = []
    
    # Test all components
    test_results.append(test_environment_config())
    test_results.append(await test_database_service())
    test_results.append(test_gateway_manager())
    test_results.append(test_health_monitor())
    test_results.append(test_websocket_manager())
    test_results.append(test_zmq_publisher())
    test_results.append(test_event_bus())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"   ✅ Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("   🎉 All tests passed! System is healthy and ready.")
        return True
    else:
        print(f"   ⚠️  {total - passed} test(s) failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(main())
    sys.exit(0 if success else 1)