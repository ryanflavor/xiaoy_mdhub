"""
ZeroMQ Publisher Service for market data distribution.
Handles tick data publishing with msgpack serialization and topic-based routing.
"""
import logging
import time
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import structlog
import zmq
import msgpack
import os

# ZMQ Configuration moved from CTP config to environment variables
ZMQ_SETTINGS = {
    "port": int(os.getenv("ZMQ_PUBLISHER_PORT", "5555")),
    "bind_address": os.getenv("ZMQ_BIND_ADDRESS", "tcp://*"),
    "queue_size": int(os.getenv("ZMQ_QUEUE_SIZE", "1000")),
    "enabled": os.getenv("ENABLE_ZMQ_PUBLISHER", "true").lower() == "true"
}
from app.config.performance_thresholds import (
    get_performance_config, 
    validate_performance_metric,
    get_environment_config
)


class ZMQPublisher:
    """
    ZeroMQ publisher for distributing tick data to downstream clients.
    Provides high-speed, low-latency messaging with topic-based subscription.
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self.context: Optional[zmq.Context] = None
        self.socket: Optional[zmq.Socket] = None
        self.is_running = False
        self.is_connected = False
        
        # Performance monitoring
        self.publish_count = 0
        self.serialization_times = []
        self.last_performance_log = time.time()
        self.performance_log_interval = 30  # seconds
        
        # Performance validation
        self.performance_config = get_performance_config()
        self.environment_config = get_environment_config()
        self.performance_alerts = []
        self.last_threshold_check = time.time()
        self.threshold_check_interval = 60  # Check thresholds every minute
        
        # Configuration
        self.port = ZMQ_SETTINGS["port"]
        self.bind_address = ZMQ_SETTINGS["bind_address"]
        self.queue_size = ZMQ_SETTINGS["queue_size"]
        self.enabled = ZMQ_SETTINGS["enabled"]
        
        # Thread safety
        self._lock = threading.RLock()
    
    async def initialize(self) -> bool:
        """
        Initialize ZeroMQ publisher and bind to configured port.
        Returns True if initialization successful, False otherwise.
        """
        if not self.enabled:
            self.logger.info("ZMQ Publisher disabled via ENABLE_ZMQ_PUBLISHER environment variable")
            return False
        
        try:
            with self._lock:
                self.logger.info(
                    "ZMQ Publisher starting...",
                    port=self.port,
                    bind_address=self.bind_address,
                    queue_size=self.queue_size
                )
                
                # Create ZMQ context
                self.context = zmq.Context()
                
                # Create PUB socket
                self.socket = self.context.socket(zmq.PUB)
                
                # Set socket options
                self.socket.set(zmq.SNDHWM, self.queue_size)  # High water mark
                self.socket.set(zmq.LINGER, 1000)  # Linger time for graceful shutdown
                
                # Bind to address
                bind_addr = f"{self.bind_address}:{self.port}"
                self.socket.bind(bind_addr)
                
                self.is_running = True
                self.is_connected = True
                
                self.logger.info(
                    "ZMQ Publisher started successfully",
                    bind_address=bind_addr,
                    socket_type="PUB",
                    timestamp=datetime.now().isoformat()
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "ZMQ Publisher initialization failed",
                error=str(e),
                port=self.port,
                bind_address=self.bind_address
            )
            await self._cleanup()
            return False
    
    def publish_tick(self, tick_data: Any) -> bool:
        """
        Publish tick data with topic-based routing and performance monitoring.
        
        Args:
            tick_data: Tick data object with vt_symbol attribute
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self.is_running or not self.socket:
            self.logger.warning("ZMQ Publisher not running, skipping tick publication")
            return False
        
        try:
            with self._lock:
                start_time = time.time()
                
                # Extract topic from vt_symbol
                topic = getattr(tick_data, 'symbol', 'unknown')
                if hasattr(tick_data, 'vt_symbol'):
                    topic = tick_data.vt_symbol
                elif hasattr(tick_data, 'symbol'):
                    topic = tick_data.symbol
                
                # Serialize tick data using msgpack
                tick_dict = self._serialize_tick_data(tick_data)
                message = msgpack.packb(tick_dict)
                
                # Calculate serialization latency
                serialization_time = (time.time() - start_time) * 1000  # ms
                self.serialization_times.append(serialization_time)
                
                # Keep only last 100 serialization times for average calculation
                if len(self.serialization_times) > 100:
                    self.serialization_times = self.serialization_times[-100:]
                
                # Publish message with topic
                self.socket.send_multipart([
                    topic.encode('utf-8'),
                    message
                ])
                
                self.publish_count += 1
                
                # Log successful publication
                self.logger.debug(
                    "Tick published",
                    topic=topic,
                    serialization_time_ms=round(serialization_time, 2),
                    message_size_bytes=len(message),
                    publish_count=self.publish_count
                )
                
                # Periodic performance logging
                self._log_performance_metrics()
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Tick publication failed",
                error=str(e),
                topic=getattr(tick_data, 'symbol', 'unknown'),
                publish_count=self.publish_count
            )
            
            # Attempt to reconnect on failure
            self._handle_publish_failure()
            return False
    
    def _serialize_tick_data(self, tick_data: Any) -> Dict[str, Any]:
        """
        Serialize tick data to dictionary format for msgpack.
        
        Args:
            tick_data: Tick data object
            
        Returns:
            Dictionary representation of tick data
        """
        tick_dict = {}
        
        # Essential tick fields
        fields = [
            'symbol', 'datetime', 'last_price', 'volume', 'last_volume',
            'bid_price_1', 'ask_price_1', 'bid_volume_1', 'ask_volume_1'
        ]
        
        for field in fields:
            if hasattr(tick_data, field):
                value = getattr(tick_data, field)
                
                # Handle datetime serialization
                if field == 'datetime' and hasattr(value, 'isoformat'):
                    tick_dict[field] = value.isoformat()
                else:
                    tick_dict[field] = value
        
        # Add vt_symbol if available
        if hasattr(tick_data, 'vt_symbol'):
            tick_dict['vt_symbol'] = tick_data.vt_symbol
        
        # Add processing timestamp
        tick_dict['processing_time'] = datetime.now().isoformat()
        
        return tick_dict
    
    def _log_performance_metrics(self):
        """Log ZMQ publisher performance metrics with threshold validation."""
        current_time = time.time()
        
        if current_time - self.last_performance_log >= self.performance_log_interval:
            try:
                # Calculate performance metrics
                avg_serialization_time = 0.0
                p95_serialization_time = 0.0
                
                if self.serialization_times:
                    avg_serialization_time = sum(self.serialization_times) / len(self.serialization_times)
                    
                    # Calculate P95 serialization time
                    sorted_times = sorted(self.serialization_times)
                    p95_index = int(len(sorted_times) * 0.95)
                    p95_serialization_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
                
                # Calculate publication rate (messages per second)
                time_window = current_time - self.last_performance_log
                publication_rate_per_sec = (self.publish_count / time_window) if time_window > 0 else 0
                publication_rate_per_min = publication_rate_per_sec * 60
                
                # Get queue depth
                queue_depth = 0
                if self.socket:
                    try:
                        queue_depth = self.socket.get(zmq.SNDHWM) - self.socket.get(zmq.EVENTS)
                    except:
                        queue_depth = 0
                
                # Base performance log
                self.logger.info(
                    "ZMQ Publisher performance metrics",
                    total_published=self.publish_count,
                    publication_rate_per_minute=round(publication_rate_per_min, 2),
                    publication_rate_per_second=round(publication_rate_per_sec, 2),
                    avg_serialization_time_ms=round(avg_serialization_time, 2),
                    p95_serialization_time_ms=round(p95_serialization_time, 3),
                    queue_depth_estimate=queue_depth,
                    is_connected=self.is_connected
                )
                
                # Threshold validation
                self._validate_performance_thresholds(
                    p95_serialization_time, 
                    publication_rate_per_sec,
                    current_time
                )
                
                self.last_performance_log = current_time
                
            except Exception as e:
                self.logger.error("ZMQ performance metrics logging failed", error=str(e))
    
    def _validate_performance_thresholds(self, p95_latency_ms: float, pub_rate_per_sec: float, current_time: float):
        """Validate current performance against established thresholds."""
        if current_time - self.last_threshold_check < self.threshold_check_interval:
            return  # Skip if not time for threshold check
        
        try:
            # Validate serialization latency
            latency_result = validate_performance_metric('serialization_p95_latency_ms', p95_latency_ms)
            
            # Validate publication rate
            rate_result = validate_performance_metric('publication_rate_per_sec', pub_rate_per_sec)
            
            # Log threshold validation results
            if latency_result['alert_level'] != 'NONE' or rate_result['alert_level'] != 'NONE':
                self.logger.warning(
                    "Performance threshold validation",
                    serialization_status=latency_result['status'],
                    serialization_message=latency_result['message'],
                    publication_status=rate_result['status'], 
                    publication_message=rate_result['message'],
                    environment=self.environment_config['conda_environment']
                )
                
                # Track alerts
                alert_info = {
                    'timestamp': current_time,
                    'serialization': latency_result,
                    'publication_rate': rate_result
                }
                self.performance_alerts.append(alert_info)
                
                # Keep only last 10 alerts
                if len(self.performance_alerts) > 10:
                    self.performance_alerts = self.performance_alerts[-10:]
            
            elif latency_result['status'] == 'EXCELLENT' and rate_result['status'] == 'EXCELLENT':
                self.logger.info(
                    "Performance threshold validation - EXCELLENT",
                    serialization_p95_ms=round(p95_latency_ms, 3),
                    publication_rate_per_sec=round(pub_rate_per_sec, 1),
                    baseline_comparison="Exceeding baseline performance",
                    environment=self.environment_config['conda_environment']
                )
            
            self.last_threshold_check = current_time
            
        except Exception as e:
            self.logger.error("Performance threshold validation failed", error=str(e))
    
    def _handle_publish_failure(self):
        """Handle publication failure with basic retry logic."""
        if not self.is_connected:
            return  # Already handling disconnection
        
        self.logger.warning("ZMQ Publisher experiencing issues, attempting recovery")
        self.is_connected = False
        
        # Schedule reconnection attempt
        def delayed_reconnect():
            time.sleep(5)  # Wait 5 seconds before retry
            if self.is_running:
                self.logger.info("Attempting ZMQ Publisher reconnection")
                # In a real implementation, we might recreate the socket here
                # For MVP, we'll just mark as connected again
                self.is_connected = True
        
        threading.Thread(target=delayed_reconnect, daemon=True).start()
    
    async def shutdown(self):
        """Gracefully shutdown the ZMQ publisher."""
        try:
            with self._lock:
                self.logger.info("ZMQ Publisher shutting down", total_published=self.publish_count)
                
                self.is_running = False
                self.is_connected = False
                
                await self._cleanup()
                
                # Final performance summary
                avg_serialization_time = 0.0
                if self.serialization_times:
                    avg_serialization_time = sum(self.serialization_times) / len(self.serialization_times)
                
                self.logger.info(
                    "ZMQ Publisher shutdown complete",
                    final_publish_count=self.publish_count,
                    final_avg_serialization_time_ms=round(avg_serialization_time, 2)
                )
                
        except Exception as e:
            self.logger.error("ZMQ Publisher shutdown error", error=str(e))
    
    async def _cleanup(self):
        """Clean up ZMQ resources."""
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
            
            if self.context:
                self.context.term()
                self.context = None
                
        except Exception as e:
            self.logger.error("ZMQ cleanup error", error=str(e))
    
    async def start(self) -> bool:
        """Start the ZMQ publisher (alias for initialize for consistency)."""
        return await self.initialize()
    
    async def stop(self):
        """Stop the ZMQ publisher (alias for shutdown for consistency)."""
        await self.shutdown()


# Global ZMQ publisher instance
zmq_publisher = ZMQPublisher()