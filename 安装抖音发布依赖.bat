@echo off
chcp 65001 >nul
title 安装抖音发布依赖

echo ========================================
echo 织梦AI - 安装抖音发布依赖
echo ========================================
echo.

set PYTHON_PATH=IndexTTS2-SonicVale\installer_files\env\python.exe

echo [1/2] 检查 Python 环境...
if not exist "%PYTHON_PATH%" (
    echo [错误] 找不到 Python: %PYTHON_PATH%
    pause
    exit /b 1
)
echo [✓] Python 环境存在

echo.
echo [2/2] 安装依赖包...
echo 正在安装 selenium...
"%PYTHON_PATH%" -m pip install selenium -i https://pypi.tuna.tsinghua.edu.cn/simple
if %ERRORLEVEL% NEQ 0 (
    echo [错误] selenium 安装失败
    pause
    exit /b 1
)

echo.
echo 正在安装 requests（用于下载ChromeDriver）...
"%PYTHON_PATH%" -m pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
if %ERRORLEVEL% NEQ 0 (
    echo [错误] requests 安装失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo [✓] 依赖安装完成！
echo ========================================
echo.
echo 现在可以使用抖音自动发布功能了。
echo.
pause
