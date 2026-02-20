@echo off
chcp 65001 >nul
title 织梦AI - Whisper 测试
color 0B

echo.
echo ═══════════════════════════════════════════════════════════
echo   Whisper 语音识别 - 功能测试
echo ═══════════════════════════════════════════════════════════
echo.

IndexTTS2-SonicVale\installer_files\env\python.exe test_whisper.py

pause
