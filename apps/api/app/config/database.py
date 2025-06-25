"""
Database configuration module.

This module handles database connection configuration, session management,
and connection pooling for the Market Data Hub API.
"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ..models import Base


class DatabaseConfig:
    """Database configuration settings."""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./mdhub.db")
        self.async_database_url = self._convert_to_async_url(self.database_url)
        self.pool_size = int(os.getenv("DATABASE_POOL_SIZE", "5"))
        self.pool_recycle = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))
        self.enable_database = os.getenv("ENABLE_DATABASE", "true").lower() == "true"
        self.echo = os.getenv("DATABASE_ECHO", "false").lower() == "true"
        
        # Retry configuration
        self.retry_attempts = int(os.getenv("DATABASE_RETRY_ATTEMPTS", "3"))
        self.retry_delay = float(os.getenv("DATABASE_RETRY_DELAY", "1"))
        self.retry_backoff_factor = float(os.getenv("DATABASE_RETRY_BACKOFF_FACTOR", "2"))
    
    def _convert_to_async_url(self, url: str) -> str:
        """Convert sync database URL to async URL."""
        if url.startswith("sqlite"):
            return url.replace("sqlite://", "sqlite+aiosqlite://")
        elif url.startswith("mysql"):
            return url.replace("mysql://", "mysql+aiomysql://")
        elif url.startswith("postgresql"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return url


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self):
        self.config = DatabaseConfig()
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None
        self._initialized = False
        self._connection_healthy = False
    
    async def initialize(self) -> bool:
        """
        Initialize database connections and create tables with retry logic.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if not self.config.enable_database:
            print("Database disabled via ENABLE_DATABASE=false")
            return False
        
        # Implement retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.config.retry_attempts):
            try:
                if attempt > 0:
                    delay = self.config.retry_delay * (self.config.retry_backoff_factor ** (attempt - 1))
                    print(f"Database connection attempt {attempt + 1} after {delay:.1f}s delay...")
                    await asyncio.sleep(delay)
                else:
                    print("Initializing database connection...")
                
                # SQLite-specific configuration
                if self.config.database_url.startswith("sqlite"):
                    # Create async engine for SQLite
                    self._async_engine = create_async_engine(
                        self.config.async_database_url,
                        echo=self.config.echo,
                        poolclass=StaticPool,
                        connect_args={"check_same_thread": False}
                    )
                    
                    # Create sync engine for Alembic migrations (SQLite)
                    self._engine = create_engine(
                        self.config.database_url,
                        echo=self.config.echo,
                        poolclass=StaticPool,
                        connect_args={"check_same_thread": False}
                    )
                else:
                    # MySQL/PostgreSQL configuration
                    self._async_engine = create_async_engine(
                        self.config.async_database_url,
                        pool_size=self.config.pool_size,
                        pool_recycle=self.config.pool_recycle,
                        echo=self.config.echo,
                    )
                    
                    # Create sync engine for Alembic migrations
                    self._engine = create_engine(
                        self.config.database_url,
                        pool_size=self.config.pool_size,
                        pool_recycle=self.config.pool_recycle,
                        echo=self.config.echo,
                    )
                
                # Create session factories
                self._async_session_factory = async_sessionmaker(
                    bind=self._async_engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )
                
                self._session_factory = sessionmaker(bind=self._engine)
                
                # Test connection with timeout
                await asyncio.wait_for(self._test_connection(), timeout=10.0)
                
                # Create tables if they don't exist (for development)
                if self.config.database_url.startswith("sqlite"):
                    async with self._async_engine.begin() as conn:
                        await conn.run_sync(Base.metadata.create_all)
                
                self._initialized = True
                self._connection_healthy = True
                print("Database connection established successfully")
                return True
                
            except Exception as e:
                last_exception = e
                self._connection_healthy = False
                
                if attempt == self.config.retry_attempts - 1:
                    # Last attempt failed
                    print(f"Database initialization failed after {self.config.retry_attempts} attempts: {e}")
                    print("Enabling fallback mode - application will continue without database")
                    return False
                else:
                    print(f"Database connection attempt {attempt + 1} failed: {e}")
        
        return False
    
    async def _test_connection(self):
        """Test database connection."""
        from sqlalchemy import text
        async with self._async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    
    async def shutdown(self):
        """Shutdown database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._engine:
            self._engine.dispose()
        self._initialized = False
        self._connection_healthy = False
        print("Database connections closed")
    
    @property
    def is_healthy(self) -> bool:
        """Check if database connection is healthy."""
        return self._connection_healthy and self._initialized
    
    @property
    def is_enabled(self) -> bool:
        """Check if database is enabled."""
        return self.config.enable_database
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session."""
        if not self._initialized or not self._async_session_factory:
            raise RuntimeError("Database not initialized")
        
        async with self._async_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_sync_session(self):
        """Get synchronous database session for Alembic migrations."""
        if not self._session_factory:
            raise RuntimeError("Database not initialized")
        return self._session_factory()


# Global database manager instance
db_manager = DatabaseManager()


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session."""
    async with db_manager.get_async_session() as session:
        yield session