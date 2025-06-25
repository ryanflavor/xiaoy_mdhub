"""
Gateway Manager Service for CTP connectivity and health monitoring.
Handles vnpy gateway lifecycle, connection monitoring, and tick data processing.
"""
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import structlog
import psutil
import os

# Conditional imports for gateways - handle gracefully if not available
try:
    from vnpy.event import EventEngine, Event
    from vnpy.trader.setting import SETTINGS
    from vnpy.trader.engine import MainEngine
    from vnpy_ctp import CtpGateway
    CTP_AVAILABLE = True
except ImportError as e:
    # Mock classes for testing when CTP is not available
    CTP_AVAILABLE = False
    print(f"CTP not available: {e}")

try:
    from vnpy_sopt.gateway.sopt_gateway import SoptGateway
    SOPT_AVAILABLE = True
except ImportError as e:
    SOPT_AVAILABLE = False
    print(f"SOPT not available: {e}")
    
    import random
    from datetime import datetime, timezone
    
    class MockTickData:
        """Mock tick data for testing"""
        def __init__(self, symbol="rb2501.SHFE"):
            self.symbol = symbol
            self.datetime = datetime.now(timezone.utc)
            self.last_price = round(3800 + random.uniform(-50, 50), 2)
            self.volume = random.randint(100, 1000)
            self.last_volume = random.randint(1, 10)
            self.bid_price_1 = self.last_price - random.uniform(0.5, 2.0)
            self.ask_price_1 = self.last_price + random.uniform(0.5, 2.0)
            self.bid_volume_1 = random.randint(10, 100)
            self.ask_volume_1 = random.randint(10, 100)
    
    class Event:
        def __init__(self, event_type="", data=None):
            self.type = event_type
            self.data = data
    
    class EventEngine:
        def __init__(self):
            self._handlers = {}
            self._mock_running = False
        
        def register(self, event_type, handler):
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
        
        def put(self, event):
            """Simulate putting an event"""
            if event.type in self._handlers:
                for handler in self._handlers[event.type]:
                    try:
                        handler(event)
                    except Exception as e:
                        print(f"Mock event handler error: {e}")
        
        def start_mock_data(self):
            """Start generating mock tick data"""
            import threading
            import time
            
            def generate_mock_ticks():
                while self._mock_running:
                    # Generate mock tick
                    tick = MockTickData()
                    event = Event("eTick", tick)
                    self.put(event)
                    time.sleep(1)  # 1 tick per second
            
            self._mock_running = True
            threading.Thread(target=generate_mock_ticks, daemon=True).start()
        
        def stop(self):
            self._mock_running = False
    
    class MainEngine:
        def __init__(self, event_engine):
            self.event_engine = event_engine
        
        def add_gateway(self, gateway_class):
            pass
        
        def connect(self, settings, gateway_name):
            # Simulate connection success after delay
            import threading
            import time
            
            def simulate_connection():
                time.sleep(2)  # Simulate connection delay
                
                # Simulate connection success event
                class MockGatewayData:
                    def __init__(self):
                        self.gateway_name = gateway_name
                        self.status = "connected"
                
                event = Event("eGateway", MockGatewayData())
                self.event_engine.put(event)
                
                # Start mock tick data
                self.event_engine.start_mock_data()
            
            threading.Thread(target=simulate_connection, daemon=True).start()
        
        def close(self):
            if hasattr(self.event_engine, 'stop'):
                self.event_engine.stop()
    
    class CtpGateway:
        pass

from app.services.zmq_publisher import zmq_publisher
from app.services.database_service import database_service


