"""
Unified timezone utilities for the Market Data Hub.

This module provides standardized timezone handling ensuring all datetime operations
use China timezone (Asia/Shanghai) consistently across the application.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

# China timezone definition
CHINA_TZ = timezone(timedelta(hours=8))

def now_china() -> datetime:
    """
    Get current datetime in China timezone.
    
    Returns:
        datetime: Current datetime with China timezone
    """
    return datetime.now(CHINA_TZ)

def utc_to_china(dt: datetime) -> datetime:
    """
    Convert UTC datetime to China timezone.
    
    Args:
        dt: UTC datetime (with or without timezone info)
        
    Returns:
        datetime: Datetime converted to China timezone
    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CHINA_TZ)

def naive_to_china(dt: datetime) -> datetime:
    """
    Convert naive datetime to China timezone.
    Assumes the naive datetime is already in China timezone.
    
    Args:
        dt: Naive datetime (no timezone info)
        
    Returns:
        datetime: Datetime with China timezone applied
    """
    return dt.replace(tzinfo=CHINA_TZ)

def to_china_tz(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert any datetime to China timezone with null safety.
    
    Args:
        dt: Datetime to convert (can be None)
        
    Returns:
        Optional[datetime]: Converted datetime or None
    """
    if dt is None:
        return None
        
    if dt.tzinfo is None:
        # Treat naive datetime as already in China timezone
        return dt.replace(tzinfo=CHINA_TZ)
    else:
        # Convert from other timezone to China timezone
        return dt.astimezone(CHINA_TZ)

def format_china_time(dt: Optional[datetime] = None) -> str:
    """
    Format datetime as ISO string in China timezone.
    
    Args:
        dt: Datetime to format (defaults to current time)
        
    Returns:
        str: ISO formatted datetime string with China timezone
    """
    if dt is None:
        dt = now_china()
    else:
        dt = to_china_tz(dt)
    
    return dt.isoformat()