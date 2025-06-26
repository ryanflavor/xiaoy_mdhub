"""
Gateway Recovery Service for automated hard restart recovery mechanism.
Provides cool-down management, process termination, and relaunch capabilities.
"""

import asyncio
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import structlog

from app.services.event_bus import event_bus
from app.services.gateway_manager import gateway_manager
from app.services.health_monitor import health_monitor
from app.services.database_service import database_service


class RecoveryStatus(Enum):
    """Recovery status enumeration."""
    IDLE = "idle"
    COOLING_DOWN = "cooling_down"
    RESTARTING = "restarting"
    RECOVERY_SUCCESS = "recovery_success"
    RECOVERY_FAILED = "recovery_failed"
    PERMANENTLY_FAILED = "permanently_failed"


class GatewayRecoveryState:
    """Recovery state tracking for a single gateway."""
    
    def __init__(self, gateway_id: str, gateway_type: str):
        self.gateway_id = gateway_id
        self.gateway_type = gateway_type
        self.status = RecoveryStatus.IDLE
        self.restart_attempt_count = 0
        self.last_restart_timestamp: Optional[datetime] = None
        self.cooldown_start_time: Optional[datetime] = None
        self.recovery_start_time: Optional[datetime] = None
        self.last_error_message: Optional[str] = None
        self.recovery_history: List[Dict[str, Any]] = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert recovery state to dictionary."""
        return {
            "gateway_id": self.gateway_id,
            "gateway_type": self.gateway_type,
            "status": self.status.value,
            "restart_attempt_count": self.restart_attempt_count,
            "last_restart_timestamp": self.last_restart_timestamp.isoformat() if self.last_restart_timestamp else None,
            "cooldown_start_time": self.cooldown_start_time.isoformat() if self.cooldown_start_time else None,
            "recovery_start_time": self.recovery_start_time.isoformat() if self.recovery_start_time else None,
            "last_error_message": self.last_error_message,
            "recovery_history": self.recovery_history
        }


class GatewayRecoveryService:
    """
    Gateway Recovery Service for automated hard restart recovery.
    
    Provides:
    - Event-driven recovery triggering from health monitor
    - Configurable cooldown period management
    - Process termination and clean restart
    - Recovery attempt tracking and limits
    - Integration with existing health monitoring
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        
        # Recovery state tracking
        self.recovery_states: Dict[str, GatewayRecoveryState] = {}
        
        # Background tasks
        self.recovery_tasks: Dict[str, asyncio.Task] = {}
        self.cooldown_tasks: Dict[str, asyncio.Task] = {}
        
        # Control flags
        self._running = False
        self._event_subscription_active = False
        
        # Performance metrics
        self.total_recovery_attempts = 0
        self.successful_recoveries = 0
        self.failed_recoveries = 0
        self.start_time = time.time()
        
    def _load_configuration(self):
        """Load configuration from environment variables at runtime."""
        self.recovery_enabled = os.getenv("RECOVERY_SERVICE_ENABLED", "true").lower() == "true"
        self.cooldown_duration_seconds = int(os.getenv("RECOVERY_COOLDOWN_SECONDS", "30"))
        self.recovery_timeout_seconds = int(os.getenv("RECOVERY_TIMEOUT_SECONDS", "120"))
        self.max_retry_attempts = int(os.getenv("RECOVERY_MAX_RETRY_ATTEMPTS", "3"))
        self.exponential_backoff_enabled = os.getenv("RECOVERY_EXPONENTIAL_BACKOFF", "true").lower() == "true"
        self.exponential_backoff_factor = float(os.getenv("RECOVERY_EXPONENTIAL_BACKOFF_FACTOR", "2.0"))
        
    async def start(self) -> bool:
        """
        Start the Gateway Recovery Service.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        # Load configuration from environment variables at runtime
        self._load_configuration()
        
        if not self.recovery_enabled:
            self.logger.info("Gateway Recovery Service disabled via RECOVERY_SERVICE_ENABLED environment variable")
            return False
            
        if self._running:
            self.logger.warning("Gateway Recovery Service already running")
            return True
            
        try:
            self.logger.info(
                "Starting Gateway Recovery Service",
                cooldown_duration=self.cooldown_duration_seconds,
                recovery_timeout=self.recovery_timeout_seconds,
                max_retry_attempts=self.max_retry_attempts,
                exponential_backoff_enabled=self.exponential_backoff_enabled
            )
            
            # Initialize recovery states for all active gateways
            await self._initialize_recovery_states()
            
            # Subscribe to health status events
            await self._subscribe_to_health_events()
            
            self._running = True
            
            self.logger.info(
                "Gateway Recovery Service started successfully",
                monitored_gateways=len(self.recovery_states)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Gateway Recovery Service startup failed",
                error=str(e)
            )
            return False
    
    async def stop(self):
        """Stop the Gateway Recovery Service."""
        if not self._running:
            return
            
        self.logger.info("Stopping Gateway Recovery Service")
        self._running = False
        
        # Cancel all recovery tasks
        for gateway_id, task in self.recovery_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(
                    "Error stopping recovery task",
                    
                    error=str(e)
                )
        
        # Cancel all cooldown tasks
        for gateway_id, task in self.cooldown_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(
                    "Error stopping cooldown task",
                    
                    error=str(e)
                )
        
        # Unsubscribe from events
        await self._unsubscribe_from_health_events()
        
        # Clear state
        self.recovery_tasks.clear()
        self.cooldown_tasks.clear()
        
        self.logger.info(
            "Gateway Recovery Service stopped",
            uptime_seconds=time.time() - self.start_time,
            total_recovery_attempts=self.total_recovery_attempts,
            successful_recoveries=self.successful_recoveries,
            failed_recoveries=self.failed_recoveries
        )
    
    async def _initialize_recovery_states(self):
        """Initialize recovery states for all active gateways."""
        try:
            # Get active gateways from gateway manager
            gateway_status = gateway_manager.get_account_status()
            
            for account in gateway_status.get('accounts', []):
                gateway_id = account['id']
                gateway_type = account['gateway_type']
                
                # Initialize recovery state
                recovery_state = GatewayRecoveryState(gateway_id, gateway_type)
                self.recovery_states[gateway_id] = recovery_state
                
                self.logger.info(
                    "Initialized recovery state",
                    
                    gateway_type=gateway_type
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to initialize recovery states",
                error=str(e)
            )
            raise
    
    async def _subscribe_to_health_events(self):
        """Subscribe to health status change events."""
        try:
            event_bus.subscribe("gateway_status_change", self._handle_health_status_change)
            self._event_subscription_active = True
            
            self.logger.info("Subscribed to health status events")
            
        except Exception as e:
            self.logger.error(
                "Failed to subscribe to health events",
                error=str(e)
            )
            raise
    
    async def _unsubscribe_from_health_events(self):
        """Unsubscribe from health status change events."""
        if self._event_subscription_active:
            try:
                event_bus.unsubscribe("gateway_status_change", self._handle_health_status_change)
                self._event_subscription_active = False
                
                self.logger.info("Unsubscribed from health status events")
                
            except Exception as e:
                self.logger.error(
                    "Failed to unsubscribe from health events",
                    error=str(e)
                )
    
    async def _handle_health_status_change(self, event_data: Dict[str, Any]):
        """
        Handle health status change events.
        
        Args:
            event_data: Health status event data
        """
        try:
            gateway_id = event_data.get("gateway_id")
            current_status = event_data.get("current_status")
            
            if not gateway_id or not current_status:
                return
                
            # Only trigger recovery for UNHEALTHY status
            if current_status == "UNHEALTHY":
                await self._trigger_recovery(gateway_id, event_data)
                
        except Exception as e:
            self.logger.error(
                "Error handling health status change",
                event_data=event_data,
                error=str(e)
            )
    
    async def _trigger_recovery(self, gateway_id: str, event_data: Dict[str, Any]):
        """
        Trigger recovery process for a gateway.
        
        Args:
            gateway_id: Gateway identifier
            event_data: Health status event data
        """
        if not self._running:
            return
            
        if gateway_id not in self.recovery_states:
            self.logger.warning(
                "Gateway not found in recovery states",
                
            )
            return
            
        recovery_state = self.recovery_states[gateway_id]
        
        # Check if already in recovery or cooling down
        if recovery_state.status in [RecoveryStatus.COOLING_DOWN, RecoveryStatus.RESTARTING]:
            self.logger.info(
                "Gateway already in recovery process",
                
                current_status=recovery_state.status.value
            )
            return
            
        # Check if maximum retry attempts exceeded
        if recovery_state.restart_attempt_count >= self.max_retry_attempts:
            recovery_state.status = RecoveryStatus.PERMANENTLY_FAILED
            recovery_state.last_error_message = "Maximum retry attempts exceeded"
            
            self.logger.error(
                "Gateway permanently failed - maximum retry attempts exceeded",
                
                retry_attempts=recovery_state.restart_attempt_count,
                max_attempts=self.max_retry_attempts
            )
            
            await self._publish_recovery_event(gateway_id, "gateway_recovery_failed", {
                "reason": "maximum_retry_attempts_exceeded",
                "retry_attempts": recovery_state.restart_attempt_count
            })
            
            return
        
        # Start cooldown period
        await self._start_cooldown_period(gateway_id)
        
        self.logger.info(
            "Recovery triggered for gateway",
            
            retry_attempt=recovery_state.restart_attempt_count + 1,
            cooldown_duration=self._get_cooldown_duration(recovery_state.restart_attempt_count)
        )
    
    async def _start_cooldown_period(self, gateway_id: str):
        """
        Start cooldown period for a gateway.
        
        Args:
            gateway_id: Gateway identifier
        """
        recovery_state = self.recovery_states[gateway_id]
        recovery_state.status = RecoveryStatus.COOLING_DOWN
        recovery_state.cooldown_start_time = datetime.now()
        
        # Calculate cooldown duration with exponential backoff
        cooldown_duration = self._get_cooldown_duration(recovery_state.restart_attempt_count)
        
        self.logger.info(
            "Starting cooldown period",
            
            cooldown_duration_seconds=cooldown_duration,
            retry_attempt=recovery_state.restart_attempt_count + 1
        )
        
        # Publish cooldown started event
        await self._publish_recovery_event(gateway_id, "gateway_recovery_cooldown_started", {
            "cooldown_duration_seconds": cooldown_duration,
            "retry_attempt": recovery_state.restart_attempt_count + 1
        })
        
        # Schedule recovery after cooldown
        cooldown_task = asyncio.create_task(
            self._cooldown_and_recover(gateway_id, cooldown_duration)
        )
        self.cooldown_tasks[gateway_id] = cooldown_task
    
    def _get_cooldown_duration(self, attempt_count: int) -> int:
        """
        Calculate cooldown duration with optional exponential backoff.
        
        Args:
            attempt_count: Current attempt count
            
        Returns:
            int: Cooldown duration in seconds
        """
        if not self.exponential_backoff_enabled:
            return self.cooldown_duration_seconds
            
        # Exponential backoff: base_duration * (backoff_factor ^ attempt_count)
        return int(self.cooldown_duration_seconds * (self.exponential_backoff_factor ** attempt_count))
    
    async def _cooldown_and_recover(self, gateway_id: str, cooldown_duration: int):
        """
        Wait for cooldown period and then start recovery.
        
        Args:
            gateway_id: Gateway identifier
            cooldown_duration: Cooldown duration in seconds
        """
        try:
            # Wait for cooldown period
            await asyncio.sleep(cooldown_duration)
            
            # Check if service is still running
            if not self._running:
                return
                
            # Start recovery process
            await self._start_recovery_process(gateway_id)
            
        except asyncio.CancelledError:
            # Cooldown cancelled during shutdown
            pass
        except Exception as e:
            self.logger.error(
                "Cooldown and recovery error",
                
                error=str(e)
            )
        finally:
            # Clean up cooldown task
            if gateway_id in self.cooldown_tasks:
                del self.cooldown_tasks[gateway_id]
    
    async def _start_recovery_process(self, gateway_id: str):
        """
        Start the recovery process for a gateway.
        
        Args:
            gateway_id: Gateway identifier
        """
        recovery_state = self.recovery_states[gateway_id]
        recovery_state.status = RecoveryStatus.RESTARTING
        recovery_state.recovery_start_time = datetime.now()
        recovery_state.restart_attempt_count += 1
        
        self.total_recovery_attempts += 1
        
        self.logger.info(
            "Starting recovery process",
            
            attempt=recovery_state.restart_attempt_count,
            max_attempts=self.max_retry_attempts
        )
        
        # Publish recovery started event
        await self._publish_recovery_event(gateway_id, "gateway_recovery_started", {
            "restart_attempt": recovery_state.restart_attempt_count,
            "max_attempts": self.max_retry_attempts
        })
        
        # Start recovery task
        recovery_task = asyncio.create_task(
            self._execute_recovery(gateway_id)
        )
        self.recovery_tasks[gateway_id] = recovery_task
    
    async def _execute_recovery(self, gateway_id: str):
        """
        Execute the recovery process (terminate + restart).
        
        Args:
            gateway_id: Gateway identifier
        """
        recovery_state = self.recovery_states[gateway_id]
        
        try:
            # Step 1: Terminate gateway process
            await self._terminate_gateway_process(gateway_id)
            
            # Step 2: Restart gateway process
            await self._restart_gateway_process(gateway_id)
            
            # Step 3: Wait for health confirmation
            recovery_success = await self._wait_for_recovery_confirmation(gateway_id)
            
            if recovery_success:
                await self._handle_recovery_success(gateway_id)
            else:
                await self._handle_recovery_failure(gateway_id, "Health confirmation timeout")
                
        except Exception as e:
            await self._handle_recovery_failure(gateway_id, str(e))
        finally:
            # Clean up recovery task
            if gateway_id in self.recovery_tasks:
                del self.recovery_tasks[gateway_id]
    
    async def _terminate_gateway_process(self, gateway_id: str):
        """
        Terminate gateway process gracefully.
        
        Args:
            gateway_id: Gateway identifier
        """
        self.logger.info(
            "Terminating gateway process",
            
        )
        
        # Use gateway manager to terminate process
        await gateway_manager.terminate_gateway_process(gateway_id)
        
        # Wait a short time for graceful shutdown
        await asyncio.sleep(2)
        
        self.logger.info(
            "Gateway process terminated",
            
        )
    
    async def _restart_gateway_process(self, gateway_id: str):
        """
        Restart gateway process with clean initialization.
        
        Args:
            gateway_id: Gateway identifier
        """
        self.logger.info(
            "Restarting gateway process",
            
        )
        
        # Get gateway settings from database
        gateway_settings = await self._get_gateway_settings(gateway_id)
        if not gateway_settings:
            raise Exception(f"Gateway settings not found for {gateway_id}")
        
        # Use gateway manager to restart process
        await gateway_manager.restart_gateway_process(gateway_id, gateway_settings)
        
        self.logger.info(
            "Gateway process restart initiated",
            
        )
    
    async def _get_gateway_settings(self, gateway_id: str) -> Optional[Dict[str, Any]]:
        """
        Get gateway settings from database.
        
        Args:
            gateway_id: Gateway identifier
            
        Returns:
            Optional[Dict[str, Any]]: Gateway settings or None if not found
        """
        try:
            # Get account from database
            account = await database_service.get_account_by_id(gateway_id)
            if account:
                return account.settings
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to get gateway settings",
                
                error=str(e)
            )
            return None
    
    async def _wait_for_recovery_confirmation(self, gateway_id: str) -> bool:
        """
        Wait for health monitor to confirm recovery.
        
        Args:
            gateway_id: Gateway identifier
            
        Returns:
            bool: True if recovery confirmed, False otherwise
        """
        timeout = self.recovery_timeout_seconds
        check_interval = 5  # Check every 5 seconds
        elapsed = 0
        
        self.logger.info(
            "Waiting for recovery confirmation",
            
            timeout_seconds=timeout
        )
        
        while elapsed < timeout:
            if not self._running:
                return False
                
            # Check health status
            health_status = health_monitor.get_gateway_health(gateway_id)
            if health_status and health_status.get("status") == "HEALTHY":
                self.logger.info(
                    "Recovery confirmed",
                    
                    elapsed_seconds=elapsed
                )
                return True
            
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        self.logger.warning(
            "Recovery confirmation timeout",
            
            timeout_seconds=timeout
        )
        return False
    
    async def _handle_recovery_success(self, gateway_id: str):
        """
        Handle successful recovery.
        
        Args:
            gateway_id: Gateway identifier
        """
        recovery_state = self.recovery_states[gateway_id]
        recovery_state.status = RecoveryStatus.RECOVERY_SUCCESS
        recovery_state.last_restart_timestamp = datetime.now()
        
        # Calculate recovery duration
        recovery_duration = 0
        if recovery_state.recovery_start_time:
            recovery_duration = (datetime.now() - recovery_state.recovery_start_time).total_seconds()
        
        # Add to recovery history
        recovery_state.recovery_history.append({
            "attempt": recovery_state.restart_attempt_count,
            "result": "success",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": recovery_duration
        })
        
        self.successful_recoveries += 1
        
        self.logger.info(
            "Gateway recovery successful",
            
            attempt=recovery_state.restart_attempt_count,
            duration_seconds=recovery_duration
        )
        
        # Publish recovery success event
        await self._publish_recovery_event(gateway_id, "gateway_recovery_completed", {
            "result": "success",
            "restart_attempt": recovery_state.restart_attempt_count,
            "recovery_duration_seconds": recovery_duration
        })
        
        # Reset recovery state
        recovery_state.status = RecoveryStatus.IDLE
        recovery_state.restart_attempt_count = 0
        recovery_state.recovery_start_time = None
        recovery_state.cooldown_start_time = None
        recovery_state.last_error_message = None
    
    async def _handle_recovery_failure(self, gateway_id: str, error_message: str):
        """
        Handle recovery failure.
        
        Args:
            gateway_id: Gateway identifier
            error_message: Error message
        """
        recovery_state = self.recovery_states[gateway_id]
        recovery_state.status = RecoveryStatus.RECOVERY_FAILED
        recovery_state.last_error_message = error_message
        
        # Calculate recovery duration
        recovery_duration = 0
        if recovery_state.recovery_start_time:
            recovery_duration = (datetime.now() - recovery_state.recovery_start_time).total_seconds()
        
        # Add to recovery history
        recovery_state.recovery_history.append({
            "attempt": recovery_state.restart_attempt_count,
            "result": "failed",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": recovery_duration,
            "error_message": error_message
        })
        
        self.failed_recoveries += 1
        
        self.logger.error(
            "Gateway recovery failed",
            
            attempt=recovery_state.restart_attempt_count,
            error=error_message,
            duration_seconds=recovery_duration
        )
        
        # Publish recovery failure event
        await self._publish_recovery_event(gateway_id, "gateway_recovery_failed", {
            "result": "failed",
            "restart_attempt": recovery_state.restart_attempt_count,
            "error_message": error_message,
            "recovery_duration_seconds": recovery_duration
        })
        
        # Reset status to idle for potential retry
        recovery_state.status = RecoveryStatus.IDLE
        recovery_state.recovery_start_time = None
    
    async def _publish_recovery_event(self, gateway_id: str, event_type: str, metadata: Dict[str, Any]):
        """
        Publish recovery event to event bus.
        
        Args:
            gateway_id: Gateway identifier
            event_type: Event type
            metadata: Event metadata
        """
        try:
            recovery_state = self.recovery_states[gateway_id]
            
            event_data = {
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "gateway_id": gateway_id,
                "gateway_type": recovery_state.gateway_type,
                "metadata": metadata
            }
            
            await event_bus.publish(event_type, event_data)
            
            self.logger.debug(
                "Published recovery event",
                
                event_type=event_type
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to publish recovery event",
                
                event_type=event_type,
                error=str(e)
            )
    
    def get_recovery_status(self) -> Dict[str, Any]:
        """
        Get recovery service status and statistics.
        
        Returns:
            Dict[str, Any]: Recovery service status
        """
        return {
            "service_running": self._running,
            "recovery_enabled": self.recovery_enabled,
            "total_gateways": len(self.recovery_states),
            "gateways_in_recovery": sum(
                1 for state in self.recovery_states.values()
                if state.status in [RecoveryStatus.COOLING_DOWN, RecoveryStatus.RESTARTING]
            ),
            "permanently_failed_gateways": sum(
                1 for state in self.recovery_states.values()
                if state.status == RecoveryStatus.PERMANENTLY_FAILED
            ),
            "performance_metrics": {
                "total_recovery_attempts": self.total_recovery_attempts,
                "successful_recoveries": self.successful_recoveries,
                "failed_recoveries": self.failed_recoveries,
                "success_rate": (
                    (self.successful_recoveries / self.total_recovery_attempts) * 100
                    if self.total_recovery_attempts > 0 else 0
                ),
                "uptime_seconds": time.time() - self.start_time
            },
            "configuration": {
                "cooldown_duration_seconds": self.cooldown_duration_seconds,
                "recovery_timeout_seconds": self.recovery_timeout_seconds,
                "max_retry_attempts": self.max_retry_attempts,
                "exponential_backoff_enabled": self.exponential_backoff_enabled,
                "exponential_backoff_factor": self.exponential_backoff_factor
            },
            "gateway_states": {
                gateway_id: state.to_dict()
                for gateway_id, state in self.recovery_states.items()
            }
        }
    
    def get_gateway_recovery_status(self, gateway_id: str) -> Optional[Dict[str, Any]]:
        """
        Get recovery status for a specific gateway.
        
        Args:
            gateway_id: Gateway identifier
            
        Returns:
            Optional[Dict[str, Any]]: Gateway recovery status or None if not found
        """
        if gateway_id in self.recovery_states:
            return self.recovery_states[gateway_id].to_dict()
        return None


# Global gateway recovery service instance
gateway_recovery_service = GatewayRecoveryService()