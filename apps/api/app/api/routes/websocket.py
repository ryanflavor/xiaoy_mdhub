"""WebSocket endpoint for real-time communication with frontend."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import json
from typing import Optional

from app.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)


async def validate_websocket_auth(websocket: WebSocket) -> bool:
    """Validate WebSocket connection authentication."""
    # Check for token in query params or headers
    token = websocket.query_params.get("token")
    if not token:
        # Try to get from headers
        auth_header = websocket.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    # TODO: Implement actual token validation per NFR8
    # For development environment, allow connections without token
    import os
    if os.getenv("ENVIRONMENT", "development") == "development":
        return True
    
    # For production, require token
    return bool(token)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    manager: WebSocketManager = Depends(lambda: WebSocketManager.get_instance())
):
    """
    WebSocket endpoint for real-time communication.
    
    Supports:
    - Gateway status updates
    - System log streaming
    - Health status broadcasts
    """
    # Validate authentication
    if not await validate_websocket_auth(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        logger.warning("WebSocket connection rejected: unauthorized")
        return
    
    # Accept connection
    await websocket.accept()
    client_id = await manager.connect(websocket)
    logger.info(f"WebSocket client connected: {client_id}")
    
    try:
        # Send initial connection success message
        await websocket.send_json({
            "event_type": "connection",
            "status": "connected",
            "client_id": client_id,
            "message": "WebSocket connection established"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    # Respond to ping with pong
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    })
                elif message.get("type") == "pong":
                    # Update client health on pong response
                    manager.update_client_health(client_id)
                else:
                    # Log unhandled message types
                    logger.debug(f"Received unhandled message type: {message.get('type')}")
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from client {client_id}")
                await websocket.send_json({
                    "event_type": "error",
                    "message": "Invalid JSON format"
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {str(e)}")
    finally:
        # Clean up connection
        await manager.disconnect(client_id)