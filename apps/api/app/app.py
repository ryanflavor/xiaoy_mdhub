"""
FastAPI application factory and configuration.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import structlog

from app.api.routes import health

# Load environment variables
load_dotenv()

def configure_logging() -> None:
    """Configure structured logging using structlog."""
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

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()
    
    environment = os.getenv("ENVIRONMENT", "development")
    
    app = FastAPI(
        title="Market Data Hub API",
        description="High-Availability Market Data Distribution Service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        debug=environment == "development"
    )
    
    # Configure CORS for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
        start_time = datetime.utcnow()
        
        response = await call_next(request)
        
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(
            "Request processed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=process_time
        )
        
        return response
    
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
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
    
    # Include routers
    app.include_router(health.router, tags=["health"])
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        logger = structlog.get_logger()
        logger.info(
            "Market Data Hub API starting up",
            version="1.0.0",
            environment=environment
        )
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        logger = structlog.get_logger()
        logger.info("Market Data Hub API shutting down")
    
    return app