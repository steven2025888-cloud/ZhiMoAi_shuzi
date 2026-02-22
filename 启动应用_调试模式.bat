@echo off
chcp 65001 >nul
title 织梦AI - 调试模式启动

echo ========================================
echo 织梦AI大模型 - 调试模式启动
echo ========================================
echo.

set PYTHON_PATH=_internal_tts\installer_files\env\python.exe
set SCRIPT_PATH=app_backend.py

echo [1/3] 检查 Python 解释器...
if not exist "%PYTHON_PATH%" (
    echo [错误] 找不到 Python 解释器: %PYTHON_PATH%
    echo.
    pause
    exit /b 1
)
echo [✓] Python 解释器存在

echo.
echo [2/3] 检查主程序文件...
if not exist "%SCRIPT_PATH%" (
    echo [错误] 找不到主程序文件: %SCRIPT_PATH%
    echo.
    pause
    exit /b 1
)
echo [✓] 主程序文件存在

echo.
echo [3/3] 启动程序...
echo 命令: "%PYTHON_PATH%" "%SCRIPT_PATH%"
echo.
echo ========================================
echo Program is running, do not close this window
echo To exit, close the main window or press Ctrl+C
echo ========================================
echo.

"%PYTHON_PATH%" "%SCRIPT_PATH%"

echo.
echo ========================================
echo Program exited, exit code: %ERRORLEVEL%
echo ========================================
echo.
pause
