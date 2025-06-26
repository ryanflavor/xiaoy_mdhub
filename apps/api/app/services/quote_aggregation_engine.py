"""
Quote Aggregation Engine for automated failover logic.

This service listens for gateway health status changes and automatically switches
contract subscriptions to backup data sources when primary sources fail.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import structlog

from app.services.event_bus import event_bus
from app.services.database_service import database_service
from app.services.gateway_manager import gateway_manager


class FailoverStatus(Enum):
    """Failover execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ContractSubscription:
    """Track contract subscription state per gateway."""
    symbol: str
    gateway_id: str
    subscribed_at: datetime
    last_tick_time: Optional[datetime] = None
    tick_count: int = 0
    is_active: bool = True


@dataclass
class GatewayFailoverState:
    """Track failover state for a gateway."""
    gateway_id: str
    gateway_type: str
    priority: int
    is_healthy: bool
    last_health_check: datetime
    failover_cooldown_until: Optional[datetime] = None
    consecutive_failures: int = 0
    
    
@dataclass
class FailoverEvent:
    """Detailed failover event data."""
    event_type: str = "failover_executed"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    failed_gateway_id: str = ""
    backup_gateway_id: str = ""
    affected_contracts: List[str] = field(default_factory=list)
    failover_duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "failed_gateway_id": self.failed_gateway_id,
            "backup_gateway_id": self.backup_gateway_id,
            "affected_contracts": self.affected_contracts,
            "failover_duration_ms": self.failover_duration_ms,
            "metadata": self.metadata
        }


