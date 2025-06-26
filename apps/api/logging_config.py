"""
优化的日志配置 - 减少VNPy和系统组件的噪音输出
"""

import logging
import os
from typing import Dict, Any


def setup_optimized_logging() -> Dict[str, Any]:
    """
    设置优化的日志配置，减少启动时的信息刷屏
    """
    
    # 环境变量控制调试级别
    debug_mode = os.getenv("GATEWAY_DEBUG_MODE", "false").lower() == "true"
    log_level = "DEBUG" if debug_mode else "INFO"
    
    # VNPy相关的库日志级别设置为WARNING，减少详细输出
    vnpy_loggers = [
        "vnpy",
        "vnpy.trader",
        "vnpy.event", 
        "vnpy_ctp",
        "vnpy_sopt",
        "ctp",
        "sopt"
    ]
    
    # 系统资源监控相关库日志级别设置
    system_loggers = [
        "psutil",
        "subprocess",
        "urllib3",
        "requests"
    ]
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "%(levelname)s - %(name)s - %(message)s"
            },
            "minimal": {
                "format": "%(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "simple" if debug_mode else "minimal",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": "logs/gateway_manager.log",
                "mode": "a"
            }
        },
        "loggers": {
            # 主应用日志
            "app": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False
            },
            # VNPy相关日志 - 只显示WARNING及以上
            **{logger_name: {
                "level": "WARNING",
                "handlers": ["file"] if not debug_mode else ["console", "file"],
                "propagate": False
            } for logger_name in vnpy_loggers},
            # 系统监控日志 - 只在调试模式显示
            **{logger_name: {
                "level": "ERROR" if not debug_mode else "WARNING", 
                "handlers": ["file"] if not debug_mode else ["console", "file"],
                "propagate": False
            } for logger_name in system_loggers},
            # uvicorn日志优化
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "WARNING",  # 减少访问日志
                "handlers": ["file"],
                "propagate": False
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console"]
        }
    }
    
    return config


def filter_vnpy_logs(record: logging.LogRecord) -> bool:
    """
    过滤VNPy日志，只保留关键信息
    """
    if not hasattr(record, 'getMessage'):
        return True
        
    message = record.getMessage()
    
    # 关键状态变化关键词
    critical_patterns = [
        "连接成功", "连接失败", "登录成功", "登录失败", 
        "授权验证成功", "授权验证失败", "断开连接",
        "connected", "disconnected", "login", "authentication",
        "网关连接成功事件", "交易服务器连接成功事件"
    ]
    
    # 需要过滤的详细信息
    filter_patterns = [
        "修正交易服务器地址", "修正行情服务器地址", "服务器地址",
        "用户名:", "经纪商代码:", "创建行情API对象", "行情数据目录",
        "注册前端服务器", "初始化行情API", "初始化查询任务",
        "CtpMdApi.connect() 开始连接", "CtpMdApi.connect() 完成",
        "发送登录请求", "登录请求结果", "CtpGateway.connect() 执行完成"
    ]
    
    # 错误级别始终显示
    if record.levelno >= logging.ERROR:
        return True
        
    # 调试模式显示所有
    if os.getenv("GATEWAY_DEBUG_MODE", "false").lower() == "true":
        return True
        
    # 检查是否包含关键信息
    for pattern in critical_patterns:
        if pattern in message:
            return True
            
    # 过滤详细信息
    for pattern in filter_patterns:
        if pattern in message:
            return False
            
    return True


class VNPyLogFilter(logging.Filter):
    """VNPy日志过滤器"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        return filter_vnpy_logs(record)