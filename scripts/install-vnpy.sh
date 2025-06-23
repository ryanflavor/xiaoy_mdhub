#!/bin/bash
# vnpy 必需组件安装脚本 - Ubuntu 24.04 Python 3.12
# 安装 vnpy, vnpy_ctp, vnpy_sopt (项目必需组件)

set -e

echo "🚀 安装 vnpy 必需组件 (Ubuntu 24.04 Python 3.12)..."
echo "vnpy_ctp 和 vnpy_sopt 是项目行情源的核心组件"

# 检查 Python 版本
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python 版本: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" < "3.12" ]]; then
    echo "❌ 错误: 本项目需要 Python 3.12，当前版本为 $PYTHON_VERSION"
    echo "推荐使用 conda 环境安装 Python 3.12"
    exit 1
fi

# 检查系统依赖
echo "🔍 检查系统依赖..."

if ! command -v gcc &> /dev/null; then
    echo "❌ 未找到 GCC，请先运行: npm run install:vnpy:deps"
    exit 1
fi

if ! command -v cmake &> /dev/null; then
    echo "❌ 未找到 CMake，请先运行: npm run install:vnpy:deps"
    exit 1
fi

echo "✅ 系统依赖检查通过"

# 升级构建工具
echo "📦 升级 pip 和构建工具..."
pip install --upgrade pip setuptools wheel

# 安装依赖 (按正确顺序) - Python 3.12 compatible
echo "📦 安装核心依赖..."
pip install --no-cache-dir "numpy>=2.2.3"
pip install --no-cache-dir ta-lib==0.6.4

echo "📦 安装生产依赖 (Python 3.12 完整兼容)..."
pip install --no-cache-dir -r apps/api/requirements.txt

# vnpy 组件现在通过 requirements.txt 安装
echo "✅ 所有依赖已通过 requirements.txt 安装 (Python 3.12 测试通过)"

# 验证安装
echo "🧪 验证必需组件..."
python3 -c "
import vnpy
print('✅ vnpy:', vnpy.__version__)

import vnpy_ctp
print('✅ vnpy_ctp: 导入成功')

import vnpy_sopt  
print('✅ vnpy_sopt: 导入成功')

print('🎉 所有必需组件安装成功！')
"

echo ""
echo "🎉 vnpy 必需组件安装完成！"
echo ""
echo "已安装的必需组件:"
echo "  ✅ vnpy - 核心交易框架"
echo "  ✅ vnpy_ctp - CTP 行情接口 (必需)" 
echo "  ✅ vnpy_sopt - SOPT 期权接口 (必需)"
echo ""
echo "项目现在可以正常运行后端服务！"