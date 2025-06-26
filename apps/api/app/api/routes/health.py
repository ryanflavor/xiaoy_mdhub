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


class CanaryContractConfig(BaseModel):
    """Canary contract configuration model."""
    ctp_contracts: List[str]
    ctp_primary: str
    sopt_contracts: List[str] 
    sopt_primary: str
    heartbeat_timeout_seconds: int


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
    canary_config: Optional[CanaryContractConfig] = None


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
    
    # Get canary contract configuration from environment
    canary_config = None
    try:
        ctp_contracts_str = os.getenv("CTP_CANARY_CONTRACTS", "rb2601,AU2512")
        sopt_contracts_str = os.getenv("SOPT_CANARY_CONTRACTS", "510050,159915")
        
        canary_config = CanaryContractConfig(
            ctp_contracts=ctp_contracts_str.split(","),
            ctp_primary=os.getenv("CTP_CANARY_PRIMARY", "rb2601"),
            sopt_contracts=sopt_contracts_str.split(","),
            sopt_primary=os.getenv("SOPT_CANARY_PRIMARY", "510050"), 
            heartbeat_timeout_seconds=int(os.getenv("CANARY_HEARTBEAT_TIMEOUT_SECONDS", "60"))
        )
    except Exception as e:
        # Canary config not available, continue without it
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
        websocket_connections=websocket_status,
        canary_config=canary_config
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


@router.post("/test-canary")
async def test_canary():
    """
    Manually trigger canary tick data for testing.
    
    Returns:
        Status of the test canary tick injection
    """
    try:
        current_time = datetime.now(timezone.utc)
        
        # Simulate tick data for canary contracts
        test_results = []
        canary_contracts = ["rb2501", "au2506"]
        
        for contract in canary_contracts:
            health_monitor.update_canary_tick(
                gateway_id="test-gateway",
                contract=contract, 
                timestamp=current_time,
                tick_data=None
            )
            test_results.append({
                "contract": contract,
                "timestamp": current_time.isoformat(),
                "status": "injected"
            })
        
        return {
            "status": "success",
            "message": "Test canary tick data injected",
            "test_results": test_results,
            "timestamp": current_time.isoformat()
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }