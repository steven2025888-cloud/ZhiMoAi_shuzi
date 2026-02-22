@echo off
chcp 65001 >nul
echo ============================================================
echo 织梦AI - 打包前验证工具
echo ============================================================
echo.

set ERROR_COUNT=0

echo [检查1] 验证Python环境...
set PYTHON_EXE=_internal_tts\installer_files\env\python.exe
if exist "%PYTHON_EXE%" (
    echo   ✓ Python环境存在
) else (
    echo   ✗ Python环境不存在：%PYTHON_EXE%
    set /a ERROR_COUNT+=1
)

echo.
echo [检查2] 验证核心Python文件...
set CORE_FILES=app_backend.py unified_app.py lib_avatar.py lib_voice.py lib_subtitle.py lib_license.py lib_douyin_publish.py lib_meta_store.py ws_worker.py
for %%F in (%CORE_FILES%) do (
    if exist "%%F" (
        echo   ✓ %%F
    ) else (
        echo   ✗ %%F 缺失
        set /a ERROR_COUNT+=1
    )
)

echo.
echo [检查3] 验证前端资源...
if exist "ui_init.js" (
    echo   ✓ ui_init.js
) else (
    echo   ✗ ui_init.js 缺失
    set /a ERROR_COUNT+=1
)
if exist "ui_style.css" (
    echo   ✓ ui_style.css
) else (
    echo   ✗ ui_style.css 缺失
    set /a ERROR_COUNT+=1
)

echo.
echo [检查4] 验证图标文件...
if exist "logo.ico" (
    echo   ✓ logo.ico
) else (
    echo   ✗ logo.ico 缺失
    set /a ERROR_COUNT+=1
)
if exist "logo.jpg" (
    echo   ✓ logo.jpg
) else (
    echo   ⚠ logo.jpg 缺失（可选）
)

echo.
echo [检查5] 验证启动器...
if exist "ZhiMoAI_Launcher.exe" (
    echo   ✓ ZhiMoAI_Launcher.exe
) else (
    echo   ⚠ ZhiMoAI_Launcher.exe 不存在（打包时会自动构建）
)

echo.
echo [检查6] 验证启动脚本...
if exist "启动应用.bat" (
    echo   ✓ 启动应用.bat
) else (
    echo   ✗ 启动应用.bat 缺失
    set /a ERROR_COUNT+=1
)

echo.
echo [检查7] 验证Inno Setup...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    echo   ✓ Inno Setup 6已安装
) else (
    echo   ✗ Inno Setup 6未安装或路径不正确
    set /a ERROR_COUNT+=1
)

echo.
echo [检查8] 验证打包配置...
if exist "setup_zhimengai.iss" (
    echo   ✓ setup_zhimengai.iss
) else (
    echo   ✗ setup_zhimengai.iss 缺失
    set /a ERROR_COUNT+=1
)

echo.
echo [检查9] 验证编译工具...
if exist "build_pyc_for_package.py" (
    echo   ✓ build_pyc_for_package.py
) else (
    echo   ✗ build_pyc_for_package.py 缺失
    set /a ERROR_COUNT+=1
)

echo.
echo ============================================================
if %ERROR_COUNT%==0 (
    echo ✓ 所有检查通过！可以开始打包
    echo.
    echo 运行以下命令开始打包：
    echo   build_package.bat
) else (
    echo ✗ 发现 %ERROR_COUNT% 个错误，请修复后再打包
)
echo ============================================================
echo.
pause
