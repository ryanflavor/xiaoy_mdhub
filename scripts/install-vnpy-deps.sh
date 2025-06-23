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
    automake

# 验证安装
echo "✅ 验证安装..."
echo "GCC: $(gcc --version | head -n1)"
echo "G++: $(g++ --version | head -n1)"
echo "CMake: $(cmake --version | head -n1)"
echo "Python: $(python3 --version)"

echo ""
echo "🎉 Ubuntu 24.04 系统依赖安装完成！"
echo ""
echo "现在可以安装 vnpy 必需组件:"
echo "  npm run install:vnpy"
echo "或手动安装:"
echo "  pip install --upgrade pip setuptools wheel"
echo "  pip install vnpy vnpy_ctp vnpy_sopt"