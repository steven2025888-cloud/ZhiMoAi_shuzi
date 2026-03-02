@echo off
title ZhiMoAI - Repair Environment
setlocal enabledelayedexpansion

echo ============================================================
echo   ZhiMoAI - Auto Repair Native Extensions
echo ============================================================
echo.

cd /d "%~dp0"

set "LOG=repair_env.log"
echo.>%LOG%
echo [%date% %time%] repair_env start in: %CD%>>%LOG%

set "PY="
if exist "_internal_app\installer_files\env\Scripts\python.exe" (
    set "PY=_internal_app\installer_files\env\Scripts\python.exe"
) else if exist "_internal_app\installer_files\env\python.exe" (
    set "PY=_internal_app\installer_files\env\python.exe"
) else if exist "_internal_tts\installer_files\env\Scripts\python.exe" (
    set "PY=_internal_tts\installer_files\env\Scripts\python.exe"
) else if exist "_internal_tts\installer_files\env\python.exe" (
    set "PY=_internal_tts\installer_files\env\python.exe"
) else if exist "IndexTTS2-SonicVale\installer_files\env\Scripts\python.exe" (
    set "PY=IndexTTS2-SonicVale\installer_files\env\Scripts\python.exe"
) else if exist "IndexTTS2-SonicVale\installer_files\env\python.exe" (
    set "PY=IndexTTS2-SonicVale\installer_files\env\python.exe"
)

if "%PY%"=="" (
    echo [ERROR] Python not found!
    echo   Tried:
    echo     _internal_app\installer_files\env\Scripts\python.exe
    echo     _internal_tts\installer_files\env\Scripts\python.exe
    echo     IndexTTS2-SonicVale\installer_files\env\Scripts\python.exe
    echo [ERROR] Python not found!>>%LOG%
    pause
    exit /b 1
)

echo [OK] Python: %PY%
echo [OK] Python: %PY%>>%LOG%
echo.

echo [1/3] Checking modules...
set "CHECK_PY=_repair_check.py"
del /f /q "%CHECK_PY%" 2>nul
(
  echo # -*- coding: utf-8 -*-
  echo import sys
  echo def _run_checks(all_checks^):
  echo^    failed = []
  echo^    ok = 0
  echo^    for name, stmt in all_checks:
  echo^        try:
  echo^            exec(stmt, {})
  echo^            ok += 1
  echo^        except Exception as e:
  echo^            failed.append((name, str(e)))
  echo^            print(f"  [BROKEN] {name}: {e}")
  echo^    return ok, failed
  echo checks = [
  echo^    ('PIL',        'from PIL import Image, ImageTk, ImageDraw'),
  echo^    ('orjson',     'import orjson'),
  echo^    ('pydantic_core','import pydantic_core'),
  echo^    ('numpy',      'import numpy'),
  echo^    ('cv2',        'import cv2'),
  echo^    ('gradio',     'import gradio'),
  echo^    ('webview',    'import webview'),
  echo^    ('cryptography','import cryptography'),
  echo^    ('cffi',       'import cffi'),
  echo^    ('fastapi',    'import fastapi'),
  echo^    ('uvicorn',    'import uvicorn'),
  echo^    ('pystray',    'import pystray'),
  echo^    ('websockets', 'import websockets'),
  echo^    ('aiohttp',    'import aiohttp'),
  echo^    ('httptools',  'import httptools'),
  echo^    ('regex',      'import regex'),
  echo^    ('ujson',      'import ujson'),
  echo^    ('pydub',      'import pydub'),
  echo^    ('selenium',   'import selenium'),
  echo ]
  echo mode = (sys.argv[1] if len(sys.argv) ^> 1 else 'check').strip().lower()
  echo ok, failed = _run_checks(checks)
  echo if not failed:
  echo^    print(f"  All {ok} modules OK - no repair needed!")
  echo^    sys.exit(0)
  echo print(f"\n  {len(failed)} broken, {ok} ok")
  echo with open('_repair_list.txt','w', encoding='utf-8') as f:
  echo^    f.write(' '.join([n for n,_ in failed]))
  echo sys.exit(1)
) > "%CHECK_PY%"

"%PY%" "%CHECK_PY%" 1>>%LOG% 2>>&1
type %LOG%

if %ERRORLEVEL%==0 (
    echo.
    echo   Environment is healthy!
    echo   Environment is healthy!>>%LOG%
    pause
    exit /b 0
)

echo.
echo [2/3] Repairing broken modules...

set /p BROKEN=<_repair_list.txt
del _repair_list.txt 2>nul

echo   Installing: %BROKEN%
echo   Installing: %BROKEN%>>%LOG%
echo.

"%PY%" -m pip install --force-reinstall "Pillow>=10.0,<11.0" orjson pydantic pydantic_core numpy opencv-python gradio pywebview cryptography cffi fastapi uvicorn pystray websockets aiohttp httptools regex ujson pydub selenium --quiet 1>>%LOG% 2>>&1

if errorlevel 1 (
    echo.
    echo   [WARNING] Some packages may have failed. Retrying individually...
    for %%p in (Pillow orjson pydantic pydantic_core numpy opencv-python gradio pywebview cryptography cffi fastapi uvicorn pystray websockets aiohttp httptools regex ujson pydub selenium) do (
        "%PY%" -m pip install --force-reinstall %%p --quiet 2>nul
    )
)

echo.
echo [3/3] Verifying repair...
"%PY%" "%CHECK_PY%" verify 1>>%LOG% 2>>&1
type %LOG%

if errorlevel 1 (
    echo.
    echo   [ERROR] Repair incomplete. Manual fix needed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Repair complete! Try running the app now.
echo ============================================================
pause
