#!/bin/bash

# 舆情通项目停止脚本

set -e

echo "停止舆情通服务..."
docker-compose down

echo "服务已停止"
