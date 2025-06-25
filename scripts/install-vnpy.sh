#!/bin/bash
# vnpy 必需组件安装脚本 - Ubuntu 24.04 Python 3.12
# 安装 vnpy, vnpy_ctp, vnpy_sopt (项目必需组件)

set -e

# 设置环境变量以使用系统的libstdc++
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"

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

# 确保构建依赖已安装
echo "📦 确保构建依赖已安装..."
pip install meson-python meson pybind11 importlib-metadata

# 安装依赖 (按正确顺序) - Python 3.12 compatible
echo "📦 安装核心依赖..."
pip install --no-cache-dir "numpy>=2.2.3"
pip install --no-cache-dir ta-lib==0.6.4

echo "📦 安装生产依赖 (Python 3.12 完整兼容)..."
# 修改requirements.txt中的vnpy_ctp和vnpy_sopt行，暂时排除它们
pip install --no-cache-dir -r <(grep -v "vnpy_ctp\|vnpy_sopt" apps/api/requirements.txt)

# 安装vnpy核心框架
pip install --no-cache-dir vnpy==4.0.0

# 本地编译安装 vnpy_ctp
echo "📦 本地编译安装 vnpy_ctp..."
pushd packages/libs/vnpy_ctp > /dev/null
echo "正在编译 vnpy_ctp (CTP行情接口)..."
pip install -e . --no-build-isolation
if [ $? -eq 0 ]; then
    echo "✅ vnpy_ctp 编译安装成功"
else
    echo "❌ vnpy_ctp 编译失败"
    popd > /dev/null
    exit 1
fi
popd > /dev/null

# 本地编译安装 vnpy_sopt
echo "📦 本地编译安装 vnpy_sopt..."
pushd packages/libs/vnpy_sopt > /dev/null
echo "正在编译 vnpy_sopt (SOPT期权接口)..."
pip install -e . --no-build-isolation
if [ $? -eq 0 ]; then
    echo "✅ vnpy_sopt 编译安装成功"
else
    echo "❌ vnpy_sopt 编译失败"
    popd > /dev/null
    exit 1
fi
popd > /dev/null

echo "✅ 所有依赖已安装完成 (Python 3.12 + 本地编译)"

# 验证安装
echo "🧪 验证必需组件..."
python3 -c "
import vnpy
print('✅ vnpy:', vnpy.__version__)

try:
    import vnpy_ctp
    print('✅ vnpy_ctp: 导入成功')
except Exception as e:
    print('❌ vnpy_ctp: 导入失败 -', str(e))

try:
    import vnpy_sopt  
    print('✅ vnpy_sopt: 导入成功')
except Exception as e:
    print('❌ vnpy_sopt: 导入失败 -', str(e))

print('🎉 必需组件验证完成！')
"

echo ""
echo "🎉 vnpy 必需组件安装完成！"
echo ""
echo "已安装的必需组件:"
echo "  ✅ vnpy - 核心交易框架"
echo "  ✅ vnpy_ctp - CTP 行情接口 (本地编译)" 
echo "  ✅ vnpy_sopt - SOPT 期权接口 (本地编译)"
echo ""

# 确保环境变量永久生效
echo "📦 设置永久环境变量..."
BASHRC_ENTRY="export LD_LIBRARY_PATH=\"/usr/lib/x86_64-linux-gnu:\$LD_LIBRARY_PATH\""
if ! grep -q "LD_LIBRARY_PATH.*x86_64-linux-gnu" ~/.bashrc; then
    echo "$BASHRC_ENTRY" >> ~/.bashrc
    echo "✅ 已添加LD_LIBRARY_PATH到~/.bashrc"
else
    echo "✅ LD_LIBRARY_PATH已存在于~/.bashrc"
fi

echo ""
echo "项目现在可以正常运行后端服务！"
echo "注意：请重新加载shell或运行 'source ~/.bashrc' 以确保环境变量生效"