class GatewayManager:
    """
    Manages CTP gateway connections with health monitoring and performance tracking.
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self.main_engines: Dict[str, MainEngine] = {}
        self.event_engines: Dict[str, EventEngine] = {}
        self.active_accounts: List[Dict[str, Any]] = []
        self.gateway_connections: Dict[str, bool] = {}
        self.connection_start_times: Dict[str, Optional[datetime]] = {}
        self.connection_attempts: Dict[str, int] = {}
        self.tick_count = 0
        self.last_tick_time: Optional[datetime] = None
        self.tick_rate_window = []
        self.performance_log_interval = 30  # seconds
        self.last_performance_log = time.time()
        self._enable_gateway = os.getenv("ENABLE_CTP_GATEWAY", "true").lower() == "true"
        
        # Performance monitoring
        self.process = psutil.Process()
        self.startup_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
    async def initialize(self) -> bool:
        """
        Initialize gateway connections from database accounts.
        Returns True if initialization successful, False otherwise.
        """
        if not self._enable_gateway:
            self.logger.info("Gateway Manager disabled via ENABLE_CTP_GATEWAY environment variable")
            return False
        
        # Initialize ZMQ publisher first
        zmq_init_success = await zmq_publisher.initialize()
        if not zmq_init_success:
            self.logger.warning("ZMQ Publisher initialization failed, continuing without publishing")
        
        try:
            # Load enabled accounts from database
            accounts = await self._load_accounts_from_database()
            if not accounts:
                self.logger.warning("No enabled accounts found in database")
                return True  # Not an error, just no accounts to initialize
            
            self.logger.info(f"Loading {len(accounts)} enabled accounts from database")
            
            # Initialize each account's gateway
            success_count = 0
            for account in accounts:
                try:
                    if await self._initialize_account_gateway(account):
                        success_count += 1
                except Exception as e:
                    self.logger.error(
                        "Account gateway initialization failed",
                        account_id=account.get('id', 'unknown'),
                        error=str(e)
                    )
            
            self.logger.info(
                "Gateway Manager initialization complete",
                total_accounts=len(accounts),
                successful_initializations=success_count
            )
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(
                "Gateway Manager initialization failed",
                error=str(e)
            )
            return False
    
    async def _load_accounts_from_database(self) -> List[Dict[str, Any]]:
        """Load enabled accounts from database."""
        try:
            # Check if database is available
            if not await database_service.is_available():
                self.logger.warning("Database service unavailable, no accounts loaded")
                return []
            
            # Get enabled accounts, ordered by priority
            accounts = await database_service.get_all_accounts(enabled_only=True)
            
            # Convert to dict format for easier handling
            account_dicts = []
            for account in accounts:
                account_dict = {
                    'id': account.id,
                    'gateway_type': account.gateway_type,
                    'settings': account.settings,
                    'priority': account.priority,
                    'description': account.description
                }
                account_dicts.append(account_dict)
            
            self.active_accounts = account_dicts
            return account_dicts
            
        except Exception as e:
            self.logger.error("Failed to load accounts from database", error=str(e))
            return []
    
    def _register_event_handlers(self, event_engine: EventEngine, account_id: str):
        """Register event handlers for vnpy events for a specific account."""
        if not event_engine:
            return
            
        # Gateway connection events
        event_engine.register("eGateway", lambda event: self._on_gateway_event(event, account_id))
        
        # Tick data events
        event_engine.register("eTick", lambda event: self._on_tick_event(event, account_id))
        
        # Log events
        event_engine.register("eLog", lambda event: self._on_log_event(event, account_id))
    
    async def _initialize_account_gateway(self, account: Dict[str, Any]) -> bool:
        """Initialize gateway for a specific account."""
        account_id = account['id']
        gateway_type = account['gateway_type']
        settings = account['settings']
        
        try:
            self.logger.info(
                "Initializing account gateway",
                account_id=account_id,
                gateway_type=gateway_type,
                priority=account['priority']
            )
            
            # Initialize based on availability and type (case insensitive)
            gateway_type_lower = gateway_type.lower()
            if gateway_type_lower == 'ctp' and not CTP_AVAILABLE:
                # Mock mode for CTP
                mock_mode = os.getenv("ENABLE_CTP_MOCK", "true").lower() == "true"
                if mock_mode:
                    return await self._initialize_mock_gateway(account)
                else:
                    self.logger.warning(
                        "CTP Gateway not available - missing native dependencies",
                        account_id=account_id,
                        gateway_type=gateway_type
                    )
                    return False
            elif gateway_type_lower == 'sopt' and not SOPT_AVAILABLE:
                # Mock mode for SOPT
                mock_mode = os.getenv("ENABLE_SOPT_MOCK", "true").lower() == "true"
                if mock_mode:
                    return await self._initialize_mock_gateway(account)
                else:
                    self.logger.warning(
                        "SOPT Gateway not available - missing native dependencies",
                        account_id=account_id,
                        gateway_type=gateway_type
                    )
                    return False
            
            # Real gateway initialization
            if gateway_type_lower == 'ctp':
                return await self._initialize_ctp_gateway(account)
            elif gateway_type_lower == 'sopt':
                return await self._initialize_sopt_gateway(account)
            else:
                self.logger.error(
                    "Unsupported gateway type",
                    account_id=account_id,
                    gateway_type=gateway_type
                )
                return False
                
        except Exception as e:
            self.logger.error(
                "Account gateway initialization failed",
                account_id=account_id,
                error=str(e)
            )
            return False
    
    def _on_gateway_event(self, event: Event, account_id: str):
        """Handle gateway connection events for a specific account."""
        gateway_data = event.data
        
        if hasattr(gateway_data, 'gateway_name'):
            if hasattr(gateway_data, 'status'):
                self._handle_connection_status_change(gateway_data.status, account_id)
    
    def _handle_connection_status_change(self, status: str, account_id: str):
        """Handle connection status changes with logging and monitoring."""
        previous_status = self.gateway_connections.get(account_id, False)
        
        if status == "连接成功" or status == "connected":
            self.gateway_connections[account_id] = True
            duration = self._get_connection_duration(account_id)
            
            self.logger.info(
                "Gateway connected successfully",
                account_id=account_id,
                connection_duration=f"{duration:.2f}s",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Subscribe to contracts for this account
            self._subscribe_contracts(account_id)
            
        elif status == "连接断开" or status == "disconnected":
            self.gateway_connections[account_id] = False
            
            self.logger.warning(
                "Gateway disconnected",
                account_id=account_id,
                previous_connection_duration=f"{self._get_connection_duration(account_id):.2f}s",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Attempt basic retry if configured
            self._attempt_reconnection(account_id)
            
        # Log state change
        if previous_status != self.gateway_connections.get(account_id, False):
            self.logger.info(
                "Connection state changed",
                account_id=account_id,
                previous_state="connected" if previous_status else "disconnected",
                new_state="connected" if self.gateway_connections.get(account_id, False) else "disconnected"
            )
    
    def _subscribe_contracts(self, account_id: str):
        """Subscribe to contracts for tick data for a specific account."""
        main_engine = self.main_engines.get(account_id)
        if not main_engine or not self.gateway_connections.get(account_id, False):
            return
            
        try:
            # Default test contracts - in production this could be configured per account
            test_contracts = [
                "rb2501.SHFE",  # Steel rebar futures May 2025
                "au2502.SHFE",  # Gold futures February 2025
            ]
            
            for contract in test_contracts:
                # Note: Actual subscription method depends on vnpy version
                # This is a simplified version for the MVP
                self.logger.info(
                    "Subscribed to contract",
                    symbol=contract,
                    account_id=account_id
                )
        except Exception as e:
            self.logger.error(
                "Contract subscription failed",
                error=str(e),
                account_id=account_id
            )
    
    def _on_tick_event(self, event: Event, account_id: str):
        """Handle incoming tick data with validation and performance monitoring."""
        tick_data = event.data
        
        try:
            current_time = datetime.now(timezone.utc)
            market_time = getattr(tick_data, 'datetime', None)
            symbol = getattr(tick_data, 'symbol', 'unknown')
            
            # Count tick
            self.tick_count += 1
            self.last_tick_time = current_time
            
            # Update health monitor with canary tick data
            self._update_health_monitor_tick(account_id, symbol, current_time)
            
            # Calculate processing latency
            latency_ms = None
            if market_time:
                latency_ms = (current_time - market_time).total_seconds() * 1000
            
            # Update tick rate monitoring
            self._update_tick_rate_monitoring(current_time)
            
            # Log tick data with essential fields
            self.logger.info(
                "Received tick",
                account_id=account_id,
                symbol=symbol,
                price=getattr(tick_data, 'last_price', None),
                volume=getattr(tick_data, 'volume', None),
                time=current_time.isoformat(),
                market_time=market_time.isoformat() if market_time else None,
                latency_ms=latency_ms,
                tick_count=self.tick_count
            )
            
            # Data freshness validation
            if market_time:
                freshness_seconds = (current_time - market_time).total_seconds()
                if freshness_seconds > 60:  # More than 1 minute old
                    self.logger.warning(
                        "Tick data freshness warning",
                        account_id=account_id,
                        symbol=symbol,
                        freshness_seconds=freshness_seconds
                    )
            
            # Publish tick via ZMQ
            try:
                zmq_success = zmq_publisher.publish_tick(tick_data)
                if not zmq_success:
                    self.logger.warning(
                        "ZMQ tick publication failed",
                        account_id=account_id,
                        symbol=symbol,
                        tick_count=self.tick_count
                    )
            except Exception as zmq_error:
                self.logger.error(
                    "ZMQ tick publication error",
                    account_id=account_id,
                    error=str(zmq_error),
                    symbol=symbol
                )
            
            # Periodic performance logging
            self._log_performance_metrics()
            
        except Exception as e:
            self.logger.error(
                "Tick processing error",
                account_id=account_id,
                error=str(e),
                tick_count=self.tick_count
            )
    
    def _update_tick_rate_monitoring(self, current_time: datetime):
        """Update tick rate monitoring with sliding window."""
        # Keep last 60 seconds of ticks for rate calculation
        self.tick_rate_window.append(current_time)
        
        # Remove ticks older than 60 seconds
        from datetime import timedelta
        cutoff_time = current_time - timedelta(seconds=60)
        self.tick_rate_window = [t for t in self.tick_rate_window if t > cutoff_time]
    
    def _log_performance_metrics(self):
        """Log performance metrics at regular intervals."""
        current_time = time.time()
        
        if current_time - self.last_performance_log >= self.performance_log_interval:
            try:
                # Calculate tick rate
                tick_rate = len(self.tick_rate_window)  # Ticks per minute
                
                # Memory usage
                current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                memory_growth = current_memory - self.startup_memory
                
                # Connection duration
                connection_duration = self._get_connection_duration()
                
                self.logger.info(
                    "Performance metrics",
                    tick_rate_per_minute=tick_rate,
                    total_ticks=self.tick_count,
                    memory_usage_mb=current_memory,
                    memory_growth_mb=memory_growth,
                    connection_duration_seconds=connection_duration,
                    gateway_connected=self.is_connected
                )
                
                self.last_performance_log = current_time
                
            except Exception as e:
                self.logger.error("Performance metrics logging failed", error=str(e))
    
    def _get_connection_duration(self, account_id: str) -> float:
        """Get connection duration in seconds for a specific account."""
        start_time = self.connection_start_times.get(account_id)
        if not start_time:
            return 0.0
        return (datetime.now(timezone.utc) - start_time).total_seconds()
    
    def _attempt_reconnection(self, account_id: str):
        """Attempt basic reconnection with single retry and 10s delay."""
        attempts = self.connection_attempts.get(account_id, 0)
        if attempts >= 2:  # Only one retry attempt
            self.logger.info(
                "Maximum reconnection attempts reached",
                account_id=account_id,
                attempts=attempts
            )
            return
        
        self.logger.info(
            "Attempting reconnection in 10 seconds",
            account_id=account_id,
            attempt=attempts + 1
        )
        
        # Schedule reconnection after 10 seconds
        def delayed_reconnect():
            time.sleep(10)
            self.connection_attempts[account_id] = attempts + 1
            self.connection_start_times[account_id] = datetime.now(timezone.utc)
            # Find account and reconnect
            account = next((acc for acc in self.active_accounts if acc['id'] == account_id), None)
            if account:
                if account['gateway_type'] == 'ctp':
                    self._connect_ctp_gateway(account)
                elif account['gateway_type'] == 'sopt':
                    self._connect_sopt_gateway(account)
        
        threading.Thread(target=delayed_reconnect, daemon=True).start()
    
    def _on_log_event(self, event: Event, account_id: str):
        """Handle vnpy log events for a specific account."""
        log_data = event.data
        
        # Filter and forward relevant logs
        if hasattr(log_data, 'msg') and hasattr(log_data, 'level'):
            self.logger.info(
                "VNPy log",
                account_id=account_id,
                message=log_data.msg,
                level=log_data.level,
                gateway=getattr(log_data, 'gateway_name', 'unknown')
            )
    
    async def shutdown(self):
        """Gracefully shutdown the gateway manager and ZMQ publisher."""
        try:
            self.logger.info("Gateway Manager shutting down")
            
            # Shutdown ZMQ publisher first
            await zmq_publisher.shutdown()
            
            # Shutdown all main engines
            for account_id, main_engine in self.main_engines.items():
                try:
                    if main_engine:
                        main_engine.close()
                except Exception as e:
                    self.logger.error("Error shutting down main engine", account_id=account_id, error=str(e))
            
            # Shutdown all event engines
            for account_id, event_engine in self.event_engines.items():
                try:
                    if event_engine:
                        event_engine.stop()
                except Exception as e:
                    self.logger.error("Error shutting down event engine", account_id=account_id, error=str(e))
            
            # Final performance summary
            self.logger.info(
                "Gateway Manager shutdown complete",
                total_accounts=len(self.active_accounts),
                total_ticks_processed=self.tick_count,
                final_memory_usage_mb=self.process.memory_info().rss / 1024 / 1024
            )
            
        except Exception as e:
            self.logger.error("Gateway shutdown error", error=str(e))


    async def _initialize_ctp_gateway(self, account: Dict[str, Any]) -> bool:
        """Initialize CTP gateway for an account."""
        account_id = account['id']
        settings = account['settings']
        
        try:
            # Create event engine for this account
            event_engine = EventEngine()
            self.event_engines[account_id] = event_engine
            
            # Create main engine for this account
            main_engine = MainEngine(event_engine)
            self.main_engines[account_id] = main_engine
            
            # Add CTP gateway
            main_engine.add_gateway(CtpGateway)
            
            # Register event handlers for this account
            self._register_event_handlers(event_engine, account_id)
            
            # Initialize connection tracking
            self.connection_attempts[account_id] = 0
            self.gateway_connections[account_id] = False
            
            # Start connection
            self._connect_ctp_gateway(account)
            
            return True
            
        except Exception as e:
            self.logger.error(
                "CTP gateway initialization failed",
                account_id=account_id,
                error=str(e)
            )
            return False
    
    def _connect_ctp_gateway(self, account: Dict[str, Any]):
        """Connect to CTP gateway with account settings."""
        account_id = account['id']
        settings = account['settings']
        main_engine = self.main_engines.get(account_id)
        
        if not main_engine:
            return
            
        try:
            self.connection_attempts[account_id] = self.connection_attempts.get(account_id, 0) + 1
            self.connection_start_times[account_id] = datetime.now(timezone.utc)
            
            # Use account-specific gateway name
            gateway_name = f"CTP_{account_id}"
            
            main_engine.connect(settings, gateway_name)
            self.logger.info(
                "CTP Gateway connection initiated",
                account_id=account_id,
                gateway_name=gateway_name,
                settings_keys=list(settings.keys())
            )
        except Exception as e:
            self.logger.error(
                "CTP Gateway connection failed",
                account_id=account_id,
                error=str(e)
            )
    
    async def _initialize_sopt_gateway(self, account: Dict[str, Any]) -> bool:
        """Initialize SOPT gateway for an account."""
        account_id = account['id']
        settings = account['settings']
        
        if not SOPT_AVAILABLE:
            self.logger.warning(
                "SOPT gateway not available - missing dependencies",
                account_id=account_id
            )
            return False
        
        try:
            # Create event engine for this account
            event_engine = EventEngine()
            self.event_engines[account_id] = event_engine
            
            # Create main engine for this account
            main_engine = MainEngine(event_engine)
            self.main_engines[account_id] = main_engine
            
            # Add SOPT gateway
            main_engine.add_gateway(SoptGateway)
            
            # Register event handlers for this account
            self._register_event_handlers(event_engine, account_id)
            
            # Initialize connection tracking
            self.connection_attempts[account_id] = 0
            self.gateway_connections[account_id] = False
            
            # Start connection
            self._connect_sopt_gateway(account)
            
            return True
            
        except Exception as e:
            self.logger.error(
                "SOPT gateway initialization failed",
                account_id=account_id,
                error=str(e)
            )
            return False
    
    def _connect_sopt_gateway(self, account: Dict[str, Any]):
        """Connect to SOPT gateway with account settings."""
        account_id = account['id']
        settings = account['settings']
        main_engine = self.main_engines.get(account_id)
        
        if not main_engine:
            return
            
        try:
            self.connection_attempts[account_id] = self.connection_attempts.get(account_id, 0) + 1
            self.connection_start_times[account_id] = datetime.now(timezone.utc)
            
            # Use account-specific gateway name
            gateway_name = f"SOPT_{account_id}"
            
            # Convert account settings to SOPT format
            sopt_settings = self._convert_to_sopt_settings(settings)
            
            main_engine.connect(sopt_settings, gateway_name)
            self.logger.info(
                "SOPT Gateway connection initiated",
                account_id=account_id,
                gateway_name=gateway_name,
                settings_keys=list(sopt_settings.keys())
            )
        except Exception as e:
            self.logger.error(
                "SOPT Gateway connection failed",
                account_id=account_id,
                error=str(e)
            )
    
    def _convert_to_sopt_settings(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """Convert database settings to SOPT gateway format."""
        # Map our database fields to SOPT expected fields
        sopt_mapping = {
            'username': '用户名',
            'password': '密码',
            'brokerID': '经纪商代码',
            'tdAddress': '交易服务器',
            'mdAddress': '行情服务器',
            'appID': '产品名称',
            'authCode': '授权编码'
        }
        
        sopt_settings = {}
        for db_key, sopt_key in sopt_mapping.items():
            if db_key in settings:
                sopt_settings[sopt_key] = str(settings[db_key])
        
        return sopt_settings
    
    async def _initialize_mock_gateway(self, account: Dict[str, Any]) -> bool:
        """Initialize mock gateway for development/testing."""
        account_id = account['id']
        
        try:
            self.logger.info(
                "Initializing mock gateway",
                account_id=account_id
            )
            
            # Create mock event engine
            event_engine = EventEngine()
            self.event_engines[account_id] = event_engine
            
            # Create mock main engine
            main_engine = MainEngine(event_engine)
            self.main_engines[account_id] = main_engine
            
            # Register event handlers
            self._register_event_handlers(event_engine, account_id)
            
            # Initialize connection tracking
            self.connection_attempts[account_id] = 1
            self.connection_start_times[account_id] = datetime.now(timezone.utc)
            self.gateway_connections[account_id] = False
            
            # Connect to mock gateway
            gateway_name = f"MOCK_{account_id}"
            main_engine.connect(account['settings'], gateway_name)
            
            self.logger.info(
                "Mock gateway initialized successfully",
                account_id=account_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Mock gateway initialization failed",
                account_id=account_id,
                error=str(e)
            )
            return False
    
    def get_account_status(self) -> Dict[str, Any]:
        """Get status of all active accounts."""
        status = {
            'total_accounts': len(self.active_accounts),
            'connected_accounts': sum(1 for connected in self.gateway_connections.values() if connected),
            'accounts': []
        }
        
        for account in self.active_accounts:
            account_id = account['id']
            account_status = {
                'id': account_id,
                'gateway_type': account['gateway_type'],
                'priority': account['priority'],
                'connected': self.gateway_connections.get(account_id, False),
                'connection_attempts': self.connection_attempts.get(account_id, 0),
                'connection_duration': self._get_connection_duration(account_id)
            }
            status['accounts'].append(account_status)
        
        return status
    
    async def migrate_contracts(self, from_gateway_id: str, to_gateway_id: str, contracts: List[str]) -> bool:
        """
        Migrate contract subscriptions from one gateway to another.
        
        Args:
            from_gateway_id: Source gateway ID
            to_gateway_id: Target gateway ID
            contracts: List of contract symbols to migrate
            
        Returns:
            True if migration successful, False otherwise
        """
        try:
            self.logger.info(
                "Starting contract migration",
                from_gateway=from_gateway_id,
                to_gateway=to_gateway_id,
                contracts=contracts
            )
            
            # Validate gateways
            if not self._is_gateway_available(to_gateway_id):
                self.logger.error(
                    "Target gateway not available for migration",
                    gateway_id=to_gateway_id
                )
                return False
            
            # Unsubscribe from source gateway (if still connected)
            if self._is_gateway_available(from_gateway_id):
                await self._unsubscribe_contracts(from_gateway_id, contracts)
            
            # Subscribe to target gateway
            success = await self._subscribe_contracts_to_gateway(to_gateway_id, contracts)
            
            if success:
                self.logger.info(
                    "Contract migration completed successfully",
                    from_gateway=from_gateway_id,
                    to_gateway=to_gateway_id,
                    contracts=contracts
                )
            else:
                self.logger.error(
                    "Contract migration failed",
                    from_gateway=from_gateway_id,
                    to_gateway=to_gateway_id,
                    contracts=contracts
                )
            
            return success
            
        except Exception as e:
            self.logger.error(
                "Contract migration error",
                from_gateway=from_gateway_id,
                to_gateway=to_gateway_id,
                contracts=contracts,
                error=str(e)
            )
            return False
    
    def _is_gateway_available(self, gateway_id: str) -> bool:
        """Check if a gateway is available and connected."""
        return (
            gateway_id in self.main_engines and
            gateway_id in self.gateway_connections and
            self.gateway_connections[gateway_id]
        )
    
    async def _unsubscribe_contracts(self, gateway_id: str, contracts: List[str]):
        """Unsubscribe contracts from a gateway."""
        try:
            # TODO: Implement actual unsubscription logic
            # This depends on vnpy gateway API
            self.logger.info(
                "Unsubscribed contracts from gateway",
                
                contracts=contracts
            )
        except Exception as e:
            self.logger.error(
                "Failed to unsubscribe contracts",
                
                contracts=contracts,
                error=str(e)
            )
    
    async def _subscribe_contracts_to_gateway(self, gateway_id: str, contracts: List[str]) -> bool:
        """Subscribe contracts to a specific gateway."""
        try:
            main_engine = self.main_engines.get(gateway_id)
            if not main_engine or not self.gateway_connections.get(gateway_id, False):
                return False
            
            # TODO: Implement actual subscription logic
            # This depends on vnpy gateway API
            # For now, simulate subscription
            
            for contract in contracts:
                self.logger.info(
                    "Subscribed contract to gateway",
                    
                    contract=contract
                )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to subscribe contracts to gateway",
                
                contracts=contracts,
                error=str(e)
            )
            return False
    
    def get_gateway_contracts(self, gateway_id: str) -> List[str]:
        """
        Get list of contracts currently subscribed to a gateway.
        
        Args:
            gateway_id: Gateway ID
            
        Returns:
            List of contract symbols
        """
        # TODO: Implement actual contract tracking
        # For now, return default contracts if gateway is connected
        if self._is_gateway_available(gateway_id):
            return [
                "rb2501.SHFE",  # Steel rebar futures May 2025
                "au2502.SHFE",  # Gold futures February 2025
            ]
        return []
    
    def get_gateway_health_status(self, gateway_id: str) -> str:
        """
        Get health status of a gateway.
        
        Args:
            gateway_id: Gateway ID
            
        Returns:
            Health status string ("HEALTHY", "UNHEALTHY", "CONNECTING", "DISCONNECTED")
        """
        if gateway_id not in self.gateway_connections:
            return "DISCONNECTED"
        
        if self.gateway_connections[gateway_id]:
            return "HEALTHY"
        else:
            # Check if currently attempting to connect
            if self.connection_attempts.get(gateway_id, 0) > 0:
                return "CONNECTING"
            else:
                return "UNHEALTHY"
    
    def _update_health_monitor_tick(self, account_id: str, symbol: str, timestamp: datetime):
        """
        Update health monitor with tick data for canary contract monitoring.
        
        Args:
            account_id: Gateway account identifier
            symbol: Contract symbol
            timestamp: Tick timestamp
        """
        try:
            # Import here to avoid circular imports
            from app.services.health_monitor import health_monitor
            
            # Check if this is a canary contract for the account
            canary_contracts = []
            account = next((acc for acc in self.active_accounts if acc['id'] == account_id), None)
            if account:
                gateway_type = account['gateway_type']
                if gateway_type == 'ctp':
                    canary_contracts = os.getenv("CTP_CANARY_CONTRACTS", "rb2501,rb2505").split(",")
                elif gateway_type == 'sopt':
                    canary_contracts = os.getenv("SOPT_CANARY_CONTRACTS", "rb2501,rb2505").split(",")
            
            # Extract base symbol (remove exchange suffix if present)
            base_symbol = symbol.split('.')[0] if '.' in symbol else symbol
            
            # Update health monitor if this is a canary contract
            if base_symbol in canary_contracts:
                health_monitor.update_canary_tick(account_id, base_symbol, timestamp)
                
        except Exception as e:
            # Log error but don't let it interrupt tick processing
            self.logger.debug(
                "Failed to update health monitor tick",
                account_id=account_id,
                symbol=symbol,
                error=str(e)
            )
    
    async def terminate_gateway_process(self, gateway_id: str) -> bool:
        """
        Terminate gateway process gracefully.
        
        Args:
            gateway_id: Gateway identifier
            
        Returns:
            bool: True if termination successful, False otherwise
        """
        try:
            self.logger.info(
                "Terminating gateway process",
                
            )
            
            # Get main engine and event engine for the gateway
            main_engine = self.main_engines.get(gateway_id)
            event_engine = self.event_engines.get(gateway_id)
            
            if not main_engine and not event_engine:
                self.logger.warning(
                    "Gateway process not found for termination",
                    
                )
                return True  # Already terminated
            
            # Mark gateway as disconnected
            self.gateway_connections[gateway_id] = False
            
            # Close main engine first
            if main_engine:
                try:
                    main_engine.close()
                    self.logger.info(
                        "Main engine closed",
                        
                    )
                except Exception as e:
                    self.logger.error(
                        "Error closing main engine",
                        
                        error=str(e)
                    )
            
            # Stop event engine
            if event_engine:
                try:
                    event_engine.stop()
                    self.logger.info(
                        "Event engine stopped",
                        
                    )
                except Exception as e:
                    self.logger.error(
                        "Error stopping event engine",
                        
                        error=str(e)
                    )
            
            # Clean up references
            if gateway_id in self.main_engines:
                del self.main_engines[gateway_id]
            if gateway_id in self.event_engines:
                del self.event_engines[gateway_id]
            
            # Clean up connection tracking
            if gateway_id in self.connection_start_times:
                del self.connection_start_times[gateway_id]
            
            self.logger.info(
                "Gateway process terminated successfully",
                
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Gateway process termination failed",
                
                error=str(e)
            )
            return False
    
    async def restart_gateway_process(self, gateway_id: str, settings: Dict[str, Any]) -> bool:
        """
        Restart gateway process with clean initialization.
        
        Args:
            gateway_id: Gateway identifier
            settings: Gateway settings from database
            
        Returns:
            bool: True if restart successful, False otherwise
        """
        try:
            self.logger.info(
                "Restarting gateway process",
                
            )
            
            # Find the account configuration
            account = next((acc for acc in self.active_accounts if acc['id'] == gateway_id), None)
            if not account:
                self.logger.error(
                    "Account not found for gateway restart",
                    
                )
                return False
            
            # Update account settings with provided settings
            account['settings'] = settings
            
            # Initialize the gateway based on type
            success = await self._initialize_account_gateway(account)
            
            if success:
                self.logger.info(
                    "Gateway process restarted successfully",
                    
                )
            else:
                self.logger.error(
                    "Gateway process restart failed",
                    
                )
            
            return success
            
        except Exception as e:
            self.logger.error(
                "Gateway process restart error",
                
                error=str(e)
            )
            return False
    
    async def get_gateway_process_status(self, gateway_id: str) -> Dict[str, Any]:
        """
        Get gateway process status for monitoring.
        
        Args:
            gateway_id: Gateway identifier
            
        Returns:
            Dict[str, Any]: Process status information
        """
        try:
            status = {
                "gateway_id": gateway_id,
                "main_engine_active": gateway_id in self.main_engines,
                "event_engine_active": gateway_id in self.event_engines,
                "connected": self.gateway_connections.get(gateway_id, False),
                "connection_attempts": self.connection_attempts.get(gateway_id, 0),
                "connection_duration": self._get_connection_duration(gateway_id),
                "last_connection_time": None
            }
            
            # Add connection time if available
            if gateway_id in self.connection_start_times:
                status["last_connection_time"] = self.connection_start_times[gateway_id].isoformat()
            
            # Add account information if available
            account = next((acc for acc in self.active_accounts if acc['id'] == gateway_id), None)
            if account:
                status.update({
                    "gateway_type": account['gateway_type'],
                    "priority": account['priority'],
                    "description": account.get('description', '')
                })
            
            return status
            
        except Exception as e:
            self.logger.error(
                "Failed to get gateway process status",
                
                error=str(e)
            )
            return {
                "gateway_id": gateway_id,
                "error": str(e),
                "main_engine_active": False,
                "event_engine_active": False,
                "connected": False
            }
    
    # Interactive Control Methods for API
    
    async def start_gateway(self, gateway_id: str) -> bool:
        """
        Start a gateway through API control interface.
        
        Args:
            gateway_id: Unique identifier of the gateway/account to start
            
        Returns:
            bool: True if start successful, False otherwise
        """
        try:
            self.logger.info(f"API: Starting gateway {gateway_id}")
            
            # Check if gateway is already running
            if self.gateway_connections.get(gateway_id, False):
                self.logger.warning(f"Gateway already running: {gateway_id}")
                return False
            
            # Find the account configuration
            account = next((acc for acc in self.active_accounts if acc['id'] == gateway_id), None)
            if not account:
                self.logger.error(f"Account not found for gateway start: {gateway_id}")
                return False
            
            # Initialize and start the gateway
            success = await self._initialize_account_gateway(account)
            
            if success:
                self.logger.info(f"API: Gateway started successfully: {gateway_id}")
            else:
                self.logger.error(f"API: Gateway start failed: {gateway_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"API: Gateway start error {gateway_id}: {str(e)}")
            return False
    
    async def stop_gateway(self, gateway_id: str) -> bool:
        """
        Stop a gateway through API control interface.
        
        Args:
            gateway_id: Unique identifier of the gateway/account to stop
            
        Returns:
            bool: True if stop successful, False otherwise
        """
        try:
            self.logger.info(f"API: Stopping gateway {gateway_id}")
            
            # Check if gateway exists
            if gateway_id not in self.gateway_connections:
                self.logger.warning(f"Gateway not found for stop operation: {gateway_id}")
                return False
            
            # Check if already stopped
            if not self.gateway_connections.get(gateway_id, False):
                self.logger.warning("Gateway already stopped")
                return False
            
            # Terminate the gateway process
            success = await self.terminate_gateway_process(gateway_id)
            
            if success:
                self.logger.info("API: Gateway stopped successfully")
            else:
                self.logger.error("API: Gateway stop failed")
            
            return success
            
        except Exception as e:
            self.logger.error("API: Gateway stop error", error=str(e))
            return False
    
    async def restart_gateway(self, gateway_id: str) -> bool:
        """
        Restart a gateway through API control interface.
        
        Args:
            gateway_id: Unique identifier of the gateway/account to restart
            
        Returns:
            bool: True if restart successful, False otherwise
        """
        try:
            self.logger.info("API: Restarting gateway")
            
            # Find the account configuration
            account = next((acc for acc in self.active_accounts if acc['id'] == gateway_id), None)
            if not account:
                self.logger.error("Account not found for gateway restart")
                return False
            
            # Attempt to stop if currently running
            if self.gateway_connections.get(gateway_id, False):
                stop_success = await self.terminate_gateway_process(gateway_id)
                if not stop_success:
                    self.logger.warning("Gateway stop phase failed during restart")
                
                # Brief pause to ensure clean shutdown
                import asyncio
                await asyncio.sleep(1)
            
            # Start the gateway with current settings
            success = await self._initialize_account_gateway(account)
            
            if success:
                self.logger.info("API: Gateway restarted successfully")
            else:
                self.logger.error("API: Gateway restart failed")
            
            return success
            
        except Exception as e:
            self.logger.error("API: Gateway restart error", error=str(e))
            return False


# Global gateway manager instance
gateway_manager = GatewayManager()