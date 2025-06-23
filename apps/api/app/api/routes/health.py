"""
Health check endpoint for Market Data Hub API.
"""

import os
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    environment: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint that returns service status and metadata.
    
    Returns:
        HealthResponse: Service health status with metadata
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat() + "Z",
        version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "development")
    )