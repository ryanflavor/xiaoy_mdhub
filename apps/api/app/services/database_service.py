"""
Database service for Market Data Account operations.

This module provides CRUD operations, validation, and data access methods
for MarketDataAccount entities.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel, ValidationError, field_validator, model_validator

from ..config.database import db_manager, get_database_session
from ..models.market_data_account import MarketDataAccount


class AccountSettingsValidator(BaseModel):
    """Pydantic model for validating account settings."""
    
    # CTP specific settings
    userID: Optional[str] = None
    password: Optional[str] = None
    brokerID: Optional[str] = None
    authCode: Optional[str] = None
    appID: Optional[str] = None
    mdAddress: Optional[str] = None
    tdAddress: Optional[str] = None
    
    # SOPT specific settings
    username: Optional[str] = None
    token: Optional[str] = None
    serverAddress: Optional[str] = None
    
    # Common settings
    timeout: Optional[int] = None


class MarketDataAccountValidator(BaseModel):
    """Pydantic model for validating MarketDataAccount data."""
    
    id: str
    gateway_type: str
    settings: Dict[str, Any]
    priority: int = 1
    is_enabled: bool = True
    description: Optional[str] = None
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Account ID cannot be empty')
        if len(v) > 100:
            raise ValueError('Account ID cannot exceed 100 characters')
        return v.strip()
    
    @field_validator('gateway_type')
    @classmethod
    def validate_gateway_type(cls, v):
        v_lower = v.lower()
        if v_lower not in ['ctp', 'sopt']:
            raise ValueError('Gateway type must be either "ctp" or "sopt" (case insensitive)')
        return v_lower
    
    @field_validator('settings')
    @classmethod
    def validate_settings_format(cls, v):
        if not isinstance(v, dict):
            raise ValueError('Settings must be a valid JSON object')
        return v
    
    @model_validator(mode='after')
    def validate_settings_content(self):
        settings = self.settings
        gateway_type = self.gateway_type
        
        # Validate settings based on gateway type
        if gateway_type == 'ctp':
            # Check for nested connect_setting structure first (new format)
            connect_setting = settings.get('connect_setting', {})
            
            if connect_setting:
                # Check for Chinese field names (new format)
                chinese_required = ['用户名', '密码', '经纪商代码']
                has_chinese = all(field in connect_setting and connect_setting[field] for field in chinese_required)
                
                # Check for English field names (legacy in nested format)
                english_required = ['userID', 'password', 'brokerID']
                has_english = all(field in connect_setting and connect_setting[field] for field in english_required)
                
                if not (has_chinese or has_english):
                    raise ValueError('CTP gateway requires user credentials (用户名, 密码, 经纪商代码) or (userID, password, brokerID) in connect_setting')
            # For direct field format (legacy flat structure)
            elif 'userID' in settings and 'password' in settings:
                required_fields = ['userID', 'password', 'brokerID', 'mdAddress']
                for field in required_fields:
                    if field not in settings or not settings[field]:
                        raise ValueError(f'CTP gateway requires {field} in settings')
            else:
                raise ValueError('CTP gateway requires connection settings in connect_setting or as direct fields')
                
        elif gateway_type == 'sopt':
            # Check for nested connect_setting structure first (prioritize new format)
            connect_setting = settings.get('connect_setting', {})
            
            if connect_setting:
                # Check for Chinese field names (SOPT only requires username, password is optional)
                chinese_required = ['用户名']
                has_chinese = all(field in connect_setting and connect_setting[field] for field in chinese_required)
                
                # Check for English field names in nested structure
                english_required = ['username']
                has_english = all(field in connect_setting and connect_setting[field] for field in english_required)
                
                if not (has_chinese or has_english):
                    raise ValueError('SOPT gateway requires user credentials (用户名) or (username) in connect_setting')
            # For direct field format (legacy)
            elif 'username' in settings:
                required_fields = ['username', 'serverAddress']
                for field in required_fields:
                    if field not in settings or not settings[field]:
                        raise ValueError(f'SOPT gateway requires {field} in settings')
            else:
                raise ValueError('SOPT gateway requires connection settings in connect_setting or as direct fields')
        
        # Skip AccountSettingsValidator for now since it expects English field names
        # and our database has Chinese field names
        
        return self
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Priority must be between 1 and 100')
        return v


class DatabaseService:
    """Service class for database operations on MarketDataAccount."""
    
    def __init__(self):
        self.db_manager = db_manager
    
    async def is_available(self) -> bool:
        """Check if database service is available."""
        return self.db_manager.is_healthy and self.db_manager.is_enabled
    
    async def create_account(self, account_data: Dict[str, Any]) -> Optional[MarketDataAccount]:
        """
        Create a new market data account.
        
        Args:
            account_data: Dictionary containing account information
            
        Returns:
            Created MarketDataAccount instance or None if database unavailable
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If database operation fails
        """
        if not await self.is_available():
            return None
        
        # Validate input data
        try:
            validated_data = MarketDataAccountValidator(**account_data)
        except ValidationError as e:
            raise ValueError(f"Account validation failed: {e}")
        
        try:
            async with self.db_manager.get_async_session() as session:
                # Check if account ID already exists
                existing = await session.execute(
                    select(MarketDataAccount).where(MarketDataAccount.id == validated_data.id)
                )
                if existing.scalar_one_or_none():
                    raise ValueError(f"Account with ID '{validated_data.id}' already exists")
                
                # Create new account
                account = MarketDataAccount(
                    id=validated_data.id,
                    gateway_type=validated_data.gateway_type,
                    settings=validated_data.settings,
                    priority=validated_data.priority,
                    is_enabled=validated_data.is_enabled,
                    description=validated_data.description,
                )
                
                session.add(account)
                await session.commit()
                await session.refresh(account)
                
                return account
                
        except IntegrityError as e:
            raise ValueError(f"Account creation failed: {e}")
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {e}")
    
    async def get_account(self, account_id: str) -> Optional[MarketDataAccount]:
        """
        Get a market data account by ID.
        
        Args:
            account_id: Unique account identifier
            
        Returns:
            MarketDataAccount instance or None if not found or database unavailable
        """
        if not await self.is_available():
            return None
        
        try:
            async with self.db_manager.get_async_session() as session:
                result = await session.execute(
                    select(MarketDataAccount).where(MarketDataAccount.id == account_id)
                )
                return result.scalar_one_or_none()
                
        except SQLAlchemyError as e:
            print(f"Database error getting account {account_id}: {e}")
            return None
    
    async def get_all_accounts(self, enabled_only: bool = False) -> List[MarketDataAccount]:
        """
        Get all market data accounts.
        
        Args:
            enabled_only: If True, only return enabled accounts
            
        Returns:
            List of MarketDataAccount instances (empty list if database unavailable)
        """
        if not await self.is_available():
            return []
        
        try:
            async with self.db_manager.get_async_session() as session:
                query = select(MarketDataAccount).order_by(MarketDataAccount.priority)
                
                if enabled_only:
                    query = query.where(MarketDataAccount.is_enabled == True)
                
                result = await session.execute(query)
                return list(result.scalars().all())
                
        except SQLAlchemyError as e:
            print(f"Database error getting accounts: {e}")
            return []
    
    async def update_account(self, account_id: str, update_data: Dict[str, Any]) -> Optional[MarketDataAccount]:
        """
        Update an existing market data account.
        
        Args:
            account_id: Unique account identifier
            update_data: Dictionary containing fields to update
            
        Returns:
            Updated MarketDataAccount instance or None if not found or database unavailable
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If database operation fails
        """
        if not await self.is_available():
            return None
        
        try:
            async with self.db_manager.get_async_session() as session:
                # Get existing account
                result = await session.execute(
                    select(MarketDataAccount).where(MarketDataAccount.id == account_id)
                )
                account = result.scalar_one_or_none()
                
                if not account:
                    return None
                
                # Validate update data
                current_data = account.to_dict()
                current_data.update(update_data)
                
                try:
                    MarketDataAccountValidator(**current_data)
                except ValidationError as e:
                    raise ValueError(f"Update validation failed: {e}")
                
                # Update account
                update_stmt = (
                    update(MarketDataAccount)
                    .where(MarketDataAccount.id == account_id)
                    .values(**update_data, updated_at=func.now())
                )
                
                await session.execute(update_stmt)
                await session.commit()
                
                # Refresh and return updated account
                await session.refresh(account)
                return account
                
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error updating account: {e}")
    
    async def delete_account(self, account_id: str) -> bool:
        """
        Delete a market data account.
        
        Args:
            account_id: Unique account identifier
            
        Returns:
            True if deleted, False if not found or database unavailable
            
        Raises:
            RuntimeError: If database operation fails
        """
        if not await self.is_available():
            return False
        
        try:
            async with self.db_manager.get_async_session() as session:
                delete_stmt = delete(MarketDataAccount).where(MarketDataAccount.id == account_id)
                result = await session.execute(delete_stmt)
                await session.commit()
                
                return result.rowcount > 0
                
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error deleting account: {e}")
    
    async def get_accounts_by_gateway_type(self, gateway_type: str, enabled_only: bool = True) -> List[MarketDataAccount]:
        """
        Get accounts filtered by gateway type.
        
        Args:
            gateway_type: Type of gateway ("ctp" or "sopt")
            enabled_only: If True, only return enabled accounts
            
        Returns:
            List of MarketDataAccount instances (empty list if database unavailable)
        """
        if not await self.is_available():
            return []
        
        try:
            async with self.db_manager.get_async_session() as session:
                query = (
                    select(MarketDataAccount)
                    .where(MarketDataAccount.gateway_type == gateway_type)
                    .order_by(MarketDataAccount.priority)
                )
                
                if enabled_only:
                    query = query.where(MarketDataAccount.is_enabled == True)
                
                result = await session.execute(query)
                return list(result.scalars().all())
                
        except SQLAlchemyError as e:
            print(f"Database error getting accounts by gateway type: {e}")
            return []
    
    async def validate_settings_json(self, settings: Union[str, Dict[str, Any]], gateway_type: str) -> Dict[str, Any]:
        """
        Validate and parse settings JSON.
        
        Args:
            settings: Settings as JSON string or dictionary
            gateway_type: Gateway type for validation
            
        Returns:
            Validated settings dictionary
            
        Raises:
            ValueError: If validation fails
        """
        # Parse JSON if string
        if isinstance(settings, str):
            try:
                settings_dict = json.loads(settings)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in settings: {e}")
        else:
            settings_dict = settings
        
        # Validate using the account validator
        temp_account = {
            "id": "temp_validation",
            "gateway_type": gateway_type,
            "settings": settings_dict,
            "priority": 1,
            "is_enabled": True
        }
        
        try:
            validated = MarketDataAccountValidator(**temp_account)
            return validated.settings
        except ValidationError as e:
            raise ValueError(f"Settings validation failed: {e}")


# Global database service instance
database_service = DatabaseService()