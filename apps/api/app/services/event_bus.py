"""
Internal event bus system for decoupled communication.
Uses asyncio for lightweight, high-performance event handling.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Callable, Any, Optional
from collections import defaultdict
import structlog

from app.models.health_status import HealthStatusEvent


class EventBus:
    """
    Lightweight asyncio-based event bus for internal communication.
    Supports publisher/subscriber pattern with type-safe event handling.
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._running = False
        self._event_count = 0
        
    async def start(self):
        """Start the event bus processing."""
        if self._running:
            return
            
        self._running = True
        self._processing_task = asyncio.create_task(self._process_events())
        self.logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event bus processing."""
        if not self._running:
            return
            
        self._running = False
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
                
        self.logger.info(
            "Event bus stopped",
            total_events_processed=self._event_count
        )
    
    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of events to subscribe to
            handler: Callback function to handle events
        """
        self._subscribers[event_type].append(handler)
        self.logger.info(
            "Event subscription added",
            event_type=event_type,
            handler=handler.__name__,
            total_subscribers=len(self._subscribers[event_type])
        )
    
    def unsubscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """
        Unsubscribe from events of a specific type.
        
        Args:
            event_type: Type of events to unsubscribe from
            handler: Callback function to remove
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                self.logger.info(
                    "Event subscription removed",
                    event_type=event_type,
                    handler=handler.__name__
                )
            except ValueError:
                self.logger.warning(
                    "Handler not found for unsubscribe",
                    event_type=event_type,
                    handler=handler.__name__
                )
    
    async def publish(self, event_type: str, event_data: Dict[str, Any]):
        """
        Publish an event to the bus.
        
        Args:
            event_type: Type of event being published
            event_data: Event data dictionary
        """
        if not self._running:
            self.logger.warning(
                "Event bus not running, event dropped",
                event_type=event_type
            )
            return
            
        event = {
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await self._event_queue.put(event)
            self.logger.debug(
                "Event published",
                event_type=event_type,
                queue_size=self._event_queue.qsize()
            )
        except Exception as e:
            self.logger.error(
                "Failed to publish event",
                event_type=event_type,
                error=str(e)
            )
    
    async def publish_health_status_change(self, health_event: HealthStatusEvent):
        """
        Publish a health status change event.
        
        Args:
            health_event: HealthStatusEvent instance
        """
        await self.publish("gateway_status_change", health_event.to_dict())
    
    async def _process_events(self):
        """Process events from the queue and dispatch to subscribers."""
        while self._running:
            try:
                # Wait for events with a timeout to allow clean shutdown
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._dispatch_event(event)
                self._event_count += 1
                
            except asyncio.TimeoutError:
                # Normal timeout, continue processing
                continue
            except asyncio.CancelledError:
                # Task cancelled during shutdown
                break
            except Exception as e:
                self.logger.error(
                    "Event processing error",
                    error=str(e)
                )
    
    async def _dispatch_event(self, event: Dict[str, Any]):
        """
        Dispatch event to all subscribers.
        
        Args:
            event: Event dictionary with type, data, and timestamp
        """
        event_type = event.get("type")
        event_data = event.get("data", {})
        
        if event_type not in self._subscribers:
            self.logger.debug(
                "No subscribers for event type",
                event_type=event_type
            )
            return
            
        subscribers = self._subscribers[event_type].copy()
        
        for handler in subscribers:
            try:
                # Handle both sync and async handlers
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
                    
            except Exception as e:
                self.logger.error(
                    "Event handler error",
                    event_type=event_type,
                    handler=handler.__name__,
                    error=str(e)
                )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            "running": self._running,
            "total_events_processed": self._event_count,
            "queue_size": self._event_queue.qsize(),
            "subscriber_count": {
                event_type: len(handlers)
                for event_type, handlers in self._subscribers.items()
            }
        }


# Global event bus instance
event_bus = EventBus()