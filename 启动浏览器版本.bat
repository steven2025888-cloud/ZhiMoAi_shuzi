@echo off
chcp 65001 >nul
title 织梦AI - 浏览器版本

echo ========================================
echo   织梦AI大模型 - 浏览器版本
echo ========================================
echo.
echo 正在启动服务器...
echo.

start /B IndexTTS2-SonicVale\installer_files\env\python.exe unified_app.py

echo 等待服务器启动...
timeout /t 5 /nobreak >nul

echo.
echo 正在打开浏览器...
start http://127.0.0.1:7870

echo.
echo ========================================
echo   服务器已启动！
echo   浏览器地址: http://127.0.0.1:7870
echo   关闭此窗口将停止服务器
echo ========================================
echo.
pause
