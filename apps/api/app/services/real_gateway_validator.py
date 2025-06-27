#!/usr/bin/env python3
"""
真实的Gateway API登录验证器
使用vnpy的实际gateway进行真实的交易所API连接测试
"""

import sys
import json
import asyncio
import threading
import time
from typing import Dict, Any, Optional
import logging
from dataclasses import dataclass
from enum import Enum

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from vnpy.event import EventEngine, Event
    from vnpy.trader.engine import MainEngine
    from vnpy.trader.constant import Exchange
    from vnpy_ctp import CtpGateway
    CTP_AVAILABLE = True
    # Try to import log event
    try:
        from vnpy.trader.event import EVENT_LOG
        EVENT_GATEWAY_LOG = EVENT_LOG
    except ImportError:
        # Fallback for older vnpy versions
        EVENT_GATEWAY_LOG = "eLog"
except ImportError as e:
    logger.error(f"vnpy not available: {e}")
    CTP_AVAILABLE = False
    EVENT_GATEWAY_LOG = "eLog"

try:
    from vnpy_sopt.gateway.sopt_gateway import SoptGateway
    SOPT_AVAILABLE = True
except ImportError as e:
    logger.error(f"SOPT Gateway not available: {e}")
    SOPT_AVAILABLE = False


class ValidationStatus(Enum):
    """验证状态枚举"""
    PENDING = "pending"
    CONNECTING = "connecting"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class RealValidationResult:
    """真实验证结果"""
    success: bool
    status: ValidationStatus
    message: str
    details: Dict[str, Any]
    logs: list
    connection_time: float
    timestamp: float


