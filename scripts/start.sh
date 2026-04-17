#!/bin/bash

# 舆情通项目一键启动脚本

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo "========================================"
echo "   舆情通项目启动脚本"
echo "========================================"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装"
    exit 1
fi

# 检查.env文件
if [ ! -f ".env" ]; then
    log_info "创建.env配置文件..."
    cp .env.example .env 2>/dev/null || true
fi

# 构建并启动
log_info "构建Docker镜像并启动服务..."
docker-compose up -d --build

log_success "服务启动完成!"
echo ""
echo "访问地址:"
echo "  前端: http://localhost:3000"
echo "  后端: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
echo ""
