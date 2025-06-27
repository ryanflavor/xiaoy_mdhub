"""
Account Validation Service for Testing Gateway Connections.
Provides functionality to validate account credentials by attempting actual login during trading hours.
"""
import asyncio
import threading
import time
import subprocess
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import structlog

# Import timezone utilities
from app.utils.timezone import now_china, to_china_tz, CHINA_TZ

# Import trading time manager
from app.services.trading_time_manager import TradingTimeManager

# Check gateway availability without importing
try:
    import vnpy_ctp
    CTP_AVAILABLE = True
except ImportError:
    CTP_AVAILABLE = False

try:
    import vnpy_sopt
    SOPT_AVAILABLE = True
except ImportError:
    SOPT_AVAILABLE = False

# Configure logging
logger = structlog.get_logger(__name__)


class ValidationResult:
    """Result of account validation"""
    def __init__(self, success: bool, message: str, details: Optional[Dict] = None):
        self.success = success
        self.message = message
        self.details = details or {}
        self.timestamp = now_china()


class AccountValidationService:
    """Service for validating account credentials by attempting actual login"""
    
    def __init__(self):
        self.trading_time_manager = TradingTimeManager()
        self._validation_engines: Dict[str, MainEngine] = {}
        self._validation_locks: Dict[str, threading.Lock] = {}
        self._last_cleanup = time.time()
        self._global_validation_lock = threading.Lock()  # Global lock to prevent concurrent validations
        
    async def validate_account(self, account_id: str, account_settings: Dict[str, Any], 
                              gateway_type: str, timeout_seconds: int = 30, 
                              allow_non_trading_validation: bool = False,
                              use_real_api_validation: bool = False) -> ValidationResult:
        """
        Validate account by attempting login during trading hours or basic connectivity testing.
        
        Args:
            account_id: Unique account identifier
            account_settings: Account configuration settings
            gateway_type: Gateway type (ctp or sopt)
            timeout_seconds: Maximum time to wait for validation
            allow_non_trading_validation: Allow basic connectivity testing outside trading hours
            use_real_api_validation: Use real vnpy gateway API login validation
            
        Returns:
            ValidationResult with success status and details
        """
        try:
            # Aggressive cleanup to prevent threading conflicts
            current_time = time.time()
            if current_time - self._last_cleanup > 60:  # 1 minute cleanup
                self.cleanup_validation_engines()
                self._last_cleanup = current_time
            
            # Always cleanup before starting new validation
            self.cleanup_validation_engines()
            
            # Add small delay to ensure cleanup is complete
            await asyncio.sleep(0.1)
            
            logger.info("Starting account validation", 
                       account_id=account_id, gateway_type=gateway_type, 
                       use_real_api=use_real_api_validation)
            
            # Check if we're in trading hours or if non-trading validation is allowed
            is_trading_time = self._is_trading_time()
            if not is_trading_time and not allow_non_trading_validation:
                trading_status = self.trading_time_manager.get_current_trading_status()
                return ValidationResult(
                    success=False,
                    message="Account validation is only available during trading hours. Outside trading hours, only basic connectivity testing is available.",
                    details={
                        "error_code": "NON_TRADING_HOURS",
                        "current_time": now_china().isoformat(),
                        "trading_status": trading_status,
                        "user_friendly_message": "Connection validation requires an active trading session",
                        "next_session": {
                            "name": trading_status.get("next_session_name"),
                            "start_time": trading_status.get("next_session_start")
                        } if trading_status.get("next_session_start") else None,
                        "recommendations": [
                            "Wait for the next trading session to start",
                            "Use 'allow_non_trading_validation' for basic connectivity testing",
                            "Verify server addresses are correct for when trading starts"
                        ]
                    }
                )
            
            # Check gateway availability
            if not self._is_gateway_available(gateway_type):
                return ValidationResult(
                    success=False,
                    message=f"Gateway {gateway_type.upper()} is not available in this environment",
                    details={
                        "error_code": "GATEWAY_UNAVAILABLE",
                        "gateway_type": gateway_type.upper(),
                        "user_friendly_message": f"The {gateway_type.upper()} trading gateway is not installed or configured",
                        "recommendations": [
                            f"Install the vnpy_{gateway_type} package",
                            "Check system dependencies",
                            "Verify gateway configuration",
                            "Contact system administrator for assistance"
                        ],
                        "available_gateways": [
                            {"type": "CTP", "available": CTP_AVAILABLE},
                            {"type": "SOPT", "available": SOPT_AVAILABLE}
                        ]
                    }
                )
            
            # Use global lock to prevent ANY concurrent validations
            if not self._global_validation_lock.acquire(blocking=False):
                return ValidationResult(
                    success=False,
                    message="Another account validation is in progress. Please wait and try again.",
                    details={
                        "error_code": "VALIDATION_IN_PROGRESS",
                        "user_friendly_message": "Only one account validation can run at a time",
                        "recommendations": [
                            "Wait a few seconds and try again",
                            "Check if another validation is running",
                            "Ensure no other users are validating accounts simultaneously"
                        ],
                        "estimated_wait_time": "30-60 seconds"
                    }
                )
            
            try:
                # Transform account settings to vnpy format
                vnpy_settings = self._transform_to_vnpy_format(account_settings, gateway_type)
                
                # Perform actual validation
                return await self._perform_validation(account_id, vnpy_settings, 
                                                     gateway_type, timeout_seconds, 
                                                     is_trading_time, allow_non_trading_validation,
                                                     use_real_api_validation)
                
            finally:
                self._global_validation_lock.release()
                
        except Exception as e:
            logger.error("Account validation failed", 
                        account_id=account_id, error=str(e))
            return ValidationResult(
                success=False,
                message=f"Validation failed: {str(e)}",
                details={"error_code": "VALIDATION_ERROR", "exception": str(e)}
            )
    
    def _is_trading_time(self) -> bool:
        """Check if current time is within trading hours"""
        try:
            status = self.trading_time_manager.get_current_trading_status()
            return status.get("is_trading", False)
        except Exception:
            # If trading time manager fails, allow validation (fallback)
            logger.warning("Trading time check failed, allowing validation")
            return True
    
    def _is_gateway_available(self, gateway_type: str) -> bool:
        """Check if the specified gateway is available"""
        if gateway_type.lower() == "ctp":
            return CTP_AVAILABLE
        elif gateway_type.lower() == "sopt":
            return SOPT_AVAILABLE
        return False
    
    def _transform_to_vnpy_format(self, account_settings: Dict[str, Any], 
                                  gateway_type: str) -> Dict[str, Any]:
        """Transform account settings to vnpy gateway format"""
        
        # Check if using new unified format
        if "connect_setting" in account_settings:
            connect_setting = account_settings["connect_setting"]
            
            if gateway_type.lower() == "ctp":
                return {
                    "用户名": connect_setting.get("用户名", connect_setting.get("userID", "")),
                    "密码": connect_setting.get("密码", connect_setting.get("password", "")),
                    "经纪商代码": connect_setting.get("经纪商代码", connect_setting.get("brokerID", "")),
                    "交易服务器": connect_setting.get("交易服务器", connect_setting.get("tdAddress", "")),
                    "行情服务器": connect_setting.get("行情服务器", connect_setting.get("mdAddress", "")),
                    "产品名称": connect_setting.get("产品名称", connect_setting.get("appID", "")),
                    "授权编码": connect_setting.get("授权编码", connect_setting.get("authCode", ""))
                }
            elif gateway_type.lower() == "sopt":
                return {
                    "用户名": connect_setting.get("用户名", connect_setting.get("username", "")),
                    "密码": connect_setting.get("密码", connect_setting.get("password", "")),
                    "经纪商代码": connect_setting.get("经纪商代码", connect_setting.get("brokerID", "")),
                    "交易服务器": connect_setting.get("交易服务器", connect_setting.get("serverAddress", "")),
                    "行情服务器": connect_setting.get("行情服务器", connect_setting.get("serverAddress", "")),
                    "产品名称": connect_setting.get("产品名称", ""),
                    "授权编码": connect_setting.get("授权编码", "")
                }
        
        # Legacy flat format - return as is
        return account_settings
    
    async def _perform_validation(self, account_id: str, vnpy_settings: Dict[str, Any],
                                  gateway_type: str, timeout_seconds: int, 
                                  is_trading_time: bool, allow_non_trading_validation: bool,
                                  use_real_api_validation: bool) -> ValidationResult:
        """Perform actual validation using isolated subprocess"""
        
        validation_id = f"{account_id}_{int(time.time())}_{threading.get_ident()}"
        
        try:
            logger.info("Starting subprocess validation", 
                       validation_id=validation_id, gateway_type=gateway_type)
            
            # Prepare input data for subprocess
            input_data = {
                "account_settings": vnpy_settings,
                "gateway_type": gateway_type,
                "timeout_seconds": timeout_seconds,
                "is_trading_time": is_trading_time,
                "allow_non_trading_validation": allow_non_trading_validation,
                "use_real_validation": use_real_api_validation
            }
            
            # Get path to validation worker
            current_dir = os.path.dirname(os.path.abspath(__file__))
            worker_path = os.path.join(current_dir, "validation_worker.py")
            
            # Start subprocess
            process = await asyncio.create_subprocess_exec(
                'python', worker_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send input data and wait for result
            input_json = json.dumps(input_data).encode('utf-8')
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_json),
                    timeout=timeout_seconds + 10  # Add buffer time
                )
                
                # Parse result
                if process.returncode == 0:
                    result_data = json.loads(stdout.decode('utf-8'))
                    
                    return ValidationResult(
                        success=result_data["success"],
                        message=result_data["message"],
                        details=result_data.get("details", {})
                    )
                else:
                    error_msg = stderr.decode('utf-8') if stderr else "Unknown subprocess error"
                    logger.error("Validation subprocess failed", 
                               validation_id=validation_id, 
                               returncode=process.returncode,
                               error=error_msg)
                    
                    return ValidationResult(
                        success=False,
                        message=f"Validation subprocess failed: {error_msg}",
                        details={"error_code": "SUBPROCESS_ERROR", "returncode": process.returncode}
                    )
                    
            except asyncio.TimeoutError:
                logger.warning("Validation subprocess timed out", validation_id=validation_id)
                
                # Kill the subprocess
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass
                
                return ValidationResult(
                    success=False,
                    message=f"Validation process timed out after {timeout_seconds} seconds",
                    details={"error_code": "PROCESS_TIMEOUT"}
                )
                
        except Exception as e:
            logger.error("Validation process creation failed", 
                        validation_id=validation_id, error=str(e))
            return ValidationResult(
                success=False,
                message=f"Failed to start validation process: {str(e)}",
                details={"error_code": "PROCESS_START_ERROR", "exception": str(e)}
            )
    
    def cleanup_validation_engines(self):
        """Cleanup any remaining validation engines"""
        for validation_id, engine in list(self._validation_engines.items()):
            try:
                engine.close()
                del self._validation_engines[validation_id]
            except Exception as e:
                logger.warning("Error cleaning up validation engine", 
                              validation_id=validation_id, error=str(e))


# Singleton instance
account_validation_service = AccountValidationService()