class RealGatewayValidator:
    """真实的Gateway API验证器"""
    
    def __init__(self):
        self.event_engine: Optional[EventEngine] = None
        self.main_engine: Optional[MainEngine] = None
        self.gateway_name: Optional[str] = None
        self.validation_logs = []
        self.connection_events = []
        self.is_connected = False
        self.is_login_success = False
        self.login_error = None
        self.start_time = 0
        self.timeout_seconds = 30
        
    def log_handler(self, event: Event):
        """处理gateway日志事件"""
        try:
            log_data = event.data
            if hasattr(log_data, 'msg'):
                log_msg = f"[{getattr(log_data, 'time', '')}] {getattr(log_data, 'msg', '')}"
                msg = getattr(log_data, 'msg', '').lower()
            else:
                log_msg = f"Log: {str(log_data)}"
                msg = str(log_data).lower()
                
            self.validation_logs.append(log_msg)
            logger.info(f"Gateway Log: {log_msg}")
            
            # 检查登录相关的日志消息
            if 'login' in msg or '登录' in msg:
                if 'success' in msg or '成功' in msg:
                    self.is_login_success = True
                    logger.info("✅ 检测到登录成功消息")
                elif 'fail' in msg or 'error' in msg or '失败' in msg or '错误' in msg:
                    self.login_error = log_msg
                    logger.error(f"❌ 检测到登录失败消息: {log_msg}")
            
            # 检查连接相关的消息
            if 'connect' in msg or '连接' in msg:
                if 'success' in msg or '成功' in msg:
                    self.is_connected = True
                    logger.info("✅ 检测到连接成功消息")
        except Exception as e:
            logger.error(f"日志处理错误: {e}")
    
    def validate_account_real(self, account_settings: Dict[str, Any], gateway_type: str, 
                             timeout_seconds: int = 30) -> RealValidationResult:
        """
        使用真实的vnpy gateway进行账户验证
        
        Args:
            account_settings: 账户设置
            gateway_type: 网关类型 (ctp/sopt)
            timeout_seconds: 超时时间
            
        Returns:
            RealValidationResult: 真实验证结果
        """
        self.timeout_seconds = timeout_seconds
        self.start_time = time.time()
        
        result = RealValidationResult(
            success=False,
            status=ValidationStatus.PENDING,
            message="验证初始化",
            details={},
            logs=[],
            connection_time=0,
            timestamp=time.time()
        )
        
        try:
            logger.info(f"🚀 开始真实Gateway验证: {gateway_type.upper()}")
            result.status = ValidationStatus.CONNECTING
            
            # 检查Gateway可用性
            if gateway_type.lower() == "ctp" and not CTP_AVAILABLE:
                result.status = ValidationStatus.ERROR
                result.message = "CTP Gateway不可用"
                result.details = {"error_code": "GATEWAY_UNAVAILABLE", "gateway": "CTP"}
                return result
            elif gateway_type.lower() == "sopt" and not SOPT_AVAILABLE:
                result.status = ValidationStatus.ERROR
                result.message = "SOPT Gateway不可用"
                result.details = {"error_code": "GATEWAY_UNAVAILABLE", "gateway": "SOPT"}
                return result
            
            # 转换账户设置为vnpy格式
            vnpy_settings = self._transform_settings(account_settings, gateway_type)
            logger.info(f"📋 转换后的设置: {self._safe_log_settings(vnpy_settings)}")
            
            # 验证必填字段
            missing_fields = self._validate_required_fields(vnpy_settings, gateway_type)
            if missing_fields:
                result.status = ValidationStatus.ERROR
                result.message = f"缺少必填字段: {', '.join(missing_fields)}"
                result.details = {"error_code": "MISSING_FIELDS", "missing": missing_fields}
                return result
            
            # 创建事件引擎和主引擎
            self.event_engine = EventEngine()
            self.main_engine = MainEngine(self.event_engine)
            
            # 注册日志事件处理器
            self.event_engine.register(EVENT_GATEWAY_LOG, self.log_handler)
            
            # 添加对应的Gateway
            if gateway_type.lower() == "ctp":
                self.main_engine.add_gateway(CtpGateway)
                self.gateway_name = "CTP"
            elif gateway_type.lower() == "sopt":
                self.main_engine.add_gateway(SoptGateway)
                self.gateway_name = "SOPT"
            
            logger.info(f"🔌 开始连接到 {self.gateway_name} Gateway...")
            
            # 尝试连接
            self.main_engine.connect(vnpy_settings, self.gateway_name)
            
            # 等待连接结果
            success = self._wait_for_connection_result()
            
            if success:
                result.success = True
                result.status = ValidationStatus.SUCCESS
                result.message = f"{self.gateway_name} Gateway登录验证成功"
                result.details = {
                    "gateway_type": gateway_type.upper(),
                    "connection_established": self.is_connected,
                    "login_successful": self.is_login_success,
                    "validation_type": "REAL_API_LOGIN"
                }
                logger.info("✅ 真实API验证成功")
            else:
                result.success = False
                result.status = ValidationStatus.FAILED
                result.message = f"{self.gateway_name} Gateway登录验证失败"
                result.details = {
                    "gateway_type": gateway_type.upper(),
                    "connection_established": self.is_connected,
                    "login_successful": self.is_login_success,
                    "login_error": self.login_error,
                    "validation_type": "REAL_API_LOGIN",
                    "error_code": "LOGIN_FAILED"
                }
                logger.error("❌ 真实API验证失败")
            
            result.connection_time = time.time() - self.start_time
            result.logs = self.validation_logs.copy()
            
            # 添加短暂延迟确保所有日志都被处理
            time.sleep(0.5)
            
        except Exception as e:
            result.success = False
            result.status = ValidationStatus.ERROR
            result.message = f"验证过程异常: {str(e)}"
            result.details = {
                "error_code": "VALIDATION_EXCEPTION",
                "exception": str(e),
                "validation_type": "REAL_API_LOGIN"
            }
            result.logs = self.validation_logs.copy()
            logger.error(f"💥 验证异常: {e}")
            
        finally:
            # 清理资源
            self._cleanup()
            
        return result
    
    def _wait_for_connection_result(self) -> bool:
        """等待连接结果"""
        max_wait_time = self.timeout_seconds
        check_interval = 0.1
        elapsed_time = 0
        
        logger.info(f"⏳ 等待连接结果，最大等待时间: {max_wait_time}秒")
        
        while elapsed_time < max_wait_time:
            time.sleep(check_interval)
            elapsed_time += check_interval
            
            # 检查是否登录成功
            if self.is_login_success:
                logger.info(f"✅ 在 {elapsed_time:.2f}秒后检测到登录成功")
                return True
            
            # 检查是否有登录错误
            if self.login_error:
                logger.error(f"❌ 在 {elapsed_time:.2f}秒后检测到登录错误: {self.login_error}")
                return False
            
            # 每秒输出一次进度
            if int(elapsed_time) % 1 == 0 and elapsed_time >= 1:
                logger.info(f"⏳ 等待中... {elapsed_time:.0f}/{max_wait_time}秒")
        
        logger.warning(f"⏱️ 验证超时 ({max_wait_time}秒)")
        return False
    
    def _transform_settings(self, account_settings: Dict[str, Any], gateway_type: str) -> Dict[str, Any]:
        """转换账户设置为vnpy格式"""
        # 检查是否使用新的统一格式
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
    
    def _safe_log_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """安全地记录设置（隐藏敏感信息）"""
        safe_settings = settings.copy()
        if "密码" in safe_settings:
            safe_settings["密码"] = "***"
        if "授权编码" in safe_settings:
            safe_settings["授权编码"] = "***"
        return safe_settings
    
    def _validate_required_fields(self, settings: Dict[str, Any], gateway_type: str) -> list:
        """验证必填字段"""
        required_fields = []
        if gateway_type.lower() == "ctp":
            required_fields = ["用户名", "密码"]
        elif gateway_type.lower() == "sopt":
            required_fields = ["用户名", "密码"]
        
        return [field for field in required_fields if not settings.get(field)]
    
    def _cleanup(self):
        """清理资源"""
        try:
            logger.info("🧹 开始清理资源...")
            
            # 强制等待一下，让所有回调完成
            time.sleep(0.2)
            
            if self.main_engine:
                # 关闭所有gateway连接
                if self.gateway_name:
                    logger.info(f"🔌 关闭 {self.gateway_name} Gateway连接")
                    try:
                        # 尝试多种方式关闭gateway
                        gateway = self.main_engine.get_gateway(self.gateway_name)
                        if gateway:
                            gateway.close()
                    except Exception as e:
                        logger.warning(f"Gateway关闭警告: {e}")
                
                # 停止主引擎
                logger.info("🛑 停止主引擎")
                try:
                    self.main_engine.close()
                except Exception as e:
                    logger.warning(f"主引擎关闭警告: {e}")
                
            if self.event_engine:
                # 停止事件引擎
                logger.info("🛑 停止事件引擎")
                try:
                    self.event_engine.stop()
                except Exception as e:
                    logger.warning(f"事件引擎停止警告: {e}")
                
            # 再等待一下确保所有资源都被释放
            time.sleep(0.1)
                
            # 重置状态
            self.event_engine = None
            self.main_engine = None
            self.gateway_name = None
            self.validation_logs.clear()
            self.connection_events.clear()
            self.is_connected = False
            self.is_login_success = False
            self.login_error = None
            
            logger.info("🧹 资源清理完成")
            
        except Exception as e:
            logger.error(f"⚠️ 清理资源时出错: {e}")
        
        # 强制垃圾回收
        try:
            import gc
            gc.collect()
        except:
            pass


