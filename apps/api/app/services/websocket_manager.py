"""WebSocket connection manager for handling multiple client connections."""

import asyncio
import uuid
from typing import Dict, Set, Optional, Any, List
from fastapi import WebSocket
import logging
import json
from datetime import datetime, timezone
from collections import deque

from app.services.event_bus import event_bus

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts messages to connected clients."""
    
    _instance: Optional['WebSocketManager'] = None
    
    def __new__(cls) -> 'WebSocketManager':
        """Ensure singleton pattern with proper initialization."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def __init__(self):
        """Initialize called by standard instantiation - no-op for singleton."""
        pass
        
    def _initialize(self):
        """Initialize the WebSocket manager attributes."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_health: Dict[str, datetime] = {}
        self._ping_interval = 30  # seconds
        self._ping_timeout = 10  # seconds
        self._ping_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Event filtering and rate limiting
        self._event_filters = {
            "gateway_status_change": self._filter_gateway_event,
            "gateway_recovery_status": self._filter_recovery_event,
            "system_log": self._filter_log_event
        }
        self._rate_limit_window = 1.0  # seconds
        self._rate_limit_max_events = 100
        self._event_buffer = deque(maxlen=1000)
        self._last_flush_time = datetime.now()
        
        # Log buffer for system logs
        self._log_buffer = deque(maxlen=500)
        self._log_levels = ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]
        
        # Subscribe to event bus
        self._setup_event_subscriptions()
        
    @classmethod
    def get_instance(cls) -> 'WebSocketManager':
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance for testing."""
        cls._instance = None
    
    async def force_flush_events(self) -> None:
        """Force flush event buffer for testing."""
        if self._event_buffer:
            events_to_send = list(self._event_buffer)
            self._event_buffer.clear()
            for event in events_to_send:
                await self.broadcast(event)
    
    async def connect(self, websocket: WebSocket) -> str:
        """
        Add a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to add
            
        Returns:
            The client ID assigned to this connection
        """
        client_id = str(uuid.uuid4())
        async with self._lock:
            self.active_connections[client_id] = websocket
            self.connection_health[client_id] = datetime.now()
            
        # Start ping monitoring if not already running
        if self._ping_task is None or self._ping_task.done():
            self._ping_task = asyncio.create_task(self._monitor_connections())
            
        logger.info(f"WebSocket connection added: {client_id}, total connections: {len(self.active_connections)}")
        return client_id
    
    async def disconnect(self, client_id: str) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            client_id: The client ID to disconnect
        """
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                del self.connection_health[client_id]
                logger.info(f"WebSocket connection removed: {client_id}, remaining connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict) -> None:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: The message dictionary to broadcast
        """
        if not self.active_connections:
            return
            
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
            
        disconnected_clients = []
        
        # Send to all clients
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {str(e)}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
    
    async def send_to_client(self, client_id: str, message: dict) -> bool:
        """
        Send a message to a specific client.
        
        Args:
            client_id: The client ID to send to
            message: The message dictionary to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        websocket = self.active_connections.get(client_id)
        if not websocket:
            return False
            
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {str(e)}")
            await self.disconnect(client_id)
            return False
    
    async def _monitor_connections(self) -> None:
        """Monitor connection health using ping/pong mechanism."""
        logger.info("Starting WebSocket connection health monitoring")
        
        while self.active_connections:
            try:
                # Sleep for ping interval
                await asyncio.sleep(self._ping_interval)
                
                current_time = datetime.now()
                disconnected_clients = []
                
                # Check each connection
                for client_id, websocket in list(self.active_connections.items()):
                    try:
                        # Check if connection is stale
                        last_seen = self.connection_health.get(client_id)
                        if last_seen and (current_time - last_seen).total_seconds() > (self._ping_interval + self._ping_timeout):
                            logger.warning(f"WebSocket client {client_id} failed to respond to ping")
                            disconnected_clients.append(client_id)
                            continue
                        
                        # Send ping
                        await websocket.send_json({
                            "type": "ping",
                            "timestamp": current_time.isoformat()
                        })
                        
                    except Exception as e:
                        logger.error(f"Error pinging client {client_id}: {str(e)}")
                        disconnected_clients.append(client_id)
                
                # Clean up disconnected clients
                for client_id in disconnected_clients:
                    await self.disconnect(client_id)
                    
            except Exception as e:
                logger.error(f"Error in connection monitoring: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
        
        logger.info("Stopping WebSocket connection health monitoring - no active connections")
    
    def update_client_health(self, client_id: str) -> None:
        """Update the last seen timestamp for a client."""
        if client_id in self.connection_health:
            self.connection_health[client_id] = datetime.now()
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all connections."""
        logger.info(f"Shutting down WebSocket manager with {len(self.active_connections)} active connections")
        
        # Cancel ping monitoring
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        shutdown_message = {
            "event_type": "shutdown",
            "message": "Server is shutting down"
        }
        
        for client_id in list(self.active_connections.keys()):
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(shutdown_message)
                await websocket.close()
            except Exception as e:
                logger.error(f"Error closing connection {client_id}: {str(e)}")
            finally:
                await self.disconnect(client_id)
        
        logger.info("WebSocket manager shutdown complete")
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_connection_info(self) -> Dict[str, dict]:
        """Get information about all active connections."""
        info = {}
        current_time = datetime.now()
        
        for client_id, _ in self.active_connections.items():
            last_seen = self.connection_health.get(client_id)
            info[client_id] = {
                "connected_since": last_seen.isoformat() if last_seen else None,
                "last_seen": last_seen.isoformat() if last_seen else None,
                "seconds_since_last_seen": (current_time - last_seen).total_seconds() if last_seen else None
            }
        
        return info
    
    def _setup_event_subscriptions(self) -> None:
        """Set up subscriptions to the event bus."""
        # Subscribe to gateway status events
        event_bus.subscribe("gateway_status_change", self._handle_gateway_event)
        event_bus.subscribe("gateway_recovery_status", self._handle_recovery_event)
        
        logger.info("WebSocket manager subscribed to event bus")
    
    async def _handle_gateway_event(self, event_data: Dict[str, Any]) -> None:
        """Handle gateway status change events."""
        try:
            # Transform internal event to client format
            client_event = {
                "event_type": "gateway_status_change",
                "timestamp": event_data.get("timestamp", datetime.now().isoformat()),
                "gateway_id": event_data.get("gateway_id"),
                "gateway_type": event_data.get("gateway_type"),
                "previous_status": event_data.get("previous_status"),
                "current_status": event_data.get("current_status"),
                "metadata": event_data.get("metadata", {})
            }
            
            # Apply rate limiting
            await self._rate_limited_broadcast(client_event)
            
        except Exception as e:
            logger.error(f"Error handling gateway event: {str(e)}")
    
    async def _handle_recovery_event(self, event_data: Dict[str, Any]) -> None:
        """Handle gateway recovery status events."""
        try:
            # Transform internal event to client format
            client_event = {
                "event_type": "gateway_recovery_status",
                "timestamp": event_data.get("timestamp", datetime.now().isoformat()),
                "gateway_id": event_data.get("gateway_id"),
                "recovery_status": event_data.get("status"),
                "attempt": event_data.get("attempt"),
                "message": event_data.get("message"),
                "metadata": event_data.get("metadata", {})
            }
            
            # Apply rate limiting
            await self._rate_limited_broadcast(client_event)
            
        except Exception as e:
            logger.error(f"Error handling recovery event: {str(e)}")
    
    async def publish_log_event(self, level: str, message: str, source: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish a system log event to WebSocket clients.
        
        Args:
            level: Log level (INFO, WARN, ERROR, CRITICAL)
            message: Log message
            source: Source component
            metadata: Additional metadata
        """
        if level not in self._log_levels:
            return
            
        log_event = {
            "event_type": "system_log",
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "source": source,
            "metadata": metadata or {}
        }
        
        # Add to log buffer
        self._log_buffer.append(log_event)
        
        # Broadcast to clients
        await self._rate_limited_broadcast(log_event)
    
    async def publish_canary_tick_update(self, gateway_id: str, contract_symbol: str, tick_count_1min: int, 
                                       last_tick_time: str, status: str, threshold_seconds: int) -> None:
        """
        Publish a canary tick update event to WebSocket clients.
        
        Args:
            gateway_id: Gateway identifier
            contract_symbol: Contract symbol
            tick_count_1min: Tick count in last minute
            last_tick_time: Last tick timestamp
            status: Canary status (ACTIVE, STALE, INACTIVE)
            threshold_seconds: Heartbeat threshold in seconds
        """
        canary_event = {
            "event_type": "canary_tick_update",
            "timestamp": datetime.now().isoformat(),
            "gateway_id": gateway_id,
            "contract_symbol": contract_symbol,
            "tick_count_1min": tick_count_1min,
            "last_tick_time": last_tick_time,
            "status": status,
            "threshold_seconds": threshold_seconds
        }
        
        # Broadcast to clients (no rate limiting for canary updates - they're important)
        await self.broadcast(canary_event)
    
    async def _rate_limited_broadcast(self, event: Dict[str, Any]) -> None:
        """Apply rate limiting to event broadcasts."""
        current_time = datetime.now()
        
        # Add event to buffer
        self._event_buffer.append(event)
        
        # Check if we should flush the buffer
        time_since_flush = (current_time - self._last_flush_time).total_seconds()
        
        if time_since_flush >= self._rate_limit_window or len(self._event_buffer) >= self._rate_limit_max_events:
            # Flush events
            events_to_send = list(self._event_buffer)[:self._rate_limit_max_events]
            self._event_buffer.clear()
            self._last_flush_time = current_time
            
            # Broadcast each event
            for event in events_to_send:
                await self.broadcast(event)
    
    def _filter_gateway_event(self, event_data: Dict[str, Any]) -> bool:
        """Filter gateway status events."""
        # For now, forward all gateway events
        return True
    
    def _filter_recovery_event(self, event_data: Dict[str, Any]) -> bool:
        """Filter recovery status events."""
        # For now, forward all recovery events
        return True
    
    def _filter_log_event(self, event_data: Dict[str, Any]) -> bool:
        """Filter log events based on level."""
        level = event_data.get("level", "INFO")
        return level in self._log_levels
    
    async def broadcast_gateway_control_action(
        self, 
        gateway_id: str, 
        action: str, 
        status: str, 
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Broadcast gateway control action event to WebSocket clients.
        
        Args:
            gateway_id: Gateway identifier
            action: Control action (start, stop, restart)
            status: Action status (initiated, completed, failed)
            message: Action result message
            metadata: Additional metadata
        """
        try:
            control_event = {
                "event_type": "gateway_control_action",
                "timestamp": datetime.now().isoformat(),
                "gateway_id": gateway_id,
                "action": action,
                "status": status,
                "message": message,
                "metadata": metadata or {}
            }
            
            # Broadcast to all connected clients
            await self.broadcast(control_event)
            
            logger.info(f"Gateway control action broadcasted: {action} - {status}")
            
        except Exception as e:
            logger.error(f"Error broadcasting gateway control action {action}: {str(e)}")
    
    def get_log_buffer(self) -> List[Dict[str, Any]]:
        """
        Get the current log buffer contents.
        
        Returns:
            List of log entries from the buffer
        """
        return list(self._log_buffer)