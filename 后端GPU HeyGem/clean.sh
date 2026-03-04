#!/bin/bash
# 织梦AI - GPU服务器一键清理脚本
# 用法: bash /root/HeyGem/clean.sh

HEYGEM_DIR=/root/HeyGem
cd "$HEYGEM_DIR" || { echo "[错误] 目录不存在: $HEYGEM_DIR"; exit 1; }

echo ""
echo "[1/4] 清理上传目录..."
rm -rf uploads/pool/* uploads/assets/* uploads/work/* uploads/store/*

echo "[2/4] 清理输出和缓存..."
rm -rf outputs/*

echo "[3/4] 清理临时文件..."
rm -rf temp/* result/*

echo "[4/4] 清理数据库..."
rm -f assets.db

echo ""
echo "========================================"
echo "  清理完成! 服务器已恢复全新状态"
echo "========================================"
echo ""
du -sh uploads/ outputs/ temp/ result/ 2>/dev/null || true
