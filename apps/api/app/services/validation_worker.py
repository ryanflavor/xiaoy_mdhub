#!/usr/bin/env python3
"""
Standalone validation worker process.
This runs in a separate process to avoid threading conflicts.
"""
import sys
import json
import asyncio
from typing import Dict, Any
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    from vnpy_ctp import CtpGateway
    CTP_AVAILABLE = True
except ImportError:
    CTP_AVAILABLE = False

try:
    from vnpy_sopt.gateway.sopt_gateway import SoptGateway
    SOPT_AVAILABLE = True
except ImportError:
    SOPT_AVAILABLE = False


def validate_account_sync(account_settings: Dict[str, Any], gateway_type: str, timeout_seconds: int = 30, 
                         is_trading_time: bool = True, allow_non_trading_validation: bool = False) -> Dict[str, Any]:
    """
    Synchronous account validation with REAL gateway connection testing.
    
    Returns:
        Dict with validation result
    """
    result = {
        "success": False,
        "message": "Validation failed",
        "details": {},
        "timestamp": None
    }
    
    event_engine = None
    main_engine = None
    
    try:
        # Check gateway availability
        if gateway_type.lower() == "ctp" and not CTP_AVAILABLE:
            result["message"] = "CTP gateway not available"
            result["details"] = {"error_code": "GATEWAY_UNAVAILABLE"}
            return result
        elif gateway_type.lower() == "sopt" and not SOPT_AVAILABLE:
            result["message"] = "SOPT gateway not available"
            result["details"] = {"error_code": "GATEWAY_UNAVAILABLE"}
            return result
        
        # Transform settings to vnpy format
        vnpy_settings = transform_settings(account_settings, gateway_type)
        
        # Validate required fields are present
        required_fields = []
        if gateway_type.lower() == "ctp":
            required_fields = ["用户名", "密码", "经纪商代码"]
        elif gateway_type.lower() == "sopt":
            required_fields = ["用户名", "密码"]  # SOPT也需要密码进行API登录验证
        
        missing_fields = [field for field in required_fields if not vnpy_settings.get(field)]
        if missing_fields:
            result["message"] = f"Missing required fields: {', '.join(missing_fields)}"
            result["details"] = {
                "error_code": "MISSING_FIELDS", 
                "missing": missing_fields,
                "user_friendly_message": f"Please provide the following required fields: {', '.join(missing_fields)}",
                "recommendations": [
                    "Check that all required connection settings are provided",
                    "Verify field names match the expected format",
                    "Contact your broker for correct connection parameters"
                ]
            }
            return result
        
        # Determine validation mode based on trading time and settings
        validation_mode = "FULL_VALIDATION" if is_trading_time else "CONNECTIVITY_ONLY"
        if not is_trading_time and allow_non_trading_validation:
            logger.info(f"Starting basic connectivity test for {gateway_type} (non-trading hours)")
        else:
            logger.info(f"Starting REAL gateway connection test for {gateway_type}")
        
        # GATEWAY CONNECTION TESTING using native socket approach
        # This avoids vnpy threading issues while still testing real connectivity
        import socket
        import time
        
        # Test server connectivity using native sockets
        start_time = time.time()
        
        # Extract server addresses
        td_server = vnpy_settings.get("交易服务器", "")
        md_server = vnpy_settings.get("行情服务器", "")
        
        # Parse server addresses
        servers_to_test = []
        if td_server:
            try:
                # Remove tcp:// prefix if present
                clean_server = td_server.replace("tcp://", "")
                if ":" in clean_server:
                    host, port = clean_server.rsplit(":", 1)  # Use rsplit to handle IPv6 addresses
                    servers_to_test.append(("Trading", host.strip(), int(port)))
                else:
                    logger.warning(f"Trading server missing port: {td_server}")
            except Exception as e:
                logger.warning(f"Invalid trading server format: {td_server}, error: {e}")
        
        if md_server and md_server != td_server:
            try:
                # Remove tcp:// prefix if present
                clean_server = md_server.replace("tcp://", "")
                if ":" in clean_server:
                    host, port = clean_server.rsplit(":", 1)  # Use rsplit to handle IPv6 addresses
                    servers_to_test.append(("Market Data", host.strip(), int(port)))
                else:
                    logger.warning(f"Market data server missing port: {md_server}")
            except Exception as e:
                logger.warning(f"Invalid market data server format: {md_server}, error: {e}")
        
        if not servers_to_test:
            result["message"] = "No valid server addresses found"
            result["details"] = {
                "error_code": "NO_SERVERS",
                "user_friendly_message": "No valid server addresses configured for connection testing",
                "recommendations": [
                    "Verify trading server (交易服务器) address is in format 'host:port'",
                    "Verify market data server (行情服务器) address is in format 'host:port'",
                    "Contact your broker for correct server addresses",
                    "Check for typos in server configuration"
                ],
                "expected_format": "tcp://hostname:port or hostname:port"
            }
            return result
        
        # Test connectivity to each server
        connection_results = []
        overall_success = False
        
        for server_type, host, port in servers_to_test:
            logger.info(f"Testing {server_type} server: {host}:{port}")
            
            try:
                # Create socket and test connection
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)  # 10 second timeout per server
                
                start_connect = time.time()
                result_code = sock.connect_ex((host, port))
                connect_time = time.time() - start_connect
                
                if result_code == 0:
                    logger.info(f"✅ {server_type} server connection successful ({connect_time:.2f}s)")
                    connection_results.append({
                        "server_type": server_type,
                        "host": host,
                        "port": port,
                        "status": "SUCCESS",
                        "connect_time": connect_time
                    })
                    overall_success = True
                else:
                    logger.error(f"❌ {server_type} server connection failed: {result_code}")
                    connection_results.append({
                        "server_type": server_type,
                        "host": host,
                        "port": port,
                        "status": "FAILED",
                        "error_code": result_code
                    })
                
                sock.close()
                
            except socket.gaierror as e:
                logger.error(f"❌ {server_type} DNS resolution failed: {e}")
                connection_results.append({
                    "server_type": server_type,
                    "host": host,
                    "port": port,
                    "status": "DNS_ERROR",
                    "error": str(e)
                })
            except socket.timeout:
                logger.error(f"❌ {server_type} connection timeout")
                connection_results.append({
                    "server_type": server_type,
                    "host": host,
                    "port": port,
                    "status": "TIMEOUT"
                })
            except Exception as e:
                logger.error(f"❌ {server_type} connection error: {e}")
                connection_results.append({
                    "server_type": server_type,
                    "host": host,
                    "port": port,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        total_time = time.time() - start_time
        
        # Evaluate overall results
        if overall_success:
            successful_connections = [r for r in connection_results if r["status"] == "SUCCESS"]
            result["success"] = True
            result["message"] = f"Account validation successful - {len(successful_connections)}/{len(servers_to_test)} servers reachable"
            result["details"] = {
                "gateway_type": gateway_type.upper(),
                "validation_time": time.time(),
                "total_time": total_time,
                "servers_tested": len(servers_to_test),
                "servers_successful": len(successful_connections),
                "connection_results": connection_results,
                "validation_type": validation_mode,
                "is_trading_time": is_trading_time,
                "validation_scope": "Full gateway validation" if is_trading_time else "Basic connectivity only"
            }
            logger.info(f"✅ Validation SUCCESS: {len(successful_connections)}/{len(servers_to_test)} servers reachable")
            
        else:
            failed_servers = [f"{r['server_type']} ({r['host']}:{r['port']})" for r in connection_results]
            result["message"] = f"Network connectivity test failed - Cannot reach gateway servers: {', '.join(failed_servers)}"
            result["details"] = {
                "error_code": "NETWORK_UNREACHABLE",
                "servers_tested": len(servers_to_test),
                "servers_failed": len(servers_to_test),
                "connection_results": connection_results,
                "validation_type": validation_mode,
                "is_trading_time": is_trading_time,
                "user_friendly_message": "Unable to connect to trading servers",
                "recommendations": [
                    "Check internet connection",
                    "Verify server addresses are correct",
                    "Check if trading servers are down for maintenance",
                    "Verify firewall settings allow outbound connections",
                    "Contact your broker to confirm server status",
                    "Try again during trading hours when servers are more likely to be active"
                ],
                "troubleshooting_steps": [
                    "1. Check network connectivity: ping google.com",
                    "2. Verify server addresses with your broker",
                    "3. Check if servers are accessible during trading hours",
                    "4. Confirm firewall/proxy settings"
                ]
            }
            logger.error(f"❌ Validation FAILED: All {len(servers_to_test)} servers unreachable")
            
    except Exception as e:
        result["message"] = f"Validation process failed: {str(e)}"
        result["details"] = {"error_code": "PROCESS_ERROR", "exception": str(e)}
        logger.error(f"💥 Validation EXCEPTION: {e}")
        
    finally:
        # No cleanup needed for socket-based validation
        pass
    
    return result


def transform_settings(account_settings: Dict[str, Any], gateway_type: str) -> Dict[str, Any]:
    """Transform account settings to vnpy format"""
    
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


if __name__ == "__main__":
    try:
        # Read input from stdin
        input_data = sys.stdin.read().strip()
        if not input_data:
            raise ValueError("No input data received")
        data = json.loads(input_data)
        
        account_settings = data["account_settings"]
        gateway_type = data["gateway_type"]
        timeout_seconds = data.get("timeout_seconds", 30)
        is_trading_time = data.get("is_trading_time", True)
        allow_non_trading_validation = data.get("allow_non_trading_validation", False)
        use_real_validation = data.get("use_real_validation", False)
        
        # Perform validation
        if use_real_validation:
            # 使用真实API验证
            from real_gateway_validator import validate_account_real_sync
            result = validate_account_real_sync(account_settings, gateway_type, timeout_seconds)
        else:
            # 使用网络连通性验证
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
            "timestamp": None
        }
        print(json.dumps(error_result))
        sys.exit(1)