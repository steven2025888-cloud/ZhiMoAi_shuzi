@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo   ZhiMoAI - Online Python Environment Setup
echo ============================================================
echo.
echo   Target: _internal_app\installer_files\env
echo.

set "APP_ENV_DIR=%~dp0..\_internal_app\installer_files\env"
set "PYTHON_VERSION=3.10"
set "PIP_INDEX=-i https://pypi.tuna.tsinghua.edu.cn/simple"

echo [1/5] Checking system Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python not found. Install Python %PYTHON_VERSION% first.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   Found: Python %%v
echo.

echo [2/5] Creating virtual environment...
if exist "%APP_ENV_DIR%" (
    echo   Directory exists. Rebuild? [Y/N]
    set /p "confirm="
    if /i "!confirm!"=="Y" (
        echo   Removing old environment...
        rmdir /s /q "%APP_ENV_DIR%"
    ) else (
        echo   Cancelled.
        pause
        exit /b 0
    )
)

python -m venv "%APP_ENV_DIR%"
if errorlevel 1 (
    echo   [ERROR] venv creation failed
    pause
    exit /b 1
)
echo   [OK] venv created
echo.

echo [3/5] Installing dependencies...
set "HTTP_PROXY="
set "HTTPS_PROXY="
set "NO_PROXY="
set "PY=%APP_ENV_DIR%\Scripts\python.exe"

echo   Upgrading pip...
"%PY%" -m pip install --upgrade pip %PIP_INDEX% --quiet

echo.
echo   --- Core (gradio + web framework) ---
"%PY%" -m pip install gradio requests python-dotenv %PIP_INDEX%
if errorlevel 1 goto :install_failed

echo   --- UI (webview + tray + image) ---
"%PY%" -m pip install pywebview pystray "Pillow>=10.0,<11.0" %PIP_INDEX%
if errorlevel 1 goto :install_failed

echo   --- Media (opencv + audio + plotting) ---
"%PY%" -m pip install opencv-python numpy pydub matplotlib kiwisolver %PIP_INDEX%
if errorlevel 1 goto :install_failed

echo   --- Crypto + Network ---
"%PY%" -m pip install pycryptodome cryptography websockets aiohttp httptools %PIP_INDEX%
if errorlevel 1 goto :install_failed

echo   --- Automation (publishing) ---
"%PY%" -m pip install selenium pyautogui %PIP_INDEX%
if errorlevel 1 goto :install_failed

echo.
echo   [OK] All dependencies installed
echo.

echo [4/5] Verifying native extensions (*.pyd)...
"%PY%" -c "import sys; print(f'  Python: {sys.version}')"
"%PY%" -c "
failed = []
checks = [
    ('PIL._imaging',            'from PIL import Image, ImageTk, ImageDraw'),
    ('orjson',                  'import orjson'),
    ('pydantic_core',           'import pydantic_core'),
    ('numpy',                   'import numpy'),
    ('cv2',                     'import cv2'),
    ('aiohttp',                 'import aiohttp'),
    ('multidict',               'import multidict'),
    ('yarl',                    'import yarl'),
    ('markupsafe',              'import markupsafe'),
    ('cryptography',            'import cryptography'),
    ('cffi',                    'import cffi'),
    ('uvicorn',                 'import uvicorn'),
    ('starlette',               'import starlette'),
    ('fastapi',                 'import fastapi'),
    ('gradio',                  'import gradio'),
    ('webview',                 'import webview'),
    ('pystray',                 'import pystray'),
    ('websockets',              'import websockets'),
    ('httptools',               'import httptools'),
    ('regex',                   'import regex'),
    ('charset_normalizer',      'import charset_normalizer'),
    ('frozenlist',              'import frozenlist'),
    ('pydub',                   'import pydub'),
    ('selenium',                'import selenium'),
]
for name, stmt in checks:
    try:
        exec(stmt)
        print(f'  [OK] {name}')
    except Exception as e:
        failed.append((name, str(e)[:80]))
        print(f'  [FAIL] {name}: {e}')
if failed:
    print(f'\n  ERROR: {len(failed)} modules failed!')
    import sys; sys.exit(1)
else:
    print(f'\n  All {len(checks)} modules OK!')
"
if errorlevel 1 (
    echo.
    echo   [ERROR] Some native extensions are broken!
    echo   Try deleting _internal_app and running this script again.
    pause
    exit /b 1
)
echo.

echo [5/5] Environment size...
for /f "tokens=3" %%a in ('dir "%APP_ENV_DIR%" /s /-c 2^>nul ^| findstr "File(s)"') do set "SIZE=%%a"
echo   Total: %SIZE% bytes
echo.

echo ============================================================
echo   [OK] Environment ready!
echo ============================================================
echo.
echo   Location: %APP_ENV_DIR%
echo.
echo   Next: run build_scripts\build_package.bat to package
echo.
pause
exit /b 0

:install_failed
echo.
echo   [ERROR] pip install failed!
pause
exit /b 1
