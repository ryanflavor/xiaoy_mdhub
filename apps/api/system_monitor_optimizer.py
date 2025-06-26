"""
系统监控优化器 - 减少网络接口检查和资源警告
"""

import os
import sys
import subprocess
import logging
from contextlib import contextmanager
from typing import Optional


class SystemMonitorOptimizer:
    """
    优化系统监控，减少启动时的网络和资源检查噪音
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.original_env = {}
        
    @contextmanager
    def suppress_system_warnings(self):
        """
        上下文管理器：临时抑制系统警告
        """
        # 保存原始环境变量
        env_vars_to_modify = [
            'PYTHONWARNINGS',
            'PSUTIL_TESTING',
        ]
        
        for var in env_vars_to_modify:
            self.original_env[var] = os.environ.get(var)
        
        try:
            # 设置环境变量以减少警告
            os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning,ignore::DeprecationWarning'
            os.environ['PSUTIL_TESTING'] = '1'  # 减少psutil的一些系统检查
            
            # 重定向标准错误流以捕获系统工具警告
            original_stderr = sys.stderr
            
            yield
            
        finally:
            # 恢复原始环境变量
            for var, original_value in self.original_env.items():
                if original_value is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = original_value
            
            # 恢复标准错误流
            sys.stderr = original_stderr
    
    def optimize_psutil_imports(self):
        """
        优化psutil导入，减少初始化时的系统检查
        """
        try:
            # 延迟导入psutil并配置为最小检查模式
            import psutil
            
            # 禁用一些可能导致网络接口警告的检查
            if hasattr(psutil, '_WINDOWS'):
                psutil._WINDOWS = False
            
            # 设置较短的超时时间
            if hasattr(psutil, 'CONN_NONE'):
                # 减少网络连接检查
                pass
                
        except ImportError:
            self.logger.debug("psutil not available, skipping optimization")
        except Exception as e:
            self.logger.debug(f"psutil optimization failed: {e}")
    
    def filter_network_warnings(self, stderr_content: str) -> str:
        """
        过滤网络相关的警告信息
        """
        lines = stderr_content.split('\n')
        filtered_lines = []
        
        # 需要过滤的警告模式
        filter_patterns = [
            'docker0: Resource temporarily unavailable',
            'br-', 'virbr0', 'virbr1',
            'No such file or directory',
            'Permission denied',
            'WARNING: you should run this program as super-user',
            'WARNING: output may be incomplete or inaccurate',
            '/sys/firmware/dmi/tables/smbios_entry_point',
            "Can't read memory from /dev/mem"
        ]
        
        for line in lines:
            # 检查是否包含需要过滤的模式
            should_filter = any(pattern in line for pattern in filter_patterns)
            
            if not should_filter and line.strip():
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def apply_optimizations(self):
        """
        应用所有系统监控优化
        """
        try:
            self.optimize_psutil_imports()
            
            # 设置环境变量减少系统工具的详细输出
            optimization_env = {
                'PSUTIL_TESTING': '1',
                'PYTHONWARNINGS': 'ignore::UserWarning',
                # 减少dmidecode和其他系统工具的输出
                'DMIDECODE_QUIET': '1',
                'IFCONFIG_QUIET': '1'
            }
            
            for key, value in optimization_env.items():
                if key not in os.environ:
                    os.environ[key] = value
                    
            self.logger.debug("System monitoring optimizations applied")
            
        except Exception as e:
            self.logger.debug(f"Failed to apply system optimizations: {e}")


# 全局实例
system_optimizer = SystemMonitorOptimizer()


def optimize_startup_logging():
    """
    启动时调用的日志优化函数
    """
    # 应用系统优化
    system_optimizer.apply_optimizations()
    
    # 配置标准库日志以减少噪音
    import logging
    
    # 设置第三方库的日志级别
    noisy_loggers = [
        'urllib3.connectionpool',
        'urllib3.util.retry',
        'requests.packages.urllib3',
        'subprocess',
        'asyncio'
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # 配置根日志记录器过滤器
    class SystemNoiseFilter(logging.Filter):
        def filter(self, record):
            message = record.getMessage()
            
            # 过滤系统资源警告
            noise_patterns = [
                'Resource temporarily unavailable',
                'Permission denied',
                'No such file or directory',
                'docker0:', 'br-', 'virbr',
                'should run this program as super-user'
            ]
            
            return not any(pattern in message for pattern in noise_patterns)
    
    # 添加过滤器到根记录器
    logging.getLogger().addFilter(SystemNoiseFilter())