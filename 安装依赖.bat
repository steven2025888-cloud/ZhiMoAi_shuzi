@echo off
chcp 65001 >nul
echo ========================================
echo   织梦AI - 安装必要依赖
echo ========================================
echo.

echo [1/4] 安装 pystray（系统托盘图标支持）...
IndexTTS2-SonicVale\installer_files\env\python.exe -m pip install pystray -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [2/4] 安装 pywin32（Windows API 支持）...
IndexTTS2-SonicVale\installer_files\env\python.exe -m pip install pywin32 -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [3/4] 安装 Whisper（语音识别支持）...
IndexTTS2-SonicVale\installer_files\env\python.exe -m pip install openai-whisper -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [4/4] 验证安装...
IndexTTS2-SonicVale\installer_files\env\python.exe -c "import pystray; import win32gui; import whisper; print('✓ 所有依赖安装成功')"

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo 已安装的组件：
echo   ✓ pystray - 系统托盘图标
echo   ✓ pywin32 - Windows API
echo   ✓ Whisper - 语音识别引擎
echo.
pause
