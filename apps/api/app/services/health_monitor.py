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
        self.ctp_canary_contracts = ["rb2501", "rb2505"]
        self.ctp_canary_primary = "rb2501"
        self.sopt_canary_contracts = ["rb2501", "rb2505"] 
        self.sopt_canary_primary = "rb2501"
        
        # Health status tracking
        self.gateway_health: Dict[str, GatewayHealthStatus] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.canary_tick_timestamps: Dict[str, datetime] = {}
        
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
        self.ctp_canary_contracts = os.getenv("CTP_CANARY_CONTRACTS", "rb2501,rb2505").split(",")
        self.ctp_canary_primary = os.getenv("CTP_CANARY_PRIMARY", "rb2501")
        self.sopt_canary_contracts = os.getenv("SOPT_CANARY_CONTRACTS", "rb2501,rb2505").split(",")
        self.sopt_canary_primary = os.getenv("SOPT_CANARY_PRIMARY", "rb2501")
        
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
                
                gateway_type=gateway_type,
                status=GatewayStatus.CONNECTING,
                metrics=HealthMetrics(),
                last_updated=datetime.now(timezone.utc)
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
            health_status.last_updated = datetime.now(timezone.utc)
            
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
                time_since_start = (datetime.now(timezone.utc) - health_status.last_updated).total_seconds()
                
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
            time_since_tick = (datetime.now(timezone.utc) - last_tick).total_seconds()
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
        health_status.last_updated = datetime.now(timezone.utc)
        
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
                timestamp=datetime.now(timezone.utc),
                
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
    
    def update_canary_tick(self, gateway_id: str, contract: str, timestamp: datetime):
        """
        Update canary contract tick timestamp.
        
        Args:
            gateway_id: Gateway identifier
            contract: Contract symbol
            timestamp: Tick timestamp
        """
        key = f"{gateway_id}:{contract}"
        self.canary_tick_timestamps[key] = timestamp
        
        # Update heartbeat in health metrics
        if gateway_id in self.gateway_health:
            self.gateway_health[gateway_id].metrics.last_heartbeat = timestamp
    
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


# Global health monitor instance
health_monitor = HealthMonitor()