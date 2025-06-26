#!/bin/bash

# Market Data Hub - 启动服务脚本
# 使用方法: ./scripts/start-services.sh [api|web|all]

set -e

echo "🚀 Market Data Hub - 启动服务脚本"
echo "================================="
echo

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -ti:$port >/dev/null 2>&1; then
        return 1  # 端口被占用
    else
        return 0  # 端口空闲
    fi
}

# 启动后端API服务
start_api() {
    echo "🔥 启动后端API服务..."
    
    if ! check_port 8000; then
        echo -e "${YELLOW}⚠️  端口8000已被占用，先停止现有服务...${NC}"
        ./scripts/stop-services.sh api
        sleep 2
    fi
    
    echo "检查conda环境..."
    if ! command -v conda &> /dev/null; then
        echo -e "${RED}❌ conda未找到，请安装Anaconda/Miniconda${NC}"
        exit 1
    fi
    
    echo "激活conda环境 'hub'..."
    eval "$(conda shell.bash hook)"
    conda activate hub
    
    echo "启动FastAPI服务器..."
    echo -e "${BLUE}📍 API将在 http://localhost:8000 启动${NC}"
    echo -e "${BLUE}📍 API文档: http://localhost:8000/docs${NC}"
    echo
    
    cd apps/api
    python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
    API_PID=$!
    cd - > /dev/null
    
    echo "API服务启动中... PID: $API_PID"
    
    # 等待API服务完全启动 (最多30秒)
    echo "等待API服务完全启动..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API服务启动成功！${NC}"
            break
        fi
        echo -n "."
        sleep 1
        if [ $i -eq 30 ]; then
            echo
            echo -e "${RED}❌ API服务启动超时${NC}"
            exit 1
        fi
    done
}

# 启动前端Web服务
start_web() {
    echo "🔥 启动前端Web服务..."
    
    if ! check_port 3000; then
        echo -e "${YELLOW}⚠️  端口3000已被占用，先停止现有服务...${NC}"
        ./scripts/stop-services.sh web
        sleep 2
    fi
    
    echo "启动Next.js开发服务器..."
    echo -e "${BLUE}📍 Web将在 http://localhost:3000 启动${NC}"
    echo
    
    cd apps/web
    npm run dev &
    WEB_PID=$!
    cd - > /dev/null
    
    echo "Web服务启动中... PID: $WEB_PID"
    sleep 5
    
    # 检查服务是否启动成功
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Web服务启动成功！${NC}"
    else
        echo -e "${YELLOW}⚠️  Web服务可能还在启动中...${NC}"
    fi
}

# 显示服务状态
show_status() {
    echo
    echo "📊 服务状态检查:"
    echo "================================="
    
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "API (8000):  ${GREEN}✅ 运行中${NC}"
    else
        echo -e "API (8000):  ${RED}❌ 未运行${NC}"
    fi
    
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "Web (3000):  ${GREEN}✅ 运行中${NC}"
    else
        echo -e "Web (3000):  ${RED}❌ 未运行${NC}"
    fi
    
    echo
    echo "🔗 访问链接:"
    echo "- 仪表板: http://localhost:3000"
    echo "- API文档: http://localhost:8000/docs"
    echo "- API健康: http://localhost:8000/health"
}

# 主逻辑
case "${1:-all}" in
    "api")
        start_api
        show_status
        ;;
    "web")
        start_web
        show_status
        ;;
    "all")
        start_api
        echo
        start_web
        show_status
        echo
        echo -e "${GREEN}🎉 所有服务启动完成！${NC}"
        echo -e "${YELLOW}💡 停止服务: ./scripts/stop-services.sh${NC}"
        echo -e "${YELLOW}💡 查看日志: 在各自终端窗口中查看${NC}"
        ;;
    *)
        echo "使用方法: $0 [api|web|all]"
        echo "  api  - 仅启动后端API服务"
        echo "  web  - 仅启动前端Web服务"
        echo "  all  - 启动所有服务 (默认)"
        exit 1
        ;;
esac