class QuoteAggregationEngine:
    """
    Quote Aggregation Engine for automated failover logic.
    
    Listens for gateway health status changes and automatically switches
    contract subscriptions to backup data sources for zero-interruption service.
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        
        # Configuration from environment variables
        self.failover_enabled = os.getenv("FAILOVER_ENABLED", "true").lower() == "true"
        self.failover_timeout_seconds = int(os.getenv("FAILOVER_TIMEOUT_SECONDS", "5"))
        self.failover_cooldown_seconds = int(os.getenv("FAILOVER_COOLDOWN_SECONDS", "30"))
        self.max_consecutive_failures = int(os.getenv("MAX_CONSECUTIVE_FAILURES", "3"))
        
        # State tracking
        self.contract_subscriptions: Dict[str, ContractSubscription] = {}
        self.gateway_states: Dict[str, GatewayFailoverState] = {}
        self.active_failovers: Dict[str, FailoverStatus] = {}
        
        # Performance tracking
        self.total_failovers_executed = 0
        self.last_failover_time: Optional[datetime] = None
        self.failover_execution_times: List[float] = []
        
        # Event subscription
        self._running = False
        self._subscription_active = False
        
    async def start(self):
        """Start the quote aggregation engine."""
        if self._running:
            self.logger.warning("Quote aggregation engine already running")
            return
        
        self._running = True
        
        try:
            # Initialize gateway state from database
            await self._initialize_gateway_states()
            
            # Subscribe to health status events
            await self._subscribe_to_health_events()
            
            # Start background tasks
            asyncio.create_task(self._maintenance_task())
            
            self.logger.info(
                "Quote Aggregation Engine started",
                failover_enabled=self.failover_enabled,
                timeout_seconds=self.failover_timeout_seconds,
                cooldown_seconds=self.failover_cooldown_seconds,
                total_gateways=len(self.gateway_states)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to start Quote Aggregation Engine",
                error=str(e)
            )
            self._running = False
            raise
    
    async def stop(self):
        """Stop the quote aggregation engine."""
        if not self._running:
            return
        
        self._running = False
        
        try:
            # Unsubscribe from events
            if self._subscription_active:
                event_bus.unsubscribe("gateway_status_change", self._handle_health_status_change)
                self._subscription_active = False
            
            self.logger.info(
                "Quote Aggregation Engine stopped",
                total_failovers_executed=self.total_failovers_executed,
                average_failover_time_ms=self._calculate_average_failover_time()
            )
            
        except Exception as e:
            self.logger.error(
                "Error stopping Quote Aggregation Engine",
                error=str(e)
            )
    
    async def _initialize_gateway_states(self):
        """Initialize gateway states from database accounts."""
        try:
            if not await database_service.is_available():
                self.logger.warning("Database unavailable, using empty gateway states")
                return
            
            # Get all enabled accounts ordered by priority
            accounts = await database_service.get_all_accounts(enabled_only=True)
            
            for account in accounts:
                gateway_state = GatewayFailoverState(
                    gateway_id=account.id,
                    gateway_type=account.gateway_type,
                    priority=account.priority,
                    is_healthy=True,  # Assume healthy until proven otherwise
                    last_health_check=datetime.now()
                )
                self.gateway_states[account.id] = gateway_state
            
            self.logger.info(
                "Gateway states initialized",
                total_gateways=len(self.gateway_states),
                gateway_priorities={gw.gateway_id: gw.priority for gw in self.gateway_states.values()}
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize gateway states",
                error=str(e)
            )
    
    async def _subscribe_to_health_events(self):
        """Subscribe to gateway health status change events."""
        try:
            event_bus.subscribe("gateway_status_change", self._handle_health_status_change)
            self._subscription_active = True
            
            self.logger.info("Subscribed to gateway health status events")
            
        except Exception as e:
            self.logger.error(
                "Failed to subscribe to health events",
                error=str(e)
            )
            raise
    
    async def _handle_health_status_change(self, event_data: Dict[str, Any]):
        """
        Handle gateway health status change events.
        
        Args:
            event_data: Health status event data from event bus
        """
        try:
            gateway_id = event_data.get("gateway_id")
            current_status = event_data.get("current_status")
            
            if not gateway_id or not current_status:
                self.logger.warning(
                    "Invalid health status event data",
                    event_data=event_data
                )
                return
            
            # Update gateway state
            await self._update_gateway_health_state(gateway_id, current_status, event_data)
            
            # Check if failover is needed
            if current_status == "UNHEALTHY" and self.failover_enabled:
                await self._trigger_failover(gateway_id, event_data)
            
        except Exception as e:
            self.logger.error(
                "Error handling health status change",
                error=str(e),
                event_data=event_data
            )
    
    async def _update_gateway_health_state(self, gateway_id: str, status: str, event_data: Dict[str, Any]):
        """Update gateway health state based on health status event."""
        current_time = datetime.now()
        
        if gateway_id not in self.gateway_states:
            self.logger.warning(
                "Health event for unknown gateway",
                
                status=status
            )
            return
        
        gateway_state = self.gateway_states[gateway_id]
        previous_health = gateway_state.is_healthy
        
        # Update health status
        gateway_state.is_healthy = status == "HEALTHY"
        gateway_state.last_health_check = current_time
        
        # Update failure tracking
        if not gateway_state.is_healthy:
            gateway_state.consecutive_failures += 1
        else:
            gateway_state.consecutive_failures = 0
        
        # Log state change
        if previous_health != gateway_state.is_healthy:
            self.logger.info(
                "Gateway health state changed",
                
                previous_health=previous_health,
                current_health=gateway_state.is_healthy,
                consecutive_failures=gateway_state.consecutive_failures,
                status=status
            )
    
    async def _trigger_failover(self, failed_gateway_id: str, trigger_event: Dict[str, Any]):
        """
        Trigger failover for a failed gateway.
        
        Args:
            failed_gateway_id: ID of the failed gateway
            trigger_event: Health event that triggered the failover
        """
        if failed_gateway_id in self.active_failovers:
            self.logger.info(
                "Failover already in progress for gateway",
                gateway_id=failed_gateway_id,
                status=self.active_failovers[failed_gateway_id]
            )
            return
        
        # Check cooldown period
        failed_gateway_state = self.gateway_states.get(failed_gateway_id)
        if failed_gateway_state and failed_gateway_state.failover_cooldown_until:
            if datetime.now() < failed_gateway_state.failover_cooldown_until:
                self.logger.info(
                    "Failover in cooldown period",
                    gateway_id=failed_gateway_id,
                    cooldown_until=failed_gateway_state.failover_cooldown_until.isoformat()
                )
                return
        
        # Mark failover as in progress
        self.active_failovers[failed_gateway_id] = FailoverStatus.IN_PROGRESS
        
        try:
            # Execute failover
            await self._execute_failover(failed_gateway_id, trigger_event)
            
            # Mark as completed
            self.active_failovers[failed_gateway_id] = FailoverStatus.COMPLETED
            
        except Exception as e:
            self.logger.error(
                "Failover execution failed",
                gateway_id=failed_gateway_id,
                error=str(e)
            )
            self.active_failovers[failed_gateway_id] = FailoverStatus.FAILED
        
        # Clean up completed/failed failovers after delay
        asyncio.create_task(self._cleanup_failover_status(failed_gateway_id))
    
    async def _execute_failover(self, failed_gateway_id: str, trigger_event: Dict[str, Any]):
        """
        Execute the actual failover logic.
        
        Args:
            failed_gateway_id: ID of the failed gateway
            trigger_event: Health event that triggered the failover
        """
        start_time = datetime.now()
        
        # Find backup gateway
        backup_gateway_id = await self._select_backup_gateway(failed_gateway_id)
        
        if not backup_gateway_id:
            self.logger.error(
                "No healthy backup gateway available",
                failed_gateway_id=failed_gateway_id
            )
            raise Exception("No healthy backup gateway available")
        
        # Get contracts affected by this failover
        affected_contracts = self._get_contracts_for_gateway(failed_gateway_id)
        
        if not affected_contracts:
            self.logger.info(
                "No active contracts for failed gateway",
                failed_gateway_id=failed_gateway_id
            )
            return
        
        # Execute contract migration
        await self._migrate_contracts(failed_gateway_id, backup_gateway_id, affected_contracts)
        
        # Calculate execution time
        end_time = datetime.now()
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Update performance tracking
        self.total_failovers_executed += 1
        self.last_failover_time = end_time
        self.failover_execution_times.append(execution_time_ms)
        
        # Set cooldown period
        if failed_gateway_id in self.gateway_states:
            from datetime import timedelta
            cooldown_until = end_time + timedelta(seconds=self.failover_cooldown_seconds)
            self.gateway_states[failed_gateway_id].failover_cooldown_until = cooldown_until
        
        # Create and publish failover event
        failover_event = FailoverEvent(
            failed_gateway_id=failed_gateway_id,
            backup_gateway_id=backup_gateway_id,
            affected_contracts=affected_contracts,
            failover_duration_ms=execution_time_ms,
            metadata={
                "primary_priority": self.gateway_states[failed_gateway_id].priority if failed_gateway_id in self.gateway_states else None,
                "backup_priority": self.gateway_states[backup_gateway_id].priority if backup_gateway_id in self.gateway_states else None,
                "contracts_migrated": len(affected_contracts),
                "health_trigger": trigger_event.get("health_check_type", "unknown"),
                "execution_time_ms": execution_time_ms
            }
        )
        
        # Publish failover event
        await event_bus.publish("failover_executed", failover_event.to_dict())
        
        self.logger.info(
            "Failover executed successfully",
            failed_gateway_id=failed_gateway_id,
            backup_gateway_id=backup_gateway_id,
            affected_contracts=affected_contracts,
            execution_time_ms=execution_time_ms,
            total_failovers=self.total_failovers_executed
        )
    
    async def _select_backup_gateway(self, failed_gateway_id: str) -> Optional[str]:
        """
        Select the best backup gateway based on priority and health.
        
        Args:
            failed_gateway_id: ID of the failed gateway
            
        Returns:
            ID of the selected backup gateway or None if none available
        """
        failed_gateway_state = self.gateway_states.get(failed_gateway_id)
        if not failed_gateway_state:
            return None
        
        # Get healthy gateways sorted by priority (lower number = higher priority)
        healthy_gateways = [
            (gateway_id, state) for gateway_id, state in self.gateway_states.items()
            if state.is_healthy and gateway_id != failed_gateway_id
        ]
        
        if not healthy_gateways:
            return None
        
        # Sort by priority (lower number = higher priority)
        healthy_gateways.sort(key=lambda x: x[1].priority)
        
        # Prefer same gateway type if available
        same_type_gateways = [
            (gateway_id, state) for gateway_id, state in healthy_gateways
            if state.gateway_type == failed_gateway_state.gateway_type
        ]
        
        if same_type_gateways:
            selected_gateway_id = same_type_gateways[0][0]
            self.logger.info(
                "Selected backup gateway (same type)",
                failed_gateway_id=failed_gateway_id,
                backup_gateway_id=selected_gateway_id,
                backup_priority=same_type_gateways[0][1].priority,
                gateway_type=failed_gateway_state.gateway_type
            )
            return selected_gateway_id
        
        # Fall back to any healthy gateway
        selected_gateway_id = healthy_gateways[0][0]
        self.logger.info(
            "Selected backup gateway (different type)",
            failed_gateway_id=failed_gateway_id,
            backup_gateway_id=selected_gateway_id,
            backup_priority=healthy_gateways[0][1].priority,
            failed_type=failed_gateway_state.gateway_type,
            backup_type=healthy_gateways[0][1].gateway_type
        )
        return selected_gateway_id
    
    def _get_contracts_for_gateway(self, gateway_id: str) -> List[str]:
        """Get list of contracts currently subscribed to a gateway."""
        # Use gateway manager to get actual contracts
        try:
            return gateway_manager.get_gateway_contracts(gateway_id)
        except Exception as e:
            self.logger.error(
                "Failed to get contracts from gateway manager",
                
                error=str(e)
            )
            # Fallback to internal tracking
            contracts = []
            for contract_id, subscription in self.contract_subscriptions.items():
                if subscription.gateway_id == gateway_id and subscription.is_active:
                    contracts.append(subscription.symbol)
            return contracts
    
    async def _migrate_contracts(self, failed_gateway_id: str, backup_gateway_id: str, contracts: List[str]):
        """
        Migrate contract subscriptions from failed gateway to backup.
        
        Args:
            failed_gateway_id: ID of the failed gateway
            backup_gateway_id: ID of the backup gateway
            contracts: List of contract symbols to migrate
        """
        migration_tasks = []
        
        for contract_symbol in contracts:
            # Create migration task for each contract
            task = self._migrate_single_contract(failed_gateway_id, backup_gateway_id, contract_symbol)
            migration_tasks.append(task)
        
        # Execute all migrations concurrently
        results = await asyncio.gather(*migration_tasks, return_exceptions=True)
        
        # Log results
        successful_migrations = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(
                    "Contract migration failed",
                    contract=contracts[i],
                    failed_gateway_id=failed_gateway_id,
                    backup_gateway_id=backup_gateway_id,
                    error=str(result)
                )
            else:
                successful_migrations += 1
        
        self.logger.info(
            "Contract migration completed",
            total_contracts=len(contracts),
            successful_migrations=successful_migrations,
            failed_migrations=len(contracts) - successful_migrations
        )
    
    async def _migrate_single_contract(self, failed_gateway_id: str, backup_gateway_id: str, contract_symbol: str):
        """
        Migrate a single contract subscription.
        
        Args:
            failed_gateway_id: ID of the failed gateway
            backup_gateway_id: ID of the backup gateway  
            contract_symbol: Contract symbol to migrate
        """
        try:
            # Use gateway manager for actual contract migration
            success = await gateway_manager.migrate_contracts(
                failed_gateway_id, 
                backup_gateway_id, 
                [contract_symbol]
            )
            
            if not success:
                raise Exception("Gateway manager migration failed")
            
            # Update subscription tracking
            contract_key = f"{failed_gateway_id}:{contract_symbol}"
            if contract_key in self.contract_subscriptions:
                # Mark old subscription as inactive
                self.contract_subscriptions[contract_key].is_active = False
                
                # Create new subscription record
                new_contract_key = f"{backup_gateway_id}:{contract_symbol}"
                self.contract_subscriptions[new_contract_key] = ContractSubscription(
                    symbol=contract_symbol,
                    gateway_id=backup_gateway_id,
                    subscribed_at=datetime.now(),
                    is_active=True
                )
            
            self.logger.debug(
                "Contract migrated successfully",
                contract=contract_symbol,
                from_gateway=failed_gateway_id,
                to_gateway=backup_gateway_id
            )
            
        except Exception as e:
            self.logger.error(
                "Single contract migration failed",
                contract=contract_symbol,
                from_gateway=failed_gateway_id,
                to_gateway=backup_gateway_id,
                error=str(e)
            )
            raise
    
    async def _cleanup_failover_status(self, gateway_id: str):
        """Clean up failover status after delay."""
        await asyncio.sleep(60)  # Keep status for 1 minute
        if gateway_id in self.active_failovers:
            del self.active_failovers[gateway_id]
    
    async def _maintenance_task(self):
        """Background maintenance task for cleanup and monitoring."""
        while self._running:
            try:
                await asyncio.sleep(30)  # Run every 30 seconds
                
                # Clean up old subscription records
                await self._cleanup_old_subscriptions()
                
                # Trim performance tracking data
                self._trim_performance_data()
                
            except Exception as e:
                self.logger.error(
                    "Maintenance task error",
                    error=str(e)
                )
    
    async def _cleanup_old_subscriptions(self):
        """Clean up old inactive subscription records."""
        current_time = datetime.now()
        cutoff_time = current_time.replace(hour=current_time.hour - 1)  # 1 hour ago
        
        keys_to_remove = []
        for key, subscription in self.contract_subscriptions.items():
            if not subscription.is_active and subscription.subscribed_at < cutoff_time:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.contract_subscriptions[key]
        
        if keys_to_remove:
            self.logger.debug(
                "Cleaned up old subscription records",
                count=len(keys_to_remove)
            )
    
    def _trim_performance_data(self):
        """Trim performance tracking data to prevent memory growth."""
        # Keep only last 100 failover times
        if len(self.failover_execution_times) > 100:
            self.failover_execution_times = self.failover_execution_times[-100:]
    
    def _calculate_average_failover_time(self) -> Optional[float]:
        """Calculate average failover execution time."""
        if not self.failover_execution_times:
            return None
        return sum(self.failover_execution_times) / len(self.failover_execution_times)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the quote aggregation engine."""
        return {
            "running": self._running,
            "failover_enabled": self.failover_enabled,
            "total_gateways": len(self.gateway_states),
            "healthy_gateways": sum(1 for state in self.gateway_states.values() if state.is_healthy),
            "active_subscriptions": len([s for s in self.contract_subscriptions.values() if s.is_active]),
            "active_failovers": len(self.active_failovers),
            "total_failovers_executed": self.total_failovers_executed,
            "last_failover_time": self.last_failover_time.isoformat() if self.last_failover_time else None,
            "average_failover_time_ms": self._calculate_average_failover_time(),
            "configuration": {
                "timeout_seconds": self.failover_timeout_seconds,
                "cooldown_seconds": self.failover_cooldown_seconds,
                "max_consecutive_failures": self.max_consecutive_failures
            }
        }


# Global quote aggregation engine instance
quote_aggregation_engine = QuoteAggregationEngine()