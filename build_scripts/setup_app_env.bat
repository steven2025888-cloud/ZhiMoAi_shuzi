@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo 织梦AI - 线上版Python环境安装脚本
echo ============================================================
echo.
echo 此脚本将创建一个轻量级Python环境用于线上版
echo 目录结构与TTS版本保持一致，方便后续合并
echo.
echo 目标目录: _internal_app\installer_files\env
echo.

set "APP_ENV_DIR=%~dp0..\_internal_app\installer_files\env"
set "PYTHON_VERSION=3.10"

echo [1/4] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ 未找到Python，请先安装Python %PYTHON_VERSION%
    pause
    exit /b 1
)
echo   ✓ Python已安装

echo.
echo [2/4] 创建虚拟环境...
if exist "%APP_ENV_DIR%" (
    echo   ! 目录已存在，是否删除重建？[Y/N]
    set /p "confirm="
    if /i "!confirm!"=="Y" (
        echo   正在删除旧环境...
        rmdir /s /q "%APP_ENV_DIR%"
    ) else (
        echo   取消操作
        pause
        exit /b 0
    )
)

echo   正在创建虚拟环境...
python -m venv "%APP_ENV_DIR%"
if errorlevel 1 (
    echo   ✗ 创建虚拟环境失败
    pause
    exit /b 1
)
echo   ✓ 虚拟环境创建成功

echo.
echo [3/4] 安装依赖包...
echo   清除代理设置...
set "HTTP_PROXY="
set "HTTPS_PROXY="
set "NO_PROXY="

echo   正在升级pip...
"%APP_ENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

echo   正在安装主程序依赖...
"%APP_ENV_DIR%\Scripts\python.exe" -m pip install gradio requests python-dotenv Pillow opencv-python numpy pycryptodome websockets aiohttp -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo   ✗ 依赖安装失败
    pause
    exit /b 1
)
echo   ✓ 依赖安装完成

echo.
echo [4/4] 验证环境...
"%APP_ENV_DIR%\Scripts\python.exe" -c "import gradio; import requests; print('✓ 环境验证成功')"
if errorlevel 1 (
    echo   ✗ 环境验证失败
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✓ 环境安装完成！
echo ============================================================
echo.
echo 环境位置: %APP_ENV_DIR%
echo.
echo 下一步操作：
echo   1. 测试环境是否能正常运行主程序
echo   2. 打包时修改 setup_zhimengai.iss，将此环境打包为 _internal_tts
echo.
echo 打包说明：
echo   - 线上版：打包 _internal_app 目录（轻量级）
echo   - 本地版：打包 _internal_tts 目录（完整TTS环境）
echo   - 两者目录结构相同，可以互相替换
echo.
pause
