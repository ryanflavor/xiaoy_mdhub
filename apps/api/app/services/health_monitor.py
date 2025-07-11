"""
Health Monitoring Service for gateway status tracking and canary contract monitoring.
Provides real-time health assessment with configurable thresholds and event publishing.
"""

import asyncio
import os
import time
import psutil
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import structlog

# Import timezone utilities
from app.utils.timezone import now_china, to_china_tz, CHINA_TZ

from app.models.health_status import (
    GatewayStatus, 
    HealthMetrics, 
    GatewayHealthStatus, 
    HealthStatusEvent
)
from app.services.event_bus import event_bus
from app.services.gateway_manager import gateway_manager


class HealthMonitor:
    """
    Monitors health of all active gateways using multiple dimensions:
    - vnpy connection status monitoring
    - Canary contract heartbeat tracking  
    - Performance metrics collection
    - Automated status change detection with event publishing
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        
        # Configuration will be loaded during start()
        self.health_check_interval = 30
        self.health_check_timeout = 10
        self.canary_heartbeat_timeout = 60
        self.fallback_mode = "connection_only"
        # Canary contracts will be loaded from environment variables
        self.ctp_canary_contracts = []
        self.ctp_canary_primary = ""
        self.sopt_canary_contracts = [] 
        self.sopt_canary_primary = ""
        
        # Health status tracking
        self.gateway_health: Dict[str, GatewayHealthStatus] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.canary_tick_timestamps: Dict[str, datetime] = {}
        
        # Canary contract tick counting (key: f"{gateway_id}:{contract}", value: list of timestamps)
        self.canary_tick_counts: Dict[str, List[datetime]] = {}
        
        # Performance monitoring
        self.process = psutil.Process()
        self.start_time = time.time()
        self.health_check_count = 0
        self.last_resource_log = time.time()
        self.resource_log_interval = 300  # 5 minutes
        
        # Control flags
        self._running = False
    
    def _load_configuration(self):
        """Load configuration from environment variables."""
        self.health_check_interval = float(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "30"))
        self.health_check_timeout = int(os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "10"))
        self.canary_heartbeat_timeout = int(os.getenv("CANARY_HEARTBEAT_TIMEOUT_SECONDS", "60"))
        self.fallback_mode = os.getenv("HEALTH_CHECK_FALLBACK_MODE", "connection_only")
        
        # Canary contract configuration
        self.ctp_canary_contracts = os.getenv("CTP_CANARY_CONTRACTS", "rb2601,au2512").split(",")
        self.ctp_canary_primary = os.getenv("CTP_CANARY_PRIMARY", "rb2601")
        self.sopt_canary_contracts = os.getenv("SOPT_CANARY_CONTRACTS", "rb2601,au2512").split(",")
        self.sopt_canary_primary = os.getenv("SOPT_CANARY_PRIMARY", "rb2601")
        
    async def start(self) -> bool:
        """
        Start the health monitoring service.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self._running:
            self.logger.warning("Health monitor already running")
            return True
        
        # Load configuration from environment variables
        self._load_configuration()
            
        try:
            self.logger.info(
                "Starting health monitor",
                health_check_interval=self.health_check_interval,
                canary_heartbeat_timeout=self.canary_heartbeat_timeout,
                fallback_mode=self.fallback_mode
            )
            
            # Start event bus first
            await event_bus.start()
            
            # Initialize health status for all active gateways
            await self._initialize_gateway_health()
            
            # Start monitoring tasks for each gateway
            await self._start_monitoring_tasks()
            
            self._running = True
            
            self.logger.info(
                "Health monitor started successfully",
                monitored_gateways=len(self.gateway_health),
                active_monitoring_tasks=len(self.monitoring_tasks)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Health monitor startup failed",
                error=str(e)
            )
            return False
    
    async def stop(self):
        """Stop the health monitoring service."""
        if not self._running:
            return
            
        self.logger.info("Stopping health monitor")
        self._running = False
        
        # Cancel all monitoring tasks
        for gateway_id, task in self.monitoring_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(
                    "Error stopping monitoring task",
                    
                    error=str(e)
                )
        
        self.monitoring_tasks.clear()
        
        # Stop event bus
        await event_bus.stop()
        
        self.logger.info(
            "Health monitor stopped",
            total_health_checks=self.health_check_count,
            uptime_seconds=time.time() - self.start_time
        )
    
    async def _initialize_gateway_health(self):
        """Initialize health status for all active gateways."""
        gateway_status = gateway_manager.get_account_status()
        
        for account in gateway_status.get('accounts', []):
            gateway_id = account['id']
            gateway_type = account['gateway_type']
            
            # Initialize health status
            health_status = GatewayHealthStatus(
                gateway_id=gateway_id,
                gateway_type=gateway_type,
                status=GatewayStatus.CONNECTING,
                metrics=HealthMetrics(),
                last_updated=now_china()
            )
            
            self.gateway_health[gateway_id] = health_status
            
            self.logger.info(
                "Initialized gateway health tracking",
                
                gateway_type=gateway_type
            )
    
    async def _start_monitoring_tasks(self):
        """Start health monitoring tasks for each gateway."""
        for gateway_id in self.gateway_health.keys():
            task = asyncio.create_task(self._monitor_gateway_health(gateway_id))
            self.monitoring_tasks[gateway_id] = task
            
            self.logger.info(
                "Started monitoring task",
                
            )
    
    async def _monitor_gateway_health(self, gateway_id: str):
        """
        Monitor health for a specific gateway.
        
        Args:
            gateway_id: Gateway identifier to monitor
        """
        while self._running:
            try:
                start_time = time.time()
                
                # Perform health check
                await self._perform_health_check(gateway_id)
                
                # Track performance metrics
                check_duration = (time.time() - start_time) * 1000  # ms
                self.health_check_count += 1
                
                # Update health check duration in metrics
                if gateway_id in self.gateway_health:
                    self.gateway_health[gateway_id].metrics.health_check_duration_ms = check_duration
                
                # Log resource usage periodically
                await self._log_resource_usage()
                
                # Wait for next check interval
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                # Task cancelled during shutdown
                break
            except Exception as e:
                self.logger.error(
                    "Health check error",
                    
                    error=str(e)
                )
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_check(self, gateway_id: str):
        """
        Perform comprehensive health check for a gateway.
        
        Args:
            gateway_id: Gateway identifier to check
        """
        if gateway_id not in self.gateway_health:
            return
            
        health_status = self.gateway_health[gateway_id]
        previous_status = health_status.status
        
        try:
            # Check vnpy connection status
            connection_healthy = await self._check_vnpy_connection(gateway_id)
            
            # Check canary contract heartbeat (if not in fallback mode)
            heartbeat_healthy = True
            if self.fallback_mode != "skip_canary":
                heartbeat_healthy = await self._check_canary_heartbeat(gateway_id)
            
            # Determine overall health status
            new_status = self._determine_health_status(
                connection_healthy, 
                heartbeat_healthy,
                gateway_id
            )
            
            # Update health status if changed
            if new_status != previous_status:
                await self._update_gateway_status(gateway_id, new_status, previous_status)
            
            # Update last updated timestamp
            health_status.last_updated = now_china()
            
        except Exception as e:
            self.logger.error(
                "Health check failed",
                
                error=str(e)
            )
            
            # Mark as unhealthy on check failure
            if previous_status != GatewayStatus.UNHEALTHY:
                await self._update_gateway_status(
                    gateway_id, 
                    GatewayStatus.UNHEALTHY,
                    previous_status,
                    error_message=str(e)
                )
    
    async def _check_vnpy_connection(self, gateway_id: str) -> bool:
        """
        Check vnpy gateway connection status.
        
        Args:
            gateway_id: Gateway identifier to check
            
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            # Get connection status from gateway manager
            gateway_status = gateway_manager.get_account_status()
            
            for account in gateway_status.get('accounts', []):
                if account['id'] == gateway_id:
                    connected = account.get('connected', False)
                    
                    # Update connection status in metrics
                    if gateway_id in self.gateway_health:
                        self.gateway_health[gateway_id].metrics.connection_status = (
                            "connected" if connected else "disconnected"
                        )
                    
                    return connected
            
            # Gateway not found in active accounts
            return False
            
        except Exception as e:
            self.logger.error(
                "vnpy connection check failed",
                
                error=str(e)
            )
            return False
    
    async def _check_canary_heartbeat(self, gateway_id: str) -> bool:
        """
        Check canary contract heartbeat for data freshness.
        
        Args:
            gateway_id: Gateway identifier to check
            
        Returns:
            bool: True if heartbeat is healthy, False otherwise
        """
        try:
            if gateway_id not in self.gateway_health:
                return False
                
            gateway_type = self.gateway_health[gateway_id].gateway_type
            
            # Get appropriate canary contract
            canary_contract = self._get_canary_contract(gateway_type)
            if not canary_contract:
                # No canary contract configured, use fallback
                if self.fallback_mode == "connection_only":
                    return True  # Skip canary check
                return False
            
            # Check last tick timestamp for canary contract
            last_tick = self.canary_tick_timestamps.get(f"{gateway_id}:{canary_contract}")
            
            if not last_tick:
                # No tick data received yet, check if we should wait
                health_status = self.gateway_health[gateway_id]
                time_since_start = (now_china() - health_status.last_updated).total_seconds()
                
                # Allow some time for initial tick data
                if time_since_start < self.canary_heartbeat_timeout:
                    return True
                else:
                    self.logger.warning(
                        "No canary tick data received",
                        
                        canary_contract=canary_contract,
                        time_since_start=time_since_start
                    )
                    return False
            
            # Check if tick data is recent enough
            time_since_tick = (now_china() - last_tick).total_seconds()
            is_fresh = time_since_tick <= self.canary_heartbeat_timeout
            
            # Update canary timestamp in metrics
            self.gateway_health[gateway_id].metrics.canary_contract_timestamp = last_tick
            
            if not is_fresh:
                self.logger.warning(
                    "Canary contract heartbeat timeout",
                    
                    canary_contract=canary_contract,
                    time_since_tick=time_since_tick,
                    timeout_threshold=self.canary_heartbeat_timeout
                )
            
            return is_fresh
            
        except Exception as e:
            self.logger.error(
                "Canary heartbeat check failed",
                
                error=str(e)
            )
            return False
    
    def _get_canary_contract(self, gateway_type: str) -> Optional[str]:
        """
        Get primary canary contract for gateway type.
        
        Args:
            gateway_type: Type of gateway (ctp, sopt)
            
        Returns:
            Optional[str]: Canary contract symbol or None
        """
        if gateway_type == "ctp":
            contract = self.ctp_canary_primary
            return contract.strip() if contract and contract.strip() else None
        elif gateway_type == "sopt":
            contract = self.sopt_canary_primary
            return contract.strip() if contract and contract.strip() else None
        else:
            return None
    
    def _determine_health_status(
        self, 
        connection_healthy: bool, 
        heartbeat_healthy: bool,
        gateway_id: str
    ) -> GatewayStatus:
        """
        Determine overall health status based on checks.
        
        Args:
            connection_healthy: Whether connection check passed
            heartbeat_healthy: Whether heartbeat check passed  
            gateway_id: Gateway identifier
            
        Returns:
            GatewayStatus: Determined health status
        """
        if not connection_healthy:
            return GatewayStatus.DISCONNECTED
        
        if connection_healthy and heartbeat_healthy:
            return GatewayStatus.HEALTHY
        
        if connection_healthy and not heartbeat_healthy:
            # Connected but stale data - still unhealthy
            return GatewayStatus.UNHEALTHY
        
        # Default to unhealthy
        return GatewayStatus.UNHEALTHY
    
    async def _update_gateway_status(
        self, 
        gateway_id: str, 
        new_status: GatewayStatus,
        previous_status: GatewayStatus,
        error_message: Optional[str] = None
    ):
        """
        Update gateway health status and publish status change event.
        
        Args:
            gateway_id: Gateway identifier
            new_status: New health status
            previous_status: Previous health status
            error_message: Optional error message
        """
        if gateway_id not in self.gateway_health:
            return
            
        health_status = self.gateway_health[gateway_id]
        health_status.status = new_status
        health_status.last_updated = now_china()
        
        # Update error tracking
        if error_message:
            health_status.metrics.error_count += 1
            health_status.metrics.last_error_message = error_message
        
        self.logger.info(
            "Gateway status changed",
            
            previous_status=previous_status.value,
            new_status=new_status.value,
            error_message=error_message
        )
        
        # Create and publish status change event
        await self._publish_status_change_event(
            gateway_id, 
            previous_status, 
            new_status,
            error_message
        )
    
    async def _publish_status_change_event(
        self,
        gateway_id: str,
        previous_status: GatewayStatus,
        current_status: GatewayStatus,
        error_message: Optional[str] = None
    ):
        """
        Publish health status change event to event bus.
        
        Args:
            gateway_id: Gateway identifier
            previous_status: Previous health status
            current_status: Current health status
            error_message: Optional error message
        """
        try:
            health_status = self.gateway_health[gateway_id]
            
            # Build metadata following example format
            metadata = {
                "last_heartbeat": (
                    health_status.metrics.last_heartbeat.isoformat() 
                    if health_status.metrics.last_heartbeat else None
                ),
                "canary_contract": self._get_canary_contract(health_status.gateway_type),
                "health_check_duration_ms": health_status.metrics.health_check_duration_ms,
                "retry_count": health_status.metrics.retry_count
            }
            
            if error_message:
                metadata["error_message"] = error_message
            
            # Create status change event
            event = HealthStatusEvent(
                event_type="gateway_status_change",
                timestamp=now_china(),
                gateway_id=gateway_id,
                gateway_type=health_status.gateway_type,
                previous_status=previous_status,
                current_status=current_status,
                metadata=metadata
            )
            
            # Publish to event bus
            await event_bus.publish_health_status_change(event)
            
            self.logger.info(
                "Published health status change event",
                
                event_type=event.event_type
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to publish status change event",
                
                error=str(e)
            )
    
    def update_canary_tick(self, gateway_id: str, contract: str, timestamp: datetime, tick_data=None):
        """
        Update canary contract tick timestamp and count with enhanced validation.
        
        Args:
            gateway_id: Gateway identifier
            contract: Contract symbol
            timestamp: Tick timestamp
            tick_data: Optional tick data for validation
        """
        key = f"{gateway_id}:{contract}"
        
        # Validate tick data before processing
        if not self._validate_tick_data(gateway_id, contract, timestamp, tick_data):
            self.logger.warning(
                "Invalid tick data received",
                gateway_id=gateway_id,
                contract=contract,
                timestamp=timestamp.isoformat() if timestamp else None
            )
            return
        
        self.canary_tick_timestamps[key] = timestamp
        
        # Initialize tick count list if not exists
        if key not in self.canary_tick_counts:
            self.canary_tick_counts[key] = []
        
        # Add timestamp to tick count list
        self.canary_tick_counts[key].append(timestamp)
        
        # Log canary tick update for monitoring
        self.logger.debug(f"Updated canary tick: {key}, count: {len(self.canary_tick_counts[key])}")
        
        # Clean old timestamps (older than 1 minute)
        from datetime import timedelta
        cutoff_time = timestamp - timedelta(minutes=1)
        self.canary_tick_counts[key] = [
            ts for ts in self.canary_tick_counts[key] if ts > cutoff_time
        ]
        
        # Update heartbeat in health metrics
        if gateway_id in self.gateway_health:
            self.gateway_health[gateway_id].metrics.last_heartbeat = timestamp
            
        # Determine canary status
        tick_count = len(self.canary_tick_counts[key])
        time_since_last = (now_china() - timestamp).total_seconds()
        
        if time_since_last <= self.canary_heartbeat_timeout:
            status = "ACTIVE"
        elif time_since_last <= self.canary_heartbeat_timeout * 2:
            status = "STALE"
        else:
            status = "INACTIVE"
            
        # Log successful tick validation
        self.logger.debug(
            "Validated canary tick",
            gateway_id=gateway_id,
            contract=contract,
            tick_count_1min=tick_count,
            status=status
        )
        
        # Publish WebSocket update (fire and forget)
        try:
            from app.services.websocket_manager import WebSocketManager
            ws_manager = WebSocketManager.get_instance()
            
            # Create asyncio task to avoid blocking
            import asyncio
            asyncio.create_task(
                ws_manager.publish_canary_tick_update(
                    gateway_id=gateway_id,
                    contract_symbol=contract,
                    tick_count_1min=tick_count,
                    last_tick_time=timestamp.isoformat(),
                    status=status,
                    threshold_seconds=self.canary_heartbeat_timeout
                )
            )
        except Exception as e:
            # Don't let WebSocket errors interrupt tick processing
            self.logger.debug(
                "Failed to publish canary WebSocket update",
                gateway_id=gateway_id,
                contract=contract,
                error=str(e)
            )
    
    async def _log_resource_usage(self):
        """Log resource usage periodically."""
        current_time = time.time()
        
        if current_time - self.last_resource_log >= self.resource_log_interval:
            try:
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                cpu_percent = self.process.cpu_percent()
                uptime = current_time - self.start_time
                
                self.logger.info(
                    "Health monitor resource usage",
                    memory_usage_mb=round(memory_mb, 2),
                    cpu_usage_percent=round(cpu_percent, 2),
                    uptime_seconds=round(uptime, 2),
                    total_health_checks=self.health_check_count,
                    monitored_gateways=len(self.gateway_health),
                    average_checks_per_second=round(self.health_check_count / uptime, 2) if uptime > 0 else 0
                )
                
                self.last_resource_log = current_time
                
            except Exception as e:
                self.logger.error(
                    "Resource usage logging failed",
                    error=str(e)
                )
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get health status summary for all gateways.
        
        Returns:
            Dict[str, Any]: Health summary with gateway statuses and metrics
        """
        # Get all unique canary contracts
        all_canary_contracts = list(set(self.ctp_canary_contracts + self.sopt_canary_contracts))
        
        # Get canary contract monitoring data
        canary_monitor_data = self.get_canary_monitor_data()
        
        return {
            "monitoring_active": self._running,
            "total_gateways": len(self.gateway_health),
            "healthy_gateways": sum(
                1 for status in self.gateway_health.values() 
                if status.status == GatewayStatus.HEALTHY
            ),
            "unhealthy_gateways": sum(
                1 for status in self.gateway_health.values()
                if status.status == GatewayStatus.UNHEALTHY
            ),
            "gateways": {
                gateway_id: status.to_dict()
                for gateway_id, status in self.gateway_health.items()
            },
            "canary_contracts": all_canary_contracts,
            "canary_monitor_data": canary_monitor_data,
            "last_health_check": now_china().isoformat(),
            "performance": {
                "total_health_checks": self.health_check_count,
                "uptime_seconds": time.time() - self.start_time,
                "memory_usage_mb": round(self.process.memory_info().rss / 1024 / 1024, 2)
            }
        }
    
    def get_gateway_health(self, gateway_id: str) -> Optional[Dict[str, Any]]:
        """
        Get health status for a specific gateway.
        
        Args:
            gateway_id: Gateway identifier
            
        Returns:
            Optional[Dict[str, Any]]: Gateway health status or None if not found
        """
        if gateway_id in self.gateway_health:
            return self.gateway_health[gateway_id].to_dict()
        return None
    
    def get_canary_monitor_data(self) -> List[Dict[str, Any]]:
        """
        Get canary contract monitoring data in dashboard format.
        
        Returns:
            List[Dict[str, Any]]: List of canary contract data for dashboard
        """
        canary_data = []
        current_time = now_china()  # Use China timezone
        
        # Get all unique canary contracts across all gateway types
        all_canary_contracts = list(set(self.ctp_canary_contracts + self.sopt_canary_contracts))
        
        for contract in all_canary_contracts:
            # Find the latest tick for this contract across all gateways
            latest_tick_time = None
            total_tick_count = 0
            
            # Check all tick data for this contract (check all possible gateway keys)
            for key in self.canary_tick_timestamps.keys():
                if key.endswith(f":{contract}"):
                    # Get latest tick timestamp
                    tick_time = self.canary_tick_timestamps[key]
                    if latest_tick_time is None or tick_time > latest_tick_time:
                        latest_tick_time = tick_time
                    
                    # Get tick count in last minute
                    if key in self.canary_tick_counts:
                        total_tick_count += len(self.canary_tick_counts[key])
            
            # Determine status based on latest tick time
            status = "INACTIVE"
            if latest_tick_time:
                time_since_tick = (current_time - latest_tick_time).total_seconds()
                if time_since_tick <= 30:  # Active if tick within 30 seconds
                    status = "ACTIVE"
                elif time_since_tick <= self.canary_heartbeat_timeout:  # Stale if within heartbeat timeout
                    status = "STALE"
                
                # Log status calculation for monitoring
                self.logger.debug(
                    f"Canary status: {contract} - {status} (time_since={time_since_tick:.1f}s, ticks={total_tick_count})"
                )
            
            canary_data.append({
                "contract_symbol": contract,
                "last_tick_time": latest_tick_time.isoformat() if latest_tick_time else current_time.isoformat(),
                "tick_count_1min": total_tick_count,
                "status": status,
                "threshold_seconds": self.canary_heartbeat_timeout
            })
        
        return canary_data
    
    
    def _validate_tick_data(self, gateway_id: str, contract: str, timestamp: datetime, tick_data=None) -> bool:
        """
        Validate tick data for quality and consistency.
        
        Args:
            gateway_id: Gateway identifier
            contract: Contract symbol
            timestamp: Tick timestamp
            tick_data: Optional tick data object
            
        Returns:
            bool: True if tick data is valid, False otherwise
        """
        try:
            current_time = now_china()  # Use China timezone
            
            # Basic timestamp validation
            if not timestamp:
                return False
                
            # Check if timestamp is too old (more than 5 minutes)
            if (current_time - timestamp).total_seconds() > 300:
                self.logger.warning(
                    "Tick data too old",
                    gateway_id=gateway_id,
                    contract=contract,
                    age_seconds=(current_time - timestamp).total_seconds()
                )
                return False
            
            # Check if timestamp is in the future (more than 1 minute)
            if (timestamp - current_time).total_seconds() > 60:
                self.logger.warning(
                    "Tick data from future",
                    gateway_id=gateway_id,
                    contract=contract,
                    future_seconds=(timestamp - current_time).total_seconds()
                )
                return False
            
            # Validate tick data content if provided
            if tick_data:
                # Check for essential price fields
                if hasattr(tick_data, 'last_price'):
                    price = getattr(tick_data, 'last_price', 0)
                    if price <= 0:
                        self.logger.warning(
                            "Invalid tick price",
                            gateway_id=gateway_id,
                            contract=contract,
                            price=price
                        )
                        return False
                
                # Gateway-specific validation
                if not self._validate_gateway_specific_tick(gateway_id, contract, tick_data):
                    return False
            
            # Rate limiting check - prevent spam (only for newer timestamps)
            key = f"{gateway_id}:{contract}"
            if key in self.canary_tick_timestamps:
                last_tick_time = self.canary_tick_timestamps[key]
                time_since_last = (timestamp - last_tick_time).total_seconds()
                
                # Only apply rate limiting for newer timestamps to prevent spam
                # Allow older timestamps for testing/replay scenarios
                if time_since_last > 0 and time_since_last < 0.1:
                    self.logger.debug(
                        "Tick rate too high - throttling",
                        gateway_id=gateway_id,
                        contract=contract,
                        time_since_last=time_since_last
                    )
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Tick validation error",
                gateway_id=gateway_id,
                contract=contract,
                error=str(e)
            )
            return False
    
    def _validate_gateway_specific_tick(self, gateway_id: str, contract: str, tick_data) -> bool:
        """
        Perform gateway-specific tick data validation.
        
        Args:
            gateway_id: Gateway identifier
            contract: Contract symbol
            tick_data: Tick data object
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        try:
            # Get gateway type
            gateway_type = None
            if gateway_id in self.gateway_health:
                gateway_type = self.gateway_health[gateway_id].gateway_type
            
            # CTP-specific validation (futures)
            if gateway_type == "ctp":
                # Validate futures contract format
                if not self._is_futures_contract(contract):
                    self.logger.warning(
                        "Invalid futures contract for CTP",
                        gateway_id=gateway_id,
                        contract=contract
                    )
                    return False
                    
                # Validate reasonable price range for different futures contracts
                if hasattr(tick_data, 'last_price'):
                    price = getattr(tick_data, 'last_price', 0)
                    
                    # Define price ranges for different contract types
                    price_valid = True
                    if contract.startswith('rb'):  # Steel rebar futures
                        price_valid = 2000 <= price <= 6000
                    elif contract.startswith('au'):  # Gold futures
                        price_valid = 400 <= price <= 1200  # Gold price range in yuan per gram
                    elif contract.startswith('ag'):  # Silver futures
                        price_valid = 5 <= price <= 50  # Silver price range in yuan per gram
                    elif contract.startswith('cu'):  # Copper futures
                        price_valid = 40000 <= price <= 80000  # Copper price range in yuan per ton
                    else:
                        # For unknown contracts, use a very broad range
                        price_valid = price > 0  # Just check it's positive
                    
                    if not price_valid:
                        self.logger.warning(
                            "CTP futures price out of range",
                            gateway_id=gateway_id,
                            contract=contract,
                            price=price
                        )
                        return False
            
            # SOPT-specific validation (ETFs)
            elif gateway_type == "sopt":
                # Validate ETF contract format
                if not self._is_etf_contract(contract):
                    self.logger.warning(
                        "Invalid ETF contract for SOPT",
                        gateway_id=gateway_id,
                        contract=contract
                    )
                    return False
                    
                # Validate reasonable price range for ETFs
                if hasattr(tick_data, 'last_price'):
                    price = getattr(tick_data, 'last_price', 0)
                    if price < 1 or price > 100:  # Reasonable range for ETF prices
                        self.logger.warning(
                            "SOPT ETF price out of range",
                            gateway_id=gateway_id,
                            contract=contract,
                            price=price
                        )
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Gateway-specific tick validation error",
                gateway_id=gateway_id,
                contract=contract,
                error=str(e)
            )
            return False
    
    def _is_futures_contract(self, contract: str) -> bool:
        """Check if contract is a valid futures contract."""
        # CTP futures contracts typically have format like "rb2601" 
        # (product code + year + month)
        import re
        pattern = r'^[a-zA-Z]{1,2}\d{4}$'
        return bool(re.match(pattern, contract))
    
    def _is_etf_contract(self, contract: str) -> bool:
        """Check if contract is a valid ETF contract."""
        # ETF contracts are typically 6-digit codes like "510050", "159915"
        import re
        pattern = r'^\d{6}$'
        return bool(re.match(pattern, contract))


# Global health monitor instance
health_monitor = HealthMonitor()