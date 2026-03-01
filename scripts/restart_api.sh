#!/bin/bash
# 清理 Hyperf 路由缓存并重启服务

echo "=== 清理 Hyperf 缓存 ==="

# 进入项目目录
cd "$(dirname "$0")/.."

# 清理运行时缓存
echo "清理运行时缓存..."
rm -rf runtime/container/*
rm -rf runtime/cache/*

# 清理代理类缓存
echo "清理代理类缓存..."
rm -rf runtime/proxy/*

# 重启服务
echo "重启 Hyperf 服务..."
php bin/hyperf.php server:restart

echo "=== 完成 ==="
echo "请等待 5 秒后测试接口"
