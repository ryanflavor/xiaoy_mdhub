"""
Trading Time Manager Service for Market Hours Validation.
Handles trading session validation, market status checking, and trading calendar management.
"""
import os
import logging
from datetime import datetime, timezone, time, date, timedelta
from typing import Dict, List, Tuple, Optional
import structlog
from enum import Enum

# China timezone (UTC+8)
CHINA_TZ = timezone(timedelta(hours=8))


class TradingStatus(Enum):
    """Trading status enumeration"""
    TRADING = "trading"
    NON_TRADING = "non_trading"
    PRE_TRADING = "pre_trading"
    POST_TRADING = "post_trading"


class TradingTimeRange:
    """Represents a single trading time range"""
    def __init__(self, start: str, end: str, buffer_minutes: int = 0):
        self.original_start = self._parse_time(start)
        self.original_end = self._parse_time(end)
        self.buffer_minutes = buffer_minutes
        
        # Apply buffer for actual checking
        self.start = self._apply_buffer_to_time(self.original_start, -buffer_minutes)
        self.end = self._apply_buffer_to_time(self.original_end, buffer_minutes)
        
        self.is_overnight = self.original_end < self.original_start  # Handle overnight sessions like 21:00-02:30
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format"""
        hour, minute = map(int, time_str.split(':'))
        return time(hour, minute)
    
    def _apply_buffer_to_time(self, original_time: time, buffer_minutes: int) -> time:
        """Apply buffer to time, handling day overflow"""
        from datetime import datetime, timedelta
        
        # Convert time to datetime for calculation
        dt = datetime.combine(date.today(), original_time)
        dt += timedelta(minutes=buffer_minutes)
        
        return dt.time()
    
    def contains_time(self, check_time: time, check_date: date) -> bool:
        """Check if given time is within this range (with buffer), handling overnight sessions"""
        if not self.is_overnight:
            # Normal session within same day
            return self.start <= check_time <= self.end
        else:
            # Overnight session (e.g., 21:00-02:30)
            # Check if time is after start (same day) or before end (next day)
            return check_time >= self.start or check_time <= self.end


class TradingSession:
    """Represents a trading session with multiple time ranges"""
    def __init__(self, name: str, ranges: List[TradingTimeRange], market_type: str):
        self.name = name
        self.ranges = ranges
        self.market_type = market_type
    
    def is_active(self, check_time: time, check_date: date) -> bool:
        """Check if session is active at given time"""
        return any(range_.contains_time(check_time, check_date) for range_ in self.ranges)


class TradingTimeManager:
    """
    Manages trading time validation and market status for CTP and SOPT gateways.
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self.buffer_minutes = int(os.getenv("TRADING_TIME_BUFFER_MINUTES", "15"))
        self.enable_trading_time_check = os.getenv("ENABLE_TRADING_TIME_CHECK", "true").lower() == "true"
        self.force_gateway_connection = os.getenv("FORCE_GATEWAY_CONNECTION", "false").lower() == "true"
        
        # Initialize trading sessions
        self.sessions = self._initialize_trading_sessions()
        
        # China holidays (simplified - in production should use proper holiday API)
        # Format: YYYY-MM-DD
        self.holidays = self._load_holidays()
        
        self.logger.info(
            "Trading Time Manager initialized",
            buffer_minutes=self.buffer_minutes,
            enable_check=self.enable_trading_time_check,
            force_connection=self.force_gateway_connection,
            sessions_count=len(self.sessions)
        )
    
    def _initialize_trading_sessions(self) -> List[TradingSession]:
        """Initialize trading sessions from environment configuration"""
        sessions = []
        
        # CTP sessions (futures and options) - using actual trading hours as default
        ctp_hours = os.getenv("CTP_TRADING_HOURS", "09:00-11:30,13:30-15:00,21:00-02:30")
        ctp_ranges = self._parse_trading_hours(ctp_hours)
        sessions.append(TradingSession("CTP", ctp_ranges, "CTP"))
        
        # SOPT sessions (stock options) - using actual trading hours as default
        sopt_hours = os.getenv("SOPT_TRADING_HOURS", "09:30-11:30,13:00-15:00")
        sopt_ranges = self._parse_trading_hours(sopt_hours)
        sessions.append(TradingSession("SOPT", sopt_ranges, "SOPT"))
        
        return sessions
    
    def _parse_trading_hours(self, hours_str: str) -> List[TradingTimeRange]:
        """Parse trading hours string into TradingTimeRange objects"""
        ranges = []
        
        for range_str in hours_str.split(','):
            range_str = range_str.strip()
            if '-' in range_str:
                start, end = range_str.split('-')
                ranges.append(TradingTimeRange(start.strip(), end.strip(), self.buffer_minutes))
        
        return ranges
    
    def _load_holidays(self) -> List[date]:
        """Load China market holidays (simplified implementation)"""
        current_year = datetime.now().year
        
        # Basic holidays for current year (should be extended with proper holiday API)
        holidays = [
            # New Year
            date(current_year, 1, 1),
            # Spring Festival (example dates - should be calculated properly)
            date(current_year, 2, 10),
            date(current_year, 2, 11),
            date(current_year, 2, 12),
            date(current_year, 2, 13),
            date(current_year, 2, 14),
            date(current_year, 2, 15),
            date(current_year, 2, 16),
            # Qingming Festival
            date(current_year, 4, 5),
            # Labor Day
            date(current_year, 5, 1),
            # National Day
            date(current_year, 10, 1),
            date(current_year, 10, 2),
            date(current_year, 10, 3),
        ]
        
        return holidays
    
    def is_trading_day(self, check_date: Optional[date] = None) -> bool:
        """Check if given date is a trading day (not weekend or holiday)"""
        if check_date is None:
            check_date = datetime.now(CHINA_TZ).date()
        
        # Check if weekend
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if holiday
        if check_date in self.holidays:
            return False
        
        return True
    
    def is_trading_time(self, gateway_type: str = "CTP", check_datetime: Optional[datetime] = None) -> bool:
        """
        Check if current time is within trading hours for given gateway type.
        
        Args:
            gateway_type: 'CTP' or 'SOPT'
            check_datetime: Optional datetime to check (defaults to now)
            
        Returns:
            True if within trading hours, False otherwise
        """
        # Force connection mode bypasses time check
        if self.force_gateway_connection:
            self.logger.debug(
                "Force connection mode enabled - bypassing trading time check",
                gateway_type=gateway_type
            )
            return True
        
        # Trading time check disabled
        if not self.enable_trading_time_check:
            self.logger.debug(
                "Trading time check disabled - allowing connection",
                gateway_type=gateway_type
            )
            return True
        
        if check_datetime is None:
            check_datetime = datetime.now(CHINA_TZ)
        
        check_date = check_datetime.date()
        check_time = check_datetime.time()
        
        # Check if trading day
        if not self.is_trading_day(check_date):
            self.logger.debug(
                "Non-trading day",
                gateway_type=gateway_type,
                check_date=check_date.isoformat(),
                weekday=check_date.weekday()
            )
            return False
        
        # Find relevant session
        session = self._get_session_by_type(gateway_type)
        if not session:
            self.logger.warning(
                "No trading session found for gateway type",
                gateway_type=gateway_type
            )
            return False
        
        # Check if time is within session
        is_active = session.is_active(check_time, check_date)
        
        self.logger.debug(
            "Trading time check result",
            gateway_type=gateway_type,
            check_time=check_time.isoformat(),
            check_date=check_date.isoformat(),
            is_active=is_active,
            session_name=session.name
        )
        
        return is_active
    
    def _get_session_by_type(self, gateway_type: str) -> Optional[TradingSession]:
        """Get trading session by gateway type"""
        return next((s for s in self.sessions if s.market_type == gateway_type), None)
    
    def get_trading_status(self, check_datetime: Optional[datetime] = None) -> Dict:
        """
        Get comprehensive trading status information.
        
        Returns:
            Dictionary with current trading status, next session info, etc.
        """
        if check_datetime is None:
            check_datetime = datetime.now(CHINA_TZ)
        
        check_date = check_datetime.date()
        check_time = check_datetime.time()
        
        # Check if trading day
        is_trading_day = self.is_trading_day(check_date)
        
        # Check each gateway type
        ctp_trading = self.is_trading_time("CTP", check_datetime)
        sopt_trading = self.is_trading_time("SOPT", check_datetime)
        
        # Determine overall status
        if ctp_trading or sopt_trading:
            status = TradingStatus.TRADING
        elif is_trading_day:
            # Trading day but not in trading hours
            next_session = self._get_next_session_start(check_datetime)
            if next_session and (next_session - check_datetime).total_seconds() < 3600:  # Within 1 hour
                status = TradingStatus.PRE_TRADING
            else:
                status = TradingStatus.POST_TRADING
        else:
            status = TradingStatus.NON_TRADING
        
        # Get current and next session info
        current_session_name = None
        if ctp_trading and sopt_trading:
            current_session_name = "CTP & SOPT"
        elif ctp_trading:
            current_session_name = "CTP"
        elif sopt_trading:
            current_session_name = "SOPT"
        
        # Get next session info for each gateway separately
        ctp_next_session = None
        sopt_next_session = None
        
        if not ctp_trading:
            ctp_next_session = self._get_next_session_start_for_gateway("CTP", check_datetime)
        
        if not sopt_trading:
            sopt_next_session = self._get_next_session_start_for_gateway("SOPT", check_datetime)
        
        # Only show overall next session if any gateway is closed
        next_session_start = None
        next_session_name = None
        
        if not ctp_trading or not sopt_trading:
            # Find the earliest next session among closed gateways
            earliest_session = None
            earliest_time = None
            
            if not ctp_trading and ctp_next_session:
                earliest_session = "CTP"
                earliest_time = ctp_next_session
            
            if not sopt_trading and sopt_next_session:
                if earliest_time is None or sopt_next_session < earliest_time:
                    earliest_session = "SOPT"
                    earliest_time = sopt_next_session
            
            if earliest_time:
                next_session_start = earliest_time
                next_session_name = earliest_session
        
        return {
            "current_time": check_datetime.isoformat(),
            "current_date": check_date.isoformat(),
            "is_trading_day": is_trading_day,
            "is_trading_time": ctp_trading or sopt_trading,
            "status": status.value,
            "ctp_trading": ctp_trading,
            "sopt_trading": sopt_trading,
            "current_session_name": current_session_name,
            "next_session_start": next_session_start.isoformat() if next_session_start else None,
            "next_session_name": next_session_name,
            "ctp_next_session": ctp_next_session.isoformat() if ctp_next_session else None,
            "sopt_next_session": sopt_next_session.isoformat() if sopt_next_session else None,
            "sessions": [
                {
                    "name": session.name,
                    "market_type": session.market_type,
                    "ranges": [
                        {
                            "start": range_.original_start.strftime("%H:%M"),
                            "end": range_.original_end.strftime("%H:%M")
                        }
                        for range_ in session.ranges
                    ]
                }
                for session in self.sessions
            ]
        }
    
    def _get_next_session_start(self, check_datetime: datetime) -> Optional[datetime]:
        """Get the start time of the next trading session"""
        check_date = check_datetime.date()
        check_time = check_datetime.time()
        
        # Collect all upcoming session starts with their session info
        upcoming_sessions = []
        
        # Check remaining sessions today for all gateways
        for session in self.sessions:
            for range_ in session.ranges:
                if not range_.is_overnight:
                    # Same day session - use original start time for display
                    if range_.original_start > check_time:
                        session_start = datetime.combine(check_date, range_.original_start, CHINA_TZ)
                        upcoming_sessions.append((session_start, session.name))
                else:
                    # Overnight session - use original start time for display
                    if range_.original_start > check_time:
                        session_start = datetime.combine(check_date, range_.original_start, CHINA_TZ)
                        upcoming_sessions.append((session_start, session.name))
                    # Check next day for overnight session end
                    next_date = check_date + timedelta(days=1)
                    if self.is_trading_day(next_date):
                        session_start = datetime.combine(next_date, range_.original_start, CHINA_TZ)
                        upcoming_sessions.append((session_start, session.name))
        
        # If we have upcoming sessions today, return the earliest one
        if upcoming_sessions:
            upcoming_sessions.sort(key=lambda x: x[0])  # Sort by time
            return upcoming_sessions[0][0]  # Return earliest time
        
        # No more sessions today, check next trading day
        next_date = check_date + timedelta(days=1)
        while not self.is_trading_day(next_date) and (next_date - check_date).days < 7:
            next_date += timedelta(days=1)
        
        if self.is_trading_day(next_date):
            # Collect all first sessions of next trading day
            next_day_sessions = []
            for session in self.sessions:
                if session.ranges:
                    first_range = min(session.ranges, key=lambda r: r.original_start)
                    session_start = datetime.combine(next_date, first_range.original_start, CHINA_TZ)
                    next_day_sessions.append((session_start, session.name))
            
            # Return earliest session start of next trading day
            if next_day_sessions:
                next_day_sessions.sort(key=lambda x: x[0])
                return next_day_sessions[0][0]
        
        return None
    
    def _get_next_session_name(self, check_datetime: datetime) -> Optional[str]:
        """Get the name of the next trading session"""
        check_date = check_datetime.date()
        check_time = check_datetime.time()
        
        # Collect all upcoming session starts with their session info
        upcoming_sessions = []
        
        # Check remaining sessions today for all gateways
        for session in self.sessions:
            for range_ in session.ranges:
                if not range_.is_overnight:
                    # Same day session - use original start time for display
                    if range_.original_start > check_time:
                        session_start = datetime.combine(check_date, range_.original_start, CHINA_TZ)
                        upcoming_sessions.append((session_start, session.name))
                else:
                    # Overnight session - use original start time for display
                    if range_.original_start > check_time:
                        session_start = datetime.combine(check_date, range_.original_start, CHINA_TZ)
                        upcoming_sessions.append((session_start, session.name))
                    # Check next day for overnight session end
                    next_date = check_date + timedelta(days=1)
                    if self.is_trading_day(next_date):
                        session_start = datetime.combine(next_date, range_.original_start, CHINA_TZ)
                        upcoming_sessions.append((session_start, session.name))
        
        # If we have upcoming sessions today, find all sessions at the earliest time
        if upcoming_sessions:
            upcoming_sessions.sort(key=lambda x: x[0])  # Sort by time
            earliest_time = upcoming_sessions[0][0]
            
            # Find all sessions that start at the same earliest time
            simultaneous_sessions = [session_name for start_time, session_name in upcoming_sessions 
                                   if start_time == earliest_time]
            
            # Return combined name if multiple gateways start simultaneously
            if len(simultaneous_sessions) > 1:
                return " & ".join(sorted(simultaneous_sessions))
            else:
                return simultaneous_sessions[0]
        
        # No more sessions today, check next trading day
        next_date = check_date + timedelta(days=1)
        while not self.is_trading_day(next_date) and (next_date - check_date).days < 7:
            next_date += timedelta(days=1)
        
        if self.is_trading_day(next_date):
            # Collect all first sessions of next trading day
            next_day_sessions = []
            for session in self.sessions:
                if session.ranges:
                    first_range = min(session.ranges, key=lambda r: r.original_start)
                    session_start = datetime.combine(next_date, first_range.original_start, CHINA_TZ)
                    next_day_sessions.append((session_start, session.name))
            
            # Find sessions at earliest time of next trading day
            if next_day_sessions:
                next_day_sessions.sort(key=lambda x: x[0])
                earliest_time = next_day_sessions[0][0]
                
                # Find all sessions that start at the same earliest time
                simultaneous_sessions = [session_name for start_time, session_name in next_day_sessions 
                                       if start_time == earliest_time]
                
                # Return combined name if multiple gateways start simultaneously
                if len(simultaneous_sessions) > 1:
                    return " & ".join(sorted(simultaneous_sessions))
                else:
                    return simultaneous_sessions[0]
        
        return None
    
    def should_connect_gateway(self, gateway_type: str) -> bool:
        """
        Determine if gateway should connect based on trading time rules.
        
        Args:
            gateway_type: 'CTP' or 'SOPT'
            
        Returns:
            True if gateway should connect, False otherwise
        """
        should_connect = self.is_trading_time(gateway_type)
        
        self.logger.info(
            "Gateway connection decision",
            gateway_type=gateway_type,
            should_connect=should_connect,
            force_connection=self.force_gateway_connection,
            enable_check=self.enable_trading_time_check
        )
        
        return should_connect
    
    def _get_next_session_start_for_gateway(self, gateway_type: str, check_datetime: datetime) -> Optional[datetime]:
        """
        Get the next trading session start time for a specific gateway type.
        
        Args:
            gateway_type: 'CTP' or 'SOPT'
            check_datetime: Current datetime to check from
            
        Returns:
            Datetime of next session start for the specified gateway, or None if not found
        """
        check_date = check_datetime.date()
        check_time = check_datetime.time()
        
        # Find sessions for the specific gateway type
        target_sessions = [session for session in self.sessions if session.market_type == gateway_type]
        
        if not target_sessions:
            return None
        
        # Collect upcoming sessions for this gateway type
        upcoming_sessions = []
        
        # Check remaining sessions today
        for session in target_sessions:
            for range_ in session.ranges:
                # Use original_start (actual trading time) for display
                if range_.original_start > check_time:
                    session_start = datetime.combine(check_date, range_.original_start, CHINA_TZ)
                    upcoming_sessions.append(session_start)
                elif range_.is_overnight:
                    # For overnight sessions, also check if they continue to next day
                    next_date = check_date + timedelta(days=1)
                    if self.is_trading_day(next_date):
                        session_start = datetime.combine(next_date, range_.original_start, CHINA_TZ)
                        upcoming_sessions.append(session_start)
        
        # If we have upcoming sessions today, return the earliest one
        if upcoming_sessions:
            upcoming_sessions.sort()
            return upcoming_sessions[0]
        
        # No more sessions today, check next trading day
        next_date = check_date + timedelta(days=1)
        while not self.is_trading_day(next_date) and (next_date - check_date).days < 7:
            next_date += timedelta(days=1)
        
        if self.is_trading_day(next_date):
            # Get first session of next trading day for this gateway
            next_day_sessions = []
            for session in target_sessions:
                if session.ranges:
                    first_range = min(session.ranges, key=lambda r: r.original_start)
                    session_start = datetime.combine(next_date, first_range.original_start, CHINA_TZ)
                    next_day_sessions.append(session_start)
            
            if next_day_sessions:
                return min(next_day_sessions)
        
        return None


# Global trading time manager instance
trading_time_manager = TradingTimeManager()