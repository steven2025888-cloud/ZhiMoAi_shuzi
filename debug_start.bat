@echo off
title ZhiMoAI Debug
echo ============================================================
echo   ZhiMoAI Debug Launcher
echo ============================================================
echo.

cd /d "%~dp0"

set "PYTHON_EXE="
if exist "_internal_tts\installer_files\env\Scripts\python.exe" (
    set "PYTHON_EXE=_internal_tts\installer_files\env\Scripts\python.exe"
) else if exist "_internal_tts\installer_files\env\python.exe" (
    set "PYTHON_EXE=_internal_tts\installer_files\env\python.exe"
) else if exist "IndexTTS2-SonicVale\installer_files\env\Scripts\python.exe" (
    set "PYTHON_EXE=IndexTTS2-SonicVale\installer_files\env\Scripts\python.exe"
) else if exist "IndexTTS2-SonicVale\installer_files\env\python.exe" (
    set "PYTHON_EXE=IndexTTS2-SonicVale\installer_files\env\python.exe"
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)

echo [OK] Python: %PYTHON_EXE%

set "APP_BACKEND="
if exist "app_backend.pyc" (
    set "APP_BACKEND=app_backend.pyc"
    echo [OK] App: app_backend.pyc
) else if exist "app_backend.py" (
    set "APP_BACKEND=app_backend.py"
    echo [OK] App: app_backend.py
) else (
    echo [ERROR] app_backend not found!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Starting... (all errors will show here)
echo   Close this window = stop program
echo ============================================================
echo.

"%PYTHON_EXE%" -u "%APP_BACKEND%"

echo.
echo ============================================================
echo   Program exited (code: %ERRORLEVEL%)
echo ============================================================
pause
