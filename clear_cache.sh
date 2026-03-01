#!/bin/bash
# 清除 Hyperf 缓存和 PHP opcache

echo "正在清除缓存..."

# 停止 Hyperf 服务
php bin/hyperf.php stop

# 清除 Hyperf 运行时缓存
rm -rf runtime/container/*
rm -rf runtime/cache/*

# 清除 Composer 类映射缓存
composer dump-autoload

echo "缓存已清除，正在重启服务..."

# 启动 Hyperf 服务
php bin/hyperf.php start

echo "完成！"
