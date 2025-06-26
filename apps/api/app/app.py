"""
FastAPI application factory and configuration.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import structlog

from app.api.routes import health
from app.api.routes import websocket
from app.routes import accounts
from app.routes import trading_time
from app.services.gateway_manager import gateway_manager
from app.services.health_monitor import health_monitor
from app.services.quote_aggregation_engine import quote_aggregation_engine
from app.services.gateway_recovery_service import gateway_recovery_service
from app.services.websocket_manager import WebSocketManager
from app.config.database import db_manager

# Load environment variables
load_dotenv()

def configure_logging() -> None:
    """Configure optimized logging to reduce startup noise."""
    import logging.config
    from logging_config import setup_optimized_logging, VNPyLogFilter
    from system_monitor_optimizer import optimize_startup_logging
    
    # 首先应用系统监控优化
    optimize_startup_logging()
    
    # 设置优化的日志配置
    config = setup_optimized_logging()
    
    # 创建logs目录
    os.makedirs("logs", exist_ok=True)
    
    # 应用日志配置
    logging.config.dictConfig(config)
    
    # 为VNPy相关的根日志记录器添加过滤器
    vnpy_filter = VNPyLogFilter()
    logging.getLogger().addFilter(vnpy_filter)
    
    # 配置structlog
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level),
    )
    
    # Set up WebSocket log broadcasting
    from app.services.websocket_log_handler import setup_websocket_logging
    setup_websocket_logging()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage the lifespan of the FastAPI application."""
    logger = structlog.get_logger()
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Startup
    logger.info(
        "Market Data Hub API starting up",
        version="1.0.0",
        environment=environment
    )
    
    # Initialize Database
    try:
        db_initialized = await db_manager.initialize()
        if db_initialized:
            logger.info("Database connection established successfully")
        else:
            logger.info("Database disabled or connection failed, using fallback mode")
    except Exception as e:
        logger.error("Database initialization error", error=str(e))
    
    # Initialize Gateway Manager with database accounts
    try:
        gateway_initialized = await gateway_manager.initialize()
        if gateway_initialized:
            logger.info("Gateway Manager initialized with database accounts")
        else:
            logger.info("Gateway Manager initialization completed with no active accounts")
    except Exception as e:
        logger.error("Gateway Manager initialization error", error=str(e))
    
    # Initialize Health Monitor
    try:
        health_monitor_initialized = await health_monitor.start()
        if health_monitor_initialized:
            logger.info("Health Monitor started successfully")
        else:
            logger.warning("Health Monitor failed to start")
    except Exception as e:
        logger.error("Health Monitor initialization error", error=str(e))
    
    # Initialize Quote Aggregation Engine
    try:
        await quote_aggregation_engine.start()
        logger.info("Quote Aggregation Engine started successfully")
    except Exception as e:
        logger.error("Quote Aggregation Engine initialization error", error=str(e))
    
    # Initialize Gateway Recovery Service
    try:
        recovery_initialized = await gateway_recovery_service.start()
        if recovery_initialized:
            logger.info("Gateway Recovery Service started successfully")
        else:
            logger.info("Gateway Recovery Service disabled or failed to start")
    except Exception as e:
        logger.error("Gateway Recovery Service initialization error", error=str(e))
    
    # Initialize WebSocket Manager (singleton, no explicit start needed)
    try:
        ws_manager = WebSocketManager.get_instance()
        logger.info("WebSocket Manager initialized successfully")
    except Exception as e:
        logger.error("WebSocket Manager initialization error", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Market Data Hub API shutting down")
    
    # Shutdown Gateway Recovery Service
    try:
        await gateway_recovery_service.stop()
    except Exception as e:
        logger.error("Gateway Recovery Service shutdown error", error=str(e))
    
    # Shutdown Quote Aggregation Engine
    try:
        await quote_aggregation_engine.stop()
    except Exception as e:
        logger.error("Quote Aggregation Engine shutdown error", error=str(e))
    
    # Shutdown Health Monitor
    try:
        await health_monitor.stop()
    except Exception as e:
        logger.error("Health Monitor shutdown error", error=str(e))
    
    # Shutdown Gateway Manager
    try:
        await gateway_manager.shutdown()
    except Exception as e:
        logger.error("Gateway Manager shutdown error", error=str(e))
    
    # Shutdown WebSocket Manager
    try:
        ws_manager = WebSocketManager.get_instance()
        await ws_manager.shutdown()
    except Exception as e:
        logger.error("WebSocket Manager shutdown error", error=str(e))
    
    # Shutdown Database
    try:
        await db_manager.shutdown()
    except Exception as e:
        logger.error("Database shutdown error", error=str(e))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()
    
    environment = os.getenv("ENVIRONMENT", "development")
    
    app = FastAPI(
        title="Market Data Hub Management API",
        description="""
        High-Availability Market Data Distribution Service
        
        This API provides comprehensive management capabilities for market data accounts,
        supporting multiple gateway types (CTP, SOPT) with automatic failover and
        health monitoring features.
        
        ## Key Features
        - **Account Management**: Full CRUD operations for market data accounts
        - **Multi-Gateway Support**: CTP and SOPT gateway configurations
        - **Priority Management**: Account priority and failover handling
        - **Real-time Status**: Live account status and health monitoring
        
        ## Gateway Types
        - **CTP**: China Trading Platform integration
        - **SOPT**: Shanghai Options Trading integration
        """,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        debug=environment == "development",
        contact={
            "name": "Market Data Hub API",
            "url": "https://github.com/your-org/mdhub",
        },
        license_info={
            "name": "MIT",
        },
    )
    
    # Configure CORS for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000", 
            "http://127.0.0.1:3000",
            "http://192.168.10.69:3000"  # Allow local IP access
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware for security
    if environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
        )
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger = structlog.get_logger()
        start_time = datetime.now()
        
        response = await call_next(request)
        
        process_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            "Request processed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=process_time
        )
        
        return response
    
    # Database-specific exception handler
    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        logger = structlog.get_logger()
        logger.error(
            "Database error",
            exception=str(exc),
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=503,
            content={
                "error": "Database error",
                "message": "Database service is temporarily unavailable",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger = structlog.get_logger()
        logger.error(
            "Unhandled exception",
            exception=str(exc),
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(accounts.router, tags=["accounts"])
    app.include_router(trading_time.router, tags=["trading-time"])
    app.include_router(websocket.router, tags=["websocket"])
    
    return app