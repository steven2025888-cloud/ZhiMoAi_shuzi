@echo off
chcp 65001 >nul

:: 切换到项目根目录（本脚本在 build_scripts\ 子目录下）
pushd "%~dp0.."

echo ========================================
echo 构建 ZhiMoAI 启动器
echo ========================================
echo.

echo [1/2] 检查 PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller 未安装，正在安装...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
)

echo [2/2] 构建启动器 exe...
pyinstaller --onefile --noconsole --icon=logo.ico --name=ZhiMoAI_Launcher launcher.py
if errorlevel 1 (
    echo [错误] 启动器构建失败
    pause
    exit /b 1
)

echo.
echo 复制启动器到项目根目录...
copy /Y dist\ZhiMoAI_Launcher.exe .
if errorlevel 1 (
    echo [错误] 复制启动器失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 启动器构建成功！
echo 输出文件: ZhiMoAI_Launcher.exe
echo ========================================
popd
pause
