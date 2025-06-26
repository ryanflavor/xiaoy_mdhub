"""
Health check endpoint for Market Data Hub API.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.gateway_manager import gateway_manager
from app.services.database_service import database_service
from app.services.health_monitor import health_monitor
from app.services.quote_aggregation_engine import quote_aggregation_engine
from app.services.gateway_recovery_service import gateway_recovery_service
from app.services.websocket_manager import WebSocketManager

router = APIRouter()


class AccountStatus(BaseModel):
    """Account status model."""
    id: str
    gateway_type: str
    priority: int
    connected: bool
    connection_attempts: int
    connection_duration: float


class GatewayManagerStatus(BaseModel):
    """Gateway manager status model."""
    total_accounts: int
    connected_accounts: int
    accounts: List[AccountStatus]


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    environment: str
    database_available: bool
    gateway_manager: Optional[GatewayManagerStatus] = None
    health_monitor: Optional[Dict[str, Any]] = None
    quote_aggregation_engine: Optional[Dict[str, Any]] = None
    gateway_recovery_service: Optional[Dict[str, Any]] = None
    websocket_connections: Optional[Dict[str, Any]] = None


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint that returns service status and metadata.
    
    Returns:
        HealthResponse: Service health status with metadata including gateway status
    """
    # Check database availability
    db_available = await database_service.is_available()
    
    # Get gateway manager status
    gateway_status = None
    try:
        status_data = gateway_manager.get_account_status()
        gateway_status = GatewayManagerStatus(
            total_accounts=status_data['total_accounts'],
            connected_accounts=status_data['connected_accounts'],
            accounts=[
                AccountStatus(**account_data) 
                for account_data in status_data['accounts']
            ]
        )
    except Exception as e:
        # Gateway manager status not available, continue without it
        pass
    
    # Get health monitor status
    health_monitor_status = None
    try:
        health_monitor_status = health_monitor.get_health_summary()
    except Exception as e:
        # Health monitor status not available, continue without it
        pass
    
    # Get quote aggregation engine status
    quote_aggregation_status = None
    try:
        quote_aggregation_status = quote_aggregation_engine.get_status()
    except Exception as e:
        # Quote aggregation engine status not available, continue without it
        pass
    
    # Get gateway recovery service status
    gateway_recovery_status = None
    try:
        gateway_recovery_status = gateway_recovery_service.get_recovery_status()
    except Exception as e:
        # Gateway recovery service status not available, continue without it
        pass
    
    # Get WebSocket connection status
    websocket_status = None
    try:
        ws_manager = WebSocketManager.get_instance()
        websocket_status = {
            "active_connections": ws_manager.get_connection_count(),
            "connection_details": ws_manager.get_connection_info()
        }
    except Exception as e:
        # WebSocket status not available, continue without it
        pass
    
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "development"),
        database_available=db_available,
        gateway_manager=gateway_status,
        health_monitor=health_monitor_status,
        quote_aggregation_engine=quote_aggregation_status,
        gateway_recovery_service=gateway_recovery_status,
        websocket_connections=websocket_status
    )


@router.get("/logs")
async def get_logs():
    """
    Get historical logs from WebSocket manager buffer.
    
    Returns:
        List of log entries from the WebSocket manager's log buffer
    """
    try:
        ws_manager = WebSocketManager.get_instance()
        logs = ws_manager.get_log_buffer()
        return {"logs": logs, "total": len(logs)}
    except Exception as e:
        return {"logs": [], "total": 0, "error": str(e)}