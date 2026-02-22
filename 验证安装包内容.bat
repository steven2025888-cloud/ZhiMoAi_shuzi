@echo off
chcp 65001 >nul
echo ============================================================
echo 织梦AI - 安装包内容验证工具
echo ============================================================
echo.

set TEST_DIR=D:\ZhiMoAI

if not exist "%TEST_DIR%" (
    echo ✗ 测试目录不存在：%TEST_DIR%
    echo.
    echo 请先安装安装包到该目录
    pause
    exit /b 1
)

echo 正在检查：%TEST_DIR%
echo.

echo [检查1] 验证.pyc文件（应该存在）
set PYC_COUNT=0
for %%F in (app_backend.pyc unified_app.pyc lib_avatar.pyc lib_voice.pyc lib_subtitle.pyc lib_license.pyc lib_douyin_publish.pyc lib_meta_store.pyc ws_worker.pyc) do (
    if exist "%TEST_DIR%\%%F" (
        echo   ✓ %%F
        set /a PYC_COUNT+=1
    ) else (
        echo   ✗ %%F 缺失
    )
)
echo   共找到 %PYC_COUNT% 个.pyc文件（应为9个）

echo.
echo [检查2] 验证.py文件（不应该存在）
set PY_COUNT=0
for %%F in (app_backend.py unified_app.py lib_avatar.py lib_voice.py lib_subtitle.py lib_license.py lib_douyin_publish.py lib_meta_store.py ws_worker.py) do (
    if exist "%TEST_DIR%\%%F" (
        echo   ✗ %%F 存在（不应该有.py源文件！）
        set /a PY_COUNT+=1
    )
)
if %PY_COUNT%==0 (
    echo   ✓ 无.py源文件（正确）
) else (
    echo   ✗ 发现 %PY_COUNT% 个.py文件（错误！）
)

echo.
echo [检查3] 验证前端资源
if exist "%TEST_DIR%\ui_init.js" (
    echo   ✓ ui_init.js
) else (
    echo   ✗ ui_init.js 缺失
)
if exist "%TEST_DIR%\ui_style.css" (
    echo   ✓ ui_style.css
) else (
    echo   ✗ ui_style.css 缺失
)

echo.
echo [检查4] 验证启动文件
if exist "%TEST_DIR%\ZhiMoAI_Launcher.exe" (
    echo   ✓ ZhiMoAI_Launcher.exe
) else (
    echo   ✗ ZhiMoAI_Launcher.exe 缺失
)
if exist "%TEST_DIR%\启动应用.bat" (
    echo   ✓ 启动应用.bat
) else (
    echo   ✗ 启动应用.bat 缺失
)

echo.
echo [检查5] 验证配置文件
if exist "%TEST_DIR%\.env" (
    echo   ✓ .env
) else (
    echo   ✗ .env 缺失
)

echo.
echo [检查6] 验证图标文件
if exist "%TEST_DIR%\logo.ico" (
    echo   ✓ logo.ico
) else (
    echo   ✗ logo.ico 缺失
)

echo.
echo ============================================================
if %PY_COUNT%==0 (
    if %PYC_COUNT%==9 (
        echo ✓ 验证通过！安装包只包含.pyc加密文件
    ) else (
        echo ⚠ .pyc文件数量不正确（应为9个，实际%PYC_COUNT%个）
    )
) else (
    echo ✗ 验证失败！发现.py源文件，需要重新打包
)
echo ============================================================
echo.
pause
