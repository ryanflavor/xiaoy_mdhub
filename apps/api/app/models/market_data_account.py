"""
Market Data Account SQLAlchemy model.

This module defines the database model for market data accounts, which stores
configuration for different trading gateways (CTP, SOPT) with their connection
settings and metadata.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class MarketDataAccount(Base):
    """
    Market Data Account model for storing gateway configuration.
    
    This table stores account configurations for different trading gateways
    including connection settings, priority, and enabled status.
    """
    
    __tablename__ = "market_data_accounts"
    
    # Primary key - unique identifier for the account
    id = Column(String(100), primary_key=True, nullable=False)
    
    # Gateway type - restricted to supported types
    gateway_type = Column(String(10), nullable=False, index=True)
    
    # JSON field for gateway-specific settings
    settings = Column(JSON, nullable=False)
    
    # Priority for account usage (lower = higher priority)
    priority = Column(Integer, nullable=False, index=True, default=1)
    
    # Whether this account is enabled
    is_enabled = Column(Boolean, nullable=False, index=True, default=True)
    
    # Optional description
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<MarketDataAccount(id='{self.id}', gateway_type='{self.gateway_type}', priority={self.priority}, enabled={self.is_enabled})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            "id": self.id,
            "gateway_type": self.gateway_type,
            "settings": self.settings,
            "priority": self.priority,
            "is_enabled": self.is_enabled,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketDataAccount":
        """Create model instance from dictionary."""
        return cls(
            id=data["id"],
            gateway_type=data["gateway_type"],
            settings=data["settings"],
            priority=data.get("priority", 1),
            is_enabled=data.get("is_enabled", True),
            description=data.get("description"),
        )