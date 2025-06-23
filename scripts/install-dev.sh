#!/bin/bash
# Development environment setup script
# Installs dev dependencies and pre-commit hooks

set -e

echo "🛠️ 设置开发环境..."

# 安装开发依赖
echo "📦 安装开发依赖..."
pip install --no-cache-dir -r apps/api/requirements-dev.txt

# 设置 pre-commit hooks
echo "🔧 设置 pre-commit hooks..."
pre-commit install

# 验证开发环境
echo "🧪 验证开发环境..."
python3 -c "
import pytest
import black
import isort
import mypy
print('✅ 开发工具验证成功')
"

echo ""
echo "🎉 开发环境设置完成！"
echo ""
echo "可用命令:"
echo "  black apps/api/  # 代码格式化"
echo "  isort apps/api/  # 导入排序"
echo "  pytest apps/api/ # 运行测试"
echo "  mypy apps/api/   # 类型检查"