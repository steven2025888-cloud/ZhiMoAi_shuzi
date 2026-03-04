@echo off
chcp 65001 >nul

:: 切换到项目根目录（本脚本在 build_scripts\ 子目录下）
pushd "%~dp0.."

echo ========================================
echo 构建 ZhiMoAI 启动器 (onedir)
echo ========================================
echo.

echo [1/3] 检查 PyInstaller...
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

echo [2/3] 构建启动器 (onedir 模式)...
:: --onedir: 运行时文件放在 _launcher_runtime 子目录，彻底消除 _MEI 临时目录问题
pyinstaller --noconfirm --onedir --noconsole --icon=logo.ico --name=织梦IP --contents-directory=_launcher_runtime launcher.py
if errorlevel 1 (
    echo [错误] 启动器构建失败
    pause
    exit /b 1
)

echo.
echo [3/3] 复制启动器到项目根目录...
:: 复制 exe
copy /Y "dist\织梦IP\织梦IP.exe" .
if errorlevel 1 (
    echo [错误] 复制启动器 exe 失败
    pause
    exit /b 1
)
:: 复制运行时目录
if exist "_launcher_runtime" rmdir /s /q "_launcher_runtime"
xcopy /E /I /Y "dist\织梦IP\_launcher_runtime" "_launcher_runtime" >nul
if errorlevel 1 (
    echo [错误] 复制运行时目录失败
    pause
    exit /b 1
)
echo   [OK]

echo.
echo ========================================
echo 启动器构建成功！(onedir)
echo 输出: 织梦IP.exe + _launcher_runtime\
echo ========================================
popd
