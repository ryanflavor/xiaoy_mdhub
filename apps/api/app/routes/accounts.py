"""
Account management REST API endpoints.

This module provides CRUD operations for MarketDataAccount entities through
REST API endpoints with proper validation, error handling, and OpenAPI documentation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_serializer
import structlog

# Import timezone utilities
from app.utils.timezone import now_china, to_china_tz, CHINA_TZ

from ..services.database_service import database_service
from ..models.market_data_account import MarketDataAccount
from ..services.gateway_manager import gateway_manager
from ..services.websocket_manager import WebSocketManager
from ..services.account_validation_service import account_validation_service

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


class ConnectSetting(BaseModel):
    """Connection settings for trading gateways."""
    # Common connection fields
    交易服务器: Optional[str] = Field(None, description="Trading server address")
    行情服务器: Optional[str] = Field(None, description="Market data server address")
    用户名: Optional[str] = Field(None, description="Username for authentication")
    密码: Optional[str] = Field(None, description="Password for authentication")
    经纪商代码: Optional[str] = Field(None, description="Broker ID")
    授权编码: Optional[str] = Field(None, description="Authorization code")
    产品信息: Optional[str] = Field(None, description="Product information")
    产品名称: Optional[str] = Field(None, description="Product name")
    
    # Legacy English field support for backward compatibility
    userID: Optional[str] = Field(None, description="User ID for CTP authentication")
    password: Optional[str] = Field(None, description="Password for CTP authentication")
    brokerID: Optional[str] = Field(None, description="Broker ID for CTP connection")
    authCode: Optional[str] = Field(None, description="Authentication code for CTP")
    appID: Optional[str] = Field(None, description="Application ID for CTP")
    mdAddress: Optional[str] = Field(None, description="Market data server address for CTP")
    tdAddress: Optional[str] = Field(None, description="Trading server address for CTP")
    username: Optional[str] = Field(None, description="Username for SOPT authentication")
    token: Optional[str] = Field(None, description="Token for SOPT authentication")
    serverAddress: Optional[str] = Field(None, description="Server address for SOPT connection")
    timeout: Optional[int] = Field(None, ge=1, le=300, description="Connection timeout in seconds")

    class Config:
        extra = "allow"  # Allow additional fields for flexibility
        
    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """Custom serialization to exclude None values"""
        data = {}
        for field_name, field_value in self.__dict__.items():
            if field_value is not None:
                data[field_name] = field_value
        return data


class GatewayInfo(BaseModel):
    """Gateway information."""
    gateway_class: str = Field(..., description="Gateway class name (e.g., CtpGateway, SoptGateway)")
    gateway_name: str = Field(..., description="Gateway name (e.g., CTP, SOPT)")


class AccountSettings(BaseModel):
    """Pydantic model for complete account settings validation."""
    
    # New unified account format
    broker: Optional[str] = Field(None, description="Broker name")
    connect_setting: Optional[ConnectSetting] = Field(None, description="Connection settings")
    gateway: Optional[GatewayInfo] = Field(None, description="Gateway information")
    market: Optional[str] = Field(None, description="Market type (e.g., 期货期权, 个股期权)")
    name: Optional[str] = Field(None, description="Account name")
    
    # Legacy flat structure support for backward compatibility
    userID: Optional[str] = Field(None, description="User ID for CTP authentication")
    password: Optional[str] = Field(None, description="Password for CTP authentication")
    brokerID: Optional[str] = Field(None, description="Broker ID for CTP connection")
    authCode: Optional[str] = Field(None, description="Authentication code for CTP")
    appID: Optional[str] = Field(None, description="Application ID for CTP")
    mdAddress: Optional[str] = Field(None, description="Market data server address for CTP")
    tdAddress: Optional[str] = Field(None, description="Trading server address for CTP")
    username: Optional[str] = Field(None, description="Username for SOPT authentication")
    token: Optional[str] = Field(None, description="Token for SOPT authentication")
    serverAddress: Optional[str] = Field(None, description="Server address for SOPT connection")
    timeout: Optional[int] = Field(None, ge=1, le=300, description="Connection timeout in seconds")

    class Config:
        extra = "allow"  # Allow additional fields for flexibility
        
    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """Custom serialization to exclude None values"""
        data = {}
        for field_name, field_value in self.__dict__.items():
            if field_value is not None:
                data[field_name] = field_value
        return data


class AccountRequest(BaseModel):
    """Request model for creating/updating accounts."""
    
    id: str = Field(..., min_length=1, max_length=100, description="Unique account identifier")
    gateway_type: str = Field(..., description="Gateway type (ctp or sopt)")
    settings: AccountSettings = Field(..., description="Gateway-specific configuration settings")
    priority: int = Field(1, ge=1, le=100, description="Priority level (lower = higher priority)")
    is_enabled: bool = Field(True, description="Whether the account should be enabled")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    validate_connection: bool = Field(True, description="Whether to validate connection before creating account")
    allow_non_trading_validation: bool = Field(False, description="Allow validation outside trading hours")
    use_real_api_validation: bool = Field(False, description="Use real vnpy gateway API login validation instead of basic connectivity test")
    
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
                        "description": "Primary CTP account",
                        "validate_connection": True,
                        "allow_non_trading_validation": False
                    }
                }
            }
        },
        400: {"description": "Validation error, connection validation failed, or invalid data"},
        409: {"description": "Account with this ID already exists"},
        423: {"description": "Validation locked due to non-trading hours"},
        503: {"description": "Database service unavailable"}
    }
)
async def create_account(
    account_data: AccountRequest = Body(..., description="Account configuration data"),
    db_service = Depends(get_database_service)
) -> AccountResponse:
    """
    Create a new market data account with optional connection validation.
    
    Args:
        account_data: Account configuration including gateway type, settings, and metadata
        
    Returns:
        Created account data with timestamps
        
    Raises:
        HTTPException: For validation errors, duplicates, connection failures, or database issues
    """
    try:
        logger.info("Creating new account", account_id=account_data.id, gateway_type=account_data.gateway_type, 
                   validate_connection=account_data.validate_connection)
        
        # Perform connection validation if requested
        if account_data.validate_connection:
            logger.info("Validating account connection before creation", account_id=account_data.id)
            
            # Perform validation with enhanced settings
            validation_result = await account_validation_service.validate_account(
                account_id=account_data.id,
                account_settings=account_data.settings.model_dump(),
                gateway_type=account_data.gateway_type,
                timeout_seconds=30,
                allow_non_trading_validation=account_data.allow_non_trading_validation,
                use_real_api_validation=account_data.use_real_api_validation
            )
            
            # Handle validation failure
            if not validation_result.success:
                error_code = validation_result.details.get("error_code", "VALIDATION_FAILED")
                
                # Special handling for non-trading hours
                if error_code == "NON_TRADING_HOURS" and not account_data.allow_non_trading_validation:
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail={
                            "error": "NON_TRADING_HOURS",
                            "message": validation_result.message,
                            "trading_status": validation_result.details.get("trading_status"),
                            "user_message": "Account validation is only available during trading hours",
                            "recommendation": "Try again during trading hours or set 'allow_non_trading_validation' to true for basic connectivity testing",
                            "details": validation_result.details
                        }
                    )
                elif error_code == "NON_TRADING_HOURS" and account_data.allow_non_trading_validation:
                    # Perform basic connectivity validation outside trading hours
                    logger.info("Performing basic connectivity validation outside trading hours", account_id=account_data.id)
                    # Continue with creation since user explicitly allowed non-trading validation
                else:
                    # Other validation failures
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error": "VALIDATION_FAILED",
                            "message": validation_result.message,
                            "validation_details": validation_result.details,
                            "user_message": f"Account validation failed: {validation_result.message}",
                            "recommendation": "Please check your account settings and try again"
                        }
                    )
            
            logger.info("Account validation successful", account_id=account_data.id, 
                       validation_message=validation_result.message)
        else:
            logger.info("Skipping connection validation as requested", account_id=account_data.id)
        
        # Convert Pydantic model to dict for database service
        account_dict = account_data.model_dump()
        # Remove validation-specific fields that shouldn't be stored
        account_dict.pop('validate_connection', None)
        account_dict.pop('allow_non_trading_validation', None)
        account_dict.pop('use_real_api_validation', None)
        
        # Create account using database service
        created_account = await db_service.create_account(account_dict)
        
        if created_account is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service is not available"
            )
        
        logger.info("Account created successfully", account_id=created_account.id)
        return account_to_response(created_account)
        
    except HTTPException:
        # Re-raise HTTP exceptions (they're already properly formatted)
        raise
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
        logger.info("Deleting account", account_id=account_id)
        
        # Delete account using database service
        deleted = await db_service.delete_account(account_id)
        
        if not deleted:
            logger.warning("Account not found for deletion", account_id=account_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with ID '{account_id}' not found"
            )
        
        logger.info("Account deleted successfully", account_id=account_id)
        return None  # FastAPI will return 204 No Content
        
    except HTTPException:
        # Re-raise HTTP exceptions (they're already properly formatted)
        raise
    except Exception as e:
        logger.error("Error deleting account", account_id=account_id, error=str(e))
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
        
        timestamp = now_china().isoformat()
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
        
        timestamp = now_china().isoformat()
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
        
        timestamp = now_china().isoformat()
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


@router.post(
    "/resubscribe-canary",
    response_model=Dict[str, Any],
    summary="Resubscribe canary contracts",
    description="Manually trigger subscription for canary contracts on all connected accounts",
    responses={
        200: {"description": "Canary contracts resubscribed successfully"},
        500: {"description": "Internal server error"}
    }
)
async def resubscribe_canary_contracts():
    """
    Manually trigger subscription for canary contracts on all connected accounts.
    
    This endpoint is useful when connections are already established but subscriptions
    need to be refreshed, especially after configuration changes.
    """
    try:
        logger.info("Manual canary contract resubscription requested")
        
        # Trigger resubscription via gateway manager
        gateway_manager.resubscribe_canary_contracts()
        
        timestamp = now_china().isoformat()
        logger.info("Canary contracts resubscribed successfully")
        
        return {
            "success": True,
            "message": "Canary contracts resubscribed successfully",
            "action": "resubscribe_canary",
            "timestamp": timestamp,
            "connected_accounts": list(gateway_manager.gateway_connections.keys())
        }
        
    except Exception as e:
        logger.error("Error resubscribing canary contracts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resubscribe canary contracts: {str(e)}"
        )


class AccountValidationRequest(BaseModel):
    """Request model for account validation."""
    
    account_id: str = Field(..., description="Account identifier for validation")
    gateway_type: str = Field(..., description="Gateway type (ctp or sopt)")
    settings: AccountSettings = Field(..., description="Account settings to validate")
    timeout_seconds: int = Field(30, ge=5, le=60, description="Validation timeout in seconds")
    allow_non_trading_validation: bool = Field(False, description="Allow validation outside trading hours")
    use_real_api_validation: bool = Field(False, description="Use real API validation instead of basic connectivity")
    
    @field_validator('gateway_type')
    @classmethod
    def validate_gateway_type(cls, v):
        v_lower = v.lower()
        if v_lower not in ['ctp', 'sopt']:
            raise ValueError('Gateway type must be either "ctp" or "sopt" (case insensitive)')
        return v_lower


class AccountValidationResponse(BaseModel):
    """Response model for account validation."""
    
    success: bool = Field(..., description="Whether validation was successful")
    message: str = Field(..., description="Validation result message")
    account_id: str = Field(..., description="Account identifier")
    gateway_type: str = Field(..., description="Gateway type")
    timestamp: str = Field(..., description="Validation timestamp")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional validation details")


@router.post(
    "/validate",
    response_model=AccountValidationResponse,
    summary="Validate account credentials",
    description="Validate account credentials by attempting actual login during trading hours",
    responses={
        200: {
            "description": "Validation completed (check success field for result)",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Account validation successful",
                        "account_id": "test_account",
                        "gateway_type": "ctp",
                        "timestamp": "2025-06-27T10:30:45.123Z",
                        "details": {"validation_time": "2025-06-27T10:30:45.123Z"}
                    }
                }
            }
        },
        400: {"description": "Invalid request or non-trading hours"},
        500: {"description": "Internal server error"}
    }
)
async def validate_account(
    validation_request: AccountValidationRequest = Body(..., description="Account validation data")
) -> AccountValidationResponse:
    """
    Validate account credentials by attempting actual login.
    
    This endpoint attempts to connect to the trading gateway using the provided
    credentials and returns the result. Validation is only performed during
    trading hours to avoid unnecessary connections.
    
    Args:
        validation_request: Account validation configuration
        
    Returns:
        Validation result with success status and details
        
    Raises:
        HTTPException: For invalid requests or server errors
    """
    try:
        logger.info("Account validation requested", 
                   account_id=validation_request.account_id,
                   gateway_type=validation_request.gateway_type)
        
        # Perform validation
        result = await account_validation_service.validate_account(
            account_id=validation_request.account_id,
            account_settings=validation_request.settings.model_dump(),
            gateway_type=validation_request.gateway_type,
            timeout_seconds=validation_request.timeout_seconds,
            allow_non_trading_validation=validation_request.allow_non_trading_validation,
            use_real_api_validation=validation_request.use_real_api_validation
        )
        
        # Return structured response
        return AccountValidationResponse(
            success=result.success,
            message=result.message,
            account_id=validation_request.account_id,
            gateway_type=validation_request.gateway_type,
            timestamp=result.timestamp.isoformat(),
            details=result.details
        )
        
    except Exception as e:
        logger.error("Account validation error", 
                    account_id=validation_request.account_id, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account validation failed: {str(e)}"
        )

