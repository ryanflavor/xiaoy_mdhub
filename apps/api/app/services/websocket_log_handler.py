"""Custom logging handler for broadcasting logs via WebSocket."""

import logging
import asyncio
from typing import Optional
from datetime import datetime, timezone

from app.services.websocket_manager import WebSocketManager


class WebSocketLogHandler(logging.Handler):
    """
    Custom logging handler that broadcasts log messages via WebSocket.
    Filters logs by level and prevents recursive logging from WebSocket components.
    """
    
    def __init__(self, level=logging.INFO):
        """
        Initialize the WebSocket log handler.
        
        Args:
            level: Minimum log level to broadcast
        """
        super().__init__(level)
        self._websocket_manager: Optional[WebSocketManager] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Prevent recursive logging from these modules
        self._excluded_loggers = {
            "app.services.websocket_manager",
            "app.api.routes.websocket",
            "websockets",
            "uvicorn.protocols.websockets"
        }
        
        # Map Python log levels to our system levels
        self._level_map = {
            logging.DEBUG: "DEBUG",
            logging.INFO: "INFO",
            logging.WARNING: "WARN",
            logging.ERROR: "ERROR",
            logging.CRITICAL: "CRITICAL"
        }
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record via WebSocket.
        
        Args:
            record: The log record to emit
        """
        try:
            # Skip logs from excluded modules to prevent recursion
            if any(record.name.startswith(excluded) for excluded in self._excluded_loggers):
                return
            
            # Skip if WebSocket manager not initialized
            if self._websocket_manager is None:
                self._websocket_manager = WebSocketManager.get_instance()
                
            if self._websocket_manager.get_connection_count() == 0:
                return
            
            # Get or create event loop
            try:
                if self._loop is None or self._loop.is_closed():
                    self._loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, skip
                return
            
            # Format the log message
            log_level = self._level_map.get(record.levelno, "INFO")
            
            # Only broadcast INFO, WARN, ERROR, CRITICAL levels (skip DEBUG for performance)
            if log_level not in ["INFO", "WARN", "ERROR", "CRITICAL"]:
                return
            
            # Extract source from logger name
            source = record.name.split('.')[-1] if record.name else "unknown"
            
            # Build metadata
            metadata = {
                "logger_name": record.name,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }
            
            # Add extra fields from structured logging if available
            if hasattr(record, 'extra'):
                metadata.update(record.extra)
            
            # Create coroutine for async broadcast
            coro = self._websocket_manager.publish_log_event(
                level=log_level,
                message=self.format(record),
                source=source,
                metadata=metadata
            )
            
            # Schedule the coroutine
            asyncio.create_task(coro)
            
        except Exception:
            # Silently fail to avoid breaking the logging system
            pass


def setup_websocket_logging():
    """Set up WebSocket log broadcasting."""
    # Create WebSocket handler
    ws_handler = WebSocketLogHandler(level=logging.INFO)
    
    # Use a simple formatter
    formatter = logging.Formatter('%(message)s')
    ws_handler.setFormatter(formatter)
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(ws_handler)
    
    # Also add to structlog logger
    structlog_logger = logging.getLogger("structlog")
    structlog_logger.addHandler(ws_handler)
    
    return ws_handler