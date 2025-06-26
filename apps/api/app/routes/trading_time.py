"""
Trading Time API Routes.
Provides endpoints for querying trading time status and market hours.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import structlog

from app.services.trading_time_manager import trading_time_manager

router = APIRouter(prefix="/api/trading-time", tags=["trading-time"])
logger = structlog.get_logger(__name__)


@router.get("/status")
async def get_trading_time_status() -> Dict[str, Any]:
    """
    Get current trading time status and market information.
    
    Returns:
        Current trading status including:
        - Current date/time
        - Trading day status
        - Current trading session info
        - Next session start time
        - Available trading sessions
    """
    try:
        status = trading_time_manager.get_trading_status()
        
        logger.debug(
            "Trading time status requested",
            status=status.get("status"),
            is_trading_time=status.get("is_trading_time"),
            current_session=status.get("current_session_name")
        )
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        logger.error(
            "Failed to get trading time status",
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trading time status: {str(e)}"
        )


@router.get("/is-trading-time")
async def is_trading_time(gateway_type: str = "CTP") -> Dict[str, Any]:
    """
    Check if current time is within trading hours for specific gateway.
    
    Args:
        gateway_type: Gateway type ('CTP' or 'SOPT')
        
    Returns:
        Boolean result indicating if trading time is active
    """
    try:
        if gateway_type not in ["CTP", "SOPT"]:
            raise HTTPException(
                status_code=400,
                detail="Gateway type must be 'CTP' or 'SOPT'"
            )
        
        is_trading = trading_time_manager.is_trading_time(gateway_type)
        
        logger.debug(
            "Trading time check requested",
            gateway_type=gateway_type,
            is_trading=is_trading
        )
        
        return {
            "success": True,
            "data": {
                "gateway_type": gateway_type,
                "is_trading_time": is_trading,
                "current_time": trading_time_manager.get_trading_status()["current_time"]
            }
        }
        
    except Exception as e:
        logger.error(
            "Failed to check trading time",
            gateway_type=gateway_type,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check trading time: {str(e)}"
        )


@router.get("/config")
async def get_trading_time_config() -> Dict[str, Any]:
    """
    Get current trading time configuration.
    
    Returns:
        Trading time configuration including:
        - Time check enabled status
        - Force connection mode
        - Buffer minutes
        - Trading sessions
    """
    try:
        config = {
            "enable_trading_time_check": trading_time_manager.enable_trading_time_check,
            "force_gateway_connection": trading_time_manager.force_gateway_connection,
            "buffer_minutes": trading_time_manager.buffer_minutes,
            "sessions": [
                {
                    "name": session.name,
                    "market_type": session.market_type,
                    "ranges": [
                        {
                            "start": range_.start.strftime("%H:%M"),
                            "end": range_.end.strftime("%H:%M"),
                            "is_overnight": range_.is_overnight
                        }
                        for range_ in session.ranges
                    ]
                }
                for session in trading_time_manager.sessions
            ]
        }
        
        logger.debug(
            "Trading time config requested",
            enable_check=config["enable_trading_time_check"],
            force_connection=config["force_gateway_connection"]
        )
        
        return {
            "success": True,
            "data": config
        }
        
    except Exception as e:
        logger.error(
            "Failed to get trading time config",
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trading time config: {str(e)}"
        )