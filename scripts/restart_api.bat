@echo off
REM 清理 Hyperf 路由缓存并重启服务

echo === 清理 Hyperf 缓存 ===

REM 进入项目目录
cd /d "%~dp0\.."

REM 清理运行时缓存
echo 清理运行时缓存...
if exist runtime\container rmdir /s /q runtime\container
if exist runtime\cache rmdir /s /q runtime\cache

REM 清理代理类缓存
echo 清理代理类缓存...
if exist runtime\proxy rmdir /s /q runtime\proxy

REM 重启服务
echo 重启 Hyperf 服务...
php bin\hyperf.php server:restart

echo === 完成 ===
echo 请等待 5 秒后测试接口
pause
