@echo off
chcp 65001 >nul
echo ============================================================
echo 织梦AI - 自动化打包系统
echo ============================================================
echo.
echo 此脚本将执行以下操作：
echo   1. 清理临时目录
echo   2. 编译Python代码为.pyc字节码
echo   3. 构建启动器（如需要）
echo   4. 生成安装包
echo   5. 清理临时.pyc文件
echo.

echo.
echo [1/6] 清理临时目录...
if exist "avatars" rmdir /s /q "avatars" 2>nul & mkdir "avatars"
if exist "voices" rmdir /s /q "voices" 2>nul & mkdir "voices"
if exist "unified_outputs" rmdir /s /q "unified_outputs" 2>nul & mkdir "unified_outputs"
echo   ✓ 临时目录已清理

echo.
echo [2/6] 编译Python代码为.pyc字节码...
python build_pyc_for_package.py
if errorlevel 1 (
    echo   ✗ 错误：Python编译失败
    exit /b 1
)
echo   ✓ Python代码编译完成

echo.
echo [3/6] 检查启动器...
if not exist "ZhiMoAI_Launcher.exe" (
    echo   启动器不存在，开始构建...
    call build_launcher.bat
    if errorlevel 1 (
        echo   ✗ 错误：启动器构建失败
        python build_pyc_for_package.py --clean
        exit /b 1
    )
    echo   ✓ 启动器构建完成
) else (
    echo   ✓ 启动器已存在
)

echo.
echo [4/6] 验证.pyc文件...
set MISSING=0
if not exist "app_backend.pyc" set MISSING=1
if not exist "unified_app.pyc" set MISSING=1
if not exist "lib_avatar.pyc" set MISSING=1
if not exist "lib_voice.pyc" set MISSING=1
if not exist "lib_subtitle.pyc" set MISSING=1
if not exist "lib_license.pyc" set MISSING=1
if not exist "lib_douyin_publish.pyc" set MISSING=1
if not exist "lib_meta_store.pyc" set MISSING=1
if not exist "ws_worker.pyc" set MISSING=1

if %MISSING%==1 (
    echo   ✗ 错误：部分.pyc文件缺失
    dir *.pyc /b 2>nul
    exit /b 1
)
echo   ✓ 所有.pyc文件已就绪

echo.
echo [5/6] 生成安装包...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    echo   正在编译安装包，请稍候...
    %ISCC% setup_zhimengai.iss
    if errorlevel 1 (
        echo   ✗ 错误：Inno Setup编译失败
        python build_pyc_for_package.py --clean
        exit /b 1
    )
    echo   ✓ 安装包生成完成
) else (
    echo   ✗ 错误：未找到Inno Setup
    echo   请安装Inno Setup 6到默认路径
    python build_pyc_for_package.py --clean
    exit /b 1
)

echo.
echo [6/6] 清理临时.pyc文件...
python build_pyc_for_package.py --clean
echo   ✓ 临时文件已清理

echo.
echo ============================================================
echo ✓ 打包成功！
echo ============================================================
echo.
echo 安装包位置：dist\ZhiMoAI_v2.0_Setup.exe
if exist "dist\ZhiMoAI_v2.0_Setup.exe" (
    for %%F in ("dist\ZhiMoAI_v2.0_Setup.exe") do echo 文件大小：%%~zF 字节 ^(约 %%~zF / 1048576 MB^)
)
echo.
echo 重要提示：
echo   ✓ 安装包只包含.pyc加密文件，不包含.py源文件
echo   ✓ 原始.py文件未被修改，可以继续开发
echo   ✓ 临时.pyc文件已清理
echo.
echo 验证安装包：
echo   1. 安装到测试目录（如D:\ZhiMoAI）
echo   2. 运行"验证安装包内容.bat"检查
echo   3. 确认只有.pyc文件，没有.py文件
echo.
echo ============================================================
