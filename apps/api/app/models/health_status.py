"""
Health monitoring data models and status enums.
"""

from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass


class GatewayStatus(Enum):
    """Gateway health status states."""
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    CONNECTING = "CONNECTING"
    DISCONNECTED = "DISCONNECTED"


@dataclass
class HealthMetrics:
    """Health metrics for a gateway."""
    last_heartbeat: Optional[datetime] = None
    connection_status: Optional[str] = None
    canary_contract_timestamp: Optional[datetime] = None
    error_count: int = 0
    last_error_message: Optional[str] = None
    health_check_duration_ms: Optional[float] = None
    retry_count: int = 0


@dataclass
class GatewayHealthStatus:
    """Complete health status for a gateway."""
    gateway_id: str
    gateway_type: str
    status: GatewayStatus
    metrics: HealthMetrics
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "gateway_id": self.gateway_id,
            "gateway_type": self.gateway_type,
            "status": self.status.value,
            "metrics": {
                "last_heartbeat": self.metrics.last_heartbeat.isoformat() if self.metrics.last_heartbeat else None,
                "connection_status": self.metrics.connection_status,
                "canary_contract_timestamp": self.metrics.canary_contract_timestamp.isoformat() if self.metrics.canary_contract_timestamp else None,
                "error_count": self.metrics.error_count,
                "last_error_message": self.metrics.last_error_message,
                "health_check_duration_ms": self.metrics.health_check_duration_ms,
                "retry_count": self.metrics.retry_count
            },
            "last_updated": self.last_updated.isoformat()
        }


@dataclass 
class HealthStatusEvent:
    """Health status change event."""
    event_type: str
    timestamp: datetime
    gateway_id: str
    gateway_type: str
    previous_status: GatewayStatus
    current_status: GatewayStatus
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format matching example JSON."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "gateway_id": self.gateway_id,
            "gateway_type": self.gateway_type,
            "previous_status": self.previous_status.value,
            "current_status": self.current_status.value,
            "metadata": self.metadata
        }