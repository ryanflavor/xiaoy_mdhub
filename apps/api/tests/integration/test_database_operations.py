#!/usr/bin/env python3
"""
Test script for database operations.

This script tests the complete database service layer by creating, reading,
updating, and deleting market data accounts.
"""

import asyncio
import json
import os
import sys
import pytest
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.config.database import db_manager
from app.services.database_service import database_service


@pytest.mark.asyncio
async def test_database_operations(test_environment):
    """Test all database operations."""
    print("🚀 Starting Database Operations Test")
    print("=" * 50)
    
    # Initialize database
    print("1. Initializing database connection...")
    db_initialized = await db_manager.initialize()
    
    if not db_initialized:
        print("❌ Database initialization failed")
        return False
    
    print("✅ Database initialized successfully")
    
    # Test data
    test_account_ctp = {
        "id": "test_ctp_account",
        "gateway_type": "ctp",
        "settings": {
            "userID": "test_user",
            "password": "test_password",
            "brokerID": "9999",
            "authCode": "test_auth",
            "appID": "simnow_client_test",
            "mdAddress": "tcp://test.md.com:41213",
            "tdAddress": "tcp://test.td.com:41205"
        },
        "priority": 1,
        "is_enabled": True,
        "description": "Test CTP Account"
    }
    
    test_account_sopt = {
        "id": "test_sopt_account",
        "gateway_type": "sopt",
        "settings": {
            "username": "sopt_user",
            "token": "sopt_token",
            "serverAddress": "tcp://sopt.test.com:7709"
        },
        "priority": 2,
        "is_enabled": True,
        "description": "Test SOPT Account"
    }
    
    try:
        # Test 1: Create accounts
        print("\n2. Testing account creation...")
        
        ctp_account = await database_service.create_account(test_account_ctp)
        if ctp_account:
            print(f"✅ Created CTP account: {ctp_account.id}")
        else:
            print("❌ Failed to create CTP account")
            return False
        
        sopt_account = await database_service.create_account(test_account_sopt)
        if sopt_account:
            print(f"✅ Created SOPT account: {sopt_account.id}")
        else:
            print("❌ Failed to create SOPT account")
            return False
        
        # Test 2: Read single account
        print("\n3. Testing single account retrieval...")
        
        retrieved_ctp = await database_service.get_account("test_ctp_account")
        if retrieved_ctp and retrieved_ctp.gateway_type == "ctp":
            print(f"✅ Retrieved CTP account: {retrieved_ctp.id}")
            print(f"   Settings: {json.dumps(retrieved_ctp.settings, indent=2)}")
        else:
            print("❌ Failed to retrieve CTP account")
            return False
        
        # Test 3: Read all accounts
        print("\n4. Testing all accounts retrieval...")
        
        all_accounts = await database_service.get_all_accounts()
        if len(all_accounts) >= 2:
            print(f"✅ Retrieved {len(all_accounts)} accounts:")
            for acc in all_accounts:
                print(f"   - {acc.id} ({acc.gateway_type}) - Priority: {acc.priority}")
        else:
            print("❌ Failed to retrieve all accounts")
            return False
        
        # Test 4: Get accounts by gateway type
        print("\n5. Testing accounts by gateway type...")
        
        ctp_accounts = await database_service.get_accounts_by_gateway_type("ctp")
        if len(ctp_accounts) >= 1:
            print(f"✅ Retrieved {len(ctp_accounts)} CTP accounts")
        else:
            print("❌ Failed to retrieve CTP accounts")
            return False
        
        # Test 5: Update account
        print("\n6. Testing account update...")
        
        update_data = {
            "priority": 5,
            "description": "Updated Test CTP Account",
            "is_enabled": False
        }
        
        updated_account = await database_service.update_account("test_ctp_account", update_data)
        if updated_account and updated_account.priority == 5:
            print(f"✅ Updated account: {updated_account.id}")
            print(f"   New priority: {updated_account.priority}")
            print(f"   New description: {updated_account.description}")
            print(f"   Enabled: {updated_account.is_enabled}")
        else:
            print("❌ Failed to update account")
            return False
        
        # Test 6: Settings validation
        print("\n7. Testing settings validation...")
        
        try:
            valid_settings = await database_service.validate_settings_json(
                {"userID": "test", "password": "test", "brokerID": "9999", "mdAddress": "tcp://test:41213"},
                "ctp"
            )
            print("✅ Settings validation passed")
        except ValueError as e:
            print(f"❌ Settings validation failed: {e}")
            return False
        
        # Test invalid settings
        try:
            await database_service.validate_settings_json(
                {"invalid": "settings"},
                "ctp"
            )
            print("❌ Invalid settings validation should have failed")
            return False
        except ValueError:
            print("✅ Invalid settings correctly rejected")
        
        # Test 7: JSON serialization/deserialization
        print("\n8. Testing JSON serialization...")
        
        account_dict = retrieved_ctp.to_dict()
        if isinstance(account_dict, dict) and "settings" in account_dict:
            print("✅ Account serialization successful")
            
            # Verify settings are properly stored and retrieved
            if account_dict["settings"]["userID"] == "test_user":
                print("✅ Settings JSON storage/retrieval successful")
            else:
                print("❌ Settings JSON storage/retrieval failed")
                return False
        else:
            print("❌ Account serialization failed")
            return False
        
        # Test 8: Database availability check
        print("\n9. Testing database availability...")
        
        is_available = await database_service.is_available()
        if is_available:
            print("✅ Database service is available")
        else:
            print("❌ Database service unavailable")
            return False
        
        # Test 9: Delete accounts (cleanup)
        print("\n10. Testing account deletion...")
        
        deleted_ctp = await database_service.delete_account("test_ctp_account")
        deleted_sopt = await database_service.delete_account("test_sopt_account")
        
        if deleted_ctp and deleted_sopt:
            print("✅ Test accounts deleted successfully")
        else:
            print("❌ Failed to delete test accounts")
            return False
        
        # Verify deletion
        remaining_accounts = await database_service.get_all_accounts()
        test_accounts_remaining = [acc for acc in remaining_accounts if acc.id.startswith("test_")]
        
        if len(test_accounts_remaining) == 0:
            print("✅ Cleanup verified - no test accounts remaining")
        else:
            print(f"⚠️  Warning: {len(test_accounts_remaining)} test accounts still exist")
        
        print("\n" + "=" * 50)
        print("🎉 All database operations tests PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Shutdown database
        await db_manager.shutdown()
        print("📊 Database connection closed")


async def main():
    """Main test function."""
    success = await test_database_operations()
    
    if success:
        print("\n✅ Database operations test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Database operations test failed!")
        sys.exit(1)


if __name__ == "__main__":
    # Set up environment for testing
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test_mdhub.db")
    os.environ.setdefault("ENABLE_DATABASE", "true")
    
    asyncio.run(main())