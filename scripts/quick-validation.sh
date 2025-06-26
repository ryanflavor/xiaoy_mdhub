#!/bin/bash

# Market Data Hub - 快速验证脚本
# 使用方法: ./scripts/quick-validation.sh

set -e

echo "🧪 Market Data Hub - 快速验证脚本"
echo "=================================="
echo

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
    else
        echo -e "${RED}❌ $1${NC}"
        return 1
    fi
}

# 1. 检查环境文件
echo "📁 检查环境配置文件..."

if [ -f "apps/web/.env.local" ]; then
    echo -e "${GREEN}✅ 前端环境文件存在${NC}"
    echo "内容:"
    cat apps/web/.env.local | sed 's/^/  /'
else
    echo -e "${RED}❌ 前端环境文件缺失${NC}"
    exit 1
fi

echo

if [ -f "apps/api/.env" ]; then
    echo -e "${GREEN}✅ 后端环境文件存在${NC}"
    echo "关键配置:"
    grep -E "(CORS_ORIGINS|ENABLE_CTP_MOCK|ENABLE_SOPT_MOCK)" apps/api/.env | sed 's/^/  /'
else
    echo -e "${RED}❌ 后端环境文件缺失${NC}"
    exit 1
fi

echo
echo "=================================================="

# 2. 检查构建状态
echo "🔨 检查项目构建状态..."

npm run type-check > /dev/null 2>&1
check_status "TypeScript 类型检查"

npm run lint > /dev/null 2>&1
check_status "代码风格检查"

echo
echo "=================================================="

# 3. 检查服务是否运行
echo "🚀 检查服务运行状态..."

# 检查后端API
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 后端API服务运行中 (localhost:8000)${NC}"
    
    # 测试API响应时间
    RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
    echo "  API响应时间: ${RESPONSE_TIME}s"
    
    # 测试API数据格式
    API_RESPONSE=$(curl -s http://localhost:8000/health)
    if echo "$API_RESPONSE" | jq -e '.gateway_manager.accounts' > /dev/null 2>&1; then
        ACCOUNT_COUNT=$(echo "$API_RESPONSE" | jq '.gateway_manager.accounts | length')
        echo -e "${GREEN}✅ API数据格式正确，发现 $ACCOUNT_COUNT 个账户${NC}"
    else
        echo -e "${YELLOW}⚠️  API数据格式异常${NC}"
    fi
else
    echo -e "${RED}❌ 后端API服务未运行${NC}"
    echo -e "${YELLOW}💡 请运行: npm run api:dev${NC}"
fi

# 检查前端Web
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 前端Web服务运行中 (localhost:3000)${NC}"
else
    echo -e "${RED}❌ 前端Web服务未运行${NC}"
    echo -e "${YELLOW}💡 请运行: npm run web:dev${NC}"
fi

echo
echo "=================================================="

# 4. 文件结构检查
echo "📂 检查关键文件结构..."

KEY_FILES=(
    "apps/web/src/hooks/use-dashboard-data.ts"
    "apps/web/src/services/websocket.ts"
    "apps/web/src/components/error-boundary.tsx"
    "apps/web/src/components/connection-status.tsx"
    "apps/web/src/hooks/use-connection-status.ts"
)

for file in "${KEY_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ $file${NC}"
    fi
done

echo
echo "=================================================="

# 5. 生成验证报告
echo "📋 验证摘要报告"
echo

echo -e "${YELLOW}下一步验证操作:${NC}"
echo "1. 打开浏览器访问: http://localhost:3000"
echo "2. 检查仪表板是否显示4个网关卡片"
echo "3. 打开开发者工具查看WebSocket连接"
echo "4. 测试离线模式和错误处理"
echo

echo -e "${YELLOW}手动测试清单:${NC}"
echo "□ 网关状态卡片显示正确"
echo "□ 系统健康摘要显示"
echo "□ WebSocket连接建立"
echo "□ 实时状态更新工作"
echo "□ 错误处理UI测试"
echo "□ 离线/重连测试"
echo

echo -e "${GREEN}✅ 快速验证完成！${NC}"
echo -e "${YELLOW}详细验证指南: ./validation-steps.md${NC}"