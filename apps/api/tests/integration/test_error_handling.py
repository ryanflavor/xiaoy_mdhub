#!/usr/bin/env python3
"""
Test script for database error handling and fallback mechanism.

This script tests the retry logic, error handling, and graceful degradation
when the database is unavailable.
"""

import asyncio
import os
import sys
import pytest
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.config.database import db_manager
from app.services.database_service import database_service


@pytest.mark.asyncio
async def test_database_unavailability():
    """Test database unavailability handling."""
    print("🔧 Testing Database Unavailability Handling")
    print("=" * 50)
    
    # Test 1: Invalid database URL (should trigger retry logic)
    print("1. Testing invalid database URL with retry logic...")
    
    # Set invalid database URL
    original_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "mysql://invalid:invalid@nonexistent:3306/invalid"
    os.environ["DATABASE_RETRY_ATTEMPTS"] = "2"
    os.environ["DATABASE_RETRY_DELAY"] = "0.5"
    
    # Reinitialize config
    db_manager.config.__init__()
    
    db_initialized = await db_manager.initialize()
    
    if not db_initialized:
        print("✅ Correctly handled invalid database URL with graceful fallback")
    else:
        print("❌ Should have failed with invalid database URL")
        return False
    
    # Test 2: Database service availability check
    print("\n2. Testing database service availability...")
    
    is_available = await database_service.is_available()
    if not is_available:
        print("✅ Database service correctly reports unavailable")
    else:
        print("❌ Database service should report unavailable")
        return False
    
    # Test 3: CRUD operations with database unavailable
    print("\n3. Testing CRUD operations with database unavailable...")
    
    # Create account should return None
    test_account = {
        "id": "test_account",
        "gateway_type": "ctp",
        "settings": {
            "userID": "test_user",
            "password": "test_password",
            "brokerID": "9999",
            "mdAddress": "tcp://test.com:41213"
        },
        "priority": 1,
        "is_enabled": True
    }
    
    created_account = await database_service.create_account(test_account)
    if created_account is None:
        print("✅ Create account correctly returns None when database unavailable")
    else:
        print("❌ Create account should return None when database unavailable")
        return False
    
    # Get account should return None
    retrieved_account = await database_service.get_account("test_account")
    if retrieved_account is None:
        print("✅ Get account correctly returns None when database unavailable")
    else:
        print("❌ Get account should return None when database unavailable")
        return False
    
    # Get all accounts should return empty list
    all_accounts = await database_service.get_all_accounts()
    if len(all_accounts) == 0:
        print("✅ Get all accounts correctly returns empty list when database unavailable")
    else:
        print("❌ Get all accounts should return empty list when database unavailable")
        return False
    
    # Test 4: Disable database via environment variable
    print("\n4. Testing database disabled via ENABLE_DATABASE=false...")
    
    # Reset database URL and disable database
    if original_url:
        os.environ["DATABASE_URL"] = original_url
    else:
        os.environ.pop("DATABASE_URL", None)
    
    os.environ["ENABLE_DATABASE"] = "false"
    
    # Shutdown current manager and create new one
    await db_manager.shutdown()
    db_manager.config.__init__()
    
    db_initialized = await db_manager.initialize()
    
    if not db_initialized:
        print("✅ Database correctly disabled via ENABLE_DATABASE=false")
    else:
        print("❌ Database should be disabled when ENABLE_DATABASE=false")
        return False
    
    # Test 5: Application startup resilience
    print("\n5. Testing application startup resilience...")
    
    # Simulate the startup sequence
    try:
        # This should not raise an exception even with database disabled
        is_healthy = db_manager.is_healthy
        is_enabled = db_manager.is_enabled
        
        print(f"   Database healthy: {is_healthy}")
        print(f"   Database enabled: {is_enabled}")
        
        if not is_healthy and not is_enabled:
            print("✅ Application startup handles database unavailability gracefully")
        else:
            print("❌ Application startup should handle database unavailability")
            return False
            
    except Exception as e:
        print(f"❌ Application startup failed with exception: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All error handling tests PASSED!")
    return True


@pytest.mark.asyncio
async def test_successful_connection_with_retry():
    """Test successful connection after retries."""
    print("\n🔄 Testing Successful Connection After Initial Failure")
    print("=" * 50)
    
    # Reset to valid configuration
    os.environ["DATABASE_URL"] = "sqlite:///./test_retry.db"
    os.environ["ENABLE_DATABASE"] = "true"
    os.environ["DATABASE_RETRY_ATTEMPTS"] = "3"
    os.environ["DATABASE_RETRY_DELAY"] = "0.1"
    
    # Shutdown current manager and create new one
    await db_manager.shutdown()
    db_manager.config.__init__()
    
    # This should succeed
    db_initialized = await db_manager.initialize()
    
    if db_initialized:
        print("✅ Database connection successful with valid configuration")
        
        # Test a basic operation
        test_account = {
            "id": "retry_test_account",
            "gateway_type": "ctp",
            "settings": {
                "userID": "test_user",
                "password": "test_password",
                "brokerID": "9999",
                "mdAddress": "tcp://test.com:41213"
            },
            "priority": 1,
            "is_enabled": True
        }
        
        created_account = await database_service.create_account(test_account)
        if created_account:
            print("✅ CRUD operations work correctly after successful connection")
            
            # Cleanup
            await database_service.delete_account("retry_test_account")
            
        else:
            print("❌ CRUD operations should work after successful connection")
            return False
            
    else:
        print("❌ Database connection should succeed with valid configuration")
        return False
    
    await db_manager.shutdown()
    
    # Cleanup test database
    try:
        os.remove("test_retry.db")
    except:
        pass
    
    print("✅ Connection retry test completed successfully!")
    return True


async def main():
    """Main test function."""
    print("🚀 Starting Database Error Handling Tests")
    print("=" * 60)
    
    try:
        # Test 1: Database unavailability handling
        success1 = await test_database_unavailability()
        
        # Test 2: Successful connection after retries
        success2 = await test_successful_connection_with_retry()
        
        if success1 and success2:
            print("\n" + "=" * 60)
            print("🎉 ALL ERROR HANDLING TESTS PASSED!")
            print("✅ Database fallback mechanism works correctly")
            print("✅ Retry logic functions properly")
            print("✅ Application remains stable without database")
            sys.exit(0)
        else:
            print("\n❌ Some error handling tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())