def validate_account_real_sync(account_settings: Dict[str, Any], gateway_type: str, 
                              timeout_seconds: int = 30) -> Dict[str, Any]:
    """
    同步的真实账户验证函数（用于子进程）
    
    Returns:
        Dict with validation result
    """
    validator = RealGatewayValidator()
    
    try:
        result = validator.validate_account_real(account_settings, gateway_type, timeout_seconds)
        
        return {
            "success": result.success,
            "message": result.message,
            "details": result.details,
            "logs": result.logs,
            "connection_time": result.connection_time,
            "timestamp": result.timestamp,
            "status": result.status.value
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"真实验证过程失败: {str(e)}",
            "details": {"error_code": "REAL_VALIDATION_ERROR", "exception": str(e)},
            "logs": [],
            "connection_time": 0,
            "timestamp": time.time(),
            "status": ValidationStatus.ERROR.value
        }


if __name__ == "__main__":
    """子进程入口点"""
    try:
        # Read input from stdin
        input_data = sys.stdin.read().strip()
        if not input_data:
            raise ValueError("No input data received")
        data = json.loads(input_data)
        
        account_settings = data["account_settings"]
        gateway_type = data["gateway_type"]
        timeout_seconds = data.get("timeout_seconds", 30)
        use_real_validation = data.get("use_real_validation", False)
        
        if use_real_validation:
            # 使用真实API验证
            result = validate_account_real_sync(account_settings, gateway_type, timeout_seconds)
        else:
            # 使用原来的网络连通性验证
            from validation_worker import validate_account_sync
            is_trading_time = data.get("is_trading_time", True)
            allow_non_trading_validation = data.get("allow_non_trading_validation", False)
            result = validate_account_sync(account_settings, gateway_type, timeout_seconds, 
                                         is_trading_time, allow_non_trading_validation)
        
        # Output result as JSON
        print(json.dumps(result))
        sys.exit(0)
        
    except Exception as e:
        error_result = {
            "success": False,
            "message": f"Worker process error: {str(e)}",
            "details": {"error_code": "WORKER_ERROR", "exception": str(e)},
            "timestamp": time.time(),
            "logs": [],
            "connection_time": 0,
            "status": ValidationStatus.ERROR.value
        }
        print(json.dumps(error_result))
        sys.exit(1)