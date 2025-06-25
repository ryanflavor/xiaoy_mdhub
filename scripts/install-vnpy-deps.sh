#!/bin/bash
# vnpy 系统依赖安装脚本 - Ubuntu 24.04
# 安装 vnpy_ctp 和 vnpy_sopt 所需的 C++ 编译环境

set -e

echo "🔧 为 Ubuntu 24.04 安装 vnpy 系统依赖..."
echo "vnpy_ctp 和 vnpy_sopt 是项目行情源的必需组件"

# 更新包管理器
echo "📦 更新包管理器..."
sudo apt-get update

# 安装 C++ 编译器和构建工具
echo "📦 安装 C++ 编译器和构建工具..."
sudo apt-get install -y \
    build-essential \
    gcc \
    g++ \
    cmake \
    ninja-build \
    pkg-config \
    python3-dev \
    python3-pip \
    python3-venv

# 安装 Boost 库（vnpy_ctp 的关键依赖）
echo "📦 安装 Boost 库..."
sudo apt-get install -y \
    libboost-all-dev \
    libboost-python-dev \
    libboost-system-dev \
    libboost-thread-dev \
    libboost-locale-dev \
    libboost-date-time-dev \
    libboost-chrono-dev \
    libboost-atomic-dev

# 安装其他必需的系统库
echo "📦 安装其他必需库..."
sudo apt-get install -y \
    git \
    curl \
    libtool \
    autoconf \
    automake \
    wget

# 安装 TA-Lib 库（技术分析库）
echo "📦 安装 TA-Lib 库..."
echo "正在下载和编译 TA-Lib，可能需要几分钟..."

pushd /tmp > /dev/null
if [ ! -f "ta-lib-0.6.4-src.tar.gz" ]; then
    wget https://pip.vnpy.com/colletion/ta-lib-0.6.4-src.tar.gz
fi
tar -xf ta-lib-0.6.4-src.tar.gz
cd ta-lib-0.6.4
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install
sudo ldconfig
popd > /dev/null

echo "✅ TA-Lib 库安装完成"

# 更新conda环境的libstdc++（解决GLIBCXX版本问题）
echo "📦 更新conda环境的libstdc++..."
if command -v conda &> /dev/null; then
    echo "检测到conda环境，正在更新libstdc++..."
    
    # 检查当前是否在base环境
    if [[ "$CONDA_DEFAULT_ENV" == "base" ]]; then
        echo "⚠️ 当前在base环境，跳过conda libstdc++更新以避免依赖冲突"
        echo "请在项目专用环境中运行此脚本，或手动激活环境后再运行"
    else
        # 在非base环境中尝试更新，使用--no-deps避免依赖冲突
        echo "正在环境 '$CONDA_DEFAULT_ENV' 中更新libstdc++..."
        conda install -c conda-forge libstdcxx-ng --no-deps -y || {
            echo "⚠️ conda更新libstdc++失败，将尝试使用系统库路径"
            echo "export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:\$LD_LIBRARY_PATH" >> ~/.bashrc
            echo "已添加系统libstdc++路径到~/.bashrc，请重新加载shell或运行: source ~/.bashrc"
        }
    fi
    echo "✅ libstdc++处理完成"
else
    echo "⚠️ 未检测到conda，跳过conda libstdc++更新"
    echo "将使用系统libstdc++..."
    echo "export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:\$LD_LIBRARY_PATH" >> ~/.bashrc
    echo "已添加系统libstdc++路径到~/.bashrc"
fi

# 安装Python构建工具
echo "📦 安装Python构建工具..."
pip install --upgrade pip setuptools wheel
pip install meson-python meson pybind11 importlib-metadata

# 验证安装
echo "✅ 验证安装..."
echo "GCC: $(gcc --version | head -n1)"
echo "G++: $(g++ --version | head -n1)"
echo "CMake: $(cmake --version | head -n1)"
echo "Python: $(python3 --version)"
echo "Meson: $(meson --version 2>/dev/null || echo '未找到')"

echo ""
echo "🎉 Ubuntu 24.04 系统依赖安装完成！"
echo ""
echo "现在可以安装 vnpy 必需组件:"
echo "  npm run install:vnpy"
echo "或手动安装:"
echo "  pip install --upgrade pip setuptools wheel"
echo "  pip install vnpy"
echo "  # vnpy_ctp 和 vnpy_sopt 将通过本地编译安装"