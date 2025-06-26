"""
Account management REST API endpoints.

This module provides CRUD operations for MarketDataAccount entities through
REST API endpoints with proper validation, error handling, and OpenAPI documentation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import structlog

from ..services.database_service import database_service
from ..models.market_data_account import MarketDataAccount
from ..services.gateway_manager import gateway_manager
from ..services.websocket_manager import WebSocketManager

# Configure logging
logger = structlog.get_logger(__name__)

# Create router with proper tags and prefix
router = APIRouter(
    prefix="/api/accounts",
    tags=["accounts"],
    responses={
        500: {"description": "Internal server error"},
        400: {"description": "Validation error"},
    }
)


class AccountSettings(BaseModel):
    """Pydantic model for account settings validation."""
    
    # CTP specific settings
    userID: Optional[str] = Field(None, description="User ID for CTP authentication")
    password: Optional[str] = Field(None, description="Password for CTP authentication")
    brokerID: Optional[str] = Field(None, description="Broker ID for CTP connection")
    authCode: Optional[str] = Field(None, description="Authentication code for CTP")
    appID: Optional[str] = Field(None, description="Application ID for CTP")
    mdAddress: Optional[str] = Field(None, description="Market data server address for CTP")
    tdAddress: Optional[str] = Field(None, description="Trading server address for CTP")
    
    # SOPT specific settings
    username: Optional[str] = Field(None, description="Username for SOPT authentication")
    token: Optional[str] = Field(None, description="Token for SOPT authentication")
    serverAddress: Optional[str] = Field(None, description="Server address for SOPT connection")
    
    # Common settings
    timeout: Optional[int] = Field(None, ge=1, le=300, description="Connection timeout in seconds")

    class Config:
        extra = "allow"  # Allow additional fields for flexibility


class AccountRequest(BaseModel):
    """Request model for creating/updating accounts."""
    
    id: str = Field(..., min_length=1, max_length=100, description="Unique account identifier")
    gateway_type: str = Field(..., description="Gateway type (ctp or sopt)")
    settings: AccountSettings = Field(..., description="Gateway-specific configuration settings")
    priority: int = Field(1, ge=1, le=100, description="Priority level (lower = higher priority)")
    is_enabled: bool = Field(True, description="Whether the account should be enabled")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    
    @field_validator('gateway_type')
    @classmethod
    def validate_gateway_type(cls, v):
        v_lower = v.lower()
        if v_lower not in ['ctp', 'sopt']:
            raise ValueError('Gateway type must be either "ctp" or "sopt" (case insensitive)')
        return v_lower


class AccountUpdateRequest(BaseModel):
    """Request model for partial account updates."""
    
    gateway_type: Optional[str] = Field(None, description="Gateway type (ctp or sopt)")
    settings: Optional[AccountSettings] = Field(None, description="Gateway-specific configuration settings")
    priority: Optional[int] = Field(None, ge=1, le=100, description="Priority level")
    is_enabled: Optional[bool] = Field(None, description="Whether the account should be enabled")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    
    @field_validator('gateway_type')
    @classmethod
    def validate_gateway_type(cls, v):
        if v is not None:
            v_lower = v.lower()
            if v_lower not in ['ctp', 'sopt']:
                raise ValueError('Gateway type must be either "ctp" or "sopt" (case insensitive)')
            return v_lower
        return v


class AccountResponse(BaseModel):
    """Response model for account data."""
    
    id: str = Field(..., description="Unique account identifier")
    gateway_type: str = Field(..., description="Gateway type")
    settings: Dict[str, Any] = Field(..., description="Gateway-specific settings")
    priority: int = Field(..., description="Priority level")
    is_enabled: bool = Field(..., description="Whether the account is enabled")
    description: Optional[str] = Field(None, description="Account description")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "ctp_main_account",
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
                "description": "Primary CTP account",
                "created_at": "2025-06-24T10:30:00Z",
                "updated_at": "2025-06-24T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    timestamp: str = Field(..., description="Error timestamp")


class GatewayControlRequest(BaseModel):
    """Request model for gateway control actions."""
    
    gateway_id: str = Field(..., description="Gateway identifier")
    action: str = Field(..., description="Control action: start, stop, or restart")
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ['start', 'stop', 'restart']:
            raise ValueError('Action must be one of: start, stop, restart')
        return v.lower()


class GatewayControlResponse(BaseModel):
    """Response model for gateway control actions."""
    
    success: bool = Field(..., description="Whether the action was successful")
    message: str = Field(..., description="Action result message")
    gateway_id: str = Field(..., description="Gateway identifier")
    action: str = Field(..., description="Action that was performed")
    timestamp: str = Field(..., description="Action timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Gateway restart initiated successfully",
                "gateway_id": "ctp_main_account",
                "action": "restart",
                "timestamp": "2025-06-25T10:30:45.123Z"
            }
        }


def account_to_response(account: MarketDataAccount) -> AccountResponse:
    """Convert database model to response model."""
    account_dict = account.to_dict()
    return AccountResponse(**account_dict)


async def get_database_service():
    """Dependency to get database service instance."""
    if not await database_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is not available"
        )
    return database_service


@router.get(
    "",
    response_model=List[AccountResponse],
    summary="List all accounts",
    description="Retrieve all configured market data accounts with their settings and status",
    responses={
        200: {
            "description": "List of accounts retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "ctp_main_account",
                            "gateway_type": "ctp",
                            "settings": {
                                "userID": "test123",
                                "password": "test456",
                                "brokerID": "9999",
                                "mdAddress": "tcp://180.168.146.187:10131"
                            },
                            "priority": 1,
                            "is_enabled": True,
                            "description": "Primary CTP account"
                        }
                    ]
                }
            }
        },
        503: {"description": "Database service unavailable"}
    }
)
async def get_accounts(
    enabled_only: bool = False,
    db_service = Depends(get_database_service)
) -> List[AccountResponse]:
    """
    Get all market data accounts.
    
    Args:
        enabled_only: If True, only return enabled accounts
        
    Returns:
        List of account configurations
    """
    try:
        logger.info("Fetching accounts", enabled_only=enabled_only)
        
        accounts = await db_service.get_all_accounts(enabled_only=enabled_only)
        response_accounts = [account_to_response(account) for account in accounts]
        
        logger.info("Accounts retrieved successfully", count=len(response_accounts))
        return response_accounts
        
    except Exception as e:
        logger.error("Error fetching accounts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve accounts: {str(e)}"
        )


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new account",
    description="Create a new market data account with validation and duplicate checking",
    responses={
        201: {
            "description": "Account created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "ctp_main_account",
                        "gateway_type": "ctp",
                        "settings": {
                            "userID": "test123",
                            "password": "test456",
                            "brokerID": "9999",
                            "mdAddress": "tcp://180.168.146.187:10131"
                        },
                        "priority": 1,
                        "is_enabled": True,
                        "description": "Primary CTP account"
                    }
                }
            }
        },
        400: {"description": "Validation error or invalid data"},
        409: {"description": "Account with this ID already exists"},
        503: {"description": "Database service unavailable"}
    }
)
async def create_account(
    account_data: AccountRequest = Body(..., description="Account configuration data"),
    db_service = Depends(get_database_service)
) -> AccountResponse:
    """
    Create a new market data account.
    
    Args:
        account_data: Account configuration including gateway type, settings, and metadata
        
    Returns:
        Created account data with timestamps
        
    Raises:
        HTTPException: For validation errors, duplicates, or database issues
    """
    try:
        logger.info("Creating new account", account_id=account_data.id, gateway_type=account_data.gateway_type)
        
        # Convert Pydantic model to dict for database service
        account_dict = account_data.model_dump()
        
        # Create account using database service
        created_account = await db_service.create_account(account_dict)
        
        if created_account is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service is not available"
            )
        
        logger.info("Account created successfully", account_id=created_account.id)
        return account_to_response(created_account)
        
    except ValueError as e:
        # Handle validation errors and duplicates
        error_msg = str(e)
        if "already exists" in error_msg:
            logger.warning("Duplicate account creation attempted", account_id=account_data.id, error=error_msg)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg
            )
        else:
            logger.warning("Account validation failed", account_id=account_data.id, error=error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
    except Exception as e:
        logger.error("Error creating account", account_id=account_data.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}"
        )


@router.put(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update account",
    description="Update an existing market data account with partial data support",
    responses={
        200: {
            "description": "Account updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "ctp_main_account",
                        "gateway_type": "ctp",
                        "settings": {
                            "userID": "test123",
                            "password": "new_password",
                            "brokerID": "9999",
                            "mdAddress": "tcp://180.168.146.187:10131"
                        },
                        "priority": 1,
                        "is_enabled": False,
                        "description": "Updated CTP account"
                    }
                }
            }
        },
        400: {"description": "Validation error or invalid data"},
        404: {"description": "Account not found"},
        503: {"description": "Database service unavailable"}
    }
)
async def update_account(
    account_id: str,
    update_data: AccountUpdateRequest = Body(..., description="Partial account data to update"),
    db_service = Depends(get_database_service)
) -> AccountResponse:
    """
    Update an existing market data account.
    
    Args:
        account_id: Unique identifier of the account to update
        update_data: Partial account data with fields to update
        
    Returns:
        Updated account data
        
    Raises:
        HTTPException: For validation errors, not found, or database issues
    """
    try:
        logger.info("Updating account", )
        
        # Convert Pydantic model to dict, excluding None values for partial updates
        update_dict = update_data.model_dump(exclude_none=True)
        
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update"
            )
        
        # Update account using database service
        updated_account = await db_service.update_account(account_id, update_dict)
        
        if updated_account is None:
            logger.warning("Account not found for update", )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with ID '{account_id}' not found"
            )
        
        logger.info("Account updated successfully", )
        return account_to_response(updated_account)
        
    except HTTPException:
        # Re-raise HTTP exceptions (they're already properly formatted)
        raise
    except ValueError as e:
        logger.warning("Account update validation failed",  error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error updating account",  error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update account: {str(e)}"
        )


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account",
    description="Delete an existing market data account",
    responses={
        204: {"description": "Account deleted successfully"},
        404: {"description": "Account not found"},
        503: {"description": "Database service unavailable"}
    }
)
async def delete_account(
    account_id: str,
    db_service = Depends(get_database_service)
):
    """
    Delete a market data account.
    
    Args:
        account_id: Unique identifier of the account to delete
        
    Returns:
        No content (204 status code)
        
    Raises:
        HTTPException: For not found or database issues
    """
    try:
        logger.info("Deleting account", )
        
        # Delete account using database service
        deleted = await db_service.delete_account(account_id)
        
        if not deleted:
            logger.warning("Account not found for deletion", )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with ID '{account_id}' not found"
            )
        
        logger.info("Account deleted successfully", )
        return None  # FastAPI will return 204 No Content
        
    except HTTPException:
        # Re-raise HTTP exceptions (they're already properly formatted)
        raise
    except Exception as e:
        logger.error("Error deleting account",  error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )


# Gateway Control Endpoints

async def get_gateway_manager():
    """Dependency to get gateway manager instance."""
    return gateway_manager


@router.post(
    "/{account_id}/start",
    response_model=GatewayControlResponse,
    summary="Start gateway",
    description="Start a gateway for the specified account",
    responses={
        200: {
            "description": "Gateway start initiated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Gateway start initiated successfully",
                        "gateway_id": "ctp_main_account",
                        "action": "start",
                        "timestamp": "2025-06-25T10:30:45.123Z"
                    }
                }
            }
        },
        400: {"description": "Invalid request or gateway already running"},
        404: {"description": "Account not found"},
        500: {"description": "Internal server error"}
    }
)
async def start_gateway(
    account_id: str,
    gw_manager = Depends(get_gateway_manager)
) -> GatewayControlResponse:
    """
    Start a gateway for the specified account.
    
    Args:
        account_id: Unique identifier of the account/gateway to start
        
    Returns:
        Gateway control response with action result
        
    Raises:
        HTTPException: For validation errors, not found, or server issues
    """
    try:
        logger.info(f"Starting gateway: {account_id}")
        
        # Call gateway manager to start the gateway
        result = await gw_manager.start_gateway(account_id)
        
        if not result["success"]:
            # Handle different error types
            error_code = result.get("error", "UNKNOWN_ERROR")
            
            if error_code == "TRADING_TIME_RESTRICTED":
                # Special handling for trading time restrictions
                trading_status = result.get("trading_status", {})
                detail = {
                    "error": "TRADING_TIME_RESTRICTED",
                    "message": result["message"],
                    "trading_status": trading_status,
                    "user_message": f"Cannot start {account_id} gateway outside trading hours",
                    "recommendation": f"Please wait until the next trading session starts",
                    "next_session": {
                        "name": trading_status.get("next_session_name"),
                        "start_time": trading_status.get("next_session_start"),
                        "time_until": None  # Frontend will calculate this
                    } if trading_status.get("next_session_start") else None
                }
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=detail
                )
            elif error_code == "ALREADY_RUNNING":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=result["message"]
                )
            elif error_code == "ACCOUNT_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["message"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["message"]
                )
        
        # Broadcast control action via WebSocket
        ws_manager = WebSocketManager.get_instance()
        await ws_manager.broadcast_gateway_control_action(
            gateway_id=account_id,
            action="start",
            status="completed",
            message="Gateway started successfully"
        )
        
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info("Gateway started successfully")
        
        return GatewayControlResponse(
            success=True,
            message=result["message"],
            gateway_id=account_id,
            action="start",
            timestamp=timestamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting gateway {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start gateway: {str(e)}"
        )


@router.post(
    "/{account_id}/stop",
    response_model=GatewayControlResponse,
    summary="Stop gateway",
    description="Stop a gateway for the specified account",
    responses={
        200: {
            "description": "Gateway stop initiated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Gateway stop initiated successfully",
                        "gateway_id": "ctp_main_account",
                        "action": "stop",
                        "timestamp": "2025-06-25T10:30:45.123Z"
                    }
                }
            }
        },
        400: {"description": "Invalid request or gateway already stopped"},
        404: {"description": "Account not found"},
        500: {"description": "Internal server error"}
    }
)
async def stop_gateway(
    account_id: str,
    gw_manager = Depends(get_gateway_manager)
) -> GatewayControlResponse:
    """
    Stop a gateway for the specified account.
    
    Args:
        account_id: Unique identifier of the account/gateway to stop
        
    Returns:
        Gateway control response with action result
        
    Raises:
        HTTPException: For validation errors, not found, or server issues
    """
    try:
        logger.info("Stopping gateway", )
        
        # Call gateway manager to stop the gateway
        result = await gw_manager.stop_gateway(account_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to stop gateway for account '{account_id}'. Gateway may already be stopped or account not found."
            )
        
        # Broadcast control action via WebSocket
        ws_manager = WebSocketManager.get_instance()
        await ws_manager.broadcast_gateway_control_action(
            gateway_id=account_id,
            action="stop",
            status="completed",
            message="Gateway stopped successfully"
        )
        
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info("Gateway stopped successfully", )
        
        return GatewayControlResponse(
            success=True,
            message="Gateway stopped successfully",
            gateway_id=account_id,
            action="stop",
            timestamp=timestamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error stopping gateway",  error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop gateway: {str(e)}"
        )


@router.post(
    "/{account_id}/restart",
    response_model=GatewayControlResponse,
    summary="Restart gateway",
    description="Restart a gateway for the specified account",
    responses={
        200: {
            "description": "Gateway restart initiated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Gateway restart initiated successfully",
                        "gateway_id": "ctp_main_account",
                        "action": "restart",
                        "timestamp": "2025-06-25T10:30:45.123Z"
                    }
                }
            }
        },
        400: {"description": "Invalid request"},
        404: {"description": "Account not found"},
        500: {"description": "Internal server error"}
    }
)
async def restart_gateway(
    account_id: str,
    gw_manager = Depends(get_gateway_manager)
) -> GatewayControlResponse:
    """
    Restart a gateway for the specified account.
    
    Args:
        account_id: Unique identifier of the account/gateway to restart
        
    Returns:
        Gateway control response with action result
        
    Raises:
        HTTPException: For validation errors, not found, or server issues
    """
    try:
        logger.info("Restarting gateway", )
        
        # Call gateway manager to restart the gateway
        result = await gw_manager.restart_gateway(account_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to restart gateway for account '{account_id}'. Account may not exist or gateway service unavailable."
            )
        
        # Broadcast control action via WebSocket
        ws_manager = WebSocketManager.get_instance()
        await ws_manager.broadcast_gateway_control_action(
            gateway_id=account_id,
            action="restart",
            status="completed",
            message="Gateway restarted successfully"
        )
        
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info("Gateway restarted successfully", )
        
        return GatewayControlResponse(
            success=True,
            message="Gateway restarted successfully",
            gateway_id=account_id,
            action="restart",
            timestamp=timestamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error restarting gateway",  error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart gateway: {str(e)}"
        )