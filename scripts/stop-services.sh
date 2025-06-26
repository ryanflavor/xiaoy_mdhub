#!/bin/bash

# Market Data Hub - 停止服务脚本
# 使用方法: ./scripts/stop-services.sh [api|web|all]

set +e  # 允许命令失败而不退出脚本

echo "🛑 Market Data Hub - 停止服务脚本"
echo "================================="
echo

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 停止后端API服务
stop_api() {
    echo "🔥 正在停止后端API服务..."
    
    # 方法1: 通过端口8000查找进程
    API_PID=$(lsof -ti:8000 2>/dev/null)
    if [ -n "$API_PID" ]; then
        echo "发现API进程 PID: $API_PID"
        kill -TERM $API_PID 2>/dev/null
        sleep 2
        
        # 检查是否还在运行
        if kill -0 $API_PID 2>/dev/null; then
            echo "正常关闭失败，强制终止..."
            kill -9 $API_PID 2>/dev/null
        fi
        
        echo -e "${GREEN}✅ API服务已停止${NC}"
    else
        echo -e "${YELLOW}⚠️  未发现运行中的API服务${NC}"
    fi
    
    # 方法2: 查找uvicorn进程
    UVICORN_PIDS=$(pgrep -f "uvicorn.*main:app" 2>/dev/null)
    if [ -n "$UVICORN_PIDS" ]; then
        echo "发现uvicorn进程: $UVICORN_PIDS"
        echo "$UVICORN_PIDS" | xargs kill -TERM 2>/dev/null
        sleep 2
        echo "$UVICORN_PIDS" | xargs kill -9 2>/dev/null
        echo -e "${GREEN}✅ uvicorn进程已清理${NC}"
    fi
}

# 停止前端Web服务
stop_web() {
    echo "🔥 正在停止前端Web服务..."
    
    # 查找端口3000的进程
    WEB_PID=$(lsof -ti:3000 2>/dev/null)
    if [ -n "$WEB_PID" ]; then
        echo "发现Web进程 PID: $WEB_PID"
        kill -TERM $WEB_PID 2>/dev/null
        sleep 2
        
        # 检查是否还在运行
        if kill -0 $WEB_PID 2>/dev/null; then
            echo "正常关闭失败，强制终止..."
            kill -9 $WEB_PID 2>/dev/null
        fi
        
        echo -e "${GREEN}✅ Web服务已停止${NC}"
    else
        echo -e "${YELLOW}⚠️  未发现运行中的Web服务${NC}"
    fi
    
    # 查找Next.js进程
    NEXTJS_PIDS=$(pgrep -f "next.*dev" 2>/dev/null)
    if [ -n "$NEXTJS_PIDS" ]; then
        echo "发现Next.js进程: $NEXTJS_PIDS"
        echo "$NEXTJS_PIDS" | xargs kill -TERM 2>/dev/null
        sleep 2
        echo "$NEXTJS_PIDS" | xargs kill -9 2>/dev/null
        echo -e "${GREEN}✅ Next.js进程已清理${NC}"
    fi
}

# 停止所有相关的npm进程
stop_npm_processes() {
    echo "🔥 正在停止npm相关进程..."
    
    # 查找npm run相关进程
    NPM_PIDS=$(pgrep -f "npm.*run" 2>/dev/null)
    if [ -n "$NPM_PIDS" ]; then
        echo "发现npm进程: $NPM_PIDS"
        echo "$NPM_PIDS" | xargs kill -TERM 2>/dev/null
        sleep 2
        echo "$NPM_PIDS" | xargs kill -9 2>/dev/null
        echo -e "${GREEN}✅ npm进程已清理${NC}"
    fi
}

# 主逻辑
case "${1:-all}" in
    "api")
        stop_api
        ;;
    "web")
        stop_web
        ;;
    "all")
        stop_api
        echo
        stop_web
        echo
        stop_npm_processes
        ;;
    *)
        echo "使用方法: $0 [api|web|all]"
        echo "  api  - 仅停止后端API服务"
        echo "  web  - 仅停止前端Web服务"
        echo "  all  - 停止所有服务 (默认)"
        exit 1
        ;;
esac

echo
echo "🔍 检查剩余进程..."
echo "端口8000: $(lsof -ti:8000 2>/dev/null || echo '空闲')"
echo "端口3000: $(lsof -ti:3000 2>/dev/null || echo '空闲')"

echo
echo -e "${GREEN}✅ 服务停止完成！${NC}"
echo -e "${YELLOW}💡 重新启动服务: npm run api:dev 和 npm run web:dev${NC}"