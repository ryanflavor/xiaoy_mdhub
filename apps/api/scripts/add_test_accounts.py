#!/usr/bin/env python3
"""
Script to add test accounts to the mdhub.db database.
Load account credentials from environment variables or configuration files.
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any

def load_test_accounts_from_env() -> List[Dict[str, Any]]:
    """
    Load test account configurations from environment variables.
    
    Expected environment variables:
    - ACCOUNT_1_CONFIG: JSON string for first account
    - ACCOUNT_2_CONFIG: JSON string for second account
    - etc.
    
    Returns:
        List[Dict[str, Any]]: List of account configurations
    """
    accounts = []
    
    # Try to load from environment variables
    for i in range(1, 11):  # Support up to 10 accounts
        env_var = f"ACCOUNT_{i}_CONFIG"
        account_json = os.getenv(env_var)
        
        if account_json:
            try:
                account = json.loads(account_json)
                accounts.append(account)
                print(f"Loaded account {i} from environment variable {env_var}")
            except json.JSONDecodeError as e:
                print(f"Error parsing {env_var}: {e}")
                continue
    
    return accounts

def load_test_accounts_from_file(file_path: str = "accounts_config.json") -> List[Dict[str, Any]]:
    """
    Load test account configurations from a JSON file.
    
    Args:
        file_path: Path to the JSON configuration file
        
    Returns:
        List[Dict[str, Any]]: List of account configurations
    """
    if not os.path.exists(file_path):
        print(f"Configuration file {file_path} not found")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'accounts' in data:
                return data['accounts']
            else:
                print(f"Invalid configuration format in {file_path}")
                return []
    except Exception as e:
        print(f"Error loading configuration from {file_path}: {e}")
        return []

def get_sample_account_structure() -> Dict[str, Any]:
    """
    Return a sample account structure for reference.
    
    Returns:
        Dict[str, Any]: Sample account structure with placeholder values
    """
    return {
        "broker": "示例期货公司",
        "connect_setting": {
            "交易服务器": "SERVER_IP:PORT",
            "产品信息": "PRODUCT_INFO",
            "产品名称": "PRODUCT_NAME", 
            "密码": "PASSWORD",
            "授权编码": "AUTH_CODE",
            "用户名": "USERNAME",
            "经纪商代码": "BROKER_CODE",
            "行情服务器": "MD_SERVER_IP:PORT"
        },
        "gateway": {
            "gateway_class": "CtpGateway or SoptGateway",
            "gateway_name": "CTP or SOPT"
        },
        "market": "期货期权 or 个股期权",
        "name": "UNIQUE_ACCOUNT_NAME"
    }

def create_account_record(account_data, priority=1):
    """Convert account data to database record format."""
    # Create settings object combining all relevant fields
    settings = {
        "broker": account_data["broker"],
        "connect_setting": account_data["connect_setting"],
        "gateway": account_data["gateway"],
        "market": account_data["market"]
    }
    
    # Determine gateway type from gateway class
    gateway_type = "SOPT" if account_data["gateway"]["gateway_class"] == "SoptGateway" else "CTP"
    
    # Create unique account ID by combining name, broker and gateway type
    unique_id = f"{account_data['name']}-{account_data['broker']}-{gateway_type}"
    
    return {
        "id": unique_id,
        "gateway_type": gateway_type,
        "settings": json.dumps(settings, ensure_ascii=False),
        "priority": priority,
        "is_enabled": True,
        "description": f"{account_data['broker']} - {account_data['market']} ({gateway_type})",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

def add_accounts_to_db():
    """Add test accounts to the database."""
    db_path = "mdhub.db"
    
    # Load test accounts from environment or configuration file
    test_accounts = load_test_accounts_from_env()
    if not test_accounts:
        test_accounts = load_test_accounts_from_file("scripts/account.json")
    
    if not test_accounts:
        print("No test accounts found!")
        print("Please provide account configuration via:")
        print("1. Environment variables (ACCOUNT_1_CONFIG, ACCOUNT_2_CONFIG, etc.)")
        print("2. Configuration file (accounts_config.json)")
        print("\nSample account structure:")
        print(json.dumps(get_sample_account_structure(), indent=2, ensure_ascii=False))
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='market_data_accounts'
        """)
        
        if not cursor.fetchone():
            print("Error: market_data_accounts table does not exist!")
            print("Please run database migrations first.")
            return False
        
        # Insert test accounts
        for i, account_data in enumerate(test_accounts, 1):
            record = create_account_record(account_data, priority=i)
            
            # Check if account already exists
            cursor.execute("SELECT id FROM market_data_accounts WHERE id = ?", (record["id"],))
            if cursor.fetchone():
                print(f"Account '{record['id']}' already exists, skipping...")
                continue
            
            # Insert new account
            cursor.execute("""
                INSERT INTO market_data_accounts 
                (id, gateway_type, settings, priority, is_enabled, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["id"],
                record["gateway_type"],
                record["settings"],
                record["priority"],
                record["is_enabled"],
                record["description"],
                record["created_at"],
                record["updated_at"]
            ))
            
            print(f"Added account: {record['id']}")
        
        # Commit changes
        conn.commit()
        print("Successfully added test accounts to database!")
        
        # Show added accounts
        cursor.execute("SELECT id, gateway_type, priority, is_enabled FROM market_data_accounts ORDER BY priority")
        accounts = cursor.fetchall()
        print("\nCurrent accounts in database:")
        for account in accounts:
            print(f"  - {account[0]} (Type: {account[1]}, Priority: {account[2]}, Enabled: {account[3]})")
        
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Account Configuration Loader")
    print("============================")
    add_accounts_to_db()