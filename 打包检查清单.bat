@echo off
chcp 65001 >nul
title 织梦AI - 打包前检查
color 0A

echo.
echo ═══════════════════════════════════════════════════════════
echo   织梦AI大模型 - 打包前检查清单
echo ═══════════════════════════════════════════════════════════
echo.

set ERROR_COUNT=0

echo [检查 1/10] 检查 Python 环境...
if exist "IndexTTS2-SonicVale\installer_files\env\python.exe" (
    echo ✓ Python 环境存在
) else (
    echo ✗ Python 环境缺失
    set /a ERROR_COUNT+=1
)

echo.
echo [检查 2/10] 检查 IndexTTS2 模型文件...
if exist "IndexTTS2-SonicVale\checkpoints\gpt.pth" (
    echo ✓ IndexTTS2 模型存在
) else (
    echo ✗ IndexTTS2 模型缺失
    set /a ERROR_COUNT+=1
)

echo.
echo [检查 3/10] 检查 LatentSync 模型文件...
if exist "LatentSync\checkpoints\latentsync_unet.pt" (
    echo ✓ LatentSync 模型存在
) else (
    echo ✗ LatentSync 模型缺失
    set /a ERROR_COUNT+=1
)

echo.
echo [检查 4/10] 检查 LatentSync Python 环境...
if exist "LatentSync\latents_env\python.exe" (
    echo ✓ LatentSync Python 环境存在
) else (
    echo ✗ LatentSync Python 环境缺失
    set /a ERROR_COUNT+=1
)

echo.
echo [检查 5/10] 检查 FFmpeg...
if exist "LatentSync\ffmpeg-7.1\bin\ffmpeg.exe" (
    echo ✓ FFmpeg 存在
) else (
    echo ✗ FFmpeg 缺失
    set /a ERROR_COUNT+=1
)

echo.
echo [检查 6/10] 检查启动脚本...
if exist "启动应用.vbs" (
    echo ✓ 启动脚本存在
) else (
    echo ✗ 启动脚本缺失
    set /a ERROR_COUNT+=1
)

echo.
echo [检查 7/10] 检查主程序文件...
if exist "app_backend.py" (
    if exist "unified_app.py" (
        echo ✓ 主程序文件存在
    ) else (
        echo ✗ unified_app.py 缺失
        set /a ERROR_COUNT+=1
    )
) else (
    echo ✗ app_backend.py 缺失
    set /a ERROR_COUNT+=1
)

echo.
echo [检查 8/10] 检查配置文件...
if exist ".env" (
    echo ✓ 配置文件存在
) else (
    echo ✗ .env 配置文件缺失
    set /a ERROR_COUNT+=1
)

echo.
echo [检查 9/10] 检查 Logo 文件...
if exist "logo.ico" (
    if exist "logo.jpg" (
        echo ✓ Logo 文件存在
    ) else (
        echo ⚠ logo.jpg 缺失（不影响运行）
    )
) else (
    echo ⚠ logo.ico 缺失（不影响运行）
)

echo.
echo [检查 10/10] 检查输出目录...
if exist "unified_outputs" (
    echo ✓ 输出目录存在
) else (
    echo ⚠ 输出目录不存在，将自动创建
    mkdir unified_outputs
)

echo.
echo ═══════════════════════════════════════════════════════════
echo   检查完成
echo ═══════════════════════════════════════════════════════════
echo.

if %ERROR_COUNT%==0 (
    echo ✓ 所有必需文件检查通过，可以打包！
    echo.
    echo 建议操作：
    echo 1. 清理 unified_outputs 文件夹中的测试文件
    echo 2. 删除 gradio_error.log（如果存在）
    echo 3. 使用 7-Zip 或 WinRAR 压缩整个文件夹
    echo.
) else (
    echo ✗ 发现 %ERROR_COUNT% 个错误，请修复后再打包
    echo.
)

echo 按任意键退出...
pause >nul
