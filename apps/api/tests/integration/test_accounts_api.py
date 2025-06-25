"""
Fixed integration tests for Account Management API endpoints.
"""

import pytest
import asyncio
import os
import tempfile
from httpx import AsyncClient
from fastapi import FastAPI

class TestAccountsAPI:
    """Test class for accounts API."""
    
    @pytest.mark.asyncio
    async def test_get_accounts_empty(self, test_environment):
        """Test GET /api/accounts with no accounts."""
        
        # Import after test environment is set
        from app.config.database import DatabaseManager, DatabaseConfig
        from app.services.database_service import DatabaseService
        from app.api.routes import health
        from app.routes.accounts import router as accounts_router, get_database_service
        
        # Create and initialize database
        config = DatabaseConfig()
        manager = DatabaseManager()
        manager.config = config
        
        success = await manager.initialize()
        assert success, "Database initialization failed"
        
        # Create database service
        db_service = DatabaseService()
        db_service.db_manager = manager
        
        try:
            # Verify database service is available
            assert await db_service.is_available(), "Database service not available"
            
            # Clear any existing accounts from previous tests
            existing_accounts = await db_service.get_all_accounts()
            for account in existing_accounts:
                await db_service.delete_account(account.id)
            
            # Create test app
            app = FastAPI(title="Test API")
            app.include_router(health.router, prefix="/api", tags=["health"])
            app.include_router(accounts_router)
            
            # Override database dependency
            async def get_test_database_service():
                return db_service
            
            app.dependency_overrides[get_database_service] = get_test_database_service
            
            # Test the API
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/accounts")
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
                data = response.json()
                assert isinstance(data, list), "Response should be a list"
                assert len(data) == 0, "Should start with no accounts"
                
        finally:
            await manager.shutdown()
    
    @pytest.mark.asyncio 
    async def test_create_account_ctp_success(self, test_environment, sample_ctp_account):
        """Test POST /api/accounts with valid CTP account."""
        
        # Import after test environment is set
        from app.config.database import DatabaseManager, DatabaseConfig
        from app.services.database_service import DatabaseService
        from app.api.routes import health
        from app.routes.accounts import router as accounts_router, get_database_service
        
        # Create and initialize database
        config = DatabaseConfig()
        manager = DatabaseManager()
        manager.config = config
        
        success = await manager.initialize()
        assert success, "Database initialization failed"
        
        # Create database service
        db_service = DatabaseService()
        db_service.db_manager = manager
        
        try:
            # Clear any existing accounts from previous tests
            existing_accounts = await db_service.get_all_accounts()
            for account in existing_accounts:
                await db_service.delete_account(account.id)
                
            # Create test app
            app = FastAPI(title="Test API")
            app.include_router(health.router, prefix="/api", tags=["health"])
            app.include_router(accounts_router)
            
            # Override database dependency
            async def get_test_database_service():
                return db_service
            
            app.dependency_overrides[get_database_service] = get_test_database_service
            
            # Test the API
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/accounts", json=sample_ctp_account)
                assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
                
                data = response.json()
                assert data["id"] == sample_ctp_account["id"]
                assert data["gateway_type"] == sample_ctp_account["gateway_type"]
                assert data["priority"] == sample_ctp_account["priority"]
                assert data["is_enabled"] == sample_ctp_account["is_enabled"]
                assert data["description"] == sample_ctp_account["description"]
                assert "created_at" in data
                assert "updated_at" in data
                
                # Verify settings
                original_settings = sample_ctp_account["settings"]
                response_settings = data["settings"]
                for key, value in original_settings.items():
                    assert response_settings[key] == value, f"Settings field {key} mismatch"
                
        finally:
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_accounts_crud_workflow(self, test_environment):
        """Test complete CRUD workflow."""
        
        # Import after test environment is set
        from app.config.database import DatabaseManager, DatabaseConfig
        from app.services.database_service import DatabaseService
        from app.api.routes import health
        from app.routes.accounts import router as accounts_router, get_database_service
        
        # Create and initialize database
        config = DatabaseConfig()
        manager = DatabaseManager()
        manager.config = config
        
        success = await manager.initialize()
        assert success, "Database initialization failed"
        
        # Create database service
        db_service = DatabaseService()
        db_service.db_manager = manager
        
        try:
            # Clear any existing accounts from previous tests
            existing_accounts = await db_service.get_all_accounts()
            for account in existing_accounts:
                await db_service.delete_account(account.id)
                
            # Create test app
            app = FastAPI(title="Test API")
            app.include_router(health.router, prefix="/api", tags=["health"])
            app.include_router(accounts_router)
            
            # Override database dependency
            async def get_test_database_service():
                return db_service
            
            app.dependency_overrides[get_database_service] = get_test_database_service
            
            test_account = {
                "id": "test_crud_account",
                "gateway_type": "ctp",
                "settings": {
                    "userID": "crud_test",
                    "password": "crud_pass",
                    "brokerID": "9999",
                    "mdAddress": "tcp://test:10131",
                    "tdAddress": "tcp://test:10130"
                },
                "priority": 1,
                "is_enabled": True,
                "description": "CRUD Test Account"
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # 1. Create account
                response = await client.post("/api/accounts", json=test_account)
                assert response.status_code == 201
                
                # 2. Get all accounts (should have 1)
                response = await client.get("/api/accounts")
                assert response.status_code == 200
                accounts = response.json()
                assert len(accounts) == 1
                assert accounts[0]["id"] == test_account["id"]
                
                # 3. Update account
                update_data = {
                    "priority": 5,
                    "description": "Updated CRUD Test Account",
                    "is_enabled": False
                }
                response = await client.put(f"/api/accounts/{test_account['id']}", json=update_data)
                assert response.status_code == 200
                updated = response.json()
                assert updated["priority"] == 5
                assert updated["description"] == "Updated CRUD Test Account"
                assert updated["is_enabled"] == False
                
                # 4. Delete account
                response = await client.delete(f"/api/accounts/{test_account['id']}")
                assert response.status_code == 204  # DELETE returns 204 No Content
                
                # 5. Verify deletion
                response = await client.get("/api/accounts")
                assert response.status_code == 200
                accounts = response.json()
                assert len(accounts) == 0
                
        finally:
            await manager.shutdown()


# Standalone tests for debugging
@pytest.mark.asyncio
async def test_openapi_schema_generation():
    """Test that OpenAPI schema generation works."""
    from app.app import create_app
    
    app = create_app()
    schema = app.openapi()
    
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "Market Data Hub Management API"
    assert "paths" in schema
    assert "/api/accounts" in schema["paths"]
    
    print("✅ OpenAPI schema generation test passed!")


@pytest.mark.asyncio
async def test_swagger_ui_accessibility():
    """Test that Swagger UI is accessible."""
    from app.app import create_app
    from httpx import AsyncClient
    
    app = create_app()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test docs endpoint
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Test redoc endpoint  
        response = await client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Test openapi.json endpoint
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
    
    print("✅ Swagger UI accessibility test passed!")


if __name__ == "__main__":
    # Run standalone tests
    asyncio.run(test_openapi_schema_generation())
    asyncio.run(test_swagger_ui_accessibility())